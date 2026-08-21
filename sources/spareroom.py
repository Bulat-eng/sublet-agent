"""
SpareRoom NYC scraper.
spareroom.com/rooms-for-rent/nyc — plain HTML, no Cloudflare.

Free tier strategy: scrape all visible listings. Skip the $14/wk "Early Bird"
upsell — for an automated agent that hits new listings on day 1, 7-day-old
ads are fine.
"""

from __future__ import annotations

import re
import hashlib
import logging
import random
import time

import requests
from bs4 import BeautifulSoup

import config
from models import Listing

logger = logging.getLogger(__name__)

BASE = "https://www.spareroom.com"

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# Neighborhood pages are narrow (~11 listings on page 1). One page per area keeps
# the per-run request count reasonable across ~30 areas; bump for deeper history.
PAGES_PER_AREA = 1


def _headers() -> dict:
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }


def _make_id(url: str) -> str:
    m = re.search(r"/(\d{6,})", url)
    return "sr_" + (m.group(1) if m else hashlib.md5(url.encode()).hexdigest()[:12])


def _parse_price(text: str) -> int | None:
    """SpareRoom shows prices like '$1,800 pcm' (per calendar month) or '$415 pw' (per week)."""
    m = re.search(r"\$\s*([\d,]+)\s*(pcm|pw|monthly|weekly|/mo|/wk)?", text, re.IGNORECASE)
    if not m:
        return None
    try:
        amount = int(m.group(1).replace(",", ""))
    except ValueError:
        return None
    unit = (m.group(2) or "").lower()
    if unit in ("pw", "weekly", "/wk"):
        return int(amount * 52 / 12)   # convert weekly → monthly
    return amount


# Bare borough/city labels — useless as a neighborhood, and setting one would
# stop filter.py from deriving a specific hood from the matched keyword.
_GENERIC_HOODS = {
    "brooklyn", "manhattan", "new york", "new york city", "nyc",
    "queens", "bronx", "staten island",
}


def _parse_from_data_attrs(card, listing_id: str) -> Listing | None:
    """Parse a listing tile from its data-listing-* attributes.

    Both the SEO area pages and the search-results pages render tiles as
    <li class="listing-result"> carrying data-listing-id / -title / -neighbourhood
    / -ad-rate-normalised. Those are far steadier than scraping rendered text —
    and the visible anchor differs between the two page types (a fad_click.pl
    tracking redirect on SEO pages, room_for_rent.pl on search pages), so the
    permalink is rebuilt from the id instead of read off the tile.
    """
    card_text = card.get_text(" ", strip=True)
    if re.search(r"deposit taken|let agreed|no longer available", card_text, re.IGNORECASE):
        return None

    title = (card.get("data-listing-title") or "SpareRoom NYC").strip()[:160]
    url = f"{BASE}/roommate/room_for_rent.pl?flatshare_id={listing_id}"

    rate = (card.get("data-listing-ad-rate-normalised")
            or card.get("data-listing-ad-headline-rate") or "")
    period = (card.get("data-listing-ad-rate-normalised-period")
              or card.get("data-listing-ad-headline-rate-period") or "")
    price = _parse_price(f"{rate} {period}".strip()) if rate else _parse_price(card_text)

    # SpareRoom writes some hyphenated names spaced out ("Bedford - Stuyvesant");
    # collapse so the config keyword ("bedford-stuyvesant") matches.
    hood = re.sub(r"\s+-\s+", "-", (card.get("data-listing-neighbourhood") or "").strip())
    specific = hood and hood.lower() not in _GENERIC_HOODS

    text_low = card_text.lower()
    furnished = True if "furnished" in text_low else (False if "unfurnished" in text_low else None)

    # Prepend the hood so filter.py can match on it even when it appears nowhere
    # in the title or the tile's visible text.
    snippet = f"{hood}. {card_text}"[:300] if specific else card_text[:300]

    return Listing(
        id=f"sr_{listing_id}",
        source="spareroom",
        url=url,
        title=title,
        price=price,
        neighborhood=hood if specific else None,
        furnished=furnished,
        body_snippet=snippet,
    )


def _parse_listing_card(card) -> Listing | None:
    """Parse one listing tile from a search-results or SEO area page."""
    listing_id = card.get("data-listing-id")
    if listing_id:
        return _parse_from_data_attrs(card, str(listing_id))

    # Fallback: older/plainer markup with no data attributes.
    a = card.select_one("a[href*='/flatshare/']") or card.find("a", href=True)
    if not a:
        return None

    href = a.get("href", "")
    if not href:
        return None
    url = href if href.startswith("http") else f"{BASE}{href}"

    card_text = card.get_text(" ", strip=True)

    # Skip listings already marked "Deposit taken"
    if re.search(r"deposit taken|let agreed|no longer available", card_text, re.IGNORECASE):
        return None

    # Title — usually in an h2 or h3
    title_el = card.find(["h2", "h3"]) or a
    title = title_el.get_text(" ", strip=True)[:160] if title_el else "SpareRoom NYC"

    price = _parse_price(card_text)

    # Neighborhood often appears as text near "in [neighborhood]"
    hood = None
    hood_match = re.search(r"\bin\s+([A-Z][A-Za-z\- ]{2,30}?)(?:,|\s+\$|\s+pcm|$)", card_text)
    if hood_match:
        hood = hood_match.group(1).strip()

    # Detect furnished / shared signals
    text_low = card_text.lower()
    furnished = None
    if "furnished" in text_low:
        furnished = True
    elif "unfurnished" in text_low:
        furnished = False

    return Listing(
        id=_make_id(url),
        source="spareroom",
        url=url,
        title=title,
        price=price,
        neighborhood=hood,
        furnished=furnished,
        body_snippet=card_text[:300],
    )


