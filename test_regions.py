"""
Region-routing regression tests.

No pytest dependency — run directly:

    .venv/bin/python test_regions.py

Re-run after ANY change to config.REGIONS. These cases encode decisions that are
easy to break silently, especially region ORDER (see 99_troubleshooting.md).
"""

from filter import _assign_region

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

    # ── ORDER-DEPENDENT: 'Flatbush Ave' is a cross street, not the neighborhood ──
    ("Park Slope 1BR steps from Flatbush Ave", "central_brooklyn",
     "central_brooklyn MUST precede south_brooklyn or this mislabels as South"),
    ("Prospect Heights near Flatbush Ave and Atlantic", "central_brooklyn",
     "same ordering guarantee"),

    # ── South Brooklyn ──
    ("Rent stabilized studio in Flatbush", "south_brooklyn",
     "the real Flatbush still routes South (cf. the 2026-07-14 missed listing)"),
    ("Ditmas Park Victorian, room for rent", "south_brooklyn", ""),
    ("Prospect Park South 2BR", "south_brooklyn",
     "must not be swallowed by 'prospect heights' or 'park slope'"),
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


def main() -> int:
    fails = []
    for text, expected, why in CASES:
        region, hood = _assign_region(text)
        if region != expected:
            fails.append((text, expected, region, why))
            status, detail = "FAIL", f"expected {expected!r}, got {region!r}"
        else:
            status, detail = "ok  ", f"{region!s:<18} {hood or ''}"
        print(f"{status}  {detail:<44} {text[:46]}")

    print()
    if fails:
        print(f"❌ {len(fails)}/{len(CASES)} FAILED\n")
        for text, expected, got, why in fails:
            print(f"  {text!r}\n    expected {expected!r}, got {got!r}"
                  + (f"\n    why it matters: {why}" if why else ""))
        return 1

    print(f"✅ {len(CASES)}/{len(CASES)} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
