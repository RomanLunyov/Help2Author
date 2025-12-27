from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import Database
from keyboards import (get_main_menu, get_book_type_keyboard, get_cancel_keyboard,
                      get_admin_book_keyboard)
import config

router = Router()
db = Database()


class AddBookStates(StatesGroup):
    waiting_for_type = State()
    waiting_for_title = State()
    waiting_for_link = State()
    waiting_for_price = State()


@router.message(F.text == "➕ Добавить свою книгу")
async def add_book_start(message: Message, state: FSMContext):
    """Начало процесса добавления книги"""
    # Проверяем, какие книги уже есть у пользователя
    user_books = await db.get_user_books(message.from_user.id)
    
    # Проверяем книги по типам
    has_paid_book = any(book['book_type'] == 'paid' for book in user_books)
    has_free_book = any(book['book_type'] == 'free' for book in user_books)
    
    # Если у пользователя уже есть книги в обоих разделах
    if has_paid_book and has_free_book:
        paid_book = next((book for book in user_books if book['book_type'] == 'paid'), None)
        free_book = next((book for book in user_books if book['book_type'] == 'free'), None)
        
        status_map = {
            'in_queue': 'В очереди',
            'in_recommendations': 'Книга рекламируется',
            'completed': 'Завершено'
        }
        
        await message.answer(
            f"❌ У вас уже есть активные книги в обоих разделах!\n\n"
            f"📘 <b>Платная:</b> {paid_book['title']}\n"
            f"Статус: {status_map.get(paid_book['status'], paid_book['status'])}\n"
            f"Позиция: {paid_book['queue_position']}\n\n"
            f"🆓 <b>Бесплатная:</b> {free_book['title']}\n"
            f"Статус: {status_map.get(free_book['status'], free_book['status'])}\n"
            f"Позиция: {free_book['queue_position']}\n\n"
            f"Дождитесь завершения продвижения одной из книг, чтобы добавить новую.",
            parse_mode="HTML",
            reply_markup=get_main_menu()
        )
        return
    
    # Проверяем лимит действий пользователя
    user = await db.get_user(message.from_user.id)
    
    # Админ может добавлять книги без ограничений
    if message.from_user.id == config.ADMIN_ID:
        await message.answer(
            "➕ <b>Добавление книги (режим администратора)</b>\n\n"
            "Вы можете добавить книгу как администратор (без условий) "
            "или как обычный пользователь.\n\n"
            "Выберите тип книги:",
            parse_mode="HTML",
            reply_markup=get_admin_book_keyboard()
        )
    else:
        # Получаем подтвержденные действия по типам книг
        actions_by_type = await db.get_user_confirmed_actions_by_type(message.from_user.id)
        
        # Обычный пользователь должен помочь другим авторам
        if actions_by_type['total'] > 0:
            # Определяем, какие типы книг можно добавить
            # Учитываем и действия, и наличие уже добавленных книг
            can_add_paid = actions_by_type['paid'] > 0 and not has_paid_book
            can_add_free = actions_by_type['free'] > 0 and not has_free_book
            
            # Если нельзя добавить ни один тип (уже есть книги во всех доступных разделах)
            if not can_add_paid and not can_add_free:
                status_map = {
                    'in_queue': 'В очереди',
                    'in_recommendations': 'Книга рекламируется',
                    'completed': 'Завершено'
                }
                
                existing_books_info = []
                if has_paid_book:
                    paid_book = next((book for book in user_books if book['book_type'] == 'paid'), None)
                    existing_books_info.append(
                        f"📘 <b>Платная:</b> {paid_book['title']}\n"
                        f"Статус: {status_map.get(paid_book['status'], paid_book['status'])}"
                    )
                if has_free_book:
                    free_book = next((book for book in user_books if book['book_type'] == 'free'), None)
                    existing_books_info.append(
                        f"🆓 <b>Бесплатная:</b> {free_book['title']}\n"
                        f"Статус: {status_map.get(free_book['status'], free_book['status'])}"
                    )
                
                books_text = "\n\n".join(existing_books_info)
                
                await message.answer(
                    f"❌ <b>У вас уже есть книга в доступных разделах</b>\n\n"
                    f"{books_text}\n\n"
                    f"Чтобы добавить книгу в другой раздел, выполните действия для книг этого раздела.",
                    parse_mode="HTML",
                    reply_markup=get_main_menu()
                )
                return
            
            # Формируем сообщение о доступных разделах
            available_sections = []
            if can_add_paid:
                available_sections.append(f"📘 Платные книги ({actions_by_type['paid']} действий)")
            if can_add_free:
                available_sections.append(f"🆓 Бесплатные книги ({actions_by_type['free']} действий)")
            
            sections_text = "\n".join(available_sections)
            
            # Добавляем информацию об уже добавленных книгах
            existing_info = ""
            if has_paid_book or has_free_book:
                existing_info = "\n\n<b>Ваши книги в системе:</b>\n"
                if has_paid_book:
                    paid_book = next((book for book in user_books if book['book_type'] == 'paid'), None)
                    existing_info += f"📘 Платная: {paid_book['title']}\n"
                if has_free_book:
                    free_book = next((book for book in user_books if book['book_type'] == 'free'), None)
                    existing_info += f"🆓 Бесплатная: {free_book['title']}\n"
            
            await message.answer(
                "➕ <b>Добавление новой книги</b>\n\n"
                f"Ваши подтвержденные действия:\n{sections_text}{existing_info}\n\n"
                "Вы можете добавить книгу в раздел, для которого вы выполнили действия.\n\n"
                "Выберите тип книги:",
                parse_mode="HTML",
                reply_markup=get_book_type_keyboard(
                    can_add_paid=can_add_paid,
                    can_add_free=can_add_free
                )
            )
            
            # Сохраняем информацию о доступных типах в состоянии
            await state.update_data(
                can_add_paid=can_add_paid,
                can_add_free=can_add_free
            )
        else:
            await message.answer(
                "❌ <b>Недостаточно действий для добавления книги</b>\n\n"
                "Чтобы добавить свою книгу, сначала помогите другим авторам:\n"
                "• Покупайте платные книги → добавите книгу в платный раздел\n"
                "• Для бесплатных книг ставьте оценки и пишите отзывы → добавите книгу в бесплатный раздел\n\n"
                "После подтверждения ваших действий, вы сможете добавить свою книгу.",
                parse_mode="HTML",
                reply_markup=get_main_menu()
            )
            return
    
    await state.set_state(AddBookStates.waiting_for_type)


