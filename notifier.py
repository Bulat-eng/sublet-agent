"""
Notification dispatch — email only.

Delivery: Gmail SMTP (smtp.gmail.com:465) using a Gmail App Password.
Set SENDER_EMAIL + GMAIL_APP_PASSWORD (env) to the sending Gmail account and
TARGET_EMAIL to the inbox that receives the digest.

Listings are grouped into labelled sections by region (Midtown, Midtown → FiDi,
FiDi, North Brooklyn, Central Brooklyn, South Brooklyn) within a single HTML
digest email, sent once per run whenever there are new matches (near-real-time).
"""

from __future__ import annotations

import sys
import ssl
import smtplib
import logging
from datetime import datetime
from html import escape as html_escape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config
from models import Listing

logger = logging.getLogger(__name__)


# ─── Source labels ────────────────────────────────────────────────────────────

SOURCE_LABELS = {
    "craigslist_nyc":   "Craigslist NYC",
    "craigslist":       "Craigslist",
    "listings_project": "Listings Project",
    "spareroom":        "SpareRoom",
    "ohana":            "Ohana",
    "leasebreak":       "LeaseBreak",
    "facebook":         "Facebook",
}


def _source_label(source: str) -> str:
    for prefix, label in SOURCE_LABELS.items():
        if source.startswith(prefix):
            return label
    if source.startswith("reddit"):
        parts = source.split("_", 1)
        return f"r/{parts[1]}" if len(parts) > 1 and parts[1] else "Reddit"
    return source


# ─── Price vs. neighborhood median ────────────────────────────────────────────

def _price_vs_median(l: Listing) -> dict | None:
    """Compare a listing's price to the neighborhood median in config.MEDIANS.

    Returns {median, diff_pct, label, below} or None when we can't compare
    (missing price/neighborhood/bedrooms, or no median on file).
    """
    if not l.price or not l.neighborhood or l.bedrooms is None:
        return None
    med = config.MEDIANS.get(l.neighborhood.lower())
    if not med:
        return None
    key = "studio" if l.bedrooms == 0 else f"{l.bedrooms}br"
    m = med.get(key)
    if not m:
        return None
    diff_pct = round((m - l.price) / m * 100)
    label = "studio" if l.bedrooms == 0 else f"{l.bedrooms}BR"
    return {"median": m, "diff_pct": diff_pct, "label": label, "below": diff_pct > 0}


# ─── Single listing card ──────────────────────────────────────────────────────

