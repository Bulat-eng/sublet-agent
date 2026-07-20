# Sublet Agent — Handover

Live and running on **GitHub Actions** (free). This doc covers what it does, how it's wired, what changed most recently, and the open threads.

_Last updated: 2026-07-19 (see CHANGELOG `[0.5.0]`: fixed Listings Project scraper + added Ohana). Released as `v0.5.0`, PR #8, merge `590f827`._

---

## What it does

Every cron tick it scrapes **Craigslist (NYC + NJ)**, **Listings Project** (sublet + rental categories), **SpareRoom** (per-neighborhood), **Reddit**, and **Ohana** (liveohana.ai, public API) for NYC sublets / rooms; filters by budget, neighborhood, and scam patterns; deduplicates via SQLite (`state.db`, committed back to the repo); and emails new matches as a single region-grouped HTML digest via **Gmail SMTP**. Cost: ~$0/mo.

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
notifier.py                 → Email-only: region-grouped HTML digest (price-vs-median
                              from config.MEDIANS) sent via Gmail SMTP.
sources/craigslist.py       → CL NYC + NJ (rotating UA, randomized delays).
sources/listings_project.py → listingsproject.com /sublets + /rentals categories, ALL
                              pages (stops when a page adds no new listings). Weekly/nightly
                              rates normalized to a monthly equivalent + flagged.
sources/spareroom.py        → Per-neighborhood SEO area pages (config.SPAREROOM_AREAS).
sources/reddit.py           → Public RSS; sublet-keyword filter + "seeker" detection +
                              direct-rental rescue (priced non-sublet posts on housing subs).
sources/ohana.py            → liveohana.ai public Bubble Data API (plain HTTP, no browser).
                              Live NYC-area listings ≤ MAX_RENT, cursor-paginated; Prime-lease
                              (straight rentals) kept & flagged "direct rental, not a sublet".
