# feeds.py — expanded, OGP-focused feeds (all RSS via Google News)
# Tip: Tune keywords per country as you watch signal.

COUNTRIES = [
    "Benin", "Morocco", "Côte d’Ivoire", "Senegal",
    "Tunisia", "Burkina Faso", "Ghana", "Liberia", "Jordan"
]

# OGP-ish filters used across countries
OGP_KEYWORDS = [
    "access to information", "freedom of information", "open data",
    "anti-corruption", "asset declaration", "whistleblower",
    "beneficial ownership", "budget transparency", "procurement",
    "open contracting", "civic space", "digital government",
    "e-government", "judicial reform", "press freedom",
    "participation", "co-creation", "OGP", "governance",
    "transparency", "accountability", "decentralization"
]

def gnews(query, lang="en", gl="US"):
    from urllib.parse import quote_plus
    # Google News RSS: q=<query>, hl=<lang>, gl=<geo>, ceid=<geo>:<lang>
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={lang}&gl={gl}&ceid={gl}:{lang}"

# Helper bundles to keep queries readable
def ogp(country):
    return f'{country} ("access to information" OR transparency OR governance OR "open data" OR "anti-corruption" OR "open contracting" OR procurement OR "press freedom" OR "civic space" OR "digital government")'

def siteq(domain, *terms):
    # Builds: site:domain term1 OR term2 ...
    inner = " OR ".join(terms)
    return f"site:{domain} ({inner})"

# Per-country curated lists.
# We favor: (1) broad OGP queries, (2) official sites via site: filters, (3) top reliable media.
FEEDS = {
    "Morocco": [
        gnews(ogp("Morocco"), lang="en", gl="MA"),
        gnews(siteq("maroc.ma", "décret", "loi", "réforme", "transparence"), lang="fr", gl="MA"),
        gnews(siteq("sgg.gov.ma", "Bulletin Officiel", "décret", "loi"), lang="fr", gl="MA"),
        gnews(siteq("mapnews.ma", "gouvernance", "transparence"), lang="fr", gl="MA"),
        gnews(siteq("worldbank.org/en/country/morocco", "press release", "loan", "policy"), lang="en", gl="MA"),
        gnews(siteq("afdb.org", "Morocco"), lang="en", gl="MA"),
        gnews(siteq("eeas.europa.eu/delegations/morocco", "press", "statement"), lang="en", gl="MA"),
        gnews(siteq("allafrica.com/morocco", "governance", "transparency"), lang="en", gl="MA"),
    ],
    "Benin": [
        gnews(ogp("Benin"), lang="en", gl="BJ"),
        gnews(siteq("gouv.bj", "décret", "loi", "transparence"), lang="fr", gl="BJ"),
        gnews(siteq("journalofficiel.gouv.bj", "Journal Officiel", "décret", "loi"), lang="fr", gl="BJ"),
        gnews(siteq("sgg.gouv.bj", "Journal Officiel", "décret", "loi"), lang="fr", gl="BJ"),
        gnews(siteq("allafrica.com/benin", "governance", "transparency"), lang="en", gl="BJ"),
    ],
    "Côte d’Ivoire": [
        gnews(ogp("Côte d’Ivoire"), lang="fr", gl="CI"),
        gnews(siteq("gouv.ci", "décret", "loi", "transparence", "gouvernance"), lang="fr", gl="CI"),
        gnews(siteq("sgg.gouv.ci", "Journal Officiel", "décret", "loi"), lang="fr", gl="CI"),
        gnews(siteq("allafrica.com/cote_d_ivoire", "gouvernance", "transparence"), lang="fr", gl="CI"),
    ],
    "Senegal": [
        gnews(ogp("Senegal"), lang="en", gl="SN"),
        gnews(siteq("presidence.sn", "communiqué", "décret", "Conseil des ministres"), lang="fr", gl="SN"),
        gnews(siteq("gouv.sn", "décret", "loi", "transparence"), lang="fr", gl="SN"),
        gnews(siteq("allafrica.com/senegal", "gouvernance", "transparence"), lang="fr", gl="SN"),
    ],
    "Tunisia": [
        gnews(ogp("Tunisia"), lang="en", gl="TN"),
        gnews(siteq("presidence.tn", "décret", "loi", "journal officiel", "communiqué"), lang="fr", gl="TN"),
        gnews(siteq("allafrica.com/tunisia", "governance", "transparency"), lang="en", gl="TN"),
        gnews(siteq("eeas.europa.eu/delegations/tunisia", "press", "statement"), lang="en", gl="TN"),
    ],
    "Burkina Faso": [
        gnews(ogp("Burkina Faso"), lang="en", gl="BF"),
        gnews(siteq("allafrica.com/burkinafaso", "governance", "transparency"), lang="en", gl="BF"),
    ],
    "Ghana": [
        gnews(ogp("Ghana"), lang="en", gl="GH"),
        gnews(siteq("presidency.gov.gh", "press release", "policy", "cabinet"), lang="en", gl="GH"),
        gnews(siteq("allafrica.com/ghana", "governance", "transparency"), lang="en", gl="GH"),
        gnews(siteq("worldbank.org/en/country/ghana", "press release", "loan", "policy"), lang="en", gl="GH"),
    ],
    "Liberia": [
        gnews(ogp("Liberia"), lang="en", gl="LR"),
        gnews(siteq("micat.gov.lr", "press release", "transparency", "policy"), lang="en", gl="LR"),
        gnews(siteq("allafrica.com/liberia", "governance", "transparency"), lang="en", gl="LR"),
    ],
    "Jordan": [
        gnews(ogp("Jordan"), lang="en", gl="JO"),
        gnews(siteq("pm.gov.jo", "قرار", "تعليمات", "الجريدة الرسمية", "بيان"), lang="ar", gl="JO"),
        gnews(siteq("mop.gov.jo", "Prime Minister", "cabinet", "decision"), lang="en", gl="JO"),
        gnews(siteq("allafrica.com/jordan", "governance", "transparency"), lang="en", gl="JO"),
        # add Arabic OGP terms to improve recall
        gnews('الأردن ("حق الحصول على المعلومة" OR الشفافية OR الحوكمة OR مكافحة الفساد)', lang="ar", gl="JO"),
    ],
}

# Regional / international context feeds
REGIONAL_FEEDS = [
    gnews("ECOWAS (governance OR transparency OR anti-corruption)", lang="en", gl="SN"),
    gnews("Maghreb (gouvernance OR transparence OR anti-corruption)", lang="fr", gl="MA"),
    gnews("African Development Bank press release governance Morocco OR Ghana OR Tunisia", lang="en", gl="MA"),
    gnews("World Bank press release governance Morocco OR Ghana OR Tunisia", lang="en", gl="MA"),
    gnews("Open Government Partnership Africa OR MENA", lang="en", gl="US"),
]
