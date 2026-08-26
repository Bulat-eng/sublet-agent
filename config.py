"""
Sublet-agent configuration. Defaults adapted from rental-agent.
Edit the constants below before running. Secrets come from env vars.
"""

import os

# ─── Your preferences ─────────────────────────────────────────────────────────

MAX_RENT = 1800                  # hard filter: reject listings above this monthly price
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
# A listing is assigned to the first region (in this dict's order) whose
# neighborhood appears in it — so ORDER MATTERS when keywords can co-occur.
# Two deliberate ordering choices:
#   * central_brooklyn before south_brooklyn, so a Park Slope / Prospect
#     Heights listing that merely names "Flatbush Ave" as a cross street
#     routes to Central, not South.
#   * Manhattan before Brooklyn (see the chinatown note below).
#
# Sub-area keywords ("east williamsburg", "bed-stuy") rarely change WHETHER a
# listing is kept — the parent name usually matches anyway — but they do change
# the LABEL shown in the email, since the regex returns the earliest match.
# "los sures" is the exception: it contains no "Williamsburg" at all.
#
# History: Queens removed 2026-07-11. New Jersey removed 2026-07-24.
# Rebuilt 2026-08-21: Manhattan split into three bands (midtown / midtown_to_fidi
# / fidi), Brooklyn re-cut, Bushwick and Red Hook dropped, ~36 areas added.

REGIONS = {
    # ── Manhattan: ~34th to 59th ──
    "midtown": {
        "label": "Midtown",
        "emoji": "🟧",
        "neighborhoods": [
            "theater district", "hudson yards", "garment district",
            "koreatown", "herald square", "midtown east", "midtown south",
            "sutton place", "turtle bay", "tudor city",
            # NOTE: also matches Murray Hill, QUEENS (Flushing) — out of scope
            # since 2026-07-11, but whole-word matching can't tell them apart.
            "murray hill",
        ],
    },
    # ── Manhattan: everything between Midtown and FiDi (~Canal to 34th) ──
    "midtown_to_fidi": {
        "label": "Midtown → FiDi",
        "emoji": "🟦",
        "neighborhoods": [
            "chelsea", "flatiron", "gramercy", "kips bay", "nomad",
            "rose hill", "union square", "meatpacking district",
            "stuyvesant town", "peter cooper village",
            "east village", "west village", "greenwich village",
            "alphabet city", "noho", "nolita", "little italy", "soho",
            "hudson square", "bowery",
            "lower east side", "les", "cooperative village",
            # NOTE: "chinatown" also matches Sunset Park listings marketed as
            # "Brooklyn Chinatown". Sunset Park was dropped 2026-08-26, but this
            # keyword still lets those through the hard filter, labelled
            # Manhattan. See HANDOFF open items.
            "chinatown", "two bridges",
        ],
    },
    # ── Manhattan: the southern tip ──
    "fidi": {
        "label": "FiDi & Lower Manhattan",
        "emoji": "🟥",
        "neighborhoods": [
            "financial district", "fidi", "battery park",
            "world trade center", "civic center", "seaport",
            # Tribeca sits just above Chambers St; grouped here to match the
            # usual "Lower Manhattan" real-estate framing rather than by strict
            # geography. Move to midtown_to_fidi if the email reads wrong.
            "tribeca",
        ],
    },
    # ── Brooklyn ──
    "north_brooklyn": {
        "label": "North Brooklyn",
        "emoji": "🟩",
        "neighborhoods": [
            "greenpoint", "williamsburg",
            # Sub-areas: mostly for a better email label, since "williamsburg"
            # already matches them. Heads-up: "east williamsburg" is how a lot
            # of Bushwick-border inventory markets itself, so it partly reopens
            # the area Bushwick's removal (2026-08-21) was meant to close.
            "east williamsburg", "industrial williamsburg",
            "north williamsburg", "northside williamsburg",
            "south williamsburg", "southside williamsburg",
            "los sures",
        ],
    },
    "central_brooklyn": {
        "label": "Central Brooklyn",
        "emoji": "🟨",
        "neighborhoods": [
            "downtown brooklyn", "dumbo", "brooklyn heights", "vinegar hill",
            "boerum hill", "cobble hill", "carroll gardens",
            "columbia street waterfront district", "columbia waterfront",
            "fort greene", "clinton hill", "gowanus",
            "park slope", "south slope", "prospect heights",
            "bedford-stuyvesant", "bedford stuyvesant",
            "bed-stuy", "bed stuy", "bedstuy",
        ],
    },
    "south_brooklyn": {
        "label": "South Brooklyn",
        "emoji": "🟪",
        "neighborhoods": [
            "windsor terrace", "greenwood heights",
            "prospect lefferts gardens", "prospect-lefferts gardens",
            "crown heights", "prospect park south", "ditmas park",
            # Kept from the 2026-07-14 addition: a $1,750 rent-stabilized
            # Flatbush studio was missed as out-of-scope. Also matches
            # "Flatbush Ave" — see the ordering note at the top of this block.
            "flatbush",
        ],
    },
}

