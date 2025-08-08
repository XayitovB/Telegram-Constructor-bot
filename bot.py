"""
Professional Telegram Bot with Admin Features
Button-only interface with comprehensive management capabilities.
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from core.config import settings
from core.database import db, User
from core.logging import setup_logging, get_logger, log_admin_action
from core.languages import get_text, get_language_name, SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE
from ui.keyboards import (
    get_user_keyboard, MainKeyboards, AdminKeyboards,
    BroadcastKeyboards, NavigationKeyboards, LanguageKeyboards,
    create_user_list_keyboard
)
from ui.formatters import (
    MessageFormatter, DataExporter, PaginationHelper
)

# Get logger (setup will be done by run.py)
logger = get_logger(__name__)

# Localized button labels for matching user clicks
MY_BOTS_LABELS = {get_text("btn_my_bots", code) for code in SUPPORTED_LANGUAGES.keys()}
ADD_BOTS_LABELS = {get_text("btn_add_bots", code) for code in SUPPORTED_LANGUAGES.keys()}
CHANGE_LANG_LABELS = {get_text("btn_change_language", code) for code in SUPPORTED_LANGUAGES.keys()}
BACK_MAIN_LABELS = {get_text("btn_back_main", code) for code in SUPPORTED_LANGUAGES.keys()}

# Initialize bot and dispatcher
bot = Bot(token=settings.bot_token, parse_mode="Markdown")
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# States for FSM
class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    confirming = State()

class UserSearchStates(StatesGroup):
    waiting_for_query = State()

class BotManagementStates(StatesGroup):
    waiting_for_bot_name = State()
    waiting_for_bot_token = State()
    waiting_for_bot_description = State()
    confirming_bot_submission = State()

class AdminMessageStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_priority = State()

class LanguageSelectionStates(StatesGroup):
    selecting_language = State()

# Global data storage
broadcast_data: Dict[int, Dict[str, Any]] = {}
user_sessions: Dict[int, Dict[str, Any]] = {}


class BotService:
    """Professional bot service with comprehensive functionality."""
    
    @staticmethod
    async def update_user(message: Message) -> User:
        """Update user information in database."""
        user_data = {
            'user_id': message.from_user.id,
            'username': message.from_user.username,
            'first_name': message.from_user.first_name,
            'last_name': message.from_user.last_name
        }
        
        try:
            user = await db.add_or_update_user(user_data)
            await db.log_message(message.from_user.id, "interaction", message.text or "button_press")
            
            if user:
                logger.info(f"User {user.user_id} ({user.display_name}) interacted with bot")
                return user
            else:
                # Create a default user if database operation fails
                logger.warning(f"Failed to get user {message.from_user.id} from database, creating default")
                return User(
                    user_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    is_admin=message.from_user.id in settings.get_admin_ids(),
                    language=None
                )
        except Exception as e:
            logger.error(f"Error updating user {message.from_user.id}: {e}")
            # Return a default user to prevent crashes
            return User(
                user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                is_admin=message.from_user.id in settings.get_admin_ids(),
                language=None
            )
    
    @staticmethod
    async def notify_admins_new_user(user: User) -> None:
        """Notify all admins about new user registration."""
        try:
            admin_ids = settings.get_admin_ids()
            if not admin_ids:
                logger.warning("No admin IDs configured for new user notifications")
                return
            
            # Create notification message
            notification_text = MessageFormatter.format_new_user_notification(user)
            
            # Send notification to all admins
            for admin_id in admin_ids:
                try:
                    await bot.send_message(
                        admin_id,
                        notification_text,
                        parse_mode="Markdown"
                    )
                    logger.info(f"New user notification sent to admin {admin_id}")
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id} about new user: {e}")
            
            # Log the notification
            await db.log_admin_action(
                admin_id=0,  # System notification
                action_type="new_user_notification",
                target_user_id=user.user_id,
                details=f"New user {user.display_name} registered"
            )
            
        except Exception as e:
            logger.error(f"Error notifying admins about new user {user.user_id}: {e}")
    
    @staticmethod
    async def check_admin(user_id: int) -> bool:
        """Check if user has admin privileges."""
        user = await db.get_user(user_id)
        return user and user.is_admin
    
    @staticmethod
    async def send_main_menu(message: Message, text: str = None) -> None:
        """Send main menu to user."""
        user = await BotService.update_user(message)
        
        if not text:
            text = MessageFormatter.format_welcome_message(
                user.full_name, 
                user.is_admin, 
                user.language or DEFAULT_LANGUAGE
            )
        
        await message.answer(
            text,
            reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
        )


# === COMMAND HANDLERS ===

@dp.message(CommandStart())
async def start_handler(message: Message):
    """Handle /start command."""
    # Check if this is a new user
    existing_user = await db.get_user(message.from_user.id)
    is_new_user = existing_user is None
    
    # If new user or user has no language set, show language selection
    if is_new_user or not existing_user or not existing_user.language:
        await message.answer(
            get_text("select_language", DEFAULT_LANGUAGE),
            reply_markup=LanguageKeyboards.get_language_selection()
        )
        
        # If new user, notify admins
        if is_new_user:
            user = await BotService.update_user(message)
            await BotService.notify_admins_new_user(user)
            logger.info(f"New user {message.from_user.id} started the bot - admins notified")
        return
    
    # Send main menu with user's language
    await BotService.send_main_menu(message)
    logger.info(f"Existing user {message.from_user.id} started the bot")


@dp.message(Command('language'))
async def language_command_handler(message: Message):
    """Handle /language command to change language via command."""
    user = await BotService.update_user(message)
    await message.answer(
        get_text("select_language", user.language or DEFAULT_LANGUAGE),
        reply_markup=LanguageKeyboards.get_language_selection()
    )


@dp.message(Command('admin'))
async def admin_command_handler(message: Message):
    """Handle /admin command - only entry point to admin panel."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer(
            "❌ **Access Denied**\n\nThis command requires administrator privileges.",
            reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
        )
        return
    
    # Show admin panel
    await message.answer(
        "👑 **Administrator Panel**\n\nWelcome to the admin control center. Choose an option below:",
        reply_markup=AdminKeyboards.get_admin_panel()
    )
    
    # Log admin access
    await db.log_admin_action(user.user_id, "admin_panel_access", details="Accessed admin panel via /admin command")


