import asyncio
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

import aggregator
import config
import feed_finder
import settings_store
import web_ui

router = Router()

CHAT_ID = os.getenv("CHAT_ID")
WEB_BASE = os.getenv("WEB_BASE", "http://localhost:8090")
seen_ids = set()

settings = settings_store.load()


def require_admin(func):
    async def wrapper(message: Message, *args, **kwargs):
        if not settings_store.is_admin(message.from_user.id):
            await message.answer("У вас нет прав на эту команду.")
            return
        return await func(message, *args, **kwargs)

    return wrapper


HELP_TEXT = (
    "<b>Доступные команды</b>\n\n"
    "<b>Просмотр:</b>\n"
    "/news — последние новости\n"
    "/news all — все новости (без фильтров)\n"
    "/sources — список источников\n"
    "/settings — текущие настройки\n\n"
    "<b>Настройка:</b>\n"
    "/addfeed URL [название] — добавить источник\n"
    "/removefeed номер — удалить источник\n"
    "/autofeed адрес_сайта — найти RSS автоматически\n"
    "/keywords слово1, слово2 — фильтр по словам\n"
    "/regions регион1, регион2 — фильтр по регионам\n"
    "/priority регион1, регион2 — приоритетные регионы\n\n"
    "<b>Пиннинг:</b>\n"
    "/pin номер — закрепить источник (всегда вверху)\n"
    "/unpin номер — открепить\n"
    "/pins — список закреплённых\n\n"
    "<b>Система:</b>\n"
    "/rsshub адрес — сменить RSSHub\n"
    "/interval минуты — интервал проверки\n"
    "/broadcast on|off — авто-рассылка\n"
    "/help — эта справка"
)


