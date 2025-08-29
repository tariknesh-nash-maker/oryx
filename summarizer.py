from datetime import datetime, timedelta

def _utc_date(days_ago=0):
    return (datetime.utcnow() - timedelta(days=days_ago)).date().isoformat()

def build_oryx_digest(countries):
    """
    Replace stubs with real fetchers in sources/fetchers.py.
    For now, this posts a clean skeleton so Slack delivery works immediately.
    """
    # Example: show 2 countries with stub items, others empty
    sample_items = [
        "• (stub) Verified governance item A — <https://example.org|source>",
        "• (stub) Verified governance item B — <https://example.org|source>"
    ]
    country_blocks = []
    for c in countries:
        items = sample_items if c in ("Benin", "Morocco") else []
        country_blocks.append({"name": c, "items": items})

    digest = {
        "countries": country_blocks,
        "subregional": [
            "• (stub) ECOWAS/Maghreb development with link — <https://example.org|source>"
        ],
        "international": [
            "• (stub) OGP/global item with link — <https://example.org|source>"
        ],
        "analysis": {
            "opportunities": [
                {
                    "title": "Benin — Open contracting dashboard pilot",
                    "relevance": "High", "ambition": "Med", "likelihood": "High", "time": "Low",
                    "note": "Quick win with strong visibility; ties to peer-learning."
                },
                {
                    "title": "Senegal — Implementation roadmap for 4 laws",
                    "relevance": "High", "ambition": "High", "likelihood": "Med", "time": "Med",
                    "note": "Requires anchoring & sequencing; high leverage potential."
                }
            ],
            "top_pick": "Benin — open contracting dashboard pilot (high relevance, quick win)."
        }
    }
    return digest

