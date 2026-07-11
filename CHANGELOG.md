# Changelog

All notable changes to the sublet-agent are documented here. Versions follow [semver](https://semver.org/).

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
