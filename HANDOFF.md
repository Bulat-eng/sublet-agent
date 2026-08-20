# Sublet Agent — Handover

Live and running on **GitHub Actions** (free). This doc covers what it does, how it's wired, what changed most recently, and the open threads.

_Last updated: 2026-08-20 — **outage + migration session**: the agent went silent 2026-08-15 (GitHub Actions free minutes exhausted, not a code bug). Repo was migrated to a **new public repo** with rewritten history, Gmail credentials were regenerated, and email delivery is verified working. **The `schedule` trigger has never fired on the new repo** — see open item #1, this is the one thing still broken. Previous entry: 2026-08-16 — diagnostic session only, **no code changes**: traced why Ohana digest prices don't match the prices on the listing pages. Found a real bug in `sources/ohana.py` (left unfixed at the user's request — see "Last session" below and open item #8). Last **code** change was still 2026-07-24 (CHANGELOG `[0.6.0]`: lowered budget to $1,800 + removed New Jersey), released as `v0.6.0`, PR #13, merge `2dda848`._

---

## What it does

Every cron tick it scrapes **Craigslist (NYC)**, **Listings Project** (sublet + rental categories), **SpareRoom** (per-neighborhood), **Reddit**, and **Ohana** (liveohana.ai, public API) for NYC sublets / rooms; filters by budget, neighborhood, and scam patterns; deduplicates via SQLite (`state.db`, committed back to the repo); and emails new matches as a single region-grouped HTML digest via **Gmail SMTP**. Cost: ~$0/mo.

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
sources/craigslist.py       → CL NYC (rotating UA, randomized delays).
sources/listings_project.py → listingsproject.com /sublets + /rentals categories, ALL
                              pages (stops when a page adds no new listings). Weekly/nightly
                              rates normalized to a monthly equivalent + flagged.
sources/spareroom.py        → Per-neighborhood SEO area pages (config.SPAREROOM_AREAS).
sources/reddit.py           → Public RSS; sublet-keyword filter + "seeker" detection +
                              direct-rental rescue (priced non-sublet posts on housing subs).
sources/ohana.py            → liveohana.ai public Bubble Data API (plain HTTP, no browser).
                              Live NYC-area listings ≤ MAX_RENT, cursor-paginated; Prime-lease
                              (straight rentals) kept & flagged "direct rental, not a sublet".
.github/workflows/hunt.yml  → cron (7,22,37,52 — off the congested :00/:15/:30/:45
                              slots) + workflow_dispatch + state.db commit-back
                              (rebases + retries on concurrent runs).
