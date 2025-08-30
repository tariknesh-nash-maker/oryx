import feedparser, hashlib, time
from datetime import datetime, timedelta, timezone
from dateutil import parser as dtparse

AFRICA_CASABLANCA = timezone(timedelta(hours=0))  # Morocco is UTC+1 most of year, but Google News timestamps are UTC-like; we filter 24h strictly.

def _normalize_entry(e):
    title = (e.get("title") or "").strip()
    link = (e.get("link") or "").strip()
    summary = (e.get("summary") or "").strip()
    published = e.get("published") or e.get("updated") or ""
    try:
        dt = dtparse.parse(published)
    except Exception:
        dt = None
    return {"title": title, "link": link, "summary": summary, "published": dt, "raw": e}

def _hash(entry):
    h = hashlib.sha256()
    h.update((entry["title"] + "|" + entry["link"]).encode("utf-8", errors="ignore"))
    return h.hexdigest()

def fetch_feed(url, timeout=12):
    # feedparser handles RSS/Atom; no network errors thrown (it embeds them), so we just proceed
    fp = feedparser.parse(url, request_headers={"User-Agent": "OryxNews/1.0"})
    entries = [_normalize_entry(e) for e in fp.entries]
    return entries

def filter_last_24h(entries):
    cutoff = datetime.utcnow() - timedelta(days=1)
    out = []
    for e in entries:
        dt = e["published"]
        if not dt:
            continue
        # ensure UTC-ish comparison
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= cutoff.replace(tzinfo=timezone.utc):
            out.append(e)
    return out

def keyword_filter(entries, keywords):
    kw = [k.lower() for k in keywords]
    out = []
    for e in entries:
        blob = " ".join([e["title"], e["summary"]]).lower()
        if any(k in blob for k in kw):
            out.append(e)
    return out

def dedupe(entries):
    seen, out = set(), []
    for e in entries:
        key = _hash(e)
        if key in seen: 
            continue
        seen.add(key)
        out.append(e)
    return out

def collect(feeds, keywords):
    all_entries = []
    for url in feeds:
        try:
            all_entries.extend(fetch_feed(url))
            time.sleep(0.25)  # be polite
        except Exception:
            continue
    all_entries = filter_last_24h(all_entries)
    all_entries = keyword_filter(all_entries, keywords)
    all_entries = dedupe(all_entries)
    # sort newest first
    all_entries.sort(key=lambda e: e["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return all_entries
