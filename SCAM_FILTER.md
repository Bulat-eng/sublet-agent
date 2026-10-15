# Scam filter — what it catches, and how each signal was found

Added in **v0.10.0** (2026-10-15). Code: `scam.py` (tables in `scam_data.py`). Tests:
`test_scam.py`. One listing by hand: `check_listing.py`. Knobs: the `SCAM_*_SCORE` lines at the
top of `config.py`.

**Craigslist posts only.** Listings Project, SpareRoom, Reddit and Ohana posts are never scored.

## Why a second layer

`filter._is_scam()` rejects the classic tells: "wire money", "Western Union", "god bless",
"out of the country", rent under `MIN_RENT` ($700), near-empty posts. The October 2026
Craigslist bait wave had **none** of them. The posts were polite, specific-sounding and priced
$1,150–$1,800 — under budget, so straight into the digest.

Over 20 of them were flagged by hand during a week of applications. Every flagged post that got a
reply answered with a scam script. Those 7 are the ground truth this filter is built on.

## The evidence: 7 confirmed scams

| Listing (addresses withheld) | Price | What gave it away in the ad | What the poster replied |
|---|---|---|---|
| LES furnished studio | $1,300 | 52% under the LES studio median; "next to 1,2,3 trains" (they don't run there); garage + EV-charging tags | Ignored the viewing request; asked for an email address and a move-in date |
| East Village "luxury condo" 1BR | $1,650 | Copy lifted from a real condo listed at ~$5,750 | Same script, nearly word for word |
| Williamsburg 1BR with garden | $1,450 | Vacation-rental copy ("sleeps another 2", stocked kitchen) reposted as a monthly | Answered at 2 AM within 3 minutes, pointing to a Gmail address; that address quoted $2,650 up front to "secure the apartment" plus an application form, no viewing |
| Downtown Brooklyn studio sublet | $1,500 | A real luxury building where studios list at ~$4,000; garage + wheelchair tags | "Only video tour is available as im currently away on a business trip" |
| LES 1BR | $1,700 | One of ~10 identical posts with different addresses (LES, Greenwich Village, Brooklyn, Staten Island) | "What's your phone number for more information?" |
| South Slope room | $755 | Title says luxury high-rise, text says a basic 3BR; garage + EV-charging tags | Form letter: "flexible with income and credit", $500 deposit, asked for pay stubs or bank statements and a credit score |
| East Village corner 1BR + roof deck | $1,800 | Every premium amenity at half the median; EV-charging tag | Said the flat was available and asked for an email address and a move-in date — the LES studio's script |

The pattern across the replies: **none answered the question asked** (the address and a viewing
time). They moved the conversation somewhere else, toward money or personal details.

## How each listing was caught

Each check below is something done by hand during the review, turned into a rule. Points add
up; the reasons are printed in the digest next to the listing.

| Signal | Points | Why it works | October example |
|---|---|---|---|
| Whole studio/1BR at ≤ 50% of the area median | 3 | The bait is "too good to be true" by design — a real tenant can't afford to rent out a $3,400 apartment for $1,650 | SoHo 1BR at $1,500 (median $4,500) |
| … at ≤ 65% of the median | 2 | Same, weaker | East Village 1BR at $1,800 |
| Same description posted for other neighborhoods | 3 | Scammers reuse one template and swap the address; a real lister reposting their own room keeps the same area | The $1,700 text in ~10 places, incl. Staten Island |
| Subway lines that don't run there | 3 | Copy written for another area, or by someone who's never been | "LES … next to 1,2,3 trains"; an "East Village" studio near "72nd St (1/2/3 and B/C)"; G train in Greenwich Village |
| Offers to mail or courier the keys | 3 | The landlord-abroad script | — (classic; none this month) |
| Room bundled with a paid "assistant" job | 3 | A known lure for fake-check and overpayment schemes | Brooklyn Heights room, $950 "negotiable" |
| Asks for your phone or email up front | 2 | Harvesting contacts to move you off Craigslist's relay | "Give us your phone number and we'll call back"; "ONLY MESSAGES WITH EMAIL AND PHONE NUMBER" |
| Tagged wheelchair accessible, text says walk-up | 2 | Every checkbox ticked so the post shows up in every filtered search | SoHo "walk-up suite"; a 4th-floor walk-up |
| Describes landmarks from another part of the city | 2 | Pasted from a listing elsewhere | "East Village" studio "close to Central Park, Riverside Park" |
| Money via Zelle / Venmo / Cash App / crypto / gift cards | 2 | Instant and irreversible; a real sublet can wait for a check or the landlord's portal | A sublet offering "direct payment via Venmo/Zelle" (a caution, not proof — only 2 points) |
| Garage / carport / EV-charging tags (each, max 2) | 1 | No Manhattan or brownstone-Brooklyn apartment has them; South Brooklyn is exempt | 4 of the 7 confirmed scams |
| Tagged in-unit laundry, text says laundromat | 1 | Same box-ticking, contradicted by the copy | "w/d in unit" + "multiple laundromats nearby" |
| Vacation-rental copy | 1 | Airbnb text reposted as a lease | "sleeps another 2", "stocked with milk, coffee…" |
| A room under $900 in Manhattan / North / Central Brooklyn | 1 | Unusually cheap, worth a second look | South Slope room at $755 |

**Thresholds** (`config.py`): **3+** marks the listing "⚠️ verify (scam score N): reasons" in
its region; **5+** moves it to a **🚩 Likely scams** section at the bottom of the digest;
`SCAM_DROP_SCORE` (default `None`) would stop emailing it entirely. Nothing is dropped by
default, so a false positive can never hide a real listing.

**Guards against false alarms**
- The price check only compares **whole apartments**. A room is never measured against a 1BR
  median. Room wording in the title or opening lines wins, and on Craigslist the "0BR / 1Ba"
  housing line is ignored for posts in rooms & shares, where posters leave it at 0.
- **Short stays** ("Nov 20–29", "5 nights", "a few weeks") are priced per stay, not per month,
  so the price check skips them.
- Areas with no median of their own fall back to the **cheapest** median on file in their region.
  An area without its own median can only look less suspicious.
- The price, subway and landmark checks judge a post by **where it says it is**: the first area
  in its title or location, else the first one in the text that isn't a commute. Routing takes
  the first match anywhere, so a Park Slope room "25 minutes to the LES" is routed to LES; it is
  not judged as an LES listing.
- The subway check fires only when **most** of the lines a post names don't stop in its area
  (the line tables are generous: a nearby hub like Atlantic Ave–Barclays counts). It stands
  down when a post names neighborhoods on both sides of the river: a Greenpoint room "30
  minutes to Union Square" is routed to Manhattan by `REGIONS` order, but it is not lying
  about the G train.
- For the template check, areas **one post names together** count as one place. A border room
  reposted as "Bushwick" and as "Bed-Stuy" names both in its text; a swapped template names only
  the area it was swapped to.

## Results

- `test_scam.py`: **7/7 confirmed and 10/10 judged scams flagged; 14/14 real legit posts clean**,
  plus 23 guard checks. The legit set includes a room in a rent-stabilized building, five
  short-stay sublets, a nightly rental paid by Zelle/Venmo, a lister's warning about a copycat
  of their own ad, and the Greenpoint "30 minutes to Union Square" room. All are real
  Craigslist posts, with contact details and street addresses redacted.
- **Dry run over the agent's own Craigslist cache** (403 posts, Oct 7–14; 300-character bodies,
  tags not yet cached): 136 in scope and under budget. 12 flagged, 5 of them "likely".
