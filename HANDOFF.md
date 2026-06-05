# Sublet Agent — Handover

Live and running on **GitHub Actions** (free). This doc covers what it does, how it's wired, what changed most recently, and the open threads.

_Last updated: 2026-06-05._

---

## What it does

Every cron tick it scrapes **Craigslist (NYC + NJ)**, **Listings Project**, **SpareRoom** (per-neighborhood), and **Reddit** for NYC sublets / rooms; filters by budget, neighborhood, and scam patterns; deduplicates via SQLite (`state.db`, committed back to the repo); and pushes new matches to **Telegram** (per-region channels) with a **Resend** email fallback. Cost: ~$0/mo.

---

## Architecture

```
main.py                     → Orchestrator: one run per GH Actions tick.
                              Per-source cadence gating (honors SOURCE_CADENCE_MINUTES).
config.py                   → ALL prefs: budget, move-in window, REGIONS + neighborhoods,
                              SPAREROOM_AREAS, cadences, secrets-from-env.
filter.py                   → HARD (budget, wrong-area) + SOFT (duration/move-in/furnished
                              tags) + SCAM filters. Whole-word neighborhood routing.
db.py                       → SQLite dedup (`seen` table) + per-source last-run
                              (`source_runs` table). Committed back to repo by the workflow.
models.py                   → Listing dataclass.
notifier.py                 → Telegram primary (per-region channels), Resend email fallback.
sources/craigslist.py       → CL NYC + NJ (rotating UA, randomized delays).
sources/listings_project.py → listingsproject.com.
sources/spareroom.py        → Per-neighborhood SEO area pages (config.SPAREROOM_AREAS).
sources/reddit.py           → Public RSS; sublet-keyword filter + "seeker" detection.
.github/workflows/hunt.yml  → cron (*/15) + workflow_dispatch + state.db commit-back.
```

The live agent runs from **`main` HEAD** — every tick checks out whatever is on `main`.

---

## Infra & accounts

| Service | Where | Purpose |
|---|---|---|
| **GitHub** | github.com/**Bulat-eng**/sublet-agent (renamed from `Bulat-personal`; old URL redirects) | Source + Actions hosting (free, public repo) |
| **Telegram** | bot via @BotFather | Primary notifications, routed to per-region channels |
| **Resend** | resend.com | Email fallback when Telegram fails |
| **Reddit** | public `/new/.rss` feeds | No auth/app needed |

### GitHub Secrets (Settings → Secrets and variables → Actions)
`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` (global fallback), per-region chat IDs
`TELEGRAM_CHAT_ID_MANHATTAN` / `_NORTH_BK` / `_SOUTH_BK` / `_QUEENS` / `_NJ`,
`RESEND_API_KEY`, `TARGET_EMAIL`. (Secrets live in GitHub, never in code.)

---

## Search criteria (all in `config.py`)

- **Rent:** $700 – **$2,300**/mo (hard reject above; below $700 flagged scam-suspicious)
- **Max bedrooms:** 2 (studio / 1BR / 2BR)
- **Sublet duration:** 1–12 months (soft tag if outside)
- **Move-in window:** **2026-06-15 → 2026-09-30** (soft flag if outside)
- **Furnished:** flagged, not filtered
- **Neighborhoods:** 5 regions → each its own Telegram channel: Manhattan (below ~23rd St), North Brooklyn, South Brooklyn, Queens, New Jersey. See `REGIONS`.
- **SpareRoom:** 31 explicit neighborhood paths in `SPAREROOM_AREAS`.

---

## What changed in the last session (2026-06-05) — PR #3, merged `5aaadca`

