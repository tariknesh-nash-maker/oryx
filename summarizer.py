from feeds import FEEDS, REGIONAL_FEEDS, OGP_KEYWORDS
from fetch import collect

def _as_bullets(entries, prefix="• "):
    bullets = []
    for e in entries[:12]:  # cap per section
        link = e["link"]
        title = e["title"].strip() or link
        bullets.append(f"{prefix}{title} — <{link}|source>")
    return bullets

def build_oryx_digest(countries):
    country_blocks = []
    for c in countries:
        urls = FEEDS.get(c, [])
        items = collect(urls, OGP_KEYWORDS)
        bullets = _as_bullets(items)
        country_blocks.append({"name": c, "items": bullets})

    subregional_items = collect(REGIONAL_FEEDS, OGP_KEYWORDS)
    subregional = _as_bullets(subregional_items)

    # Simple placeholder analysis; you can evolve this later
    analysis = {
        "opportunities": [],
        "top_pick": "—"
    }

    return {
        "countries": country_blocks,
        "subregional": subregional,
        "international": [],
        "analysis": analysis
    }
