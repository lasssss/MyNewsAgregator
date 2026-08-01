import os

from aiohttp import web

import settings_store

WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", "8090"))
WEB_TOKEN = os.getenv("WEB_TOKEN", "")


def render_page(settings, message=""):
    kw = ", ".join(settings["keywords"]) if settings["keywords"] else ""
    feeds_rows = ""
    for i, f in enumerate(settings["feeds"]):
        feeds_rows += (
            f"<div class='feed'><span>{i + 1}. <b>{f['name']}</b></span>"
            f"<code>{f['url']}</code>"
            f"<form method='post' action='/remove' style='display:inline'>"
            f"<input type='hidden' name='idx' value='{i}'>"
            f"<button class='danger'>Удалить</button></form></div>"
        )
    if not feeds_rows:
        feeds_rows = "<p>Источников нет</p>"
    broadcast = "checked" if settings["auto_broadcast"] else ""
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
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
.msg {{ background: #d4edda; border: 1px solid #c3e6cb; color: #155724; padding: 10px; border-radius: 4px; margin-bottom: 12px; }}
</style>
</head>
<body>
<h1>DailyNews — настройки</h1>
{('<div class="msg">' + message + '</div>') if message else ''}
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
<h2>Фильтр по ключевым словам</h2>
<form method="post" action="/save">
<label>Ключевые слова (через запятую, пусто — отключить)</label>
<input type="text" name="keywords" value="{kw}">
<h2>Интервал проверки (минуты)</h2>
<input type="number" name="interval" min="1" value="{settings['interval_minutes']}">
<h2>Авто-рассылка</h2>
<label><input type="checkbox" name="broadcast" {broadcast}> Отправлять новые новости в чат</label>
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
        settings_store.save(settings)
        msg = f"Источник удалён: {removed['name']}"
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
    try:
        interval = int(data.get("interval", "15"))
        settings["interval_minutes"] = max(1, interval)
    except ValueError:
        pass
    settings["auto_broadcast"] = data.get("broadcast") == "on"
    settings_store.save(settings)
    return web.Response(text=render_page(settings, "Настройки сохранены"), content_type="text/html")


def build_app():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/login", handle_login)
    app.router.add_post("/login", handle_login)
    app.router.add_post("/add", handle_add)
    app.router.add_post("/remove", handle_remove)
    app.router.add_post("/save", handle_save)
    return app


async def start():
    runner = web.AppRunner(build_app())
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    print(f"Web-интерфейс: http://{WEB_HOST}:{WEB_PORT}")
