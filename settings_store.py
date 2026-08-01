import json
import os

import config

SETTINGS_FILE = os.getenv("SETTINGS_FILE", "settings.json")

DEFAULTS = {
    "feeds": config.RSS_FEEDS,
    "keywords": [],
    "regions": [],
    "pinned_feeds": [],
    "priority_regions": list(config.PRIORITY_REGIONS),
    "interval_minutes": config.CHECK_INTERVAL_MINUTES,
    "auto_broadcast": True,
    "rsshub_base": config.RSSHUB_BASE,
}


def load():
    settings = dict(DEFAULTS)
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, encoding="utf-8") as f:
                data = json.load(f)
            for key in DEFAULTS:
                if key in data:
                    settings[key] = data[key]
        except Exception:
            pass
    return settings


def save(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def is_admin(user_id):
    admin_id = os.getenv("ADMIN_ID", "")
    if not admin_id:
        return True
    return str(user_id) == str(admin_id)
