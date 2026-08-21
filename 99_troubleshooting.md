# Troubleshooting & Lessons

Append lessons here as scrapers break and we patch them. Each entry should be:
- **Date** + **what broke** + **how we fixed it** + **how to detect it next time**.

---

## Known fragile spots (be ready)

| Source | Fragility | First sign of breakage |
|---|---|---|
| Craigslist | CSS class names occasionally change (e.g. `li.cl-static-search-result`) | All searches return 0 results; logs show 200 status but empty `out` |
| Listings Project | URL pattern + card markup; their site redesigns ~yearly (broke 2026-07) | LP fetch returns 0 listings; check page HTML manually |
| SpareRoom | Listing card CSS class evolves (`.listing-result` may rename) | Fewer listings than expected; manual page check shows ads exist |
| Reddit (PRAW) | Reddit API changes are rare but they're aggressive about rate limits | `praw.exceptions.RedditAPIException`; 429 in logs |
| Ohana | Public Bubble Data API; could be turned off or the `listing` type renamed | `[Ohana] HTTP 4xx/5xx` or 0 results; check `curl 'https://liveohana.ai/api/1.1/obj/listing?limit=1'` |
| Ohana (prices) | `min_rent_number` is a rollup, not the real room price — **known wrong**, see 2026-08-16 log entry | Silent: no log signal. Digest price ≠ price on the listing page |
| LeaseBreak | Cloudflare challenge bumps | 403 in logs; need to update Playwright stealth config |

---

## Common fixes

### "All sources return 0 listings"
Most likely a **rate limit / IP block**. Wait 30 min, try again. If GH Actions specifically gets blocked but local works, the site is fingerprinting the runner IP — add jitter, slow down, or move that source to local-only.

### "Telegram messages stopped arriving"
- Check the bot token didn't get rotated
- Check the bot wasn't blocked/deleted on your end
- Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are set as GitHub Secrets
- Manually call: `curl https://api.telegram.org/bot<TOKEN>/getMe` — should return ok=true

### "state.db merge conflicts in GitHub"
Caused by two workflow runs racing to commit. The `concurrency:` block in `hunt.yml` should prevent this, but if it happens:
```bash
git checkout main
git pull --rebase
# state.db is a binary blob; just keep "ours" or "theirs", either is recoverable
```

### "Reddit API: invalid_grant"
- `REDDIT_USER_AGENT` must be a real string (e.g. `"sublet-agent/0.1 by <your-reddit-username>"`)
- Reddit blocks generic UAs like "python-requests"

### "GitHub Actions cron not firing"
- GitHub disables scheduled workflows on repos with no activity for 60 days. Push any commit to re-enable.
- Cron can be delayed up to ~10 min under load — this is normal, not broken.

---

## Log

<!-- Add entries below as we hit issues -->

### YYYY-MM-DD — Template
- **What broke:**
- **Symptom in logs:**
- **Root cause:**
- **Fix:**
- **How to detect earlier next time:**

### 2026-08-16 — Ohana digest price ≠ price on the listing page (DIAGNOSED, NOT FIXED)
- **What broke:** Listings passed the budget filter and showed e.g. $1,489 / $1,585 in the digest; clicking through to liveohana.ai showed a much higher, over-budget price ($2,119).
- **Symptom in logs:** *None* — nothing errors. This is a silent correctness bug, which is why it went unnoticed. Only visible by comparing a digest price against the live page.
- **Root cause — three independent things, only the first is ours:**
  1. **`min_rent_number` is the listing-wide floor, not the price of a specific room.** `_price()` in `sources/ohana.py` reads it first. On multi-room listings it's the cheapest room; sometimes it's just stale. Of 278 listings currently ≤$1,800: 20 have >1 priced room, 13 have a `min_rent_number` that disagrees with their own cheapest room, and 12 pass the filter while containing a room over budget. Worst case seen live: `peaceful-room-with-private-entrance-in-carroll-gardens`, digest $1,498 vs cheapest real room $2,354.
  2. **Variable pricing is flagged on the room, not the listing.** `listing.dynamic_pricing_boolean` was `False` while `room.variable_pricing__boolean` was `True` — 51/278 (18%) are like this. For those the API rent is a base and the site quotes a term/date-dependent figure.
  3. **Hosts re-price frequently and we never re-check.** All 15 units at 7 Eldridge St were re-priced within 5 days of being emailed. `seen` stores only `id, url, source, seen_at` — no price — so the digest price is a permanent snapshot and a listing is never revisited.
