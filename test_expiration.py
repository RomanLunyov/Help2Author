"""
Скрипт для тестирования функции удаления просроченных книг
"""
import asyncio
import aiosqlite
from database import Database
from datetime import datetime, timedelta

async def test_expiration():
    db = Database()
    
    print("=== Тест автоматического удаления просроченных книг ===\n")
    
    # Получаем все книги
    print("Книги в базе до проверки:")
    async with aiosqlite.connect(db.db_path) as conn:
        async with conn.execute("SELECT book_id, title, book_type, status, confirmed_actions, recommendations_started_at FROM books") as cursor:
            books = await cursor.fetchall()
            for book in books:
                print(f"ID: {book[0]}, Название: {book[1]}, Тип: {book[2]}, Статус: {book[3]}, Действий: {book[4]}, Начало рекомендаций: {book[5]}")
    
    if not books:
        print("Нет книг в базе")
    
    print("\n--- Запуск проверки просроченных книг ---")
    removed_count = await db.auto_remove_expired_books()
    print(f"Удалено книг: {removed_count}\n")
    
    # Получаем все книги после удаления
    print("Книги в базе после проверки:")
    async with aiosqlite.connect(db.db_path) as conn:
        async with conn.execute("SELECT book_id, title, book_type, status, confirmed_actions, recommendations_started_at FROM books") as cursor:
            books = await cursor.fetchall()
            for book in books:
                print(f"ID: {book[0]}, Название: {book[1]}, Тип: {book[2]}, Статус: {book[3]}, Действий: {book[4]}, Начало рекомендаций: {book[5]}")
    
    if not books:
        print("Нет книг в базе")

if __name__ == "__main__":
    asyncio.run(test_expiration())
