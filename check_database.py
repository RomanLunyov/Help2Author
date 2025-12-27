"""
Диагностический скрипт для проверки базы данных
"""
import asyncio
import aiosqlite
import config


async def check_database():
    """Проверить содержимое базы данных"""
    db_path = config.DATABASE_PATH
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        print("="*70)
        print("📊 ДИАГНОСТИКА БАЗЫ ДАННЫХ")
        print("="*70)
        
        # Проверяем все книги
        for book_type in ['paid', 'free']:
            print(f"\n{'='*70}")
            print(f"📚 ТИП: {book_type.upper()}")
            print(f"{'='*70}\n")
            
            # Все книги этого типа
            async with db.execute(
                """SELECT book_id, title, status, queue_position, confirmed_actions, 
                          actions_limit, user_id, created_at, recommendations_started_at
                   FROM books 
                   WHERE book_type = ?
                   ORDER BY status DESC, queue_position ASC""",
                (book_type,)
            ) as cursor:
                books = await cursor.fetchall()
                
                if not books:
                    print(f"   ❌ Нет книг типа {book_type}")
                    continue
                
                print(f"   Всего книг: {len(books)}\n")
                
                # Группируем по статусам
                by_status = {}
                for book in books:
                    status = book['status']
                    if status not in by_status:
                        by_status[status] = []
                    by_status[status].append(book)
                
                # Выводим по группам
                for status in ['in_recommendations', 'in_queue', 'completed']:
                    if status in by_status:
                        print(f"\n   📌 Статус: {status.upper()}")
                        print(f"   {'─'*66}")
                        
                        for book in by_status[status]:
                            title = book['title'][:40] + '...' if len(book['title']) > 40 else book['title']
                            print(f"   #{book['queue_position']:2d} | ID:{book['book_id']:3d} | {title}")
                            print(f"       User: {book['user_id']}")
                            print(f"       Действия: {book['confirmed_actions']}/{book['actions_limit']}")
                            print(f"       Создана: {book['created_at']}")
                            if book['recommendations_started_at']:
                                print(f"       В рекомендациях с: {book['recommendations_started_at']}")
                            print()
        
        # Проверяем get_recommendations
        print("\n" + "="*70)
        print("🔍 ПРОВЕРКА ФУНКЦИИ get_recommendations()")
        print("="*70 + "\n")
        
        for book_type in ['paid', 'free']:
            print(f"\n📘 {book_type.upper()}:")
            async with db.execute(
                """SELECT b.book_id, b.title, b.status, b.queue_position
                   FROM books b
                   JOIN users u ON b.user_id = u.telegram_id
                   WHERE b.book_type = ? AND b.status = 'in_recommendations'
                   ORDER BY b.queue_position ASC
                   LIMIT ?""",
                (book_type, config.MAX_BOOKS_IN_RECOMMENDATIONS)
            ) as cursor:
                recs = await cursor.fetchall()
                
                if recs:
                    print(f"   Найдено в рекомендациях: {len(recs)}")
                    for rec in recs:
                        title = rec['title'][:50] + '...' if len(rec['title']) > 50 else rec['title']
                        print(f"   ✅ #{rec['queue_position']} - {title}")
                else:
                    print(f"   ❌ Нет книг в статусе 'in_recommendations'")
        
        print("\n" + "="*70)
        print("✅ Диагностика завершена")
        print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(check_database())