def main_menu_kb(admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📰 Новости", callback_data="menu:news")],
        [InlineKeyboardButton(text="📰 Все новости", callback_data="menu:news_all")],
        [InlineKeyboardButton(text="📡 Источники", callback_data="menu:sources")],
    ]
    if admin:
        rows.append([InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings")])
        rows.append([InlineKeyboardButton(text="ℹ️ Помощь", callback_data="menu:help")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(CommandStart())
async def cmd_start(message: Message):
    admin = settings_store.is_admin(message.from_user.id)
    text = (
        "<b>Новостной агрегатор</b>\n\n"
        "Собираю новости из источников и выдаю по запросу.\n\n"
        "Нажмите кнопку или напишите <b>/news</b> чтобы получить свежие новости.\n\n"
    )
    if admin:
        text += f"Web UI: <a href=\"{WEB_BASE}\">{WEB_BASE}</a>"
    await message.answer(text, reply_markup=main_menu_kb(admin))


@router.callback_query(lambda c: c.data == "menu:news")
async def cb_news(callback: CallbackQuery):
    await callback.answer()
    items = aggregator.fetch_all(
        settings["feeds"], settings["keywords"], settings["regions"],
        pinned=settings.get("pinned_feeds", []),
        priority_regions=settings.get("priority_regions", []),
    )
    if not items:
        await callback.message.answer("Нет новостей. Попробуйте позже или проверьте настройки.")
        return
    chunks = split_items(items, 4000)
    for i, chunk in enumerate(chunks):
        await callback.message.answer(chunk, disable_web_page_preview=True)


@router.callback_query(lambda c: c.data == "menu:news_all")
async def cb_news_all(callback: CallbackQuery):
    await callback.answer()
    items = aggregator.fetch_all(
        settings["feeds"], settings["keywords"], settings["regions"],
        pinned=settings.get("pinned_feeds", []), show_all=True,
        priority_regions=settings.get("priority_regions", []),
    )
    if not items:
        await callback.message.answer("Нет новостей. Попробуйте позже или проверьте настройки.")
        return
    chunks = split_items(items, 4000)
    for i, chunk in enumerate(chunks):
        prefix = "<i>Показано из все источники:</i>\n\n" if i == 0 else ""
        await callback.message.answer(prefix + chunk, disable_web_page_preview=True)


@router.callback_query(lambda c: c.data == "menu:sources")
async def cb_sources(callback: CallbackQuery):
    await callback.answer()
    if not settings["feeds"]:
        await callback.message.answer("Источники не заданы.")
        return
    pinned = settings.get("pinned_feeds", [])
    lines = []
    for i, f in enumerate(settings["feeds"]):
        pin = " [pin]" if f["name"] in pinned else ""
        lines.append(f"{i + 1}. {f['name']}{pin} — {f['url']}")
    await callback.message.answer("Источники:\n" + "\n".join(lines))


@router.callback_query(lambda c: c.data == "menu:settings")
async def cb_settings(callback: CallbackQuery):
    await callback.answer()
    if not settings_store.is_admin(callback.from_user.id):
        await callback.message.answer("У вас нет прав на эту команду.")
        return
    kw = ", ".join(settings["keywords"]) if settings["keywords"] else "не заданы"
    reg = ", ".join(settings["regions"]) if settings["regions"] else "не заданы"
    broadcast = "вкл" if settings["auto_broadcast"] else "выкл"
    pinned = settings.get("pinned_feeds", [])
    pin_list = ", ".join(pinned) if pinned else "нет"
    prio = settings.get("priority_regions", [])
    prio_list = ", ".join(prio) if prio else "нет"
    text = (
        f"<b>Настройки</b>\n"
        f"Источников: {len(settings['feeds'])}\n"
        f"Ключевые слова: {kw}\n"
        f"Страны/регионы: {reg}\n"
        f"Приоритетные: {prio_list}\n"
        f"Закреплено: {pin_list}\n"
        f"RSSHub: {settings['rsshub_base']}\n"
        f"Интервал проверки: {settings['interval_minutes']} мин\n"
        f"Авто-рассылка: {broadcast}"
    )
    await callback.message.answer(text)


@router.callback_query(lambda c: c.data == "menu:help")
async def cb_help(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer(HELP_TEXT)


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(HELP_TEXT)


@router.message(Command("news"))
async def cmd_news(message: Message):
    args = message.text.split()
    show_all = len(args) > 1 and args[1].lower() == "all"
    items = aggregator.fetch_all(
        settings["feeds"], settings["keywords"], settings["regions"],
        pinned=settings.get("pinned_feeds", []), show_all=show_all,
        priority_regions=settings.get("priority_regions", []),
    )
    if not items:
        await message.answer("Нет новостей. Попробуйте позже или проверьте настройки.")
        return
    label = "все источники" if show_all else "мои фильтры"
    header = f"<i>Показано из {label}:</i>\n\n" if show_all else ""
    chunks = split_items(items, 4000)
    for i, chunk in enumerate(chunks):
        prefix = header if i == 0 else ""
        await message.answer(prefix + chunk, disable_web_page_preview=True)


@router.message(Command("sources"))
async def cmd_sources(message: Message):
    if not settings["feeds"]:
        await message.answer("Источники не заданы.")
        return
    pinned = settings.get("pinned_feeds", [])
    lines = []
    for i, f in enumerate(settings["feeds"]):
        pin = " [pin]" if f["name"] in pinned else ""
        lines.append(f"{i + 1}. {f['name']}{pin} — {f['url']}")
    await message.answer("Источники:\n" + "\n".join(lines))


@router.message(Command("settings"))
@require_admin
async def cmd_settings(message: Message):
    kw = ", ".join(settings["keywords"]) if settings["keywords"] else "не заданы"
    reg = ", ".join(settings["regions"]) if settings["regions"] else "не заданы"
    broadcast = "вкл" if settings["auto_broadcast"] else "выкл"
    pinned = settings.get("pinned_feeds", [])
    pin_list = ", ".join(pinned) if pinned else "нет"
    prio = settings.get("priority_regions", [])
    prio_list = ", ".join(prio) if prio else "нет"
    text = (
        f"<b>Настройки</b>\n"
        f"Источников: {len(settings['feeds'])}\n"
        f"Ключевые слова: {kw}\n"
        f"Страны/регионы: {reg}\n"
        f"Приоритетные: {prio_list}\n"
        f"Закреплено: {pin_list}\n"
        f"RSSHub: {settings['rsshub_base']}\n"
        f"Интервал проверки: {settings['interval_minutes']} мин\n"
        f"Авто-рассылка: {broadcast}"
    )
    await message.answer(text)


@router.message(Command("addfeed"))
@require_admin
async def cmd_addfeed(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Использование: /addfeed URL [название]")
        return
    url = args[1].strip()
    name = args[2].strip() if len(args) > 2 else url
    for feed in settings["feeds"]:
        if feed["url"] == url:
            await message.answer("Такой источник уже есть.")
            return
    settings["feeds"].append({"name": name, "url": url})
    settings_store.save(settings)
    await message.answer(f"Источник добавлен: {name}")


@router.message(Command("autofeed"))
@require_admin
async def cmd_autofeed(message: Message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        await message.answer("Использование: /autofeed адрес_сайта [название]")
        return
    site = args[1].strip()
    name = args[2].strip() if len(args) > 2 else ""
    await message.answer("Ищу RSS-ленту, это может занять до минуты...")
    feed_url = await asyncio.to_thread(feed_finder.find_feed, site, settings["rsshub_base"])
    if not feed_url:
        await message.answer("RSS-ленту не удалось найти. Проверь адрес или добавь вручную: /addfeed URL")
        return
    if not name:
        name = feed_url
    for f in settings["feeds"]:
        if f["url"] == feed_url:
            await message.answer(f"Такой источник уже есть: {feed_url}")
            return
    settings["feeds"].append({"name": name, "url": feed_url})
    settings_store.save(settings)
    await message.answer(f"Найдена лента: <a href=\"{feed_url}\">{name}</a>\nИсточник добавлен.")


@router.message(Command("removefeed"))
@require_admin
async def cmd_removefeed(message: Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /removefeed номер (номер из /sources)")
        return
    idx = int(args[1]) - 1
    if not 0 <= idx < len(settings["feeds"]):
        await message.answer("Неверный номер.")
        return
    removed = settings["feeds"].pop(idx)
    pinned = settings.get("pinned_feeds", [])
    if removed["name"] in pinned:
        pinned.remove(removed["name"])
        settings["pinned_feeds"] = pinned
    settings_store.save(settings)
    await message.answer(f"Источник удалён: {removed['name']}")


@router.message(Command("pin"))
@require_admin
async def cmd_pin(message: Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /pin номер (номер из /sources)")
        return
    idx = int(args[1]) - 1
    if not 0 <= idx < len(settings["feeds"]):
        await message.answer("Неверный номер.")
        return
    name = settings["feeds"][idx]["name"]
    pinned = settings.get("pinned_feeds", [])
    if name in pinned:
        await message.answer(f"Источник «{name}» уже закреплён.")
        return
    pinned.append(name)
    settings["pinned_feeds"] = pinned
    settings_store.save(settings)
    await message.answer(f"Закреплён: <b>{name}</b>\nТеперь всегда будет вверху в /news.")


@router.message(Command("unpin"))
@require_admin
async def cmd_unpin(message: Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /unpin номер (номер из /sources)")
        return
    idx = int(args[1]) - 1
    if not 0 <= idx < len(settings["feeds"]):
        await message.answer("Неверный номер.")
        return
    name = settings["feeds"][idx]["name"]
    pinned = settings.get("pinned_feeds", [])
    if name not in pinned:
        await message.answer(f"Источник «{name}» не закреплён.")
        return
    pinned.remove(name)
    settings["pinned_feeds"] = pinned
    settings_store.save(settings)
    await message.answer(f"Откреплён: <b>{name}</b>")


@router.message(Command("pins"))
async def cmd_pins(message: Message):
    pinned = settings.get("pinned_feeds", [])
    if not pinned:
        await message.answer("Нет закреплённых источников. Используйте /pin номер чтобы закрепить.")
        return
    lines = []
    for i, name in enumerate(pinned, 1):
        idx = next((j + 1 for j, f in enumerate(settings["feeds"]) if f["name"] == name), "?")
        lines.append(f"{i}. {name} (источник #{idx})")
    await message.answer("<b>Закреплённые:</b>\n" + "\n".join(lines))


@router.message(Command("keywords"))
@require_admin
async def cmd_keywords(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Использование: /keywords слово1, слово2 (пусто — отключить фильтр)")
        return
    raw = args[1].strip()
    if raw in ("-", "off", "нет"):
        settings["keywords"] = []
    else:
        settings["keywords"] = [k.strip() for k in raw.split(",") if k.strip()]
    settings_store.save(settings)
    await message.answer(f"Ключевые слова: {', '.join(settings['keywords']) or 'не заданы'}")


@router.message(Command("regions"))
@require_admin
async def cmd_regions(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer("Использование: /regions Россия, США (пусто — отключить фильтр)")
        return
    raw = args[1].strip()
    if raw in ("-", "off", "нет"):
        settings["regions"] = []
    else:
        settings["regions"] = [k.strip() for k in raw.split(",") if k.strip()]
    settings_store.save(settings)
    await message.answer(f"Страны/регионы: {', '.join(settings['regions']) or 'не заданы'}")


@router.message(Command("priority"))
@require_admin
async def cmd_priority(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        current = settings.get("priority_regions", [])
        await message.answer(
            f"Текущие приоритетные: {', '.join(current) or 'нет'}\n\n"
            "Источники с этими регионами (region: ...) всегда идут вверху в /news.\n\n"
            "Использование: /priority by, ru (пусто — отключить)\n"
            "Регионы задаются кодом из поля region источника (by, ru, us и т.д.)"
        )
        return
    raw = args[1].strip()
    if raw in ("-", "off", "нет"):
        settings["priority_regions"] = []
    else:
        settings["priority_regions"] = [k.strip().lower() for k in raw.split(",") if k.strip()]
    settings_store.save(settings)
    await message.answer(f"Приоритетные регионы: {', '.join(settings['priority_regions']) or 'не заданы'}")


@router.message(Command("rsshub"))
@require_admin
async def cmd_rsshub(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2 or not args[1].strip():
        await message.answer(
            f"Текущий RSSHub: {settings['rsshub_base']}\n\n"
            "Использование: /rsshub https://адрес-инстанса\n"
            "Публичный rsshub.app часто перегружен, поэтому лучше развернуть свой "
            "RSSHub на NAS (docker) или использовать другой публичный инстанс."
        )
        return
    url = args[1].strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        await message.answer("Адрес должен начинаться с http:// или https://")
        return
    settings["rsshub_base"] = url
    settings_store.save(settings)
    await message.answer(f"RSSHub: {settings['rsshub_base']}")


@router.message(Command("interval"))
@require_admin
async def cmd_interval(message: Message):
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit() or int(args[1]) < 1:
        await message.answer("Использование: /interval минуты (минимум 1)")
        return
    settings["interval_minutes"] = int(args[1])
    settings_store.save(settings)
    await message.answer(f"Интервал проверки: {settings['interval_minutes']} мин")


@router.message(Command("broadcast"))
@require_admin
async def cmd_broadcast(message: Message):
    args = message.text.split()
    if len(args) < 2 or args[1].lower() not in ("on", "off"):
        await message.answer("Использование: /broadcast on|off")
        return
    settings["auto_broadcast"] = args[1].lower() == "on"
    settings_store.save(settings)
    state = "включена" if settings["auto_broadcast"] else "выключена"
    await message.answer(f"Авто-рассылка {state}")


def format_items(items):
    lines = []
    for item in items:
        pin = " *" if item.get("pinned") else ""
        line = f"<b>[{item['source']}{pin}]</b> {item['title']}\n"
        if item["summary"]:
            line += f"{item['summary']}\n"
        if item["link"]:
            line += f"<a href=\"{item['link']}\">Читать</a>\n"
        lines.append(line)
    return "\n".join(lines)


def split_items(items, limit=4000):
    chunks = []
    current = []
    current_len = 0
    for item in items:
        line = format_items([item])
        if current_len + len(line) > limit and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += len(line)
    if current:
        chunks.append("\n".join(current))
    return chunks


async def periodic_check(bot: Bot):
    while True:
        try:
            if settings["auto_broadcast"] and CHAT_ID:
                items = aggregator.fetch_all(
                    settings["feeds"], settings["keywords"], settings["regions"],
                    pinned=settings.get("pinned_feeds", []),
                    priority_regions=settings.get("priority_regions", []),
                )
                for item in items:
                    key = aggregator.item_id(item)
                    if key not in seen_ids:
                        seen_ids.add(key)
                        msg = format_items([item])
                        if len(msg) <= 4096:
                            await bot.send_message(
                                CHAT_ID, msg, disable_web_page_preview=True,
                            )
                        break
        except Exception:
            pass
        await asyncio.sleep(settings["interval_minutes"] * 60)


async def main():
    if not config.BOT_TOKEN:
        print("Ошибка: задайте BOT_TOKEN (см. README)")
        return

    bot = Bot(
        config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    await web_ui.start()
    asyncio.create_task(periodic_check(bot))

    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
