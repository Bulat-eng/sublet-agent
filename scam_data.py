"""
Reference tables for scam.py: subway lines per area, landmarks per area.

Keys are config.REGIONS keywords. Both tables are deliberately GENEROUS — a line
counts for an area if a station is a short walk from any part of it — because
the subway check only fires when NONE of the lines a post names serve its area.
A missing area just skips the check; a missing line could cause a false alarm,
so err on the side of adding.

CI checks that every key here is a REGIONS keyword.
"""

_LES = set("BDFJMZ")
_EV = set("456BDFJLMNQRWZ")
_WILLIAMSBURG = set("GJLMZ")

AREA_LINES: dict[str, set[str]] = {
    # ── Midtown ──
    "theater district":  set("1237ACENQRWBDFM"),
    "hudson yards":      set("7ACE123"),
    "garment district":  set("123ACEBDFMNQRW7"),
    "koreatown":         set("BDFMNQRW1236"),
    "herald square":     set("BDFMNQRW123ACE6"),
    "midtown east":      set("4567EMNQRWFS"),
    "midtown south":     set("BDFMNQRW123ACE67"),
    "sutton place":      set("456NRWEMF"),
    "turtle bay":        set("4567EM"),
    "tudor city":        set("4567"),
    "murray hill":       set("4567BDFMNQRW"),
    # ── Midtown → FiDi ──
    "chelsea":           set("123ACEFMLNQRW7"),
    "flatiron":          set("NQRWFM6451L"),
    "gramercy":          set("645LNQRW"),
    "kips bay":          set("6457"),
    "nomad":             set("NQRW6FMBD1"),
    "rose hill":         set("645NRW"),
    "union square":      set("456LNQRWFM"),
    "meatpacking district": set("ACEL123"),
    "stuyvesant town":   set("L456NQRW"),
    "peter cooper village": set("L456NQRW"),
    "east village":      _EV,
    "west village":      set("123ACEBDFMLNRW"),
    "greenwich village": set("ABCDEFM1NQRW6L45"),
    "alphabet city":     set("LFJMZ6"),
    "noho":              set("6BDFMNRW45"),
    "nolita":            set("6JZBDFMNQRW"),
    "little italy":      set("6JZNQRWBDFM"),
    "soho":              set("ACE1NRW6BDFMJZQ"),
    "hudson square":     set("1ACE23"),
    "bowery":            set("JZ6FMBD"),
    "lower east side":   _LES,
    "les":               _LES,
    "cooperative village": set("FJMZBD"),
    "chinatown":         set("6JZNQRWBDF45ACE"),
    "two bridges":       set("FBDJMZ"),
    # ── FiDi & Lower Manhattan ──
    "financial district": set("2345JZRW1ACE"),
    "fidi":              set("2345JZRW1ACE"),
    "battery park":      set("1RW4523ACEJZ"),
    "world trade center": set("ACE123RW45JZ"),
    "civic center":      set("456JZRWACE123"),
    "seaport":           set("2345ACJZ"),
    "tribeca":           set("123ACE6JZNQRW45"),   # Canal St + Chambers
    # ── North Brooklyn ──
    "greenpoint":        set("GL"),
    "williamsburg":      _WILLIAMSBURG,
    "east williamsburg": _WILLIAMSBURG,
    "industrial williamsburg": _WILLIAMSBURG,
    "north williamsburg": _WILLIAMSBURG,
    "northside williamsburg": _WILLIAMSBURG,
    "south williamsburg": _WILLIAMSBURG,
    "southside williamsburg": _WILLIAMSBURG,
    "los sures":         _WILLIAMSBURG,
    # ── Central Brooklyn ──
    "downtown brooklyn": set("2345ACFRNQBDG"),
    "dumbo":             set("FAC23R"),
    "brooklyn heights":  set("2345RNACF"),
    "vinegar hill":      set("FAC"),
    "boerum hill":       set("ACGF2345BDNQR"),
    "cobble hill":       set("FG2345R"),
    "carroll gardens":   set("FGR"),
    "columbia street waterfront district": set("FGR"),
    "columbia waterfront": set("FGR"),
    "fort greene":       set("CGBDNQR2345A"),
    "clinton hill":      set("CGA2345BDNQR"),     # Atlantic Ave–Barclays
    "gowanus":           set("FGRDN2345BQ"),      # Atlantic Ave–Barclays
    "park slope":        set("FGR2345BQDNS"),
    "south slope":       set("RFGDN"),
    "prospect heights":  set("2345BQSAC"),
    # ── South Brooklyn ──
    "greenwood heights": set("RFGDN"),
    "prospect lefferts gardens": set("BQ25S"),
    "prospect-lefferts gardens": set("BQ25S"),
    "flatbush":          set("BQ25S"),
}

_MIDTOWN = [
    "theater district", "hudson yards", "garment district", "koreatown",
    "herald square", "midtown east", "midtown south", "sutton place",
    "turtle bay", "tudor city", "murray hill",
]
_WILLIAMSBURG_AREAS = [
    "williamsburg", "east williamsburg", "industrial williamsburg",
    "north williamsburg", "northside williamsburg", "south williamsburg",
    "southside williamsburg", "los sures",
]

