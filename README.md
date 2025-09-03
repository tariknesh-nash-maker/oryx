
# Oryx — Multi‑Channel Daily Slack Digest (Updated)

This version adds **multi-channel** support so you can post separate daily digests for different country sets — including a new channel **`news-ctrl-eur`** for:
- Austria
- Bosnia and Herzegovina
- Czech Republic
- Malta
- Serbia
- Slovakia

It keeps your existing pipeline intact: if you already have a function that builds the digest, this wrapper will import and use it. If not, it falls back to a minimal placeholder so you can verify Slack delivery quickly.

---

## Quick Start

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set secrets (env vars)**
   - `SLACK_BOT_TOKEN` — your Slack Bot token (starts with `xoxb-...`)
   - `ORYX_CHANNELS_JSON` — JSON mapping of Slack channels to country lists. Example:
     ```json
     {
       "news-ame": ["Benin","Morocco","Côte d’Ivoire","Senegal","Tunisia","Burkina Faso","Ghana","Liberia","Jordan"],
       "news-ctrl-eur": ["Austria","Bosnia and Herzegovina","Czech Republic","Malta","Serbia","Slovakia"]
     }
     ```
   - (Optional) `POST_AT_LOCAL_TIME` — local time to send (HH:MM, 24h). Default: `08:30`.
   - (Optional) `LOCAL_TZ` — IANA timezone string. Default: `Africa/Casablanca`.

3. **Run once (local test)**
   ```bash
   python app.py --once
   ```

4. **Schedule (GitHub Actions)**  
   Add this repo to GitHub and keep the provided workflow at `.github/workflows/daily.yml`.  
   In your GitHub repo settings → **Secrets and variables → Actions**, add:
   - `SLACK_BOT_TOKEN`
   - `ORYX_CHANNELS_JSON`
   - (Optional) `POST_AT_LOCAL_TIME`
   - (Optional) `LOCAL_TZ`

---

## Plugging in your existing digest builder

If you already have a function in your code that assembles the daily Oryx digest, expose it as:

```python
# somewhere in your repo, e.g. oryx_core/digest.py
def generate_digest(countries: list[str], hours: int = 24, verified_only: bool = True) -> str:
    """Return a markdown string for Slack"""
    ...
```

This wrapper will try to import:
- `from oryx_core.digest import generate_digest` **then** `from oryx_digest import generate_digest`  
If neither exists, it uses the included **placeholder** (so you can test Slack delivery).

---

## Posting format

Each channel gets its own message with:
- A bolded title with date (local time)
- The country list included in the header for clarity
- The markdown digest body returned by your generator

---

## Files

- `app.py` — Orchestrates multi-channel digests and posts to Slack
- `oryx_digest.py` — Lightweight fallback digest generator (safe placeholder)
- `requirements.txt` — Minimal deps (`slack_sdk`, `pytz`, `python-dateutil`)
- `.github/workflows/daily.yml` — GitHub Actions to run daily on a schedule

---

## Notes on timezones

- The app converts the **local target time** to UTC and sleeps until then if `--daemon` is used. On GitHub Actions, it simply runs on a cron (UTC). Adjust the cron in `daily.yml` to match your preferred local time.

---

## Troubleshooting

- **Two versions running?** Ensure only one scheduler is active (either Actions or your server/cron).
- **Wrong Slack channel?** Confirm the channel name is correct and the bot is invited to that channel.
- **Empty digests?** Test locally with the placeholder first. Once confirmed, wire in your real `generate_digest`.

Enjoy!
