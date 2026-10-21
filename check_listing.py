"""
Check one listing for scam signals, with the same rules the digest uses (scam.py).

    .venv/bin/python check_listing.py https://newyork.craigslist.org/...   # fetches the page
    .venv/bin/python check_listing.py listing.md                           # saved/pasted text
    pbpaste | .venv/bin/python check_listing.py -                          # clipboard

For text, the first line is taken as the title and the first "$1,234" as the
price. Pasted text has no Craigslist tags, so the garage / EV / wheelchair /
laundry checks are skipped. The "same text posted elsewhere" check compares
against the agent's Craigslist cache (state.db) when it is present.

The agent never sees replies, and most October scams were confirmed by theirs:
read "Before you pay anyone" in SCAM_FILTER.md before sending money or documents.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys

import requests

import config
import scam
from filter import _SCAM_RE, _assign_region


def filter_region(area: str) -> str:
    return _assign_region(area)[0]
from models import Listing
from sources import craigslist

STATE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.db")


def _from_url(url: str) -> Listing:
    resp = requests.get(url, headers=craigslist._headers(), timeout=15)
    if resp.status_code != 200:
        sys.exit(f"{url} returned HTTP {resp.status_code}" +
                 (" — the post was removed (often by Craigslist, for scams)" if resp.status_code == 410 else ""))
    d = craigslist.parse_detail(resp.text)
    return Listing(
        id="__checked__", source="craigslist_nyc", url=url, title=d.get("title", ""),
        price=d.get("price"), bedrooms=d.get("bedrooms"), body=d.get("body", ""),
        body_snippet=d.get("description", ""), attrs=d.get("attrs", {}),
        category=d.get("category"),
    )


def _from_text(text: str) -> Listing:
    lines = [ln.strip() for ln in text.strip().splitlines()]
    title = re.sub(r"^[#*>\-\s]+|[*\s]+$", "", lines[0]) if lines else ""
    body = " ".join(ln for ln in lines[1:] if ln)
    prices = [int(p.replace(",", "")) for p in re.findall(r"\$\s?(\d{1,2},?\d{3})\b", text)]
    price = next((p for p in prices if 300 <= p <= 20000), None)
    return Listing(id="__checked__", source="manual", url="", title=title, price=price,
                   body=body, body_snippet=body[:300])


def _cached_listings(skip_url: str) -> list[Listing] | None:
    if not os.path.exists(STATE_DB):
        return None
    conn = sqlite3.connect(f"file:{STATE_DB}?mode=ro", uri=True)
    try:
        rows = conn.execute("SELECT url, detail FROM cl_details").fetchall()
    finally:
        conn.close()
    out = []
    for url, detail in rows:
        if url == skip_url:
            continue
        d = json.loads(detail)
        out.append(Listing(id=url, source="craigslist_nyc", url=url, title=d.get("title", ""),
                           body=d.get("body", ""), body_snippet=d.get("description", "")))
    return out


def check(l: Listing) -> int:
    text = " ".join(filter(None, [l.title, l.body]))
    l.region, hood = _assign_region(text)
    kind = scam.unit_kind(l)
    cached = _cached_listings(l.url)
    families = scam.template_families([l] + cached) if cached is not None else None
    reasons = scam.assess(l, hood, families)
    score = sum(p for p, _ in reasons)

    area = scam.located_area(l)     # what the price / subway / landmark checks judge it as
    if area and area in config.NEIGHBORHOOD_KEYWORDS:
        where = f"{scam._area_label(area)} ({config.REGIONS[filter_region(area)]['label']})"
    elif area:
        where = f"{scam._area_label(area)} (outside the search areas)"
    else:
        where = "no neighborhood named" if not hood else f"only named as a commute ({scam._area_label(hood)})"
    price = f"${l.price:,}" if l.price else "no price found"
    print(f"\n{l.title or '(no title)'}\n{price} · {kind or 'unit type unclear'} · {where}\n")

    lvl = scam.level(score)
    banner = {"likely": "🚩 LIKELY SCAM", "verify": "⚠️  VERIFY", "clean": "✅ no strong signals"}[lvl]
    print(f"{banner} — scam score {score}  "
          f"(verify ≥ {config.SCAM_FLAG_SCORE}, likely ≥ {config.SCAM_LIKELY_SCORE})")
    for points, why in reasons:
        print(f"   +{points}  {why}")
    if config.SCAM_DROP_SCORE is not None and score >= config.SCAM_DROP_SCORE:
        print(f"\n   The agent would not email this one (drops at scam score {config.SCAM_DROP_SCORE}).")

    classic = _SCAM_RE.search(text)
    if classic:
        print(f"\n   Classic tell \"{classic.group(0)}\" — the agent drops these outright "
              "when they appear in a post's first 300 characters.")

    skipped = []
    if not l.attrs:
        skipped.append("Craigslist tags (garage, EV charging, wheelchair, laundry): none in pasted text")
    if not area:
        skipped.append("price vs. median, subway lines, landmarks: no neighborhood named")
    elif kind not in ("studio", "1br"):
        skipped.append("price vs. median: only whole studios and 1BRs are compared")
    elif scam.is_short_stay(l):
        skipped.append("price vs. median: short stay, priced per stay")
    if families is None:
        skipped.append("same text posted elsewhere: no state.db cache here")
    if skipped:
        print("\nNot checked:")
        for s in skipped:
            print(f"   – {s}")
    print("\nThe agent can't see replies. Before paying anyone, read "
          "\"Before you pay anyone\" in SCAM_FILTER.md.")
    return score


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    if arg.startswith(("http://", "https://")):
        listing = _from_url(arg)
    elif arg == "-":
        listing = _from_text(sys.stdin.read())
    else:
        with open(arg, encoding="utf-8") as f:
            listing = _from_text(f.read())
    check(listing)


if __name__ == "__main__":
    main()