# === BUTTON HANDLERS - USER INTERFACE ===

@dp.message(F.text.in_(MY_BOTS_LABELS))
async def my_bots_handler(message: Message):
    """Handle My Bots button - Show user's created bots."""
    user = await BotService.update_user(message)
    user_lang = user.language or DEFAULT_LANGUAGE
    
    # Import bot manager
    from bot_manager import bot_manager
    
    try:
        # Get user's bots
        user_bots = await bot_manager.get_user_bots(user.user_id)
        
        if not user_bots:
            # No bots created yet
            if user_lang == 'uz':
                text = (
                    "🤖 **Mening botlarim**\n\n"
                    "❌ Sizda hali yaratilgan bot yo'q.\n\n"
                    "Yangi bot yaratish uchun **🤖 Bot qo'shish** tugmasini bosing."
                )
            elif user_lang == 'ru':
                text = (
                    "🤖 **Мои боты**\n\n"
                    "❌ У вас пока нет созданных ботов.\n\n"
                    "Для создания нового бота нажмите кнопку **🤖 Добавить бот**."
                )
            else:
                text = (
                    "🤖 **My Bots**\n\n"
                    "❌ You haven't created any bots yet.\n\n"
                    "To create a new bot, click the **🤖 Add Bot** button."
                )
        else:
            # Show user's bots
            if user_lang == 'uz':
                text_lines = ["🤖 **Mening botlarim**\n"]
                for bot_data in user_bots:
                    status_emoji = "🟢" if bot_data['is_running'] else "🔴"
                    status_text = "Ishlamoqda" if bot_data['is_running'] else "To'xtatilgan"
                    created_date = bot_data['created_at'][:10] if bot_data.get('created_at') else 'Noma\'lum'
                    
                    text_lines.append(
                        f"🤖 **{bot_data['bot_name']}**\n"
                        f"📱 @{bot_data.get('bot_username', 'N/A')}\n"
                        f"{status_emoji} {status_text}\n"
                        f"📅 {created_date}\n"
                    )
                text_lines.append(f"\n📊 **Jami:** {len(user_bots)} ta bot")
            elif user_lang == 'ru':
                text_lines = ["🤖 **Мои боты**\n"]
                for bot_data in user_bots:
                    status_emoji = "🟢" if bot_data['is_running'] else "🔴"
                    status_text = "Работает" if bot_data['is_running'] else "Остановлен"
                    created_date = bot_data['created_at'][:10] if bot_data.get('created_at') else 'Неизвестно'
                    
                    text_lines.append(
                        f"🤖 **{bot_data['bot_name']}**\n"
                        f"📱 @{bot_data.get('bot_username', 'N/A')}\n"
                        f"{status_emoji} {status_text}\n"
                        f"📅 {created_date}\n"
                    )
                text_lines.append(f"\n📊 **Всего:** {len(user_bots)} ботов")
            else:
                text_lines = ["🤖 **My Bots**\n"]
                for bot_data in user_bots:
                    status_emoji = "🟢" if bot_data['is_running'] else "🔴"
                    status_text = "Running" if bot_data['is_running'] else "Stopped"
                    created_date = bot_data['created_at'][:10] if bot_data.get('created_at') else 'Unknown'
                    
                    text_lines.append(
                        f"🤖 **{bot_data['bot_name']}**\n"
                        f"📱 @{bot_data.get('bot_username', 'N/A')}\n"
                        f"{status_emoji} {status_text}\n"
                        f"📅 {created_date}\n"
                    )
                text_lines.append(f"\n📊 **Total:** {len(user_bots)} bots")
            
            text = "\n".join(text_lines)
        
        await message.answer(
            text,
            reply_markup=get_user_keyboard(user.is_admin, user_lang)
        )
        
    except Exception as e:
        logger.error(f"Error getting user bots: {e}")
        error_text = (
            "❌ Botlarni yuklashda xatolik yuz berdi." if user_lang == 'uz' else
            "❌ Ошибка при загрузке ботов." if user_lang == 'ru' else
            "❌ Error loading bots."
        )
        await message.answer(
            error_text,
            reply_markup=get_user_keyboard(user.is_admin, user_lang)
        )

@dp.message(F.text.in_(ADD_BOTS_LABELS))
async def add_bots_handler(message: Message, state: FSMContext):
    """Handle Add Bots button - Start bot creation process."""
    user = await BotService.update_user(message)
    
    # Get current user language
    user_lang = user.language or DEFAULT_LANGUAGE
    
    if user_lang == 'uz':
        text = (
            "🤖 **Bot yaratish**\n\n"
            "Yangi bot yaratish uchun botingizning tokenini yuboring.\n\n"
            "**Token olish yo'li:**\n"
            "1. @BotFather ga o'ting\n"
            "2. /newbot buyrug'ini yuboring\n"
            "3. Bot nomini kiriting\n"
            "4. Bot username kiriting\n"
            "5. Tokenni nusxalab, bu yerga yuboring\n\n"
            "⚠️ **Diqqat:** Token maxfiy ma'lumot, boshqalar bilan baham ko'rmang!"
        )
    elif user_lang == 'ru':
        text = (
            "🤖 **Создание бота**\n\n"
            "Для создания нового бота отправьте токен вашего бота.\n\n"
            "**Как получить токен:**\n"
            "1. Перейдите к @BotFather\n"
            "2. Отправьте команду /newbot\n"
            "3. Введите имя бота\n"
            "4. Введите username бота\n"
            "5. Скопируйте токен и отправьте его сюда\n\n"
            "⚠️ **Внимание:** Токен - секретная информация, не делитесь ею с другими!"
        )
    else:
        text = (
            "🤖 **Create Bot**\n\n"
            "To create a new bot, send your bot token.\n\n"
            "**How to get token:**\n"
            "1. Go to @BotFather\n"
            "2. Send /newbot command\n"
            "3. Enter bot name\n"
            "4. Enter bot username\n"
            "5. Copy token and send it here\n\n"
            "⚠️ **Warning:** Token is secret information, don't share it with others!"
        )
    
    await state.set_state(BotManagementStates.waiting_for_bot_token)
    
    await message.answer(
        text,
        reply_markup=MainKeyboards.get_cancel_button()
    )


