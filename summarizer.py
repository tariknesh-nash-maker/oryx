# summarizer.py
import sys
from feeds import FEEDS, REGIONAL_FEEDS, OGP_KEYWORDS
from fetch import collect

def _as_bullets(entries, prefix="• "):
    bullets = []
    for e in entries[:12]:
        title = (e["title"] or e["link"]).strip()
        link = e["link"]
        bullets.append(f"{prefix}{title} — <{link}|source>")
    return bullets

def build_oryx_digest(countries):
    country_blocks = []
    for c in countries:
        urls = FEEDS.get(c, [])
        items = collect(urls, OGP_KEYWORDS)
        print(f"[ORYX] {c}: {len(items)} live items", file=sys.stdout)
        country_blocks.append({"name": c, "items": _as_bullets(items)})

    subregional_items = collect(REGIONAL_FEEDS, OGP_KEYWORDS)
    print(f"[ORYX] Subregional: {len(subregional_items)} items", file=sys.stdout)
    subregional = _as_bullets(subregional_items)

    digest = {
        "countries": country_blocks,
        "subregional": subregional,
        "international": [],
        "analysis": {"opportunities": [], "top_pick": "—"}  # kept minimal (no matrix)
    }

    # Guardrail: refuse to post if any "(stub)" text is still present
    blob = str(digest)
    if "(stub)" in blob:
        raise RuntimeError("Stub content detected in digest. Refusing to post.")

    return digest
