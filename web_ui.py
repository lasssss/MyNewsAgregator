import asyncio
import os

from aiohttp import web

import feed_finder
import settings_store

WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8090"))
WEB_TOKEN = os.getenv("WEB_TOKEN", "")


def render_page(settings, message=""):
    kw = ", ".join(settings["keywords"]) if settings["keywords"] else ""
    reg = ", ".join(settings["regions"]) if settings["regions"] else ""
    prio = ", ".join(settings.get("priority_regions", []))
    rsshub = settings.get("rsshub_base", "https://rsshub.app")
    pinned = settings.get("pinned_feeds", [])
    feeds_rows = ""
    for i, f in enumerate(settings["feeds"]):
        is_pinned = f["name"] in pinned
        pin_btn = (
            f"<form method='post' action='/unpin' style='display:inline'>"
            f"<input type='hidden' name='idx' value='{i}'>"
            f"<button class='pin active' title='Открепить'>pin</button></form>"
            if is_pinned else
            f"<form method='post' action='/pin' style='display:inline'>"
            f"<input type='hidden' name='idx' value='{i}'>"
            f"<button class='pin' title='Закрепить'>pin</button></form>"
        )
        feeds_rows += (
            f"<div class='feed'><span>{i + 1}. <b>{f['name']}</b></span>"
            f"<code>{f['url']}</code>"
            f"{pin_btn}"
            f"<form method='post' action='/remove' style='display:inline'>"
            f"<input type='hidden' name='idx' value='{i}'>"
            f"<button class='danger'>Удалить</button></form></div>"
        )
    if not feeds_rows:
        feeds_rows = "<p>Источников нет</p>"
    locations = settings.get("weather_locations", [])
    city_rows = ""
    for i, loc in enumerate(locations):
        city_rows += (
            f"<div class='feed'><span>{i + 1}. <b>{loc['name']}</b></span>"
            f"<code>{loc['lat']}, {loc['lon']}</code>"
            f"<form method='post' action='/removecity' style='display:inline'>"
            f"<input type='hidden' name='idx' value='{i}'>"
            f"<button class='danger'>Удалить</button></form></div>"
        )
    if not city_rows:
        city_rows = "<p>Городов нет</p>"
    broadcast = "checked" if settings["auto_broadcast"] else ""
    wbroadcast = "checked" if settings.get("weather_broadcast") else ""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>DailyNews — настройки</title>
