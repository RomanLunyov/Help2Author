import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from database import Database
from scheduler import setup_scheduler

# Импорт всех handlers
from handlers import common, paid_books, free_books, add_book, my_book, support, confirmations

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


async def on_startup():
    """Действия при запуске бота"""
    logger.info("Bot is starting...")
    
    # Инициализация базы данных
    db = Database()
    await db.connect()
    logger.info("Database initialized")
    
    # Запуск планировщика
    setup_scheduler()
    logger.info("Scheduler started")
    
    # Уведомление администратора о запуске
    try:
        await bot.send_message(
            config.ADMIN_ID,
            "🤖 Бот успешно запущен и готов к работе!"
        )
    except Exception as e:
        logger.warning(f"Could not send startup message to admin: {e}")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("Bot is shutting down...")
    
    # Уведомление администратора об остановке
    try:
        await bot.send_message(
            config.ADMIN_ID,
            "🤖 Бот остановлен"
        )
    except Exception as e:
        logger.warning(f"Could not send shutdown message to admin: {e}")
    
    await bot.session.close()


async def main():
    """Главная функция запуска бота"""
    # Регистрация роутеров (confirmations должен быть первым для обработки подтверждений)
    dp.include_router(confirmations.router)
    dp.include_router(common.router)
    dp.include_router(paid_books.router)
    dp.include_router(free_books.router)
    dp.include_router(add_book.router)
    dp.include_router(my_book.router)
    dp.include_router(support.router)
    
    # Выполнение действий при запуске
    await on_startup()
    
    try:
        # Запуск polling
        logger.info("Starting polling...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await on_shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Critical error: {e}")
