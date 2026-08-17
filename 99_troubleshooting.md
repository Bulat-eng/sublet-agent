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
