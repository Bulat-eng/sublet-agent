# Changelog

All notable changes to the sublet-agent are documented here. Versions follow [semver](https://semver.org/).

## [0.7.2] — 2026-08-26

### Removed
- **Sunset Park**, at the user's request. Dropped from three places in
  `config.py`: the `south_brooklyn` `REGIONS` keyword list (the hard area
  filter), the `"sunset park windsor terrace greenwood heights"` Craigslist
  search group (now `"windsor terrace greenwood heights"`), and the
  `brooklyn/sunset_park` SpareRoom area path. 66 → 65 neighborhoods, 42 → 41
  SpareRoom paths.
- Two regression tests added to `test_regions.py` asserting Sunset Park text now
  routes to `None` (32/32 passing), matching the existing Bushwick/Red Hook
  cases.

### Notes
- **Known leak:** `"chinatown"` remains a `midtown_to_fidi` keyword for Manhattan
  Chinatown, so a Sunset Park listing marketed as "Brooklyn Chinatown" still
  clears the area filter. Tracked as HANDOFF open item #12.
- `MEDIANS` never covered Sunset Park, so nothing to remove there.

## [0.7.1] — 2026-08-21

Closes the Bed-Stuy SpareRoom gap left open by 0.7.0, and fixes a URL bug found
along the way.

### Added
- **`_fetch_search()` in `sources/spareroom.py`** — queries SpareRoom's search
  endpoint for neighborhoods that have no SEO area page, driven by the new
  `config.SPAREROOM_SEARCH_QUERIES`. **Bed-Stuy is now covered** (326 results
  live); it was the highest-volume gap in the 0.7.0 expansion.
- **`"bedford stuyvesant"`** (unhyphenated) as a neighborhood keyword — the form
  SpareRoom actually uses in listing titles. Two regression tests added.

### Fixed
- **Mangled listing URLs on search-results pages.** The parser took the first
  anchor in a tile, which on search pages is a URL-encoded tracking fragment, so
  listings got unusable links and unstable ids. Tiles are now parsed from their
  `data-listing-*` attributes and the permalink is rebuilt from the stable
  listing id. Verified id-compatible with the 348 existing `sr_*` rows in
  `state.db`, so no re-notification storm.
- **Silent empty results.** A missing SEO page 302s to a disambiguation *form*
  that still returns HTTP 200, so the old `status_code == 200` check treated "no
  such place" as "no listings". `_fetch_search()` now detects that page and logs
  a warning naming the config key to re-check.

### Notes
- Only Bed-Stuy proved recoverable. South Slope, Turtle Bay, Midtown South,
  NoMad, Rose Hill, Hudson Square, World Trade Center, Herald Square, Peter
  Cooper Village and Cooperative Village have no working search name and remain
  uncovered by SpareRoom (still reachable via Craigslist / Reddit / Ohana /
  Listings Project).
- **Do not add a bare place name without checking where it resolves** — bare
  `"Seaport"` returns Redwood City, CALIFORNIA listings.
- The Bed-Stuy search also returns neighbors (Bushwick, Ocean Hill, Crown
  Heights). The neighborhood filter handles them: Bushwick and Ocean Hill are
  dropped, Crown Heights routes to South Brooklyn.

## [0.7.0] — 2026-08-21

Coverage release: the search area roughly doubles (30 → 66 neighborhoods) and the
region map is re-cut. Driven by four neighborhood maps the user supplied, then
trimmed by hand over several passes.

### Added
- **~36 new neighborhoods**, taking the allow-list from 30 areas to **66**
  (80 keywords including aliases).
- **Three Manhattan regions replace the single `manhattan` region**, split into
  north-to-south bands: `midtown` (🟧, ~34th–59th), `midtown_to_fidi` (🟦, the
  band between them), and `fidi` (🟥, the southern tip). Region keys are looked
  up dynamically in `notifier.py`, so the old key simply stops being emitted.
- **Williamsburg sub-area keywords** in North Brooklyn — `east williamsburg`,
  `north/northside`, `south/southside`, `industrial`, and **`los sures`**. These
  mostly improve the *label* in the digest rather than what's matched, since
  `williamsburg` already catches them; `los sures` is the exception, containing
  no "Williamsburg" at all.
- **Bed-Stuy alias set** (`bedford-stuyvesant`, `bed-stuy`, `bed stuy`, `bedstuy`).
- 17 new SpareRoom area paths and 5 new Craigslist search groups.

### Changed
- **Brooklyn re-cut.** Central Brooklyn absorbed the old South Brooklyn
  brownstone belt (Downtown Brooklyn, DUMBO, Park Slope, Carroll Gardens et al.)
  plus Bed-Stuy and Prospect Heights. South Brooklyn was redefined as the true
  southern band: Windsor Terrace, Greenwood Heights, Sunset Park, Prospect
  Lefferts Gardens, Crown Heights, Flatbush, Ditmas Park, Prospect Park South.
- **Region order is now load-bearing.** `_assign_region` returns the first
  *region* that matches, so `central_brooklyn` is deliberately ordered before
  `south_brooklyn`: a Park Slope listing naming "Flatbush Ave" as a cross street
  routes to Central rather than being mislabelled South. Verified by test.
- `notifier.py` test digest (`--test`) now covers all six regions.

### Removed
- **Bushwick** — dropped from North Brooklyn (region keyword, SpareRoom path, and
  its Craigslist search group). Note that `east williamsburg` partly reopens the
  Bushwick-border strip, since that inventory routinely markets itself that way.
- **Red Hook** — considered during planning, never added.
- **Queens from `OHANA_CITIES`** — a leftover from the v0.3.0 region removal
  (2026-07-11). Queens listings were fetched from the Bubble API only to be
  discarded by the neighborhood filter, wasting budget against the 600-listing cap.

### Notes
- `murray hill` also matches **Murray Hill, Queens** (Flushing). Whole-word
  matching cannot distinguish the two; flagged in a code comment.
- Manhattan regions are checked before Brooklyn, so a Sunset Park listing that
  says "Brooklyn Chinatown" lands in `midtown_to_fidi`. Cosmetic only — region
  never affects whether a listing is kept.
- `MEDIANS` still covers only the original 13 neighborhoods, so the
  "% below median" enrichment is silently skipped for all newly added areas.

## [0.6.0] — 2026-07-24

Preferences release: the user lowered their budget and decided against living in
New Jersey, so NJ is dropped from the search entirely. Same shape as the v0.3.0
Queens removal + budget change.

### Changed
- **Budget lowered:** `MAX_RENT` $2,000 → **$1,800** — a hard ceiling; the user
  won't go above $1,800. One constant drives everything, so it propagates to the
  filter, the Craigslist `max_price`, the Ohana server-side price ceiling, and the
  digest subject + footer.

### Removed
- **Removed New Jersey** from the search — region (Jersey City, Hoboken, Journal
  Square, Newport), the `nj` Craigslist search group **and** the
  `newjersey.craigslist.org` site, the two `nj/hudson_county/*` SpareRoom area
  paths, and the Jersey City / Hoboken `MEDIANS` entries all deleted. Because the
  neighborhood allow-list is derived from `REGIONS`, NJ listings arriving from
  national sources (Ohana, Reddit, SpareRoom) now fall out as "wrong area."

## [0.5.0] — 2026-07-19

Coverage + reliability release, prompted by two user reports: no listings were
ever coming from Listings Project, and a request to add liveohana.ai.

### Fixed
- **Listings Project produced 0 listings on every run.** Their site was
  restructured (the old `/listings/housing/new-york` path now 404s), so the
  scraper had been silently returning nothing — the `except` swallowed the 404.
  Rebuilt against the current structure: one card per `/listings/<slug>`, stable
  id from the card's `data-listingid`, neighborhood + move-in/out dates pulled
  from the card. **Scrapes every page** of each category (not just the first
  few): the front pages are the featured/expensive Manhattan listings, and ~95%
  of target-neighborhood matches live deeper in the feed (only 22 of 428 were in
  the first 3 pages). Termination is "stop when a page adds no new listings" —
  LP clamps out-of-range pages to the last page rather than returning empty.
- **Scrape only the sublet + rental categories** (`/real-estate/new-york-city/sublets`
  and `/rentals`), not the bare index. The index also interleaves
  `/seeking_living` (people looking FOR a place — demand-side "ISO"/"looking for
  a room" noise), `/studios` (which on LP means art/creative *workspaces*, not
  studio apartments), and `/commercial` (offices). Sublets + rentals together
  cover every living-space offer — apartments, rooms, houses, and studio
  *apartments* — while excluding those three buckets.
- **Weekly/nightly rates were misread as cheap monthly rent.** Listings Project
  quotes many short-term stays per week or per night (`$650/day`, `$850/week`);
  these were parsed as `$650`/`$850` monthly and sailed under the budget cap.
  Prices are now normalized to a monthly equivalent, and any non-monthly rate is
  flagged `short-term … rate (~$X/mo equiv)` — surfaced, never silently dropped.

### Added
- **Ohana source (liveohana.ai).** Uses Ohana's public Bubble Data API
  (`/api/1.1/obj/listing`) over plain HTTP — no headless browser, so it ships in
  Phase 1, not Phase 2. Constrained server-side to **Live** listings in the
  NYC-area cities (`config.OHANA_CITIES`) that are **at or under `MAX_RENT`**, and
  paginated through **all** of them (~340) rather than just the newest 100. This
  matters: of ~1,500 live NYC listings only ~340 are under budget, so a plain
  "newest 100" spent ~74% of the fetch on over-budget Manhattan listings and left
  affordable Brooklyn ones unseen. The shared filter still narrows to target
  neighborhoods. `Prime lease` listings (straight rentals, not sublets) are kept
  and flagged `direct rental, not a sublet`, matching the Reddit rescue.

## [0.4.0] — 2026-07-14

Coverage release, prompted by a $1,750 rent-stabilized Flatbush studio that the
agent silently missed on two counts: Flatbush was out of area, and a rent-stabilized
lease has none of the Reddit sublet keywords, so it was dropped at the source.

### Added
- **Central Brooklyn region** (`🟨`) — Flatbush, Ditmas Park, Prospect-Lefferts
  Gardens. Kept deliberately small (immediate neighbors, not all of central
  Brooklyn); widen `REGIONS["central_brooklyn"]` in `config.py` if more slip past.
  Auto-creates its own labelled section in the digest.
- **Direct-rental rescue on Reddit housing subs.** A post with no sublet keyword
  used to be dropped; now, on the housing subs, one that **names a price** is kept
  and flagged `direct rental, not a sublet` (`⚠️ filter not passed`) — surfaced,
  never silently dropped. r/AskNYC stays keyword-strict (`REDDIT_KEYWORD_STRICT_SUBS`)
  so priced *questions* don't flood the digest.

### Changed
- Digest footer now notes direct rentals alongside sublets and rooms.

## [0.3.0] — 2026-07-11

Consolidation release: folded the retired `rental-agent` into this agent and
switched to email-only delivery.

### Changed
- **Notifications are now email-only.** Telegram is removed entirely (bot,
  per-region channels, `--get-chat-id` helper, all `TELEGRAM_*` secrets). The
  digest is delivered by **Gmail SMTP** (`SENDER_EMAIL` + `GMAIL_APP_PASSWORD`
  → `TARGET_EMAIL`). Rationale: the Telegram pings went unread; email is the
  channel actually used.
- **Richer HTML digest** ported from `rental-agent`: per-listing cards (price,
  neighborhood, badges, description, "View listing" button) grouped into
  labelled **region sections** within one email. Includes **price-vs-median %**
  computed from the existing `config.MEDIANS` table. One email per run whenever
  there are new matches (near-real-time).
- **Removed Queens** from the search — region, Craigslist search group, and the
  three `queens/*` SpareRoom area paths all deleted.
- **Budget lowered:** `MAX_RENT` $2,300 → **$2,000** — a hard ceiling; the user
  won't go above $2,000.

### Removed
- Resend email path (replaced by Gmail SMTP).

## [0.2.0] — 2026-05-30

### Added
- **Per-region Telegram routing** across 5 NYC channels (Manhattan, North Brooklyn, South Brooklyn, Queens, New Jersey). Listings route to the channel of their first matching neighborhood, falling back to the global chat.
- **Reddit "seeker" detection** — first-person posts like _"I'm looking for a/an apartment/room/sublet"_ are identified as demand-side (someone wanting a place, not offering one). The matched nouns are editable in `config.py` (`REDDIT_SEEKER_NOUNS`). The first-person rule deliberately does **not** catch offers that say _"looking for someone to take over my lease"_.

### Changed
- **Flagged posts are no longer dropped silently.** A flagged post is still sent to Telegram (and the email fallback) with its link unchanged, marked `⚠️ filter not passed`, so a false positive can never hide a real listing. Implemented via the new `Listing.flagged` field.

### Decisions
- **Facebook groups: shelved.** Automated scraping risks the account, and manual feeding provides no value over reading the post directly. No Facebook code shipped.

## [0.1.0] — initial
- Initial sublet-agent: Craigslist (NYC + NJ), Listings Project, SpareRoom, and Reddit sources; budget / area / scam filters; Telegram notifications with Resend email fallback; GitHub Actions cron (every 15 min) with `state.db` dedup.
