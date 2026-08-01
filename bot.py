import asyncio
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

import aggregator
import config
import settings_store

router = Router()

CHAT_ID = os.getenv("CHAT_ID")
seen_ids = set()

settings = settings_store.load()


def require_admin(func):
    async def wrapper(message: Message, *args, **kwargs):
        if not settings_store.is_admin(message.from_user.id):
            await message.answer("У вас нет прав на эту команду.")
            return
        return await func(message, *args, **kwargs)

    return wrapper


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я новостной агрегатор.\n\n"
        "Команды:\n"
        "/news — последние новости\n"
        "/sources — список источников\n"
        "/settings — текущие настройки\n\n"
        "Настройки:\n"
        "/addfeed URL [название] — добавить источник\n"
        "/removefeed номер — удалить источник\n"
        "/keywords слово1, слово2 — фильтр по ключевым словам\n"
        "/interval минуты — интервал авто-проверки\n"
        "/broadcast on|off — вкл/выкл авто-рассылку"
    )


@router.message(Command("news"))
async def cmd_news(message: Message):
    items = aggregator.fetch_all(settings["feeds"], settings["keywords"])
    if not items:
        await message.answer("Нет новостей. Попробуйте позже или проверьте настройки.")
        return
    await message.answer(format_items(items), disable_web_page_preview=True)


@router.message(Command("sources"))
async def cmd_sources(message: Message):
    if not settings["feeds"]:
        await message.answer("Источники не заданы.")
        return
    lines = [f"{i + 1}. {f['name']} — {f['url']}" for i, f in enumerate(settings["feeds"])]
    await message.answer("Источники:\n" + "\n".join(lines))


@router.message(Command("settings"))
@require_admin
async def cmd_settings(message: Message):
    kw = ", ".join(settings["keywords"]) if settings["keywords"] else "не заданы"
    broadcast = "вкл" if settings["auto_broadcast"] else "выкл"
    text = (
        f"<b>Настройки</b>\n"
        f"Источников: {len(settings['feeds'])}\n"
        f"Ключевые слова: {kw}\n"
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
    settings_store.save(settings)
    await message.answer(f"Источник удалён: {removed['name']}")


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
        line = f"<b>[{item['source']}]</b> {item['title']}\n"
        if item["summary"]:
            line += f"{item['summary']}\n"
        if item["link"]:
            line += f"<a href=\"{item['link']}\">Читать</a>\n"
        lines.append(line)
    return "\n".join(lines)


async def periodic_check(bot: Bot):
    while True:
        try:
            if settings["auto_broadcast"] and CHAT_ID:
                items = aggregator.fetch_all(settings["feeds"], settings["keywords"])
                for item in items:
                    key = aggregator.item_id(item)
                    if key not in seen_ids:
                        seen_ids.add(key)
                        await bot.send_message(
                            CHAT_ID,
                            format_items([item]),
                            disable_web_page_preview=True,
                        )
                        break
        except Exception:
            pass
        await asyncio.sleep(settings["interval_minutes"] * 60)


async def main():
    if not config.BOT_TOKEN:
        print("Ошибка: задайте BOT_TOKEN (см. README)")
        return

    bot = Bot(config.BOT_TOKEN, default=None)
    dp = Dispatcher()
    dp.include_router(router)

    asyncio.create_task(periodic_check(bot))

    print("Бот запущен. Нажмите Ctrl+C для остановки.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
