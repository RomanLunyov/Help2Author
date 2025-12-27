from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню бота"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📘 Платные книги"),
        KeyboardButton(text="🆓 Бесплатные книги")
    )
    builder.row(
        KeyboardButton(text="➕ Добавить свою книгу"),
        KeyboardButton(text="📊 Моя книга")
    )
    builder.row(
        KeyboardButton(text="💖 Поддержать проект"),
        KeyboardButton(text="ℹ️ Как это работает")
    )
    builder.row(
        KeyboardButton(text="💬 Отзывы и предложения")
    )
    return builder.as_markup(resize_keyboard=True)


def get_book_type_keyboard(can_add_paid: bool = True, can_add_free: bool = True) -> InlineKeyboardMarkup:
    """Клавиатура выбора типа книги"""
    builder = InlineKeyboardBuilder()
    
    buttons = []
    if can_add_paid:
        buttons.append(InlineKeyboardButton(text="📘 Платная книга", callback_data="add_book:paid"))
    if can_add_free:
        buttons.append(InlineKeyboardButton(text="🆓 Бесплатная книга", callback_data="add_book:free"))
    
    # Добавляем кнопки в один или два ряда в зависимости от количества
    if len(buttons) == 2:
        builder.row(*buttons)
    elif len(buttons) == 1:
        builder.row(buttons[0])
    
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_book_card_keyboard(book_id: int, book_type: str, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для карточки книги"""
    builder = InlineKeyboardBuilder()
    
    if book_type == "paid":
        builder.row(
            InlineKeyboardButton(
                text="📸 Отправить скриншот покупки", 
                callback_data=f"send_screenshot:{book_id}:{user_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="✅ Действия выполнены", 
                callback_data=f"complete_action:{book_id}:{user_id}"
            )
        )
    
    return builder.as_markup()


def get_confirm_action_keyboard(action_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия владельцем книги"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_action:{action_id}:confirmed"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"confirm_action:{action_id}:rejected")
    )
    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()


def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура возврата в меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    return builder.as_markup()


def get_pagination_keyboard(book_type: str, current_page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Клавиатура пагинации для списка книг"""
    builder = InlineKeyboardBuilder()
    
    buttons = []
    if current_page > 0:
        buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"page:{book_type}:{current_page - 1}"))
    
    buttons.append(InlineKeyboardButton(text=f"{current_page + 1}/{total_pages}", callback_data="current_page"))
    
    if current_page < total_pages - 1:
        buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"page:{book_type}:{current_page + 1}"))
    
    builder.row(*buttons)
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    
    return builder.as_markup()


def get_donation_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для доната"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Перевести на карту", callback_data="donate:card"),
        InlineKeyboardButton(text="💰 Другой способ", callback_data="donate:wallet")
    )
    builder.row(
        InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu")
    )
    return builder.as_markup()


def get_admin_book_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для админа при добавлении книги"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📘 Платная (админ)", callback_data="add_book:paid:admin"),
        InlineKeyboardButton(text="🆓 Бесплатная (админ)", callback_data="add_book:free:admin")
    )
    builder.row(
        InlineKeyboardButton(text="📘 Платная (обычная)", callback_data="add_book:paid"),
        InlineKeyboardButton(text="🆓 Бесплатная (обычная)", callback_data="add_book:free")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()
