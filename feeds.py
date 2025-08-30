# Countries covered
COUNTRIES = [
    "Benin", "Morocco", "Côte d’Ivoire", "Senegal",
    "Tunisia", "Burkina Faso", "Ghana", "Liberia", "Jordan"
]

# OGP-ish keywords; tweak anytime
OGP_KEYWORDS = [
    "access to information", "freedom of information", "open data",
    "anti-corruption", "asset declaration", "whistleblower", "beneficial ownership",
    "budget transparency", "procurement", "open contracting", "civic space",
    "digital government", "e-government", "judicial reform", "press freedom",
    "participation", "co-creation", "OGP", "governance", "transparency",
    "accountability", "decentralization"
]

def gnews(query, lang="en", gl="MA"):
    from urllib.parse import quote_plus
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={lang}&gl={gl}&ceid={gl}:{lang}"

# Minimal curated feed list per country (expand later)
FEEDS = {
    "Morocco": [
        gnews("Morocco governance OR transparency OR anti-corruption OR open data"),
        gnews("site:maroc.ma decree OR law OR reform OR transparency"),
        gnews("site:mapnews.ma governance OR transparency"),
    ],
    "Benin": [
        gnews("Benin governance OR transparency OR anti-corruption"),
        gnews("site:gouv.bj décret OR loi OR transparence", lang="fr", gl="BJ"),
    ],
    "Côte d’Ivoire": [
        gnews("Côte d’Ivoire governance OR transparency OR anti-corruption", lang="fr", gl="CI"),
        gnews("site:gouv.ci décret OR loi OR transparence", lang="fr", gl="CI"),
    ],
    "Senegal": [
        gnews("Senegal governance OR transparency OR anti-corruption"),
        gnews("site:gouv.sn décret OR loi OR transparence", lang="fr", gl="SN"),
    ],
    "Tunisia": [
        gnews("Tunisia governance OR transparency OR anti-corruption"),
        gnews("site:presidence.tn décret OR loi", lang="fr", gl="TN"),
    ],
    "Burkina Faso": [
        gnews("Burkina Faso governance OR transparency OR anti-corruption"),
    ],
    "Ghana": [
        gnews("Ghana governance OR transparency OR anti-corruption"),
    ],
    "Liberia": [
        gnews("Liberia governance OR transparency OR anti-corruption"),
    ],
    "Jordan": [
        gnews("Jordan governance OR transparency OR anti-corruption"),
    ],
}

REGIONAL_FEEDS = [
    gnews("ECOWAS governance OR transparency OR anti-corruption"),
    gnews("Maghreb governance OR transparency OR anti-corruption"),
]
