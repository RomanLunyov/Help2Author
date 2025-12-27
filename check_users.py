"""
Проверка пользователей в базе данных
"""
import asyncio
import aiosqlite
import config


async def check_users():
    """Проверить пользователей"""
    db_path = config.DATABASE_PATH
    
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        
        print("="*70)
        print("👥 ПРОВЕРКА ПОЛЬЗОВАТЕЛЕЙ")
        print("="*70 + "\n")
        
        # Все пользователи из таблицы users
        async with db.execute("SELECT * FROM users") as cursor:
            users = await cursor.fetchall()
            print(f"📊 Всего пользователей в таблице users: {len(users)}\n")
            for user in users:
                print(f"   ID: {user['telegram_id']}, Username: {user['username']}")
        
        print("\n" + "="*70)
        print("📚 ПОЛЬЗОВАТЕЛИ С КНИГАМИ")
        print("="*70 + "\n")
        
        # Все уникальные user_id из таблицы books
        async with db.execute(
            "SELECT DISTINCT user_id FROM books ORDER BY user_id"
        ) as cursor:
            book_users = await cursor.fetchall()
            print(f"📊 Уникальных авторов книг: {len(book_users)}\n")
            
            for row in book_users:
                user_id = row['user_id']
                
                # Проверяем, есть ли этот user в таблице users
                async with db.execute(
                    "SELECT * FROM users WHERE telegram_id = ?", (user_id,)
                ) as u_cursor:
                    user = await u_cursor.fetchone()
                
                if user:
                    print(f"   ✅ ID: {user_id} - ЕСТЬ в таблице users")
                else:
                    print(f"   ❌ ID: {user_id} - ОТСУТСТВУЕТ в таблице users!")
                    
                    # Показываем книги этого пользователя
                    async with db.execute(
                        "SELECT book_id, title FROM books WHERE user_id = ?", (user_id,)
                    ) as b_cursor:
                        books = await b_cursor.fetchall()
                        for book in books:
                            print(f"      Книга ID:{book['book_id']} - {book['title'][:50]}")
        
        print("\n" + "="*70)
        print("✅ Проверка завершена")
        print("="*70)


if __name__ == "__main__":
    asyncio.run(check_users())
