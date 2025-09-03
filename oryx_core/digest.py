# oryx_core/digest.py
from __future__ import annotations
import os, html, time, urllib.parse, re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Set, Iterable
import feedparser
from collections import Counter

# ---------- Country names & locales ----------
ALT_NAMES = {
    # Central Europe
    "Austria": ["Austria", "Österreich"],
    "Bosnia and Herzegovina": ["Bosnia and Herzegovina", "Bosnia", "BiH", "Bosna i Hercegovina"],
    "Czech Republic": ["Czech Republic", "Czechia", "Česko", "Česká republika"],
    "Malta": ["Malta"],
    "Serbia": ["Serbia", "Srbija"],
    "Slovakia": ["Slovakia", "Slovensko"],
    # AME
    "Benin": ["Benin"],
    "Morocco": ["Morocco", "Maroc", "المغرب"],
    "Côte d’Ivoire": ["Côte d’Ivoire", "Cote d'Ivoire", "Ivory Coast", "CIV"],
    "Senegal": ["Senegal", "Sénégal"],
    "Tunisia": ["Tunisia", "Tunisie", "تونس"],
    "Burkina Faso": ["Burkina Faso"],
    "Ghana": ["Ghana"],
    "Liberia": ["Liberia"],
    "Jordan": ["Jordan", "الأردن", "Al Urdun"],
}

GN_LOCALE = {
    "Austria": ("de", "AT", "AT:de"),
    "Bosnia and Herzegovina": ("bs", "BA", "BA:bs"),
    "Czech Republic": ("cs", "CZ", "CZ:cs"),
    "Malta": ("en", "MT", "MT:en"),
    "Serbia": ("sr", "RS", "RS:sr"),
    "Slovakia": ("sk", "SK", "SK:sk"),
    "Benin": ("fr", "BJ", "BJ:fr"),
    "Morocco": ("fr", "MA", "MA:fr"),
    "Côte d’Ivoire": ("fr", "CI", "CI:fr"),
    "Senegal": ("fr", "SN", "SN:fr"),
    "Tunisia": ("fr", "TN", "TN:fr"),
    "Burkina Faso": ("fr", "BF", "BF:fr"),
    "Ghana": ("en", "GH", "GH:en"),
    "Liberia": ("en", "LR", "LR:en"),
    "Jordan": ("ar", "JO", "JO:ar"),
}

# Local TLDs to enforce "localness"
COUNTRY_TLDS = {
    "Austria": [".at"],
    "Bosnia and Herzegovina": [".ba"],
    "Czech Republic": [".cz"],
    "Malta": [".mt"],
    "Serbia": [".rs"],
    "Slovakia": [".sk"],
    "Benin": [".bj"],
    "Morocco": [".ma"],
    "Côte d’Ivoire": [".ci"],
    "Senegal": [".sn"],
    "Tunisia": [".tn"],
    "Burkina Faso": [".bf"],
    "Ghana": [".gh"],
    "Liberia": [".lr"],
    "Jordan": [".jo"],
}

