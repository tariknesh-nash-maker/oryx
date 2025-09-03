
import os
import json
import argparse
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

def post_to_slack(channel, text, bot_token):
    client = WebClient(token=bot_token)
    try:
        client.chat_postMessage(channel=f"#{channel}", text=text, mrkdwn=True)
        print(f"[OK] Posted to #{channel}")
    except SlackApiError as e:
        print(f"[ERROR] Slack API error for #{channel}: {e.response.get('error')}")
    except Exception as e:
        print(f"[ERROR] Failed to post to #{channel}: {e}")

def build_message(countries, local_tz_name):
    now_local = datetime.now(tz.gettz(local_tz_name))
    title = f"*Oryx :large_orange_circle: — {now_local.strftime('%A, %d %B %Y')}*"
    sub = f"_Countries: {', '.join(countries)}_\n"
    body = generate_digest(countries, hours=24, verified_only=True)
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

    def run_once_all():
        for channel, countries in channels_map.items():
            msg = build_message(countries, local_tz_name)
            post_to_slack(channel, msg, bot_token)

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
            import time; time.sleep(sleep_s)
            run_once_all()
    else:
        # default behavior: just run once (useful for CI)
        run_once_all()

if __name__ == "__main__":
    main()
