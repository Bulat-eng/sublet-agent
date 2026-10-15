"""
Filter sublet listings against user criteria.

Four layers:
  - HARD filters → reject (over budget, wrong area — incl. areas blocked by name)
  - SOFT filters → flag via tags but keep (duration/move-in unknown)
  - SCAM filters → reject (suspiciously cheap, suspicious text patterns)
  - SCAM score   → mark but keep (scam.py, Craigslist only; dropped only past config.SCAM_DROP_SCORE)
"""

from __future__ import annotations

import re
import logging
from datetime import date

import config
import scam
from models import Listing

logger = logging.getLogger(__name__)


SCAM_PATTERNS = [
    r"wire (?:money|transfer|funds)",
    r"western union",
    r"moneygram",
    r"send (?:me )?(?:the )?(?:money|payment|deposit) (?:via|through|by)",
    r"god ?bless",                      # very common scam tell
    r"out of (?:the )?country",
    r"out of state and",
    r"missionary",
    r"god[' ]?s? will",
]
_SCAM_RE = re.compile("|".join(SCAM_PATTERNS), re.IGNORECASE)


def _hood_regex(hoods: list[str]) -> re.Pattern:
    """Whole-word/phrase matcher for a list of neighborhoods.

    Word boundaries stop short abbreviations from matching inside unrelated
    words — e.g. "les" (Lower East Side) must NOT match "stainless"/"wireless",
    and "lic" (Long Island City) must NOT match "police".
    """
    if not hoods:
        # An empty alternation, \b(?:)\b, matches EVERY string — fatal for an
        # emptied EXCLUDED_AREAS, which would then block every listing.
        return re.compile(r"(?!)")
    alternation = "|".join(re.escape(h) for h in hoods)
    return re.compile(rf"\b(?:{alternation})\b", re.IGNORECASE)


# Precompiled matchers (built once at import) — per-region for routing, combined for membership
_REGION_RES = {key: _hood_regex(r["neighborhoods"]) for key, r in config.REGIONS.items()}
_NEIGHBORHOOD_RE = _hood_regex(config.NEIGHBORHOOD_KEYWORDS)
_EXCLUDED_RE = _hood_regex(config.EXCLUDED_AREAS)
_CHEAPER_AREAS = frozenset(config.CHEAPER_AREAS)


def _matches_neighborhood(text: str) -> str | None:
    """Return the first matching neighborhood keyword (whole-word), or None."""
    m = _NEIGHBORHOOD_RE.search(text)
    return m.group(0).lower() if m else None


def _assign_region(text: str) -> tuple[str | None, str | None]:
    """Return (region_key, matched_neighborhood) for the first region whose neighborhood appears in text (whole-word match).

    Text naming any config.EXCLUDED_AREAS keyword returns (None, None) even if it
    also names a target neighborhood — checked first, so the block always wins.
    """
    if _EXCLUDED_RE.search(text):
        return None, None
    for region_key, rx in _REGION_RES.items():
        m = rx.search(text)
        if m:
            return region_key, m.group(0).lower()
    return None, None


def _rent_cap(hood: str) -> int:
    """Monthly rent cap for a matched neighborhood keyword (lowercase, as _assign_region returns it)."""
    return config.CHEAPER_AREA_MAX_RENT if hood in _CHEAPER_AREAS else config.MAX_RENT


def _is_scam(listing: Listing) -> bool:
    """Heuristic scam detection."""
    text = (listing.title + " " + listing.body_snippet)

    # Pattern match
    if _SCAM_RE.search(text):
        return True

    # Suspiciously cheap (well below MIN_RENT)
    if listing.price is not None and listing.price > 0 and listing.price < config.MIN_RENT:
        return True

    # Empty / near-empty listing
    if len((listing.title + listing.body_snippet).strip()) < 30:
        return True

    return False


def _check_move_in(listing: Listing) -> str | None:
    """Return a tag if move-in date is outside the target window. None if fine or unknown."""
    if not listing.move_in_date:
        return None
    try:
        d = date.fromisoformat(listing.move_in_date)
    except (ValueError, TypeError):
        return None

    earliest = config.EARLIEST_MOVE_IN and date.fromisoformat(config.EARLIEST_MOVE_IN)
    latest   = config.LATEST_MOVE_IN and date.fromisoformat(config.LATEST_MOVE_IN)

    if earliest and d < earliest:
        return f"early-move-in:{listing.move_in_date}"
    if latest and d > latest:
        return f"late-move-in:{listing.move_in_date}"
    return None


def filter_listings(listings: list[Listing]) -> list[Listing]:
    """Apply all filters. Returns the listings that pass, with soft-filter tags added."""
    kept: list[Listing] = []
    rejected = {"over_budget": 0, "wrong_area": 0, "scam": 0, "scam_score": 0}
    marked = {"verify": 0, "likely": 0}

    # Scam scoring is Craigslist-only (the other sources are moderated or
    # structured). Templates are matched over ALL Craigslist posts, before area
    # filtering: a copy reused for an out-of-scope area still gives away the
    # in-scope ones.
    families = scam.template_families([l for l in listings if scam.applies_to(l)])

    for l in listings:
        # HARD: not in target neighborhoods + assign region for routing
        full_text = " ".join(filter(None, [l.title, l.body_snippet, l.neighborhood or ""]))
        region_key, hood = _assign_region(full_text)
        if hood is None:
            rejected["wrong_area"] += 1
            continue

        # HARD: over budget — after the area match, because the cap depends on it
        if l.price is not None and l.price > _rent_cap(hood):
            rejected["over_budget"] += 1
            continue

        if not l.neighborhood:
            l.neighborhood = hood.title()
        l.region = region_key

        # SCAM
        if _is_scam(l):
            rejected["scam"] += 1
            continue

        # SCAM score (Craigslist only) — marked in the digest; dropped only if SCAM_DROP_SCORE is set
        reasons = scam.assess(l, hood, families) if scam.applies_to(l) else []
        l.scam_score = sum(points for points, _ in reasons)
        l.scam_reasons = [why for _, why in reasons]
        if config.SCAM_DROP_SCORE is not None and l.scam_score >= config.SCAM_DROP_SCORE:
            rejected["scam_score"] += 1
            logger.info(f"  ↳ dropped, scam score {l.scam_score}: {l.title[:60]} — "
                        f"{'; '.join(l.scam_reasons)}")
            continue
        lvl = scam.level(l.scam_score)
        if lvl in marked:
            marked[lvl] += 1

        # SOFT tags
        if l.duration_months is not None:
            if l.duration_months < config.SUBLET_DURATION_MIN_MONTHS:
                l.tags.append(f"short-{l.duration_months}mo")
            elif l.duration_months > config.SUBLET_DURATION_MAX_MONTHS:
                l.tags.append(f"long-{l.duration_months}mo")

        move_in_tag = _check_move_in(l)
        if move_in_tag:
            l.tags.append(move_in_tag)

        if config.REQUIRE_FURNISHED and l.furnished is False:
            l.tags.append("unfurnished")

        kept.append(l)

    logger.info(
        f"Filter: kept {len(kept)} / {len(listings)} "
        f"(rejected: {rejected['over_budget']} over budget, "
        f"{rejected['wrong_area']} wrong area, {rejected['scam']} scam"
        + (f", {rejected['scam_score']} over scam score" if rejected["scam_score"] else "")
        + f"; marked: {marked['verify']} verify, {marked['likely']} likely scam)"
    )
    return kept
