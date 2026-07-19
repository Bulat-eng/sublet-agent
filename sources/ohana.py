"""
Ohana (liveohana.ai) scraper.

liveohana.ai is a Bubble.io app. Its public Data API exposes the `listing`
object at /api/1.1/obj/listing, so we can pull structured data over plain HTTP
— no headless browser (this is why Ohana moved from Phase 2 into Phase 1).

We constrain server-side to Live listings in the NYC-area cities (config.OHANA_CITIES),
newest first, and hand them to the shared filter for neighborhood/budget narrowing.

Notes learned from the live API (see 99_troubleshooting.md):
  - Rent lives in min_rent_number / max_rent_number / price_number (monthly).
    nightly_rate_number is used only for nightly stays.
  - neighborhood_geographic_address is unreliable (a Williamsburg listing was
    geocoded to Brisbane, AU; an Astoria one to Oregon) — we only trust it when
    it resolves to NY, and otherwise let the title carry the neighborhood.
  - lease_type "Prime lease" is a straight rental, not a sublet — kept but flagged.
"""

from __future__ import annotations

import json
import logging

import requests

import config
from models import Listing

logger = logging.getLogger(__name__)

API_URL = "https://liveohana.ai/api/1.1/obj/listing"
LISTING_URL = "https://liveohana.ai/listing/{slug}"
NIGHTLY_TO_MONTHLY = 30.4

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def _price(r: dict) -> tuple[int | None, str | None]:
    """Return (monthly_price, flag). Prefer the monthly rent fields; fall back to
    a nightly rate normalized to a monthly figure (flagged as short-term)."""
    for key in ("min_rent_number", "max_rent_number", "price_number", "total_rent_number"):
        v = r.get(key)
        if isinstance(v, (int, float)) and v > 0:
            return int(round(v)), None
    nightly = r.get("nightly_rate_number")
    if isinstance(nightly, (int, float)) and nightly > 0:
        monthly = int(round(nightly * NIGHTLY_TO_MONTHLY))
        return monthly, f"nightly rate (~${monthly:,}/mo equiv) — verify total cost"
    return None, None


def _neighborhood(r: dict) -> str | None:
    """Only trust the geocoded neighborhood when it resolves to New York — the
    field is otherwise noisy. The title (matched by filter.py) is the real source."""
    geo = r.get("neighborhood_geographic_address") or {}
    addr = geo.get("address") or ""
    if ", NY" in addr or addr.endswith("NY, USA"):
        return addr.split(",")[0].strip() or None
    return None


def _iso_date(val) -> str | None:
    if isinstance(val, str) and len(val) >= 10 and val[4] == "-" and val[7] == "-":
        return val[:10]
    return None


def _furnished(r: dict) -> bool | None:
    status = (r.get("furnished_status_option_os_furnished_status") or "").lower()
    if not status:
        return None
    if "unfurnished" in status:
        return False
    if "furnished" in status or "move-in" in status:
        return True
    return None


def _to_listing(r: dict) -> Listing | None:
    slug = r.get("Slug")
    lid = r.get("_id")
    if not slug and not lid:
        return None
    url = LISTING_URL.format(slug=slug) if slug else "https://liveohana.ai"

    city = r.get("city_name_text") or "New York"
    title = (r.get("title_text") or "").strip() or f"Ohana listing in {city}"
    body = (r.get("long_description_text") or "").strip()

    price, price_flag = _price(r)

    flags: list[str] = []
    if price_flag:
        flags.append(price_flag)
    # A "Prime lease" is a direct rental, not a sublet — keep it, but mark it
    # (same convention as the Reddit direct-rental rescue). Never silently dropped.
    if (r.get("lease_type_option_os_lease_type") or "").lower().startswith("prime"):
        flags.append("direct rental, not a sublet")

    return Listing(
        id=f"oh_{lid}" if lid else f"oh_{slug}",
        source="ohana",
        url=url,
        title=title,
        price=price,
        neighborhood=_neighborhood(r),
        move_in_date=_iso_date(r.get("move_in_available_date")),
        move_out_date=_iso_date(r.get("move_out_date_date")),
        furnished=_furnished(r),
        body_snippet=body[:300],
        posted_at=_iso_date(r.get("date_published_date")),
        flagged="; ".join(flags) or None,
    )


def fetch() -> list[Listing]:
    """Pull recent Live NYC-area listings from the Ohana Bubble Data API."""
    constraints = [
        {"key": "status_option_listing_status", "constraint_type": "equals", "value": "Live"},
        {"key": "city_name_text", "constraint_type": "in", "value": config.OHANA_CITIES},
    ]
    params = {
        "limit": min(config.OHANA_FETCH_LIMIT, 100),
        "constraints": json.dumps(constraints),
        "sort_field": "date_published_date",
        "descending": "true",
    }
    try:
        resp = requests.get(API_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=25)
        if resp.status_code != 200:
            logger.warning(f"[Ohana] HTTP {resp.status_code}")
            return []
        results = resp.json().get("response", {}).get("results", [])
    except Exception as exc:
        logger.warning(f"[Ohana] fetch failed: {exc}")
        return []

    out: list[Listing] = []
    for r in results:
        listing = _to_listing(r)
        if listing:
            out.append(listing)
    logger.info(f"[Ohana] {len(out)} Live NYC-area listings")
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    listings = fetch()
    print(f"\n=== {len(listings)} listings ===")
    for r in listings[:10]:
        flag = f"  [{r.flagged}]" if r.flagged else ""
        print(f"{r.id} | ${r.price} | {r.neighborhood or '-'} | {r.title[:45]}{flag}")
