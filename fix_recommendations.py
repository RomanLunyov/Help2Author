"""
Скрипт для пересчета статусов книг в рекомендациях
Исправляет проблему с отображением только 1 книги вместо 5
"""
import asyncio
import aiosqlite
import config


async def fix_recommendations():
    """Пересчитать статусы всех книг в рекомендациях"""
    db_path = config.DATABASE_PATH
    
    async with aiosqlite.connect(db_path) as db:
        # Включаем WAL режим
        await db.execute("PRAGMA journal_mode=WAL")
        
        print("🔍 Проверяем текущее состояние базы данных...\n")
        
        # Проверяем книги по типам
        for book_type in ['paid', 'free']:
            print(f"\n📚 Тип книг: {book_type.upper()}")
            
            # Смотрим все книги этого типа
            async with db.execute(
                """SELECT book_id, title, status, queue_position 
                   FROM books 
                   WHERE book_type = ? AND status != 'completed'
                   ORDER BY queue_position ASC""",
                (book_type,)
            ) as cursor:
                books = await cursor.fetchall()
                print(f"   Всего активных книг: {len(books)}")
                
                for book in books:
                    book_id, title, status, position = book
                    print(f"   #{position}: {title[:30]}... - статус: {status}")
        
        print("\n" + "="*60)
        print("🔧 Начинаем исправление статусов...\n")
        
        # Исправляем статусы для каждого типа книг
        for book_type in ['paid', 'free']:
            print(f"\n📘 Обрабатываем {book_type} книги...")
            
            # Шаг 1: Сбрасываем все в in_queue
            await db.execute(
                """UPDATE books 
                   SET status = 'in_queue', recommendations_started_at = NULL 
                   WHERE book_type = ? AND status = 'in_recommendations'""",
                (book_type,)
            )
            
            # Шаг 2: Получаем топ-5 книг
            async with db.execute(
                f"""SELECT book_id, title FROM books 
                   WHERE book_type = ? AND status IN ('in_queue', 'in_recommendations')
                   ORDER BY queue_position ASC 
                   LIMIT {config.MAX_BOOKS_IN_RECOMMENDATIONS}""",
                (book_type,)
            ) as cursor:
                top_books = await cursor.fetchall()
            
            print(f"   Найдено книг для топ-{config.MAX_BOOKS_IN_RECOMMENDATIONS}: {len(top_books)}")
            
            # Шаг 3: Устанавливаем статус in_recommendations для топ-5
            for book_id, title in top_books:
                await db.execute(
                    """UPDATE books 
                       SET status = 'in_recommendations',
                           recommendations_started_at = CASE 
                               WHEN recommendations_started_at IS NULL 
                               THEN CURRENT_TIMESTAMP 
                               ELSE recommendations_started_at 
                           END
                       WHERE book_id = ?""",
                    (book_id,)
                )
                print(f"   ✅ {title[:40]}... -> в рекомендациях")
        
        await db.commit()
        
        print("\n" + "="*60)
        print("✅ Статусы успешно обновлены!\n")
        
        # Проверяем результат
        print("📊 Итоговое состояние:\n")
        for book_type in ['paid', 'free']:
            async with db.execute(
                """SELECT COUNT(*) FROM books 
                   WHERE book_type = ? AND status = 'in_recommendations'""",
                (book_type,)
            ) as cursor:
                count = (await cursor.fetchone())[0]
                print(f"   {book_type.capitalize()}: {count} книг(и) в рекомендациях")


if __name__ == "__main__":
    print("🚀 Запуск скрипта исправления рекомендаций...\n")
    asyncio.run(fix_recommendations())
    print("\n✨ Готово! Теперь перезапустите бота.")
