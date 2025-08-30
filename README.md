# Oryx 🟠 — Daily OGP News (Streamlit)

A lightweight app that aggregates **last-24h, OGP-relevant news** for 9 countries:
Benin, Morocco, Côte d’Ivoire, Senegal, Tunisia, Burkina Faso, Ghana, Liberia, Jordan.

## Run locally
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # optional if you want Slack share
streamlit run app.py