# Landmark → the areas it is plausibly "close to". Only proximity wording
# ("close to", "steps from", "overlooking") counts — "20 minutes to Union Square"
# is a commute, not a location — so commute landmarks are left out entirely.
# An empty set means no in-scope area is near it (Riverside Park, the Met).
LANDMARKS: dict[str, list[str]] = {
    "central park": _MIDTOWN,
    "riverside park": ["theater district", "hudson yards"],
    "lincoln center": ["theater district"],
    "metropolitan museum": [],
    "museum mile": [],
    "columbia university": [],
    "bryant park": _MIDTOWN + ["nomad", "flatiron"],
    "madison square park": ["flatiron", "nomad", "gramercy", "kips bay", "rose hill",
                            "chelsea", "union square", "murray hill", "koreatown"],
    "gramercy park": ["gramercy", "flatiron", "kips bay", "union square", "rose hill",
                      "stuyvesant town", "peter cooper village", "nomad"],
    "washington square": ["greenwich village", "west village", "soho", "noho",
                          "east village", "union square", "nolita"],
    "tompkins square": ["east village", "alphabet city", "lower east side", "les",
                        "stuyvesant town", "peter cooper village"],
    "seward park": ["lower east side", "les", "two bridges", "chinatown",
                    "cooperative village"],
    "high line": ["chelsea", "meatpacking district", "west village", "hudson yards",
                  "hudson square"],
    "hudson river park": ["west village", "chelsea", "tribeca", "meatpacking district",
                          "hudson square", "battery park", "greenwich village",
                          "hudson yards"],
    "mccarren park": ["greenpoint"] + _WILLIAMSBURG_AREAS,
    "domino park": _WILLIAMSBURG_AREAS,
    "fort greene park": ["fort greene", "clinton hill", "downtown brooklyn", "boerum hill",
                         "dumbo", "vinegar hill", "prospect heights"],
    "brooklyn bridge park": ["dumbo", "brooklyn heights", "cobble hill", "vinegar hill",
                             "downtown brooklyn", "columbia waterfront",
                             "columbia street waterfront district", "boerum hill",
                             "carroll gardens"],
    "barclays center": ["downtown brooklyn", "fort greene", "prospect heights", "park slope",
                        "boerum hill", "clinton hill", "gowanus"],
    # Brooklyn posts stretch "close to" further: most of Central Brooklyn counts
    "prospect park": ["park slope", "south slope", "prospect heights", "gowanus",
                      "prospect lefferts gardens", "prospect-lefferts gardens",
                      "flatbush", "greenwood heights", "fort greene",
                      "clinton hill", "boerum hill", "carroll gardens", "downtown brooklyn"],
    "brooklyn museum": ["prospect heights", "park slope",
                        "prospect lefferts gardens", "prospect-lefferts gardens"],
    "botanic garden": ["prospect heights", "park slope",
                       "prospect lefferts gardens", "prospect-lefferts gardens", "flatbush"],
}

# Place names outside REGIONS. Used only to tell where a post claims to be, for
# the template check (a text reused for Staten Island still counts). Bare borough
# names are left out: "Brooklyn" vs "Williamsburg" is the same post, not a swap.
OTHER_AREAS = [
    "staten island", "bushwick", "bed-stuy", "bed stuy", "bedstuy", "bedford-stuyvesant",
    "bedford stuyvesant", "harlem", "east harlem", "upper east side", "upper west side",
    "astoria", "long island city", "sunnyside", "ridgewood", "sunset park",
    "windsor terrace", "ditmas park", "red hook", "bay ridge", "kensington",
    "east flatbush", "little haiti", "crown heights", "washington heights", "inwood", "jersey city",
    "hoboken", "forest hills", "jackson heights", "flushing",
]

# Lines for OTHER_AREAS, for posts whose own wording places them outside REGIONS
# even though a commute mention routed them in ("Bushwick … access to downtown
# Brooklyn"). Areas without a subway line are left out, which skips the check.
OTHER_AREA_LINES: dict[str, set[str]] = {
    "bushwick": set("LJMZ"),
    "bed-stuy": set("ACGJMZ"),
    "harlem": set("123456ABCD"),
    "east harlem": set("456"),
    "upper east side": set("456QFNRW"),
    "upper west side": set("123ABCD"),
    "astoria": set("NWMR"),
    "long island city": set("7EMGNWR"),
    "sunnyside": set("7"),
    "ridgewood": set("ML"),
    "sunset park": set("DNR"),
    "windsor terrace": set("FG"),
    "ditmas park": set("BQ"),
    "red hook": set("FG"),
    "bay ridge": set("R"),
    "kensington": set("FG"),
    "east flatbush": set("2345"),
    "little haiti": set("25BQ"),
    "crown heights": set("2345ACSBQ"),
    "washington heights": set("1AC"),
    "inwood": set("1A"),
    "forest hills": set("EFMR"),
    "jackson heights": set("7EFMR"),
    "flushing": set("7"),
}

# Spellings of one place. SAME_PLACE also shares config.MEDIANS entries; the
# wider AREA_ALIASES (sub-areas → parent) is only for the template check, so a
# lister reposting their own room as "LES" and "Lower East Side", or
# "Williamsburg" and "East Williamsburg", is not taken for a swapped template.
SAME_PLACE = {
    "les": "lower east side",
    "fidi": "financial district",
    "prospect-lefferts gardens": "prospect lefferts gardens",
    "columbia street waterfront district": "columbia waterfront",
}
AREA_ALIASES = {
    **SAME_PLACE,
    "bed stuy": "bed-stuy", "bedstuy": "bed-stuy", "bedford-stuyvesant": "bed-stuy",
    "bedford stuyvesant": "bed-stuy", "crown hts": "crown heights",
    **{a: "williamsburg" for a in _WILLIAMSBURG_AREAS},
}
