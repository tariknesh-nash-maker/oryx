# app_cli.py
import os, datetime as dt, subprocess, sys
from dotenv import load_dotenv
import requests

from summarizer import build_oryx_digest
from slack_blocks import build_blocks
from feeds import COUNTRIES

load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def _git_sha_short():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"]).decode().strip()
    except Exception:
        return "no-git"

def post_to_slack(blocks):
    resp = requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks})
    print(f"[SLACK] status={resp.status_code}, body={resp.text[:200]}")
    if resp.status_code != 200:
        sys.exit(1)

def main():
    if not SLACK_WEBHOOK_URL:
        sys.exit("Missing SLACK_WEBHOOK_URL in env/secrets.")
    today = dt.date.today().strftime("%A, %d %B %Y")
    sha = _git_sha_short()
    print(f"[ORYX] Starting run @ {sha}")
    digest = build_oryx_digest(COUNTRIES)
    blocks = build_blocks(title=f"Oryx 🟠 — {today} (sha:{sha})", digest=digest)
    post_to_slack(blocks)
    print("[ORYX] Done.")

if __name__ == "__main__":
    main()
