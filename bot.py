import asyncio
import os

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

import aggregator
import config

router = Router()

CHAT_ID = os.getenv("CHAT_ID")
seen_ids = set()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я новостной агрегатор.\n\n"
        "Доступные команды:\n"
        "/news — последние новости из всех источников\n"
        "/sources — список источников"
    )


@router.message(Command("news"))
async def cmd_news(message: Message):
    items = aggregator.fetch_all()
    if not items:
        await message.answer("Не удалось получить новости. Попробуйте позже.")
        return
    text = format_items(items)
    await message.answer(text, disable_web_page_preview=True)


@router.message(Command("sources"))
async def cmd_sources(message: Message):
    sources = "\n".join(f"• {f['name']}" for f in config.RSS_FEEDS)
    await message.answer(f"Источники:\n{sources}")


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
            items = aggregator.fetch_all()
            for item in items:
                key = aggregator.item_id(item)
                if key not in seen_ids:
                    seen_ids.add(key)
                    if CHAT_ID and seen_ids:
                        await bot.send_message(
                            CHAT_ID,
                            format_items([item]),
                            disable_web_page_preview=True,
                        )
                    break
        except Exception:
            pass
        await asyncio.sleep(config.CHECK_INTERVAL_MINUTES * 60)


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