@dp.message(F.text.in_(CHANGE_LANG_LABELS))
async def change_language_handler(message: Message):
    """Handle Change Language button."""
    user = await BotService.update_user(message)
    await message.answer(
        get_text("select_language", user.language or DEFAULT_LANGUAGE),
        reply_markup=LanguageKeyboards.get_language_selection()
    )

# === ADMIN BUTTON HANDLERS ===

@dp.message(F.text == "📊 Bot Statistics")
async def bot_statistics_handler(message: Message):
    """Handle bot statistics button."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    stats = await db.get_statistics()
    stats_text = MessageFormatter.format_bot_statistics(stats)
    
    await message.answer(
        stats_text,
        reply_markup=AdminKeyboards.get_statistics_menu()
    )
    
    await db.log_admin_action(user.user_id, "view_statistics", details="Viewed bot statistics")


@dp.message(F.text == "📈 Detailed Analytics")
async def detailed_analytics_handler(message: Message):
    """Handle detailed analytics button."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    stats = await db.get_statistics()
    
    detailed_text = f"""
📈 **Detailed Analytics Dashboard**

👥 **User Metrics:**
• Total Users: **{stats.total_users:,}**
• Active Users: **{stats.active_users:,}** ({stats.active_rate:.1f}%)
• Banned Users: **{stats.banned_users:,}**
• New Users Today: **{stats.new_users_today:,}**

💬 **Message Analytics:**
• Messages Today: **{stats.messages_today:,}**
• Total Messages: **{stats.messages_total:,}**
• Avg per User: **{stats.messages_total / max(stats.total_users, 1):.1f}**

👑 **Administration:**
• Admin Count: **{stats.admin_count:,}**
• Admin Ratio: **{(stats.admin_count / max(stats.total_users, 1)) * 100:.1f}%**

🔍 **Health Indicators:**
• User Retention: **{((stats.total_users - stats.banned_users) / max(stats.total_users, 1)) * 100:.1f}%**
• Ban Rate: **{(stats.banned_users / max(stats.total_users, 1)) * 100:.1f}%**
• Activity Score: **{min(100, stats.active_rate + (stats.messages_today / max(stats.total_users, 1)) * 10):.1f}/100**
    """
    
    await message.answer(
        detailed_text,
        reply_markup=AdminKeyboards.get_statistics_menu()
    )
    
    await db.log_admin_action(user.user_id, "view_detailed_analytics", details="Viewed detailed analytics")


@dp.message(F.text == "📢 Send Broadcast")
async def send_broadcast_handler(message: Message):
    """Handle send broadcast button."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    await message.answer(
        "📢 **Broadcast Management**\n\nChoose your broadcast option:",
        reply_markup=BroadcastKeyboards.get_broadcast_menu()
    )


@dp.message(F.text == "⚙️ Bot Settings")
async def bot_settings_handler(message: Message):
    """Handle bot settings button."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    settings_text = f"""
⚙️ **Bot Settings & Configuration**

🤖 **Current Settings:**
• Bot Name: **{settings.bot.name}**
• Users Per Page: **{settings.bot.users_per_page}**
• Broadcast Delay: **{settings.bot.broadcast_delay}s**
• Max Message Length: **{settings.bot.max_message_length}** chars
• Environment: **{settings.environment}**
• Debug Mode: **{'Enabled' if settings.debug else 'Disabled'}**

🔒 **Security Settings:**
• Rate Limiting: **{'Enabled' if settings.security.rate_limit_enabled else 'Disabled'}**
• Max Requests/min: **{settings.security.max_requests_per_minute}**
• Ban Duration: **{settings.security.ban_duration_hours}h**

📊 **Database:**
• Path: **{settings.database_path}**
• Backups: **{'Enabled' if settings.database.backup_enabled else 'Disabled'}**
    """
    
    await message.answer(
        settings_text,
        reply_markup=AdminKeyboards.get_admin_panel()
    )
    
    await db.log_admin_action(user.user_id, "view_settings", details="Viewed bot settings")


# Admin buttons are only accessible via /admin command


# === ADMIN PANEL BUTTON HANDLERS ===

@dp.message(F.text == "👥 View All Users")
async def view_all_users_handler(message: Message):
    """Handle view all users button."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    users = await db.get_users(limit=settings.bot.users_per_page)
    
    if not users:
        await message.answer(
            "👥 **No Users Found**\n\nThe database is empty.",
            reply_markup=AdminKeyboards.get_admin_panel()
        )
        return
    
    # Paginate users
    paginated_users, page, total_pages, total_items = PaginationHelper.paginate_list(users)
    
    # Format user list
    text_lines = [
        "👥 **All Users**\n",
        PaginationHelper.create_page_info(page, total_pages, total_items),
        ""
    ]
    
    for user_item in paginated_users:
        text_lines.append(MessageFormatter.format_user_summary(user_item))
        text_lines.append("")
    
    await message.answer(
        "\n".join(text_lines),
        reply_markup=create_user_list_keyboard(paginated_users, page, total_pages)
    )
    
    await db.log_admin_action(user.user_id, "view_all_users", details=f"Viewed all users (page {page})")


