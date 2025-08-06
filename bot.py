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
from ui.keyboards import (
    get_user_keyboard, MainKeyboards, AdminKeyboards,
    BroadcastKeyboards, NavigationKeyboards, BotManagementKeyboards,
    create_user_list_keyboard
)
from ui.formatters import (
    MessageFormatter, DataExporter, PaginationHelper
)

# Get logger (setup will be done by run.py)
logger = get_logger(__name__)

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
                    is_admin=message.from_user.id in settings.get_admin_ids()
                )
        except Exception as e:
            logger.error(f"Error updating user {message.from_user.id}: {e}")
            # Return a default user to prevent crashes
            return User(
                user_id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                is_admin=message.from_user.id in settings.get_admin_ids()
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
            text = MessageFormatter.format_welcome_message(user.full_name, user.is_admin)
        
        await message.answer(
            text,
            reply_markup=get_user_keyboard()
        )


# === COMMAND HANDLERS ===

@dp.message(CommandStart())
async def start_handler(message: Message):
    """Handle /start command."""
    # Check if this is a new user
    existing_user = await db.get_user(message.from_user.id)
    is_new_user = existing_user is None
    
    # Send main menu
    await BotService.send_main_menu(message)
    
    # If new user, notify admins
    if is_new_user:
        user = await BotService.update_user(message)
        await BotService.notify_admins_new_user(user)
        logger.info(f"New user {message.from_user.id} started the bot - admins notified")
    else:
        logger.info(f"Existing user {message.from_user.id} started the bot")


@dp.message(Command('admin'))
async def admin_command_handler(message: Message):
    """Handle /admin command - only entry point to admin panel."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer(
            "❌ **Access Denied**\n\nThis command requires administrator privileges.",
            reply_markup=get_user_keyboard()
        )
        return
    
    # Show admin panel
    await message.answer(
        "👑 **Administrator Panel**\n\nWelcome to the admin control center. Choose an option below:",
        reply_markup=AdminKeyboards.get_admin_panel()
    )
    
    # Log admin access
    log_admin_action(user.user_id, "admin_panel_access", "Accessed admin panel via /admin command")


# === BUTTON HANDLERS - USER INTERFACE ===



# === ADMIN BUTTON HANDLERS ===


@dp.message(F.text == "📊 Statistics")
async def statistics_button_handler(message: Message):
    """Handle statistics button."""
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
    
    log_admin_action(user.user_id, "view_statistics", "Viewed bot statistics")


@dp.message(F.text == "👥 User Management")
async def user_management_button_handler(message: Message):
    """Handle user management button."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    await message.answer(
        "👥 **User Management**\n\nSelect an option to manage users:",
        reply_markup=AdminKeyboards.get_user_management()
    )


@dp.message(F.text == "📢 Broadcast")
async def broadcast_button_handler(message: Message, state: FSMContext):
    """Handle broadcast button - Direct broadcast composition."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer("❌ Access denied.")
        return
    
    # Get recipient count for preview
    recipients = await db.get_broadcast_users()
    
    await message.answer(
        f"📢 **Broadcast Message**\n\nSend me the message you want to broadcast to **{len(recipients)}** users.\n\n" +
        "💡 **Tips:**\n" +
        "• Keep messages clear and concise\n" +
        "• Maximum length: 4000 characters\n" +
        "• The message will be sent immediately after confirmation",
        reply_markup=MainKeyboards.get_cancel_button()
    )
    
    await state.set_state(BroadcastStates.waiting_for_message)


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
    
    log_admin_action(user.user_id, "view_all_users", f"Viewed all users (page {page})")


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
    
    log_admin_action(user.user_id, "view_active_users", f"Viewed {len(users)} active users")


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
        reply_markup=MainKeyboards.get_back_button()
    )
    
    log_admin_action(user.user_id, "view_admins", f"Viewed {len(admins)} administrators")


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
        await message.answer(
            "❌ **Broadcast Cancelled**",
            reply_markup=get_user_keyboard()
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

@dp.message(F.text == "🔙 Back to Main Menu")
async def back_to_main_handler(message: Message):
    """Handle back to main menu button."""
    await BotService.send_main_menu(message, "🏠 **Main Menu**\n\nWelcome back! Choose an option below:")


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
    log_admin_action(user_id, "export_users", f"Exported {len(users)} users to CSV")


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
    
    # Send broadcast
    sent_count = 0
    failed_count = 0
    
    for recipient_id in recipient_ids:
        try:
            await bot.send_message(
                recipient_id,
                message_text
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {recipient_id}: {e}")
            failed_count += 1
        
        # Rate limiting
        await asyncio.sleep(settings.bot.broadcast_delay)
    
    # Log broadcast
    await db.log_broadcast(user_id, message_text, sent_count, failed_count)
    
    # Show results
    result_text = MessageFormatter.format_broadcast_result(sent_count, failed_count, sent_count + failed_count)
    
    await callback.message.edit_text(result_text)
    
    # Cleanup
    del broadcast_data[user_id]
    await state.clear()
    
    log_admin_action(user_id, "broadcast_sent", f"Sent to {sent_count} users, {failed_count} failed")


@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Handle broadcast cancellation."""
    user_id = callback.from_user.id
    
    if user_id in broadcast_data:
        del broadcast_data[user_id]
    
    await callback.message.edit_text("❌ **Broadcast Cancelled**")
    await state.clear()


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
    
    log_admin_action(user_id, "view_all_users_callback", "Viewed all users via callback")


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
    
    log_admin_action(user_id, "view_active_users_callback", f"Viewed {len(users)} active users via callback")


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
    
    log_admin_action(user_id, "view_basic_stats", "Viewed basic statistics")


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
    
    log_admin_action(user_id, "view_user_stats", "Viewed user statistics")


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
    
    log_admin_action(user_id, "view_detailed_stats", "Viewed detailed statistics")


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
    
    log_admin_action(user_id, "export_stats", "Exported statistics report")


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
    
    log_admin_action(user_id, "refresh_stats", "Refreshed statistics")


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
    
    log_admin_action(user_id, "view_user_details", f"Viewed details for user {target_user_id}")


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
    
    log_admin_action(user_id, "view_admins_callback", f"Viewed {len(admins)} administrators via callback")


