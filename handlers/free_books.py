from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import Database
from keyboards import get_main_menu, get_book_card_keyboard, get_back_to_menu_keyboard
import config

router = Router()
db = Database()


@router.message(F.text == "🆓 Бесплатные книги")
async def show_free_books(message: Message):
    """Показать список бесплатных книг"""
    books = await db.get_recommendations("free")
    
    if not books:
        await message.answer(
            "🆓 <b>Бесплатные книги</b>\n\n"
            "Пока нет книг в рекомендациях. Будьте первым, кто добавит свою книгу!",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    await message.answer(
        "🆓 <b>Бесплатные книги</b>\n\n"
        f"Сейчас в рекомендациях:👇",
        parse_mode="HTML"
    )
     
    for book in books:
        remaining_actions = config.ACTIONS_REQUIRED - book['confirmed_actions']
        
        book_text = (
            f"📚 <b>{book['title']}</b>\n"
            f"🆓 Бесплатно\n"
            f"🔗 Ссылка: {book['link']}\n\n"
            f"<b>Сделайте это и здесь появится Ваша книга:</b>\n"
            f"📥 Добавьте книгу в свою библиотеку\n"
            f"⭐️ Поставьте оценку\n"
            f"✍️ Напишите отзыв\n"
            f"📢 Подпишитесь на автора\n\n"
            f"Осталось действий для завершения: <b>{remaining_actions}</b>"
        )
        
        # Проверяем, выполнял ли пользователь действие для этой книги
        user_action = await db.get_user_action_for_book(message.from_user.id, book['book_id'])
        
        if user_action and user_action['status'] in ['confirmed', 'auto_confirmed']:
            # Действие уже подтверждено - показываем статус
            status_emoji = {
                'confirmed': '✅',
                'auto_confirmed': '✅'
            }
            status_text = {
                'confirmed': 'Подтверждено',
                'auto_confirmed': 'Автоподтверждено'
            }
            book_text += f"\n\n{status_emoji.get(user_action['status'], '✅')} Ваш статус: {status_text.get(user_action['status'], 'Подтверждено')}"
            await message.answer(book_text, parse_mode="HTML")
        elif user_action and user_action['status'] == 'pending':
            # Ожидает подтверждения
            book_text += "\n\n⏳ Ваш статус: Ожидает подтверждения"
            await message.answer(book_text, parse_mode="HTML")
        else:
            # Пользователь может выполнить действие (первый раз или после отклонения)
            if book['user_id'] == message.from_user.id:
                book_text += "\n\n<i>Это ваша книга</i>"
                await message.answer(book_text, parse_mode="HTML")
            else:
                if user_action and user_action['status'] == 'rejected':
                    book_text += "\n\n❌ Ваше предыдущее действие было отклонено. Вы можете попробовать снова."
                await message.answer(
                    book_text,
                    parse_mode="HTML",
                    reply_markup=get_book_card_keyboard(book['book_id'], "free", message.from_user.id)
                )


@router.callback_query(F.data.startswith("complete_action:"))
async def complete_free_book_action(callback: CallbackQuery, state: FSMContext):
    """Запрос скриншота для бесплатной книги"""
    _, book_id, user_id = callback.data.split(":")
    book_id = int(book_id)
    user_id = int(user_id)
    
    # Проверяем, не ожидает ли уже подтверждения или подтверждено
    user_action = await db.get_user_action_for_book(callback.from_user.id, book_id)
    if user_action and user_action['status'] in ['pending', 'confirmed', 'auto_confirmed']:
        await callback.answer("Вы уже отправили действие для этой книги!", show_alert=True)
        return
    
    book = await db.get_book_by_id(book_id)
    if not book:
        await callback.answer("Книга не найдена", show_alert=True)
        return
    
    # Сохраняем информацию в состоянии для бесплатных книг
    await state.update_data(book_id=book_id, action_type="rating", book_type="free")
    await state.set_state("waiting_for_screenshot")
    
    # Удаляем предыдущее сообщение с кнопкой
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer(
        f"📸 <b>Отправьте скриншот выполненных действий</b>\n\n"
        f"📚 Книга: {book['title']}\n\n"
        f"<b>Как отправить скриншот:</b>\n"
        f"1️⃣ Сделайте скриншот выполненных действий (оценка, отзыв, подписка)\n"
        f"2️⃣ Нажмите на скрепку 📎 (или кнопку прикрепления) внизу экрана\n"
        f"3️⃣ Выберите фото из галереи или сделайте новое\n"
        f"4️⃣ Отправьте его в этот чат\n\n"
        f"После отправки скриншота автор книги получит уведомление "
        f"и сможет подтвердить ваши действия в течение 12 часов.\n\n"
        f"Если автор не ответит, действия будут подтверждены автоматически.",
        parse_mode="HTML",
        reply_markup=get_back_to_menu_keyboard()
    )
    
    try:
        await callback.answer()
    except:
        pass  # Игнорируем ошибку устаревшего callback


@router.message(F.photo)
async def receive_free_screenshot(message: Message, state: FSMContext):
    """Получение скриншота для бесплатной книги"""
    # Проверяем состояние
    current_state = await state.get_state()
    if current_state != "waiting_for_screenshot":
        return  # Игнорируем фото, если не ждём скриншот
    
    data = await state.get_data()
    book_id = data.get('book_id')
    book_type = data.get('book_type', 'free')
    
    if not book_id:
        await message.answer("Ошибка: не найдена информация о книге")
        await state.clear()
        return
    
    # Получаем ID самого большого фото
    photo_id = message.photo[-1].file_id
    
    # Проверяем, есть ли отклонённое действие - удаляем его
    user_action = await db.get_user_action_for_book(message.from_user.id, book_id)
    if user_action and user_action['status'] == 'rejected':
        await db.delete_action(user_action['action_id'])
    
    # Добавляем новое действие в базу
    action_id = await db.add_action(book_id, message.from_user.id, "rating", photo_id)
    
    if action_id == -1:
        await message.answer(
            "❌ Вы уже отправили действие для этой книги!",
            reply_markup=get_main_menu()
        )
        await state.clear()
        return
    
    # Получаем информацию о книге и владельце
    book = await db.get_book_by_id(book_id)
    
    # Отправляем уведомление владельцу книги
    from keyboards import get_confirm_action_keyboard
    
    notification_text = (
        f"🔔 <b>Пользователь выполнил действия с вашей книгой!</b>\n\n"
        f"📚 Книга: {book['title']}\n"
        f"👤 Пользователь: @{message.from_user.username or 'Аноним'}\n\n"
        f"Пожалуйста, проверьте и подтвердите или отклоните действия в течение 12 часов.\n"
        f"Если вы не ответите, действия будут подтверждены автоматически."
    )
    
    try:
        from main import bot
        await bot.send_photo(
            book['user_id'],
            photo_id,
            caption=notification_text,
            parse_mode="HTML",
            reply_markup=get_confirm_action_keyboard(action_id)
        )
    except:
        pass  # Владелец может быть недоступен
    
    await message.answer(
        "✅ <b>Скриншот отправлен!</b>\n\n"
        "Автор книги получил уведомление и проверит ваши действия. "
        "Вы получите уведомление, когда ваше действие будет подтверждено.\n\n"
        "Спасибо за поддержку автора! 💖",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
    
    await state.clear()