@dp.message(F.text == "✅ View Active Users")
async def view_active_users_handler(message: Message):
    """Handle view active users button."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    users = await db.get_users(active_only=True, limit=settings.bot.users_per_page)
    
    if not users:
        await message.answer(
            "✅ **No Active Users Found**",
            reply_markup=AdminKeyboards.get_admin_panel()
        )
        return
    
    # Format and send user list
    text_lines = ["✅ **Active Users**\n"]
    
    for user_item in users:
        text_lines.append(MessageFormatter.format_user_summary(user_item))
        text_lines.append("")
    
    await message.answer(
        "\n".join(text_lines),
        reply_markup=create_user_list_keyboard(users, 1, 1)
    )
    
    await db.log_admin_action(user.user_id, "view_active_users", details=f"Viewed {len(users)} active users")


@dp.message(F.text == "👑 View Admins")
async def view_admins_handler(message: Message):
    """Handle view admins button."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    admins = await db.get_users(admin_only=True)
    
    if not admins:
        await message.answer(
            "👑 **No Administrators Found**",
            reply_markup=AdminKeyboards.get_admin_panel()
        )
        return
    
    text_lines = ["👑 **Bot Administrators**\n"]
    
    for admin in admins:
        text_lines.append(MessageFormatter.format_user_summary(admin))
        text_lines.append("")
    
    await message.answer(
        "\n".join(text_lines),
        reply_markup=MainKeyboards.get_back_button(user.language or DEFAULT_LANGUAGE)
    )
    
    await db.log_admin_action(user.user_id, "view_admins", details=f"Viewed {len(admins)} administrators")


# === BROADCAST HANDLERS ===

@dp.message(F.text == "📝 Compose Message")
async def compose_message_handler(message: Message, state: FSMContext):
    """Handle compose message for broadcast."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    await message.answer(
        "📝 **Compose Broadcast Message**\n\nPlease send me the message you want to broadcast to all users.\n\n" +
        "💡 **Tips:**\n" +
        "• Keep messages clear and concise\n" +
        "• Use markdown formatting if needed\n" +
        "• Maximum length: 4000 characters",
        reply_markup=MainKeyboards.get_cancel_button()
    )
    
    await state.set_state(BroadcastStates.waiting_for_message)


@dp.message(BroadcastStates.waiting_for_message)
async def broadcast_message_received(message: Message, state: FSMContext):
    """Handle received broadcast message."""
    if message.text == "❌ Cancel Operation":
        user = await BotService.update_user(message)
        await message.answer(
            "❌ **Broadcast Cancelled**",
            reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
        )
        await state.clear()
        return
    
    if not message.text or len(message.text) > settings.bot.max_message_length:
        await message.answer(
            f"❌ **Invalid Message**\n\nMessage must be text and under {settings.bot.max_message_length} characters."
        )
        return
    
    # Get recipient count
    recipients = await db.get_broadcast_users()
    
    # Store broadcast data
    broadcast_data[message.from_user.id] = {
        'message': message.text,
        'recipients': len(recipients)
    }
    
    # Show preview
    preview_text = MessageFormatter.format_broadcast_preview(message.text, len(recipients))
    
    await message.answer(
        preview_text,
        reply_markup=AdminKeyboards.get_broadcast_confirmation(len(recipients))
    )
    
    await state.set_state(BroadcastStates.confirming)


# === NAVIGATION HANDLERS ===

@dp.message(F.text.in_(BACK_MAIN_LABELS))
async def back_to_main_handler(message: Message):
    """Handle back to main menu button."""
    user = await BotService.update_user(message)
    back_text = get_text("back_main_menu", user.language or DEFAULT_LANGUAGE)
    await BotService.send_main_menu(message, back_text)


@dp.message(F.text == "🔙 Back to Admin Panel")
async def back_to_admin_handler(message: Message):
    """Handle back to admin panel button."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    await message.answer(
        "👑 **Administrator Panel**\n\nChoose an option below:",
        reply_markup=AdminKeyboards.get_admin_panel()
    )


# === CALLBACK QUERY HANDLERS ===

@dp.callback_query(F.data == "users_export")
async def export_users_callback(callback: CallbackQuery):
    """Handle export users callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    users = await db.get_users()
    
    if not users:
        await callback.answer("No users to export", show_alert=True)
        return
    
    # Create CSV export
    csv_file = DataExporter.create_users_csv(users)
    
    await callback.message.answer_document(
        csv_file,
        caption=f"📊 **Users Export**\n\n• Total users: {len(users)}\n• Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    
    await callback.answer("✅ Export generated!")
    await db.log_admin_action(user_id, "export_users", details=f"Exported {len(users)} users to CSV")


@dp.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm_callback(callback: CallbackQuery, state: FSMContext):
    """Handle broadcast confirmation."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    if user_id not in broadcast_data:
        await callback.answer("❌ Broadcast data not found", show_alert=True)
        return
    
    data = broadcast_data[user_id]
    message_text = data['message']
    
    # Get recipients
    recipient_ids = await db.get_broadcast_users()
    
    await callback.message.edit_text(
        "📤 **Sending Broadcast**\n\nPlease wait while the message is being sent to all users..."
    )
    
    # Send broadcast with bounded concurrency to improve throughput safely
    sent_count = 0
    failed_count = 0
    semaphore = asyncio.Semaphore(10)  # limit concurrent sends

    async def send_to_user(recipient_id: int):
        nonlocal sent_count, failed_count
        async with semaphore:
            try:
                await bot.send_message(recipient_id, message_text)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to {recipient_id}: {e}")
                failed_count += 1
            finally:
                # gentle pacing to avoid hitting hard limits
                await asyncio.sleep(settings.bot.broadcast_delay)

    await asyncio.gather(*(send_to_user(rid) for rid in recipient_ids))
    
    # Log broadcast
    await db.log_broadcast(user_id, message_text, sent_count, failed_count)
    
    # Show results
    result_text = MessageFormatter.format_broadcast_result(sent_count, failed_count, sent_count + failed_count)
    
    await callback.message.edit_text(result_text)
    
    # Cleanup
    del broadcast_data[user_id]
    await state.clear()
    
    await db.log_admin_action(user_id, "broadcast_sent", details=f"Sent to {sent_count} users, {failed_count} failed")


# === LANGUAGE SELECTION HANDLERS ===

