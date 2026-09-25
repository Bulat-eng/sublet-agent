"""
Region-routing and per-area rent-cap regression tests.

No pytest dependency — run directly:

    .venv/bin/python test_regions.py

Re-run after ANY change to config.REGIONS or config.CHEAPER_AREAS. These cases
encode decisions that are easy to break silently, especially region ORDER (see
99_troubleshooting.md).
"""

from filter import _assign_region, filter_listings
from models import Listing

# (text, expected_region_key_or_None, why)
CASES = [
    # ── North Brooklyn: Williamsburg sub-areas ──
    ("Sunny room in East Williamsburg near the L", "north_brooklyn",
     "sub-area keyword should win over bare 'williamsburg' for a better label"),
    ("Los Sures sublet, 2 months", "north_brooklyn",
     "'los sures' contains no 'Williamsburg' — only match is the alias itself"),
    ("Northside Williamsburg loft", "north_brooklyn", ""),

    # ── Removed areas must NOT match ──
    ("Bushwick 1BR near Jefferson St", None, "Bushwick removed 2026-08-21"),
    ("Red Hook waterfront studio", None, "Red Hook never added"),
    ("Sunset Park 1BR near the D train", None, "Sunset Park removed 2026-08-26"),
    ("Sunny room, 5th Ave Sunset Park, Brooklyn", None, "same — removed 2026-08-26"),
    ("Ditmas Park Victorian, room for rent", None, "Ditmas Park removed 2026-09-25"),
    ("Prospect Park South 2BR", None,
     "removed 2026-09-25 — and must not be swallowed by 'prospect heights'/'park slope'"),
    ("Windsor Terrace 1BR near the F", None, "Windsor Terrace removed 2026-09-25"),

    # ── ORDER-DEPENDENT: 'Flatbush Ave' is a cross street, not the neighborhood ──
    ("Park Slope 1BR steps from Flatbush Ave", "central_brooklyn",
     "central_brooklyn MUST precede south_brooklyn or this mislabels as South"),
    ("Prospect Heights near Flatbush Ave and Atlantic", "central_brooklyn",
     "same ordering guarantee"),

    # ── South Brooklyn ──
    ("Rent stabilized studio in Flatbush", "south_brooklyn",
     "the real Flatbush still routes South (cf. the 2026-07-14 missed listing)"),
    ("Room in Flatbush - Ditmas Park, near the Q", "south_brooklyn",
     "KNOWN LEAK, by choice: Ditmas Park sits inside Flatbush (see config note)"),
    ("Crown Heights sublet", "south_brooklyn", ""),

    # ── Central Brooklyn ──
    ("Bed-Stuy brownstone room", "central_brooklyn", ""),
    ("BedStuy room available", "central_brooklyn", "no-space alias"),
    ("#1183 Rooms in 2Br/1Ba in Bedford Stuyvesant", "central_brooklyn",
     "SpareRoom titles use the unhyphenated form — added 2026-08-21"),
    ("Bedford-Stuyvesant share", "central_brooklyn",
     "scraper normalises SpareRoom's spaced 'Bedford - Stuyvesant' to this"),
    ("Brooklyn Heights promenade studio", "central_brooklyn", ""),
    ("South Slope 1BR", "central_brooklyn",
     "'park slope' does NOT match 'South Slope' — needs its own keyword"),

    # ── Manhattan bands ──
    ("Murray Hill room, midtown east adjacent", "midtown", ""),
    ("Koreatown share", "midtown", ""),
    ("Tribeca loft sublet", "fidi", "grouped with Lower Manhattan by choice"),
    ("FiDi studio, doorman", "fidi", ""),
    ("Alphabet City walkup", "midtown_to_fidi", ""),
    ("NoMad furnished room", "midtown_to_fidi", ""),
    ("Sublet on the Bowery", "midtown_to_fidi", ""),

    # ── Out of scope ──
    ("Astoria Queens 1BR", None, "Queens removed 2026-07-11"),
    ("Hell's Kitchen studio", None, "deliberately excluded 2026-08-21"),
    ("Upper East Side 1BR", None, ""),
    ("Jersey City waterfront", None, "NJ removed 2026-07-24"),

    # ── Whole-word guards (see _hood_regex) ──
    ("Stainless steel appliances, wireless internet included", None,
     "'les' must not match inside stainless/wireless"),
    ("Police station nearby, spotless unit", None, "'lic' must not match police"),
]

