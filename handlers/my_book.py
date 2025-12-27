from aiogram import Router, F
from aiogram.types import Message

from database import Database
from keyboards import get_main_menu
import config

router = Router()
db = Database()


@router.message(F.text == "📊 Моя книга")
async def show_my_book_status(message: Message):
    """Показать статус книг пользователя"""
    books = await db.get_user_books(message.from_user.id)
    
    if not books:
        await message.answer(
            "📊 <b>Мои книги</b>\n\n"
            "У вас пока нет активных книг в системе.\n"
            "Нажмите '➕ Добавить свою книгу' для добавления.",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    status_emoji = {
        'in_queue': '⏳',
        'in_recommendations': '🔥',
        'completed': '✅'
    }
    status_name = {
        'in_queue': 'В очереди',
        'in_recommendations': 'Книга рекламируется',
        'completed': 'Завершена'
    }
    
    # Формируем информацию по каждой книге
    books_info = []
    for book in books:
        type_emoji = "📘" if book['book_type'] == "paid" else "🆓"
        type_name = "Платная" if book['book_type'] == "paid" else "Бесплатная"
        price_text = f"{book['price']:.0f} ₽" if book['book_type'] == "paid" else "Бесплатно"
        remaining_actions = config.ACTIONS_REQUIRED - book['confirmed_actions']
        
        # Получаем количество книг в очереди перед этой
        queue_books = await db.get_queue_books(book['book_type'])
        books_before = sum(1 for b in queue_books if b['queue_position'] < book['queue_position'])
        
        book_text = (
            f"{type_emoji} <b>{book['title']}</b> ({type_name})\n"
            f"💰 {price_text}\n"
            f"🔗 {book['link']}\n\n"
            f"<b>Статистика:</b>\n"
            f"{status_emoji.get(book['status'], '❓')} Статус: {status_name.get(book['status'], 'Неизвестно')}\n"
            f"📍 Позиция: {book['queue_position']}\n"
            f"👥 Книг впереди: {books_before}\n"
            f"✅ Действий: {book['confirmed_actions']}/{config.ACTIONS_REQUIRED}\n"
            f"📈 Лимит: {book['actions_limit']}\n"
        )
        
        if book['is_admin_book']:
            book_text += "⚡️ Администраторская книга\n"
        
        if book['status'] == 'in_recommendations':
            book_text += f"🔥 <b>В топ-{config.MAX_BOOKS_IN_RECOMMENDATIONS} рекомендаций!</b>\n"
        elif book['status'] == 'in_queue':
            book_text += "⏳ В очереди. Помогайте другим авторам!\n"
        
        if remaining_actions > 0:
            book_text += f"📊 До завершения: <b>{remaining_actions}</b> ещё"
        else:
            book_text += "✅ <b>Набрала необходимое количество действий!</b>"
        
        books_info.append(book_text)
    
    # Формируем итоговое сообщение
    header = "📊 <b>Мои книги</b>\n\n" if len(books) > 1 else "📊 <b>Моя книга</b>\n\n"
    separator = "\n\n" + "─" * 30 + "\n\n"
    status_text = header + separator.join(books_info)
    
    await message.answer(
        status_text,
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
