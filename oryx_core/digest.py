# oryx_core/digest.py
from __future__ import annotations
import html, time, urllib.parse, re
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
    # AME (so we cover your other channel too)
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

# Per-country precision source lists
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
    # (Optionally add AME verified/media lists later to improve hit-rate)
}

# Small global allowlist (only if country appears in title/summary)
GLOBAL_ALLOWED = [
    "europa.eu", "ec.europa.eu", "coe.int", "oecd.org",
    "worldbank.org", "afdb.org", "eiti.org", "transparency.org",
    "undp.org", "un.org", "news.un.org", "osce.org", "ebrd.com",
]

# Topics (OGP-ish, multilingual hints)
TOPIC_KEYWORDS = [
    '"open government"', "transparency", '"access to information"', "whistleblower",
    '"beneficial ownership"', '"open data"', "anticorruption", "anti-corruption",
    "transparentnost", "protikorupcia", "prístup k informáciám",
    "antikorupcija", "pristup informacijama", "protikorupční",
    "Transparenz", "Informationsfreiheit", "Offene Daten",
    "transparence", "accès à l'information", "données ouvertes",
    "شفافية", "وصول إلى المعلومات", "البيانات المفتوحة",
]

# ---------- Helpers ----------
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

def _dedupe(items: List[Dict]) -> List[Dict]:
    seen: Set[str] = set(); out=[]
    for it in items:
        key = it.get("link") or (it.get("title","") + it.get("domain",""))
        if key and key not in seen:
            seen.add(key); out.append(it)
    return out

def _q_from_sites(sites: Iterable[str]) -> str:
    return " OR ".join([f"site:{s}" for s in sites])

def _build_queries(country: str, targeted: bool) -> Dict[str, List[str]]:
    names = " OR ".join([f'"{n}"' for n in _names(country)])
    topics = " OR ".join(TOPIC_KEYWORDS)
    if targeted and country in COUNTRY_CONF:
        conf = COUNTRY_CONF[country]
        return {
            "verified": [f"({topics}) ({names}) ({_q_from_sites(conf['verified_sites'])})"],
            "media":    [f"({topics}) ({names}) ({_q_from_sites(conf['media_sites'])})"],
        }
    # generic fallback: no site filter in the query string; we’ll filter post-fetch
    return {"generic": [f"({topics}) ({names})"]}

def _allowed_domain_for_country(country: str, dom: str, title: str, summary: str, verified_hint=False) -> bool:
    # 1) Strong allow: explicit country lists
    if country in COUNTRY_CONF:
        if dom in COUNTRY_CONF[country]["verified_sites"] or dom in COUNTRY_CONF[country]["media_sites"]:
            return True

    # 2) Local TLDs (e.g., .ba for Bosnia), if the country is mentioned in the text
    for tld in COUNTRY_TLDS.get(country, []):
        if dom.endswith(tld) and _contains_country(f"{title} {summary}", country):
            return True

    # 3) Global allowlist (EU, WB, AfDB, etc.) — only if the country is clearly mentioned
    if any(dom.endswith(g) or dom == g for g in GLOBAL_ALLOWED):
        return _contains_country(f"{title} {summary}", country)

    # 4) Verified heuristics (gov/parliament) for countries without explicit conf
    if verified_hint:
        if re.search(r"(gov|gouv|parliament|parlament|senat|senate|assemblee|data\.gov)", dom):
            return _contains_country(f"{title} {summary}", country)

    return False

# ---------- Collectors ----------
def _collect_for(country: str, hours: int) -> Tuple[List[Dict], List[Dict]]:
    hl, gl, ceid = _locale(country)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    verified, media = [], []
    qsets = _build_queries(country, targeted=True) if country in COUNTRY_CONF else _build_queries(country, targeted=False)

    for label, qlist in qsets.items():
        for q in qlist:
            # try local feed; then english fallback for breadth
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
                    item = {"title": title, "link": link, "summary": summary, "domain": dom, "time": dt}

                    # Post-filtering to avoid irrelevant (e.g., US) stories:
                    if label in ("verified",):
                        allow = _allowed_domain_for_country(country, dom, title, summary, verified_hint=True)
                        if allow:
                            verified.append(item)
                    else:
                        allow = _allowed_domain_for_country(country, dom, title, summary, verified_hint=False)
                        if allow:
                            media.append(item)

    return _dedupe(verified), _dedupe(media)

# ---------- Public API ----------
def generate_digest(countries: List[str], hours: int = 24, verified_only: bool = True) -> str:
    """
    Country-targeted Google News with:
      • strict recency (last `hours`)
      • verified-first & local TLD filtering
      • global de-dup across countries
      • per-country metrics (counts, verified %, top sources)
    Returns Slack-ready Markdown.
    """
    global_seen: Set[str] = set()
    header = f"Country updates (past {hours}h)\n"
    blocks: List[str] = []

    for c in countries:
        v, m = _collect_for(c, hours)
        items = v if (verified_only and v) else (v + m)

        # Global de-dup across all countries in this run
        unique = []
        for it in items:
            key = it["link"] or (it["title"] + it["domain"])
            if key in global_seen:
                continue
            global_seen.add(key)
            unique.append(it)

        # Quant metrics
        total = len(unique)
        vcount = sum(1 for it in unique if it in v)
        mcount = total - vcount
        top_src = ", ".join(f"{dom} ({cnt})" for dom, cnt in Counter(it["domain"] for it in unique).most_common(3))

        # Qual + Quant header line
        lines = [f"*{c} — {total} items ({vcount}✅/{mcount}📰){' | Top: ' + top_src if total else ''}*"]

        if not unique:
            lines.append(f"• No verified items in the past {hours}h.")
        else:
            for it in unique[:6]:  # up to 6 items per country
                badge = "✅" if it in v else "📰"
                lines.append(f"• {badge} {it['title']} — <{it['link']}|{it['domain']}>")

        blocks.append("\n".join(lines) + "\n")

    return header + "\n".join(blocks)