@dp.callback_query(F.data.startswith("lang_"))
async def language_selection_callback(callback: CallbackQuery):
    """Handle language selection."""
    user_id = callback.from_user.id
    
    try:
        selected_language = callback.data.split("_")[1]
        
        if selected_language not in SUPPORTED_LANGUAGES:
            await callback.answer("❌ Invalid language", show_alert=True)
            return
        
        # Get existing user data and update language
        user_data = {
            'user_id': user_id,
            'username': callback.from_user.username,
            'first_name': callback.from_user.first_name,
            'last_name': callback.from_user.last_name,
            'language': selected_language
        }
        
        user = await db.add_or_update_user(user_data)
        
        # Send confirmation and main menu
        language_name = get_language_name(selected_language)
        confirmation_text = get_text("language_selected", selected_language, language_name=language_name)
        
        try:
            await callback.message.edit_text(confirmation_text)
        except Exception as e:
            logger.warning(f"Could not edit message text: {e}")
            # If edit fails, send new message instead
            await callback.message.answer(confirmation_text)
        
        # Send main menu after a short delay
        await asyncio.sleep(1)
        
        # Get updated user and send welcome message directly
        updated_user = await db.get_user(user_id)
        if updated_user:
            welcome_text = MessageFormatter.format_welcome_message(
                updated_user.full_name,
                updated_user.is_admin,
                updated_user.language or DEFAULT_LANGUAGE
            )
            
            await bot.send_message(
                callback.message.chat.id,
                welcome_text,
                reply_markup=get_user_keyboard(updated_user.is_admin, updated_user.language or DEFAULT_LANGUAGE),
                parse_mode="Markdown"
            )
        else:
            logger.error(f"Could not retrieve updated user {user_id}")
            # Fallback - send basic welcome
            await bot.send_message(
                callback.message.chat.id,
                get_text("welcome_message", selected_language, name=callback.from_user.first_name or "User", admin_hint=""),
                reply_markup=get_user_keyboard(user_id in settings.get_admin_ids(), selected_language),
                parse_mode="Markdown"
            )
        
        await callback.answer(f"✅ Language set to {language_name}")
        
        # Log the language change
        await db.log_admin_action(
            user_id, 
            "language_changed", 
            details=f"Changed language to {selected_language} ({language_name})"
        )
        
        logger.info(f"User {user_id} selected language: {selected_language}")
        
    except Exception as e:
        logger.error(f"Error in language selection callback: {e}")
        await callback.answer("❌ Error setting language. Please try again.", show_alert=True)
        
        # Send fallback message
        try:
            await bot.send_message(
                callback.message.chat.id,
                "⚠️ **Error occurred while setting language.**\n\nPlease try selecting your language again.",
                reply_markup=LanguageKeyboards.get_language_selection()
            )
        except Exception as fallback_error:
            logger.error(f"Fallback language message failed: {fallback_error}")

@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Handle broadcast cancellation."""
    user_id = callback.from_user.id
    
    if user_id in broadcast_data:
        del broadcast_data[user_id]
    
    await callback.message.edit_text("❌ **Broadcast Cancelled**")
    await state.clear()


@dp.callback_query(F.data == "broadcast_preview")
async def broadcast_preview_callback(callback: CallbackQuery):
    """Show a preview of the broadcast message before sending."""
    user_id = callback.from_user.id
    if user_id not in broadcast_data:
        await callback.answer("❌ Nothing to preview", show_alert=True)
        return
    data = broadcast_data[user_id]
    preview_text = MessageFormatter.format_broadcast_preview(data['message'], data.get('recipients', 0))
    try:
        await callback.message.edit_text(
            preview_text,
            reply_markup=AdminKeyboards.get_broadcast_confirmation(data.get('recipients', 0))
        )
    except Exception as e:
        logger.debug(f"Could not edit preview message: {e}")
        await callback.message.answer(
            preview_text,
            reply_markup=AdminKeyboards.get_broadcast_confirmation(data.get('recipients', 0))
        )
    await callback.answer("👁️ Preview shown")


# === ADDITIONAL CALLBACK HANDLERS ===

@dp.callback_query(F.data == "users_all")
async def users_all_callback(callback: CallbackQuery):
    """Handle view all users callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    users = await db.get_users(limit=settings.bot.users_per_page)
    
    if not users:
        await callback.message.edit_text(
            "👥 **No Users Found**\n\nThe database is empty.",
            reply_markup=AdminKeyboards.get_admin_panel()
        )
        await callback.answer()
        return
    
    # Format user list
    text_lines = ["👥 **All Users**\n"]
    
    for user_item in users:
        text_lines.append(MessageFormatter.format_user_summary(user_item))
        text_lines.append("")
    
    await callback.message.edit_text(
        "\n".join(text_lines),
        reply_markup=create_user_list_keyboard(users, 1, 1)
    )
    await callback.answer()
    
    await db.log_admin_action(user_id, "view_all_users_callback", details="Viewed all users via callback")


@dp.callback_query(F.data == "users_refresh")
async def users_refresh_callback(callback: CallbackQuery):
    """Handle refresh users callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    users = await db.get_users(limit=settings.bot.users_per_page)
    
    if not users:
        try:
            await callback.message.edit_text("👥 **No Users Found**\n\nThe database is empty.")
        except Exception as e:
            logger.debug(f"Message edit failed (content likely unchanged): {e}")
        await callback.answer("Data refreshed")
        return
    
    text_lines = ["👥 **All Users** (Refreshed)\n"]
    
    for user_item in users:
        text_lines.append(MessageFormatter.format_user_summary(user_item))
        text_lines.append("")
    
    try:
        await callback.message.edit_text(
            "\n".join(text_lines),
            reply_markup=create_user_list_keyboard(users, 1, 1)
        )
    except Exception as e:
        # If message content is the same, just show callback response
        logger.debug(f"Message edit failed (content likely unchanged): {e}")
        
    await callback.answer("✅ Data refreshed!")


@dp.callback_query(F.data == "users_active")
async def users_active_callback(callback: CallbackQuery):
    """Handle view active users callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    users = await db.get_users(active_only=True, limit=settings.bot.users_per_page)
    
    if not users:
        await callback.message.edit_text("✅ **No Active Users Found**")
        await callback.answer()
        return
    
    text_lines = ["✅ **Active Users**\n"]
    
    for user_item in users:
        text_lines.append(MessageFormatter.format_user_summary(user_item))
        text_lines.append("")
    
    await callback.message.edit_text(
        "\n".join(text_lines),
        reply_markup=create_user_list_keyboard(users, 1, 1)
    )
    await callback.answer()
    
    await db.log_admin_action(user_id, "view_active_users_callback", details=f"Viewed {len(users)} active users via callback")


