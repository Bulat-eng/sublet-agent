"""
Listings Project scraper.
listingsproject.com — curated NYC sublets/rentals, refreshed weekly (digest Wed).

Strategy: scrape the public NYC real-estate index pages, one card per listing.

History: the old site path (/listings/housing/new-york) started returning 404
after a 2026 site restructure — the scraper silently produced 0 listings every
run. The current structure is:
  - NYC index:    /real-estate/new-york-city  (paginated ?page=N)
  - listing card: /listings/<slug>            (stable numeric data-listingid)
Cards mix monthly, weekly and nightly rates; we normalize everything to a
monthly-equivalent price so the shared budget filter behaves, and flag any
non-monthly rate so it's never silently misread. See 99_troubleshooting.md.
"""

from __future__ import annotations

import re
import hashlib
import logging
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from models import Listing

logger = logging.getLogger(__name__)

NYC_URL = "https://www.listingsproject.com/real-estate/new-york-city"
MAX_PAGES = 3          # newest ~36 listings; dedup makes re-scraping cheap
REQUEST_DELAY = 1.0    # polite pause between pages

# Rate-period → monthly multiplier. Listings Project short-term stays quote
# weekly and nightly rates; leaving those as a raw "monthly" price would let a
# $650/night place slip under a monthly budget cap. ~4.33 weeks / ~30.4 days per month.
_PERIOD_MULT = {"month": 1.0, "week": 52 / 12, "day": 30.4, "night": 30.4}

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
)


def _headers() -> dict:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _make_id(listing_id: str | None, slug: str) -> str:
    if listing_id:
        return f"lp_{listing_id}"
    return "lp_" + hashlib.md5(slug.encode()).hexdigest()[:12]


def _parse_price(text: str) -> tuple[int | None, str | None]:
    """Parse a Listings Project rate.

    Returns (monthly_equivalent_price, period) where period is one of
    month/week/day/night (or None if no explicit period was given — treated as
    monthly). A bare '$2,600' is assumed monthly.
    """
    m = re.search(r"\$\s*([\d,]+)\s*(?:/|per\s+)?\s*(month|week|day|night)?", text, re.IGNORECASE)
    if not m:
        return None, None
    try:
        raw = int(m.group(1).replace(",", ""))
    except ValueError:
        return None, None
    period = (m.group(2) or "").lower() or None
    mult = _PERIOD_MULT.get(period or "month", 1.0)
    return int(round(raw * mult)), period


def _parse_dates(text: str) -> tuple[str | None, str | None]:
    """Extract move-in / move-out ISO dates from a range like
    'July 17, 2026 - July 31, 2026'. Returns (move_in, move_out)."""
    found = re.findall(r"[A-Z][a-z]+ \d{1,2}, \d{4}", text)
    out: list[str] = []
    for f in found[:2]:
        try:
            out.append(datetime.strptime(f, "%B %d, %Y").date().isoformat())
        except ValueError:
            pass
    move_in = out[0] if out else None
    move_out = out[1] if len(out) > 1 else None
    return move_in, move_out


def _card_container(node):
    """Climb from a title <h4> to the smallest ancestor that also holds the
    card's bookmark element (which carries the stable data-listingid)."""
    card = node
    for _ in range(6):
        card = card.parent
        if card is None:
            return node
        if card.find(attrs={"data-listingid": True}):
            return card
    return node


def _parse_card(h4) -> Listing | None:
    a = h4.find("a", href=re.compile(r"^/listings/"))
    if not a:
        return None
    href = a.get("href", "")
    slug = href.rstrip("/").split("/")[-1]
    url = href if href.startswith("http") else f"https://www.listingsproject.com{href}"
    title = a.get_text(strip=True) or slug.replace("-", " ")

    card = _card_container(h4)
    card_text = card.get_text(" ", strip=True)

    bm = card.find(attrs={"data-listingid": True})
    listing_id = bm.get("data-listingid") if bm else None

    # Price lives in a highlighted <span> like "$850/week" / "$2,600".
    price, period = None, None
    for span in card.find_all("span"):
        t = span.get_text(" ", strip=True)
        if re.search(r"\$\s*[\d,]+", t):
            price, period = _parse_price(t)
            break

    # Neighborhood row: "Flatbush, Brooklyn | Apartments for Sublet | Pet Friendly"
    neighborhood = None
    for div in card.select("div.text-grey-dark"):
        t = div.get_text(" ", strip=True)
        if "|" in t:
            neighborhood = t.split("|")[0].strip()
            break

    move_in, move_out = _parse_dates(card_text)

    body = ""
    p = card.find("p")
    if p:
        body = re.sub(r"\s+", " ", p.get_text(" ", strip=True))[:300]

    flagged = None
    if period and period != "month":
        adverb = {"week": "weekly", "day": "daily", "night": "nightly"}.get(period, period)
        flagged = f"short-term {adverb} rate (~${price:,}/mo equiv) — verify total cost"

    return Listing(
        id=_make_id(listing_id, slug),
        source="listings_project",
        url=url,
        title=title,
        price=price,
        neighborhood=neighborhood,
        move_in_date=move_in,
        move_out_date=move_out,
        body_snippet=body,
        flagged=flagged,
    )


def _fetch_page(page: int) -> list[Listing]:
    url = NYC_URL if page == 1 else f"{NYC_URL}?page={page}"
    resp = requests.get(url, headers=_headers(), timeout=20)
    if resp.status_code != 200:
        logger.warning(f"LP page {page}: HTTP {resp.status_code}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    out: list[Listing] = []
    seen: set[str] = set()
    for h4 in soup.find_all("h4"):
        a = h4.find("a", href=re.compile(r"^/listings/"))
        if not a or a.get("href") in seen:
            continue
        seen.add(a.get("href"))
        listing = _parse_card(h4)
        if listing:
            out.append(listing)
    return out


def fetch() -> list[Listing]:
    """Scrape recent NYC listings from Listings Project (first MAX_PAGES pages)."""
    out: list[Listing] = []
    seen_ids: set[str] = set()
    try:
        for page in range(1, MAX_PAGES + 1):
            page_listings = _fetch_page(page)
            if not page_listings:
                break  # ran past the last page (or a transient error) — stop
            for l in page_listings:
                if l.id not in seen_ids:
                    seen_ids.add(l.id)
                    out.append(l)
            if page < MAX_PAGES:
                time.sleep(REQUEST_DELAY)
        logger.info(f"[LP] {len(out)} NYC listings across {page} page(s)")
        return out
    except Exception as exc:
        logger.warning(f"LP fetch failed: {exc}")
        return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = fetch()
    print(f"\n=== {len(results)} listings ===")
    for r in results[:10]:
        flag = f"  [{r.flagged}]" if r.flagged else ""
        print(f"{r.id} | ${r.price} | {r.neighborhood} | {r.title[:45]}{flag}")
