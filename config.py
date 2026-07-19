"""
Sublet-agent configuration. Defaults adapted from rental-agent.
Edit the constants below before running. Secrets come from env vars.
"""

import os

# ─── Your preferences ─────────────────────────────────────────────────────────

MAX_RENT = 2000                  # hard filter: reject listings above this monthly price
MIN_RENT = 700                   # quality filter: scam-suspicious below this
MAX_BEDROOMS = 2                 # 0=studio, 1=1BR, 2=2BR

# Sublet-specific
SUBLET_DURATION_MIN_MONTHS = 1
SUBLET_DURATION_MAX_MONTHS = 12
REQUIRE_FURNISHED = False        # flag, not filter (still get unfurnished listings)
EARLIEST_MOVE_IN = "2026-06-15"  # ISO date; flag listings starting before
LATEST_MOVE_IN   = "2026-09-30"  # ISO date; flag listings starting after


# ─── Regions ──────────────────────────────────────────────────────────────────
#
# Regions group listings into labelled sections inside the digest email.
# A listing is assigned to the first region whose neighborhood appears in it.
# (Queens was removed 2026-07-11 — no longer part of the search.)

REGIONS = {
    "manhattan": {
        "label": "Manhattan",
        "emoji": "🟦",
        "neighborhoods": [
            "soho", "tribeca", "financial district", "fidi", "battery park",
            "lower east side", "les", "east village", "west village",
            "greenwich village", "nolita", "noho", "chinatown", "two bridges",
            "seaport", "chelsea", "flatiron", "gramercy", "kips bay",
        ],
    },
    "north_brooklyn": {
        "label": "North Brooklyn",
        "emoji": "🟩",
        "neighborhoods": ["williamsburg", "greenpoint", "bushwick"],
    },
    "south_brooklyn": {
        "label": "South Brooklyn",
        "emoji": "🟪",
        "neighborhoods": [
            "downtown brooklyn", "dumbo", "boerum hill",
            "cobble hill", "carroll gardens", "park slope", "gowanus",
        ],
    },
    # Added 2026-07-14 after a $1,750 rent-stabilized Flatbush studio was missed
    # (out of scope). Kept deliberately small — Flatbush + its immediate neighbors,
    # not all of central Brooklyn. Widen here if more central-BK deals slip past.
    "central_brooklyn": {
        "label": "Central Brooklyn",
        "emoji": "🟨",
        "neighborhoods": [
            "flatbush", "ditmas park",
            "prospect lefferts gardens", "prospect-lefferts gardens",
        ],
    },
    "new_jersey": {
        "label": "New Jersey",
        "emoji": "🟫",
        "neighborhoods": ["jersey city", "hoboken", "journal square", "newport"],
    },
}

# Derived: flat list of all neighborhood keywords (used by filter + scrapers)
NEIGHBORHOOD_KEYWORDS = [
    hood for region in REGIONS.values() for hood in region["neighborhoods"]
]


# ─── Craigslist search groups (sublets/rooms categories only) ─────────────────

CL_SEARCH_GROUPS = {
    "nyc": [
        "soho tribeca chelsea lower east side",
        "east village west village greenwich village",
        "williamsburg greenpoint",
        "bushwick",
        "downtown brooklyn carroll gardens",
        "park slope cobble hill",
    ],
    "nj": [
        "jersey city hoboken",
    ],
}

# ─── SpareRoom search areas ───────────────────────────────────────────────────
#
# SpareRoom scrapes by SEO area URL: spareroom.com/rooms-for-rent/<path>. We hit
# one page per target neighborhood so off-target areas (e.g. uptown Manhattan
# like Hamilton Heights) are never returned — much better signal than the broad
# /nyc page, where low-volume downtown targets get buried under high-volume
# uptown listings. Paths verified live 2026-06-05.
# No dedicated SpareRoom page: Seaport, Journal Square, Newport (the latter two
# are covered by jersey_city). Add/remove paths to widen or narrow coverage.

SPAREROOM_AREAS = [
    # Manhattan (below ~23rd St)
    "manhattan/soho", "manhattan/tribeca", "manhattan/financial_district",
    "manhattan/battery_park_city", "manhattan/lower_east_side",
    "manhattan/east_village", "manhattan/west_village",
    "manhattan/greenwich_village", "manhattan/nolita", "manhattan/noho",
    "manhattan/chinatown", "manhattan/two_bridges", "manhattan/chelsea",
    "manhattan/flatiron_district", "manhattan/gramercy_park", "manhattan/kips_bay",
    # North Brooklyn
    "brooklyn/williamsburg", "brooklyn/greenpoint", "brooklyn/bushwick",
    # South Brooklyn
    "brooklyn/downtown_brooklyn", "brooklyn/dumbo", "brooklyn/boerum_hill",
    "brooklyn/cobble_hill", "brooklyn/carroll_gardens", "brooklyn/park_slope",
    "brooklyn/gowanus",
    # New Jersey
    "nj/hudson_county/jersey_city", "nj/hudson_county/hoboken",
]


# ─── Neighborhood median rents (for % comparison enrichment) ──────────────────

