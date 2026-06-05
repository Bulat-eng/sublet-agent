# Troubleshooting & Lessons

Append lessons here as scrapers break and we patch them. Each entry should be:
- **Date** + **what broke** + **how we fixed it** + **how to detect it next time**.

---

## Known fragile spots (be ready)

| Source | Fragility | First sign of breakage |
|---|---|---|
| Craigslist | CSS class names occasionally change (e.g. `li.cl-static-search-result`) | All searches return 0 results; logs show 200 status but empty `out` |
| Listings Project | URL pattern + card markup; their site redesigns ~yearly | LP fetch returns 0 listings; check page HTML manually |
| SpareRoom | Listing card CSS class evolves (`.listing-result` may rename) | Fewer listings than expected; manual page check shows ads exist |
| Reddit (PRAW) | Reddit API changes are rare but they're aggressive about rate limits | `praw.exceptions.RedditAPIException`; 429 in logs |
| Ohana | Bubble.io regenerates selector classes on deploy | Playwright finds 0 cards; check `liveohana.ai/sublet/new-york-city` |
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

### 2026-06-05 — Out-of-area listing (Hamilton Heights) routed to Manhattan channel
- **What broke:** A SpareRoom listing in Hamilton Heights (not in our neighborhood list) was pushed to the Manhattan Telegram channel instead of being rejected.
- **Symptom in logs:** Filter keeps a listing and `_assign_region` returns `manhattan` for text that has no real Manhattan neighborhood in it.
- **Root cause:** `filter._assign_region` matched neighborhood keywords as raw substrings (`hood in text_low`). The abbreviation `"les"` (Lower East Side) is a substring of common words — "stain**les**s", "wire**les**s", "tab**les**" — and `"lic"` (Long Island City) hides inside "po**lic**e". SpareRoom scrapes *all* of NYC and leans entirely on the filter for area, so these got mis-routed rather than dropped.
- **Fix:** Match neighborhoods as whole words/phrases with `\b(?:...)\b` (`_hood_regex` in `filter.py`, precompiled per region). Verified Hamilton Heights/Harlem/Washington Heights/Inwood now reject while LES/LIC/Park Slope/etc. still route.
- **How to detect earlier next time:** If an out-of-area listing slips through, run `python -c "from filter import _assign_region; print(_assign_region('<card text>'))"` to see which keyword matched. Be wary of any short abbreviation (`les`, `lic`, `fidi`, `noho`) when adding new keywords.
