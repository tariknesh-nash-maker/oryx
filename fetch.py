import feedparser, hashlib, time
from datetime import datetime, timedelta, timezone
from dateutil import parser as dtparse

def _normalize(e):
    title = (e.get("title") or "").strip()
    link = (e.get("link") or "").strip()
    summary = (e.get("summary") or "").strip()
    published = e.get("published") or e.get("updated") or ""
    try:
        dt = dtparse.parse(published)
    except Exception:
        dt = None
    return {"title": title, "link": link, "summary": summary, "published": dt}

def _sig(entry):
    h = hashlib.sha256()
    h.update((entry["title"] + "|" + entry["link"]).encode("utf-8", errors="ignore"))
    return h.hexdigest()

def fetch_feed(url):
    fp = feedparser.parse(url, request_headers={"User-Agent": "OryxDigest/1.0"})
    return [_normalize(e) for e in fp.entries]

def filter_last_24h(entries):
    cutoff = datetime.utcnow() - timedelta(days=1)
    out = []
    for e in entries:
        dt = e["published"]
        if not dt:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt >= cutoff.replace(tzinfo=timezone.utc):
            out.append(e)
    return out

def keyword_filter(entries, keywords):
    kws = [k.lower() for k in keywords]
    out = []
    for e in entries:
        blob = (e["title"] + " " + e["summary"]).lower()
        if any(k in blob for k in kws):
            out.append(e)
    return out

def dedupe(entries):
    seen, out = set(), []
    for e in entries:
        s = _sig(e)
        if s in seen:
            continue
        seen.add(s)
        out.append(e)
    return out

def collect(urls, keywords, polite_delay=0.25):
    items = []
    for u in urls:
        try:
            items.extend(fetch_feed(u))
            time.sleep(polite_delay)
        except Exception:
            continue
    items = filter_last_24h(items)
    items = keyword_filter(items, keywords)
    items = dedupe(items)
    items.sort(key=lambda e: e["published"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return items
