from aiogram import Router, F
from aiogram.types import Message

from keyboards import get_main_menu, get_donation_keyboard
import config

router = Router()


@router.message(F.text == "💖 Поддержать проект")
async def support_project(message: Message):
    """Раздел поддержки проекта"""
    support_text = (
        "💖 <b>Поддержать проект</b>\n\n"
        "Этот бот создан для взаимопомощи авторов и полностью бесплатен. "
        "Если вы хотите поддержать развитие проекта, буду очень благодарен!\n\n"
        f"💰 Минимальная сумма: любая\n\n"
        "<b>💳 Банковские карты:</b>\n"
        f"Карта 1: <code>{config.SUPPORT_CARD_NUMBER_1}</code>\n"
        f"Карта 2: <code>{config.SUPPORT_CARD_NUMBER_2}</code>\n\n"
        "<b>💰 Электронные кошельки:</b>\n"
        f"Кошелёк 1: <code>{config.SUPPORT_WALLET_1}</code>\n"
        f"Кошелёк 2: <code>{config.SUPPORT_WALLET_2}</code>\n"
        f"Кошелёк 3: <code>{config.SUPPORT_WALLET_3}</code>\n\n"
        "💡 <i>Нажмите на номер или ссылку, чтобы скопировать</i>\n\n"
        "Все средства идут на развитие проекта и повышение продаж ваших книг! 🚀\n\n"
        "❤️ Спасибо за поддержку!"
    )
    
    await message.answer(
        support_text,
        parse_mode="HTML",
        reply_markup=get_main_menu()
    )
