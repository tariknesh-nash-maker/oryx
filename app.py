import os
import streamlit as st
from dotenv import load_dotenv
from datetime import datetime
import requests

from feeds import COUNTRIES, FEEDS, REGIONAL_FEEDS, OGP_KEYWORDS
from fetch import collect

load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")  # optional

st.set_page_config(page_title="Oryx Daily — OGP News", page_icon="🟠", layout="wide")
st.title("Oryx 🟠 — Daily OGP News (last 24h)")

left, right = st.columns([2,1], gap="large")

with right:
    st.subheader("Filters")
    countries = st.multiselect("Countries", COUNTRIES, default=COUNTRIES)
    show_regional = st.checkbox("Include subregional/international context", value=True)
    st.caption("OGP keywords used for filtering:")
    st.code(", ".join(OGP_KEYWORDS), language="text")

    send_to_slack = st.checkbox("Send summary to Slack (optional)", value=False, help="Requires SLACK_WEBHOOK_URL in .env")

with left:
    st.subheader("Results")
    total = 0
    digest_lines = []

    for c in countries:
        urls = FEEDS.get(c, [])
        items = collect(urls, OGP_KEYWORDS)
        if not items:
            continue
        total += len(items)
        st.markdown(f"### {c}")
        for e in items[:12]:  # cap per country to keep UI light
            ts = e['published'].strftime("%Y-%m-%d %H:%M UTC") if e['published'] else ""
            st.markdown(f"- **{e['title']}** — [{e['link']}]({e['link']})  \n  <small>{ts}</small>", unsafe_allow_html=True)
            digest_lines.append(f"• {c}: {e['title']} — {e['link']}")

    if show_regional:
        reg_items = collect(REGIONAL_FEEDS, OGP_KEYWORDS)
        if reg_items:
            st.markdown("### Subregional / International")
            for e in reg_items[:12]:
                ts = e['published'].strftime("%Y-%m-%d %H:%M UTC") if e['published'] else ""
                st.markdown(f"- **{e['title']}** — [{e['link']}]({e['link']})  \n  <small>{ts}</small>", unsafe_allow_html=True)
                digest_lines.append(f"• Regional: {e['title']} — {e['link']}")

    if total == 0 and not reg_items:
        st.info("No items matched in the last 24 hours. Try widening keywords or deselecting filters.")

    st.write("---")
    st.caption(f"Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    if send_to_slack and SLACK_WEBHOOK_URL:
        if st.button("Send summary to Slack"):
            blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": f"*Oryx — Daily OGP News ({datetime.utcnow().strftime('%Y-%m-%d')})*"}}]
            if digest_lines:
                # Slack section blocks max ~3000 chars; join safely
                chunk = "\n".join(digest_lines)[:2800]
                blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk}})
            r = requests.post(SLACK_WEBHOOK_URL, json={"blocks": blocks}, timeout=20)
            if r.status_code == 200:
                st.success("Posted to Slack ✅")
            else:
                st.error(f"Slack error {r.status_code}: {r.text[:200]}")
    elif send_to_slack and not SLACK_WEBHOOK_URL:
        st.warning("Set SLACK_WEBHOOK_URL in your environment to enable Slack posting.")
