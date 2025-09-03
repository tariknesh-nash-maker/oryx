# oryx_core/digest.py
from __future__ import annotations
import html, time, urllib.parse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Set
import feedparser

# ---------- Config ----------
ALT_NAMES = {
    "Austria": ["Austria", "Österreich"],
    "Bosnia and Herzegovina": ["Bosnia and Herzegovina", "Bosnia", "BiH", "Bosna i Hercegovina"],
    "Czech Republic": ["Czech Republic", "Czechia", "Česko", "Česká republika"],
    "Malta": ["Malta"],
    "Serbia": ["Serbia", "Srbija"],
    "Slovakia": ["Slovakia", "Slovensko"],
}

# Topic focus (OGP-ish). Tweak as needed.
TOPIC_KEYWORDS = [
    '"open government"', "transparency", '"access to information"', "whistleblower",
    '"beneficial ownership"', '"open data"', "anticorruption", "anti-corruption",
    # CS/CZ/SK/BA/SR/DE hints
    "transparentnost", "protikorupcia", "prístup k informáciám",
    "antikorupcija", "pristup informacijama", "protikorupční",
    "Transparenz", "Informationsfreiheit", "Offene Daten"
]

# Country-specific sources (verified first; then reputable media)
COUNTRY_CONF = {
    "Austria": {
        "hl": "de", "gl": "AT", "ceid": "AT:de",
        "verified_sites": ["parlament.gv.at", "bundeskanzleramt.gv.at", "data.gv.at", "gv.at"],
        "media_sites": ["orf.at", "derstandard.at", "kurier.at", "diepresse.com", "profil.at", "wienerzeitung.at"],
    },
    "Bosnia and Herzegovina": {
        "hl": "bs", "gl": "BA", "ceid": "BA:bs",
        "verified_sites": ["parlament.ba", "gov.ba"],  # add entity sites if you wish
        "media_sites": ["klix.ba", "avaz.ba", "nezavisne.com", "rtrs.tv", "bhrt.ba", "radiosarajevo.ba"],
    },
    "Czech Republic": {
        "hl": "cs", "gl": "CZ", "ceid": "CZ:cs",
        "verified_sites": ["vlada.cz", "psp.cz", "senat.cz", "gov.cz", "data.gov.cz"],
        "media_sites": ["seznamzpravy.cz", "denikn.cz", "novinky.cz", "idnes.cz", "aktualne.cz", "ceskenoviny.cz"],
    },
    "Malta": {
        "hl": "en", "gl": "MT", "ceid": "MT:en",
        "verified_sites": ["gov.mt", "parlament.mt", "data.gov.mt"],
        "media_sites": ["timesofmalta.com", "maltatoday.com.mt", "newsbook.com.mt", "tvmnews.mt", "lovinmalta.com"],
    },
    "Serbia": {
        "hl": "sr", "gl": "RS", "ceid": "RS:sr",
        "verified_sites": ["gov.rs", "parlament.rs"],
        "media_sites": ["rts.rs", "n1info.rs", "b92.net", "danas.rs", "nova.rs", "politika.rs"],
    },
    "Slovakia": {
        "hl": "sk", "gl": "SK", "ceid": "SK:sk",
        "verified_sites": ["gov.sk", "nrsr.sk", "data.gov.sk"],
        "media_sites": ["sme.sk", "dennikn.sk", "aktuality.sk", "pravda.sk", "teraz.sk", "tasr.sk"],
    },
}

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

def _q_from_sites(sites: List[str]) -> str:
    # Build "site:dom1 OR site:dom2 ..." safely
    return " OR ".join([f"site:{s}" for s in sites])

def _build_queries(country: str) -> Dict[str, List[str]]:
    names = ALT_NAMES.get(country, [country])
    name_q = " OR ".join([f'"{n}"' for n in names])
    topics = " OR ".join(TOPIC_KEYWORDS)
    conf = COUNTRY_CONF[country]
    verified_q = f"({topics}) ({name_q}) ({_q_from_sites(conf['verified_sites'])})"
    media_q    = f"({topics}) ({name_q}) ({_q_from_sites(conf['media_sites'])})"
    # Try local-language first, then English fallback for breadth
    return {"verified": [verified_q], "media": [media_q]}

def _collect_for(country: str, hours: int) -> Tuple[List[Dict], List[Dict]]:
    conf = COUNTRY_CONF[country]
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    verified, media = [], []

    for label, qlist in _build_queries(country).items():
        for q in qlist:
            # Local feed
            feed_url = _gn_rss(q, conf["hl"], conf["gl"], conf["ceid"])
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

def generate_digest(countries: List[str], hours: int = 24, verified_only: bool = True) -> str:
    """
    Country-targeted Google News (RSS) with:
      • local language + country targeting
      • strict 24h (hours param) window
      • per-run global de-duplication (avoid repeats across countries)
      • verified-first (gov/parliament/EU); graceful fallback to reputable media
    Returns Slack-ready Markdown.
    """
    global_seen: Set[str] = set()
    header = f"Country updates (past {hours}h)\n"
    blocks: List[str] = []

    for c in countries:
        v, m = _collect_for(c, hours)
        items = v if (verified_only and v) else (v + m)  # verified-first, fallback to media
        # drop items already used for another country in this run
        unique = []
        for it in items:
            key = it["link"] or (it["title"] + it["domain"])
            if key in global_seen: 
                continue
            global_seen.add(key)
            unique.append(it)

        if not unique:
            blocks.append(f"*{c}*\n• No verified items in the past {hours}h.\n")
            continue

        # Trim to 4 per country
        lines = [f"*{c}*"]
        for it in unique[:4]:
            badge = "✅" if any(it["domain"].endswith(s) for s in COUNTRY_CONF[c]["verified_sites"]) else "📰"
            lines.append(f"• {badge} {it['title']} — <{it['link']}|{it['domain']}>")
        blocks.append("\n".join(lines) + "\n")

    return header + "\n".join(blocks)
