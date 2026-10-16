"""
Reddit price-parsing regression tests.

No pytest dependency — run directly:

    .venv/bin/python test_reddit.py

A post the parser reads as "no price" skips the rent cap in filter.py and goes
straight into the digest, so every miss here is an over-budget email.
"""

from filter import filter_listings
from models import Listing
from sources.reddit import _parse_price

# (text, expected_price, why)
CASES = [
    ("Sublet 1Br/1Ba in Fort Greene steps from park (Oct 24 or Nov 1 - Mar 31, $4k/month)",
     4000, "real r/NYCapartments post 1x6k4zw, emailed 2026-10-15 with no price"),
    ("$3.5k/mo 1BR sublet", 3500, "decimal shorthand"),
    ("Room for $1.8K per month", 1800, "capital K"),
    ("$ 2k a month, utilities included", 2000, "space after the dollar sign"),
    ("$1,500/mo room in Clinton Hill", 1500, "plain price with comma"),
    ("Studio sublet $1650 monthly", 1650, "plain price, no comma"),
    ("$4,000 per month", 4000, "plain price that the shorthand branch must not cut short"),
    ("Sublet, $2 kitchen fee waived", None, "'k' starting a word is not shorthand"),
    ("Sublet near the park, DM me", None, "no price at all"),
]


def _check_parse() -> list[str]:
    fails = []
    for text, expected, why in CASES:
        got = _parse_price(text)
        ok = got == expected
        print(f"{'✅' if ok else '❌'} {got!s:>5}  {text[:70]}")
        if not ok:
            fails.append(f"  parse {text!r}: expected {expected}, got {got} — {why}")
    return fails


def _check_budget() -> list[str]:
    """The real post must now be rejected as over budget, not emailed."""
    title = CASES[0][0]
    l = Listing(id="rd_1x6k4zw", source="reddit_NYCapartments", url="", title=title,
                price=_parse_price(title), body_snippet="1-Bedroom sublet in Fort Greene")
    kept = filter_listings([l])
    ok = not kept
    print(f"{'✅' if ok else '❌'} $4k Fort Greene sublet rejected by the rent cap")
    return [] if ok else ["  budget: $4k Fort Greene sublet still passes filter_listings"]


def main() -> int:
    fails = _check_parse()
    print()
    fails += _check_budget()
    total = len(CASES) + 1

    print()
    if fails:
        print(f"❌ {len(fails)}/{total} FAILED\n")
        print("\n".join(fails))
        return 1

    print(f"✅ {total}/{total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
