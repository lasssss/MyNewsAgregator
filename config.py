import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

ADMIN_ID = os.getenv("ADMIN_ID", "")
SETTINGS_FILE = os.getenv("SETTINGS_FILE", "settings.json")
RSSHUB_BASE = os.getenv("RSSHUB_BASE", "https://rsshub.app")

RSS_FEEDS = [
    {"name": "Lenta.ru", "url": "https://lenta.ru/rss"},
    {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/rss.xml"},
    {"name": "Habr", "url": "https://habr.com/ru/rss/all/all/"},
    {"name": "VC.ru", "url": "https://vc.ru/rss"},
    {"name": "Sputnik Беларусь", "url": "https://sputnik.by/export/rss2/archive/index.xml", "region": "by"},
    {"name": "БЕЛТА", "url": "https://www.belta.by/rss/news", "region": "by"},
    {"name": "Onliner.by", "url": "https://people.onliner.by/feed", "region": "by"},
    {"name": "Минск-Новости", "url": "https://www.minsknews.by/rss", "region": "by"},
    {"name": "Родная нива (Климовичи)", "url": "https://www.rodniva.by/rss", "region": "by"},
    {"name": "СБ. Беларусь сегодня", "url": "https://rsshub.app/telegram/channel/sbbytoday", "region": "by"},
    {"name": "МогилевТВ (TVR Mogilev)", "url": "https://rsshub.app/telegram/channel/belarus4mogilev", "region": "by"},
]

# Регионы, чьи источники выводятся в приоритете
PRIORITY_REGIONS = ["by"]

CHECK_INTERVAL_MINUTES = 15

MAX_ITEMS_PER_FEED = 5
