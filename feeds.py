# Countries in scope
COUNTRIES = [
    "Benin", "Morocco", "Côte d’Ivoire", "Senegal",
    "Tunisia", "Burkina Faso", "Ghana", "Liberia", "Jordan"
]

# OGP-ish filters (adjust anytime)
OGP_KEYWORDS = [
    "access to information", "freedom of information", "open data",
    "anti-corruption", "asset declaration", "whistleblower", "beneficial ownership",
    "budget transparency", "procurement", "open contracting", "civic space",
    "digital government", "e-government", "judicial reform", "press freedom",
    "participation", "co-creation", "OGP", "governance", "transparency",
    "accountability", "decentralization"
]

# Helper to build Google News RSS query URLs (works well across countries)
def gnews(query, lang="en", geocode="MA"):
    from urllib.parse import quote_plus
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={lang}&gl={geocode}&ceid={geocode}:{lang}"

# Curated feeds per country (mix of Google News queries + official/IFI sources)
FEEDS = {
    "Morocco": [
        gnews("Morocco governance OR transparency OR anti-corruption OR open data"),
        gnews("site:maroc.ma government reform OR law OR decree"),
        gnews("site:mapnews.ma governance OR transparency"),
        # IMF country page/news often relevant to fiscal openness
        "https://www.imf.org/external/cntpst/rss/morocco.xml",  # IMF country news (generic endpoint varies)
    ],
    "Benin": [
        gnews("Benin governance OR transparency OR anti-corruption"),
        gnews("site:gouv.bj décret OR loi OR transparence"),
        gnews("site:sgg.gouv.bj Journal Officiel"),
    ],
    "Côte d’Ivoire": [
        gnews("Côte d’Ivoire governance OR transparency OR anti-corruption"),
        gnews("site:gouv.ci décret OR loi OR transparence"),
    ],
    "Senegal": [
        gnews("Senegal governance OR transparency OR anti-corruption"),
        gnews("site:gouv.sn décret OR loi OR transparence"),
    ],
    "Tunisia": [
        gnews("Tunisia governance OR transparency OR anti-corruption"),
        gnews("site:presidence.tn décret OR loi"),
    ],
    "Burkina Faso": [
        gnews("Burkina Faso governance OR transparency OR anti-corruption"),
    ],
    "Ghana": [
        gnews("Ghana governance OR transparency OR anti-corruption"),
        "https://presidency.gov.gh/press-releases/feed/",  # Presidency press releases (RSS)
    ],
    "Liberia": [
        gnews("Liberia governance OR transparency OR anti-corruption"),
        gnews("site:micat.gov.lr press release OR transparency"),
    ],
    "Jordan": [
        gnews("Jordan governance OR transparency OR anti-corruption"),
        gnews("site:pm.gov.jo decree OR law OR transparency"),
    ],
}

# (Optional) Regional/international context feeds
REGIONAL_FEEDS = [
    gnews("ECOWAS governance OR transparency OR anti-corruption"),
    gnews("Maghreb governance OR transparency OR anti-corruption"),
    "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf"  # broad, we will keyword-filter
]
