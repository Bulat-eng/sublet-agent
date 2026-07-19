# Changelog

All notable changes to the sublet-agent are documented here. Versions follow [semver](https://semver.org/).

## [0.5.0] — 2026-07-19

Coverage + reliability release, prompted by two user reports: no listings were
ever coming from Listings Project, and a request to add liveohana.ai.

### Fixed
- **Listings Project produced 0 listings on every run.** Their site was
  restructured (the old `/listings/housing/new-york` path now 404s), so the
  scraper had been silently returning nothing — the `except` swallowed the 404.
  Rebuilt against the current structure: NYC index at `/real-estate/new-york-city`
  (paginated, first 3 pages), one card per `/listings/<slug>`, stable id from the
  card's `data-listingid`, neighborhood + move-in/out dates pulled from the card.
- **Weekly/nightly rates were misread as cheap monthly rent.** Listings Project
  quotes many short-term stays per week or per night (`$650/day`, `$850/week`);
  these were parsed as `$650`/`$850` monthly and sailed under the budget cap.
  Prices are now normalized to a monthly equivalent, and any non-monthly rate is
  flagged `short-term … rate (~$X/mo equiv)` — surfaced, never silently dropped.

### Added
- **Ohana source (liveohana.ai).** Uses Ohana's public Bubble Data API
  (`/api/1.1/obj/listing`) over plain HTTP — no headless browser, so it ships in
  Phase 1, not Phase 2. Constrained server-side to **Live** listings in the
  NYC-area cities (`config.OHANA_CITIES`), newest first; the shared filter narrows
  to target neighborhoods. `Prime lease` listings (straight rentals, not sublets)
  are kept and flagged `direct rental, not a sublet`, matching the Reddit rescue.

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