@dp.callback_query(F.data == "stats_basic")
async def stats_basic_callback(callback: CallbackQuery):
    """Handle basic stats callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    stats = await db.get_statistics()
    stats_text = MessageFormatter.format_bot_statistics(stats)
    
    await callback.message.edit_text(
        f"📊 **Basic Statistics**\n\n{stats_text}",
        reply_markup=AdminKeyboards.get_statistics_menu()
    )
    await callback.answer()
    
    await db.log_admin_action(user_id, "view_basic_stats", details="Viewed basic statistics")


@dp.callback_query(F.data == "stats_users")
async def stats_users_callback(callback: CallbackQuery):
    """Handle user stats callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    stats = await db.get_statistics()
    
    user_stats_text = f"""
📊 **User Statistics**

👥 **Total Users:** {stats.total_users}
✅ **Active Users:** {stats.active_users}
🚫 **Banned Users:** {stats.banned_users}
👑 **Administrators:** {stats.admin_count}
📈 **Activity Rate:** {stats.active_rate:.1f}%
🆕 **New Today:** {stats.new_users_today}
    """
    
    await callback.message.edit_text(
        user_stats_text,
        reply_markup=AdminKeyboards.get_statistics_menu()
    )
    await callback.answer()
    
    await db.log_admin_action(user_id, "view_user_stats", details="Viewed user statistics")


@dp.callback_query(F.data == "stats_detailed")
async def stats_detailed_callback(callback: CallbackQuery):
    """Handle detailed stats callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    stats = await db.get_statistics()
    
    detailed_stats_text = f"""
📈 **Detailed Statistics**

👥 **Users:**
• Total: {stats.total_users}
• Active: {stats.active_users} ({stats.active_rate:.1f}%)
• Banned: {stats.banned_users}
• Admins: {stats.admin_count}
• New Today: {stats.new_users_today}

💬 **Messages:**
• Today: {stats.messages_today}
• Total: {stats.messages_total}
• Avg per User: {stats.messages_total / max(stats.total_users, 1):.1f}
    """
    
    await callback.message.edit_text(
        detailed_stats_text,
        reply_markup=AdminKeyboards.get_statistics_menu()
    )
    await callback.answer()
    
    await db.log_admin_action(user_id, "view_detailed_stats", details="Viewed detailed statistics")


@dp.callback_query(F.data == "stats_export")
async def stats_export_callback(callback: CallbackQuery):
    """Handle stats export callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    stats = await db.get_statistics()
    
    # Create a simple stats report
    stats_report = f"""
📊 Bot Statistics Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== USER STATISTICS ===
Total Users: {stats.total_users}
Active Users: {stats.active_users}
Banned Users: {stats.banned_users}
Admin Count: {stats.admin_count}
Activity Rate: {stats.active_rate:.1f}%
New Users Today: {stats.new_users_today}

=== MESSAGE STATISTICS ===
Messages Today: {stats.messages_today}
Total Messages: {stats.messages_total}
Average per User: {stats.messages_total / max(stats.total_users, 1):.1f}
    """
    
    await callback.message.reply(f"📋 **Statistics Export**\n\n```\n{stats_report}\n```")
    await callback.answer("📊 Statistics exported!")
    
    await db.log_admin_action(user_id, "export_stats", details="Exported statistics report")


@dp.callback_query(F.data == "stats_broadcasts")
async def stats_broadcasts_callback(callback: CallbackQuery):
    """Handle broadcasts stats callback (placeholder)."""
    user_id = callback.from_user.id
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    await callback.message.edit_text(
        "📢 Broadcast History\n\nThis feature will show broadcast history and metrics in a future update.",
        reply_markup=AdminKeyboards.get_statistics_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "stats_activity")
async def stats_activity_callback(callback: CallbackQuery):
    """Handle activity report callback (placeholder)."""
    user_id = callback.from_user.id
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    await callback.message.edit_text(
        "📱 Activity Report\n\nThis feature will provide timeline-based activity analytics in a future update.",
        reply_markup=AdminKeyboards.get_statistics_menu()
    )
    await callback.answer()


@dp.callback_query(F.data == "stats_refresh")
async def stats_refresh_callback(callback: CallbackQuery):
    """Handle stats refresh callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    stats = await db.get_statistics()
    stats_text = MessageFormatter.format_bot_statistics(stats)
    
    try:
        await callback.message.edit_text(
            f"📊 **Bot Statistics** (Refreshed)\n\n{stats_text}",
            reply_markup=AdminKeyboards.get_statistics_menu()
        )
    except Exception as e:
        # If message content is the same, just show callback response
        logger.debug(f"Message edit failed (content likely unchanged): {e}")
    
    await callback.answer("✅ Statistics refreshed!")
    
    await db.log_admin_action(user_id, "refresh_stats", details="Refreshed statistics")


@dp.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    """Handle admin panel callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👑 **Administrator Panel**\n\nChoose an option below:",
        reply_markup=AdminKeyboards.get_user_management()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("user_detail_"))