def _listing_card(l: Listing) -> str:
    title = html_escape((l.title or "Listing")[:90])
    url   = html_escape(l.url or "#")
    hood  = html_escape(l.neighborhood or "NYC")
    price_str = f"${l.price:,}" if l.price else "Price on request"

    # Beds
    br_html = ""
    if l.bedrooms is not None:
        br_html = "Studio" if l.bedrooms == 0 else f"{l.bedrooms} Bed"
        br_html = f"&nbsp; {br_html}"

    # % below median
    cmp = _price_vs_median(l)
    cmp_html = ""
    if cmp and cmp["below"] and cmp["diff_pct"] >= 1:
        cmp_html = (
            '<div style="border-left:3px solid #10B981;padding-left:10px;margin:6px 0 10px;">'
            f'<span style="color:#059669;font-weight:700;font-size:13px;">'
            f'↓ {cmp["diff_pct"]}% below {hood} {cmp["label"]} median</span><br>'
            f'<span style="color:#9CA3AF;font-size:12px;">Area median: ${cmp["median"]:,}/mo</span>'
            '</div>'
        )

    # Tag pills: furnished + soft-filter tags (early-move-in, short-2mo, …)
    pills = []
    if l.furnished is True:
        pills.append(("🛋️ Furnished", "#FEF3C7", "#92400E"))
    if l.duration_months:
        pills.append((f"📅 {l.duration_months}mo", "#E0E7FF", "#3730A3"))
    if l.move_in_date:
        pills.append((f"➡️ move-in {html_escape(l.move_in_date)}", "#DBEAFE", "#1E40AF"))
    for t in (l.tags or []):
        pills.append((html_escape(t), "#F3F4F6", "#374151"))
    pills_html = ""
    if pills:
        chips = "".join(
            f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:10px;'
            f'font-size:11px;font-weight:600;margin-right:4px;">{text}</span>'
            for text, bg, fg in pills
        )
        pills_html = f'<div style="margin:8px 0;">{chips}</div>'

    # Soft "filter not passed" flag — still shown, just marked
    flag_html = ""
    if l.flagged:
        flag_html = (
            '<p style="color:#B45309;font-size:13px;margin:6px 0;">'
            f'⚠️ filter not passed — {html_escape(l.flagged)}</p>'
        )

    # Description snippet
    desc = html_escape((l.body_snippet or "")[:280])
    desc_html = (
        f'<p style="color:#374151;font-size:13px;line-height:1.55;margin:10px 0 6px;">{desc}…</p>'
        if desc else ""
    )

    source = html_escape(_source_label(l.source))

    return f"""
<div style="border:1px solid #E5E7EB;border-radius:14px;padding:20px 22px;margin-bottom:18px;
            background:#FFFFFF;">
  <a href="{url}" style="text-decoration:none;">
    <p style="margin:0;font-size:17px;font-weight:700;color:#111827;line-height:1.3;">{title}</p>
  </a>
  <p style="margin:3px 0 0;color:#6B7280;font-size:13px;">{hood}</p>

  <div style="margin:10px 0 2px;">
    <span style="font-size:26px;font-weight:800;color:#111827;">{price_str}</span>
    <span style="color:#9CA3AF;font-size:14px;">/mo {br_html}</span>
  </div>

  {cmp_html}
  {pills_html}
  {flag_html}
  {desc_html}

  <div style="margin-top:14px;">
    <a href="{url}" style="background:#1D4ED8;color:#fff;padding:9px 20px;border-radius:8px;
       text-decoration:none;font-weight:600;font-size:14px;display:inline-block;">View listing →</a>
    <span style="color:#D1D5DB;font-size:12px;margin-left:12px;">via {source}</span>
  </div>
</div>
"""


# ─── Full digest HTML ─────────────────────────────────────────────────────────

def _group_by_region(listings: list[Listing]) -> dict[str, list[Listing]]:
    """Bucket listings by region key, preserving config.REGIONS ordering."""
    buckets: dict[str, list[Listing]] = {}
    for l in listings:
        buckets.setdefault(l.region or "other", []).append(l)
    ordered = {k: buckets[k] for k in config.REGIONS if k in buckets}
    if "other" in buckets:
        ordered["other"] = buckets["other"]
    return ordered


def _build_html(listings: list[Listing]) -> str:
    count = len(listings)
    now   = datetime.now().strftime("%B %d, %Y · %I:%M %p ET")

    sections = []
    for region_key, region_listings in _group_by_region(listings).items():
        region = config.REGIONS.get(region_key, {"label": "Other", "emoji": "📌"})
        n = len(region_listings)
        header = (
            f'<h2 style="font-size:16px;font-weight:700;color:#111827;'
            f'margin:26px 0 12px;">{region["emoji"]} {html_escape(region["label"])} '
            f'<span style="color:#9CA3AF;font-weight:500;">({n})</span></h2>'
        )
        cards = "\n".join(_listing_card(l) for l in region_listings)
        sections.append(header + cards)

    area_summary = " · ".join(r["label"] for r in config.REGIONS.values())

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F3F4F6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
<div style="max-width:620px;margin:0 auto;padding:28px 16px;">

  <div style="text-align:center;margin-bottom:8px;">
    <h1 style="font-size:24px;font-weight:800;color:#111827;margin:0 0 6px;">🏙️ NYC Rental Digest</h1>
    <p style="color:#6B7280;font-size:14px;margin:0;">{now}</p>
    <p style="color:#1D4ED8;font-size:15px;font-weight:600;margin:6px 0 0;">
      {count} new listing{"s" if count != 1 else ""} found
    </p>
  </div>

  {"".join(sections)}

  <div style="text-align:center;margin-top:32px;padding-top:20px;border-top:1px solid #E5E7EB;">
    <p style="color:#9CA3AF;font-size:12px;line-height:1.6;margin:0;">
      {html_escape(area_summary)}<br>
      Max ${config.MAX_RENT:,}/mo · Studios–{config.MAX_BEDROOMS}BR · Sublets · Rooms · Direct rentals · Furnished flagged
    </p>
  </div>

