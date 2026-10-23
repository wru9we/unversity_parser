import asyncio

from aiogram import Bot, Dispatcher

import config
from router import router


async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    print("Бот запущен")
    try:
        await dp.start_polling(bot)
    finally:
        print("Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())