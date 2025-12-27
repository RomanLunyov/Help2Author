import os
from dotenv import load_dotenv

load_dotenv()

# Настройки бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

# Ссылка на чат для отзывов
FEEDBACK_CHAT_LINK = os.getenv('FEEDBACK_CHAT_LINK', 'https://t.me/your_chat')

# Данные для поддержки
SUPPORT_CARD_NUMBER_1 = os.getenv('SUPPORT_CARD_NUMBER_1', '1234 5678 9012 3456')
SUPPORT_CARD_NUMBER_2 = os.getenv('SUPPORT_CARD_NUMBER_2', '9876 5432 1098 7654')
SUPPORT_WALLET_1 = os.getenv('SUPPORT_WALLET_1', 'wallet_address_1')
SUPPORT_WALLET_2 = os.getenv('SUPPORT_WALLET_2', 'wallet_address_2')
SUPPORT_WALLET_3 = os.getenv('SUPPORT_WALLET_3', 'wallet_address_3')

# Параметры системы
MAX_BOOKS_IN_RECOMMENDATIONS = 5  # Максимальное количество книг в рекомендациях одновременно
MAX_PAID_BOOK_PRICE = 200  # Максимальная цена платной книги в рублях
ACTIONS_REQUIRED = 5  # Количество действий для завершения продвижения
AUTO_CONFIRM_HOURS = 12  # Часы для автоподтверждения
MIN_DONATION = 50  # Минимальная сумма доната
BOOK_EXPIRATION_DAYS = 30  # Дней до автоматического удаления книги из рекомендаций

# База данных
DATABASE_PATH = 'books_bot.db'
