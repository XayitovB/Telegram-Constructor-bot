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
    """Handle My Bots button."""
    user = await BotService.update_user(message)
    
    title = get_text("my_bots_title", user.language or DEFAULT_LANGUAGE)
    text = get_text("my_bots_text", user.language or DEFAULT_LANGUAGE)
    
    await message.answer(
        f"{title}\n\n{text}",
        reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
    )

@dp.message(F.text.in_(ADD_BOTS_LABELS))
async def add_bots_handler(message: Message):
    """Handle Add Bots button."""
    user = await BotService.update_user(message)
    
    title = get_text("add_bots_title", user.language or DEFAULT_LANGUAGE)
    text = get_text("add_bots_text", user.language or DEFAULT_LANGUAGE)
    
    await message.answer(
        f"{title}\n\n{text}",
        reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
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