# Per-country precision source lists (verified + reputable media)
COUNTRY_CONF: Dict[str, Dict[str, List[str]]] = {
    "Austria": {
        "verified_sites": ["parlament.gv.at", "bundeskanzleramt.gv.at", "data.gv.at", "gv.at"],
        "media_sites":    ["orf.at", "derstandard.at", "kurier.at", "diepresse.com", "profil.at", "wienerzeitung.at"],
    },
    "Bosnia and Herzegovina": {
        "verified_sites": ["parlament.ba", "gov.ba"],
        "media_sites":    ["klix.ba", "avaz.ba", "nezavisne.com", "rtrs.tv", "bhrt.ba", "radiosarajevo.ba"],
    },
    "Czech Republic": {
        "verified_sites": ["vlada.cz", "psp.cz", "senat.cz", "gov.cz", "data.gov.cz"],
        "media_sites":    ["seznamzpravy.cz", "denikn.cz", "novinky.cz", "idnes.cz", "aktualne.cz", "ceskenoviny.cz"],
    },
    "Malta": {
        "verified_sites": ["gov.mt", "parlament.mt", "data.gov.mt"],
        "media_sites":    ["timesofmalta.com", "maltatoday.com.mt", "newsbook.com.mt", "tvmnews.mt", "lovinmalta.com"],
    },
    "Serbia": {
        "verified_sites": ["gov.rs", "parlament.rs"],
        "media_sites":    ["rts.rs", "n1info.rs", "b92.net", "danas.rs", "nova.rs", "politika.rs"],
    },
    "Slovakia": {
        "verified_sites": ["gov.sk", "nrsr.sk", "data.gov.sk"],
        "media_sites":    ["sme.sk", "dennikn.sk", "aktuality.sk", "pravda.sk", "teraz.sk", "tasr.sk"],
    },
}
COUNTRY_CONF.update({
    "Benin": {
        "verified_sites": ["gouv.bj", "sgg.gouv.bj", "assemblee-nationale.bj"],
        "media_sites":    ["lanouvelletribune.info", "ortb.bj", "24haubenin.info"],
    },
    "Morocco": {
        "verified_sites": ["maroc.ma", "cg.gov.ma", "justice.gov.ma", "parlement.ma", "data.gov.ma"],
        "media_sites":    ["le360.ma", "hespress.com", "medi1news.com", "mapnews.ma", "telquel.ma"],
    },
    "Côte d’Ivoire": {
        "verified_sites": ["gouv.ci", "assembleenationale.ci", "presidence.ci", "go.ci"],
        "media_sites":    ["abidjan.net", "fratmat.info", "rtici.ci", "linfodrome.com", "koaci.com"],
    },
    "Senegal": {
        "verified_sites": ["gouv.sn", "assemblee-nationale.sn", "presidence.sn"],
        "media_sites":    ["aps.sn", "seneweb.com", "lequotidien.sn", "lepopulaire.sn"],
    },
    "Tunisia": {
        "verified_sites": ["pm.gov.tn", "gouvernement.tn", "arp.tn", "data.gov.tn"],
        "media_sites":    ["tap.info.tn", "businessnews.com.tn", "lapresse.tn", "kapitalis.com"],
    },
    "Burkina Faso": {
        "verified_sites": ["gouvernement.gov.bf", "assembleenationale.bf", "presidence.bf"],
        "media_sites":    ["lefaso.net", "sidwaya.info", "rtb.bf"],
    },
    "Ghana": {
        "verified_sites": ["ghana.gov.gh", "gov.gh", "parliament.gh"],
        "media_sites":    ["graphic.com.gh", "citinewsroom.com", "myjoyonline.com"],
    },
    "Liberia": {
        "verified_sites": ["emansion.gov.lr", "mofa.gov.lr", "moj.gov.lr"],
        "media_sites":    ["frontpageafricaonline.com", "theliberianobserver.com", "news.gov.lr"],
    },
    "Jordan": {
        "verified_sites": ["jordan.gov.jo", "pm.gov.jo", "parliament.jo", "moi.gov.jo"],
        "media_sites":    ["petra.gov.jo", "jordantimes.com", "alrai.com"],
    },
})

# Small global allowlist (only if country appears in title/summary)
GLOBAL_ALLOWED = [
    "europa.eu", "ec.europa.eu", "coe.int", "oecd.org",
    "worldbank.org", "afdb.org", "eiti.org", "transparency.org",
    "undp.org", "un.org", "news.un.org", "osce.org", "ebrd.com",
]

# Topic hints (assist discovery; final filter is themes)
TOPIC_KEYWORDS = [
    '"open government"', "transparency", '"access to information"', "whistleblower",
    '"beneficial ownership"', '"open data"', "anticorruption", "anti-corruption",
    "transparentnost", "protikorupcia", "prístup k informáciám",
    "antikorupcija", "pristup informacijama", "protikorupční",
    "Transparenz", "Informationsfreiheit", "Offene Daten",
    "transparence", "accès à l'information", "données ouvertes",
    "شفافية", "وصول إلى المعلومات", "البيانات المفتوحة",
]