1. **Tuning:** max rent $2,500 → **$2,300**; earliest move-in → **2026-06-15**.
2. **Reddit seeker filter:** now flags bare **"Looking for &lt;area&gt; sublet/lease"** titles, not just first-person "I'm looking for…"; added `"lease"` to `REDDIT_SEEKER_NOUNS`. Still **flags** (notifies), doesn't drop.
3. **Region-routing bug fix:** neighborhoods now match as **whole words** (`\b…\b`). Previously the abbreviation `"les"` matched inside "stain**les**s"/"wire**les**s" and `"lic"` inside "po**lic**e", which mis-routed Hamilton Heights / Harlem into the Manhattan feed. Logged in `99_troubleshooting.md`.
4. **SpareRoom → per-neighborhood:** fetches one SEO area page per target neighborhood (`SPAREROOM_AREAS`, 31 verified paths) instead of the broad `/rooms-for-rent/nyc`. The broad feed buried low-volume downtown targets under high-volume uptown listings; per-neighborhood returns ~95–100% on-target. Parser unchanged.
5. **Per-source cadence gating:** `main.py` + new `source_runs` table honor `SOURCE_CADENCE_MINUTES` so we don't hit every source every tick (SpareRoom 30m, Listings Project 6h).

**Verified live:** workflow_dispatch run `27041956302` (2026-06-05 21:50Z) succeeded in 6m21s —
`craigslist 74 · listings_project 0 · spareroom 220 across 31 areas (no rate-limiting) · reddit 2`
→ 296 scraped → kept 176 (rejected: 82 over-budget, **20 wrong-area**, 18 scam) → 70 new → notified.

---

## Open items / current limitations

1. **⚠️ Cron is throttled (biggest issue).** GitHub runs the `*/15` schedule only **every ~2–4 hours** on this public repo, so listings arrive stale — a real handicap in a fast rental market. Fix: an external pinger (e.g. cron-job.org → `repository_dispatch`, or hitting `workflow_dispatch`). **Not yet done.** Once fixed, the cadence gating (item below) actually starts earning its keep.
2. **Node 20 action deprecation.** `hunt.yml` uses `actions/checkout@v4` + `actions/setup-python@v5` (Node 20); GitHub forces Node 24 on **2026-06-16**. Bump the action versions. _(A task chip was spawned for this.)_
3. **First-run notification bursts.** After a coverage expansion the catch-up run can notify a lot at once (last run: 70). No per-run cap yet — easy to add if it's annoying.
4. **SpareRoom area-URL dependency.** 31 hardcoded slugs in `SPAREROOM_AREAS`. If SpareRoom renames an area path it 404s (logged warning, run continues). No dedicated SpareRoom page for **Seaport / Journal Square / Newport** (the latter two are covered by `jersey_city`).
5. **Cadence gating is mostly dormant** while the cron only fires every 2–4h (always longer than the 30m/6h cadences). It's forward-looking insurance for when item #1 is fixed.
6. **Phase 2 sources** (Ohana, LeaseBreak via Playwright) and **Facebook** remain off / opt-in. See README.

---

## Common tasks

| Task | How |
|---|---|
| Change budget / move-in / bedrooms | Edit constants at top of `config.py` |
| Add/remove neighborhoods | Edit `REGIONS` in `config.py` (drives filtering + Telegram routing) |
| Add/remove SpareRoom areas | Edit `SPAREROOM_AREAS` — path format `borough/neighborhood` (NJ: `nj/hudson_county/city`); verify the URL returns listings first |
| Change per-source frequency | Edit `SOURCE_CADENCE_MINUTES` |
| Tune Reddit seeker detection | `REDDIT_SEEKER_NOUNS` + the `_SEEKER_RE` regex in `sources/reddit.py` |
| Debug why a listing routed somewhere | `python -c "from filter import _assign_region; print(_assign_region('<card text>'))"` |
| Deploy a change | PR into `main` (agent runs from `main` HEAD); cron picks it up next tick |
| Roll back a bad release | `git revert -m 1 <merge-sha> && git push origin main` |
| Trigger a run manually | `gh workflow run hunt.yml -R Bulat-eng/sublet-agent` (or Actions tab → Run workflow) |
| Cut a release | Update `CHANGELOG.md`, `git tag vX.Y.Z && git push origin vX.Y.Z` (see README) |

---

## Run / test locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in your own secrets — never commit it
python main.py            # full run
python -m sources.spareroom   # test a single source
```

Living docs: `99_troubleshooting.md` (append lessons as scrapers break), `CHANGELOG.md` (releases), `README.md` (setup).