@router.callback_query(F.data.startswith("add_book:"), AddBookStates.waiting_for_type)
async def book_type_selected(callback: CallbackQuery, state: FSMContext):
    """Выбор типа книги"""
    parts = callback.data.split(":")
    book_type = parts[1]  # paid или free
    is_admin = len(parts) > 2 and parts[2] == "admin"
    
    # Проверяем права доступа для обычных пользователей
    if not is_admin and callback.from_user.id != config.ADMIN_ID:
        data = await state.get_data()
        can_add_paid = data.get('can_add_paid', False)
        can_add_free = data.get('can_add_free', False)
        
        # Проверяем, может ли пользователь добавить книгу выбранного типа
        if book_type == 'paid' and not can_add_paid:
            await callback.answer(
                "❌ Чтобы добавить платную книгу, нужно купить книгу из платного раздела!",
                show_alert=True
            )
            return
        
        if book_type == 'free' and not can_add_free:
            await callback.answer(
                "❌ Чтобы добавить бесплатную книгу, нужно выполнить действия для книги из бесплатного раздела!",
                show_alert=True
            )
            return
    
    await state.update_data(book_type=book_type, is_admin_book=is_admin)
    
    type_name = "платную" if book_type == "paid" else "бесплатную"
    admin_note = " (режим администратора)" if is_admin else ""
    
    await callback.message.edit_text(
        f"📝 Вы выбрали <b>{type_name} книгу</b>{admin_note}\n\n"
        f"Введите название книги:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard()
    )
    
    await state.set_state(AddBookStates.waiting_for_title)
    await callback.answer()