# === BOT MANAGEMENT HANDLERS ===

@dp.message(F.text == "🤖 My Bots Panel")
async def bot_panel_handler(message: Message):
    """Handle bot panel button."""
    user = await BotService.update_user(message)
    
    await message.answer(
        "🤖 **My Bots Panel**\n\nWelcome to your bot management center. Here you can:",
        reply_markup=BotManagementKeyboards.get_bot_panel()
    )

@dp.message(F.text == "🤖 My Bots")
async def my_bots_handler(message: Message):
    """Handle my bots button."""
    user = await BotService.update_user(message)
    user_bots = await db.get_user_bots(user.user_id)
    
    bot_list_text = MessageFormatter.format_bot_list(user_bots, "all")
    
    await message.answer(
        bot_list_text,
        reply_markup=BotManagementKeyboards.get_my_bots_menu()
    )

@dp.message(F.text == "➕ Add New Bot")
async def add_bot_handler(message: Message, state: FSMContext):
    """Handle add new bot button."""
    user = await BotService.update_user(message)
    
    await message.answer(
        "🤖 **Add New Bot**\n\nLet's get your bot registered! First, what's your bot's name?\n\n📝 **Enter your bot name:**",
        reply_markup=MainKeyboards.get_cancel_button()
    )
    
    await state.set_state(BotManagementStates.waiting_for_bot_name)

@dp.message(F.text == "👨‍💼 Contact Admin")
async def contact_admin_handler(message: Message):
    """Handle contact admin button."""
    user = await BotService.update_user(message)
    
    await message.answer(
        "👨‍💼 **Contact Admin**\n\nNeed help or have questions? Choose the type of message you'd like to send:",
        reply_markup=BotManagementKeyboards.get_contact_admin_menu()
    )

@dp.message(F.text == "📜 Bot Guidelines")
async def bot_guidelines_handler(message: Message):
    """Handle bot guidelines button."""
    user = await BotService.update_user(message)
    guidelines_text = MessageFormatter.format_bot_guidelines()
    
    await message.answer(
        guidelines_text,
        reply_markup=BotManagementKeyboards.get_bot_panel()
    )

# FSM Handlers for Bot Management

@dp.message(BotManagementStates.waiting_for_bot_name)
async def bot_name_received(message: Message, state: FSMContext):
    """Handle bot name input."""
    if message.text == "❌ Cancel Operation":
        await message.answer(
            "❌ **Operation Cancelled**",
            reply_markup=BotManagementKeyboards.get_bot_panel()
        )
        await state.clear()
        return
    
    if not message.text or len(message.text) < 3 or len(message.text) > 50:
        await message.answer(
            "❌ **Invalid Bot Name**\n\nBot name must be between 3 and 50 characters. Please try again:"
        )
        return
    
    # Store bot name
    await state.update_data(bot_name=message.text)
    
    await message.answer(
        f"✅ **Bot Name:** {message.text}\n\nNow I need your bot token from @BotFather.\n\n🔑 **Send your bot token:**\n\n⚠️ Keep your token secure!",
        reply_markup=MainKeyboards.get_cancel_button()
    )
    
    await state.set_state(BotManagementStates.waiting_for_bot_token)

