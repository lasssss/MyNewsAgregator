import hashlib

import feedparser

import config


def fetch_feed(feed_url, limit, keywords=None, regions=None):
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
        item = {"title": title, "link": link, "summary": summary}
        if keywords and not match_terms(item, keywords):
            continue
        if regions and not match_terms(item, regions):
            continue
        items.append(item)
    return items


def strip_html(text):
    import re

    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def match_terms(item, terms):
    text = f"{item['title']} {item['summary']}".lower()
    return any(t.lower() in text for t in terms)


def fetch_all(feeds=None, keywords=None, regions=None, pinned=None, show_all=False):
    feeds = feeds or config.RSS_FEEDS
    pinned = pinned or []
    result = []
    for feed in feeds:
        try:
            kw = None if show_all else keywords
            rg = None if show_all else regions
            items = fetch_feed(feed["url"], config.MAX_ITEMS_PER_FEED, kw, rg)
            for item in items:
                item = {"source": feed["name"], **item}
                item["priority"] = feed.get("region") in config.PRIORITY_REGIONS
                item["pinned"] = feed["name"] in pinned
                result.append(item)
        except Exception:
            continue
    result.sort(key=lambda i: (not i["pinned"], not i["priority"]))
    return result


def item_id(item):
    raw = f"{item['source']}:{item['title']}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()
