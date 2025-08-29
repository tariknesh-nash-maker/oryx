import os, datetime as dt
from dotenv import load_dotenv
import requests
from slack_blocks import build_blocks
from summarizer import build_oryx_digest

# Load env (local runs). In GitHub Actions we pass env via secrets.
load_dotenv()

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
if not SLACK_WEBHOOK_URL:
    raise SystemExit("Missing SLACK_WEBHOOK_URL in environment.")

COUNTRIES = [
    "Benin", "Morocco", "Côte d’Ivoire", "Senegal",
    "Tunisia", "Burkina Faso", "Ghana", "Liberia", "Jordan"
]

def post_to_slack(blocks):
    resp = requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks})
    if resp.status_code >= 400:
        raise RuntimeError(f"Slack webhook error {resp.status_code}: {resp.text}")

def main():
    today = dt.date.today().strftime("%A, %d %B %Y")
    digest = build_oryx_digest(COUNTRIES)
    blocks = build_blocks(title=f"Oryx 🟠 — {today}", digest=digest)
    post_to_slack(blocks)
    print("Posted Oryx digest to Slack.")

if __name__ == "__main__":
    main()

