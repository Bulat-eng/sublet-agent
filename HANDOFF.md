# Sublet Agent — Handover

Live and running on **GitHub Actions** (free). This doc covers what it does, how it's wired, what changed most recently, and the open threads.

_Last updated: 2026-08-21 — **coverage session**: the search area doubled (30 → **66 neighborhoods**, 4 → **6 regions**), the Bed-Stuy SpareRoom gap was closed, and **CI was added** (`test_regions.py` + config integrity, green on every PR). Released as `v0.7.0` + `v0.7.1`, PR #1, squash-merged `e40b438`. **The cron is FIXED** — `schedule` now accounts for 25 of the last 40 runs (open item #1 closed); the Mac-side pinger is therefore removable (item #10). The local repo also **moved to `~/Developer/sublet-agent`** (macOS TCC blocks `~/Documents`). Previous entry: 2026-08-20 — **outage + migration session**: the agent went silent 2026-08-15 (GitHub Actions free minutes exhausted, not a code bug). Repo was migrated to a **new public repo** with rewritten history, Gmail credentials were regenerated, and email delivery is verified working. (At the time, the `schedule` trigger had never fired on the new repo — **since resolved, see item #1**.) Previous entry: 2026-08-16 — diagnostic session only, **no code changes**: traced why Ohana digest prices don't match the prices on the listing pages. Found a real bug in `sources/ohana.py` (left unfixed at the user's request — see "Last session" below and open item #8). Last **code** change was still 2026-07-24 (CHANGELOG `[0.6.0]`: lowered budget to $1,800 + removed New Jersey), released as `v0.6.0`, PR #13, merge `2dda848`._

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
sources/spareroom.py        → Per-neighborhood SEO area pages (config.SPAREROOM_AREAS),
                              PLUS a search-endpoint fallback (config.SPAREROOM_SEARCH_QUERIES)
                              for areas with no SEO page. Tiles parsed from their
                              data-listing-* attributes; permalinks rebuilt from listing id.
sources/reddit.py           → Public RSS; sublet-keyword filter + "seeker" detection +
                              direct-rental rescue (priced non-sublet posts on housing subs).
sources/ohana.py            → liveohana.ai public Bubble Data API (plain HTTP, no browser).
                              Live NYC-area listings ≤ MAX_RENT, cursor-paginated; Prime-lease
                              (straight rentals) kept & flagged "direct rental, not a sublet".
.github/workflows/hunt.yml  → cron (7,22,37,52 — off the congested :00/:15/:30/:45
                              slots) + workflow_dispatch + state.db commit-back
                              (rebases + retries on concurrent runs).
.github/workflows/ci.yml    → PR + push-to-main checks: module imports, region-routing
                              tests, config integrity. Ignores state.db pushes so the
                              bot's ~96 daily state commits don't each trigger a run.