<style>
body {{ font-family: sans-serif; max-width: 640px; margin: 40px auto; padding: 0 16px; color: #333; }}
h1 {{ font-size: 22px; }}
label {{ display: block; margin: 12px 0 4px; font-weight: bold; }}
input[type=text], input[type=number] {{ width: 100%; padding: 8px; box-sizing: border-box; }}
button {{ padding: 8px 16px; margin-top: 12px; cursor: pointer; }}
.feed {{ display: flex; align-items: center; gap: 10px; margin: 6px 0; }}
.feed span {{ min-width: 220px; }}
.feed code {{ flex: 1; font-size: 12px; overflow-wrap: anywhere; }}
.danger {{ background: #d9534f; color: #fff; border: none; border-radius: 4px; }}
.pin {{ background: #6c757d; color: #fff; border: none; border-radius: 4px; padding: 4px 8px; cursor: pointer; font-size: 12px; }}
.pin.active {{ background: #ffc107; color: #333; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
.msg {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 10px; border-radius: 4px; margin-bottom: 12px; }}
</style>
</head>
<body>
<h1>DailyNews — настройки</h1>
{('<div class="msg">' + message + '</div>') if message else ''}
<div class="card">
<h2>Автопоиск RSS-источника</h2>
<form method="post" action="/autofeed">
<label>Адрес сайта</label>
<input type="text" name="site" placeholder="https://example.com" required>
<label>Название</label>
<input type="text" name="name" placeholder="(необязательно)">
<button>Найти и добавить</button>
</form>
</div>
<div class="card">
<h2>Источники</h2>
{feeds_rows}
<form method="post" action="/add">
<label>URL ленты</label>
<input type="text" name="url" placeholder="https://example.com/rss" required>
<label>Название</label>
<input type="text" name="name" placeholder="(необязательно)">
<button>Добавить источник</button>
</form>
</div>
<div class="card">
<h2>Города для погоды</h2>
{city_rows}
<form method="post" action="/addcity">
<label>Название города</label>
<input type="text" name="city" placeholder="Минск" required>
<button>Добавить город</button>
</form>
</div>
<div class="card">
<h2>Фильтр по ключевым словам</h2>
<form method="post" action="/save">
<label>Ключевые слова (через запятую, пусто — отключить)</label>
<input type="text" name="keywords" value="{kw}">
<h2>Фильтр по стране/региону</h2>
<label>Страны/регионы (через запятую, пусто — отключить)</label>
<input type="text" name="regions" value="{reg}" placeholder="Россия, США, ЕС">
<h2>Приоритетные регионы (коды: by, ru, us...)</h2>
<label>Источники с этими регионами всегда вверху в /news</label>
<input type="text" name="priority_regions" value="{prio}" placeholder="by, ru">
<h2>RSSHub (для сайтов без RSS)</h2>
<label>Базовый адрес инстанса RSSHub</label>
<input type="text" name="rsshub" value="{rsshub}" placeholder="https://rsshub.app">
<h2>Интервал проверки (минуты)</h2>
<input type="number" name="interval" min="1" value="{settings['interval_minutes']}">
<h2>Авто-рассылка</h2>
<label><input type="checkbox" name="broadcast" {broadcast}> Отправлять новые новости в чат</label>
<label><input type="checkbox" name="weather_broadcast" {wbroadcast}> Отправлять погоду при изменениях</label>
<button>Сохранить</button>
</form>
</div>
</body>
</html>
"""


def check_auth(request):
    if not WEB_TOKEN:
        return True
    cookie = request.cookies.get("dn_token")
    return cookie == WEB_TOKEN


async def handle_index(request):
    if not check_auth(request):
        raise web.HTTPFound("/login")
    return web.Response(text=render_page(settings_store.load()), content_type="text/html")


async def handle_login(request):
    if request.method == "GET":
        return web.Response(
            text="""<!DOCTYPE html><html><body style="font-family:sans-serif;max-width:320px;margin:80px auto">
            <h2>Вход</h2><form method="post"><input type="password" name="token" placeholder="Пароль" required
            style="width:100%;padding:8px;box-sizing:border-box"><br>
            <button style="margin-top:12px;padding:8px 16px">Войти</button></form></body></html>""",
            content_type="text/html",
        )
    data = await request.post()
    if WEB_TOKEN and data.get("token") == WEB_TOKEN:
        resp = web.HTTPFound("/")
        resp.set_cookie("dn_token", WEB_TOKEN, httponly=True)
        return resp
    return web.Response(text="Неверный пароль", status=403)


async def handle_add(request):
    if not check_auth(request):
        raise web.HTTPFound("/login")
    data = await request.post()
    url = data.get("url", "").strip()
    name = (data.get("name") or "").strip() or url
    settings = settings_store.load()
    if url and not any(f["url"] == url for f in settings["feeds"]):
        settings["feeds"].append({"name": name, "url": url})
        settings_store.save(settings)
        msg = f"Источник добавлен: {name}"
    else:
        msg = "Такой источник уже есть"
    return web.Response(text=render_page(settings, msg), content_type="text/html")


async def handle_autofeed(request):
    if not check_auth(request):
        raise web.HTTPFound("/login")
    data = await request.post()
    site = (data.get("site") or "").strip()
    name = (data.get("name") or "").strip()
    if not site:
        return web.Response(text=render_page(settings_store.load(), "Введите адрес сайта"), content_type="text/html")
    feed_url = await asyncio.to_thread(feed_finder.find_feed, site, settings_store.load()["rsshub_base"])
    settings = settings_store.load()
    if not feed_url:
        msg = f"RSS-ленту для {site} не удалось найти. Добавьте вручную."
    elif any(f["url"] == feed_url for f in settings["feeds"]):
        msg = f"Такой источник уже есть: {feed_url}"
    else:
        if not name:
            name = feed_url
        settings["feeds"].append({"name": name, "url": feed_url})
        settings_store.save(settings)
        msg = f"Найдена лента и добавлена: {name}"
    return web.Response(text=render_page(settings, msg), content_type="text/html")


async def handle_remove(request):
    if not check_auth(request):
        raise web.HTTPFound("/login")
    data = await request.post()
    try:
        idx = int(data.get("idx", "-1"))
    except ValueError:
        idx = -1
    settings = settings_store.load()
    if 0 <= idx < len(settings["feeds"]):
        removed = settings["feeds"].pop(idx)
        pinned = settings.get("pinned_feeds", [])
        if removed["name"] in pinned:
            pinned.remove(removed["name"])
            settings["pinned_feeds"] = pinned
        settings_store.save(settings)
        msg = f"Источник удалён: {removed['name']}"
    else:
        msg = "Неверный номер"
    return web.Response(text=render_page(settings, msg), content_type="text/html")


async def handle_pin(request):
    if not check_auth(request):
        raise web.HTTPFound("/login")
    data = await request.post()
    try:
        idx = int(data.get("idx", "-1"))
    except ValueError:
        idx = -1
    settings = settings_store.load()
    if 0 <= idx < len(settings["feeds"]):
        name = settings["feeds"][idx]["name"]
        pinned = settings.get("pinned_feeds", [])
        if name not in pinned:
            pinned.append(name)
            settings["pinned_feeds"] = pinned
            settings_store.save(settings)
            msg = f"Закреплён: {name}"
        else:
            msg = f"Уже закреплён: {name}"
    else:
        msg = "Неверный номер"
    return web.Response(text=render_page(settings, msg), content_type="text/html")


async def handle_unpin(request):
    if not check_auth(request):
        raise web.HTTPFound("/login")
    data = await request.post()
    try:
        idx = int(data.get("idx", "-1"))
    except ValueError:
        idx = -1
    settings = settings_store.load()
    if 0 <= idx < len(settings["feeds"]):
        name = settings["feeds"][idx]["name"]
        pinned = settings.get("pinned_feeds", [])
        if name in pinned:
            pinned.remove(name)
            settings["pinned_feeds"] = pinned
            settings_store.save(settings)
            msg = f"Откреплён: {name}"
        else:
            msg = f"Не закреплён: {name}"
    else:
        msg = "Неверный номер"
    return web.Response(text=render_page(settings, msg), content_type="text/html")


async def handle_save(request):
    if not check_auth(request):
        raise web.HTTPFound("/login")
    data = await request.post()
    settings = settings_store.load()
    keywords = (data.get("keywords") or "").strip()
    settings["keywords"] = [k.strip() for k in keywords.split(",") if k.strip()]
    regions = (data.get("regions") or "").strip()
    settings["regions"] = [r.strip() for r in regions.split(",") if r.strip()]
    priority_regions = (data.get("priority_regions") or "").strip()
    settings["priority_regions"] = [r.strip().lower() for r in priority_regions.split(",") if r.strip()]
    rsshub = (data.get("rsshub") or "").strip().rstrip("/")
    if rsshub.startswith(("http://", "https://")):
        settings["rsshub_base"] = rsshub
    try:
        interval = int(data.get("interval", "15"))
        settings["interval_minutes"] = max(1, interval)
    except ValueError:
        pass
    settings["auto_broadcast"] = data.get("broadcast") == "on"
    settings["weather_broadcast"] = data.get("weather_broadcast") == "on"
    settings_store.save(settings)
    return web.Response(text=render_page(settings, "Настройки сохранены"), content_type="text/html")


async def handle_addcity(request):
    if not check_auth(request):
        raise web.HTTPFound("/login")
    data = await request.post()
    city = (data.get("city") or "").strip()
    if not city:
        return web.Response(text=render_page(settings_store.load(), "Введите название города"), content_type="text/html")
    import urllib.request
    import json as _json
    import urllib.parse
    settings = settings_store.load()
    try:
        geo_url = (
            f"https://geocoding-api.open-meteo.com/v1/search"
            f"?name={urllib.parse.quote(city)}&count=1&language=ru"
        )
        req = urllib.request.Request(geo_url, headers={"User-Agent": "DailyNews/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            geo = _json.loads(resp.read())
        if not geo.get("results"):
            return web.Response(text=render_page(settings, f"Город «{city}» не найден"), content_type="text/html")
        r = geo["results"][0]
        name = r.get("name", city)
        locs = settings.get("weather_locations", [])
        if any(l["name"].lower() == name.lower() for l in locs):
            return web.Response(text=render_page(settings, f"Город «{name}» уже есть"), content_type="text/html")
        locs.append({"name": name, "lat": r["latitude"], "lon": r["longitude"]})
        settings["weather_locations"] = locs
        settings_store.save(settings)
        msg = f"Добавлен: {name}"
    except Exception:
        msg = "Не удалось найти город"
    return web.Response(text=render_page(settings, msg), content_type="text/html")


async def handle_removecity(request):
    if not check_auth(request):
        raise web.HTTPFound("/login")
    data = await request.post()
    try:
        idx = int(data.get("idx", "-1"))
    except ValueError:
        idx = -1
    settings = settings_store.load()
    locs = settings.get("weather_locations", [])
    if 0 <= idx < len(locs):
        removed = locs.pop(idx)
        settings["weather_locations"] = locs
        settings_store.save(settings)
        msg = f"Удалён: {removed['name']}"
    else:
        msg = "Неверный номер"
    return web.Response(text=render_page(settings, msg), content_type="text/html")


def build_app():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/login", handle_login)
    app.router.add_post("/login", handle_login)
    app.router.add_post("/add", handle_add)
    app.router.add_post("/autofeed", handle_autofeed)
    app.router.add_post("/remove", handle_remove)
    app.router.add_post("/pin", handle_pin)
    app.router.add_post("/unpin", handle_unpin)
    app.router.add_post("/save", handle_save)
    app.router.add_post("/addcity", handle_addcity)
    app.router.add_post("/removecity", handle_removecity)
    return app


async def start():
    runner = web.AppRunner(build_app())
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    print(f"Web-интерфейс: http://{WEB_HOST}:{WEB_PORT}")
