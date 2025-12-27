import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

from database import Database
import config

db = Database()


async def auto_confirm_old_actions():
    """Автоматически подтверждать действия старше 12 часов"""
    try:
        await db.auto_confirm_old_actions()
        print(f"[{datetime.now()}] Auto-confirmation check completed")
    except Exception as e:
        print(f"[{datetime.now()}] Error in auto-confirmation: {e}")


async def check_completed_books():
    """Проверить завершённые книги"""
    try:
        # Получаем все книги в рекомендациях
        for book_type in ['paid', 'free']:
            books = await db.get_recommendations(book_type)
            for book in books:
                await db.check_book_completion(book['book_id'])
        print(f"[{datetime.now()}] Book completion check completed")
    except Exception as e:
        print(f"[{datetime.now()}] Error in book completion check: {e}")


async def remove_expired_paid_books():
    """Удалить просроченные платные книги (не набравшие 5 действий за 30 дней)"""
    try:
        removed_count = await db.auto_remove_expired_books()
        if removed_count > 0:
            print(f"[{datetime.now()}] Removed {removed_count} expired paid book(s)")
        else:
            print(f"[{datetime.now()}] No expired books to remove")
    except Exception as e:
        print(f"[{datetime.now()}] Error in expired books removal: {e}")


def setup_scheduler():
    """Настроить планировщик задач"""
    scheduler = AsyncIOScheduler()
    
    # Автоподтверждение каждые 30 минут
    scheduler.add_job(
        auto_confirm_old_actions,
        'interval',
        minutes=30,
        id='auto_confirm',
        replace_existing=True
    )
    
    # Проверка завершённых книг каждые 15 минут
    scheduler.add_job(
        check_completed_books,
        'interval',
        minutes=15,
        id='check_books',
        replace_existing=True
    )
    
    # Удаление просроченных платных книг каждые 6 часов
    scheduler.add_job(
        remove_expired_paid_books,
        'interval',
        hours=6,
        id='remove_expired',
        replace_existing=True
    )
    
    scheduler.start()
    print("Scheduler started")
    
    return scheduler