@router.message(AddBookStates.waiting_for_title)
async def book_title_received(message: Message, state: FSMContext):
    """Получение названия книги"""
    title = message.text.strip()
    
    if len(title) < 3:
        await message.answer(
            "❌ Название книги слишком короткое. Минимум 3 символа.\n"
            "Попробуйте ещё раз:"
        )
        return
    
    if len(title) > 200:
        await message.answer(
            "❌ Название книги слишком длинное. Максимум 200 символов.\n"
            "Попробуйте ещё раз:"
        )
        return
    
    await state.update_data(title=title)
    await message.answer(
        f"✅ Название: <b>{title}</b>\n\n"
        f"Теперь отправьте ссылку на книгу:",
        parse_mode="HTML"
    )
    
    await state.set_state(AddBookStates.waiting_for_link)


@router.message(AddBookStates.waiting_for_link)
async def book_link_received(message: Message, state: FSMContext):
    """Получение ссылки на книгу"""
    link = message.text.strip()
    
    # Проверяем минимальную длину ссылки
    if len(link) < 3:
        await message.answer(
            "❌ Ссылка слишком короткая. Пожалуйста, отправьте корректную ссылку.\n"
            "Попробуйте ещё раз:"
        )
        return
    
    data = await state.get_data()
    book_type = data.get('book_type')
    
    await state.update_data(link=link)
    
    if book_type == "paid":
        await message.answer(
            f"✅ Ссылка сохранена\n\n"
            f"Теперь укажите цену книги в рублях:",
            parse_mode="HTML"
        )
        await state.set_state(AddBookStates.waiting_for_price)
    else:
        # Для бесплатных книг цена = 0
        await finalize_book_addition(message, state, 0)


async def finalize_book_addition(message: Message, state: FSMContext, price: float):
    """Завершение добавления книги"""
    data = await state.get_data()
    title = data.get('title')
    link = data.get('link')
    book_type = data.get('book_type')
    is_admin_book = data.get('is_admin_book', False)
    
    # Добавляем книгу в базу
    book_id = await db.add_book(
        user_id=message.from_user.id,
        title=title,
        link=link,
        price=price,
        book_type=book_type,
        is_admin_book=is_admin_book
    )
    
    # Получаем информацию о книге
    book = await db.get_book_by_id(book_id)
    
    type_emoji = "📘" if book_type == "paid" else "🆓"
    type_name = "Платная" if book_type == "paid" else "Бесплатная"
    price_text = f"{price:.0f} ₽" if book_type == "paid" else "Бесплатно"
    admin_note = "\n\n⚡️ Книга добавлена в режиме администратора" if is_admin_book else ""
    
    await message.answer(
        f"🎉 <b>Ваша книга добавлена в очередь рекомендаций!</b>\n\n"
        f"{type_emoji} <b>{title}</b>\n"
        f"💰 {price_text}\n"
        f"🔗 {link}\n\n"
        f"Статус: <b>в очереди</b>\n"
        f"Позиция: <b>{book['queue_position']}</b>\n"
        f"Тип: {type_name}{admin_note}\n\n"
        f"Ваша книга будет показана в рекомендациях, когда дойдёт очередь. "
        f"Продолжайте помогать другим авторам, чтобы быстрее продвинуться!",
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
    
    await state.clear()


@router.message(AddBookStates.waiting_for_price)
async def book_price_received(message: Message, state: FSMContext):
    """Получение цены книги"""
    try:
        price = float(message.text.strip().replace(',', '.'))
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректную цену (число).\n"
            "Например: 99 или 149.99"
        )
        return
    
    if price < 0:
        await message.answer("❌ Цена не может быть отрицательной")
        return
    
    await finalize_book_addition(message, state, price)


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено",
        reply_markup=None
    )
    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_menu()
    )
    await callback.answer()
