import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

RSS_FEEDS = [
    {"name": "Lenta.ru", "url": "https://lenta.ru/rss"},
    {"name": "BBC News", "url": "https://feeds.bbci.co.uk/news/rss.xml"},
    {"name": "Habr", "url": "https://habr.com/ru/rss/all/all/"},
    {"name": "VC.ru", "url": "https://vc.ru/rss"},
]

CHECK_INTERVAL_MINUTES = 15

MAX_ITEMS_PER_FEED = 5
