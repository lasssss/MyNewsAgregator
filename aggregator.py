import hashlib

import feedparser

import config


def fetch_feed(feed_url, limit):
    parsed = feedparser.parse(feed_url)
    items = []
    if parsed.bozo and not parsed.entries:
        return items
    for entry in parsed.entries[:limit]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        if not title:
            continue
        summary = ""
        if entry.get("summary"):
            summary = strip_html(entry["summary"])[:200]
        items.append({"title": title, "link": link, "summary": summary})
    return items


def strip_html(text):
    import re

    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_all():
    result = []
    for feed in config.RSS_FEEDS:
        try:
            items = fetch_feed(feed["url"], config.MAX_ITEMS_PER_FEED)
            for item in items:
                result.append({"source": feed["name"], **item})
        except Exception:
            continue
    return result


def item_id(item):
    raw = f"{item['source']}:{item['title']}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
