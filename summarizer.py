from feeds import FEEDS, REGIONAL_FEEDS, OGP_KEYWORDS
from fetch import collect

def _as_bullets(entries, prefix="• "):
    return [f"{prefix}{e['title']} — <{e['link']}|source>" for e in entries[:12]]

def build_oryx_digest(countries):
    country_blocks = []
    for c in countries:
        items = collect(FEEDS.get(c, []), OGP_KEYWORDS)
        country_blocks.append({"name": c, "items": _as_bullets(items)})

    subregional = _as_bullets(collect(REGIONAL_FEEDS, OGP_KEYWORDS))

    return {
        "countries": country_blocks,
        "subregional": subregional,
        "international": [],
        "analysis": {"opportunities": [], "top_pick": "—"}
    }