# Derived: flat list of all neighborhood keywords (used by filter + scrapers)
NEIGHBORHOOD_KEYWORDS = [
    hood for region in REGIONS.values() for hood in region["neighborhoods"]
]


# ─── Craigslist search groups (sublets/rooms categories only) ─────────────────

CL_SEARCH_GROUPS = {
    "nyc": [
        # Manhattan
        "soho tribeca chelsea lower east side",
        "east village west village greenwich village",
        "financial district battery park city",
        "midtown east murray hill koreatown",
        # North Brooklyn ("bushwick" group dropped 2026-08-21)
        "williamsburg greenpoint",
        # Central Brooklyn
        "downtown brooklyn carroll gardens",
        "park slope cobble hill",
        "brooklyn heights fort greene clinton hill",
        "prospect heights crown heights bed stuy",
        # South Brooklyn
        "flatbush ditmas park prospect lefferts gardens",
        # "sunset park" dropped 2026-08-26 (user request)
        "windsor terrace greenwood heights",
    ],
}

# ─── SpareRoom search areas ───────────────────────────────────────────────────
#
# SpareRoom scrapes by SEO area URL: spareroom.com/rooms-for-rent/<path>. We hit
# one page per target neighborhood so off-target areas are never returned — much
# better signal than the broad /nyc page, where low-volume targets get buried.
#
# Every path below was re-verified live 2026-08-21 (HTTP 200). A path that does
# NOT exist returns 302 → /roommate/search.pl, so 200 is the check that matters.
#
# Deliberately NOT listed, even though the page exists — low listing volume
# and/or priced far above MAX_RENT, and each entry is an HTTP request every run:
#   manhattan/sutton_place, manhattan/tudor_city, manhattan/civic_center,
#   manhattan/meatpacking_district, manhattan/stuyvesant_town, manhattan/bowery,
#   brooklyn/vinegar_hill
#
# No SEO page exists at all (302), so these rely on Craigslist / Reddit / Ohana /
# Listings Project instead: Bed-Stuy (every spelling tried), South Slope,
# Turtle Bay, Midtown South, NoMad, Rose Hill, Hudson Square, World Trade Center,
# Herald Square, Peter Cooper Village, Cooperative Village, Seaport.
# Bed-Stuy is the notable loss given its volume — recovering it means following
# SpareRoom's redirect to the search endpoint, a scraper change, not a config one.

