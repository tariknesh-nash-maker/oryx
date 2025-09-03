# oryx_core/digest.py
from __future__ import annotations
import time, html, urllib.parse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple
import feedparser

ALT_NAMES = {
    "Austria": ["Austria", "Österreich"],
    "Bosnia and Herzegovina": ["Bosnia and Herzegovina", "Bosnia", "BiH", "Bosna i Hercegovina"],
    "Czech Republic": ["Czech Republic", "Czechia", "Česko", "Česká republika"],
    "Malta": ["Malta"],
    "Serbia": ["Serbia", "Srbija"],
    "Slovakia": ["Slovakia", "Slovensko"],
}

# “Verified” government/parliament domains (suffixes)
VERIFIED_SUFFIXES = [
    ".gv.at", ".gov.at",          # Austria
    ".gov.ba",                    # Bosnia and Herzegovina
    ".gov.cz", ".psp.cz", ".senat.cz", # Czech
    ".gov.mt", ".parlament.mt",   # Malta
    ".gov.rs", ".parlament.rs",   # Serbia
    ".gov.sk", ".nrsr.sk",        # Slovakia
    ".europa.eu"                  # EU institutions
]

# Topic keywords (EN + local) — add more as needed
TOPIC_KEYWORDS = [
    '"open government"', "transparency", '"access to information"', "whistleblower",
    '"beneficial ownership"', '"open data"', "anticorruption", "anti-corruption",
    "transparentnost", "protikorupcia", "prístup k informáciám",        # SK
    "transparentnost", "antikorupcija", "pristup informacijama",        # SR/BA/HR
    "transparentnost", "prístup k informáciám", "protikorupční",        # CS/CZ
    "Transparenz", "Informationsfreiheit", "Offene Daten"               # DE/AT
]

def _google_news_rss(query: str, lang: str = "en", country: str = "US") -> str:
    q = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={q}&hl={lang}&gl={country}&ceid={country}:{lang}"

def _ts(entry) -> datetime | None:
    # Prefer published_parsed, then updated_parsed
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t: return None
    return datetime.fromtimestamp(time.mktime(t), tz=timezone.utc)

def _domain(url: str) -> str:
    try:
        return urllib.parse.urlsplit(url).netloc.lower()
    except Exception:
        return ""

def _is_verified(domain: str) -> bool:
    return any(domain.endswith(suf) for suf in VERIFIED_SUFFIXES)

def _dedupe(items: List[Dict]) -> List[Dict]:
    seen = set(); out=[]
    for it in items:
        key = it.get("link") or it.get("title")
        if key and key not in seen:
            seen.add(key); out.append(it)
    return out

def _queries_for_country(country: str) -> List[str]:
    names = ALT_NAMES.get(country, [country])
    name_q = " OR ".join([f'"{n}"' for n in names])
    topics = " OR ".join(TOPIC_KEYWORDS)
    # Two queries: (A) verified sources, (B) broad media
    q_verified = f"({topics}) ({name_q}) (site:.gov.* OR site:.gv.at OR site:.europa.eu OR site:parlament.* OR site:parliament.*)"
    q_broad   = f"({topics}) ({name_q})"
    return [q_verified, q_broad]

def _collect(country: str, hours: int) -> Tuple[List[Dict], List[Dict]]:
    """Return (verified_items, all_items) for the country within the window."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    verified, all_items = [], []
    # Try English UI for breadth; Google News respects site: filters
    for q in _queries_for_country(country):
        feed_url = _google_news_rss(q, lang="en", country="US")
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
            all_items.append(item)
            if _is_verified(dom):
                verified.append(item)
    return _dedupe(verified), _dedupe(all_items)

def generate_digest(countries: List[str], hours: int = 24, verified_only: bool = True) -> str:
    """
    Returns Slack-ready Markdown.
    Strategy:
      1) Try verified gov/parliament/EU sources first.
      2) If none found, fall back to reputable media from Google News (same queries).
    """
    header = f"Country updates (past {hours}h)\n"
    blocks = []
    for c in countries:
        v, all_items = _collect(c, hours)
        items = v if (verified_only and v) else all_items
        if not items:
            blocks.append(f"*{c}*\n• No verified items in the past {hours}h.\n")
            continue

        lines = [f"*{c}*"]
        # Limit to top 4 per country to avoid flooding
        for it in items[:4]:
            badge = "✅" if _is_verified(it["domain"]) else "📰"
            t = it["title"]
            link = it["link"]
            src = it["domain"].replace("www.", "")
            lines.append(f"• {badge} {t} — <{link}|{src}>")
        blocks.append("\n".join(lines) + "\n")

    return header + "\n".join(blocks)