MEDIANS = {
    "williamsburg":      {"studio": 3000, "1br": 3500, "2br": 4800},
    "greenpoint":        {"studio": 2800, "1br": 3200, "2br": 4200},
    "bushwick":          {"studio": 2200, "1br": 2800, "2br": 3500},
    "park slope":        {"studio": 2600, "1br": 3200, "2br": 4400},
    "carroll gardens":   {"studio": 2700, "1br": 3300, "2br": 4500},
    "cobble hill":       {"studio": 2700, "1br": 3400, "2br": 4600},
    "downtown brooklyn": {"studio": 2800, "1br": 3400, "2br": 4600},
    "east village":      {"studio": 2800, "1br": 3400, "2br": 4800},
    "west village":      {"studio": 3200, "1br": 4200, "2br": 6000},
    "soho":              {"studio": 3500, "1br": 4500, "2br": 6500},
    "tribeca":           {"studio": 3800, "1br": 5000, "2br": 7000},
    "chelsea":           {"studio": 3000, "1br": 3800, "2br": 5200},
    "lower east side":   {"studio": 2700, "1br": 3200, "2br": 4500},
    "jersey city":       {"studio": 2200, "1br": 2800, "2br": 3600},
    "hoboken":           {"studio": 2400, "1br": 3000, "2br": 4000},
}

# ─── Ohana (liveohana.ai) ─────────────────────────────────────────────────────
#
# liveohana.ai is a Bubble.io app whose public Data API (/api/1.1/obj/listing)
# returns structured listings — no headless browser needed. It's a national
# platform, so we constrain server-side to Live listings in the NYC-area cities
# below and sort newest-first; the shared neighborhood filter narrows the rest.
# "New York" is Bubble's city label for Manhattan; the boroughs are separate.

OHANA_CITIES = ["New York", "Brooklyn", "Queens", "Manhattan", "Bronx"]
OHANA_FETCH_LIMIT = 100      # newest N Live NYC-area listings per run

# ─── Reddit subreddits ────────────────────────────────────────────────────────

REDDIT_SUBREDDITS = [
    "SublettingNYC",
    "NYCapartments",
    "AskNYC",            # filter heavily for sublet keywords
]

REDDIT_SUBLET_KEYWORDS = [
    "sublet", "sublease", "sub-let", "subletting",
    "lease takeover", "lease transfer", "lease break", "lease assignment",
    "room available", "room for rent",
]

# Demand-side "seeker" detection (Reddit-specific): FLAG (not drop) posts where
# the author is looking FOR a place rather than offering one — e.g. "I'm looking
# for a furnished apartment" or a bare title like "Looking for Manhattan Sublet".
# Matched in sources/reddit.py as "[I'm] looking for [a] <up to 2 words> <noun>";
# the optional "I'm" lets title-style posts match, and the 2-word cap still keeps
# offers like "looking for someone to take over my lease" out. Add nouns to extend.
REDDIT_SEEKER_NOUNS = ["apartment", "room", "sublet", "lease"]

# Direct-rental rescue (per-source): a post with no sublet keyword is normally
# dropped. On the housing subs we instead KEEP it if it names a price — many great
# listings are straight rentals, not sublets (e.g. "$1750 Rent Stabilized Studio
# Flatbush"). Rescued posts are flagged "direct rental, not a sublet" and still
# notified — never silently dropped. r/AskNYC is too noisy (mostly questions) for
# this, so it stays strict: sublet keyword required or the post is dropped.
REDDIT_KEYWORD_STRICT_SUBS = ["AskNYC"]

# ─── Sources to enable ────────────────────────────────────────────────────────

# Phase 1 — no Playwright required. Ohana joined here (2026-07-19): its public
# Bubble Data API means it needs plain HTTP, not the headless browser Phase 2
# originally assumed.
ENABLED_SOURCES = ["craigslist", "listings_project", "spareroom", "reddit", "ohana"]

# Phase 2 — flip on once Playwright is wired in CI
# ENABLED_SOURCES += ["leasebreak"]

# Facebook: opt-in via ENABLE_FACEBOOK=true env var, local-only

# ─── Per-source minimum cadence (informational; GH Actions runs every 15min) ──

SOURCE_CADENCE_MINUTES = {
    "craigslist": 15,
    "listings_project": 360,    # weekly inventory — 6h is plenty
    "spareroom": 30,
    "reddit": 15,
    "ohana": 20,
    "leasebreak": 30,
    "facebook": 60,
}

# ─── Secrets (env vars only — never hardcode) ─────────────────────────────────

# Email delivery via Gmail SMTP. Create a Gmail App Password (NOT your normal
# login password) at myaccount.google.com/apppasswords and set both vars below.
SENDER_EMAIL       = os.environ.get("SENDER_EMAIL", "")       # the Gmail that sends
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "") # 16-char app password
TARGET_EMAIL       = os.environ.get("TARGET_EMAIL", "REDACTED@example.com")  # inbox that receives

# Reddit uses public RSS feeds — no credentials needed.

ENABLE_FACEBOOK   = os.environ.get("ENABLE_FACEBOOK", "false").lower() == "true"
FB_COOKIES_PATH   = os.environ.get("FB_COOKIES_PATH", "./fb_cookies.json")