async def user_detail_callback(callback: CallbackQuery):
    """Handle user detail callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Extract target user ID
    target_user_id = int(callback.data.split("_")[-1])
    target_user = await db.get_user(target_user_id)
    
    if not target_user:
        await callback.answer("❌ User not found", show_alert=True)
        return
    
    # Format user details
    user_details = MessageFormatter.format_user_profile(target_user, show_admin_info=True)
    
    await callback.message.edit_text(
        f"👤 **User Details**\n\n{user_details}",
        reply_markup=AdminKeyboards.get_user_actions(
            target_user_id, 
            target_user.is_admin, 
            target_user.is_banned
        )
    )
    await callback.answer()
    
    await db.log_admin_action(user_id, "view_user_details", details=f"Viewed details for user {target_user_id}")


@dp.callback_query(F.data == "users_admins")
async def users_admins_callback(callback: CallbackQuery):
    """Handle view admins callback."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    admins = await db.get_users(admin_only=True)
    
    if not admins:
        await callback.message.edit_text("👑 **No Administrators Found**")
        await callback.answer()
        return
    
    text_lines = ["👑 **Bot Administrators**\n"]
    
    for admin in admins:
        text_lines.append(MessageFormatter.format_user_summary(admin))
        text_lines.append("")
    
    await callback.message.edit_text(
        "\n".join(text_lines),
        reply_markup=create_user_list_keyboard(admins, 1, 1)
    )
    await callback.answer()
    
    await db.log_admin_action(user_id, "view_admins_callback", details=f"Viewed {len(admins)} administrators via callback")




# === BOT CREATION STATE HANDLERS ===

@dp.message(BotManagementStates.waiting_for_bot_token)
async def bot_token_received(message: Message, state: FSMContext):
    """Handle bot token submission."""
    user = await BotService.update_user(message)
    
    # Check if user wants to cancel
    if message.text == "❌ Cancel Operation":
        await state.clear()
        await message.answer(
            "❌ **Operation cancelled**",
            reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
        )
        return
    
    if not message.text:
        user_lang = user.language or DEFAULT_LANGUAGE
        error_text = "❌ Iltimos, bot tokenini yuboring!" if user_lang == 'uz' else (
            "❌ Пожалуйста, отправьте токен бота!" if user_lang == 'ru' else
            "❌ Please send the bot token!"
        )
        await message.answer(error_text)
        return
    
    token = message.text.strip()
    user_lang = user.language or DEFAULT_LANGUAGE
    
    # Show validation message
    validating_text = "🔍 Token tekshirilmoqda..." if user_lang == 'uz' else (
        "🔍 Проверяем токен..." if user_lang == 'ru' else
        "🔍 Validating token..."
    )
    
    validation_msg = await message.answer(validating_text)
    
    # Import bot manager here to avoid circular imports
    from bot_manager import bot_manager
    
    try:
        # Validate token with Telegram API
        bot_info = await bot_manager.validate_bot_token(token)
        
        if not bot_info.is_valid:
            error_text = (
                f"❌ **Token noto'g'ri!**\n\n"
                f"Xatolik: {bot_info.error_message}\n\n"
                f"Iltimos, to'g'ri tokenni yuboring."
                if user_lang == 'uz' else
                f"❌ **Неверный токен!**\n\n"
                f"Ошибка: {bot_info.error_message}\n\n"
                f"Пожалуйста, отправьте правильный токен."
                if user_lang == 'ru' else
                f"❌ **Invalid token!**\n\n"
                f"Error: {bot_info.error_message}\n\n"
                f"Please send a valid token."
            )
            
            await validation_msg.edit_text(error_text)
            return
        
        # Token is valid, show bot info and confirmation
        bot_name = bot_info.first_name
        bot_username = bot_info.username
        
        confirmation_text = (
            f"✅ **Bot topildi!**\n\n"
            f"🤖 **Nom:** {bot_name}\n"
            f"👤 **Username:** @{bot_username}\n"
            f"🆔 **ID:** `{bot_info.id}`\n\n"
            f"Bu botni yaratishni xohlaysizmi?"
            if user_lang == 'uz' else
            f"✅ **Бот найден!**\n\n"
            f"🤖 **Имя:** {bot_name}\n"
            f"👤 **Username:** @{bot_username}\n"
            f"🆔 **ID:** `{bot_info.id}`\n\n"
            f"Хотите создать этого бота?"
            if user_lang == 'ru' else
            f"✅ **Bot found!**\n\n"
            f"🤖 **Name:** {bot_name}\n"
            f"👤 **Username:** @{bot_username}\n"
            f"🆔 **ID:** `{bot_info.id}`\n\n"
            f"Do you want to create this bot?"
        )
        
        # Store bot data in session
        user_sessions[user.user_id] = {
            'bot_token': token,
            'bot_info': bot_info,
            'bot_name': bot_name
        }
        
        # Create confirmation keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        yes_text = "✅ Ha, yaratish" if user_lang == 'uz' else ("✅ Да, создать" if user_lang == 'ru' else "✅ Yes, create")
        no_text = "❌ Yo'q, bekor qilish" if user_lang == 'uz' else ("❌ Нет, отменить" if user_lang == 'ru' else "❌ No, cancel")
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=yes_text, callback_data="create_bot_confirm")],
            [InlineKeyboardButton(text=no_text, callback_data="create_bot_cancel")]
        ])
        
        await validation_msg.edit_text(confirmation_text, reply_markup=keyboard)
        await state.set_state(BotManagementStates.confirming_bot_submission)
        
    except Exception as e:
        logger.error(f"Error validating bot token: {e}")
        error_text = (
            "❌ **Xatolik!**\n\nTokenni tekshirishda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring."
            if user_lang == 'uz' else
            "❌ **Ошибка!**\n\nОшибка при проверке токена. Пожалуйста, попробуйте снова."
            if user_lang == 'ru' else
            "❌ **Error!**\n\nError validating token. Please try again."
        )
        await validation_msg.edit_text(error_text)