def _fetch_page(url: str, page: int = 1) -> list[Listing]:
    params = {"offset": (page - 1) * 30} if page > 1 else {}
    try:
        resp = requests.get(url, params=params, headers=_headers(), timeout=20)
        if resp.status_code != 200:
            logger.warning(f"SpareRoom {url} (page {page}): HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        # SpareRoom listings tend to be in <li class="listing-result"> or similar
        cards = soup.select("li.listing-result, article.listing, li[class*='listing']")
        if not cards:
            # Fallback: look for any container with an /flatshare/ link
            cards = []
            for a in soup.select("a[href*='/flatshare/']"):
                parent = a.find_parent(["li", "article", "div"])
                if parent and parent not in cards:
                    cards.append(parent)

        out: list[Listing] = []
        seen_urls: set[str] = set()
        for card in cards:
            listing = _parse_listing_card(card)
            if listing and listing.url not in seen_urls:
                seen_urls.add(listing.url)
                out.append(listing)
        return out

    except Exception as exc:
        logger.warning(f"SpareRoom {url} (page {page}) failed: {exc}")
        return []


_SEARCH_SESSION: requests.Session | None = None


def _search_session() -> requests.Session:
    """Session for the search endpoint, warmed up so it carries SpareRoom's cookies."""
    global _SEARCH_SESSION
    if _SEARCH_SESSION is None:
        sess = requests.Session()
        sess.headers.update(_headers())
        try:
            sess.get(BASE, timeout=15)      # pick up cookies before searching
        except Exception as exc:
            logger.debug(f"SpareRoom session warm-up failed (continuing): {exc}")
        _SEARCH_SESSION = sess
    return _SEARCH_SESSION


def _fetch_search(query: str) -> list[Listing]:
    """Fetch listings via SpareRoom's search endpoint.

    For neighborhoods with no SEO area page — Bed-Stuy above all — the
    /rooms-for-rent/<area> URL 302s to a location-disambiguation FORM, not to
    results, which is why simply following the redirect yields nothing. The
    search endpoint does reach them, but only for names SpareRoom's US gazetteer
    resolves unambiguously. See the notes on config.SPAREROOM_SEARCH_QUERIES.
    """
    try:
        resp = _search_session().get(
            f"{BASE}/roommate/search.pl",
            params={"search": query, "flatshare_type": "offered", "action": "search"},
            timeout=20,
        )
        if resp.status_code != 200:
            logger.warning(f"SpareRoom search '{query}': HTTP {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        if "several possible matches" in soup.get_text(" ", strip=True):
            logger.warning(
                f"SpareRoom search '{query}' landed on the disambiguation page — 0 listings. "
                "The gazetteer stopped resolving this name; re-check it against "
                "config.SPAREROOM_SEARCH_QUERIES."
            )
            return []

        out: list[Listing] = []
        seen_urls: set[str] = set()
        for card in soup.select("li.listing-result"):
            listing = _parse_listing_card(card)
            if listing and listing.url not in seen_urls:
                seen_urls.add(listing.url)
                out.append(listing)
        logger.info(f"[SpareRoom search] '{query}' → {len(out)} listings")
        return out

    except Exception as exc:
        logger.warning(f"SpareRoom search '{query}' failed: {exc}")
        return []


def fetch() -> list[Listing]:
    """Scrape SpareRoom across the configured area pages, then the search fallbacks.

    We hit one SEO area URL per target neighborhood (config.SPAREROOM_AREAS) so
    off-target areas (e.g. uptown Manhattan) are never returned — instead of
    scraping all of NYC and discarding most of it downstream. Neighborhoods with
    no SEO page are picked up afterwards via config.SPAREROOM_SEARCH_QUERIES.
    """
    all_listings: list[Listing] = []
    for area in config.SPAREROOM_AREAS:
        url = f"{BASE}/rooms-for-rent/{area}"
        for page in range(1, PAGES_PER_AREA + 1):
            page_results = _fetch_page(url, page)
            if not page_results:
                break
            all_listings.extend(page_results)
            time.sleep(random.uniform(2.0, 4.0))   # polite delay between requests

    for query in getattr(config, "SPAREROOM_SEARCH_QUERIES", []):
        all_listings.extend(_fetch_search(query))
        time.sleep(random.uniform(2.0, 4.0))

    # Dedup by URL across areas/pages
    seen: set[str] = set()
    unique = []
    for l in all_listings:
        if l.url not in seen:
            seen.add(l.url)
            unique.append(l)

    n_search = len(getattr(config, "SPAREROOM_SEARCH_QUERIES", []))
    logger.info(
        f"[SpareRoom] {len(unique)} unique listings across "
        f"{len(config.SPAREROOM_AREAS)} area pages + {n_search} search queries"
    )
    return unique


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    results = fetch()
    print(f"\n=== {len(results)} listings ===")
    for r in results[:5]:
        print(f"{r.id} | ${r.price} | {r.title[:60]} | {r.url}")