.github/workflows/hunt.yml  → cron (*/15) + workflow_dispatch + state.db commit-back.
```

The live agent runs from **`main` HEAD** — every tick checks out whatever is on `main`.

---

## Infra & accounts

| Service | Where | Purpose |
|---|---|---|
| **GitHub** | github.com/**Bulat-eng**/sublet-agent (renamed from `Bulat-personal`; old URL redirects) | Source + Actions hosting (free, public repo) |
| **Gmail SMTP** | smtp.gmail.com:465 (App Password) | Sends the digest email |
| **Reddit** | public `/new/.rss` feeds | No auth/app needed |
| **Ohana** | `liveohana.ai/api/1.1/obj/listing` (public Bubble Data API) | No auth/app needed — plain HTTP |

### GitHub Secrets (Settings → Secrets and variables → Actions)
`SENDER_EMAIL` (sending Gmail), `GMAIL_APP_PASSWORD` (16-char app password),
`TARGET_EMAIL` (inbox that receives). The old `TELEGRAM_*` / `RESEND_API_KEY`
secrets are no longer read and can be deleted. (Secrets live in GitHub, never in code.)

---

## Search criteria (all in `config.py`)

- **Rent:** $700 – **$2,000**/mo (hard reject above; below $700 flagged scam-suspicious)
- **Max bedrooms:** 2 (studio / 1BR / 2BR)
- **Sublet duration:** 1–12 months (soft tag if outside)
- **Move-in window:** **2026-06-15 → 2026-09-30** (soft flag if outside)
- **Furnished:** flagged, not filtered
- **Neighborhoods:** 5 regions → labelled sections in the digest email: Manhattan (below ~23rd St), North Brooklyn, South Brooklyn, Central Brooklyn (Flatbush / Ditmas Park / Prospect-Lefferts, added 2026-07-14), New Jersey. (Queens removed 2026-07-11.) See `REGIONS`.
- **SpareRoom:** 28 explicit neighborhood paths in `SPAREROOM_AREAS`.

---

## What changed in the last session (2026-07-19) — PR #8, merged `590f827`, tagged `v0.5.0`

Two user reports: no listings ever came from Listings Project, and "add liveohana.ai."

1. **Listings Project was silently returning 0** (had been for a while). The old URL `/listings/housing/new-york` now **404s** (site restructure) and the `except` swallowed it. Rebuilt against the current markup: `/listings/<slug>` cards, stable id from each card's **`data-listingid`**, neighborhood + move-in/out dates parsed from the card.
2. **LP now scrapes the `/sublets` + `/rentals` categories, every page** — not the bare index, which also interleaves `/seeking_living` (ISO / "looking for a room" — demand-side noise, out of scope), `/studios` (on LP these are art/creative **workspaces**, not studio apartments), and `/commercial`. Studio **apartments** are kept (they carry "Apartments for Sublet/Rent"). Pagination stops when a page adds **no new listings** — LP clamps out-of-range pages to the last page instead of returning empty, so "stop on empty page" never fired (it was running to the 80-page safety cap).
3. **LP weekly/nightly rates → monthly-equivalent + flagged.** Many LP stays are quoted per week/night (`$650/day`); they were read as cheap monthly rent and slid under the budget cap. Now normalized (×4.33 wk, ×30.4 day) and flagged `short-term … rate (~$X/mo equiv)`.
4. **New source: Ohana (liveohana.ai).** It's a Bubble.io app, but its **public Data API** (`/api/1.1/obj/listing`) returns structured JSON over plain HTTP — no Playwright, so it moved from Phase 2 into **Phase 1**. Constrained server-side to **Live** listings in `OHANA_CITIES` (`New York` = Manhattan, `Brooklyn`, `Queens`) **at/under `MAX_RENT`**, cursor-paginated through all ~340 (of ~1,500 live NYC). This stops the fetch wasting slots on over-budget Manhattan listings and burying affordable Brooklyn ones. `Prime lease` (straight rentals) kept and flagged `direct rental, not a sublet`. The geo `neighborhood_geographic_address` is unreliable (a Williamsburg listing geocoded to Brisbane AU) — the title carries the neighborhood for routing.

**Verified end-to-end** (fetch → shared filter, no email/DB writes): Listings Project **0 → 372** offers, Ohana **342** affordable, **104** pass the shared filter (was 4 before this branch). LP full scrape ≈ 50s (28 sublet + 11 rental pages), Ohana ≈ 9s. Not yet observed on a live GH Actions run — the next scheduled tick will be the first (see open item #3).

---

## Open items / current limitations

1. **⚠️ Cron is throttled (biggest issue).** GitHub runs the `*/15` schedule only **every ~2–4 hours** on this public repo, so listings arrive stale — a real handicap in a fast rental market. Fix: an external pinger (e.g. cron-job.org → `repository_dispatch`, or hitting `workflow_dispatch`). **Not yet done.** Once fixed, the cadence gating (item below) actually starts earning its keep.
2. **Node 20 action deprecation.** `hunt.yml` uses `actions/checkout@v4` + `actions/setup-python@v5` (Node 20); GitHub forces Node 24 on **2026-06-16**. Bump the action versions. _(A task chip was spawned for this.)_
3. **First-run notification burst is imminent (expected, accepted).** v0.5.0 massively widened coverage — end-to-end testing showed **~104 matches** currently passing the filter (LP 0→372, Ohana +342). The **next scheduled run** will email that whole backlog in one big digest, then dedup keeps later ones small. The user was asked and **explicitly wants it uncapped** ("the first digest will be big — it's fine"). No per-run cap added by choice; still easy to add later if it becomes annoying.
4. **SpareRoom area-URL dependency.** 28 hardcoded slugs in `SPAREROOM_AREAS`. If SpareRoom renames an area path it 404s (logged warning, run continues). No dedicated SpareRoom page for **Seaport / Journal Square / Newport** (the latter two are covered by `jersey_city`).
5. **Cadence gating is mostly dormant** while the cron only fires every 2–4h (always longer than the 30m/6h cadences). It's forward-looking insurance for when item #1 is fixed.
6. **Remaining off sources:** **LeaseBreak** (Phase 2, Cloudflare-protected → needs Playwright, skeleton not written) and **Facebook** (shelved / opt-in). Ohana is now **on** (Phase 1, public API — no Playwright). See README.
7. **Ohana coverage caveats.** Only listings with a populated `min_rent_number` are fetched — ~23 price-unknown ones are excluded by the server-side price ceiling (mention if the user ever wants them, flagged). City labels `Manhattan`/`Bronx` return nothing (Manhattan uses `New York`), so they're intentionally omitted from `OHANA_CITIES`. If the public Data API is ever disabled, Ohana would need the Playwright approach after all — detect via `[Ohana] HTTP 4xx/5xx` or a drop to 0 results.
8. **Region mis-routing on cross-mentions (minor, pre-existing).** `filter._assign_region` returns the *first* region whose neighborhood keyword appears anywhere in the text (incl. body), Manhattan first. A Brooklyn listing whose body says "20 min to Chelsea" can land in the Manhattan section. Cosmetic (affects the digest section, not whether a listing shows); more visible now with ~104 matches. Not fixed this session.

---

## Common tasks

| Task | How |
|---|---|
| Change budget / move-in / bedrooms | Edit constants at top of `config.py` |
| Add/remove neighborhoods | Edit `REGIONS` in `config.py` (drives filtering + email section grouping) |
| Add/remove SpareRoom areas | Edit `SPAREROOM_AREAS` — path format `borough/neighborhood` (NJ: `nj/hudson_county/city`); verify the URL returns listings first |
| Change Ohana scope | `OHANA_CITIES` (Bubble city labels; Manhattan = `"New York"`). The price ceiling is inherited from `MAX_RENT`. `OHANA_MAX_LISTINGS` caps the paginated total |
| Test the changed sources | `python -m sources.listings_project` · `python -m sources.ohana` (both print a sample; no email/DB writes) |
| Change per-source frequency | Edit `SOURCE_CADENCE_MINUTES` (Ohana 20m, Listings Project 6h) |
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
python -m sources.spareroom          # test a single source
python -m sources.listings_project   # LP: /sublets + /rentals, all pages (~50s)
python -m sources.ohana              # Ohana: Live NYC listings ≤ MAX_RENT (~9s)
```

Living docs: `99_troubleshooting.md` (append lessons as scrapers break), `CHANGELOG.md` (releases), `README.md` (setup).