@dp.callback_query(F.data == "create_bot_confirm")
async def create_bot_confirm_callback(callback: CallbackQuery, state: FSMContext):
    """Handle bot creation confirmation."""
    user_id = callback.from_user.id
    
    if user_id not in user_sessions:
        await callback.answer("❌ Session expired. Please try again.", show_alert=True)
        await state.clear()
        return
    
    session_data = user_sessions[user_id]
    user = await db.get_user(user_id)
    user_lang = user.language if user else DEFAULT_LANGUAGE
    
    # Show creating message
    creating_text = "🔄 Bot yaratilmoqda..." if user_lang == 'uz' else (
        "🔄 Создаем бота..." if user_lang == 'ru' else
        "🔄 Creating bot..."
    )
    
    await callback.message.edit_text(creating_text)
    
    # Import bot manager
    from bot_manager import bot_manager
    
    try:
        # Create the bot
        success, message, bot_id = await bot_manager.create_bot_request(
            user_id=user_id,
            bot_name=session_data['bot_name'],
            bot_token=session_data['bot_token'],
            bot_info=session_data['bot_info']
        )
        
        if success:
            success_text = (
                f"✅ **Bot muvaffaqiyatli yaratildi!**\n\n"
                f"🤖 **Bot:** {session_data['bot_name']}\n"
                f"📱 **Username:** @{session_data['bot_info'].username}\n"
                f"🚀 **Holat:** Ishlamoqda\n\n"
                f"Botingiz tayyor va foydalanishga ochiq!"
                if user_lang == 'uz' else
                f"✅ **Бот успешно создан!**\n\n"
                f"🤖 **Бот:** {session_data['bot_name']}\n"
                f"📱 **Username:** @{session_data['bot_info'].username}\n"
                f"🚀 **Статус:** Работает\n\n"
                f"Ваш бот готов к использованию!"
                if user_lang == 'ru' else
                f"✅ **Bot created successfully!**\n\n"
                f"🤖 **Bot:** {session_data['bot_name']}\n"
                f"📱 **Username:** @{session_data['bot_info'].username}\n"
                f"🚀 **Status:** Running\n\n"
                f"Your bot is ready to use!"
            )
            
            # Notify admins about new bot
            admin_notification = (
                f"🆕 **New Bot Created**\n\n"
                f"👤 **User:** {callback.from_user.full_name} (@{callback.from_user.username or 'N/A'})\n"
                f"🤖 **Bot:** {session_data['bot_name']}\n"
                f"📱 **Username:** @{session_data['bot_info'].username}\n"
                f"🆔 **Bot ID:** {bot_id}\n"
                f"🚀 **Status:** Running"
            )
            
            # Send notification to admins
            for admin_id in settings.get_admin_ids():
                try:
                    await bot.send_message(admin_id, admin_notification)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
            
        else:
            success_text = f"❌ **Xatolik:** {message}" if user_lang == 'uz' else (
                f"❌ **Ошибка:** {message}" if user_lang == 'ru' else
                f"❌ **Error:** {message}"
            )
        
        await callback.message.edit_text(success_text)
        
        # Cleanup
        if user_id in user_sessions:
            del user_sessions[user_id]
        await state.clear()
        
        # Send main menu after delay
        await asyncio.sleep(3)
        user = await db.get_user(user_id)
        if user:
            await bot.send_message(
                callback.message.chat.id,
                get_text("back_main_menu", user.language or DEFAULT_LANGUAGE),
                reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
            )
            
    except Exception as e:
        logger.error(f"Error creating bot: {e}")
        error_text = (
            "❌ **Xatolik!**\n\nBot yaratishda xatolik yuz berdi. Iltimos qaytadan urinib ko'ring."
            if user_lang == 'uz' else
            "❌ **Ошибка!**\n\nОшибка при создании бота. Пожалуйста, попробуйте снова."
            if user_lang == 'ru' else
            "❌ **Error!**\n\nError creating bot. Please try again."
        )
        await callback.message.edit_text(error_text)
        
        # Cleanup
        if user_id in user_sessions:
            del user_sessions[user_id]
        await state.clear()


@dp.callback_query(F.data == "create_bot_cancel")
async def create_bot_cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Handle bot creation cancellation."""
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    user_lang = user.language if user else DEFAULT_LANGUAGE
    
    cancel_text = "❌ Bot yaratish bekor qilindi." if user_lang == 'uz' else (
        "❌ Создание бота отменено." if user_lang == 'ru' else
        "❌ Bot creation cancelled."
    )
    
    await callback.message.edit_text(cancel_text)
    
    # Cleanup
    if user_id in user_sessions:
        del user_sessions[user_id]
    await state.clear()
    
    # Send main menu
    await asyncio.sleep(2)
    if user:
        await bot.send_message(
            callback.message.chat.id,
            get_text("back_main_menu", user.language or DEFAULT_LANGUAGE),
            reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
        )


# === ERROR HANDLERS ===

@dp.message()
async def unknown_message_handler(message: Message):
    """Handle unknown messages with helpful response."""
    user = await BotService.update_user(message)
    
    response_text = get_text("unknown_command", user.language or DEFAULT_LANGUAGE)
    
    await message.answer(
        response_text,
        reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
    )


@dp.callback_query()
async def unknown_callback_handler(callback: CallbackQuery):
    """Handle unknown callback queries."""
    await callback.answer("❓ Unknown action", show_alert=True)
    logger.warning(f"Unknown callback: {callback.data}")


# === MAIN FUNCTION ===

async def main():
    """Main bot function."""
    try:
        logger.info(f"Starting {settings.bot.name}...")
        
        # Initialize database
        await db.initialize()
        logger.success("Database initialized successfully")
        
        # Add initial admins
        for admin_id in settings.get_admin_ids():
            admin_user_data = {
                'user_id': admin_id,
                'username': f"admin_{admin_id}",
                'first_name': "Admin",
                'last_name': "User"
            }
            await db.add_or_update_user(admin_user_data)
        
        logger.info(f"Added {len(settings.get_admin_ids())} initial administrators")
        
        # Initialize and start user bots
        try:
            from bot_manager import bot_manager
            await bot_manager.start_all_approved_bots()
            logger.info("User bots initialization completed")
        except Exception as e:
            logger.error(f"Error starting user bots: {e}")
        
        # Set bot commands
        commands = [
            ("start", "🚀 Start the bot"),
            ("admin", "👑 Admin panel (admins only)")
        ]
        
        from aiogram.types import BotCommand
        await bot.set_my_commands([BotCommand(command=cmd, description=desc) for cmd, desc in commands])
        
        logger.info("Bot commands configured")
        logger.success(f"{settings.bot.name} is ready!")
        
        # Start polling
        await dp.start_polling(bot)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
