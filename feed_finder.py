import re
from urllib.parse import urljoin, urlparse

import feedparser
import requests

COMMON_PATHS = [
    "/rss",
    "/rss.xml",
    "/feed",
    "/feed.xml",
    "/feeds/posts/default",
    "/atom.xml",
    "/index.xml",
    "/rss/",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; DailyNews/1.0; +https://github.com/lasssss/MyNewsAgregator)"
}

TIMEOUT = 15


def find_feed(site_url):
    site_url = normalize(site_url)
    if not site_url:
        return None

    candidates = list(COMMON_PATHS)
    html_feeds = extract_html_feeds(site_url)
    if html_feeds:
        candidates = html_feeds + candidates

    seen = set()
    for path in candidates:
        url = urljoin(site_url, path)
        if url in seen:
            continue
        seen.add(url)
        if is_valid_feed(url):
            return url
    return None


def normalize(url):
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    if not parsed.netloc:
        return None
    return url


def extract_html_feeds(site_url):
    try:
        resp = requests.get(site_url, headers=HEADERS, timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
        links = re.findall(
            r'<link[^>]+rel=["\']alternate["\'][^>]*>|<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]*>',
            resp.text,
            re.IGNORECASE,
        )
        urls = []
        for tag in links:
            href = re.search(r'href=["\']([^"\']+)["\']', tag, re.IGNORECASE)
            if href:
                urls.append(urljoin(site_url, href.group(1)))
        return urls
    except Exception:
        return []


def is_valid_feed(url):
    try:
        parsed = feedparser.parse(requests.get(url, headers=HEADERS, timeout=TIMEOUT).content)
        return bool(parsed.entries) and parsed.feed.get("title")
    except Exception:
        return False