# (text, price, expected_kept, why) — run through the full filter_listings()
# pipeline, so these also guard that the budget check runs AFTER the area match.
# Caps as of 2026-09-25: $1,650 in config.CHEAPER_AREAS, $1,800 everywhere else.
CAP_CASES = [
    # ── Cheaper areas: $1,650 ──
    ("Bed-Stuy brownstone room, sunny and quiet", 1650, True, "exactly at the lower cap"),
    ("Bed-Stuy brownstone room, sunny and quiet", 1651, False, "$1 over the lower cap"),
    ("Bedford Stuyvesant room, 2 blocks to the A", 1700, False,
     "every Bed-Stuy spelling must carry the lower cap"),
    ("Crown Heights sublet near the 2/3 train", 1700, False, ""),
    ("Greenwood Heights room by the park", 1700, False, ""),
    ("Room in Flatbush - Ditmas Park, near the Q", 1700, False,
     "the Ditmas Park leak lands on Flatbush, so it still gets the lower cap"),

    # ── Everywhere else: $1,800 ──
    ("Williamsburg room near the Bedford L", 1800, True, "exactly at the higher cap"),
    ("Williamsburg room near the Bedford L", 1801, False, "$1 over the higher cap"),
    ("Clinton Hill room with big windows", 1750, True,
     "Central BK, but not a cheaper area — Bed-Stuy is the only one there"),
    ("Park Slope 1BR steps from Flatbush Ave", 1750, True,
     "ORDER: routes Central, so naming Flatbush Ave must not drag it to $1,650"),
    ("East Village studio, 3 month sublet", 1800, True, ""),

    # ── Unknown price is never rejected on budget ──
    ("Crown Heights room, price on request", None, True, ""),
]


def _check_regions() -> list[str]:
    fails = []
    for text, expected, why in CASES:
        region, hood = _assign_region(text)
        if region != expected:
            fails.append(f"  {text!r}\n    expected {expected!r}, got {region!r}"
                         + (f"\n    why it matters: {why}" if why else ""))
            status, detail = "FAIL", f"expected {expected!r}, got {region!r}"
        else:
            status, detail = "ok  ", f"{region!s:<18} {hood or ''}"
        print(f"{status}  {detail:<44} {text[:46]}")
    return fails


def _check_caps() -> list[str]:
    fails = []
    for i, (text, price, expected, why) in enumerate(CAP_CASES):
        listing = Listing(id=f"t{i}", source="test", url="https://example.com", title=text,
                          price=price)
        kept = bool(filter_listings([listing]))
        verdict = "kept" if kept else "rejected"
        if kept != expected:
            fails.append(f"  {text!r} at ${price}\n    expected "
                         f"{'kept' if expected else 'rejected'}, got {verdict}"
                         + (f"\n    why it matters: {why}" if why else ""))
            status = "FAIL"
        else:
            status = "ok  "
        price_str = f"${price:,}" if price is not None else "no price"
        print(f"{status}  {verdict:<9} {price_str:<9} {text[:58]}")
    return fails


def main() -> int:
    fails = _check_regions()
    print()
    fails += _check_caps()
    total = len(CASES) + len(CAP_CASES)

    print()
    if fails:
        print(f"❌ {len(fails)}/{total} FAILED\n")
        print("\n".join(fails))
        return 1

    print(f"✅ {total}/{total} passed ({len(CASES)} routing, {len(CAP_CASES)} rent cap)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
