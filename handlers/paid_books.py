from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database import Database
from keyboards import get_main_menu, get_book_card_keyboard, get_back_to_menu_keyboard
import config

router = Router()
db = Database()


@router.message(F.text == "📘 Платные книги")
async def show_paid_books(message: Message):
    """Показать список платных книг"""
    books = await db.get_recommendations("paid")
    
    if not books:
        await message.answer(
            "📘 <b>Платные книги</b>\n\n"
            "Пока нет книг в рекомендациях. Будьте первым, кто добавит свою книгу!",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    await message.answer(
        "📘 <b>Платные книги</b>\n\n"
        f"Сейчас в рекомендациях {len(books)} книг(и). "
        "Купите 1 книгу, и сможете добавить свою, Вашу книгу купят 5 других участников! 👇",
        parse_mode="HTML"
    )
    
    for book in books:
        remaining_actions = config.ACTIONS_REQUIRED - book['confirmed_actions']
        
        book_text = (
            f"📚 <b>{book['title']}</b>\n"
            f"💰 Цена: {book['price']:.0f} ₽\n"
            f"🔗 Ссылка: {book['link']}\n\n"
            f"<b>Чтобы помочь:</b>\n"
            f"✅ Купите книгу\n"
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
                    reply_markup=get_book_card_keyboard(book['book_id'], "paid", message.from_user.id)
                )


@router.callback_query(F.data.startswith("send_screenshot:"))
async def request_screenshot(callback: CallbackQuery, state: FSMContext):
    """Запрос скриншота покупки"""
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
    
    # Сохраняем информацию в состоянии
    await state.update_data(book_id=book_id, action_type="purchase")
    await state.set_state("waiting_for_screenshot")
    
    # Удаляем предыдущее сообщение с кнопкой
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer(
        f"📸 <b>Отправьте скриншот покупки книги</b>\n\n"
        f"📚 Книга: {book['title']}\n\n"
        f"<b>Как отправить скриншот:</b>\n"
        f"1️⃣ Сделайте скриншот подтверждения покупки\n"
        f"2️⃣ Нажмите на скрепку 📎 (или кнопку прикрепления) внизу экрана\n"
        f"3️⃣ Выберите фото из галереи или сделайте новое\n"
        f"4️⃣ Отправьте его в этот чат\n\n"
        f"После отправки скриншота автор книги получит уведомление "
        f"и сможет подтвердить вашу покупку в течение 12 часов.\n\n"
        f"Если автор не ответит, покупка будет подтверждена автоматически.",
        parse_mode="HTML",
        reply_markup=get_back_to_menu_keyboard()
    )
    
    try:
        await callback.answer()
    except:
        pass  # Игнорируем ошибку устаревшего callback


@router.message(F.photo)
async def receive_screenshot(message: Message, state: FSMContext):
    """Получение скриншота покупки"""
    # Проверяем состояние
    current_state = await state.get_state()
    if current_state != "waiting_for_screenshot":
        return  # Игнорируем фото, если не ждём скриншот
    
    data = await state.get_data()
    book_id = data.get('book_id')
    book_type = data.get('book_type', 'paid')
    
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
    
    # Добавляем действие в базу
    action_type = "purchase" if book_type == "paid" else "rating"
    action_id = await db.add_action(book_id, message.from_user.id, action_type, photo_id)
    
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
    
    book_type_text = "покупка вашей книги" if book_type == "paid" else "действие с вашей книгой"
    
    notification_text = (
        f"🔔 <b>У Вас {book_type_text}!</b>\n\n"
        f"📚 Книга: {book['title']}\n"
        f"👤 Пользователь: @{message.from_user.username or 'Аноним'}\n\n"
        f"Пожалуйста, подтвердите или отклоните действие в течение 12 часов.\n"
        f"Если вы не ответите, действие будет подтверждено автоматически."
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
    
    success_message = "✅ <b>Скриншот отправлен!</b>\n\n"
    if book_type == "paid":
        success_message += "Автор книги получил уведомление и проверит вашу покупку. "
    else:
        success_message += "Автор книги получил уведомление и проверит ваши действия. "
    success_message += "Вы получите уведомление, когда действие будет подтверждено.\n\n"
    success_message += "Спасибо за поддержку автора! 💖"
    
    await message.answer(
        success_message,
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
    
    await state.clear()


@router.callback_query(F.data == "main_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu()
    )
    await callback.message.delete()
    await callback.answer()