- **Fix:** *Not applied* — user deferred (2026-08-16). Plan is in HANDOFF open item #8: read the room object for real per-room rents, flag variable-pricing listings in the digest, and (bigger) persist price in `seen` to re-check.
- **The thing worth knowing:** there is an undocumented **`room` object type** on the same Data API — `/api/1.1/obj/room`, filter `listing_custom_product` = listing `_id` (use `constraint_type: "in"` and batch ~40 ids per call). Fields: `rent_number` (renter-facing), `rent_earned_by_host_number`, `variable_pricing__boolean`, `type_of_place_option_type_of_place`. Also confirms **Ohana's fee is 7%**: `rent_earned_by_host_number` × 1.07 = `rent_number`, so the price we email is already fee-inclusive.
- **How to detect earlier next time:** price-correctness bugs are invisible in logs — you have to spot-check. Periodically diff a few digest prices against their live pages. A quick assertion worth adding: for each Ohana listing, compare `listing.min_rent_number` against `min(room.rent_number)` and warn on any mismatch. Generally: when a Bubble app exposes one object type, look for the related types before trusting a rollup field on the parent.

### 2026-07-19 — Listings Project silently returned 0 listings (site restructure)
- **What broke:** No LP listings had appeared in the digest for a while. The user noticed "I don't see any posts coming from Listings Project."
- **Symptom in logs:** `LP fetch 404`, then `[LP] 0 NYC listings`. The `except` in `fetch()` meant a bad URL degraded to an empty list instead of an error.
- **Root cause:** LP restructured their site. Old paths `/listings/housing/new-york`, `/listings/all` now 404. Current NYC index is `/real-estate/new-york-city` (paginated `?page=N`); listing detail URLs are `/listings/<slug>` (no numeric id in the URL — the stable id lives in the card's `data-listingid` attribute). The old regex `\/listings\/[^/]+/[^/]+/\d+` matched nothing.
- **Fix:** Rewrote `sources/listings_project.py` to parse the new card markup (anchor on `<h4>` title → climb to the ancestor holding `data-listingid`). Also normalized weekly/nightly rates to a monthly equivalent + flag, because LP quotes many short-term stays per day/week and they were being read as cheap monthly rent.
- **How to detect earlier next time:** A source that returns 0 for many consecutive runs is suspicious even when nothing errors. Sanity-check live with `python -m sources.listings_project`; if it's 404, open `https://www.listingsproject.com/real-estate/new-york-city` in a browser and re-derive the card selectors.

### 2026-07-19 — Added Ohana (liveohana.ai) via its public Bubble Data API
- **Note (not a break):** liveohana.ai is a Bubble.io app; everything renders client-side, so it was originally slated for Phase 2 (Playwright). But its **public Data API** (`/api/1.1/obj/listing`) returns structured JSON over plain HTTP — no browser needed — so it ships in Phase 1.
- **Gotchas found live:** rent is in `min_rent_number` / `max_rent_number` / `price_number` (monthly), not a single field; `neighborhood_geographic_address` is unreliable (a Williamsburg listing geocoded to Brisbane AU, an Astoria one to Oregon) so we trust it only when it resolves to NY and otherwise let the title carry the neighborhood; filter to `status = "Live"` or you get a flood of `Draft` rows.
- **Volume / coverage:** ~1,500 live NYC listings but only ~340 under $2,000. We constrain server-side to `min_rent_number < MAX_RENT+1` and paginate (cursor) through all matches — a plain "newest 100 of everything" wasted ~74% of the fetch on over-budget Manhattan listings and missed affordable Brooklyn ones. Constraint types are Bubble's exact strings: `equals`, `in`, `less than`, `is_empty` (there is no "less than or equal to"). Listings with an empty `min_rent_number` (~23) are excluded by the price constraint.
- **How to detect breakage:** `[Ohana] HTTP 4xx/5xx` or a sudden drop to 0 results. Probe with `curl 'https://liveohana.ai/api/1.1/obj/listing?limit=1'` — if that 404s or 403s, the Data API was disabled and Ohana would need the Playwright approach after all.

### 2026-06-05 — Out-of-area listing (Hamilton Heights) routed to Manhattan channel
- **What broke:** A SpareRoom listing in Hamilton Heights (not in our neighborhood list) was pushed to the Manhattan Telegram channel instead of being rejected.
- **Symptom in logs:** Filter keeps a listing and `_assign_region` returns `manhattan` for text that has no real Manhattan neighborhood in it.
- **Root cause:** `filter._assign_region` matched neighborhood keywords as raw substrings (`hood in text_low`). The abbreviation `"les"` (Lower East Side) is a substring of common words — "stain**les**s", "wire**les**s", "tab**les**" — and `"lic"` (Long Island City) hides inside "po**lic**e". SpareRoom scrapes *all* of NYC and leans entirely on the filter for area, so these got mis-routed rather than dropped.
- **Fix:** Match neighborhoods as whole words/phrases with `\b(?:...)\b` (`_hood_regex` in `filter.py`, precompiled per region). Verified Hamilton Heights/Harlem/Washington Heights/Inwood now reject while LES/LIC/Park Slope/etc. still route.
- **How to detect earlier next time:** If an out-of-area listing slips through, run `python -c "from filter import _assign_region; print(_assign_region('<card text>'))"` to see which keyword matched. Be wary of any short abbreviation (`les`, `lic`, `fidi`, `noho`) when adding new keywords.

---

## 2026-08-18 — All runs failing in 4s: GitHub Actions free-minutes exhausted

**Symptom:** every scheduled run `failure` after 4–5s, no logs, no step output.
`gh run view --log` returns "log not found" (the job never started, so there is
nothing to log). No emails since 2026-08-15.

**Root cause:** NOT a code bug. The job annotation (only visible via the API,
not in the runs list) said:

```bash
gh api repos/<owner>/<repo>/actions/runs/<run_id>/jobs --jq '.jobs[0].id'
gh api repos/<owner>/<repo>/check-runs/<job_id>/annotations
```

> The job was not started because recent account payments have failed or your
> spending limit needs to be increased.

Private repos draw from a **2,000 min/month** free allowance on GitHub Free.
Billing page showed `2,000 / 2,000 min used`. Growth in run volume caused it:
505 runs (Jun) → 843 (Jul) → 864 in the first 15 days of Aug. Adding Zumper and
Craigslist-sublets on 2026-07-27 also lengthened each run (sublet-agent averages
5.4 billable min/run vs bk-apartment-agent's 1.0), so sublet-agent alone was
77% of the spend.

**Gotcha that caused a wrong first diagnosis:** the Actions API returns max 100
runs per request. Without `--paginate` a month looks far smaller than it is.
Always use `gh api --paginate`. Also note GitHub rounds each job UP to a whole
billable minute.

**Fix applied:** made this repo **public** (public repos get unlimited free
Actions) and disabled bk-apartment-agent's workflow.

**Second gotcha — force-push does NOT remove secrets from GitHub.** After
rewriting history with `git filter-repo --replace-text` to purge a personal
email, the orphaned commits were still served by SHA:

```bash
gh api "repos/<owner>/<repo>/contents/config.py?ref=<old_sha>"
```

still returned the old content, and the old SHAs are discoverable because
workflow runs record them as `head_sha`. Going public would have re-exposed the
data. **The only reliable purge is a fresh repo**: rename the old one, create a
new one, push the rewritten history, verify old SHAs 404.

---

## SpareRoom: a 302 means the area page does not exist (2026-08-21)

When adding new `SPAREROOM_AREAS` paths, verify each one before committing it.
SpareRoom does **not** 404 for an unknown area — it 302-redirects to its generic
search endpoint, so a naive "did the request succeed?" check passes for paths
that will never return targeted listings.

```bash
curl -s -o /dev/null -w "%{http_code}" \
  "https://www.spareroom.com/rooms-for-rent/brooklyn/bed_stuy"
# → 302, i.e. NO area page
```

Only **HTTP 200** means a real SEO area page exists. Inspecting the redirect
target shows what's actually happening:

```bash
curl -s -o /dev/null -w "%{redirect_url}\n" \
  "https://www.spareroom.com/rooms-for-rent/brooklyn/bed_stuy"
# → .../roommate/search.pl?...&search=Bed%20Stuy%2C%20Brooklyn&...
```

Areas confirmed to have **no** SEO page: Bed-Stuy (every spelling tried —
`bed_stuy`, `bed-stuy`, `bedstuy`, `bedford_stuyvesant`, `bedford-stuyvesant`),
South Slope, Turtle Bay, Midtown South, NoMad, Rose Hill, Hudson Square, World
Trade Center, Herald Square, Peter Cooper Village, Cooperative Village, Seaport,
Hell's Kitchen, Times Square.

**Correction (same day, after implementing it).** The paragraph originally here
said the redirect proves the area "is searchable" and that following it would
recover Bed-Stuy. Both halves were wrong, and the details matter:

1. **`requests` already follows the redirect** (`allow_redirects=True` by
   default) and gets HTTP 200 — so "follow the redirect" was never the fix.
2. **The 200 page is a location-disambiguation FORM, not results.** It contains
   exactly one `/flatshare/` link ("post a room wanted ad") and the text
   "We found several possible matches for your search". Any scraper that trusts
   `status_code == 200` will silently return nothing here.
3. **The `<Area>, <Borough>` format shown in the redirect URL does not work.**
   `"Bed Stuy, Brooklyn"` disambiguates, and so do `"Bedford-Stuyvesant,
   Brooklyn"`, `"Bedford Stuyvesant, Brooklyn"` and `"Bed-Stuy"`.

**What actually works** is the bare, correctly-spelled gazetteer name — for
Bed-Stuy, `"Bedford Stuyvesant"` with no hyphen and no borough → **326 results**.
Implemented 2026-08-21 as `_fetch_search()` + `config.SPAREROOM_SEARCH_QUERIES`.

**Two traps when adding more search queries:**

- **Check where a name resolves before trusting it.** Bare `"Seaport"` returns
  listings in **Redwood City, California** (Friendly Acres, Redwood Village).
  The neighborhood filter drops them, so the damage is wasted requests rather
  than bad email — but it looks like a working query in the logs.
- **Detect the disambiguation page explicitly.** `_fetch_search()` checks for
  "several possible matches" and logs a warning, because a silent empty result
  is indistinguishable from "no listings today".

These names were each checked and have **no** usable search query, so SpareRoom
does not cover them at all: South Slope, Turtle Bay, Midtown South, NoMad, Rose
Hill, Hudson Square, World Trade Center, Herald Square, Peter Cooper Village,
Cooperative Village.

## SpareRoom tiles carry data-listing-* attributes — use them (2026-08-21)

Both page types render tiles as `<li class="listing-result">` with structured
attributes: `data-listing-id`, `-title`, `-neighbourhood`,
`-ad-rate-normalised` (+ `-period`). Parsing those beats scraping rendered text,
and it fixed a real bug — the visible anchor differs between page types
(`fad_click.pl` tracking redirect on SEO pages, `room_for_rent.pl` on search
pages), so the old text parser produced mangled URL-encoded hrefs on search
pages. The permalink is now rebuilt from the id:
`{BASE}/roommate/room_for_rent.pl?flatshare_id=<data-listing-id>`.

`data-listing-id` matches the ids the old URL-digit regex produced (verified
11/11 against a live page), so switching cost no dedup state — important, since
`state.db` held 348 `sr_*` rows that would otherwise all re-notify.

Two gotchas: `data-listing-neighbourhood` is sometimes just the borough
("Brooklyn"), which is worse than letting `filter.py` derive the hood from the
matched keyword — so generic values are discarded (`_GENERIC_HOODS`). And it
spaces out some hyphenated names ("Bedford - Stuyvesant"), which the parser
collapses so the config keyword matches.

## Neighborhood keywords: region ORDER is load-bearing (2026-08-21)

`filter._assign_region` iterates `config.REGIONS` in dict order and returns the
first **region** whose regex matches anywhere in the text — not the earliest
match position across all regions. So when a keyword in one region can appear
incidentally in another region's listings, the more specific region must come
first.

Concrete case: `flatbush` (South Brooklyn) also matches **"Flatbush Ave"**, a
cross street named in listings all over Park Slope and Prospect Heights. With
`central_brooklyn` ordered before `south_brooklyn`, those route correctly.
Reversing the order silently mislabels them. There is a routing test for this —
re-run it after any change to `REGIONS`.

Related whole-word gotchas already handled by `_hood_regex`: `les` must not match
"stainless"/"wireless", `lic` must not match "police". Add new short aliases with
care. Unfixable by regex: `murray hill` matches **Murray Hill, Queens** too.