```

The live agent runs from **`main` HEAD** — every tick checks out whatever is on `main`.

---

## Infra & accounts

| Service | Where | Purpose |
|---|---|---|
| **GitHub** | github.com/**Bulat-eng**/sublet-agent — **recreated 2026-08-18 as a brand-new PUBLIC repo** (public ⇒ unlimited free Actions). The previous private repo is preserved, read-only, as `sublet-agent-private-old` (workflow disabled). | Source + Actions hosting (free, public repo) |
| **Gmail SMTP** | smtp.gmail.com:465 (App Password) | Sends the digest email |
| **Reddit** | public `/new/.rss` feeds | No auth/app needed |
| **Ohana** | `liveohana.ai/api/1.1/obj/listing` (public Bubble Data API) | No auth/app needed — plain HTTP |

### GitHub Secrets (Settings → Secrets and variables → Actions)
`SENDER_EMAIL` (sending Gmail), `GMAIL_APP_PASSWORD` (16-char app password),
`TARGET_EMAIL` (inbox that receives). All three were **re-created 2026-08-19** on the new
repo; the legacy `TELEGRAM_*` / `RESEND_API_KEY` secrets did not carry over and are gone.
(Secrets live in GitHub, never in code.) **Secrets are write-only — you cannot read an old
value back**, so if the app password is ever lost it must be regenerated at
`myaccount.google.com/apppasswords`. Sender and target are both the same Gmail.

---

## Search criteria (all in `config.py`)

- **Rent:** $700 – **$1,800**/mo (hard reject above; below $700 flagged scam-suspicious)
- **Max bedrooms:** 2 (studio / 1BR / 2BR)
- **Sublet duration:** 1–12 months (soft tag if outside)
- **Move-in window:** **2026-06-15 → 2026-09-30** (soft flag if outside)
- **Furnished:** flagged, not filtered
- **Neighborhoods:** 4 regions → labelled sections in the digest email: Manhattan (below ~23rd St), North Brooklyn, South Brooklyn, Central Brooklyn (Flatbush / Ditmas Park / Prospect-Lefferts, added 2026-07-14). (Queens removed 2026-07-11; New Jersey removed 2026-07-24.) See `REGIONS`.
- **SpareRoom:** 26 explicit neighborhood paths in `SPAREROOM_AREAS`.

---

## Last session (2026-08-20) — outage recovery + repo migration

**Symptom reported:** no emails since 2026-08-15, "GitHub is full of failed attempts".

**Root cause (not a code bug).** Every scheduled run was failing in 4–5s with no logs,
because the job never started. The reason is only visible via the API:

```bash
gh api repos/<owner>/<repo>/actions/runs/<run_id>/jobs --jq '.jobs[0].id'
gh api repos/<owner>/<repo>/check-runs/<job_id>/annotations
```

> The job was not started because recent account payments have failed or your spending
> limit needs to be increased.

The account's **2,000 min/month free private-repo Actions allowance was exhausted**
(billing page read 2,000/2,000; GitHub Free plan, no failed payment). Usage had simply
grown: **505 runs (Jun) → 843 (Jul) → 864 in the first 15 days of Aug**, and adding Zumper
+ CL-sublets on 2026-07-27 lengthened each run. This repo averages **5.4 billable min/run**
and was **77%** of the account's Actions spend.

**What was done:**
1. **Repo made public** (public repos get unlimited free Actions). Because a plain
   force-push does NOT purge orphaned commits from GitHub — old SHAs stayed readable, and
   workflow runs publish them as `head_sha` — a clean publish required a **fresh repo**:
   old one renamed `sublet-agent-private-old`, history rewritten with `git filter-repo`
   to purge the personal email, pushed to a brand-new public repo. Verified: old SHAs 404.
2. **Email default scrubbed** from `config.py` and `.env.example` (it was hardcoded in both).
3. **Gmail credentials regenerated.** The old pair returned `535 BadCredentials` and was
   unrecoverable. Delivery **verified working** 2026-08-19 and again 2026-08-20
   (`Gmail SMTP: digest sent` → 97 and 53 listings).
4. **`state.db` push made resilient** to concurrent runs (rebase + retry, keeps ours on
   conflict) — commit `38cc0f7`.
5. **Stale branches deleted** — only `main` remains.
6. **Cron slot changed** `*/15` → `7,22,37,52` (commit `aac53c2`) to force schedule
   re-registration and dodge the congested quarter-hour slots. **Unverified — see item #1.**

**Backups:** `~/Documents/_archive/bundles/sublet-agent-backup-20260818-094536.bundle`.

---

## Previous session (2026-08-16) — diagnostic only, no code changes

The user reported that Ohana listings pass the filter and show one price in the digest, but the listing page shows a **much higher, over-budget** price. Traced live against the Bubble Data API and the rendered page. **Three independent causes**, only one of which is our bug. Nothing was changed — the user said "nevermind for now."

**1. Real bug — `min_rent_number` is the cheapest room, not the room you get.** `_price()` in `sources/ohana.py` reads `min_rent_number` first. On a multi-room listing that is the *floor* across all rooms, and sometimes it's simply stale/wrong. Measured against the 278 listings the agent currently considers at ≤$1,800:
- **20** have more than one priced room
- **13** have a `min_rent_number` that disagrees with their own cheapest room
- **12** pass the budget filter while containing a room *over* $1,800

  Worst live example: `peaceful-room-with-private-entrance-in-carroll-gardens` — digest would say **$1,498**, cheapest actual room is **$2,354**. Others: `2br-fully-furnished-in-the-ues` $1,605 → $1,739; `room-in-3br1ba-apt-4-mins-6-train` $1,502 → $1,605.

**2. Variable pricing (not fully fixable via the Data API).** The *listing* field `dynamic_pricing_boolean` is `False`, which is why this was missed — but the **`room`** object carries `variable_pricing__boolean`, and **51 of 278 (18%)** have it set. For those, the API rent is a base and the site quotes a term/date-dependent number. Example: `private-room-in-new-york-302` API base $2,006.46, page quotes **$2,119** for its Sep 15 dates.

**3. Price drift (not a bug).** The listing the user clicked has exactly one room, so cause 1 can't apply — the host genuinely re-priced it. All **15** units at 7 Eldridge St (same pro host, "Sam" / OJH Holdings) were re-priced between the 8/11 digest and 8/16; they're $1,835–$2,285 now, vs the $1,489/$1,585 that was emailed. Compounding this: `state.db`'s `seen` table stores only `id, url, source, seen_at` — **no price** — so a listing is never re-checked after first sight and the emailed price is a permanent snapshot.

**Confirmed as *not* a problem:** the emailed price is already inclusive of Ohana's 7% renter fee. The room object exposes both sides — `rent_earned_by_host_number` (1875.2) × 1.07 = `rent_number` (2006.46).

**Key discovery for whoever picks this up:** there is a **`room` object type** at `/api/1.1/obj/room`, queryable exactly like `listing`, filterable by `listing_custom_product` (the listing `_id`). It holds the per-room truth: `rent_number`, `rent_earned_by_host_number`, `variable_pricing__boolean`. `sources/ohana.py` never reads it. See open item #8 for the proposed fix.

---

## Previous session (2026-07-30) — diagnostic only, no code changes

The user asked why no Listings Project listings had shown up recently — bug, or genuinely no matches? Traced the full pipeline live. **Not a bug** — everything working as designed:

- **Scraper healthy.** A live fetch pulled **318** NYC sublet+rental listings, parsed correctly (prices, neighborhoods, dates).
- **22 currently pass the filter** (in-budget + target neighborhood), and **all 22 had already been emailed** — most recently in the **Wed 7/29 ~11 AM ET** refresh. Cross-referenced every passing listing against the cloud `seen` table: **0 genuinely-new being wrongly suppressed**. (Marking-seen is gated on a successful send in `main.py`, so their presence in `seen` also proves the digest actually went out.)
- **LP is a weekly pulse.** Listings Project refreshes ~weekly (its own "Wednesday digest" cadence). Confirmed in the data: new in-budget LP matches landed **Wed 7/22 (25)** and **Wed 7/29 (22)** — exactly 7 days apart (the 40 on Mon 7/20 was the one-time initial backfill of pre-existing inventory). Between Wednesdays, dedup correctly suppresses the already-sent batch, so the LP portion of the digest is empty until the next refresh. Other sources still feed the digest daily, so digests aren't empty in between.
- **Budget is the yield cap, not a bug.** Of 161 in-neighborhood LP listings, only 22 fit under $1,800 (44 at $2,500, 60 at $3,000); ~82% of all LP listings are rejected on price alone. **Rooms/shares are fully included** — most matches are exactly that; there is no room-type filter anywhere.
- **Noted for a future session:** `config.MAX_BEDROOMS = 2` is **dead code** — defined but never referenced in `filter.py`/`main.py`, so it silently filters nothing. Decide whether to wire it into the filter or delete it (a stale-looking cap is a footgun). Separately, the $700 `MIN_RENT` floor drops sub-$700 rooms as scam-suspicious — relevant if very cheap shared rooms are ever wanted.

---

## What changed in the last session (2026-07-24) — PR #13, merged `2dda848`, tagged `v0.6.0`

Two user-preference changes (the full v0.5.0 coverage work remains in CHANGELOG `[0.5.0]`).

1. **Budget lowered: `MAX_RENT` $2,000 → $1,800.** A single hard cap; because everything reads `config.MAX_RENT`, it propagates to the filter, the Craigslist `max_price`, the Ohana server-side price ceiling, and the digest subject + footer. "Above $1,800" is strictly above — a listing priced at exactly $1,800 still comes through.
2. **New Jersey removed entirely.** The user decided against living there. Deleted the `new_jersey` region (Jersey City, Hoboken, Journal Square, Newport), the `nj` Craigslist search group **and** the `newjersey.craigslist.org` site, both `nj/hudson_county/*` SpareRoom paths, and the Jersey City / Hoboken `MEDIANS` entries. Because the neighborhood allow-list is derived from `REGIONS`, NJ listings arriving from national sources (Ohana, Reddit, SpareRoom) now fall out as "wrong area." Search now covers **Manhattan · North Brooklyn · South Brooklyn · Central Brooklyn**.

**Verified:** `MAX_RENT == 1800` with the boundary confirmed ($1,750 and $1,800 kept; $1,801 and $1,900 rejected); no functional NJ references remain (only a dated breadcrumb in `config.py`); a $1,600 Jersey City listing is now rejected as "wrong area"; the digest still builds with no NJ section.

---

## Open items / current limitations

1. **🔴 THE CRON HAS NEVER FIRED ON THE NEW REPO (biggest issue — currently blocking autonomy).** As of 2026-08-20, **every run this repo has ever had was `workflow_dispatch`; `schedule` count is 0** over 2+ days. Note `workflow_dispatch` is one-shot — a manual run never seeds future runs, so between manual pokes the agent is simply dead.
   - **Ruled out:** the workflow file (diffed against the old repo — the `on: schedule` block was byte-identical), default branch (`main`), fork/archived/disabled status, Actions permissions (`enabled=true, allowed_actions=all`), workflow state (`active`).
   - **Disproved theory:** exhausted Actions minutes do NOT suppress `schedule`. The old repo shows **100/100 runs with `event=schedule`** firing right through the billing block — GitHub created the runs and merely refused to start them.
   - **Root cause still unknown**, and it is GitHub-side. The only material change is that this is a brand-new repo whose scheduler never activated.
   - **Attempted fix (unverified):** cron moved to `7,22,37,52` in `aac53c2` — rewriting the cron line forces re-registration, and odd minutes avoid the heavily oversubscribed `:00/:15/:30/:45` slots.
   - **If that fails, escalate in this order:** (a) delete `hunt.yml`, push, re-add, push again (harder re-registration); (b) recreate it under a NEW filename e.g. `hunt2.yml` — GitHub treats that as an entirely new workflow with a fresh schedule; (c) external pinger (cron-job.org → `workflow_dispatch`, needs a fine-grained PAT given to a third party); (d) GitHub Support — a public repo with a valid cron on the default branch that never fires in 48h+ is arguably a platform bug.
2. **Node 20 action deprecation — RESOLVED.** `hunt.yml` now pins `actions/checkout@v6.0.3` + `actions/setup-python@v6.2.0`.
3. **First-run notification burst — RESOLVED (2026-07-30).** The anticipated big first digest went out and the system is now in **steady state**: dedup keeps each run small and per-source volume has settled (LP is now a ~20-listing weekly-Wednesday pulse — see "Last session (2026-07-30)"). No per-run cap was added (user wanted it uncapped) and none has proven necessary. Verified healthy in production 2026-07-30. _(Original note: v0.5.0 widened coverage to ~104 matches — LP 0→372, Ohana +342 — and the first scheduled run emailed that whole backlog at once, as expected/accepted.)_
4. **SpareRoom area-URL dependency.** 26 hardcoded slugs in `SPAREROOM_AREAS`. If SpareRoom renames an area path it 404s (logged warning, run continues). No dedicated SpareRoom page for **Seaport**.
5. **Cadence gating is mostly dormant** while the cron only fires every 2–4h (always longer than the 30m/6h cadences). It's forward-looking insurance for when item #1 is fixed.
6. **Remaining off sources:** **LeaseBreak** (Phase 2, Cloudflare-protected → needs Playwright, skeleton not written) and **Facebook** (shelved / opt-in). Ohana is now **on** (Phase 1, public API — no Playwright). See README.
7. **Ohana coverage caveats.** Only listings with a populated `min_rent_number` are fetched — ~23 price-unknown ones are excluded by the server-side price ceiling (mention if the user ever wants them, flagged). City labels `Manhattan`/`Bronx` return nothing (Manhattan uses `New York`), so they're intentionally omitted from `OHANA_CITIES`. If the public Data API is ever disabled, Ohana would need the Playwright approach after all — detect via `[Ohana] HTTP 4xx/5xx` or a drop to 0 results.
8. **⚠️ Ohana digest prices can be wrong / over budget (diagnosed 2026-08-16, NOT fixed).** Three causes, detailed in "Last session (2026-08-16)". Proposed fix, in priority order — the user deferred all of it:
   1. **Read the `room` object** (`/api/1.1/obj/room`, filter `listing_custom_product` in `[listing ids]`, batch ~40 ids per call — ~7 calls for the current 278). Price from the real room instead of the listing rollup, and budget-filter on that. ~30 lines in `sources/ohana.py`. Fixes cause 1 outright.
   2. **Flag variable-pricing listings** in the digest ("price varies by term — verify on site") when any room has `variable_pricing__boolean`. Trivial; mitigates cause 2. Can't be fully fixed without emulating the booking widget.
   3. **Store price in `seen` + re-check known listings** each run — schema migration in `db.py` plus a re-fetch loop in `main.py`. Fixes cause 3 and would enable "price dropped" alerts. Bigger job; deferred.
9. **⚠️ A GREEN RUN DOES NOT MEAN EMAIL WAS SENT.** `main.py` exits 0 after a delivery failure, so the workflow shows **success** while silently sending nothing — exactly how a broken digest can go unnoticed for days. It does correctly skip marking listings as seen on failure, so nothing is lost and they retry next run. **Proposed fix (offered, not yet approved): make delivery failure fail the run** so it shows red. To spot it manually, grep a run log for `Gmail SMTP` / `Notification failed`.
10. **Mac-side launchd pinger is a TEMPORARY crutch for item #1.** `~/.local/bin/sublet-hunt-ping.sh` + LaunchAgent `~/Library/LaunchAgents/com.bulat.sublet-hunt-ping.plist` (`StartInterval 900`) dispatch the workflow every 15 min via `gh workflow run`; no token is stored (uses the keychain `gh` login), and the scrape still runs on GitHub's runners so the Mac need only be awake ~1s. Logs to `~/Library/Logs/sublet-hunt-ping.log`. **The user explicitly does not want Mac reliance — remove this the moment the cron works:** `launchctl bootout gui/$(id -u)/com.bulat.sublet-hunt-ping`. Gotcha: `launchctl load` returns `Load failed: 5: Input/output error` when the job is already registered — that error is harmless; check with `launchctl print gui/$(id -u)/com.bulat.sublet-hunt-ping`.
11. **Region mis-routing on cross-mentions (minor, pre-existing).** `filter._assign_region` returns the *first* region whose neighborhood keyword appears anywhere in the text (incl. body), Manhattan first. A Brooklyn listing whose body says "20 min to Chelsea" can land in the Manhattan section. Cosmetic (affects the digest section, not whether a listing shows); more visible now with ~104 matches. Not fixed this session.

---

## Common tasks

| Task | How |
|---|---|
| Change budget / move-in / bedrooms | Edit constants at top of `config.py` |
| Add/remove neighborhoods | Edit `REGIONS` in `config.py` (drives filtering + email section grouping) |
| Add/remove SpareRoom areas | Edit `SPAREROOM_AREAS` — path format `borough/neighborhood`; verify the URL returns listings first |
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
