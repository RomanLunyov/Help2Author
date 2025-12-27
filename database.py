import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import config


class Database:
    def __init__(self, db_path: str = config.DATABASE_PATH):
        self.db_path = db_path
        self.timeout = 30.0  # Таймаут для ожидания блокировки БД

    async def connect(self):
        """Инициализация базы данных и создание таблиц"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            # Включаем WAL режим для лучшей конкурентности
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA busy_timeout=30000")  # 30 секунд
            
            # Таблица пользователей
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    telegram_id INTEGER PRIMARY KEY,
                    username TEXT,
                    confirmed_actions INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Таблица книг
            await db.execute("""
                CREATE TABLE IF NOT EXISTS books (
                    book_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    link TEXT NOT NULL,
                    price REAL DEFAULT 0,
                    book_type TEXT NOT NULL CHECK(book_type IN ('paid', 'free')),
                    confirmed_actions INTEGER DEFAULT 0,
                    actions_limit INTEGER DEFAULT 0,
                    queue_position INTEGER,
                    status TEXT DEFAULT 'in_queue' CHECK(status IN ('in_queue', 'in_recommendations', 'completed')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    recommendations_started_at TIMESTAMP,
                    is_admin_book INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id)
                )
            """)
            
            # Добавляем поле recommendations_started_at если его нет (миграция)
            try:
                await db.execute("""
                    ALTER TABLE books 
                    ADD COLUMN recommendations_started_at TIMESTAMP
                """)
            except:
                pass  # Поле уже существует

            # Таблица действий пользователей (для предотвращения накрутки)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_actions (
                    action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL CHECK(action_type IN ('purchase', 'rating', 'review', 'subscribe')),
                    screenshot_file_id TEXT,
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'confirmed', 'rejected', 'auto_confirmed')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    confirmed_at TIMESTAMP,
                    FOREIGN KEY (book_id) REFERENCES books(book_id),
                    FOREIGN KEY (user_id) REFERENCES users(telegram_id),
                    UNIQUE(book_id, user_id)
                )
            """)

            # Таблица очередей (для отслеживания позиций)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS queue_history (
                    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    book_id INTEGER NOT NULL,
                    old_position INTEGER,
                    new_position INTEGER,
                    reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (book_id) REFERENCES books(book_id)
                )
            """)

            await db.commit()

    # ===== ПОЛЬЗОВАТЕЛИ =====
    async def add_user(self, telegram_id: int, username: str = None):
        """Добавить нового пользователя"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            try:
                await db.execute(
                    "INSERT INTO users (telegram_id, username) VALUES (?, ?)",
                    (telegram_id, username)
                )
                await db.commit()
            except aiosqlite.IntegrityError:
                # Пользователь уже существует, обновляем username
                await db.execute(
                    "UPDATE users SET username = ? WHERE telegram_id = ?",
                    (username, telegram_id)
                )
                await db.commit()

    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Получить информацию о пользователе"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM users WHERE telegram_id = ?",
                (telegram_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def increment_user_actions(self, telegram_id: int):
        """Увеличить количество подтверждённых действий пользователя"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            await db.execute(
                "UPDATE users SET confirmed_actions = confirmed_actions + 1 WHERE telegram_id = ?",
                (telegram_id,)
            )
            await db.commit()

    # ===== КНИГИ =====
    async def add_book(self, user_id: int, title: str, link: str, price: float, 
                      book_type: str, is_admin_book: bool = False) -> int:
        """Добавить новую книгу в очередь"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            # Получаем последнюю позицию в очереди для данного типа книги
            async with db.execute(
                """SELECT MAX(queue_position) FROM books 
                   WHERE book_type = ? AND status IN ('in_queue', 'in_recommendations')""",
                (book_type,)
            ) as cursor:
                row = await cursor.fetchone()
                last_position = row[0] if row[0] is not None else 0
                new_position = last_position + 1

            # Добавляем книгу
            cursor = await db.execute(
                """INSERT INTO books (user_id, title, link, price, book_type, 
                   queue_position, actions_limit, is_admin_book) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, title, link, price, book_type, new_position, 
                 0 if is_admin_book else 0, 1 if is_admin_book else 0)
            )
            book_id = cursor.lastrowid

            # Обновляем статус, если книга попала в топ-5
            await self._update_recommendations_status(db, book_type)

            await db.commit()
            return book_id

    async def get_user_book(self, user_id: int, book_type: str = None) -> Optional[Dict]:
        """Получить активную книгу пользователя (опционально по типу)"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            if book_type:
                # Получаем книгу определенного типа
                async with db.execute(
                    """SELECT * FROM books 
                       WHERE user_id = ? AND book_type = ? AND status != 'completed' 
                       ORDER BY created_at DESC LIMIT 1""",
                    (user_id, book_type)
                ) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
            else:
                # Получаем любую активную книгу
                async with db.execute(
                    """SELECT * FROM books 
                       WHERE user_id = ? AND status != 'completed' 
                       ORDER BY created_at DESC LIMIT 1""",
                    (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None

    async def get_user_books(self, user_id: int) -> List[Dict]:
        """Получить все активные книги пользователя"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT * FROM books 
                   WHERE user_id = ? AND status != 'completed' 
                   ORDER BY book_type, created_at DESC""",
                (user_id,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_book_by_id(self, book_id: int) -> Optional[Dict]:
        """Получить книгу по ID"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM books WHERE book_id = ?",
                (book_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_recommendations(self, book_type: str) -> List[Dict]:
        """Получить топ-5 книг для рекомендаций"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT b.*, u.username 
                   FROM books b
                   JOIN users u ON b.user_id = u.telegram_id
                   WHERE b.book_type = ? AND b.status = 'in_recommendations'
                   ORDER BY b.queue_position ASC
                   LIMIT ?""",
                (book_type, config.MAX_BOOKS_IN_RECOMMENDATIONS)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_queue_books(self, book_type: str) -> List[Dict]:
        """Получить все книги в очереди определённого типа"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT b.*, u.username 
                   FROM books b
                   JOIN users u ON b.user_id = u.telegram_id
                   WHERE b.book_type = ? AND b.status IN ('in_queue', 'in_recommendations')
                   ORDER BY b.queue_position ASC""",
                (book_type,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def complete_book(self, book_id: int):
        """Завершить продвижение книги"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            # Получаем информацию о книге
            async with db.execute(
                "SELECT book_type, queue_position FROM books WHERE book_id = ?",
                (book_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return
                book_type, position = row

            # Удаляем книгу (согласно требованиям)
            await db.execute("DELETE FROM books WHERE book_id = ?", (book_id,))

            # Пересчитываем позиции в очереди
            await db.execute(
                """UPDATE books 
                   SET queue_position = queue_position - 1 
                   WHERE book_type = ? AND queue_position > ?""",
                (book_type, position)
            )

            # Обновляем статусы рекомендаций
            await self._update_recommendations_status(db, book_type)

            await db.commit()

    async def _update_recommendations_status(self, db, book_type: str):
        """Обновить статусы книг (топ-5 в рекомендациях)"""
        # Сбрасываем статусы в in_queue для книг, которые выходят из рекомендаций
        await db.execute(
            """UPDATE books 
               SET status = 'in_queue', recommendations_started_at = NULL 
               WHERE book_type = ? AND status = 'in_recommendations'""",
            (book_type,)
        )

        # Получаем топ-5 книг для рекомендаций
        async with db.execute(
            f"""SELECT book_id FROM books 
               WHERE book_type = ? AND status = 'in_queue'
               ORDER BY queue_position ASC 
               LIMIT {config.MAX_BOOKS_IN_RECOMMENDATIONS}""",
            (book_type,)
        ) as cursor:
            book_ids = [row[0] for row in await cursor.fetchall()]
        
        # Устанавливаем статус in_recommendations и время начала рекомендаций
        for book_id in book_ids:
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

    async def move_book_up(self, book_id: int) -> bool:
        """Продвинуть книгу на 1 позицию вверх (если возможно)"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            # Получаем текущую позицию книги
            async with db.execute(
                "SELECT queue_position, book_type FROM books WHERE book_id = ?",
                (book_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return False
                current_position, book_type = row

            if current_position <= 1:
                return False  # Уже на первой позиции

            # Меняем позиции с предыдущей книгой
            await db.execute(
                """UPDATE books 
                   SET queue_position = ? 
                   WHERE book_type = ? AND queue_position = ?""",
                (current_position, book_type, current_position - 1)
            )

            await db.execute(
                "UPDATE books SET queue_position = ? WHERE book_id = ?",
                (current_position - 1, book_id)
            )

            # Записываем историю
            await db.execute(
                """INSERT INTO queue_history (book_id, old_position, new_position, reason)
                   VALUES (?, ?, ?, 'additional_activity')""",
                (book_id, current_position, current_position - 1)
            )

            await db.commit()
            return True

    async def increment_actions_limit(self, user_id: int):
        """Увеличить лимит действий для книги пользователя"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            await db.execute(
                """UPDATE books 
                   SET actions_limit = actions_limit + 1 
                   WHERE user_id = ? AND status != 'completed'""",
                (user_id,)
            )
            await db.commit()

    # ===== ДЕЙСТВИЯ =====
    async def add_action(self, book_id: int, user_id: int, action_type: str = 'purchase', 
                        screenshot_file_id: str = None) -> int:
        """Добавить действие пользователя (покупка, оценка и т.д.)"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            try:
                cursor = await db.execute(
                    """INSERT INTO user_actions (book_id, user_id, action_type, screenshot_file_id)
                       VALUES (?, ?, ?, ?)""",
                    (book_id, user_id, action_type, screenshot_file_id)
                )
                await db.commit()
                return cursor.lastrowid
            except aiosqlite.IntegrityError:
                # Пользователь уже выполнил действие для этой книги
                return -1

    async def confirm_action(self, action_id: int, status: str = 'confirmed'):
        """Подтвердить или отклонить действие"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            # Обновляем статус действия
            await db.execute(
                """UPDATE user_actions 
                   SET status = ?, confirmed_at = CURRENT_TIMESTAMP 
                   WHERE action_id = ?""",
                (status, action_id)
            )

            if status in ['confirmed', 'auto_confirmed']:
                # Получаем информацию о действии
                async with db.execute(
                    "SELECT book_id, user_id FROM user_actions WHERE action_id = ?",
                    (action_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        book_id, user_id = row

                        # Увеличиваем счётчик подтверждённых действий для книги
                        await db.execute(
                            """UPDATE books 
                               SET confirmed_actions = confirmed_actions + 1 
                               WHERE book_id = ?""",
                            (book_id,)
                        )

                        # Увеличиваем счётчик действий пользователя
                        await db.execute(
                            """UPDATE users 
                               SET confirmed_actions = confirmed_actions + 1 
                               WHERE telegram_id = ?""",
                            (user_id,)
                        )

                        # Увеличиваем лимит действий для книги пользователя, совершившего действие
                        # Делаем это в том же соединении, чтобы избежать блокировки БД
                        await db.execute(
                            """UPDATE books 
                               SET actions_limit = actions_limit + 1 
                               WHERE user_id = ? AND status != 'completed'""",
                            (user_id,)
                        )

            await db.commit()

    async def delete_action(self, action_id: int):
        """Удалить действие (для возможности повторной отправки после отклонения)"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            await db.execute(
                "DELETE FROM user_actions WHERE action_id = ?",
                (action_id,)
            )
            await db.commit()

    async def get_pending_actions(self) -> List[Dict]:
        """Получить все ожидающие подтверждения действия"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT ua.*, b.title, b.user_id as book_owner_id, u.username
                   FROM user_actions ua
                   JOIN books b ON ua.book_id = b.book_id
                   JOIN users u ON ua.user_id = u.telegram_id
                   WHERE ua.status = 'pending'
                   ORDER BY ua.created_at ASC"""
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def get_action_by_id(self, action_id: int) -> Optional[Dict]:
        """Получить действие по ID"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """SELECT ua.*, b.title, b.user_id as book_owner_id
                   FROM user_actions ua
                   JOIN books b ON ua.book_id = b.book_id
                   WHERE ua.action_id = ?""",
                (action_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def auto_confirm_old_actions(self):
        """Автоматически подтвердить действия старше 12 часов"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            threshold = datetime.now() - timedelta(hours=config.AUTO_CONFIRM_HOURS)
            
            # Получаем действия для автоподтверждения
            async with db.execute(
                """SELECT action_id FROM user_actions 
                   WHERE status = 'pending' AND created_at < ?""",
                (threshold,)
            ) as cursor:
                action_ids = [row[0] for row in await cursor.fetchall()]

            # Подтверждаем каждое действие
            for action_id in action_ids:
                await self.confirm_action(action_id, 'auto_confirmed')

    async def check_book_completion(self, book_id: int) -> bool:
        """Проверить, набрала ли книга необходимое количество действий"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            async with db.execute(
                "SELECT confirmed_actions FROM books WHERE book_id = ?",
                (book_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row and row[0] >= config.ACTIONS_REQUIRED:
                    await self.complete_book(book_id)
                    return True
                return False

    async def auto_remove_expired_books(self) -> int:
        """Автоматически удалить платные книги, которые не набрали 5 действий за 30 дней"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            threshold = datetime.now() - timedelta(days=config.BOOK_EXPIRATION_DAYS)
            
            # Находим книги для удаления
            async with db.execute(
                """SELECT book_id, title, user_id FROM books 
                   WHERE book_type = 'paid' 
                   AND status = 'in_recommendations'
                   AND confirmed_actions < ?
                   AND recommendations_started_at < ?
                   AND recommendations_started_at IS NOT NULL""",
                (config.ACTIONS_REQUIRED, threshold)
            ) as cursor:
                expired_books = await cursor.fetchall()
            
            removed_count = 0
            for book_id, title, user_id in expired_books:
                # Получаем информацию о книге
                async with db.execute(
                    "SELECT book_type, queue_position FROM books WHERE book_id = ?",
                    (book_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if not row:
                        continue
                    book_type, position = row

                # Удаляем все связанные действия
                await db.execute("DELETE FROM user_actions WHERE book_id = ?", (book_id,))

                # Удаляем книгу
                await db.execute("DELETE FROM books WHERE book_id = ?", (book_id,))

                # Пересчитываем позиции в очереди
                await db.execute(
                    """UPDATE books 
                       SET queue_position = queue_position - 1 
                       WHERE book_type = ? AND queue_position > ?""",
                    (book_type, position)
                )

                # Обновляем статусы рекомендаций
                await self._update_recommendations_status(db, book_type)
                
                removed_count += 1
                print(f"[{datetime.now()}] Удалена книга '{title}' (ID: {book_id}) за неактивность")
            
            await db.commit()
            return removed_count

    async def get_user_action_for_book(self, user_id: int, book_id: int) -> Optional[Dict]:
        """Проверить, выполнял ли пользователь действие для данной книги"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM user_actions WHERE user_id = ? AND book_id = ?",
                (user_id, book_id)
            ) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_user_confirmed_actions_by_type(self, user_id: int) -> Dict[str, int]:
        """Получить количество подтвержденных действий пользователя по типам книг"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            db.row_factory = aiosqlite.Row
            
            # Подсчитываем подтвержденные действия для платных книг
            async with db.execute(
                """SELECT COUNT(*) as count FROM user_actions ua
                   JOIN books b ON ua.book_id = b.book_id
                   WHERE ua.user_id = ? 
                   AND ua.status IN ('confirmed', 'auto_confirmed')
                   AND b.book_type = 'paid'""",
                (user_id,)
            ) as cursor:
                paid_row = await cursor.fetchone()
                paid_count = paid_row['count'] if paid_row else 0
            
            # Подсчитываем подтвержденные действия для бесплатных книг
            async with db.execute(
                """SELECT COUNT(*) as count FROM user_actions ua
                   JOIN books b ON ua.book_id = b.book_id
                   WHERE ua.user_id = ? 
                   AND ua.status IN ('confirmed', 'auto_confirmed')
                   AND b.book_type = 'free'""",
                (user_id,)
            ) as cursor:
                free_row = await cursor.fetchone()
                free_count = free_row['count'] if free_row else 0
            
            return {
                'paid': paid_count,
                'free': free_count,
                'total': paid_count + free_count
            }

    # ===== СТАТИСТИКА =====
    async def get_statistics(self) -> Dict:
        """Получить общую статистику"""
        async with aiosqlite.connect(self.db_path, timeout=self.timeout) as db:
            stats = {}
            
            # Всего пользователей
            async with db.execute("SELECT COUNT(*) FROM users") as cursor:
                stats['total_users'] = (await cursor.fetchone())[0]

            # Всего книг в очередях
            async with db.execute(
                "SELECT COUNT(*) FROM books WHERE status != 'completed'"
            ) as cursor:
                stats['total_books'] = (await cursor.fetchone())[0]

            # Платные книги
            async with db.execute(
                "SELECT COUNT(*) FROM books WHERE book_type = 'paid' AND status != 'completed'"
            ) as cursor:
                stats['paid_books'] = (await cursor.fetchone())[0]

            # Бесплатные книги
            async with db.execute(
                "SELECT COUNT(*) FROM books WHERE book_type = 'free' AND status != 'completed'"
            ) as cursor:
                stats['free_books'] = (await cursor.fetchone())[0]

            # Всего действий
            async with db.execute("SELECT COUNT(*) FROM user_actions") as cursor:
                stats['total_actions'] = (await cursor.fetchone())[0]

            return stats