# --- THEMES (OGP focus) ---
THEMES = {
    "Open Government": [
        "open government", "open gov", "ogp", "open governance",
        "offene regierung", "vláda otevřená", "otvorená vláda", "otvorena vlada",
    ],
    "Access to Information": [
        "access to information", "freedom of information", "foi", "foia", "rti",
        "informationsfreiheit", "právo na informace", "pravo na pristup informacijama",
        "slobodan pristup informacijama", "prístup k informáciám", "pristup informacijama",
        "accès à l'information", "حق الوصول إلى المعلومات",
    ],
    "Anti-Corruption": [
        "anti-corruption", "anticorruption", "corruption", "bribery", "integrity",
        "korupce", "korupcia", "korupcija", "bestechung",
    ],
    "Civic Space": [
        "civic space", "civil society", "ngo law", "freedom of association", "assembly", "protest",
        "udruženja", "nevladine organizacije", "nvo", "občianske združenie", "spolek",
    ],
    "Climate and Environment": [
        "climate", "emissions", "carbon", "co2", "environment", "biodiversity", "air quality",
        "klima", "umwelt", "životní prostředí", "životné prostredie", "životna sredina", "okoliš",
    ],
    "Digital Governance": [
        "digital government", "e-government", "egov", "digital identity", "eid", "ai policy",
        "cybersecurity", "govtech", "open data", "data portal",
        "e-government", "e-úrad", "eidas", "digitální", "digitálne",
    ],
    "Fiscal Openness": [
        "budget transparency", "open budget", "procurement", "public procurement", "tenders",
        "spending", "fiscal", "beneficial ownership", "tax transparency",
        "verejné obstarávanie", "veřejné zakázky", "javne nabavke",
    ],
    "Gender and Inclusion": [
        "gender", "women", "equality", "inclusion", "disability", "lgbt",
        "rovnosť", "rovnost", "ravnopravnost", "gleichstellung",
    ],
    "Justice": [
        "justice", "judiciary", "court", "prosecution", "rule of law", "whistleblower",
        "pravosudje", "pravosuđe", "súd", "soud", "gericht",
    ],
    "Media Freedom": [
        "media freedom", "press freedom", "journalist", "defamation",
        "sloboda medija", "svoboda tisku", "medienfreiheit",
    ],
    "Public Participation": [
        "public consultation", "participation", "citizen engagement", "petition", "referendum",
        "verejná konzultácia", "účast verejnosti", "javna rasprava", "javna konsultacija", "mitbestimmung",
    ],
}

# Optional: narrow themes via env ORYX_THEMES="Justice, Media Freedom"
ENABLED_THEMES = None
_env_themes = os.environ.get("ORYX_THEMES")
if _env_themes:
    ENABLED_THEMES = {t.strip() for t in _env_themes.split(",") if t.strip() in THEMES}

# ---------- Helpers ----------
def _match_themes(text: str) -> List[str]:
    text_l = text.lower()
    out = []
    for theme, kws in THEMES.items():
        if ENABLED_THEMES and theme not in ENABLED_THEMES:
            continue
        for kw in kws:
            if kw.lower() in text_l:
                out.append(theme)
                break
    return out

def _gn_rss(query: str, hl: str, gl: str, ceid: str) -> str:
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl={hl}&gl={gl}&ceid={ceid}"

def _ts(entry) -> datetime | None:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t: return None
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)