test_regions.py             → 30 region-routing cases. No pytest — run it directly.
                              RE-RUN AFTER ANY `REGIONS` EDIT (ordering is load-bearing).
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
- **Neighborhoods:** **65 areas across 6 regions** (was 30 / 4), each a labelled section in the digest:
  | Region | Emoji | Covers |
  |---|---|---|
  | `midtown` | 🟧 | ~34th–59th: Theater District, Hudson Yards, Garment District, Koreatown, Herald Sq, Midtown East/South, Sutton Place, Turtle Bay, Tudor City, Murray Hill |
  | `midtown_to_fidi` | 🟦 | ~Canal–34th: Chelsea, Flatiron, Gramercy, Kips Bay, NoMad, Rose Hill, Union Sq, Meatpacking, Stuy Town, Peter Cooper, the Villages, Alphabet City, NoHo/Nolita/Little Italy/SoHo, Hudson Sq, Bowery, LES, Co-op Village, Chinatown, Two Bridges |
  | `fidi` | 🟥 | Financial District, Battery Park City, WTC, Civic Center, Seaport, Tribeca |
  | `north_brooklyn` | 🟩 | Greenpoint, Williamsburg (+ east/north/south/side variants, "los sures") |
  | `central_brooklyn` | 🟨 | Downtown BK, DUMBO, Brooklyn Heights, Vinegar Hill, Boerum/Cobble Hill, Carroll Gardens, Columbia St Waterfront, Fort Greene, Clinton Hill, Gowanus, Park Slope, South Slope, Prospect Heights, Bed-Stuy |
  | `south_brooklyn` | 🟪 | Windsor Terrace, Greenwood Heights, Prospect Lefferts Gardens, Crown Heights, Flatbush, Ditmas Park, Prospect Park South |

  **`REGIONS` dict order is load-bearing** — `filter._assign_region` returns the *first region* that matches, so `central_brooklyn` MUST precede `south_brooklyn` (a Park Slope listing naming "Flatbush Ave" would otherwise be mislabelled South). Covered by `test_regions.py`.
  (Queens removed 2026-07-11; New Jersey 2026-07-24; Bushwick 2026-08-21; **Sunset Park 2026-08-26**. Hell's Kitchen deliberately excluded.)
- **SpareRoom:** **41** neighborhood paths in `SPAREROOM_AREAS`, plus `SPAREROOM_SEARCH_QUERIES` for areas with no SEO page (currently just `"Bedford Stuyvesant"`).
- **⚠️ `MEDIANS` still covers only the original 13 neighborhoods**, so the "% vs median" line in the digest is silently skipped for all 36 newly-added areas — including Bed-Stuy and Crown Heights, the two the fall-hunt plan actually targets.

---

## Last session (2026-08-21) — coverage expansion + CI

**What the user asked for:** add the neighborhoods shown in four maps they pasted, then trim.
**How they wanted it done:** *plan first.* They pushed back twice on wasted effort — "Before
actually doing work, lets make a plan"; "I feel like We will be doing a lot of unnessesary
work." **Show the proposed list and wait for confirmation before editing `config.py`.**

### 1. Search area doubled — `v0.7.0`
30 → **66 neighborhoods**, 4 → **6 regions** (table under "Search criteria"). Manhattan was
split into three north-to-south bands at the user's request ("Midtown, Fidi, and Anything
between Midtown and FIdi"); Brooklyn was re-cut so Central holds the brownstone belt and
South is the true southern band. **Bed-Stuy + Crown Heights are now in** — closing the
neighborhood re-spec that had been pending from the 2026-06-16 strategy reframe.

Removed: **Bushwick**, Red Hook (never added), Hell's Kitchen (declined), and **Queens from
`OHANA_CITIES`** — a leftover from the 2026-07-11 region removal that was fetching Queens
listings only for the filter to discard them.

> ⚠️ Dropping Bushwick does not fully close it: `east williamsburg` is how a lot of
> Bushwick-border inventory markets itself, so some still arrives under that label.

### 2. Bed-Stuy SpareRoom gap closed — `v0.7.1`
The gap that `v0.7.0` left open. **The obvious diagnosis was wrong and cost time — read this
before touching `sources/spareroom.py`:**

- A missing SEO area page **302s to a location-disambiguation FORM that still returns HTTP
  200.** `requests` follows the redirect automatically, so "just follow the redirect" was
  never the fix, and any `status_code == 200` check reads "no such place" as "no listings".
- **The `<Area>, <Borough>` format in the redirect URL does not work.** `"Bed Stuy, Brooklyn"`,
  `"Bedford-Stuyvesant, Brooklyn"` and `"Bed-Stuy"` all disambiguate.
- **What works is the bare gazetteer name:** `"Bedford Stuyvesant"` — no hyphen, no borough
  — **326 results**. Now in `config.SPAREROOM_SEARCH_QUERIES`, consumed by `_fetch_search()`.
- **Trap: bare `"Seaport"` resolves to Redwood City, CALIFORNIA.** Always check where a
  search name lands before adding it. The filter drops off-target results, so the symptom is
  wasted requests, not bad email — it looks like a working query in the logs.
- **Only Bed-Stuy was recoverable.** South Slope, Turtle Bay, Midtown South, NoMad, Rose Hill,
  Hudson Square, WTC, Herald Square, Peter Cooper Village and Cooperative Village have **no**
  usable search name and stay uncovered by SpareRoom (still reachable via CL/Reddit/Ohana/LP).

**Bug fixed along the way:** listing tiles carry `data-listing-*` attributes on *both* page
types. The old parser took the first anchor in a tile, which on search pages is a URL-encoded
tracking fragment → mangled links and unstable ids. Now parsed from the attributes, with the
permalink rebuilt as `/roommate/room_for_rent.pl?flatshare_id=<data-listing-id>`. **Verified
id-compatible with the 348 existing `sr_*` rows in `state.db`** (11/11 against a live page),
so no re-notification storm. Generic borough values ("Brooklyn") are discarded so `filter.py`
can derive a better hood; `"Bedford - Stuyvesant"` is collapsed to match the config keyword.

### 3. CI added
`.github/workflows/ci.yml` — module imports, `test_regions.py` (30 cases), and config
integrity (duplicate keywords across regions, non-lowercase keywords, malformed SpareRoom
paths). Each integrity check was **negative-tested** to confirm it actually fails on bad
input. Green on PR #1 in 9s.

### 4. Local repo moved out of `~/Documents`
Mid-session, macOS **TCC** revoked access to `~/Documents` (and `~/Desktop`, `~/Downloads`) —
every read failed `EPERM`, including `git`. This is a macOS privacy grant, *not* a Claude Code
sandbox issue (disabling the sandbox changed nothing). The repo now lives at
**`~/Developer/sublet-agent`**, which is outside TCC and needs no permission grant.
`~/Developer` and `~/Proff Development` are unprotected; `~/Library`, `~/.config` and dotfiles
are too (they hold more sensitive material than Documents does, so TCC's boundary is not a
sensitivity ranking). The launchd pinger was **unaffected** — it targets
`-R Bulat-eng/sublet-agent`, not a local path.

### 5. Git identity
No `user.name`/`user.email` was configured, so git derived
`Bulat Khalilrakhmanov <bulat@Bulats-MacBook-Air.local>` per-machine (three variants exist in
history). Checked before acting: that identity is **already on 20 commits in `main`**, so the
new commits added no fresh exposure and **no history rewrite was needed** — important given
that force-pushing does not purge orphaned commits from GitHub. Now set globally to
`Bulat-eng <272103303+Bulat-eng@users.noreply.github.com>`.
_Note: commit metadata still carries `bulat.k.dev@gmail.com` on 8 older commits. The August
scrub purged `milkypillow@gmail.com` from **file contents**, not from commit metadata. If that
address was also meant to be private, that is a separate — and much larger — cleanup._

**Verified in production:** first scheduled run on the merged SHA (`e40b438`, 19:08Z) succeeded
end-to-end — 11 CL listings → 5 kept (**0 "wrong area"**) → 1 new → `Gmail SMTP: digest sent`.

---

## Previous session (2026-08-20) — outage recovery + repo migration

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

1. **✅ CRON — RESOLVED 2026-08-21.** The `schedule` trigger now fires: **25 of the last 40
   runs are `event=schedule`** (it was 0 across 2+ days). The fix was the previous session's
   unverified change — moving the cron off the oversubscribed `:00/:15/:30/:45` slots to
   `7,22,37,52` (`aac53c2`), which both re-registers the schedule and dodges the slots GitHub
   drops first under load. **Caveat:** it is still throttled — real firings are ~30–50 min
   apart, not 15. That is far better than the "every 2–4h" in older notes, and worlds better
   than never. No further action needed unless cadence regresses; the escalation ladder
   (delete/re-add `hunt.yml`, rename to `hunt2.yml`, external pinger, GitHub Support) is
   preserved in the 2026-08-20 section if it does.
2. **Node 20 action deprecation — RESOLVED.** `hunt.yml` now pins `actions/checkout@v6.0.3` + `actions/setup-python@v6.2.0`.
3. **First-run notification burst — RESOLVED (2026-07-30).** The anticipated big first digest went out and the system is now in **steady state**: dedup keeps each run small and per-source volume has settled (LP is now a ~20-listing weekly-Wednesday pulse — see "Last session (2026-07-30)"). No per-run cap was added (user wanted it uncapped) and none has proven necessary. Verified healthy in production 2026-07-30. _(Original note: v0.5.0 widened coverage to ~104 matches — LP 0→372, Ohana +342 — and the first scheduled run emailed that whole backlog at once, as expected/accepted.)_
4. **SpareRoom area-URL dependency.** **42** hardcoded slugs in `SPAREROOM_AREAS`, all
   verified HTTP 200 on 2026-08-21. A renamed path does **not** 404 — it **302s to a
   disambiguation form that returns 200**, so it fails *silently*. `_fetch_search()` detects
   that page ("several possible matches") and logs a warning; the area-page path does not.
   Ten areas have no SEO page and no usable search name (listed in the 2026-08-21 section) —
   Seaport among them, and bare `"Seaport"` searches resolve to **California**.
5. **Cadence gating is now live.** With the cron fixed (item #1) and the pinger still
   running, ticks arrive every ~15 min — shorter than the 30m SpareRoom / 6h Listings
   Project cadences, so `SOURCE_CADENCE_MINUTES` is actively skipping sources rather than
   being dormant insurance. Expect `skipped (Nm since last run < Xm cadence)` lines in run
   logs; that is correct behaviour, not a fault. It does mean **a given run may not exercise
   the source you're debugging** — check the log before concluding a scraper is broken.
6. **Remaining off sources:** **LeaseBreak** (Phase 2, Cloudflare-protected → needs Playwright, skeleton not written) and **Facebook** (shelved / opt-in). Ohana is now **on** (Phase 1, public API — no Playwright). See README.
7. **Ohana coverage caveats.** Only listings with a populated `min_rent_number` are fetched — ~23 price-unknown ones are excluded by the server-side price ceiling (mention if the user ever wants them, flagged). City labels `Manhattan`/`Bronx` return nothing (Manhattan uses `New York`), so they're intentionally omitted from `OHANA_CITIES`. If the public Data API is ever disabled, Ohana would need the Playwright approach after all — detect via `[Ohana] HTTP 4xx/5xx` or a drop to 0 results.
8. **⚠️ Ohana digest prices can be wrong / over budget (diagnosed 2026-08-16, NOT fixed).** Three causes, detailed in "Last session (2026-08-16)". Proposed fix, in priority order — the user deferred all of it:
   1. **Read the `room` object** (`/api/1.1/obj/room`, filter `listing_custom_product` in `[listing ids]`, batch ~40 ids per call — ~7 calls for the current 278). Price from the real room instead of the listing rollup, and budget-filter on that. ~30 lines in `sources/ohana.py`. Fixes cause 1 outright.
   2. **Flag variable-pricing listings** in the digest ("price varies by term — verify on site") when any room has `variable_pricing__boolean`. Trivial; mitigates cause 2. Can't be fully fixed without emulating the booking widget.
   3. **Store price in `seen` + re-check known listings** each run — schema migration in `db.py` plus a re-fetch loop in `main.py`. Fixes cause 3 and would enable "price dropped" alerts. Bigger job; deferred.
9. **⚠️ A GREEN RUN DOES NOT MEAN EMAIL WAS SENT.** `main.py` exits 0 after a delivery failure, so the workflow shows **success** while silently sending nothing — exactly how a broken digest can go unnoticed for days. It does correctly skip marking listings as seen on failure, so nothing is lost and they retry next run. **Proposed fix (offered, not yet approved): make delivery failure fail the run** so it shows red. To spot it manually, grep a run log for `Gmail SMTP` / `Notification failed`.
10. **🟡 Mac-side launchd pinger — NOW REMOVABLE (item #1 is fixed).** The user
    **explicitly does not want Mac reliance**, and the cron works again as of 2026-08-21, so
    this crutch has served its purpose. It is still running (~every 15 min) and currently
    *supplements* the throttled cron, which is why observed cadence looks tighter than
    `schedule` alone. **Decide with the user: remove it, or keep it for tighter timing.**
    Remove with `launchctl bootout gui/$(id -u)/com.bulat.sublet-hunt-ping`, then delete
    `~/.local/bin/sublet-hunt-ping.sh` and `~/Library/LaunchAgents/com.bulat.sublet-hunt-ping.plist`.
    Files: script + LaunchAgent (`StartInterval 900`), no token stored (keychain `gh` login),
    logs to `~/Library/Logs/sublet-hunt-ping.log`. Gotcha: `launchctl load` returns
    `Load failed: 5: Input/output error` when already registered — harmless; check with
    `launchctl print gui/$(id -u)/com.bulat.sublet-hunt-ping`.
11. **Region mis-routing on cross-mentions (minor, pre-existing).** `filter._assign_region` returns the *first* region whose neighborhood keyword appears anywhere in the text (incl. body), Manhattan first. A Brooklyn listing whose body says "20 min to Chelsea" can land in the Manhattan section. Cosmetic (affects the digest section, not whether a listing shows). **Partly mitigated
    2026-08-21:** the ordering that matters most is now deliberate and test-covered —
    `central_brooklyn` precedes `south_brooklyn` so "Flatbush Ave" cross-street mentions
    route correctly (`test_regions.py`). The general cross-borough case remains: Manhattan
    regions are checked first, so a listing saying "Brooklyn Chinatown" lands in
    `midtown_to_fidi`.
12. **⚠️ "Brooklyn Chinatown" leaks removed Sunset Park listings (opened 2026-08-26).** Sunset
    Park was dropped from `REGIONS` on 2026-08-26, but `"chinatown"` is still a
    `midtown_to_fidi` keyword (for Manhattan Chinatown, which IS wanted). A Sunset Park
    listing marketed as "Brooklyn Chinatown" therefore still passes the hard area filter and
    arrives in the digest labelled Manhattan. No longer cosmetic — it admits listings the
    user asked to exclude. Fix would be a negative match on `"brooklyn chinatown"` in
    `filter._assign_region`, ahead of the region scan. **Not implemented — ask first.**

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
| **Run the region tests (after ANY `REGIONS` edit)** | `.venv/bin/python test_regions.py` — 30 cases, no pytest needed |
| Add a SpareRoom area | Add to `SPAREROOM_AREAS`; **verify it returns HTTP 200 first** — a bad path 302s to a form that still returns 200 |
| Cover an area with no SpareRoom SEO page | Add the **bare gazetteer name** to `SPAREROOM_SEARCH_QUERIES`; confirm where it resolves (`"Seaport"` → California) |
| Debug why a listing routed somewhere | `python -c "from filter import _assign_region; print(_assign_region('<card text>'))"` |
| Deploy a change | PR into `main` (agent runs from `main` HEAD); cron picks it up next tick |
| Roll back a bad release | `git revert -m 1 <merge-sha> && git push origin main` |
| Trigger a run manually | `gh workflow run hunt.yml -R Bulat-eng/sublet-agent` (or Actions tab → Run workflow) |
| Cut a release | Update `CHANGELOG.md`, `git tag vX.Y.Z && git push origin vX.Y.Z` (see README) |

---

## Run / test locally

```bash
cd ~/Developer/sublet-agent          # moved out of ~/Documents 2026-08-21 (macOS TCC)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # fill in your own secrets — never commit it
python main.py            # full run
python test_regions.py               # region routing (fast, no network)
python -m sources.spareroom          # test a single source
python -m sources.listings_project   # LP: /sublets + /rentals, all pages (~50s)
python -m sources.ohana              # Ohana: Live NYC listings ≤ MAX_RENT (~9s)
```

Living docs: `99_troubleshooting.md` (append lessons as scrapers break), `CHANGELOG.md` (releases), `README.md` (setup).
