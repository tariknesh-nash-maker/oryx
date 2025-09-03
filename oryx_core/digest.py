# oryx_core/digest.py
from __future__ import annotations
import html, time, urllib.parse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Set
import feedparser

# ---------- Names & language setup ----------
ALT_NAMES = {
    # Central Europe
    "Austria": ["Austria", "Österreich"],
    "Bosnia and Herzegovina": ["Bosnia and Herzegovina", "Bosnia", "BiH", "Bosna i Hercegovina"],
    "Czech Republic": ["Czech Republic", "Czechia", "Česko", "Česká republika"],
    "Malta": ["Malta"],
    "Serbia": ["Serbia", "Srbija"],
    "Slovakia": ["Slovakia", "Slovensko"],
    # AME (so we don't crash)
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

# Language/region for Google News (hl/gl/ceid)
GN_LOCALE = {
    # Central Europe
    "Austria": ("de", "AT", "AT:de"),
    "Bosnia and Herzegovina": ("bs", "BA", "BA:bs"),
    "Czech Republic": ("cs", "CZ", "CZ:cs"),
    "Malta": ("en", "MT", "MT:en"),
    "Serbia": ("sr", "RS", "RS:sr"),
    "Slovakia": ("sk", "SK", "SK:sk"),
    # AME
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

# Topic focus (OGP-like)
TOPIC_KEYWORDS = [
    '"open government"', "transparency", '"access to information"', "whistleblower",
    '"beneficial ownership"', '"open data"', "anticorruption", "anti-corruption",
    # local hints
    "transparentnost", "protikorupcia", "prístup k informáciám",  # SK
    "antikorupcija", "pristup informacijama",                     # SR/BA
    "protikorupční",                                              # CZ
    "Transparenz", "Informationsfreiheit", "Offene Daten",        # DE/AT
    "transparence", "accès à l'information", "données ouvertes",  # FR
    "شفافية", "وصول إلى المعلومات", "البيانات المفتوحة"           # AR
]

# Per-country precise site whitelists (strongest signal) – Central Europe tailored
COUNTRY_CONF = {
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

# Generic “verified” domain heuristics (for countries not in COUNTRY_CONF)
GENERIC_VERIFIED_HINTS = (
    "gov.", ".gov", "gouv", "parliament", "parlament", "assemblee", "senat", "senate",
    "presidence", "primature", "gouvernement", "data.gov"
)

# ---------- Helpers ----------
def _gn_rss(query: str, lang: str, gl: str, ceid: str) -> str:
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={gl}&ceid={ceid}"

def _ts(entry) -> datetime | None:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t: return None
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)

def _domain(url: str) -> str:
    try:
        return urllib.parse.urlsplit(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""

def _dedupe(items: List[Dict]) -> List[Dict]:
    seen: Set[str] = set(); out=[]
    for it in items:
        key = it.get("link") or it.get("title")
        if key and key not in seen:
            seen.add(key); out.append(it)
    return out

def _names(country: str) -> List[str]:
    return ALT_NAMES.get(country, [country])

def _locale(country: str) -> tuple[str,str,str]:
    return GN_LOCALE.get(country, ("en", "US", "US:en"))

def _is_verified_domain(country: str, dom: str) -> bool:
    # Strong check if we have exact sites for that country
    if country in COUNTRY_CONF:
        return any(dom.endswith(s) for s in COUNTRY_CONF[country]["verified_sites"])
    # Generic heuristic for others
    d = dom.lower()
    return any(h in d for h in GENERIC_VERIFIED_HINTS)

# ---------- Query builders ----------
def _build_queries_targeted(country: str) -> Dict[str, List[str]]:
    names = " OR ".join([f'"{n}"' for n in _names(country)])
    topics = " OR ".join(TOPIC_KEYWORDS)
    conf = COUNTRY_CONF[country]
    verified_q = f"({topics}) ({names}) ({' OR '.join([f'site:{s}' for s in conf['verified_sites']])})"
    media_q    = f"({topics}) ({names}) ({' OR '.join([f'site:{s}' for s in conf['media_sites']])})"
    return {"verified": [verified_q], "media": [media_q]}

def _build_queries_generic(country: str) -> List[str]:
    names = " OR ".join([f'"{n}"' for n in _names(country)])
    topics = " OR ".join(TOPIC_KEYWORDS)
    # No site: filter (Google News wildcards are unreliable). We'll filter by domain after fetching.
    return [f"({topics}) ({names})"]

# ---------- Collectors ----------
def _collect_for(country: str, hours: int) -> Tuple[List[Dict], List[Dict]]:
    """
    Returns (verified_items, media_items) for a country within the window.
    Uses country-targeted site lists when available, otherwise a generic collector.
    """
    hl, gl, ceid = _locale(country)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    if country in COUNTRY_CONF:
        verified, media = [], []
        for label, qlist in _build_queries_targeted(country).items():
            for q in qlist:
                feed_url = _gn_rss(q, hl, gl, ceid)
                parsed = feedparser.parse(feed_url)
                for e in parsed.entries:
                    dt = _ts(e)
                    if not dt or dt < cutoff: 
                        continue
                    link = e.get("link") or ""
                    title = html.unescape(e.get("title", "")).strip()
                    summary = html.unescape(e.get("summary", "")).strip()
                    dom = _domain(link)
                    item = {"title": title, "link": link, "summary": summary, "domain": dom, "time": dt}
                    if label == "verified":
                        verified.append(item)
                    else:
                        media.append(item)
        return _dedupe(verified), _dedupe(media)

    # Generic fallback (for Benin, Morocco, etc.)
    verified, media = [], []
    for q in _build_queries_generic(country):
        # Local-language feed + English fallback for breadth
        for lang, glc, ce in [(hl, gl, ceid), ("en", "US", "US:en")]:
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
                item = {"title": title, "link": link, "summary": summary, "domain": dom, "time": dt}
                (verified if _is_verified_domain(country, dom) else media).append(item)
    return _dedupe(verified), _dedupe(media)

# ---------- Public API ----------
def generate_digest(countries: List[str], hours: int = 24, verified_only: bool = True) -> str:
    """
    Country-targeted Google News with:
      • local language per country + EN fallback
      • strict recency (last `hours`)
      • global de-dup per run (avoid repeats across countries)
      • verified-first (gov/parliament); graceful fallback to reputable media
    Returns Slack-ready Markdown.
    """
    global_seen: Set[str] = set()
    header = f"Country updates (past {hours}h)\n"
    blocks: List[str] = []

    for c in countries:
        v, m = _collect_for(c, hours)
        items = v if (verified_only and v) else (v + m)
        # Global de-dupe across countries
        unique = []
        for it in items:
            key = it["link"] or (it["title"] + it["domain"])
            if key in global_seen:
                continue
            global_seen.add(key); unique.append(it)

        if not unique:
            blocks.append(f"*{c}*\n• No verified items in the past {hours}h.\n")
            continue

        lines = [f"*{c}*"]
        for it in unique[:4]:
            badge = "✅" if _is_verified_domain(c, it["domain"]) else "📰"
            lines.append(f"• {badge} {it['title']} — <{it['link']}|{it['domain']}>")
        blocks.append("\n".join(lines) + "\n")

    return header + "\n".join(blocks)
