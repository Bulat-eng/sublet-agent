"""
Scam scoring: the second layer behind filter._is_scam(). See SCAM_FILTER.md.

filter._is_scam() hard-drops the classic tells ("wire money", "god bless", rent
under MIN_RENT). The October 2026 Craigslist bait wave had none of them: polite,
specific-sounding posts priced just under budget. This module scores what gets
past it. Each signal adds points; filter.py stores the total and the reasons on
the listing and drops it at config.SCAM_DROP_SCORE (by default the flag score,
so anything flagged is never emailed). Below that, the digest marks it
(config.SCAM_FLAG_SCORE) or moves it to a "Likely scams" section
(config.SCAM_LIKELY_SCORE).

Craigslist only (applies_to): the other sources are moderated or structured,
and the October wave was all Craigslist.

Entry points:
  template_families(listings)    once per run, over every Craigslist post scraped
  assess(listing, hood, families) per listing → [(points, reason), ...]

check_listing.py runs the same two functions on a single post.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date

import config
from models import Listing
from scam_data import (AREA_ALIASES, AREA_LINES, LANDMARKS, OTHER_AREA_LINES, OTHER_AREAS,
                       SAME_PLACE)

Reason = tuple[int, str]


def _words(names) -> re.Pattern:
    """Whole-word matcher for a list of place names, longest first."""
    alternation = "|".join(re.escape(n) for n in sorted(set(names), key=len, reverse=True))
    return re.compile(rf"\b(?:{alternation})\b", re.IGNORECASE)


_MANHATTAN_REGIONS = ("midtown", "midtown_to_fidi", "fidi")
_HOOD_REGION = {h: k for k, r in config.REGIONS.items() for h in r["neighborhoods"]}
_MANHATTAN_RE = _words(h for h, k in _HOOD_REGION.items() if k in _MANHATTAN_REGIONS)
_BROOKLYN_RE = _words(h for h, k in _HOOD_REGION.items() if k not in _MANHATTAN_REGIONS)
_ANY_AREA_RE = _words(list(_HOOD_REGION) + config.EXCLUDED_AREAS + OTHER_AREAS)


def _text(l: Listing) -> str:
    return " ".join(filter(None, [l.title, l.neighborhood, l.body or l.body_snippet]))


def _area_label(hood: str) -> str:
    return "LES" if hood == "les" else hood.title()


# A mention right after these words is a commute, not the location: "25 minutes
# to reach the LES", "direct access to downtown Brooklyn".
_COMMUTE_BEFORE = re.compile(
    r"(?:\bmin(?:ute)?s?\b|\bhours?\b|\bride\b|\bcommute\b|\breach\b|\bget to\b|\baccess to\b"
    r"|\bexpress\b|\bstops? (?:to|from)\b|\btrip\b|\bdirect(?:ly)?\b)[^.;!?\n]*$", re.IGNORECASE)


def located_area(l: Listing) -> str | None:
    """Where the post says the place is: the first area named in the title or
    location, else the first one in the body that isn't a commute. filter.py's
    region routing takes the first REGIONS match anywhere, Manhattan first, so a
    Park Slope room "25 minutes to the LES" is routed to LES; the price, subway
    and landmark checks must not judge it as an LES listing."""
    for text, skip_commutes in ((f"{l.title} {l.neighborhood or ''}", False),
                                (l.body or l.body_snippet or "", True)):
        for m in _ANY_AREA_RE.finditer(text):
            if skip_commutes and _COMMUTE_BEFORE.search(text[max(0, m.start() - 40):m.start()]):
                continue
            name = m.group(0).lower()
            return SAME_PLACE.get(name, name)
    return None


# ─── What is being rented: a room, or a whole studio / 1BR / 2BR ──────────────

# "<word> room" that is part of an apartment, not the thing being rented
_NOT_A_ROOM = {
    "living", "dining", "laundry", "bath", "mud", "family", "sitting", "storage", "show",
    "elbow", "rest", "class", "utility", "media", "bonus", "common", "locker", "bike",
    "boiler", "mail", "package", "party", "fitness", "workout", "game", "play", "sun",
    "guest", "powder", "great", "breakfast", "tv", "lounge", "screening", "theater",
    "dressing", "wiggle", "leg", "head", "trash", "music", "community", "conference",
    "meeting", "recreation", "rec", "spa", "steam", "kids", "yoga", "work", "computer",
    "billiards", "golf", "waiting", "changing", "stock", "control", "board",
    # "windows in every room", "both rooms have closets"
    "every", "each", "all", "both", "other", "many", "several", "multiple",
}
_ROOM_WORD = re.compile(r"(?:([a-z]+)[\s-]+)?\b(?:rooms?|roommates?)\b", re.IGNORECASE)
_BEDROOM_IN_SHARE = re.compile(
    r"\b(?:bed)?room (?:available )?in (?:a |an |my |our |the )?"
    r"(?:\d|two|three|four|five|six)[\s-]?(?:bed|br|bd|bdrm|bedroom)", re.IGNORECASE)
_ADJ_BEDROOM = re.compile(
    r"\b(?:private|sunny|furnished|spacious|large|big|cozy|bright|beautiful|nice|huge|"
    r"master|quiet|lovely|clean|shared)\s+bedroom\b(?!\s+(?:apartment|apt|unit|condo|flat))",
    re.IGNORECASE)

# A room in someone's place, whatever else the text says
_SHARED_PLACE = re.compile(
    r"\bshared (?:bath(?:room)?s?|kitchen|apartment|apt|house|home|flat|living(?: room)?)\b"
    r"|\b(?:furnished|private|converted|spacious|nice|large|cozy) living room\b"
    r"|\bliving room (?:for rent|available)\b", re.IGNORECASE)

_STUDIO = re.compile(r"(?<!art )(?<!artist )(?<!yoga )(?<!recording )(?<!music )"
                     r"\bstudio\b(?!\s+(?:space|session))", re.IGNORECASE)
_ONE_BR = re.compile(r"\b(?:1|one)[\s-]?(?:br|bd|bdr|bdrm|bed|bedroom)s?\b|\bjr\.?\s*(?:1|one)\b|"
                     r"\bjunior (?:1|one)\b", re.IGNORECASE)
_TWO_BR = re.compile(r"\b(?:2|two)[\s-]?(?:br|bd|bdr|bdrm|bed|bedroom)s?\b", re.IGNORECASE)


def _is_room_wording(text: str) -> bool:
    for m in _ROOM_WORD.finditer(text):
        if (m.group(1) or "").lower() not in _NOT_A_ROOM:
            return True
    return bool(_BEDROOM_IN_SHARE.search(text) or _ADJ_BEDROOM.search(text)
                or _SHARED_PLACE.search(text))


def _whole_unit_wording(text: str) -> str | None:
    hits = [(m.start(), kind) for rx, kind in ((_STUDIO, "studio"), (_ONE_BR, "1br"), (_TWO_BR, "2br"))
            if (m := rx.search(text))]
    return min(hits)[1] if hits else None


def unit_kind(l: Listing) -> str | None:
    """'room', 'studio', '1br', '2br' or None. Room wording up front wins."""
    body = l.body or l.body_snippet or ""
    head = f"{l.title} {body[:200]}"
    if _is_room_wording(head) or re.search(r"\bshare\b", l.title, re.IGNORECASE):
        return "room"       # "2BR SHARE", "Apartment share"
    kind = _whole_unit_wording(l.title) or _whole_unit_wording(head)
    if kind:
        return kind
    if l.category == "rooms":
        return "room"       # CL rooms & shares: the "0BR" housing line means nothing
    if l.bedrooms is not None:
        return {0: "studio", 1: "1br"}.get(l.bedrooms, f"{l.bedrooms}br")
    return _whole_unit_wording(body)


# ─── Short stays are priced per stay, not per month ───────────────────────────

_SHORT_WORDS = re.compile(
    r"\b(?:\d{1,2}|a few|few|couple(?: of)?|one|two|three)\s+nights?\b"
    r"|\b(?:a few|few|couple(?: of)?|one|two|three|[1-3])\s+weeks?\b"
    r"|\bper (?:night|week)\b|\bnightly\b|\$[\d,]+\s*(?:/|per|a)?\s*(?:night|nt|week|wk)\b"
    r"|\bweek[- ]long\b|\bweek sublet\b|\b(?:thanksgiving|christmas|holiday|nye) week\b",
    re.IGNORECASE)

_MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
_MON = (r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?"
        r"|sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b\.?")
_DAYNAME = r"(?:(?:mon|tues|wednes|thurs|fri|satur|sun)day,?\s*)?"
_DATE_RANGE = re.compile(
    rf"\b(?:(?P<m1>{_MON})\s+(?P<d1>\d{{1,2}})|(?P<n1>\d{{1,2}})/(?P<e1>\d{{1,2}}))(?:st|nd|rd|th)?"
    rf"[,\s]*(?:-|–|—|to|through|thru|until|till)\s*{_DAYNAME}"
    rf"(?:(?P<m2>{_MON})\s+(?P<d2>\d{{1,2}})|(?P<n2>\d{{1,2}})[/-](?P<e2>\d{{1,2}})|(?P<d3>\d{{1,2}}))\b",
    re.IGNORECASE)


def _range_days(m: re.Match) -> int | None:
    try:
        if m["m1"]:
            m1, d1 = _MONTHS.index(m["m1"][:3].lower()) + 1, int(m["d1"])
        else:
            m1, d1 = int(m["n1"]), int(m["e1"])
        if m["m2"]:
            m2, d2 = _MONTHS.index(m["m2"][:3].lower()) + 1, int(m["d2"])
        elif m["n2"]:
            m2, d2 = int(m["n2"]), int(m["e2"])
        else:
            m2, d2 = m1, int(m["d3"])
        start, end = date(2026, m1, d1), date(2026, m2, d2)
    except ValueError:
        return None
    if end < start:
        end = end.replace(year=2027)
    return (end - start).days


def is_short_stay(l: Listing) -> bool:
    period = (l.attrs or {}).get("rent_period", ["", ""])[1]
    if period in ("daily", "weekly"):
        return True
    text = f"{l.title} {l.body or l.body_snippet}"
    if _SHORT_WORDS.search(text):
        return True
    return any(0 < (_range_days(m) or 0) < 28 for m in _DATE_RANGE.finditer(text))


# ─── Price vs. area median ────────────────────────────────────────────────────

def _median(hood: str, kind: str) -> tuple[int, str] | None:
    """(median, label). Areas without their own fall back to the cheapest on file
    in their region, then overall — so a missing median only makes a post look
    LESS suspicious."""
    own = config.MEDIANS.get(SAME_PLACE.get(hood, hood), {}).get(kind)
    if own:
        return own, _area_label(hood)
    region = _HOOD_REGION.get(hood)
    in_region = [config.MEDIANS[h][kind] for h in config.REGIONS.get(region, {}).get("neighborhoods", [])
                 if kind in config.MEDIANS.get(h, {})]
    if in_region:
        return min(in_region), f"cheapest {config.REGIONS[region]['label']}"
    overall = [m[kind] for m in config.MEDIANS.values() if kind in m]
    return (min(overall), "cheapest NYC") if overall else None


def _price_signal(l: Listing, kind: str | None, hood: str | None) -> Reason | None:
    if kind not in ("studio", "1br") or not l.price or not hood or is_short_stay(l):
        return None
    med = _median(hood, kind)
    if not med:
        return None
    median, where = med
    ratio = l.price / median
    points = 3 if ratio <= 0.50 else 2 if ratio <= 0.65 else 0
    if points <= 0:
        return None
    label = "studio" if kind == "studio" else "1BR"
    return points, f"whole {label} at ${l.price:,} is {ratio:.0%} of the {where} {label} median (${median:,})"


# ─── Subway lines that don't run there ────────────────────────────────────────

_LINE = r"(?:[1-7]|[ABCDEFGJLMNQRWZ])(?![\w'’])"
_SEP = r"\s*(?:,|/|&|\+|\band\b|\bor\b)\s*"
_GROUP = rf"(?<![\w/$#.,]){_LINE}(?:{_SEP}{_LINE})*"
_NOT_A_LINE_AFTER = (r"(?!\s*(?i:bed|br\b|bd\b|bath|room|block|min|person|people|stor|level|floor|"
                     r"month|year|week|day|night|unit|apartment|apt|car\b|other|same|one|best|first|last))")
_LINE_PATTERNS = [
    # "1,2,3 trains", "L and G trains", "G train", "2 & 5 trains"
    re.compile(rf"({_GROUP})\s*(?i:trains?|lines?|subways?|stops?|stations?|express|local)\b"),
    # "72nd St (1/2/3 and B/C)"
    re.compile(rf"\(\s*({_LINE}(?:{_SEP}{_LINE})+)\s*\)"),
    # "A/C/E", "N/Q/R/W" — three or more, so "A/C" (air conditioning) and "W/D" don't count
    re.compile(r"(?<![\w/])([1-7A-Z](?:/[1-7A-Z]){2,})(?![\w/])"),
    # "near the L", "take the 1"
    re.compile(rf"(?i:\b(?:on|off|near|by|via|take|to|from)\s+the)\s+({_GROUP}){_NOT_A_LINE_AFTER}"),
]


def lines_named(text: str) -> set[str]:
    named: set[str] = set()
    for i, rx in enumerate(_LINE_PATTERNS):
        for m in rx.finditer(text):
            group = m.group(1)
            if m.end(1) >= len(text.rstrip()) - 1:
                continue    # cut off mid-sentence ("2 blocks from the 7" was "7th Ave")
            # "2 stops away", "3 subway lines nearby" are counts, not lines
            if i == 0 and group.isdigit() and re.match(r"\s*(?i:stops?|stations?|lines?|subways?)",
                                                       text[m.end(1):]):
                continue
            named.update(re.findall(r"[1-7A-Z]", group))
    return named


def _names_both_sides(text: str) -> bool:
    return bool(_MANHATTAN_RE.search(text) and _BROOKLYN_RE.search(text))


def _subway_signal(text: str, hood: str | None) -> Reason | None:
    served = AREA_LINES.get(hood or "") or OTHER_AREA_LINES.get(AREA_ALIASES.get(hood or "", hood or ""))
    if not served:
        return None
    named = lines_named(text)
    foreign = named - served
    # Most of the lines it names don't stop there: "LES … next to 1,2,3 trains",
    # "East Village … 72nd St (1/2/3 and B/C)". One local line among them doesn't save it.
    if len(foreign) <= len(named & served) or _names_both_sides(text):
        return None
    return 3, f"says {'/'.join(sorted(foreign))} trains — they don't stop in {_area_label(hood)}"


# ─── Landmarks from another part of the city ──────────────────────────────────

_PROXIMITY = (r"(?:close to|near(?:by)?|next to|steps (?:away )?(?:from|to)|"
              r"walk(?:ing)?(?: distance)? (?:to|from)|blocks? (?:from|to|away from)|"
              r"across (?:the street )?from|overlooking|views? of|around the corner from|"
              r"min(?:ute)?s?(?:'|’)? walk (?:to|from)|adjacent to)")
_COMMUTE = re.compile(r"train|subway|ride|bus\b|commute|\bmin", re.IGNORECASE)
_LANDMARK_RES = {
    lm: re.compile(rf"\b{_PROXIMITY}\b([^.;!?\n]{{0,60}}?)\b(?:the )?{re.escape(lm)}", re.IGNORECASE)
    for lm in LANDMARKS
}


def _landmark_signal(text: str, hood: str | None) -> Reason | None:
    if hood not in _HOOD_REGION:
        return None     # no landmark data outside REGIONS
    wrong = []
    for lm, areas in LANDMARKS.items():
        if hood in areas:
            continue
        near = any(not _COMMUTE.search(m.group(1)) for m in _LANDMARK_RES[lm].finditer(text))
        # stand down when the post also names an area the landmark IS near
        if near and not (areas and _words(areas).search(text)):
            wrong.append(lm.title())
    if not wrong:
        return None
    return 2, f"describes {', '.join(wrong)} — not near {_area_label(hood)}"


# ─── Text signals ─────────────────────────────────────────────────────────────

_KEYS_BY_MAIL = re.compile(
    r"\bkeys?\b[^.]{0,40}\b(?:mail(?:ed)?|ship(?:ped)?|courier(?:ed)?|fedex(?:ed)?|ups|dhl|"
    r"deliver(?:ed)?|post(?:ed)?)\b|\b(?:mail|ship|courier|fedex|send|deliver)(?:ed)?\s+(?:you\s+)?"
    r"the\s+keys?\b", re.IGNORECASE)
_ASSISTANT_JOB = re.compile(
    r"\b(?:personal|part[- ]time|paid|errands?|virtual|executive|house(?:hold)?|home)\s+assistant\b"
    r"|\bassistant\s+(?:job|position|role|work|duties)\b", re.IGNORECASE)
_ASKS_CONTACT = re.compile(
    r"\b(?:send|give|leave|include|provide|share|text|drop|tell)\s+(?:us|me)?\s*(?:with\s+)?"
    r"(?:your|ur)\s+(?:phone|cell|mobile|number|e-?mail|contact)"
    r"|\b(?:only|must|please)\b[^.]{0,30}\b(?:messages?|e-?mails?|replies|responses?|inquiries)\s+"
    r"(?:with|including|that include)\b[^.]{0,20}\b(?:e-?mail|phone|number)"
    r"|\b(?:respond|reply|message|write)\s+(?:to\s+(?:me|us)\s+|back\s+)?with\s+(?:your|ur)\s+"
    r"(?:phone|cell|number|e-?mail)"
    r"|\b(?:e-?mail|message|text)\s+(?:me|us)\s+(?:your|ur)\s+(?:phone|cell|number)"
    r"|\bwhat(?:'s| is) your (?:phone|cell|number|e-?mail)", re.IGNORECASE)
_PAYMENT_APPS = re.compile(
    r"\b(?:zelle|venmo|cash ?app|bitcoin|btc|crypto(?:currency)?|usdt|gift ?cards?)\b", re.IGNORECASE)
_WALK_UP = re.compile(r"walk[- ]?up|\bno elevator\b|flights? of stairs|\bstairs only\b", re.IGNORECASE)
_LAUNDROMAT = re.compile(
    r"laundromats?|coin[- ]op|laundry (?:room )?(?:is )?(?:in|on) (?:the )?(?:building|basement|premises|site)",
    re.IGNORECASE)
_VACATION_COPY = re.compile(
    r"\bsleeps\b|\bstocked with\b|\bcheck[- ]?(?:in|out) (?:time|is at|by)\b|\bself[- ]check[- ]?in\b"
    r"|\bour guests\b|\bsuperhost\b|\bfresh (?:linens|towels)\b", re.IGNORECASE)


def _attr_label(l: Listing, key: str) -> str:
    return ((l.attrs or {}).get(key) or ["", ""])[1]


def _tag_signals(l: Listing, text: str, region: str | None) -> list[Reason]:
    out: list[Reason] = []
    if not l.attrs:
        return out
    if "wheelchaccess" in l.attrs and _WALK_UP.search(text):
        out.append((2, "tagged wheelchair accessible, but the text says walk-up"))
    if region != "south_brooklyn":
        parking = _attr_label(l, "parking")
        box = [parking] if "garage" in parking or "carport" in parking else []
        if "ev_charging" in l.attrs:
            box.append("EV charging")
        if box:
            out.append((min(len(box), 2), f"tagged {' + '.join(box)} — rare outside South Brooklyn"))
    if _attr_label(l, "laundry") == "w/d in unit" and _LAUNDROMAT.search(text):
        out.append((1, "tagged in-unit laundry, but the text mentions a laundromat"))
    return out


# ─── Same text posted for other neighborhoods ─────────────────────────────────

_STRIP_FOR_TEMPLATE = _words(list(_HOOD_REGION) + config.EXCLUDED_AREAS + OTHER_AREAS
                             + ["manhattan", "brooklyn", "queens", "bronx", "new york", "nyc"])
_TEMPLATE_WORDS = 200        # compare the opening of each post (cached pre-0.10.0 bodies are short)
_MIN_SHINGLES = 20
_CONTAINMENT = 0.7           # share of the shorter post's 5-word runs found in the other
_COMMON_SHINGLE = 50         # boilerplate in this many posts is ignored


def _shingles(text: str) -> set[str]:
    words = [w for w in re.findall(r"[a-z']+", _STRIP_FOR_TEMPLATE.sub(" ", text.lower())) if len(w) > 1]
    words = words[:_TEMPLATE_WORDS]
    return {" ".join(words[i:i + 5]) for i in range(len(words) - 4)}


def claimed_area(l: Listing) -> str | None:
    """located_area(), with sub-areas folded into their parent for comparison."""
    area = located_area(l)
    return AREA_ALIASES.get(area, area) if area else None


def template_families(listings: list[Listing]) -> dict[str, str]:
    """{listing id: reason} for posts whose text also appears under ANOTHER area.

    Run over the whole scraped batch (before area filtering), so a copy posted
    for Staten Island still counts against the LES original.
    """
    docs = [(l, sh, claimed_area(l)) for l in listings
            if len(sh := _shingles(l.body or l.body_snippet or "")) >= _MIN_SHINGLES]
    index: dict[str, list[int]] = defaultdict(list)
    for i, (_, sh, _) in enumerate(docs):
        for s in sh:
            index[s].append(i)

    parent = list(range(len(docs)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, (_, sh, _) in enumerate(docs):
        shared = Counter(j for s in sh if len(index[s]) <= _COMMON_SHINGLE for j in index[s] if j > i)
        for j, n in shared.items():
            if n / min(len(sh), len(docs[j][1])) >= _CONTAINMENT:
                parent[find(i)] = find(j)

    families: dict[int, list[int]] = defaultdict(list)
    for i in range(len(docs)):
        families[find(i)].append(i)

    out: dict[str, str] = {}
    for members in families.values():
        if len({docs[i][2] for i in members if docs[i][2]}) < 2:
            continue
        # Areas one post names together are one place: a border room reposted as
        # "Bushwick" and as "Bed-Stuy" names both in its text; a swapped template
        # names only the area it was swapped to.
        same: dict[str, str] = {}

        def root(a: str) -> str:
            while same.setdefault(a, a) != a:
                a = same[a]
            return a

        for i in members:
            named = [AREA_ALIASES.get(n, n) for n in
                     (m.group(0).lower() for m in _ANY_AREA_RE.finditer(_text(docs[i][0])))]
            for n in named[1:]:
                same[root(n)] = root(named[0])
        places = {root(docs[i][2]) for i in members if docs[i][2]}
        if len(places) < 2:
            continue
        for i in members:
            own = root(docs[i][2]) if docs[i][2] else None
            others = sorted({docs[j][2] for j in members if docs[j][2] and root(docs[j][2]) != own})
            shown = ", ".join(_area_label(a) for a in others[:4]) + (" …" if len(others) > 4 else "")
            out[docs[i][0].id] = f"same text also posted for {shown}"
    return out


# ─── Public API ───────────────────────────────────────────────────────────────

def applies_to(l: Listing) -> bool:
    """Scam scoring is for Craigslist posts only (user decision, 2026-10-15)."""
    return l.source.startswith("craigslist")


def assess(l: Listing, hood: str | None, families: dict[str, str] | None = None) -> list[Reason]:
    """Score one listing. `hood` is the neighborhood filter._assign_region matched."""
    text = _text(l)
    # What the post describes, not what it routed to. None when every area it
    # names is a commute ("25 minutes to the LES"): location checks are skipped.
    area = located_area(l)
    region = _HOOD_REGION.get(area or "") or _HOOD_REGION.get(hood or "")
    kind = unit_kind(l)
    reasons: list[Reason] = []

    def add(r: Reason | None):
        if r:
            reasons.append(r)

    add(_price_signal(l, kind, area))
    if families and l.id in families:
        add((3, families[l.id]))
    add(_subway_signal(text, area))
    if _KEYS_BY_MAIL.search(text):
        add((3, "offers to mail or courier the keys"))
    if _ASSISTANT_JOB.search(text):
        add((3, "room bundled with a paid assistant job"))
    if _ASKS_CONTACT.search(text):
        add((2, "asks for your phone or email up front"))
    add(_landmark_signal(text, area))
    if m := _PAYMENT_APPS.search(text):
        add((2, f"payment via {m.group(0)}"))
    reasons.extend(_tag_signals(l, text, region))
    if m := _VACATION_COPY.search(text):
        add((1, f"vacation-rental copy (\"{m.group(0)}\")"))
    if kind == "room" and l.price and l.price < 900 and region and region != "south_brooklyn":
        where = f" in {config.REGIONS[region]['label']}" if area else ""
        add((1, f"room at ${l.price:,}{where}, unusually cheap"))
    return reasons


def level(score: int) -> str:
    """'likely', 'verify' or 'clean' for a total score."""
    if score >= config.SCAM_LIKELY_SCORE:
        return "likely"
    if score >= config.SCAM_FLAG_SCORE:
        return "verify"
    return "clean"
