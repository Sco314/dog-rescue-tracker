# 🐕 Dog Rescue Scraper & Tracker

A Python-based system for tracking dogs across multiple rescue organizations, calculating fit scores, and sending notifications when good matches appear.

**🚀 Runs automatically on GitHub Actions - no server needed!**

## Features

- **Multi-Rescue Scraping**: Scrapes Doodle Rock, Doodle Dandy, and Poodle Patch rescues
- **Fit Score Calculation**: Automatically scores dogs based on your preferences
- **Change Detection**: Tracks when dogs are added, removed, or change status
- **Email Notifications**: Alerts for new dogs, watch list changes, and high-fit dogs becoming available
- **Predictive Analytics**: Estimates time-to-adoption based on historical data
- **SQLite Database**: Stored in the repo, persists between runs
- **GitHub Actions**: Runs every 4 hours automatically

---

## 🚀 GitHub Setup (Recommended)

### Step 1: Create Your Repository

1. Go to [github.com/new](https://github.com/new)
2. Name it `dog-rescue-tracker` (or whatever you like)
3. Make it **Private** (your email will be in secrets)
4. **Don't** initialize with README
5. Click "Create repository"

### Step 2: Upload the Files

**Option A - Web Upload:**
1. Unzip `dog-rescue-scraper.zip` on your computer
2. On your new repo page, click "uploading an existing file"
3. Drag ALL the files/folders into the browser (including `.github` folder)
4. Commit

**Option B - Command Line:**
```bash
unzip dog-rescue-scraper.zip
cd dog-rescue-scraper
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/dog-rescue-tracker.git
git branch -M main
git push -u origin main
```

### Step 3: Add Email Secrets

1. Go to your repo → **Settings** → **Secrets and variables** → **Actions**
2. Click "New repository secret" and add these three:

| Secret Name | Value |
|-------------|-------|
| `SENDER_EMAIL` | Your Gmail address (e.g., `you@gmail.com`) |
| `SENDER_PASSWORD` | Gmail App Password (see below) |
| `RECIPIENT_EMAILS` | Comma-separated emails (e.g., `you@gmail.com,spouse@gmail.com`) |

#### Getting a Gmail App Password:
1. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Select "Mail" and "Other (Custom name)" → name it "Dog Tracker"
3. Copy the 16-character password (looks like `xxxx xxxx xxxx xxxx`)
4. Use this as `SENDER_PASSWORD` (no spaces)

### Step 4: Run It!

1. Go to your repo → **Actions** tab
2. Click "Dog Rescue Scraper" workflow on the left
3. Click "Run workflow" → "Run workflow"
4. Watch it run! 🎉

**From now on, it runs automatically every 4 hours.**

---

## 📧 What You'll Get Notified About

- 🔔 **Watch List Alerts**: Drizzle, Kru, Nimbi, Zira, or Jojo change status
- 🆕 **New Dogs**: Any new dog with fit score ≥ 5
- 📢 **Status Changes**: High-fit dog goes Available or Pending

---

## ⚙️ Customization

### Edit Your Watch List

Edit `config.py` and change:
```python
WATCH_LIST_DOGS = [
  "Drizzle",
  "Kru", 
  "Nimbi",
  "Zira",
  "Jojo"
]
```

### Adjust Fit Score Weights

In `config.py`, tweak the `SCORING_WEIGHTS` to match your preferences.

### Change Schedule

Edit `.github/workflows/scrape.yml`:
```yaml
schedule:
  - cron: '0 */4 * * *'  # Every 4 hours
  # Other examples:
  # - cron: '0 */2 * * *'  # Every 2 hours
  # - cron: '0 8,12,18 * * *'  # 8am, noon, 6pm
```

---

## 📊 View Results

- **Actions tab**: See each run's output
- **dogs.db**: Download to view in SQLite browser
- **Run manually**: Click Actions → Run workflow anytime

---

## 🏃 Local Development (Optional)

If you want to run locally too:

```bash
pip install -r requirements.txt
python scraper.py --test      # Test run
python scraper.py --report    # View dogs
python analysis.py            # See analytics
```

---

## 📁 File Structure

```
dog-rescue-scraper/
├── scraper.py           # Main runner script
├── config.py            # Rescue URLs, scoring weights, watch list
├── database.py          # SQLite operations
├── models.py            # Dog and ChangeRecord classes
├── scoring.py           # Fit score calculation
├── notifications.py     # Email notification system
├── analysis.py          # Predictive analytics
├── scrapers/
│   ├── base_scraper.py  # Base scraper class
│   ├── poodle_patch.py  # Poodle Patch Rescue scraper
│   ├── doodle_rock.py   # Doodle Rock Rescue scraper
│   └── doodle_dandy.py  # Doodle Dandy Rescue scraper
├── dogs.db              # SQLite database (created on first run)
└── requirements.txt     # Python dependencies
```

---

## Fit Score Breakdown

| Criteria | Points |
|----------|--------|
| Weight >= 40 lbs | +2 |
| Non-shedding | +2 |
| Low shedding | +1 |
| Low/Medium energy | +2 |
| High energy | +1 |
| Good with kids | +1 |
| Good with dogs | +1 |
| Good with cats | +1 |
| Special needs | -1 |

**Max Score: 9 points**

A score of 5+ is considered a "good fit" for notifications.

## Troubleshooting

**Workflow not running?**
- Check Actions tab for error messages
- Verify secrets are set correctly (Settings → Secrets)

**No dogs found from Doodle Rock/Doodle Dandy?**
- These sites use heavy JavaScript
- GitHub Actions should handle this, but results may be limited
- Poodle Patch typically works best

**Not getting emails?**
- Check spam folder
- Verify Gmail App Password (not your regular password)
- Check Actions log for email errors

---

## Adding New Rescues

1. Create a new scraper in `scrapers/` based on existing ones
2. Add config to `RESCUES` in `config.py`
3. Import in `scrapers/__init__.py`
4. Add to `get_scraper()` in `scraper.py`

---

Made with ❤️ for finding the perfect furry family member