</div>
</body>
</html>"""


# ─── Send via Gmail SMTP ──────────────────────────────────────────────────────

def _send_gmail(subject: str, html: str) -> bool:
    sender   = config.SENDER_EMAIL
    password = config.GMAIL_APP_PASSWORD
    to       = config.TARGET_EMAIL

    if not sender or not password:
        logger.error("SENDER_EMAIL or GMAIL_APP_PASSWORD not set — cannot send email")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"NYC Rental Agent <{sender}>"
    msg["To"]      = to
    msg.attach(MIMEText(html, "html"))

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx, timeout=30) as srv:
            srv.login(sender, password)
            srv.sendmail(sender, [to], msg.as_string())
        logger.info(f"Gmail SMTP: digest sent to {to}")
        return True
    except Exception as exc:
        logger.error(f"Gmail SMTP failed: {exc}")
        return False


# ─── Public API ───────────────────────────────────────────────────────────────

def notify(listings: list[Listing]) -> bool:
    """Send the digest email. Returns True on success (so main.py marks seen)."""
    if not listings:
        logger.info("notify: no listings to send")
        return False

    n = len(listings)
    subject = f"🏙️ {n} new NYC listing{'s' if n != 1 else ''} — ${config.MAX_RENT:,} max"
    html = _build_html(listings)
    return _send_gmail(subject, html)


# ─── CLI helper ───────────────────────────────────────────────────────────────

def _send_test():
    """Send a hardcoded test digest across the regions."""
    samples = [
        Listing(id="test_mid", source="spareroom",
                url="https://example.com/mid", title="TEST Midtown: $1,750 room in Murray Hill",
                price=1750, neighborhood="Murray Hill", bedrooms=1,
                body_snippet="Test notification — Midtown section.", region="midtown"),
        Listing(id="test_m", source="craigslist_nyc",
                url="https://example.com/m", title="TEST Midtown→FiDi: $2,200 sublet in East Village",
                price=2200, neighborhood="East Village", duration_months=3,
                move_in_date="2026-06-15", furnished=True, bedrooms=1,
                body_snippet="Test notification — Midtown → FiDi section.", region="midtown_to_fidi"),
        Listing(id="test_fidi", source="craigslist_nyc",
                url="https://example.com/fidi", title="TEST FiDi: $1,800 studio in Financial District",
                price=1800, neighborhood="Financial District", bedrooms=0,
                body_snippet="Test notification — FiDi section.", region="fidi"),
        Listing(id="test_nbk", source="spareroom",
                url="https://example.com/nbk", title="TEST North BK: $1,900 room in East Williamsburg",
                price=1900, neighborhood="East Williamsburg", bedrooms=1,
                body_snippet="Test notification — North Brooklyn section.", region="north_brooklyn"),
        Listing(id="test_cbk", source="craigslist_nyc",
                url="https://example.com/cbk", title="TEST Central BK: $2,100 sublet in Park Slope",
                price=2100, neighborhood="Park Slope", bedrooms=1,
                body_snippet="Test notification — Central Brooklyn section.", region="central_brooklyn"),
        Listing(id="test_sbk", source="craigslist_nyc",
                url="https://example.com/sbk", title="TEST South BK: $1,700 sublet in Ditmas Park",
                price=1700, neighborhood="Ditmas Park", bedrooms=1,
                body_snippet="Test notification — South Brooklyn section.", region="south_brooklyn"),
    ]
    ok = notify(samples)
    print("✅ Sent" if ok else "❌ Send failed — check logs above")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        _send_test()
    else:
        print("Usage:")
        print("  python -m notifier --test   # send a test digest email to TARGET_EMAIL")
