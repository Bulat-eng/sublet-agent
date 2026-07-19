# 🏙️ NYC Sublet Agent

A free, every-15-minutes agent that hunts NYC sublets across Craigslist, Listings Project, SpareRoom, Reddit, and Ohana (liveohana.ai), and emails you a digest when something matches your criteria.

**Cost: $0/month.** Hosted on GitHub Actions (unlimited free minutes on a public repo) + Gmail SMTP + free Reddit API.

---

## What it does (Phase 1)

Every 15 minutes, it:
1. Scrapes **Craigslist NYC + NJ** (sublets + rooms categories)
2. Scrapes **Listings Project** (curated, weekly-refreshing housing listings)
3. Scrapes **SpareRoom NYC** (~2,300+ live ads, plain HTML)
4. Pulls recent **Reddit** posts from r/SublettingNYC, r/NYCapartments, r/AskNYC (filtered for sublet keywords)
5. Pulls **Ohana** (liveohana.ai) NYC listings via its public Bubble Data API (plain HTTP)
6. Filters by your budget, neighborhoods, and basic scam patterns
7. Deduplicates against the persistent `state.db` (committed back to the repo)
8. Emails any new matches to you as a single region-grouped HTML digest (Gmail SMTP)

**Phase 2** (commented out, ready to enable): LeaseBreak via Playwright.
**Facebook groups** — evaluated and shelved: automation risks the account, and manual feeding adds no value over reading the post yourself. See `CHANGELOG.md`.

---

## Setup

### 1. Tweak your preferences

Edit `config.py`:

```python
MAX_RENT = 2000
EARLIEST_MOVE_IN = "2026-06-15"
LATEST_MOVE_IN   = "2026-09-30"
REGIONS = { ... }   # neighborhoods per region — add/remove as you like
```

### 2. Set up email delivery (Gmail App Password, 5 min, free)

The agent emails you the digest through a Gmail account using an **App Password**
(not your normal Gmail login password):

1. On the sending Gmail account, enable **2-Step Verification**
   (myaccount.google.com → Security).
2. Create an App Password at **myaccount.google.com/apppasswords** → name it
   "Sublet Agent" → **Create**. Copy the 16-character password (drop the spaces).
3. You'll add three values as GitHub Secrets in step 5:
   - `SENDER_EMAIL` — the Gmail that sends (a burner account is fine)
   - `GMAIL_APP_PASSWORD` — the 16-char password from above
   - `TARGET_EMAIL` — the inbox that receives the digest (can be the same address)

### 3. Reddit — nothing to do!

We use Reddit's public RSS feeds (`reddit.com/r/<sub>/new/.rss`), which need no app, no API key, no account. Skip ahead.

### 4. Push to a **public** GitHub repo

```bash
cd /Users/bulat/Documents/sublet-agent
git init -b main
git add .
git commit -m "Initial sublet-agent"
# Create a NEW public repo on github.com (e.g. "sublet-agent"), then:
git remote add origin https://github.com/<your-username>/sublet-agent.git
git push -u origin main
```

**Important: it must be a PUBLIC repo.** GitHub Actions only gives unlimited free minutes on public repos. Private repos cap at 2,000 min/month, which isn't enough for every-15-min runs.

(No worries about secrets — they live in GitHub Secrets, not the code.)

### 5. Add secrets in GitHub

Go to your repo → **Settings → Secrets and variables → Actions → New repository secret**, and add:

| Name | Value |
|---|---|
| `SENDER_EMAIL` | the sending Gmail address (from step 2) |
| `GMAIL_APP_PASSWORD` | the 16-char app password (from step 2) |
| `TARGET_EMAIL` | the inbox that receives the digest |

### 6. Test it manually

In your GitHub repo → **Actions tab → sublet-hunt workflow → Run workflow**. Wait ~1 min for it to finish. Check your inbox.

After the first successful run, the cron schedule will fire every 15 min automatically.

---

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Fill in .env yourself — never commit it (it's in .gitignore)
python main.py
```

Test individual sources:
```bash
python -m sources.craigslist
python -m sources.listings_project
python -m sources.spareroom
python -m sources.reddit
python -m sources.ohana
```

Test the email digest (needs SENDER_EMAIL + GMAIL_APP_PASSWORD in `.env`):
```bash
python -m notifier --test
```

---

## Releasing & rolling back

The agent runs from `main` HEAD — every cron tick checks out whatever is on `main`. Releases are tracked with git tags + `CHANGELOG.md`, and there's always a tagged known-good commit to return to.

**Cutting a release**
1. Land changes on `main` (via PR) and update `CHANGELOG.md`.
2. Tag and push: `git tag v0.X.0 && git push origin v0.X.0`
3. (Optional) Create a GitHub Release from the tag using the changelog notes.

**Rolling back a bad release**

Because runs always use `main` HEAD, roll back by putting a known-good commit back on `main` — *without* rewriting history (the bot auto-commits `state.db` to `main`):

```bash
git revert -m 1 <merge-commit-sha>   # undo the release merge as a new commit
git push origin main                 # next cron run (≤15 min) uses the reverted code
```

To inspect or run a known-good version directly, check out its tag (e.g. `git checkout v0.1.0`). Avoid `git reset --hard` / force-push on `main`.

---

## Enabling Phase 2 (LeaseBreak)

LeaseBreak uses Playwright (headless browser) because it's Cloudflare-protected.
(Ohana was originally slated for Phase 2 too, but it exposes a public Data API,
so it runs over plain HTTP in Phase 1 — no Playwright.)

1. In `config.py`, uncomment:
   ```python
   ENABLED_SOURCES += ["leasebreak"]
   ```
2. In `.github/workflows/hunt.yml`, uncomment the **"Install Playwright + Chromium"** step.
3. Implement `sources/leasebreak.py` (skeleton not included in Phase 1).
4. Push.

Playwright adds ~30s per run — still well within GitHub Actions free tier.

---

## Files

| File | Purpose |
|---|---|
| `main.py` | Orchestrator — one run per GitHub Actions cron tick |
| `config.py` | Your preferences (rent, neighborhoods, move-in window) |
| `db.py` | SQLite dedup, committed back to repo as `state.db` |
| `filter.py` | Hard/soft/scam filters |
| `models.py` | `Listing` dataclass |
| `notifier.py` | Email-only: region-grouped HTML digest via Gmail SMTP |
| `sources/craigslist.py` | CL NYC + NJ sublets/rooms |
| `sources/listings_project.py` | listingsproject.com NYC |
| `sources/spareroom.py` | spareroom.com NYC |
| `sources/reddit.py` | PRAW for sublet subreddits |
| `sources/ohana.py` | liveohana.ai NYC listings via public Bubble Data API |
| `.github/workflows/hunt.yml` | GitHub Actions cron + state commit |

---

## Living docs

- `99_troubleshooting.md` — append lessons as scrapers break and we patch them