def _domain(url: str) -> str:
    try:
        return urllib.parse.urlsplit(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""

def _names(country: str) -> List[str]:
    return ALT_NAMES.get(country, [country])

def _locale(country: str) -> tuple[str,str,str]:
    return GN_LOCALE.get(country, ("en", "US", "US:en"))

def _contains_country(txt: str, country: str) -> bool:
    t = txt.lower()
    for n in _names(country):
        if n.lower() in t:
            return True
    return False

def _is_local_domain(country: str, dom: str) -> bool:
    return any(dom.endswith(tld) for tld in COUNTRY_TLDS.get(country, []))

def _dedupe(items: List[Dict]) -> List[Dict]:
    seen: Set[str] = set(); out=[]
    for it in items:
        key = it.get("link") or (it.get("title","") + it.get("domain",""))
        if key and key not in seen:
            seen.add(key); out.append(it)
    return out

def _endswith_any(d: str, sites: List[str]) -> bool:
    d = d.lower()
    for s in sites:
        s = s.lower()
        if d == s or d.endswith(s):
            return True
    return False

def _is_verified_domain(country: str, dom: str) -> bool:
    if country in COUNTRY_CONF and _endswith_any(dom, COUNTRY_CONF[country]["verified_sites"]):
        return True
    # Heuristic for countries w/o explicit lists
    return bool(re.search(r"(gov|gouv|parliament|parlament|senat|senate|assemblee|data\.gov)", dom))

def _build_queries(country: str, targeted: bool) -> Dict[str, List[str]]:
    names = " OR ".join([f'"{n}"' for n in _names(country)])
    topics = " OR ".join(TOPIC_KEYWORDS)
    if targeted and country in COUNTRY_CONF:
        conf = COUNTRY_CONF[country]
        ver = [f"({topics}) ({names}) (site:{s})" for s in conf["verified_sites"]]
        med = [f"({topics}) ({names}) (site:{s})" for s in conf["media_sites"]]
        return {"verified": ver, "media": med}
    return {"generic": [f"({topics}) ({names})"]}

def _allowed_domain_for_country(country: str, dom: str, title: str, summary: str, verified_hint=False) -> bool:
    # 1) Strong allow: explicit per-country lists
    if country in COUNTRY_CONF:
        if _endswith_any(dom, COUNTRY_CONF[country]["verified_sites"]) or _endswith_any(dom, COUNTRY_CONF[country]["media_sites"]):
            return True
    # 2) Local TLDs if the country is mentioned
    if _is_local_domain(country, dom) and _contains_country(f"{title} {summary}", country):
        return True
    # 3) Global allowlist (EU, WB, etc.) if the country is clearly mentioned
    if any(dom == g or dom.endswith(g) for g in GLOBAL_ALLOWED):
        return _contains_country(f"{title} {summary}", country)
    # 4) Heuristic verified for countries without explicit conf
    if verified_hint and _is_verified_domain(country, dom):
        return _contains_country(f"{title} {summary}", country)
    return False

# ---------- Collectors ----------
def _collect_for(country: str, hours: int) -> Tuple[List[Dict], List[Dict]]:
    hl, gl, ceid = _locale(country)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    verified: List[Dict] = []
    media: List[Dict] = []
    qsets = _build_queries(country, targeted=True) if country in COUNTRY_CONF else _build_queries(country, targeted=False)

    for label, qlist in qsets.items():
        for q in qlist:
            for (lang, glc, ce) in [(hl, gl, ceid), ("en","US","US:en")]:
                feed_url = _gn_rss(q, lang, glc, ce)
                parsed = feedparser.parse(feed_url)
                for e in parsed.entries:
                    dt = _ts(e)
                    if not dt or dt < cutoff:
                        continue
                    link = e.get("link") or ""
                    title = html.unescape(e.get("title", "")).strip()
                    summary = html.unescape(e.get("summary", "")).strip()
                    dom = _domain(link)

                    # THEME filter (must match ≥1)
                    themes = _match_themes(f"{title} {summary}")
                    if not themes:
                        continue

                    # Domain allow
                    allow = _allowed_domain_for_country(country, dom, title, summary, verified_hint=(label == "verified"))
                    if not allow:
                        continue

                    item = {
                        "title": title, "link": link, "summary": summary,
                        "domain": dom, "time": dt, "themes": themes,
                        "verified": (label == "verified") or _is_verified_domain(country, dom),
                    }
                    (verified if item["verified"] else media).append(item)

    # ---------- Fallbacks if zero after theme filter ----------
    if not verified and not media:
        # (A) site-only on official domains (no topic keywords), still theme-required
        if country in COUNTRY_CONF:
            conf = COUNTRY_CONF[country]
            for site in conf["verified_sites"]:
                for (lang, glc, ce) in [(hl, gl, ceid), ("en","US","US:en")]:
                    feed_url = _gn_rss(f"site:{site}", lang, glc, ce)
                    parsed = feedparser.parse(feed_url)
                    for e in parsed.entries:
                        dt = _ts(e)
                        if not dt or dt < cutoff:
                            continue
                        link = e.get("link") or ""
                        title = html.unescape(e.get("title","")).strip()
                        summary = html.unescape(e.get("summary","")).strip()
                        dom = _domain(link)
                        themes = _match_themes(f"{title} {summary}")
                        if not themes:
                            continue
                        verified.append({
                            "title": title, "link": link, "summary": summary,
                            "domain": dom, "time": dt, "themes": themes, "verified": True
                        })

        # (B) name-only local fallback (country mention + local TLD/global), still theme-required
        if not verified and not media:
            names_only = " OR ".join([f'"{n}"' for n in _names(country)])
            for (lang, glc, ce) in [(hl, gl, ceid), ("en","US","US:en")]:
                feed_url = _gn_rss(f"({names_only})", lang, glc, ce)
                parsed = feedparser.parse(feed_url)
                for e in parsed.entries:
                    dt = _ts(e)
                    if not dt or dt < cutoff:
                        continue
                    link = e.get("link") or ""
                    title = html.unescape(e.get("title","")).strip()
                    summary = html.unescape(e.get("summary","")).strip()
                    dom = _domain(link)
                    if not _contains_country(title + " " + summary, country):
                        continue
                    themes = _match_themes(f"{title} {summary}")
                    if not themes:
                        continue
                    is_local = _is_local_domain(country, dom)
                    is_global = any(dom == g or dom.endswith(g) for g in GLOBAL_ALLOWED)
                    if is_local or is_global:
                        media.append({
                            "title": title, "link": link, "summary": summary,
                            "domain": dom, "time": dt, "themes": themes, "verified": False
                        })

    return _dedupe(verified), _dedupe(media)

# ---------- Public API ----------
def generate_digest(countries: List[str], hours: int = 24, verified_only: bool = True) -> str:
    """
    Country-targeted Google News with:
      • strict recency (last `hours`)
      • OGP THEMES filter (must match at least one)
      • verified-first & local TLD filtering
      • global de-dup across countries
      • per-country metrics (counts, themes, top sources)
    Returns Slack-ready Markdown.
    """
    global_seen: Set[str] = set()
    header = f"Country updates (past {hours}h)\n"
    blocks: List[str] = []

    for c in countries:
        v, m = _collect_for(c, hours)
        items = v if (verified_only and v) else (v + m)

        # Global de-dup across all countries in this run
        unique: List[Dict] = []
        for it in items:
            key = it["link"] or (it["title"] + it["domain"])
            if key in global_seen:
                continue
            global_seen.add(key)
            unique.append(it)

        # Quant metrics
        total = len(unique)
        vcount = sum(1 for it in unique if it.get("verified"))
        mcount = total - vcount
        top_src = ", ".join(f"{dom} ({cnt})" for dom, cnt in Counter(it["domain"] for it in unique).most_common(3))
        by_theme = Counter(t for it in unique for t in it.get("themes", []))
        top_themes = ", ".join(f"{t} ({n})" for t, n in by_theme.most_common(3))

        # Header with metrics
        lines = [f"*{c} — {total} items ({vcount}✅/{mcount}📰)"
                 f"{' | Themes: ' + top_themes if total else ''}"
                 f"{' | Top: ' + top_src if total else ''}*"]

        if not unique:
            lines.append(f"• No theme-matching items in the past {hours}h.")
        else:
            # Rank: verified → #themes matched → recency (newest first)
            unique.sort(key=lambda it: (it.get('verified', False), len(it.get('themes', [])), it['time']),
                        reverse=True)
            for it in unique[:6]:  # up to 6 items per country
                badge = "✅" if it.get("verified") else "📰"
                tlist = ", ".join(it.get("themes", []))
                lines.append(f"• {badge} {it['title']} — <{it['link']}|{it['domain']}> _(themes: {tlist})_")

        blocks.append("\n".join(lines) + "\n")

    return header + "\n".join(blocks)