@dp.message(BotManagementStates.waiting_for_bot_token)
async def bot_token_received(message: Message, state: FSMContext):
    """Handle bot token input."""
    if message.text == "❌ Cancel Operation":
        await message.answer(
            "❌ **Operation Cancelled**",
            reply_markup=BotManagementKeyboards.get_bot_panel()
        )
        await state.clear()
        return
    
    if not message.text or not message.text.count(':') == 1 or len(message.text) < 40:
        await message.answer(
            "❌ **Invalid Bot Token**\n\nPlease provide a valid bot token from @BotFather. It should look like: 123456789:ABCdefGHIjklMNOpqrSTUvwxyz"
        )
        return
    
    # Store bot token
    await state.update_data(bot_token=message.text)
    
    await message.answer(
        "✅ **Bot Token Received**\n\nFinally, please provide a description of your bot (what it does, its features, etc.):\n\n📝 **Bot Description:**",
        reply_markup=MainKeyboards.get_cancel_button()
    )
    
    await state.set_state(BotManagementStates.waiting_for_bot_description)

@dp.message(BotManagementStates.waiting_for_bot_description)
async def bot_description_received(message: Message, state: FSMContext):
    """Handle bot description input."""
    if message.text == "❌ Cancel Operation":
        await message.answer(
            "❌ **Operation Cancelled**",
            reply_markup=BotManagementKeyboards.get_bot_panel()
        )
        await state.clear()
        return
    
    if not message.text or len(message.text) < 10 or len(message.text) > 500:
        await message.answer(
            "❌ **Invalid Description**\n\nDescription must be between 10 and 500 characters. Please try again:"
        )
        return
    
    # Store description and show confirmation
    data = await state.get_data()
    await state.update_data(bot_description=message.text)
    
    confirmation_text = f"""
🤖 **Bot Submission Summary**

• **Name:** {data['bot_name']}
• **Token:** {data['bot_token'][:20]}...
• **Description:** {message.text[:100]}{'...' if len(message.text) > 100 else ''}

🔍 **Ready to Submit?**
Your bot will be reviewed by admins and you'll be notified of the decision.
    """
    
    await message.answer(
        confirmation_text,
        reply_markup=NavigationKeyboards.get_confirmation("bot_submission")
    )
    
    await state.set_state(BotManagementStates.confirming_bot_submission)

# Bot Management Callback Handlers

@dp.callback_query(F.data == "confirm_bot_submission")
async def confirm_bot_submission(callback: CallbackQuery, state: FSMContext):
    """Confirm bot submission."""
    user_id = callback.from_user.id
    data = await state.get_data()
    
    # Add bot to database
    bot_id = await db.add_user_bot(
        user_id=user_id,
        bot_name=data['bot_name'],
        bot_token=data['bot_token'],
        bot_description=data['bot_description']
    )
    
    if bot_id:
        await callback.message.edit_text(
            "✅ **Bot Submitted Successfully!**\n\nYour bot has been submitted for review. You'll be notified when it's approved or if we need more information."
        )
        
        # Notify admins about new bot submission
        admin_ids = settings.get_admin_ids()
        if admin_ids:
            user = await db.get_user(user_id)
            notification_text = f"""
🆕 **New Bot Submission**

👤 **User:** {user.display_name} (`{user_id}`)
🤖 **Bot Name:** {data['bot_name']}
📝 **Description:** {data['bot_description'][:100]}...

💡 **Admin Actions:**
• Use `/admin` to review and approve
• Check bot functionality before approval
            """
            
            for admin_id in admin_ids:
                try:
                    await bot.send_message(admin_id, notification_text)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
    else:
        await callback.message.edit_text(
            "❌ **Submission Failed**\n\nThere was an error submitting your bot. Please try again later."
        )
    
    await state.clear()
    await callback.answer("✅ Bot submitted!")

@dp.callback_query(F.data == "cancel_bot_submission")
async def cancel_bot_submission(callback: CallbackQuery, state: FSMContext):
    """Cancel bot submission."""
    await callback.message.edit_text(
        "❌ **Bot Submission Cancelled**"
    )
    await state.clear()
    await callback.answer()

# My Bots Callback Handlers