- **The same cache with the posts that are still up re-fetched** (full text and tags, Oct 15;
  216 of the 403 were already gone): 142 in scope, 22 flagged, 10 "likely".
- The top of both lists includes two template families: the LES $1,300 text re-posted for
  Cobble Hill ($1,700), with the neighborhood and train lines swapped in, and an East Village
  studio text re-posted as a Murray Hill one-bedroom.

## What the code can't see

- **A cheap room with generic copy.** The Williamsburg room by Domino Park ($1,150 with a
  private bath, the priciest block) scores 0. Rooms have no median to compare against.
- **Copied marketing text** from a real building. Catching it takes a web search for a distinctive
  sentence or the address. That's how the "luxury condo" and the new-development 1BR were confirmed.
- **Photo-caption copy** (descriptions generated from the photos) and **stale dates** ("available
  mid to end September", posted in October).
- **Tag signals only exist for posts fetched by v0.10.0+.** Older cached details refresh within
  the 40-pages-per-run budget, within about 11 runs of deploying.
- **4 of the 7 confirmed scams sit exactly at the threshold**, carried by Craigslist tags. If the
  tag parser stops matching, they drop below it. The scraper logs a warning when a batch of
  fresh pages yields no tags. The parser keys on each tag link's search parameter
  (`?laundry=1`, `?parking=2`), checked against a live page on 2026-10-14.

## Checking one listing by hand

```
.venv/bin/python check_listing.py https://newyork.craigslist.org/...   # fetches the post
.venv/bin/python check_listing.py listing.md                           # saved or pasted text
pbpaste | .venv/bin/python check_listing.py -                          # clipboard
```

It runs the same rules and prints the score, each reason, and which checks it couldn't run.
Pasted text has no Craigslist tags; the "same text elsewhere" check compares against the
agent's cache in `state.db`. In Claude Code, drop a listing in as a `.md` file and ask for it to
be checked.

## Before you pay anyone: the reply check

The agent never sees replies, but most of the confirmations above came from them. Stop when a
reply:

1. **Doesn't answer what you asked.** You asked for the address and a viewing; they ask for
   your email, phone or move-in date.
2. **Arrives in minutes at odd hours**, or matches another "landlord's" reply word for word.
3. **Moves you off the platform:** a Gmail address, text, WhatsApp.
4. **Asks for money or documents before a viewing:** "to secure the unit", an application form,
   pay stubs, bank statements, credit score, ID.
5. **Can't show the place:** away on business, abroad, "video tour only", keys by mail.
6. **Is "flexible with income and credit"** but wants your financial documents. That's a
   phishing form, not screening.

Manual checks worth the five minutes: search the address or a distinctive sentence (real
listings at 2–3× the price give it away); reverse-image search the photos; look the building
up on whoownswhat.justfix.org or HPD (does it exist, how many units, who owns it).

## Tuning

- **Too many false alarms in a region:** add that area's real medians to `config.MEDIANS`. Only
  12 of the 72 area keywords have one; the rest borrow the cheapest in their region (or overall).
- **A legit post names a line "that doesn't stop there":** widen that area's set in
  `scam_data.AREA_LINES`. The sets are meant to be generous.
- **A scam got through:** add it to `test_scam.py` first (CONFIRMED or JUDGED), then adjust a
  weight or regex in `scam.py` until it's flagged and every LEGIT case stays clean.
- **Ready to stop seeing the worst ones:** set `SCAM_DROP_SCORE` (e.g. 8). Drops are logged with
  their reasons in the Actions run log.
