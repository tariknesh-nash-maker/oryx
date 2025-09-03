import os
import json
import argparse
import re
import time
from typing import Dict, List
from datetime import datetime, timedelta
from dateutil import tz
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Try importing user's real digest generator first
_generate_digest = None
try:
    from oryx_core.digest import generate_digest as _generate_digest  # type: ignore
except Exception:
    try:
        from oryx_digest import generate_digest as _generate_digest  # type: ignore
    except Exception:
        pass

def generate_digest(countries, hours=24, verified_only=True):
    if _generate_digest is None:
        from oryx_digest import generate_digest as fallback_generate
        return fallback_generate(countries, hours=hours, verified_only=verified_only)
    return _generate_digest(countries, hours=hours, verified_only=verified_only)

def load_channels_config():
    # Default mapping includes the new 'news-ctrl-eur' channel
    default_map = {
        "news-ame": ["Benin","Morocco","Côte d’Ivoire","Senegal","Tunisia","Burkina Faso","Ghana","Liberia","Jordan"],
        "news-ctrl-eur": ["Austria","Bosnia and Herzegovina","Czech Republic","Malta","Serbia","Slovakia"]
    }
    raw = os.environ.get("ORYX_CHANNELS_JSON")
    if not raw:
        return default_map
    try:
        parsed = json.loads(raw)
        # simple validation
        assert isinstance(parsed, dict)
        for k,v in parsed.items():
            assert isinstance(k, str)
            assert isinstance(v, list)
        return parsed
    except Exception as e:
        print(f"[WARN] Failed to parse ORYX_CHANNELS_JSON, using default. Error: {e}")
        return default_map

# ---------- Robust channel handling & dedupe ----------
ID_RE = re.compile(r'^[CG][A-Z0-9]{8,}$')  # Slack channel/group IDs

def _resolve_channel_id(client: WebClient, name: str) -> str | None:
    """Return channel ID for a given channel name the bot can see, else None."""
    name = name.lstrip("#")
    types = "public_channel,private_channel"
    cursor = None
    try:
        while True:
            resp = client.conversations_list(types=types, limit=1000, cursor=cursor)
            for ch in resp.get("channels", []):
                if ch.get("name") == name:
                    return ch.get("id")
            cursor = resp.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break
    except SlackApiError as e:
        print(f"[WARN] conversations_list failed: {e.response.get('error')}")
    return None

def _dedupe_targets(client: WebClient, channels_map: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Merge duplicate targets if the same channel appears by name and by ID.
    Returns mapping of normalized targets -> merged country list.
    Normalized target = channel ID if resolvable, else '#name' fallback.
    """
    out: Dict[str, List[str]] = {}
    for key, countries in channels_map.items():
        if ID_RE.match(key):
            target = key  # already an ID
        else:
            cid = _resolve_channel_id(client, key)
            target = cid if cid else f"#{key.lstrip('#')}"
        if target in out:
            seen = set(out[target])
            out[target].extend([c for c in countries if c not in seen])
        else:
            out[target] = list(countries)
    return out

def _already_posted_recently(client: WebClient, target: str, text: str, minutes: int = 180) -> bool:
    """
    True if an identical message exists in the last N minutes.
    Requires channels:history / groups:history for the given channel type.
    """
    # Resolve to channel ID for history
    cid = target
    if not ID_RE.match(cid):
        resolved = _resolve_channel_id(client, target.lstrip('#'))
        if not resolved:
            return False
        cid = resolved
    try:
        oldest = str(time.time() - minutes * 60)
        hist = client.conversations_history(channel=cid, oldest=oldest, limit=50)
        want = text.strip()
        for m in hist.get("messages", []):
            if m.get("text", "").strip() == want:
                return True
    except SlackApiError as e:
        # If we lack scopes, don't block sending; just warn.
        print(f"[WARN] conversations_history failed: {e.response.get('error')}")
    return False

def post_to_slack(channel_target: str, text: str, bot_token: str, dedupe_minutes: int = 180):
    client = WebClient(token=bot_token)

    # Idempotency guard
    if _already_posted_recently(client, channel_target, text, minutes=dedupe_minutes):
        print(f"[SKIP] Duplicate within {dedupe_minutes}m: {channel_target}")
        return

    # Post using ID if given/resolved, else '#name' fallback
    target = channel_target
    if not ID_RE.match(target):
        cid = _resolve_channel_id(client, channel_target)
        target = cid if cid else f"#{channel_target.lstrip('#')}"

    try:
        client.chat_postMessage(channel=target, text=text, mrkdwn=True)
        print(f"[OK] Posted to {channel_target} ({target})")
        return
    except SlackApiError as e:
        err = e.response.get("error")
        print(f"[ERROR] Slack API error for {channel_target}: {err}")
        if err in {"channel_not_found", "not_in_channel"}:
            print("[HINT] If using an ID, do NOT prefix with '#'. If using a name, invite the bot or grant 'channels:read'/'groups:read' and reinstall.")
        return
    except Exception as e:
        print(f"[ERROR] Failed to post to {channel_target}: {e}")

def build_message(countries, local_tz_name):
    hours = int(os.environ.get("ORYX_HOURS", "24"))
    verified_only = os.environ.get("ORYX_VERIFIED_ONLY", "1").lower() not in ("0","false","no")
    now_local = datetime.now(tz.gettz(local_tz_name))
    title = f"*Oryx :large_orange_circle: — {now_local.strftime('%A, %d %B %Y')}*"
    sub = f"_Countries: {', '.join(countries)}_\n"
    body = generate_digest(countries, hours=hours, verified_only=verified_only)
    return f"{title}\n{sub}\n{body}"

def main():
    parser = argparse.ArgumentParser(description="Oryx multi-channel daily poster")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously, posting daily at the given local time")
    args = parser.parse_args()

    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    if not bot_token:
        raise SystemExit("Missing SLACK_BOT_TOKEN")

    local_tz_name = os.environ.get("LOCAL_TZ", "Africa/Casablanca")
    post_at = os.environ.get("POST_AT_LOCAL_TIME", "08:30")  # HH:MM
    channels_map = load_channels_config()
    dedupe_minutes = int(os.environ.get("ORYX_DEDUP_MINUTES", "180"))

    client = WebClient(token=bot_token)
    deduped_targets = _dedupe_targets(client, channels_map)

    def run_once_all():
        for target, countries in deduped_targets.items():
            msg = build_message(countries, local_tz_name)
            post_to_slack(target, msg, bot_token, dedupe_minutes)

    if args.once:
        run_once_all()
        return

    if args.daemon:
        # Simple daily loop
        hh, mm = [int(x) for x in post_at.split(":")]
        while True:
            now = datetime.now(tz.gettz(local_tz_name))
            target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if target <= now:
                target = target + timedelta(days=1)
            sleep_s = (target - now).total_seconds()
            print(f"[INFO] Sleeping {int(sleep_s)}s until {target.isoformat()}")
            import time as _t; _t.sleep(sleep_s)
            run_once_all()
    else:
        # default behavior: just run once (useful for CI)
        run_once_all()

if __name__ == "__main__":
    main()