SPAREROOM_AREAS = [
    # Midtown
    "manhattan/midtown_east", "manhattan/murray_hill", "manhattan/koreatown",
    "manhattan/garment_district", "manhattan/theater_district",
    "manhattan/hudson_yards",
    # Midtown → FiDi
    "manhattan/chelsea", "manhattan/flatiron_district", "manhattan/gramercy_park",
    "manhattan/kips_bay", "manhattan/union_square", "manhattan/east_village",
    "manhattan/west_village", "manhattan/greenwich_village",
    "manhattan/alphabet_city", "manhattan/noho", "manhattan/nolita",
    "manhattan/little_italy", "manhattan/soho", "manhattan/lower_east_side",
    "manhattan/chinatown", "manhattan/two_bridges",
    # FiDi & Lower Manhattan
    "manhattan/financial_district", "manhattan/battery_park_city",
    "manhattan/tribeca",
    # North Brooklyn ("brooklyn/bushwick" dropped 2026-08-21)
    "brooklyn/williamsburg", "brooklyn/greenpoint",
    # Central Brooklyn
    "brooklyn/downtown_brooklyn", "brooklyn/dumbo", "brooklyn/brooklyn_heights",
    "brooklyn/boerum_hill", "brooklyn/cobble_hill", "brooklyn/carroll_gardens",
    "brooklyn/fort_greene", "brooklyn/clinton_hill", "brooklyn/gowanus",
    "brooklyn/park_slope", "brooklyn/prospect_heights",
    # South Brooklyn
    # "brooklyn/sunset_park" dropped 2026-08-26 (user request)
    "brooklyn/crown_heights", "brooklyn/windsor_terrace",
    "brooklyn/greenwood_heights",
]


# ─── SpareRoom search-endpoint fallbacks ──────────────────────────────────────
#
# Neighborhoods with NO SEO area page. /rooms-for-rent/<area> 302-redirects to a
# location-disambiguation FORM (not to results), so following the redirect gets
# you nothing — the search endpoint has to be queried by name instead.
#
# The name must be one SpareRoom's US gazetteer resolves unambiguously, and the
# exact spelling matters: "Bedford Stuyvesant" resolves (326 results), while
# "Bed Stuy", "Bed-Stuy", "Bedford-Stuyvesant, Brooklyn" and "Bedford
# Stuyvesant, Brooklyn" all land on the disambiguation page. Verified 2026-08-21.
#
# DO NOT add a bare place name without checking where it actually resolves —
# "Seaport" returns listings in Redwood City, CALIFORNIA. Anything that resolves
# off-target is wasted requests (the neighborhood filter drops the results).
#
# Confirmed to have no usable search name, so they stay uncovered by SpareRoom:
# South Slope, Turtle Bay, Midtown South, NoMad, Rose Hill, Hudson Square,
# World Trade Center, Herald Square, Peter Cooper Village, Cooperative Village.
#
# This search also returns some neighbors (Bushwick, Crown Heights, Ocean Hill);
# the shared neighborhood filter sorts them out, dropping Bushwick/Ocean Hill and
# routing Crown Heights to its own region.

SPAREROOM_SEARCH_QUERIES = [
    "Bedford Stuyvesant",
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
}

# ─── Ohana (liveohana.ai) ─────────────────────────────────────────────────────
#
# liveohana.ai is a Bubble.io app whose public Data API (/api/1.1/obj/listing)
# returns structured listings — no headless browser needed. It's a national
# platform with ~1,500 live NYC listings but only ~340 under budget, so we
# constrain server-side to Live listings that are (a) in the NYC-area cities
# below and (b) at or under MAX_RENT, then paginate through all of them. This
# stops us wasting the fetch on expensive Manhattan listings and, more
# importantly, from missing affordable Brooklyn listings buried deep in the feed.
# The shared neighborhood filter still narrows the rest.
#
# "New York" is Bubble's city label for Manhattan; the boroughs are separate.
# ("Manhattan" and "Bronx" as city labels return nothing — Manhattan listings
# carry the "New York" label — so they're intentionally omitted. Queens was
# dropped 2026-08-21 to match the REGIONS removal of 2026-07-11: its listings
# were fetched only to be discarded by the neighborhood filter.)

OHANA_CITIES = ["New York", "Brooklyn"]
OHANA_PAGE_SIZE = 100        # Bubble Data API max page size
OHANA_MAX_LISTINGS = 600     # safety cap on total pulled per run (well above the ~340 under budget)

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
TARGET_EMAIL       = os.environ.get("TARGET_EMAIL", "")  # inbox that receives

# Reddit uses public RSS feeds — no credentials needed.

ENABLE_FACEBOOK   = os.environ.get("ENABLE_FACEBOOK", "false").lower() == "true"
FB_COOKIES_PATH   = os.environ.get("FB_COOKIES_PATH", "./fb_cookies.json")