@dp.callback_query(F.data.startswith("my_bots_"))
async def my_bots_filter_callback(callback: CallbackQuery):
    """Handle my bots filter callbacks."""
    user_id = callback.from_user.id
    filter_type = callback.data.split("_")[-1]
    
    user_bots = await db.get_user_bots(user_id)
    
    if filter_type != "all":
        user_bots = [bot for bot in user_bots if bot['status'] == filter_type]
    
    bot_list_text = MessageFormatter.format_bot_list(user_bots, filter_type)
    
    try:
        await callback.message.edit_text(
            bot_list_text,
            reply_markup=BotManagementKeyboards.get_my_bots_menu()
        )
    except Exception as e:
        logger.debug(f"Message edit failed: {e}")
    
    await callback.answer(f"🤖 Showing {filter_type} bots")

@dp.callback_query(F.data.startswith("contact_"))
async def contact_admin_type_callback(callback: CallbackQuery, state: FSMContext):
    """Handle contact admin type selection."""
    message_type = callback.data.split("_")[-1]
    
    form_text = MessageFormatter.format_contact_admin_form(message_type)
    
    await callback.message.edit_text(form_text)
    await state.update_data(message_type=message_type)
    await state.set_state(AdminMessageStates.waiting_for_message)
    await callback.answer()

@dp.message(AdminMessageStates.waiting_for_message)
async def admin_message_received(message: Message, state: FSMContext):
    """Handle admin message input."""
    if not message.text or len(message.text) > 1000:
        await message.answer(
            "❌ **Invalid Message**\n\nMessage must be under 1000 characters. Please try again:"
        )
        return
    
    data = await state.get_data()
    message_type = data.get('message_type', 'custom')
    
    # Create subject based on message type
    subjects = {
        "issue": "🆘 Issue Report",
        "feature": "💡 Feature Request",
        "question": "❓ General Question",
        "bot_approval": "🤖 Bot Approval Query",
        "custom": "📨 Custom Message"
    }
    
    subject = subjects.get(message_type, subjects["custom"])
    
    # Show priority selection
    await message.answer(
        f"📝 **Message Preview:**\n{message.text[:200]}...\n\n📈 **Select Priority:**",
        reply_markup=BotManagementKeyboards.get_priority_selection()
    )
    
    await state.update_data(message_text=message.text, subject=subject)
    await state.set_state(AdminMessageStates.waiting_for_priority)

@dp.callback_query(F.data.startswith("priority_"))
async def priority_selected_callback(callback: CallbackQuery, state: FSMContext):
    """Handle priority selection."""
    priority = callback.data.split("_")[-1]
    data = await state.get_data()
    
    # Create admin message
    message_id = await db.create_admin_message(
        user_id=callback.from_user.id,
        subject=data['subject'],
        message=data['message_text'],
        priority=priority
    )
    
    if message_id:
        await callback.message.edit_text(
            "✅ **Message Sent to Admin!**\n\nYour message has been sent to the administrators. You'll receive a response soon."
        )
        
        # Notify admins about new message
        admin_ids = settings.get_admin_ids()
        if admin_ids:
            user = await db.get_user(callback.from_user.id)
            priority_emoji = {
                "urgent": "🔴",
                "high": "🟠",
                "normal": "🟡",
                "low": "🟢"
            }.get(priority, "🟡")
            
            notification_text = f"""
📨 **New Admin Message**

👤 **From:** {user.display_name} (`{callback.from_user.id}`)
{priority_emoji} **Priority:** {priority.title()}
📝 **Subject:** {data['subject']}

**Message:**
{data['message_text'][:300]}{'...' if len(data['message_text']) > 300 else ''}

💡 Use `/admin` to respond
            """
            
            for admin_id in admin_ids:
                try:
                    await bot.send_message(admin_id, notification_text)
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
    else:
        await callback.message.edit_text(
            "❌ **Failed to Send Message**\n\nPlease try again later."
        )
    
    await state.clear()
    await callback.answer("📨 Message sent!")

# Removed users_banned and users_search callback handlers as requested


# === ERROR HANDLERS ===

@dp.message()
async def unknown_message_handler(message: Message):
    """Handle unknown messages with helpful response."""
    user = await BotService.update_user(message)
    
    response_text = (
        "🤔 **Unknown Command**\n\n"
        "I don't understand that message. Please use the buttons below to navigate the bot.\n\n"
        "💡 **Quick Help:**\n"
        "• Use menu buttons for navigation\n"
        "• Admins can access admin panel with /admin\n"
        "• Press 📋 Help for more information"
    )
    
    await message.answer(
        response_text,
        reply_markup=get_user_keyboard()
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
            admin_user = User(
                user_id=admin_id,
                is_admin=True,
                username=f"admin_{admin_id}",
                first_name="Admin",
                last_name="User"
            )
            await db.add_or_update_user(admin_user.__dict__)
        
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
