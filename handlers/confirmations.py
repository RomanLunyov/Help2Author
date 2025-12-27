from aiogram import Router, F
from aiogram.types import CallbackQuery
import logging

from database import Database
from keyboards import get_main_menu

router = Router()
db = Database()
logger = logging.getLogger(__name__)


@router.callback_query(F.data.startswith("confirm_action:"))
async def confirm_user_action(callback: CallbackQuery):
    """Подтверждение или отклонение действия владельцем книги"""
    logger.info(f"=== CONFIRM ACTION HANDLER CALLED ===")
    logger.info(f"Callback data: {callback.data}")
    logger.info(f"User ID: {callback.from_user.id}")
    
    # Сразу отвечаем на callback, чтобы убрать "часики"
    try:
        await callback.answer("Обрабатываю...")
        logger.info("Callback answered successfully")
    except Exception as e:
        logger.error(f"Error answering callback: {e}")
    
    try:
        _, action_id, status = callback.data.split(":")
        action_id = int(action_id)
    except ValueError as e:
        logger.error(f"Error parsing callback data: {e}")
        return
    
    # Получаем информацию о действии
    action = await db.get_action_by_id(action_id)
    logger.info(f"Action data: {action}")
    
    if not action:
        logger.warning(f"Action {action_id} not found")
        try:
            await callback.message.answer("❌ Действие не найдено")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
        return
    
    # Проверяем, что подтверждает владелец книги
    if action['book_owner_id'] != callback.from_user.id:
        logger.warning(f"User {callback.from_user.id} is not book owner {action['book_owner_id']}")
        try:
            await callback.message.answer("❌ Вы не можете подтверждать действия для этой книги")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
        return
    
    # Проверяем, не подтверждено ли уже
    if action['status'] != 'pending':
        logger.info(f"Action {action_id} already processed with status {action['status']}")
        try:
            await callback.message.answer("ℹ️ Это действие уже обработано")
        except Exception as e:
            logger.error(f"Error sending message: {e}")
        return
    
    # Подтверждаем или отклоняем действие
    logger.info(f"Confirming action {action_id} with status {status}")
    await db.confirm_action(action_id, status)
    
    if status == 'confirmed':
        response_text = "✅ Вы подтвердили действие пользователя!"
        user_notification = (
            f"✅ <b>Ваше действие подтверждено!</b>\n\n"
            f"📚 Книга: {action['title']}\n"
            f"👤 Автор: @{callback.from_user.username or 'Аноним'}\n\n"
            f"Лимит продвижения вашей книги увеличен! 🎉"
        )
    else:
        response_text = "❌ Вы отклонили действие пользователя"
        user_notification = (
            f"❌ <b>Ваше действие отклонено</b>\n\n"
            f"📚 Книга: {action['title']}\n"
            f"👤 Автор: @{callback.from_user.username or 'Аноним'}\n\n"
            f"Автор не подтвердил ваше действие."
        )
    
    # Удаляем кнопки из сообщения первым делом
    try:
        await callback.message.edit_reply_markup(reply_markup=None)
        logger.info("Removed inline keyboard")
    except Exception as e:
        logger.error(f"Error removing keyboard: {e}")
    
    # Отправляем подтверждение владельцу книги
    try:
        await callback.message.answer(response_text, parse_mode="HTML")
        logger.info("Sent confirmation to book owner")
    except Exception as e:
        logger.error(f"Error sending confirmation: {e}")
    
    # Отправляем уведомление пользователю
    try:
        from main import bot
        await bot.send_message(
            action['user_id'],
            user_notification,
            parse_mode="HTML"
        )
        logger.info(f"Sent notification to user {action['user_id']}")
    except Exception as e:
        logger.error(f"Error sending user notification: {e}")
    
    # Проверяем, не завершена ли книга
    book_completed = await db.check_book_completion(action['book_id'])
    logger.info(f"Book completion check: {book_completed}")
    
    if book_completed and status == 'confirmed':
        # Уведомляем владельца о завершении
        try:
            await callback.message.answer(
                "🎉 <b>Поздравляем!</b>\n\n"
                f"Ваша книга '{action['title']}' набрала необходимое количество действий "
                f"и завершила продвижение! Теперь вы можете добавить новую книгу.",
                parse_mode="HTML",
                reply_markup=get_main_menu()
            )
            logger.info("Sent book completion message")
        except Exception as e:
            logger.error(f"Error sending completion message: {e}")
