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

class BotManagementStates(StatesGroup):
    waiting_for_bot_name = State()
    waiting_for_bot_token = State()
    waiting_for_bot_description = State()
    confirming_bot_submission = State()

class AdminMessageStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_priority = State()

class UserSearchStates(StatesGroup):
    waiting_for_query = State()
    waiting_for_user_input = State()

class LanguageSelectionStates(StatesGroup):
    selecting_language = State()

class BotExtensionStates(StatesGroup):
    waiting_for_bot_extend = State()

class ChannelStates(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_username = State()

# Additional state groups for compatibility
class UserStates(StatesGroup):
    waiting_for_input = State()

class AdminStates(StatesGroup):
    waiting_for_input = State()

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


# === MANDATORY CHANNEL FUNCTIONS ===

async def send_channel_join_requirement_direct(chat_id: int, missing_channels: list, user_language: str):
    """Send channel join requirement message directly to chat."""
    try:
        # Import escape function for safe markdown handling
        from ui.formatters import escape_markdown
        
        # Create concise multilingual messages
        if user_language == 'uz':
            header_text = (
                "🔐 **Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:**\n\n"
            )
            join_guide = ""
            benefits_text = ""
        elif user_language == 'ru':
            header_text = (
                "🔐 **Для использования бота подпишитесь на каналы:**\n\n"
            )
            join_guide = ""
            benefits_text = ""
        else:
            header_text = (
                "🔐 **To use this bot, join these channels:**\n\n"
            )
            join_guide = ""
            benefits_text = ""
        
        # Create enhanced channel list with better formatting
        text_lines = [header_text, "\n"]
        
        for i, channel in enumerate(missing_channels, 1):
            channel_title = channel.get('channel_title', 'Unknown Channel')
            channel_username = channel.get('channel_username', '')
            
            # Safely escape channel data
            safe_channel_title = escape_markdown(channel_title)
            safe_channel_username = escape_markdown(channel_username) if channel_username else ""
            
            # Enhanced channel display with emojis and better formatting
            if channel_username and channel_username != "N/A":
                text_lines.append(f"🔸 **{i}.** 📺 **{safe_channel_title}**")
                text_lines.append(f"      └ 🔗 @{safe_channel_username}\n")
            else:
                text_lines.append(f"🔸 **{i}.** 📺 **{safe_channel_title}**\n")
        
        # Add guide and benefits
        text_lines.extend([join_guide, benefits_text])
        message_text = "".join(text_lines)
        
        # Create inline keyboard with join buttons
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard_buttons = []
        
        # Add channel join buttons
        valid_channels = []
        for channel in missing_channels:
            channel_title = channel.get('channel_title', 'Unknown Channel')
            channel_url = channel.get('channel_url')
            channel_username = channel.get('channel_username')
            
            # Determine best join method based on available information
            button_url = None
            
            # Priority 1: Use proper username if available and not auto-generated
            if channel_username and not channel_username.startswith("channel_") and channel_username != "N/A":
                button_url = f"https://t.me/{channel_username}"
            # Priority 2: Use channel URL if it's not a private channel link 
            elif channel_url and not channel_url.startswith("https://t.me/c/"):
                button_url = channel_url
            # Priority 3: For private channels, try to provide helpful message
            elif channel_url and channel_url.startswith("https://t.me/c/"):
                # This is a private channel - users can't join via direct link
                logger.warning(f"Channel {channel_title} is private - users need invitation")
                # Still add to list but with special handling
                button_url = "https://t.me/" # Redirect to Telegram main page
            else:
                # No valid join method available
                logger.warning(f"Channel {channel_title} has no valid join URL - ID: {channel.get('channel_id')}, Username: {channel_username}, URL: {channel_url}")
                continue
            
            if button_url:
                valid_channels.append((channel, button_url))
        
        # Create buttons for valid channels
        for channel, button_url in valid_channels:
            # Get the actual channel title from the channel data
            actual_channel_title = channel.get('channel_title', 'Unknown Channel')
            
            # Truncate long titles for button display
            if len(actual_channel_title) > 25:
                display_title = actual_channel_title[:22] + "..."
            else:
                display_title = actual_channel_title
            
            # Special handling for private channels (invite links)
            if button_url.startswith("https://t.me/+") or button_url == "https://t.me/":
                # This is a private channel - add special button text with actual name
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"🔒 {display_title}",
                        url=button_url if button_url != "https://t.me/" else channel.get('channel_url', button_url)
                    )
                ])
            else:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"📺 {display_title}",
                        url=button_url
                    )
                ])
        
        # Add check membership button
        if user_language == 'uz':
            check_text = "✅ A'zolikni tekshirish"
        elif user_language == 'ru':
            check_text = "✅ Проверить подписку"
        else:
            check_text = "✅ Check Membership"
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=check_text,
                callback_data="check_membership"
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await bot.send_message(
            chat_id,
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error sending channel join requirement direct: {e}")
        # Fallback message
        await bot.send_message(
            chat_id,
            "⚠️ You need to join our channels to use this bot. Please contact support for assistance."
        )


async def send_channel_join_requirement(message: Message, missing_channels: list, user_language: str):
    """Send channel join requirement message with join buttons."""
    try:
        # Import escape function for safe markdown handling
        from ui.formatters import escape_markdown
        
        # Create concise multilingual messages
        if user_language == 'uz':
            header_text = (
                "🔐 **Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:**\n\n"
            )
            join_guide = ""
            benefits_text = ""
        elif user_language == 'ru':
            header_text = (
                "🔐 **Для использования бота подпишитесь на каналы:**\n\n"
            )
            join_guide = ""
            benefits_text = ""
        else:
            header_text = (
                "🔐 **To use this bot, join these channels:**\n\n"
            )
            join_guide = ""
            benefits_text = ""
        
        # Create enhanced channel list with better formatting
        text_lines = [header_text, "\n"]
        
        for i, channel in enumerate(missing_channels, 1):
            channel_title = channel.get('channel_title', 'Unknown Channel')
            channel_username = channel.get('channel_username', '')
            
            # Safely escape channel data
            safe_channel_title = escape_markdown(channel_title)
            safe_channel_username = escape_markdown(channel_username) if channel_username else ""
            
            # Enhanced channel display with emojis and better formatting
            if channel_username and channel_username != "N/A":
                text_lines.append(f"🔸 **{i}.** 📺 **{safe_channel_title}**")
                text_lines.append(f"      └ 🔗 @{safe_channel_username}\n")
            else:
                text_lines.append(f"🔸 **{i}.** 📺 **{safe_channel_title}**\n")
        
        # Only add check instruction if needed
        if user_language == 'uz':
            text_lines.append("\n\n✅ A'zo bo'lgandan so'ng, 'A'zolikni tekshirish' tugmasini bosing.")
        elif user_language == 'ru':
            text_lines.append("\n\n✅ После подписки нажмите 'Проверить подписку'.")
        else:
            text_lines.append("\n\n✅ After joining, click 'Check Membership'.")
        message_text = "".join(text_lines)
        
        # Create inline keyboard with join buttons
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard_buttons = []
        
        # Add channel join buttons
        valid_channels = []
        for channel in missing_channels:
            channel_title = channel.get('channel_title', 'Unknown Channel')
            channel_url = channel.get('channel_url')
            channel_username = channel.get('channel_username')
            
            # Determine best join method based on available information
            button_url = None
            
            # Priority 1: Use proper username if available and not auto-generated
            if channel_username and not channel_username.startswith("channel_") and channel_username != "N/A":
                button_url = f"https://t.me/{channel_username}"
            # Priority 2: Use channel URL if it's not a private channel link 
            elif channel_url and not channel_url.startswith("https://t.me/c/"):
                button_url = channel_url
            # Priority 3: For private channels, try to provide helpful message
            elif channel_url and channel_url.startswith("https://t.me/c/"):
                # This is a private channel - users can't join via direct link
                logger.warning(f"Channel {channel_title} is private - users need invitation")
                # Still add to list but with special handling
                button_url = "https://t.me/" # Redirect to Telegram main page
            else:
                # No valid join method available
                logger.warning(f"Channel {channel_title} has no valid join URL - ID: {channel.get('channel_id')}, Username: {channel_username}, URL: {channel_url}")
                continue
            
            if button_url:
                valid_channels.append((channel, button_url))
        
        # Create buttons for valid channels
        for channel, button_url in valid_channels:
            # Get the actual channel title from the channel data
            actual_channel_title = channel.get('channel_title', 'Unknown Channel')
            
            # Truncate long titles for button display
            if len(actual_channel_title) > 25:
                display_title = actual_channel_title[:22] + "..."
            else:
                display_title = actual_channel_title
            
            # Special handling for private channels (invite links)
            if button_url.startswith("https://t.me/+") or button_url == "https://t.me/":
                # This is a private channel - add special button text with actual name
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"🔒 {display_title}",
                        url=button_url if button_url != "https://t.me/" else channel.get('channel_url', button_url)
                    )
                ])
            else:
                keyboard_buttons.append([
                    InlineKeyboardButton(
                        text=f"📺 {display_title}",
                        url=button_url
                    )
                ])
        
        # Add check membership button
        if user_language == 'uz':
            check_text = "✅ A'zolikni tekshirish"
        elif user_language == 'ru':
            check_text = "✅ Проверить подписку"
        else:
            check_text = "✅ Check Membership"
        
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=check_text,
                callback_data="check_membership"
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Error sending channel join requirement: {e}")
        # Fallback message
        await message.answer(
            "⚠️ You need to join our channels to use this bot. Please contact support for assistance."
        )


# === COMMAND HANDLERS ===

@dp.message(CommandStart())
async def start_handler(message: Message):
    """Handle /start command with mandatory channel checking."""
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
    
    # Check mandatory channel membership for existing users
    user = await BotService.update_user(message)
    
    # Skip channel check for admins
    if not user.is_admin:
        membership_check = await db.check_user_channel_membership(user.user_id, settings.bot_token)
        
        if not membership_check['all_joined'] and membership_check['missing_channels']:
            # User hasn't joined all mandatory channels
            await send_channel_join_requirement(message, membership_check['missing_channels'], user.language or DEFAULT_LANGUAGE)
            return
    
    # Send main menu with user's language
    await BotService.send_main_menu(message)
    logger.info(f"User {message.from_user.id} started the bot")


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
    """Handle /admin command - show admin panel."""
    user = await BotService.update_user(message)
    
    if not user.is_admin:
        await message.answer(
            "❌ **Access Denied**\n\nThis command requires administrator privileges.",
            reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
        )
        return
    
    # Create admin panel keyboard
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Send Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 All Users", callback_data="admin_users")],
        [InlineKeyboardButton(text="🤖 Bot Management", callback_data="admin_bots")],
        [InlineKeyboardButton(text="🔍 User Search", callback_data="admin_user_search")],
        [InlineKeyboardButton(text="📊 Daily Statistics", callback_data="admin_daily_stats")],
        [InlineKeyboardButton(text="📺 Must Join Channels", callback_data="admin_mandatory_channels")],
        [InlineKeyboardButton(text="❌ Close", callback_data="admin_close")]
    ])
    
    await message.answer(
        "👑 **Admin Panel**\n\nChoose an option:",
        reply_markup=keyboard
    )
    
    # Log admin access
    await db.log_admin_action(user.user_id, "admin_panel_access", details="Accessed admin panel via /admin command")


# === BUTTON HANDLERS - USER INTERFACE ===

@dp.message(F.text.in_(MY_BOTS_LABELS))
async def my_bots_handler(message: Message):
    """Handle My Bots button - Show user's created bots with management options."""
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
                    "To create a new bot, click the **�🤖 Add Bot** button."
                )
            
            await message.answer(
                text,
                reply_markup=get_user_keyboard(user.is_admin, user_lang)
            )
        else:
            # Show user's bots with inline management buttons
            from ui.formatters import escape_markdown
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            if user_lang == 'uz':
                text_lines = ["🤖 **Mening botlarim**\n"]
            elif user_lang == 'ru':
                text_lines = ["🤖 **Мои боты**\n"]
            else:
                text_lines = ["🤖 **My Bots**\n"]
            
            # Create inline keyboard with bot management options
            keyboard_buttons = []
            
            for i, bot_data in enumerate(user_bots, 1):
                status_emoji = "🟢" if bot_data['is_running'] else "🔴"
                
                # Language-specific status text
                if user_lang == 'uz':
                    status_text = "Ishlamoqda" if bot_data['is_running'] else "To'xtatilgan"
                elif user_lang == 'ru':
                    status_text = "Работает" if bot_data['is_running'] else "Остановлен"
                else:
                    status_text = "Running" if bot_data['is_running'] else "Stopped"
                
                created_date = bot_data['created_at'][:10] if bot_data.get('created_at') else (
                    'Noma\'lum' if user_lang == 'uz' else 
                    'Неизвестно' if user_lang == 'ru' else 'Unknown'
                )
                
                # Escape bot name and username to prevent markdown issues
                safe_bot_name = escape_markdown(bot_data['bot_name']) if bot_data.get('bot_name') else "Unknown"
                safe_bot_username = escape_markdown(bot_data.get('bot_username', 'N/A'))
                
                text_lines.append(
                    f"**{i}.** 🤖 **{safe_bot_name}**\n"
                    f"📱 @{safe_bot_username}\n"
                    f"{status_emoji} {status_text}\n"
                    f"📅 {created_date}\n"
                )
                
                # Create management buttons for this bot
                bot_id = bot_data['id']
                
                # Truncate bot name for button display
                button_name = bot_data['bot_name']
                if len(button_name) > 20:
                    button_name = button_name[:17] + "..."
                
                # Language-specific button texts
                if user_lang == 'uz':
                    manage_text = f"⚙️ {button_name}"
                    restart_text = "🔄 Qayta ishga tushirish" if not bot_data['is_running'] else "⏹️ To'xtatish"
                    delete_text = "🗑️ O'chirish"
                elif user_lang == 'ru':
                    manage_text = f"⚙️ {button_name}"
                    restart_text = "🔄 Перезапустить" if not bot_data['is_running'] else "⏹️ Остановить"
                    delete_text = "🗑️ Удалить"
                else:
                    manage_text = f"⚙️ {button_name}"
                    restart_text = "🔄 Restart" if not bot_data['is_running'] else "⏹️ Stop"
                    delete_text = "🗑️ Delete"
                
                # Add row with manage and control buttons
                keyboard_buttons.append([
                    InlineKeyboardButton(text=manage_text, callback_data=f"manage_bot_{bot_id}")
                ])
                keyboard_buttons.append([
                    InlineKeyboardButton(text=restart_text, callback_data=f"toggle_bot_{bot_id}"),
                    InlineKeyboardButton(text=delete_text, callback_data=f"delete_bot_{bot_id}")
                ])
            
            # Add summary and total count
            if user_lang == 'uz':
                text_lines.append(f"\n📊 **Jami:** {len(user_bots)} ta bot")
                text_lines.append("\n💡 **Botlarni boshqarish uchun quyidagi tugmalardan foydalaning:**")
            elif user_lang == 'ru':
                text_lines.append(f"\n📊 **Всего:** {len(user_bots)} ботов")
                text_lines.append("\n💡 **Используйте кнопки ниже для управления ботами:**")
            else:
                text_lines.append(f"\n📊 **Total:** {len(user_bots)} bots")
                text_lines.append("\n💡 **Use the buttons below to manage your bots:**")
            
            text = "\n".join(text_lines)
            
            # Add back button
            if user_lang == 'uz':
                back_text = "🔙 Orqaga"
            elif user_lang == 'ru':
                back_text = "🔙 Назад"
            else:
                back_text = "🔙 Back"
            
            keyboard_buttons.append([InlineKeyboardButton(text=back_text, callback_data="back_to_main")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await message.answer(text, reply_markup=keyboard)
        
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



# Admin buttons are only accessible via /admin command




# === BROADCAST HANDLERS ===



@dp.message(Command('cancel'))
async def cancel_command(message: Message, state: FSMContext):
    """Handle /cancel command to cancel current operation."""
    user = await BotService.update_user(message)
    await state.clear()
    
    # Clear any stored data
    if message.from_user.id in broadcast_data:
        del broadcast_data[message.from_user.id]
    if message.from_user.id in user_sessions:
        del user_sessions[message.from_user.id]
    
    await message.answer(
        "❌ **Operation Cancelled**\n\nAll current operations have been cancelled.",
        reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
    )


@dp.message(BroadcastStates.waiting_for_message)
async def broadcast_message_received(message: Message, state: FSMContext):
    """Handle received broadcast message and send immediately."""
    # Check for cancel
    if message.text and (message.text.lower() in ['/cancel', 'cancel'] or "cancel" in message.text.lower()):
        user = await BotService.update_user(message)
        await state.clear()
        await message.answer(
            "❌ **Broadcast Cancelled**",
            reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
        )
        return

    # Validate message
    if not message.text or len(message.text) > settings.bot.max_message_length:
        await message.answer(
            f"❌ **Invalid Message**\n\nMessage must be text and under {settings.bot.max_message_length} characters. Please try again or send /cancel.",
        )
        return

    # Get recipients
    recipient_ids = await db.get_broadcast_users()
    if not recipient_ids:
        await message.answer("⚠️ **No users to send broadcast to.**")
        await state.clear()
        return

    # Acknowledge and inform admin
    await message.answer(f"📤 Sending your message to {len(recipient_ids)} users...")

    # Send broadcast
    sent_count = 0
    failed_count = 0
    semaphore = asyncio.Semaphore(10)  # Limit concurrent sends

    async def send_to_user(recipient_id: int):
        nonlocal sent_count, failed_count
        async with semaphore:
            try:
                await bot.send_message(recipient_id, message.text, parse_mode="Markdown")
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to {recipient_id}: {e}")
                failed_count += 1
            finally:
                await asyncio.sleep(settings.bot.broadcast_delay)

    # Send to all users concurrently
    await asyncio.gather(*(send_to_user(rid) for rid in recipient_ids), return_exceptions=True)

    # Log broadcast
    await db.log_broadcast(message.from_user.id, message.text, sent_count, failed_count)
    await db.log_admin_action(
        message.from_user.id,
        "broadcast_completed",
        details=f"Broadcast sent: {sent_count} success, {failed_count} failed"
    )

    # Clear state and show simple result
    user = await BotService.update_user(message)
    await state.clear()
    await message.answer(
        f"✅ **Broadcast Complete**\n\nSent: {sent_count}\nFailed: {failed_count}",
        reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
    )


# === NAVIGATION HANDLERS ===

@dp.message(F.text.in_(BACK_MAIN_LABELS))
async def back_to_main_handler(message: Message):
    """Handle back to main menu button."""
    user = await BotService.update_user(message)
    back_text = get_text("back_main_menu", user.language or DEFAULT_LANGUAGE)
    await BotService.send_main_menu(message, back_text)




# === CALLBACK QUERY HANDLERS ===

# === BOT MANAGEMENT CALLBACK HANDLERS ===

@dp.callback_query(F.data.startswith("delete_bot_"))
async def delete_bot_callback(callback: CallbackQuery):
    """Handle delete bot callback."""
    user_id = callback.from_user.id
    
    try:
        bot_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid bot ID", show_alert=True)
        return
    
    # Import bot manager
    from bot_manager import bot_manager
    
    try:
        # Check if user owns this bot
        user_bots = await bot_manager.get_user_bots(user_id)
        bot_to_delete = None
        
        for bot in user_bots:
            if bot['id'] == bot_id:
                bot_to_delete = bot
                break
        
        if not bot_to_delete:
            await callback.answer("❌ Bot not found or access denied", show_alert=True)
            return
        
        user = await db.get_user(user_id)
        user_lang = user.language if user else DEFAULT_LANGUAGE
        
        # Create confirmation dialog
        from ui.formatters import escape_markdown
        safe_bot_name = escape_markdown(bot_to_delete['bot_name']) if bot_to_delete.get('bot_name') else "Unknown"
        
        if user_lang == 'uz':
            confirm_text = (
                f"⚠️ **Bot o'chirish tasdiqi**\n\n"
                f"🤖 **Bot:** {safe_bot_name}\n\n"
                f"❌ **Diqqat:** Bu amalni bekor qilib bo'lmaydi!\n"
                f"Bot butunlay o'chiriladi va qayta tiklanmaydi.\n\n"
                f"Haqiqatan ham o'chirishni xohlaysizmi?"
            )
            yes_text = "🗑️ Ha, o'chirish"
            no_text = "❌ Yo'q, bekor qilish"
        elif user_lang == 'ru':
            confirm_text = (
                f"⚠️ **Подтверждение удаления бота**\n\n"
                f"🤖 **Бот:** {safe_bot_name}\n\n"
                f"❌ **Внимание:** Это действие нельзя отменить!\n"
                f"Бот будет полностью удален и не может быть восстановлен.\n\n"
                f"Действительно хотите удалить?"
            )
            yes_text = "🗑️ Да, удалить"
            no_text = "❌ Нет, отменить"
        else:
            confirm_text = (
                f"⚠️ **Bot Deletion Confirmation**\n\n"
                f"🤖 **Bot:** {safe_bot_name}\n\n"
                f"❌ **Warning:** This action cannot be undone!\n"
                f"Bot will be completely deleted and cannot be recovered.\n\n"
                f"Are you sure you want to delete?"
            )
            yes_text = "🗑️ Yes, delete"
            no_text = "❌ No, cancel"
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=yes_text, callback_data=f"confirm_delete_{bot_id}")],
            [InlineKeyboardButton(text=no_text, callback_data="back_to_bots")]
        ])
        
        await callback.message.edit_text(confirm_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in delete_bot_callback: {e}")
        await callback.answer("❌ Error processing request", show_alert=True)


@dp.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete_bot_callback(callback: CallbackQuery):
    """Handle bot deletion confirmation."""
    user_id = callback.from_user.id
    
    try:
        bot_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid bot ID", show_alert=True)
        return
    
    # Import bot manager
    from bot_manager import bot_manager
    
    try:
        # Check if user owns this bot
        user_bots = await bot_manager.get_user_bots(user_id)
        bot_to_delete = None
        
        for bot in user_bots:
            if bot['id'] == bot_id:
                bot_to_delete = bot
                break
        
        if not bot_to_delete:
            await callback.answer("❌ Bot not found or access denied", show_alert=True)
            return
        
        user = await db.get_user(user_id)
        user_lang = user.language if user else DEFAULT_LANGUAGE
        
        # Show deleting message
        if user_lang == 'uz':
            deleting_text = "🗑️ Bot o'chirilmoqda..."
        elif user_lang == 'ru':
            deleting_text = "🗑️ Удаление бота..."
        else:
            deleting_text = "🗑️ Deleting bot..."
        
        await callback.message.edit_text(deleting_text)
        
        # Stop the bot if it's running
        if bot_to_delete['is_running']:
            await bot_manager.stop_bot(bot_id)
        
        # Delete from database
        await db.delete_user_bot(bot_id, user_id)
        
        # Show success message
        from ui.formatters import escape_markdown
        safe_bot_name = escape_markdown(bot_to_delete['bot_name']) if bot_to_delete.get('bot_name') else "Unknown"
        
        if user_lang == 'uz':
            success_text = (
                f"✅ **Bot muvaffaqiyatli o'chirildi!**\n\n"
                f"🤖 **O'chirilgan bot:** {safe_bot_name}\n\n"
                f"Bot butunlay o'chirildi va endi mavjud emas."
            )
        elif user_lang == 'ru':
            success_text = (
                f"✅ **Бот успешно удален!**\n\n"
                f"🤖 **Удаленный бот:** {safe_bot_name}\n\n"
                f"Бот полностью удален и больше недоступен."
            )
        else:
            success_text = (
                f"✅ **Bot deleted successfully!**\n\n"
                f"🤖 **Deleted bot:** {safe_bot_name}\n\n"
                f"Bot has been completely removed and is no longer available."
            )
        
        await callback.message.edit_text(success_text)
        await callback.answer()
        
        # Log the deletion
        await db.log_admin_action(
            user_id,
            "bot_deleted",
            target_user_id=user_id,
            details=f"Deleted bot {safe_bot_name} (ID: {bot_id})"
        )
        
        # Go back to bot list after delay
        await asyncio.sleep(3)
        
        # Refresh bot list by directly triggering the back_to_bots callback logic
        await back_to_bots_callback(callback)
        
    except Exception as e:
        logger.error(f"Error in confirm_delete_bot_callback: {e}")
        
        user = await db.get_user(user_id)
        user_lang = user.language if user else DEFAULT_LANGUAGE
        
        if user_lang == 'uz':
            error_text = "❌ **Xatolik!**\n\nBot o'chirishda xatolik yuz berdi."
        elif user_lang == 'ru':
            error_text = "❌ **Ошибка!**\n\nОшибка при удалении бота."
        else:
            error_text = "❌ **Error!**\n\nError deleting bot."
        
        await callback.message.edit_text(error_text)
        await callback.answer()


@dp.callback_query(F.data.startswith("toggle_bot_"))
async def toggle_bot_callback(callback: CallbackQuery):
    """Handle toggle bot (start/stop) callback."""
    user_id = callback.from_user.id
    
    try:
        bot_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid bot ID", show_alert=True)
        return
    
    # Import bot manager
    from bot_manager import bot_manager
    
    try:
        # Check if user owns this bot
        user_bots = await bot_manager.get_user_bots(user_id)
        target_bot = None
        
        for bot in user_bots:
            if bot['id'] == bot_id:
                target_bot = bot
                break
        
        if not target_bot:
            await callback.answer("❌ Bot not found or access denied", show_alert=True)
            return
        
        user = await db.get_user(user_id)
        user_lang = user.language if user else DEFAULT_LANGUAGE
        
        # Show processing message
        if target_bot['is_running']:
            if user_lang == 'uz':
                processing_text = "⏹️ Bot to'xtatilmoqda..."
            elif user_lang == 'ru':
                processing_text = "⏹️ Остановка бота..."
            else:
                processing_text = "⏹️ Stopping bot..."
        else:
            if user_lang == 'uz':
                processing_text = "🔄 Bot ishga tushirilmoqda..."
            elif user_lang == 'ru':
                processing_text = "🔄 Запуск бота..."
            else:
                processing_text = "🔄 Starting bot..."
        
        await callback.message.edit_text(processing_text)
        
        # Toggle bot status
        if target_bot['is_running']:
            # Stop the bot
            success = await bot_manager.stop_bot(bot_id)
            action = "stopped"
        else:
            # Start the bot
            success = await bot_manager.restart_bot(bot_id)
            action = "started"
        
        # Show result message
        from ui.formatters import escape_markdown
        safe_bot_name = escape_markdown(target_bot['bot_name']) if target_bot.get('bot_name') else "Unknown"
        
        if success:
            if action == "stopped":
                if user_lang == 'uz':
                    result_text = f"⏹️ **Bot to'xtatildi!**\n\n🤖 **Bot:** {safe_bot_name}\n\nBot muvaffaqiyatli to'xtatildi."
                elif user_lang == 'ru':
                    result_text = f"⏹️ **Бот остановлен!**\n\n🤖 **Бот:** {safe_bot_name}\n\nБот успешно остановлен."
                else:
                    result_text = f"⏹️ **Bot stopped!**\n\n🤖 **Bot:** {safe_bot_name}\n\nBot has been stopped successfully."
            else:
                if user_lang == 'uz':
                    result_text = f"🔄 **Bot ishga tushirildi!**\n\n🤖 **Bot:** {safe_bot_name}\n\nBot muvaffaqiyatli ishga tushirildi."
                elif user_lang == 'ru':
                    result_text = f"🔄 **Бот запущен!**\n\n🤖 **Бот:** {safe_bot_name}\n\nБот успешно запущен."
                else:
                    result_text = f"🔄 **Bot started!**\n\n🤖 **Bot:** {safe_bot_name}\n\nBot has been started successfully."
        else:
            if user_lang == 'uz':
                result_text = f"❌ **Xatolik!**\n\n🤖 **Bot:** {safe_bot_name}\n\nBot {action} qilishda xatolik yuz berdi."
            elif user_lang == 'ru':
                result_text = f"❌ **Ошибка!**\n\n🤖 **Бот:** {safe_bot_name}\n\nОшибка при {'остановке' if action == 'stopped' else 'запуске'} бота."
            else:
                result_text = f"❌ **Error!**\n\n🤖 **Bot:** {safe_bot_name}\n\nError {action.replace('ed', 'ing')} bot."
        
        await callback.message.edit_text(result_text)
        await callback.answer()
        
        # Log the action
        await db.log_admin_action(
            user_id,
            f"bot_{action}",
            target_user_id=user_id,
            details=f"Bot {safe_bot_name} (ID: {bot_id}) {action}"
        )
        
        # Go back to bot list after delay
        await asyncio.sleep(3)
        
        # Refresh bot list by directly triggering the back_to_bots callback logic
        await back_to_bots_callback(callback)
        
    except Exception as e:
        logger.error(f"Error in toggle_bot_callback: {e}")
        await callback.answer("❌ Error processing request", show_alert=True)


@dp.callback_query(F.data.startswith("manage_bot_"))
async def manage_bot_callback(callback: CallbackQuery):
    """Handle manage bot callback - show detailed bot information."""
    user_id = callback.from_user.id
    
    try:
        bot_id = int(callback.data.split("_")[2])
    except (ValueError, IndexError):
        await callback.answer("❌ Invalid bot ID", show_alert=True)
        return
    
    # Import bot manager
    from bot_manager import bot_manager
    
    try:
        # Check if user owns this bot
        user_bots = await bot_manager.get_user_bots(user_id)
        target_bot = None
        
        for bot in user_bots:
            if bot['id'] == bot_id:
                target_bot = bot
                break
        
        if not target_bot:
            await callback.answer("❌ Bot not found or access denied", show_alert=True)
            return
        
        user = await db.get_user(user_id)
        user_lang = user.language if user else DEFAULT_LANGUAGE
        
        # Format detailed bot information
        from ui.formatters import escape_markdown
        safe_bot_name = escape_markdown(target_bot['bot_name']) if target_bot.get('bot_name') else "Unknown"
        safe_bot_username = escape_markdown(target_bot.get('bot_username', 'N/A'))
        
        status_emoji = "🟢" if target_bot['is_running'] else "🔴"
        created_date = target_bot['created_at'][:10] if target_bot.get('created_at') else (
            'Noma\'lum' if user_lang == 'uz' else 
            'Неизвестно' if user_lang == 'ru' else 'Unknown'
        )
        
        if user_lang == 'uz':
            status_text = "Ishlamoqda" if target_bot['is_running'] else "To'xtatilgan"
            info_text = (
                f"⚙️ **Bot ma'lumotlari**\n\n"
                f"🤖 **Nom:** {safe_bot_name}\n"
                f"📱 **Username:** @{safe_bot_username}\n"
                f"{status_emoji} **Holat:** {status_text}\n"
                f"📅 **Yaratilgan:** {created_date}\n"
                f"🆔 **ID:** {bot_id}\n\n"
                f"💡 **Bot boshqaruvi:**\n"
                f"• Bot to'xtatish/ishga tushirish\n"
                f"• Bot o'chirish (qaytarib bo'lmaydi!)\n"
                f"• Bot statistikasini ko'rish"
            )
            back_text = "🔙 Botlarga qaytish"
        elif user_lang == 'ru':
            status_text = "Работает" if target_bot['is_running'] else "Остановлен"
            info_text = (
                f"⚙️ **Информация о боте**\n\n"
                f"🤖 **Имя:** {safe_bot_name}\n"
                f"📱 **Username:** @{safe_bot_username}\n"
                f"{status_emoji} **Статус:** {status_text}\n"
                f"📅 **Создан:** {created_date}\n"
                f"🆔 **ID:** {bot_id}\n\n"
                f"💡 **Управление ботом:**\n"
                f"• Остановка/запуск бота\n"
                f"• Удаление бота (необратимо!)\n"
                f"• Просмотр статистики бота"
            )
            back_text = "🔙 К ботам"
        else:
            status_text = "Running" if target_bot['is_running'] else "Stopped"
            info_text = (
                f"⚙️ **Bot Information**\n\n"
                f"🤖 **Name:** {safe_bot_name}\n"
                f"📱 **Username:** @{safe_bot_username}\n"
                f"{status_emoji} **Status:** {status_text}\n"
                f"📅 **Created:** {created_date}\n"
                f"🆔 **ID:** {bot_id}\n\n"
                f"💡 **Bot Management:**\n"
                f"• Start/stop bot\n"
                f"• Delete bot (irreversible!)\n"
                f"• View bot statistics"
            )
            back_text = "🔙 Back to Bots"
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=back_text, callback_data="back_to_bots")]
        ])
        
        await callback.message.edit_text(info_text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in manage_bot_callback: {e}")
        await callback.answer("❌ Error loading bot information", show_alert=True)


@dp.callback_query(F.data == "back_to_bots")
async def back_to_bots_callback(callback: CallbackQuery):
    """Handle back to bots callback."""
    await callback.answer()
    
    # Import bot manager to get user's bots
    from bot_manager import bot_manager
    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    user_lang = user.language if user else DEFAULT_LANGUAGE
    
    try:
        # Get user's bots
        user_bots = await bot_manager.get_user_bots(user_id)
        
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
            
            await callback.message.answer(
                text,
                reply_markup=get_user_keyboard(user.is_admin if user else False, user_lang)
            )
        else:
            # Show user's bots with inline management buttons
            from ui.formatters import escape_markdown
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            if user_lang == 'uz':
                text_lines = ["🤖 **Mening botlarim**\n"]
            elif user_lang == 'ru':
                text_lines = ["🤖 **Мои боты**\n"]
            else:
                text_lines = ["🤖 **My Bots**\n"]
            
            # Create inline keyboard with bot management options
            keyboard_buttons = []
            
            for i, bot_data in enumerate(user_bots, 1):
                status_emoji = "🟢" if bot_data['is_running'] else "🔴"
                
                # Language-specific status text
                if user_lang == 'uz':
                    status_text = "Ishlamoqda" if bot_data['is_running'] else "To'xtatilgan"
                elif user_lang == 'ru':
                    status_text = "Работает" if bot_data['is_running'] else "Остановлен"
                else:
                    status_text = "Running" if bot_data['is_running'] else "Stopped"
                
                created_date = bot_data['created_at'][:10] if bot_data.get('created_at') else (
                    'Noma\'lum' if user_lang == 'uz' else 
                    'Неизвестно' if user_lang == 'ru' else 'Unknown'
                )
                
                # Escape bot name and username to prevent markdown issues
                safe_bot_name = escape_markdown(bot_data['bot_name']) if bot_data.get('bot_name') else "Unknown"
                safe_bot_username = escape_markdown(bot_data.get('bot_username', 'N/A'))
                
                text_lines.append(
                    f"**{i}.** 🤖 **{safe_bot_name}**\n"
                    f"📱 @{safe_bot_username}\n"
                    f"{status_emoji} {status_text}\n"
                    f"📅 {created_date}\n"
                )
                
                # Create management buttons for this bot
                bot_id = bot_data['id']
                
                # Truncate bot name for button display
                button_name = bot_data['bot_name']
                if len(button_name) > 20:
                    button_name = button_name[:17] + "..."
                
                # Language-specific button texts
                if user_lang == 'uz':
                    manage_text = f"⚙️ {button_name}"
                    restart_text = "🔄 Qayta ishga tushirish" if not bot_data['is_running'] else "⏹️ To'xtatish"
                    delete_text = "🗑️ O'chirish"
                elif user_lang == 'ru':
                    manage_text = f"⚙️ {button_name}"
                    restart_text = "🔄 Перезапустить" if not bot_data['is_running'] else "⏹️ Остановить"
                    delete_text = "🗑️ Удалить"
                else:
                    manage_text = f"⚙️ {button_name}"
                    restart_text = "🔄 Restart" if not bot_data['is_running'] else "⏹️ Stop"
                    delete_text = "🗑️ Delete"
                
                # Add row with manage and control buttons
                keyboard_buttons.append([
                    InlineKeyboardButton(text=manage_text, callback_data=f"manage_bot_{bot_id}")
                ])
                keyboard_buttons.append([
                    InlineKeyboardButton(text=restart_text, callback_data=f"toggle_bot_{bot_id}"),
                    InlineKeyboardButton(text=delete_text, callback_data=f"delete_bot_{bot_id}")
                ])
            
            # Add summary and total count
            if user_lang == 'uz':
                text_lines.append(f"\n📊 **Jami:** {len(user_bots)} ta bot")
                text_lines.append("\n💡 **Botlarni boshqarish uchun quyidagi tugmalardan foydalaning:**")
            elif user_lang == 'ru':
                text_lines.append(f"\n📊 **Всего:** {len(user_bots)} ботов")
                text_lines.append("\n💡 **Используйте кнопки ниже для управления ботами:**")
            else:
                text_lines.append(f"\n📊 **Total:** {len(user_bots)} bots")
                text_lines.append("\n💡 **Use the buttons below to manage your bots:**")
            
            text = "\n".join(text_lines)
            
            # Add back button
            if user_lang == 'uz':
                back_text = "🔙 Orqaga"
            elif user_lang == 'ru':
                back_text = "🔙 Назад"
            else:
                back_text = "🔙 Back"
            
            keyboard_buttons.append([InlineKeyboardButton(text=back_text, callback_data="back_to_main")])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            await callback.message.answer(text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in back_to_bots_callback: {e}")
        error_text = (
            "❌ Botlarni yuklashda xatolik yuz berdi." if user_lang == 'uz' else
            "❌ Ошибка при загрузке ботов." if user_lang == 'ru' else
            "❌ Error loading bots."
        )
        await callback.message.answer(
            error_text,
            reply_markup=get_user_keyboard(user.is_admin if user else False, user_lang)
        )


@dp.callback_query(F.data == "back_to_main")
async def back_to_main_callback(callback: CallbackQuery):
    """Handle back to main menu callback."""
    user = await db.get_user(callback.from_user.id)
    user_lang = user.language if user else DEFAULT_LANGUAGE
    
    welcome_text = MessageFormatter.format_welcome_message(
        user.full_name if user else callback.from_user.first_name or "User",
        user.is_admin if user else callback.from_user.id in settings.get_admin_ids(),
        user_lang
    )
    
    await callback.message.answer(
        welcome_text,
        reply_markup=get_user_keyboard(
            user.is_admin if user else callback.from_user.id in settings.get_admin_ids(),
            user_lang
        )
    )
    await callback.answer()


# === ADMIN CALLBACK HANDLERS ===

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
    """Handle broadcast button in admin panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Set state to wait for broadcast message
    await state.set_state(BroadcastStates.waiting_for_message)
    
    await callback.message.edit_text(
        "📢 **Send Broadcast Message**\n\n"
        "Type your message and it will be sent to all users immediately.\n\n"
        "❌ Send /cancel to cancel"
    )
    
    await callback.answer()
    await db.log_admin_action(user_id, "admin_broadcast_start", details="Started broadcast from admin panel")


@dp.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery):
    """Handle all users button in admin panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Get all users
        users = await db.get_users()
        logger.info(f"Retrieved {len(users)} users from database")
        
        if not users:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
            ])
            await callback.message.edit_text(
                "👥 **All Users**\n\n"
                "❌ No users found in the database.",
                reply_markup=keyboard
            )
            await callback.answer()
            return
        
        # Format user list with improved error handling
        from ui.formatters import escape_markdown, PaginationHelper
        
        # Limit users to avoid message length issues
        MAX_USERS_DISPLAY = 30  # Reduced to ensure message stays under Telegram's limit
        display_users = users[:MAX_USERS_DISPLAY]
        user_lines = []
        
        for i, user in enumerate(display_users, 1):
            try:
                # Safely get user properties with fallbacks
                user_id_str = str(getattr(user, 'user_id', 'Unknown'))
                username = getattr(user, 'username', None)
                first_name = getattr(user, 'first_name', None)
                last_name = getattr(user, 'last_name', None)
                is_admin = getattr(user, 'is_admin', False)
                is_banned = getattr(user, 'is_banned', False)
                is_active = getattr(user, 'is_active', True)
                
                # Status icon based on user type
                if is_banned:
                    status = "🔴"
                elif is_admin:
                    status = "👑"
                elif is_active:
                    status = "🟢"
                else:
                    status = "⚪"
                
                # Construct display name safely
                name_parts = []
                if first_name:
                    name_parts.append(str(first_name))
                if last_name:
                    name_parts.append(str(last_name))
                
                if name_parts:
                    display_name = " ".join(name_parts)
                else:
                    display_name = f"User {user_id_str}"
                
                # Truncate long names
                if len(display_name) > 25:
                    display_name = display_name[:22] + "..."
                
                # Username display
                username_display = f"@{username}" if username else "No username"
                if len(username_display) > 20:
                    username_display = username_display[:17] + "..."
                
                # Escape markdown properly
                safe_name = escape_markdown(display_name)
                safe_username = escape_markdown(username_display)
                
                # Create user line with role indicator
                role = "Admin" if is_admin else "User"
                user_lines.append(f"{i}. {status} **{safe_name}** ({safe_username}) - {role}")
                
            except Exception as user_error:
                logger.error(f"Error formatting user {i}: {user_error}")
                # Safe fallback format
                try:
                    fallback_id = getattr(user, 'user_id', f'Unknown_{i}')
                    user_lines.append(f"{i}. 🔵 **User {fallback_id}** (Format error)")
                except:
                    user_lines.append(f"{i}. ❓ **Unknown User** (Data error)")
        
        # Create header with statistics
        active_count = sum(1 for u in users if getattr(u, 'is_active', True) and not getattr(u, 'is_banned', False))
        banned_count = sum(1 for u in users if getattr(u, 'is_banned', False))
        admin_count = sum(1 for u in users if getattr(u, 'is_admin', False))
        premium_count = sum(1 for u in users if getattr(u, 'effective_premium_status', False))
        
        # Get active users this week count
        active_week_count = await db.get_active_users_this_week()
        
        text_lines = [
            "👥 **All Users - Admin Panel**\n",
            f"📊 **Statistics:**",
            f"• Total: {len(users)} users",
            f"• Active: {active_count} users", 
            f"• Active this week: {active_week_count} users",
            f"• Banned: {banned_count} users",
            f"• Admins: {admin_count} users",
            f"• Premium: {premium_count} users\n"
        ]
        
        if len(users) > MAX_USERS_DISPLAY:
            text_lines.append(f"⚠️ *Showing first {MAX_USERS_DISPLAY} users only*\n")
        
        text_lines.append("👤 **User List:**")
        text_lines.extend(user_lines)
        
        # Add helpful information
        if len(users) > MAX_USERS_DISPLAY:
            text_lines.append(f"\n... and {len(users) - MAX_USERS_DISPLAY} more users")
        
        text_lines.append("\n💡 Use database export for complete user list")
        
        # Create keyboard with additional options
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Export CSV", callback_data="admin_export_users")],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_users_refresh")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        
        final_text = "\n".join(text_lines)
        
        # Ensure message length is within Telegram's limits (4096 characters)
        if len(final_text) > 4000:
            # Truncate user list if too long
            header_text = "\n".join(text_lines[:6])  # Keep header
            footer_text = "\n\n💡 Use database export for complete user list"
            available_space = 4000 - len(header_text) - len(footer_text)
            
            truncated_users = []
            current_length = 0
            for line in user_lines:
                if current_length + len(line) + 1 < available_space:
                    truncated_users.append(line)
                    current_length += len(line) + 1
                else:
                    break
            
            final_text = header_text + "\n" + "\n".join(truncated_users) + footer_text
            logger.info(f"Truncated user list to fit in {len(final_text)} characters")
        
        logger.info(f"Sending user list with {len(final_text)} characters")
        
        await callback.message.edit_text(
            final_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        # Log admin action
        await db.log_admin_action(user_id, "view_all_users", details=f"Viewed {len(users)} users")
        
    except Exception as e:
        logger.error(f"Error in admin_users_callback: {e}")
        logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        
        # Send error message to admin
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
            ])
            await callback.message.edit_text(
                "❌ **Error Loading Users**\n\n"
                "There was an error retrieving the user list. "
                "Please try again or check the bot logs.",
                reply_markup=keyboard
            )
        except:
            # If even error message fails, use callback answer
            await callback.answer("❌ Critical error loading users", show_alert=True)


@dp.callback_query(F.data == "admin_bots")
async def admin_bots_callback(callback: CallbackQuery):
    """Handle bot management button in admin panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Import bot manager
        from bot_manager import bot_manager
        
        # Get all bots from database
        all_bots = await db.get_all_user_bots()
        
        if not all_bots:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
            ])
            await callback.message.edit_text(
                "🤖 **Bot Management**\n\n"
                "❌ No user bots found in the database.",
                reply_markup=keyboard
            )
            await callback.answer()
            return
        
        # Get bot statistics
        stats = await bot_manager.get_all_bots_stats()
        
        # Get expired and expiring bots
        expired_bots = await db.get_expired_bots()
        expiring_bots = await db.get_expiring_bots(hours=168)  # Expiring in next 7 days (7*24=168 hours)
        
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create bot management overview
        text_lines = [
            f"🤖 **Bot Management - Admin Panel** (Updated at {current_time})\n",
            f"📅 **Date:** {current_date}\n",
            f"📊 **Bot Statistics:**",
            f"• Total Bots: {stats.get('total_bots', len(all_bots))} bots",
            f"• Running Bots: {stats.get('running_bots', 0)} bots",
            f"• Pending Approval: {stats.get('pending_bots', 0)} bots",
            f"• Approved Bots: {stats.get('approved_bots', 0)} bots",
            f"• Expired Bots: {len(expired_bots)} bots",
            f"• Expiring Soon: {len(expiring_bots)} bots\n"
        ]
        
        # Show expired bots if any
        if expired_bots:
            text_lines.append("⚠️ **Expired Bots:**")
            for bot in expired_bots[:5]:  # Show first 5 expired bots
                text_lines.append(f"• {bot['bot_name']} (ID: {bot['id']}) - Expired")
            if len(expired_bots) > 5:
                text_lines.append(f"... and {len(expired_bots) - 5} more")
            text_lines.append("")
        
        # Show expiring bots if any
        if expiring_bots:
            text_lines.append("⏰ **Expiring Soon (Next 7 days):**")
            for bot in expiring_bots[:5]:  # Show first 5 expiring bots
                time_left = await db.get_bot_time_left(bot['id'])
                days_left = time_left.days if time_left else 0
                text_lines.append(f"• {bot['bot_name']} (ID: {bot['id']}) - {days_left} days left")
            if len(expiring_bots) > 5:
                text_lines.append(f"... and {len(expiring_bots) - 5} more")
            text_lines.append("")
        
        text_lines.append("💡 **Available Actions:**")
        text_lines.append("• Handle expired bots")
        text_lines.append("• Extend bot time")
        text_lines.append("• View all bots")
        
        final_text = "\n".join(text_lines)
        
        # Create keyboard with management options
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard_buttons = []
        
        # Add action buttons
        if expired_bots:
            keyboard_buttons.append([
                InlineKeyboardButton(text=f"⚠️ Handle Expired Bots ({len(expired_bots)})", callback_data="admin_handle_expired")
            ])
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="⏰ Extend Bot Time", callback_data="admin_extend_time")],
            [InlineKeyboardButton(text="📋 View All Bots", callback_data="admin_view_all_bots")],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_bots_refresh")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            final_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        # Log admin action
        await db.log_admin_action(user_id, "view_bot_management", details=f"Viewed bot management panel with {len(all_bots)} total bots")
        
    except Exception as e:
        logger.error(f"Error in admin_bots_callback: {e}")
        logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        
        # Send error message to admin
        try:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
            ])
            await callback.message.edit_text(
                "❌ **Error Loading Bot Management**\n\n"
                "There was an error retrieving bot management data. "
                "Please try again or check the bot logs.",
                reply_markup=keyboard
            )
        except:
            # If even error message fails, use callback answer
            await callback.answer("❌ Critical error loading bot management", show_alert=True)


@dp.callback_query(F.data == "admin_back")
async def admin_back_callback(callback: CallbackQuery):
    """Handle back to admin panel button."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Recreate admin panel
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Send Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 All Users", callback_data="admin_users")],
        [InlineKeyboardButton(text="🤖 Bot Management", callback_data="admin_bots")],
        [InlineKeyboardButton(text="🔍 User Search", callback_data="admin_user_search")],
        [InlineKeyboardButton(text="📊 Daily Statistics", callback_data="admin_daily_stats")],
        [InlineKeyboardButton(text="📺 Must Join Channels", callback_data="admin_mandatory_channels")],
        [InlineKeyboardButton(text="❌ Close", callback_data="admin_close")]
    ])
    
    await callback.message.edit_text(
        "👑 **Admin Panel**\n\nChoose an option:",
        reply_markup=keyboard
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_users_refresh")
async def admin_users_refresh_callback(callback: CallbackQuery):
    """Handle refresh button in admin users panel with timestamp to avoid duplicate content."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Show loading message first
        await callback.answer("🔄 Refreshing user list...", show_alert=False)
        
        # Get all users
        users = await db.get_users()
        logger.info(f"Refreshed and retrieved {len(users)} users from database")
        
        if not users:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
            ])
            # Add timestamp to avoid duplicate content error
            current_time = datetime.now().strftime("%H:%M:%S")
            await callback.message.edit_text(
                f"👥 **All Users** (Refreshed at {current_time})\n\n"
                "❌ No users found in the database.",
                reply_markup=keyboard
            )
            return
        
        # Reuse the same formatting logic as admin_users_callback
        from ui.formatters import escape_markdown, PaginationHelper
        
        # Limit users to avoid message length issues
        MAX_USERS_DISPLAY = 30
        display_users = users[:MAX_USERS_DISPLAY]
        user_lines = []
        
        for i, user in enumerate(display_users, 1):
            try:
                # Safely get user properties with fallbacks
                user_id_str = str(getattr(user, 'user_id', 'Unknown'))
                username = getattr(user, 'username', None)
                first_name = getattr(user, 'first_name', None)
                last_name = getattr(user, 'last_name', None)
                is_admin = getattr(user, 'is_admin', False)
                is_banned = getattr(user, 'is_banned', False)
                is_active = getattr(user, 'is_active', True)
                
                # Status icon based on user type
                if is_banned:
                    status = "🔴"
                elif is_admin:
                    status = "👑"
                elif is_active:
                    status = "🟢"
                else:
                    status = "⚪"
                
                # Construct display name safely
                name_parts = []
                if first_name:
                    name_parts.append(str(first_name))
                if last_name:
                    name_parts.append(str(last_name))
                
                if name_parts:
                    display_name = " ".join(name_parts)
                else:
                    display_name = f"User {user_id_str}"
                
                # Truncate long names
                if len(display_name) > 25:
                    display_name = display_name[:22] + "..."
                
                # Username display
                username_display = f"@{username}" if username else "No username"
                if len(username_display) > 20:
                    username_display = username_display[:17] + "..."
                
                # Escape markdown properly
                safe_name = escape_markdown(display_name)
                safe_username = escape_markdown(username_display)
                
                # Create user line with role indicator
                role = "Admin" if is_admin else "User"
                user_lines.append(f"{i}. {status} **{safe_name}** ({safe_username}) - {role}")
                
            except Exception as user_error:
                logger.error(f"Error formatting user {i} during refresh: {user_error}")
                # Safe fallback format
                try:
                    fallback_id = getattr(user, 'user_id', f'Unknown_{i}')
                    user_lines.append(f"{i}. 🔵 **User {fallback_id}** (Format error)")
                except:
                    user_lines.append(f"{i}. ❓ **Unknown User** (Data error)")
        
        # Create header with statistics and timestamp
        active_count = sum(1 for u in users if getattr(u, 'is_active', True) and not getattr(u, 'is_banned', False))
        banned_count = sum(1 for u in users if getattr(u, 'is_banned', False))
        admin_count = sum(1 for u in users if getattr(u, 'is_admin', False))
        premium_count = sum(1 for u in users if getattr(u, 'effective_premium_status', False))
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Get active users this week count
        active_week_count = await db.get_active_users_this_week()
        
        text_lines = [
            f"👥 **All Users - Admin Panel** (Refreshed at {current_time})\n",
            f"📊 **Statistics:**",
            f"• Total: {len(users)} users",
            f"• Active: {active_count} users", 
            f"• Active this week: {active_week_count} users",
            f"• Banned: {banned_count} users",
            f"• Admins: {admin_count} users",
            f"• Premium: {premium_count} users\n"
        ]
        
        if len(users) > MAX_USERS_DISPLAY:
            text_lines.append(f"⚠️ *Showing first {MAX_USERS_DISPLAY} users only*\n")
        
        text_lines.append("👤 **User List:**")
        text_lines.extend(user_lines)
        
        # Add helpful information
        if len(users) > MAX_USERS_DISPLAY:
            text_lines.append(f"\n... and {len(users) - MAX_USERS_DISPLAY} more users")
        
        text_lines.append("\n💡 Use database export for complete user list")
        
        # Create keyboard with additional options
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Export CSV", callback_data="admin_export_users")],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_users_refresh")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        
        final_text = "\n".join(text_lines)
        
        # Ensure message length is within Telegram's limits
        if len(final_text) > 4000:
            # Truncate user list if too long
            header_text = "\n".join(text_lines[:6])  # Keep header with timestamp
            footer_text = "\n\n💡 Use database export for complete user list"
            available_space = 4000 - len(header_text) - len(footer_text)
            
            truncated_users = []
            current_length = 0
            for line in user_lines:
                if current_length + len(line) + 1 < available_space:
                    truncated_users.append(line)
                    current_length += len(line) + 1
                else:
                    break
            
            final_text = header_text + "\n" + "\n".join(truncated_users) + footer_text
            logger.info(f"Truncated refreshed user list to fit in {len(final_text)} characters")
        
        logger.info(f"Sending refreshed user list with {len(final_text)} characters")
        
        await callback.message.edit_text(
            final_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # Log admin action
        await db.log_admin_action(user_id, "refresh_all_users", details=f"Refreshed and viewed {len(users)} users")
        
    except Exception as e:
        logger.error(f"Error in admin_users_refresh_callback: {e}")
        logger.error(f"Exception details: {type(e).__name__}: {str(e)}")
        
        # Handle the specific Telegram error for unchanged content
        if "message is not modified" in str(e).lower():
            await callback.answer("✅ User list is already up to date!", show_alert=True)
        else:
            # Send error message to admin
            try:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
                ])
                await callback.message.edit_text(
                    "❌ **Error Refreshing Users**\n\n"
                    "There was an error refreshing the user list. "
                    "Please try again or check the bot logs.",
                    reply_markup=keyboard
                )
            except:
                # If even error message fails, use callback answer
                await callback.answer("❌ Critical error refreshing users", show_alert=True)


@dp.callback_query(F.data == "admin_export_users")
async def admin_export_users_callback(callback: CallbackQuery):
    """Handle export users CSV button in admin panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        await callback.answer("🔄 Preparing user export...", show_alert=False)
        
        # Get all users
        users = await db.get_users()
        
        if not users:
            await callback.answer("❌ No users to export", show_alert=True)
            return
        
        # Create CSV file
        csv_file = DataExporter.create_users_csv(users)
        
        # Send the file
        await bot.send_document(
            callback.message.chat.id,
            csv_file,
            caption=f"📋 **User Database Export**\n\n"
                   f"📊 **Total Users:** {len(users)}\n"
                   f"🗓️ **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                   f"📝 This file contains all user data in CSV format.",
            parse_mode="Markdown"
        )
        
        # Log the export
        await db.log_admin_action(user_id, "export_users_csv", details=f"Exported {len(users)} users to CSV")
        logger.info(f"Admin {user_id} exported {len(users)} users to CSV")
        
    except Exception as e:
        logger.error(f"Error exporting users CSV: {e}")
        await callback.answer("❌ Error creating export file", show_alert=True)


@dp.callback_query(F.data == "admin_daily_stats")
async def admin_daily_stats_callback(callback: CallbackQuery):
    """Handle daily statistics button in admin panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Get daily statistics
        daily_stats = await db.get_daily_statistics()
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create detailed daily statistics message
        stats_text = (
            f"📊 **Daily Statistics** (Updated at {current_time})\n\n"
            f"📅 **Date:** {current_date}\n\n"
            f"👥 **User Activity (24 hours):**\n"
            f"• Active users: {daily_stats['active_users_24h']} users\n"
            f"• New registrations: {daily_stats['new_users_today']} users\n\n"
            f"💬 **Messages:**\n"
            f"• Messages today: {daily_stats['messages_today']} messages\n\n"
            f"🤖 **Bot Activity:**\n"
            f"• New bots created: {daily_stats['new_bots_today']} bots\n\n"
            f"⏰ **Note:** Statistics are based on the last 24 hours and current date."
        )
        
        # Create keyboard with refresh and back options
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh Stats", callback_data="admin_daily_stats_refresh")],
            [InlineKeyboardButton(text="📈 Get Weekly Overview", callback_data="admin_weekly_stats")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=keyboard
        )
        await callback.answer()
        
        # Log admin action
        await db.log_admin_action(user_id, "view_daily_statistics", details="Viewed daily statistics")
        
    except Exception as e:
        logger.error(f"Error in admin_daily_stats_callback: {e}")
        await callback.answer("❌ Error loading daily statistics", show_alert=True)


@dp.callback_query(F.data == "admin_daily_stats_refresh")
async def admin_daily_stats_refresh_callback(callback: CallbackQuery):
    """Handle daily statistics refresh button."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Show loading message
        await callback.answer("🔄 Refreshing daily statistics...", show_alert=False)
        
        # Get fresh daily statistics
        daily_stats = await db.get_daily_statistics()
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create refreshed statistics message
        stats_text = (
            f"📊 **Daily Statistics** (Refreshed at {current_time})\n\n"
            f"📅 **Date:** {current_date}\n\n"
            f"👥 **User Activity (24 hours):**\n"
            f"• Active users: {daily_stats['active_users_24h']} users\n"
            f"• New registrations: {daily_stats['new_users_today']} users\n\n"
            f"💬 **Messages:**\n"
            f"• Messages today: {daily_stats['messages_today']} messages\n\n"
            f"🤖 **Bot Activity:**\n"
            f"• New bots created: {daily_stats['new_bots_today']} bots\n\n"
            f"⏰ **Note:** Statistics are based on the last 24 hours and current date."
        )
        
        # Create keyboard with options
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh Stats", callback_data="admin_daily_stats_refresh")],
            [InlineKeyboardButton(text="📈 Get Weekly Overview", callback_data="admin_weekly_stats")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=keyboard
        )
        
        # Log admin action
        await db.log_admin_action(user_id, "refresh_daily_statistics", details="Refreshed daily statistics")
        
    except Exception as e:
        logger.error(f"Error in admin_daily_stats_refresh_callback: {e}")
        if "message is not modified" in str(e).lower():
            await callback.answer("✅ Statistics are already up to date!", show_alert=True)
        else:
            await callback.answer("❌ Error refreshing statistics", show_alert=True)


@dp.callback_query(F.data == "admin_weekly_stats")
async def admin_weekly_stats_callback(callback: CallbackQuery):
    """Handle weekly statistics overview button."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Get comprehensive statistics including weekly data
        bot_stats = await db.get_statistics()
        current_time = datetime.now().strftime("%H:%M:%S")
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create comprehensive statistics message
        stats_text = (
            f"📈 **Weekly Overview** (Updated at {current_time})\n\n"
            f"📅 **Date:** {current_date}\n\n"
            f"👥 **User Statistics:**\n"
            f"• Total users: {bot_stats.total_users} users\n"
            f"• Active users: {bot_stats.active_users} users ({bot_stats.active_rate:.1f}%)\n"
            f"• Active this week: {bot_stats.active_users_week} users\n"
            f"• New today: {bot_stats.new_users_today} users\n"
            f"• Premium users: {bot_stats.premium_users} users ({bot_stats.premium_rate:.1f}%)\n"
            f"• Banned users: {bot_stats.banned_users} users\n"
            f"• Admin users: {bot_stats.admin_count} users\n\n"
            f"💬 **Message Activity:**\n"
            f"• Messages today: {bot_stats.messages_today} messages\n"
            f"• Total messages: {bot_stats.messages_total} messages\n\n"
            f"📊 **Engagement Metrics:**\n"
            f"• Weekly activity rate: {(bot_stats.active_users_week / max(bot_stats.total_users, 1) * 100):.1f}%\n"
            f"• Daily new users: {bot_stats.new_users_today} users\n"
            f"• Messages per user: {(bot_stats.messages_total / max(bot_stats.total_users, 1)):.1f}\n\n"
            f"⏰ **Note:** Weekly data based on last 7 days."
        )
        
        # Create keyboard with back option
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh Overview", callback_data="admin_weekly_stats")],
            [InlineKeyboardButton(text="📊 Back to Daily Stats", callback_data="admin_daily_stats")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=keyboard
        )
        await callback.answer()
        
        # Log admin action
        await db.log_admin_action(user_id, "view_weekly_statistics", details="Viewed weekly overview")
        
    except Exception as e:
        logger.error(f"Error in admin_weekly_stats_callback: {e}")
        await callback.answer("❌ Error loading weekly statistics", show_alert=True)


@dp.callback_query(F.data == "admin_user_search")
async def admin_user_search_callback(callback: CallbackQuery, state: FSMContext):
    """Handle user search button in admin panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Set state to wait for user input
    await state.set_state(UserSearchStates.waiting_for_user_input)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
    ])
    
    await callback.message.edit_text(
        "🔍 **User Search**\n\n"
        "Enter a user ID or username to search for detailed user information.\n\n"
        "**Examples:**\n"
        "• `123456789` (User ID)\n"
        "• `@username` (Username)\n"
        "• `username` (Username without @)\n\n"
        "❌ Send /cancel to cancel",
        reply_markup=keyboard
    )
    
    await callback.answer()
    await db.log_admin_action(user_id, "admin_user_search_start", details="Started user search from admin panel")


@dp.callback_query(F.data.startswith("remove_channel_"))
async def remove_channel_confirm_callback(callback: CallbackQuery):
    """Handle individual channel removal confirmation."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Extract channel ID from callback data
        channel_id = callback.data.split("_")[2]
        
        # Get channel information
        channel = await db.get_mandatory_channel(channel_id)
        if not channel:
            await callback.answer("❌ Channel not found", show_alert=True)
            return
        
        # Import escape function for safe markdown
        from ui.formatters import escape_markdown
        safe_channel_title = escape_markdown(channel.get('channel_title', 'Unknown'))
        safe_channel_username = escape_markdown(channel.get('channel_username', 'N/A'))
        
        # Create confirmation dialog
        confirmation_text = (
            f"⚠️ **Confirm Channel Removal**\n\n"
            f"📺 **Channel:** {safe_channel_title}\n"
            f"🔗 **Username:** @{safe_channel_username}\n"
            f"🆔 **ID:** `{channel_id}`\n"
            f"📊 **Status:** {'🟢 Active' if channel.get('is_active', True) else '🔴 Inactive'}\n\n"
            f"❌ **Warning:** This action will:\n"
            f"• Remove the channel from mandatory join list\n"
            f"• Stop enforcing membership for this channel\n"
            f"• Allow all users to access the bot without joining this channel\n\n"
            f"⚠️ **This action cannot be easily undone!**\n\n"
            f"Are you sure you want to remove this channel?"
        )
        
        # Create confirmation keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🗑️ Yes, Remove Channel", 
                callback_data=f"confirm_remove_{channel_id}"
            )],
            [InlineKeyboardButton(
                text="❌ No, Keep Channel", 
                callback_data="admin_remove_channel"
            )],
            [InlineKeyboardButton(
                text="🔙 Back to Management", 
                callback_data="admin_manage_channels"
            )]
        ])
        
        await callback.message.edit_text(
            confirmation_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        # Log admin action
        await db.log_admin_action(
            user_id, 
            "channel_removal_confirmation", 
            details=f"Requested removal confirmation for channel {safe_channel_title} (ID: {channel_id})"
        )
        
    except Exception as e:
        logger.error(f"Error in remove_channel_confirm_callback: {e}")
        await callback.answer("❌ Error loading channel information", show_alert=True)


@dp.callback_query(F.data.startswith("confirm_remove_"))
async def confirm_channel_removal_callback(callback: CallbackQuery):
    """Handle final confirmation and removal of mandatory channel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Extract channel ID from callback data
        channel_id = callback.data.split("_")[2]
        
        # Get channel information before removal
        channel = await db.get_mandatory_channel(channel_id)
        if not channel:
            await callback.answer("❌ Channel not found", show_alert=True)
            return
        
        # Show removing message
        await callback.message.edit_text("🗑️ **Removing channel from mandatory list...**")
        
        # Remove channel from database
        success = await db.remove_mandatory_channel(channel_id)
        
        # Import escape function for safe markdown
        from ui.formatters import escape_markdown
        safe_channel_title = escape_markdown(channel.get('channel_title', 'Unknown'))
        safe_channel_username = escape_markdown(channel.get('channel_username', 'N/A'))
        
        if success:
            # Success message
            success_text = (
                f"✅ **Channel Removed Successfully!**\n\n"
                f"📺 **Removed Channel:** {safe_channel_title}\n"
                f"🔗 **Username:** @{safe_channel_username}\n"
                f"🆔 **ID:** `{channel_id}`\n\n"
                f"The channel has been removed from the mandatory join list.\n"
                f"Users will no longer be required to join this channel to use the bot.\n\n"
                f"💡 **Note:** You can always add it back later if needed."
            )
            
            # Log successful removal
            await db.log_admin_action(
                user_id,
                "remove_mandatory_channel",
                details=f"Removed mandatory channel {safe_channel_title} (ID: {channel_id})"
            )
            
            logger.info(f"Admin {user_id} removed mandatory channel {safe_channel_title} (ID: {channel_id})")
            
        else:
            # Error message
            success_text = (
                f"❌ **Error Removing Channel**\n\n"
                f"📺 **Channel:** {safe_channel_title}\n"
                f"🆔 **ID:** `{channel_id}`\n\n"
                f"There was an error removing the channel from the database.\n"
                f"Please try again or contact support."
            )
        
        await callback.message.edit_text(
            success_text,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        # Return to channel management after delay
        await asyncio.sleep(4)
        
        # Create return keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Manage Channels", callback_data="admin_manage_channels")],
            [InlineKeyboardButton(text="📺 Channel Overview", callback_data="admin_mandatory_channels")],
            [InlineKeyboardButton(text="🔙 Admin Panel", callback_data="admin_back")]
        ])
        
        await callback.message.answer(
            "🔄 **Channel removal completed.**\n\n"
            "Use the buttons below to continue managing channels:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in confirm_channel_removal_callback: {e}")
        
        error_text = (
            "❌ **Critical Error**\n\n"
            "There was a critical error removing the channel.\n"
            "Please check the bot logs and try again."
        )
        
        await callback.message.edit_text(error_text)
        await callback.answer()


@dp.callback_query(F.data == "admin_mandatory_channels")
async def admin_mandatory_channels_callback(callback: CallbackQuery):
    """Handle mandatory channels button in admin panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Get all mandatory channels
        channels = await db.get_mandatory_channels(active_only=False)
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Calculate enhanced statistics
        active_channels = [ch for ch in channels if ch.get('is_active', True)]
        inactive_channels = [ch for ch in channels if not ch.get('is_active', True)]
        
        # Create enhanced header with better formatting
        text_lines = [
            "📺 **Mandatory Channels Management Portal**",
            "═" * 35 + "\n",
            f"⏰ **Last Updated:** {current_time}",
            f"📅 **Date:** {datetime.now().strftime('%Y-%m-%d')}\n",
            "📊 **Overview Statistics:**",
            f"┌─ 📈 **Total Channels:** {len(channels)} channels",
            f"├─ 🟢 **Active Channels:** {len(active_channels)} channels",
            f"├─ 🔴 **Inactive Channels:** {len(inactive_channels)} channels",
            f"└─ ⚡ **Enforcement Status:** {'✅ Active' if len(active_channels) > 0 else '❌ No enforcement'}\n"
        ]
        
        if channels:
            text_lines.append("📋 **Channel Directory:**\n")
            for i, channel in enumerate(channels[:8], 1):  # Reduced to 8 for better formatting
                status_emoji = "🟢" if channel.get('is_active', True) else "🔴"
                channel_title = channel.get('channel_title', 'Unknown Channel')
                channel_username = channel.get('channel_username', 'N/A')
                
                # Truncate long titles more elegantly
                if len(channel_title) > 25:
                    display_title = channel_title[:22] + "..."
                else:
                    display_title = channel_title
                
                # Import escape function to safely handle markdown characters
                from ui.formatters import escape_markdown
                
                # Safely escape channel data to prevent markdown parsing errors
                safe_channel_title = escape_markdown(display_title)
                safe_channel_username = escape_markdown(channel_username)
                
                # Enhanced channel display with better formatting
                text_lines.append(
                    f"🔸 **{i}.** {status_emoji} **{safe_channel_title}**"
                )
                text_lines.append(
                    f"   ├─ 📱 Username: @{safe_channel_username}"
                )
                text_lines.append(
                    f"   ├─ 🆔 Channel ID: `{channel.get('channel_id', 'N/A')}`"
                )
                text_lines.append(
                    f"   └─ 📊 Status: {'✅ Enforcing membership' if channel.get('is_active', True) else '❌ Not enforced'}\n"
                )
            
            if len(channels) > 8:
                text_lines.append(f"📎 **Plus {len(channels) - 8} additional channels** (use detailed management to view all)\n")
        else:
            text_lines.extend([
                "❌ **No mandatory channels configured**\n",
                "🚀 **Get Started:**",
                "• Click **'➕ Add Channel'** to add your first mandatory channel",
                "• Users will be required to join before accessing the bot",
                "• You can manage existing channels and view detailed statistics\n"
            ])
        
        # Add helpful information section
        text_lines.extend([
            "💡 **Quick Actions Available:**",
            "• ➕ Add new channels to the mandatory list",
            "• 📋 Manage existing channels (edit/remove/activate)",
            "• 🔄 Refresh data and view updated statistics",
            "• 🔍 View detailed channel analytics\n",
            "⚠️ **Important:** Changes take effect immediately for new users."
        ])
        
        final_text = "\n".join(text_lines)
        
        # Create enhanced management keyboard with better organization
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard_buttons = []
        
        # Primary action buttons
        if len(channels) == 0:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🚀 Add First Channel", callback_data="admin_add_channel")
            ])
        else:
            keyboard_buttons.append([
                InlineKeyboardButton(text="➕ Add Channel", callback_data="admin_add_channel"),
                InlineKeyboardButton(text="📋 Manage All", callback_data="admin_manage_channels")
            ])
        
        # Management and utility buttons
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="📊 View Analytics", callback_data="admin_channel_analytics")],
            [InlineKeyboardButton(text="⚙️ Channel Settings", callback_data="admin_channel_settings")],
            [InlineKeyboardButton(text="🔄 Refresh Data", callback_data="admin_mandatory_channels")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            final_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        # Log admin action with more details
        await db.log_admin_action(
            user_id, 
            "view_mandatory_channels_enhanced", 
            details=f"Viewed enhanced mandatory channels panel: {len(channels)} total, {len(active_channels)} active, {len(inactive_channels)} inactive"
        )
        
    except Exception as e:
        logger.error(f"Error in admin_mandatory_channels_callback: {e}")
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        await callback.message.edit_text(
            "❌ **Error Loading Mandatory Channels Management**\n\n"
            "🔧 **What happened:**\n"
            "There was an error retrieving mandatory channels data from the database.\n\n"
            "🔨 **Possible solutions:**\n"
            "• Try refreshing the page\n"
            "• Check bot logs for detailed error information\n"
            "• Contact technical support if the issue persists\n\n"
            "⚠️ **Status:** Channel enforcement may still be working normally.",
            reply_markup=keyboard
        )
        await callback.answer("❌ Error loading mandatory channels management", show_alert=True)


@dp.callback_query(F.data.startswith("manage_channel_"))
async def manage_individual_channel_callback(callback: CallbackQuery):
    """Handle mandatory channels button in admin panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Get all mandatory channels
        channels = await db.get_mandatory_channels(active_only=False)
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # Create header
        text_lines = [
            f"📺 **Must Join Channels Management** (Updated at {current_time})\n",
            f"📊 **Statistics:**",
            f"• Total Channels: {len(channels)} channels",
            f"• Active Channels: {len([ch for ch in channels if ch.get('is_active', True)])} channels",
            f"• Inactive Channels: {len([ch for ch in channels if not ch.get('is_active', True)])} channels\n"
        ]
        
        if channels:
            text_lines.append("📋 **Channel List:**\n")
            for i, channel in enumerate(channels[:10], 1):  # Show first 10 channels
                status_emoji = "🟢" if channel.get('is_active', True) else "🔴"
                channel_title = channel.get('channel_title', 'Unknown')
                channel_username = channel.get('channel_username', 'N/A')
                
                # Truncate long titles
                if len(channel_title) > 30:
                    channel_title = channel_title[:27] + "..."
                
                # Import escape function to safely handle markdown characters
                from ui.formatters import escape_markdown
                
                # Safely escape channel data to prevent markdown parsing errors
                safe_channel_title = escape_markdown(channel_title)
                safe_channel_username = escape_markdown(channel_username)
                
                text_lines.append(
                    f"{i}. {status_emoji} **{safe_channel_title}**\n"
                    f"   • Username: @{safe_channel_username}\n"
                    f"   • ID: `{channel.get('channel_id', 'N/A')}`\n"
                )
            
            if len(channels) > 10:
                text_lines.append(f"\n... and {len(channels) - 10} more channels")
        else:
            text_lines.append("❌ **No mandatory channels configured yet.**\n")
            text_lines.append("Use the buttons below to add your first mandatory channel.")
        
        final_text = "\n".join(text_lines)
        
        # Create management keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard_buttons = [
            [InlineKeyboardButton(text="➕ Add Channel", callback_data="admin_add_channel")],
            [InlineKeyboardButton(text="📋 Manage Channels", callback_data="admin_manage_channels")],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_mandatory_channels")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ]
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            final_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        # Log admin action
        await db.log_admin_action(user_id, "view_mandatory_channels", details=f"Viewed mandatory channels panel with {len(channels)} channels")
        
    except Exception as e:
        logger.error(f"Error in admin_mandatory_channels_callback: {e}")
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        await callback.message.edit_text(
            "❌ **Error Loading Mandatory Channels**\n\n"
            "There was an error retrieving mandatory channels data. "
            "Please try again or check the bot logs.",
            reply_markup=keyboard
        )
        await callback.answer("❌ Error loading mandatory channels", show_alert=True)


@dp.callback_query(F.data == "admin_add_channel")
async def admin_add_channel_callback(callback: CallbackQuery, state: FSMContext):
    """Handle add channel button in mandatory channels panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Use the global ChannelStates class defined earlier
    
    await state.set_state(ChannelStates.waiting_for_channel_info)
    
    instructions_text = (
        "➕ **Add Mandatory Channel**\n\n"
        "Please send the channel information in one of these formats:\n\n"
        "**Method 1 - Channel Username:**\n"
        "`@channelUsername`\n\n"
        "**Method 2 - Channel URL:**\n"
        "`https://t.me/channelUsername`\n\n"
        "**Method 3 - Channel ID:**\n"
        "`-1001234567890`\n\n"
        "💡 **Tips:**\n"
        "• Make sure the bot is an admin in the channel\n"
        "• The channel should be public or the bot should have access\n"
        "• You can get channel ID by forwarding a message from the channel\n\n"
        "❌ Send /cancel to cancel"
    )
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_mandatory_channels")]
    ])
    
    await callback.message.edit_text(
        instructions_text,
        reply_markup=keyboard
    )
    await callback.answer()
    
    # Log admin action
    await db.log_admin_action(user_id, "start_add_channel", details="Started adding mandatory channel")


@dp.callback_query(F.data == "admin_remove_channel")
async def admin_remove_channel_callback(callback: CallbackQuery):
    """Handle remove channel button in mandatory channels panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Get all mandatory channels
        channels = await db.get_mandatory_channels(active_only=False)
        
        if not channels:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Add Channel Instead", callback_data="admin_add_channel")],
                [InlineKeyboardButton(text="🔙 Back", callback_data="admin_mandatory_channels")]
            ])
            await callback.message.edit_text(
                "🗑️ **Remove Mandatory Channel**\n\n"
                "❌ No mandatory channels found to remove.\n\n"
                "Add channels first before you can remove them.",
                reply_markup=keyboard
            )
            await callback.answer()
            return
        
        # Create removal interface with channel selection
        text_lines = [
            "🗑️ **Remove Mandatory Channel**\n",
            "⚠️ **Warning:** Removing a channel will immediately stop enforcing membership for that channel.\n",
            "Select a channel to remove:\n"
        ]
        
        # Create inline keyboard with channel removal options
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard_buttons = []
        
        for i, channel in enumerate(channels[:15], 1):  # Limit to 15 channels for UI
            status_emoji = "🟢" if channel.get('is_active', True) else "🔴"
            channel_title = channel.get('channel_title', 'Unknown')
            channel_username = channel.get('channel_username', 'N/A')
            
            # Truncate long titles for buttons
            if len(channel_title) > 25:
                button_title = channel_title[:22] + "..."
            else:
                button_title = channel_title
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"🗑️ {button_title}", 
                    callback_data=f"remove_channel_{channel['channel_id']}"
                )
            ])
            
            # Import escape function to safely handle markdown characters
            from ui.formatters import escape_markdown
            
            # Safely escape channel data to prevent markdown parsing errors
            safe_channel_title = escape_markdown(channel_title)
            safe_channel_username = escape_markdown(channel_username)
            
            text_lines.append(f"{i}. {status_emoji} **{safe_channel_title}** (@{safe_channel_username})")
        
        if len(channels) > 15:
            text_lines.append(f"\n... and {len(channels) - 15} more channels (use database management for full list)")
        
        # Add control buttons
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="❌ Cancel Removal", callback_data="admin_manage_channels")],
            [InlineKeyboardButton(text="🔙 Back to Channels", callback_data="admin_mandatory_channels")]
        ])
        
        final_text = "\n".join(text_lines)
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            final_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        # Log admin action
        await db.log_admin_action(user_id, "start_remove_channel", details=f"Started channel removal process with {len(channels)} channels available")
        
    except Exception as e:
        logger.error(f"Error in admin_remove_channel_callback: {e}")
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="admin_mandatory_channels")]
        ])
        await callback.message.edit_text(
            "❌ **Error Loading Channel Removal**\n\n"
            "There was an error loading the channel removal interface. "
            "Please try again or check the bot logs.",
            reply_markup=keyboard
        )
        await callback.answer("❌ Error loading channel removal", show_alert=True)


@dp.callback_query(F.data == "admin_manage_channels")
async def admin_manage_channels_callback(callback: CallbackQuery):
    """Handle manage channels button in mandatory channels panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Get all mandatory channels
        channels = await db.get_mandatory_channels(active_only=False)
        
        if not channels:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="➕ Add First Channel", callback_data="admin_add_channel")],
                [InlineKeyboardButton(text="🔙 Back", callback_data="admin_mandatory_channels")]
            ])
            await callback.message.edit_text(
                "📋 **Manage Channels**\n\n"
                "❌ No mandatory channels found.\n\n"
                "Add your first mandatory channel to get started.",
                reply_markup=keyboard
            )
            await callback.answer()
            return
        
        # Create management interface
        text_lines = [
            "📋 **Channel Management**\n",
            f"Select a channel to manage:\n"
        ]
        
        # Create inline keyboard with channel management options
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard_buttons = []
        
        for i, channel in enumerate(channels[:15], 1):  # Limit to 15 channels for UI
            status_emoji = "🟢" if channel.get('is_active', True) else "🔴"
            channel_title = channel.get('channel_title', 'Unknown')
            channel_username = channel.get('channel_username', 'N/A')
            
            # Truncate long titles for buttons
            if len(channel_title) > 25:
                button_title = channel_title[:22] + "..."
            else:
                button_title = channel_title
            
            keyboard_buttons.append([
                InlineKeyboardButton(
                    text=f"{status_emoji} {button_title}", 
                    callback_data=f"manage_channel_{channel['channel_id']}"
                )
            ])
            
            # Import escape function to safely handle markdown characters
            from ui.formatters import escape_markdown
            
            # Safely escape channel data to prevent markdown parsing errors
            safe_channel_title = escape_markdown(channel_title)
            safe_channel_username = escape_markdown(channel_username)
            
            text_lines.append(f"{i}. {status_emoji} **{safe_channel_title}** (@{safe_channel_username})")
        
        if len(channels) > 15:
            text_lines.append(f"\n... and {len(channels) - 15} more channels")
        
        # Add control buttons
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="➕ Add New Channel", callback_data="admin_add_channel")],
            [InlineKeyboardButton(text="🗑️ Remove Channel", callback_data="admin_remove_channel")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="admin_mandatory_channels")]
        ])
        
        final_text = "\n".join(text_lines)
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            final_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        # Log admin action
        await db.log_admin_action(user_id, "view_channel_management", details=f"Viewed channel management with {len(channels)} channels")
        
    except Exception as e:
        logger.error(f"Error in admin_manage_channels_callback: {e}")
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back", callback_data="admin_mandatory_channels")]
        ])
        await callback.message.edit_text(
            "❌ **Error Loading Channel Management**\n\n"
            "There was an error loading the channel management interface. "
            "Please try again or check the bot logs.",
            reply_markup=keyboard
        )
        await callback.answer("❌ Error loading channel management", show_alert=True)


@dp.callback_query(F.data == "admin_close")
async def admin_close_callback(callback: CallbackQuery):
    """Handle close admin panel button."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    await callback.message.edit_text("👑 **Admin panel closed.**")
    await callback.answer()


# === CHECK MEMBERSHIP CALLBACK HANDLER ===

@dp.callback_query(F.data == "check_membership")
async def check_membership_callback(callback: CallbackQuery):
    """Handle check membership button press."""
    user_id = callback.from_user.id
    
    try:
        # Get user from database
        user = await db.get_user(user_id)
        if not user:
            await callback.answer("❌ User not found in database", show_alert=True)
            return
        
        # Show checking message
        await callback.answer("🔄 Checking membership...", show_alert=False)
        
        # Check mandatory channel membership for user
        membership_check = await db.check_user_channel_membership(user_id, settings.bot_token)
        
        if membership_check['all_joined']:
            # All channels joined - send success message and main menu
            user_lang = user.language or DEFAULT_LANGUAGE
            
            if user_lang == 'uz':
                success_text = (
                    "✅ **Ajoyib!**\n\n"
                    "Barcha majburiy kanallarga muvaffaqiyatli a'zo bo'ldingiz!\n\n"
                    "Endi botdan to'liq foydalanishingiz mumkin."
                )
            elif user_lang == 'ru':
                success_text = (
                    "✅ **Отлично!**\n\n"
                    "Вы успешно подписались на все обязательные каналы!\n\n"
                    "Теперь вы можете полноценно пользоваться ботом."
                )
            else:
                success_text = (
                    "✅ **Excellent!**\n\n"
                    "You have successfully joined all mandatory channels!\n\n"
                    "You can now use the bot fully."
                )
            
            await callback.message.edit_text(success_text)
            
            # Send main menu after a short delay
            await asyncio.sleep(2)
            
            welcome_text = MessageFormatter.format_welcome_message(
                user.full_name,
                user.is_admin,
                user_lang
            )
            
            await bot.send_message(
                callback.message.chat.id,
                welcome_text,
                reply_markup=get_user_keyboard(user.is_admin, user_lang),
                parse_mode="Markdown"
            )
            await callback.answer()
            
        else:
            # Still missing some channels - update the message
            missing_channels = membership_check['missing_channels']
            user_lang = user.language or DEFAULT_LANGUAGE
            
            if user_lang == 'uz':
                still_missing_text = (
                    "⚠️ **Hali ba'zi kanallarga a'zo bo'lmagansiz**\n\n"
                    f"Qolgan kanallar: {len(missing_channels)} ta\n\n"
                    "Iltimos, barcha kanallarga a'zo bo'ling va qayta tekshiring."
                )
            elif user_lang == 'ru':
                still_missing_text = (
                    "⚠️ **Вы ещё не подписались на некоторые каналы**\n\n"
                    f"Осталось каналов: {len(missing_channels)}\n\n"
                    "Пожалуйста, подпишитесь на все каналы и проверьте снова."
                )
            else:
                still_missing_text = (
                    "⚠️ **You haven't joined some channels yet**\n\n"
                    f"Remaining channels: {len(missing_channels)}\n\n"
                    "Please join all channels and check again."
                )
            
            await callback.message.edit_text(still_missing_text)
            
            # Re-send the channel join requirement after delay
            await asyncio.sleep(2)
            
            # Send the channel join requirement using bot.send_message directly
            await send_channel_join_requirement_direct(
                callback.message.chat.id, missing_channels, user_lang
            )
            await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in check_membership_callback: {e}")
        await callback.answer("❌ Error checking membership. Please try again.", show_alert=True)


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
            
            await validation_msg.edit_text(error_text, parse_mode=None)
            return
        
        # Token is valid, show bot info and confirmation
        bot_name = bot_info.first_name
        bot_username = bot_info.username
        
        # Import escape function to prevent markdown parsing errors
        from ui.formatters import escape_markdown
        
        # Safely escape bot name and username to prevent markdown conflicts
        safe_bot_name = escape_markdown(bot_name) if bot_name else "Unknown"
        safe_bot_username = escape_markdown(bot_username) if bot_username else "Unknown"
        
        confirmation_text = (
            f"✅ **Bot topildi!**\n\n"
            f"🤖 **Nom:** {safe_bot_name}\n"
            f"👤 **Username:** @{safe_bot_username}\n"
            f"🆔 **ID:** `{bot_info.id}`\n\n"
            f"Bu botni yaratishni xohlaysizmi?"
            if user_lang == 'uz' else
            f"✅ **Бот найден!**\n\n"
            f"🤖 **Имя:** {safe_bot_name}\n"
            f"👤 **Username:** @{safe_bot_username}\n"
            f"🆔 **ID:** `{bot_info.id}`\n\n"
            f"Хотите создать этого бота?"
            if user_lang == 'ru' else
            f"✅ **Bot found!**\n\n"
            f"🤖 **Name:** {safe_bot_name}\n"
            f"👤 **Username:** @{safe_bot_username}\n"
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
        await validation_msg.edit_text(error_text, parse_mode=None)


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
            # Import escape function and safely escape bot name and username
            from ui.formatters import escape_markdown
            safe_bot_name = escape_markdown(session_data['bot_name']) if session_data.get('bot_name') else "Unknown"
            safe_bot_username = escape_markdown(session_data['bot_info'].username) if session_data.get('bot_info') and session_data['bot_info'].username else "Unknown"
            
            success_text = (
                f"✅ **Bot muvaffaqiyatli yaratildi!**\n\n"
                f"🤖 **Bot:** {safe_bot_name}\n"
                f"📱 **Username:** @{safe_bot_username}\n"
                f"🚀 **Holat:** Ishlamoqda\n\n"
                f"Botingiz tayyor va foydalanishga ochiq!"
                if user_lang == 'uz' else
                f"✅ **Бот успешно создан!**\n\n"
                f"🤖 **Бот:** {safe_bot_name}\n"
                f"📱 **Username:** @{safe_bot_username}\n"
                f"🚀 **Статус:** Работает\n\n"
                f"Ваш бот готов к использованию!"
                if user_lang == 'ru' else
                f"✅ **Bot created successfully!**\n\n"
                f"🤖 **Bot:** {safe_bot_name}\n"
                f"📱 **Username:** @{safe_bot_username}\n"
                f"🚀 **Status:** Running\n\n"
                f"Your bot is ready to use!"
            )
            
            # Notify admins about new bot (with escaped names to prevent markdown issues)
            safe_user_name = escape_markdown(callback.from_user.full_name) if callback.from_user.full_name else "Unknown"
            safe_username = escape_markdown(callback.from_user.username) if callback.from_user.username else "N/A"
            
            admin_notification = (
                f"🆕 **New Bot Created**\n\n"
                f"👤 **User:** {safe_user_name} (@{safe_username})\n"
                f"🤖 **Bot:** {safe_bot_name}\n"
                f"📱 **Username:** @{safe_bot_username}\n"
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
    
    # Clear session data
    if user_id in user_sessions:
        del user_sessions[user_id]
    
    await state.clear()
    
    user = await db.get_user(user_id)
    user_lang = user.language if user else DEFAULT_LANGUAGE
    
    cancel_text = (
        "❌ **Bot yaratish bekor qilindi.**"
        if user_lang == 'uz' else
        "❌ **Создание бота отменено.**"
        if user_lang == 'ru' else
        "❌ **Bot creation cancelled.**"
    )
    
    await callback.message.edit_text(cancel_text)
    await callback.answer()
    
    # Return to main menu after delay
    await asyncio.sleep(2)
    if user:
        await bot.send_message(
            callback.message.chat.id,
            get_text("back_main_menu", user.language or DEFAULT_LANGUAGE),
            reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
        )


# === USER SEARCH MESSAGE HANDLER ===

# === CHANNEL MANAGEMENT MESSAGE HANDLER ===

class ChannelStates(StatesGroup):
    waiting_for_channel_info = State()

@dp.message(ChannelStates.waiting_for_channel_info)
async def channel_info_received(message: Message, state: FSMContext):
    """Handle channel ID/username input from admin."""
    admin_user = await BotService.update_user(message)
    
    # Check admin permissions
    if not admin_user.is_admin:
        await state.clear()
        await message.answer(
            "❌ **Access Denied**\n\nThis feature requires administrator privileges.",
            reply_markup=get_user_keyboard(admin_user.is_admin, admin_user.language or DEFAULT_LANGUAGE)
        )
        return
    
    # Check for cancel
    if message.text and (message.text.lower() in ['/cancel', 'cancel'] or "cancel" in message.text.lower()):
        await state.clear()
        await message.answer(
            "❌ **Channel Addition Cancelled**",
            reply_markup=get_user_keyboard(admin_user.is_admin, admin_user.language or DEFAULT_LANGUAGE)
        )
        return
    
    if not message.text:
        await message.answer(
            "❌ **Invalid Input**\n\nPlease enter a valid channel ID, username, or URL."
        )
        return
    
    channel_input = message.text.strip()
    
    # Show processing message
    processing_msg = await message.answer("🔍 **Processing channel information...**")
    
    try:
        # Parse channel input
        channel_id = None
        channel_username = None
        channel_url = None
        
        if channel_input.startswith('@'):
            # Username format: @channelname
            channel_username = channel_input[1:]  # Remove @
            channel_url = f"https://t.me/{channel_username}"
            # For username, we'll use a placeholder ID and update later
            channel_id = hash(channel_username) % 1000000  # Generate a temporary ID
            
        elif channel_input.startswith('https://t.me/'):
            # URL format: https://t.me/channelname
            channel_username = channel_input.replace('https://t.me/', '')
            channel_url = channel_input
            # For URL, we'll use a placeholder ID and update later
            channel_id = hash(channel_username) % 1000000  # Generate a temporary ID
            
        elif channel_input.startswith('-') and channel_input[1:].isdigit():
            # Channel ID format: -1001234567890
            channel_id = int(channel_input)
            channel_username = f"channel_{abs(channel_id)}"
            channel_url = f"https://t.me/c/{abs(channel_id)}"
            
        else:
            await processing_msg.edit_text(
                "❌ **Invalid Format**\n\n"
                "Please use one of these formats:\n\n"
                "• `@channelname` (username)\n"
                "• `https://t.me/channelname` (URL)\n"
                "• `-1001234567890` (channel ID)"
            )
            return
        
        # Validate channel with bot (optional - you might want to check if bot can access)
        try:
            # Try to get channel info from Telegram API
            channel_info = await bot.get_chat(channel_id if isinstance(channel_id, int) else f"@{channel_username}")
            
            # Update with real information from Telegram
            if hasattr(channel_info, 'id'):
                channel_id = channel_info.id
            if hasattr(channel_info, 'username') and channel_info.username:
                channel_username = channel_info.username
                channel_url = f"https://t.me/{channel_username}"
            
            channel_title = getattr(channel_info, 'title', channel_username or f"Channel {channel_id}")
            
            # Check if channel already exists
            existing_channel = await db.get_mandatory_channel(channel_id)
            if existing_channel:
                # Import escape function to safely handle markdown characters
                from ui.formatters import escape_markdown
                
                # Safely escape channel data to prevent markdown parsing errors
                safe_existing_title = escape_markdown(existing_channel['channel_title'])
                safe_existing_username = escape_markdown(existing_channel['channel_username'])
                
                await processing_msg.edit_text(
                    f"❌ **Channel Already Exists**\n\n"
                    f"This channel is already in the mandatory channels list:\n\n"
                    f"📺 **{safe_existing_title}**\n"
                    f"🔗 @{safe_existing_username}\n"
                    f"📊 Status: {'✅ Active' if existing_channel.get('is_active', True) else '❌ Inactive'}"
                )
                await state.clear()
                return
            
        except Exception as api_error:
            logger.warning(f"Could not validate channel via API: {api_error}")
            # Continue with user-provided information
            channel_title = channel_username or f"Channel {channel_id}"
        
        # Add channel to database
        result = await db.add_mandatory_channel(
            channel_id=channel_id,
            channel_username=channel_username or "",
            channel_title=channel_title,
            channel_url=channel_url or "",
            added_by=admin_user.user_id
        )
        
        if result:
            # Import escape function to safely handle markdown characters
            from ui.formatters import escape_markdown
            
            # Safely escape channel data to prevent markdown parsing errors
            safe_channel_title = escape_markdown(channel_title)
            safe_channel_username = escape_markdown(channel_username or 'N/A')
            safe_channel_url = escape_markdown(channel_url or 'N/A')
            
            success_text = (
                f"✅ **Channel Added Successfully!**\n\n"
                f"📺 **Title:** {safe_channel_title}\n"
                f"🔗 **Username:** @{safe_channel_username}\n"
                f"🆔 **ID:** `{channel_id}`\n"
                f"🌐 **URL:** {safe_channel_url}\n\n"
                f"The channel has been added to the mandatory channels list and is now active."
            )
            
            # Log admin action
            await db.log_admin_action(
                admin_user.user_id, 
                "add_mandatory_channel", 
                details=f"Added channel {channel_title} (ID: {channel_id})"
            )
            
        else:
            success_text = (
                f"❌ **Error Adding Channel**\n\n"
                f"There was an error adding the channel to the database. "
                f"Please try again or contact support."
            )
        
        await processing_msg.edit_text(success_text)
        await state.clear()
        
        # Return to mandatory channels panel after delay
        await asyncio.sleep(3)
        
        # Create return keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📺 Back to Channels", callback_data="admin_mandatory_channels")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        
        await message.answer(
            "🔄 **Channel management completed.**\n\n"
            "Use the buttons below to continue:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error processing channel information: {e}")
        await processing_msg.edit_text(
            f"❌ **Error Processing Channel**\n\n"
            f"There was an error processing the channel information: {str(e)}\n\n"
            f"Please try again with a different format or contact support."
        )
        await state.clear()

@dp.message(BotExtensionStates.waiting_for_bot_extend)
async def bot_extend_input_received(message: Message, state: FSMContext):
    """Handle bot extension input from admin."""
    admin_user = await BotService.update_user(message)
    
    # Check admin permissions
    if not admin_user.is_admin:
        await state.clear()
        await message.answer(
            "❌ **Access Denied**\n\nThis feature requires administrator privileges.",
            reply_markup=get_user_keyboard(admin_user.is_admin, admin_user.language or DEFAULT_LANGUAGE)
        )
        return
    
    # Check for cancel
    if message.text and (message.text.lower() in ['/cancel', 'cancel'] or "cancel" in message.text.lower()):
        await state.clear()
        await message.answer(
            "❌ **Bot Extension Cancelled**",
            reply_markup=get_user_keyboard(admin_user.is_admin, admin_user.language or DEFAULT_LANGUAGE)
        )
        return
    
    if not message.text:
        await message.answer(
            "❌ **Invalid Input**\n\nPlease enter bot ID and days in format: `bot_id days`"
        )
        return
    
    input_parts = message.text.strip().split()
    
    if len(input_parts) != 2:
        await message.answer(
            "❌ **Invalid Format**\n\n"
            "Please use the format: `bot_id days`\n"
            "Example: `123 30` to extend bot 123 by 30 days"
        )
        return
    
    try:
        bot_id = int(input_parts[0])
        days = int(input_parts[1])
        
        if days <= 0 or days > 365:
            await message.answer(
                "❌ **Invalid Days**\n\n"
                "Days must be between 1 and 365."
            )
            return
        
    except ValueError:
        await message.answer(
            "❌ **Invalid Numbers**\n\n"
            "Bot ID and days must be valid numbers.\n"
            "Example: `123 30`"
        )
        return
    
    # Show processing message
    processing_msg = await message.answer("⏰ **Processing bot extension...**")
    
    try:
        # Check if bot exists
        bot_info = await db.get_user_bot(bot_id)
        if not bot_info:
            await processing_msg.edit_text(
                f"❌ **Bot Not Found**\n\n"
                f"No bot found with ID: `{bot_id}`\n\n"
                f"Please check the bot ID and try again."
            )
            await state.clear()
            return
        
        # Extend bot time
        success = await db.extend_bot_time(bot_id, days)
        
        if success:
            # Get updated bot info
            updated_bot = await db.get_user_bot(bot_id)
            
            from ui.formatters import escape_markdown
            safe_bot_name = escape_markdown(bot_info['bot_name']) if bot_info.get('bot_name') else "Unknown"
            
            # Calculate new expiry date
            new_expiry = "Unknown"
            if updated_bot and updated_bot.get('expires_at'):
                try:
                    expiry_dt = datetime.fromisoformat(updated_bot['expires_at']) if isinstance(updated_bot['expires_at'], str) else updated_bot['expires_at']
                    new_expiry = expiry_dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    new_expiry = "Unknown"
            
            success_text = (
                f"✅ **Bot Time Extended Successfully!**\n\n"
                f"🤖 **Bot:** {safe_bot_name}\n"
                f"🆔 **Bot ID:** `{bot_id}`\n"
                f"📅 **Extended by:** {days} days\n"
                f"⏰ **New Expiry:** {new_expiry}\n\n"
                f"The bot's subscription has been successfully extended."
            )
            
            # Notify bot owner
            try:
                bot_owner_id = bot_info.get('user_id')
                if bot_owner_id:
                    owner = await db.get_user(bot_owner_id)
                    owner_lang = owner.language if owner else DEFAULT_LANGUAGE
                    
                    if owner_lang == 'uz':
                        owner_notification = (
                            f"🎉 **Botingiz vaqti uzaytirildi!**\n\n"
                            f"🤖 **Bot:** {safe_bot_name}\n"
                            f"⏰ **Uzaytirilgan muddat:** {days} kun\n"
                            f"📅 **Yangi muddat:** {new_expiry}\n\n"
                            f"Administrator tomonidan botingiz vaqti uzaytirildi!"
                        )
                    elif owner_lang == 'ru':
                        owner_notification = (
                            f"🎉 **Время вашего бота продлено!**\n\n"
                            f"🤖 **Бот:** {safe_bot_name}\n"
                            f"⏰ **Продлено на:** {days} дней\n"
                            f"📅 **Новый срок:** {new_expiry}\n\n"
                            f"Администратор продлил время вашего бота!"
                        )
                    else:
                        owner_notification = (
                            f"🎉 **Your bot time has been extended!**\n\n"
                            f"🤖 **Bot:** {safe_bot_name}\n"
                            f"⏰ **Extended by:** {days} days\n"
                            f"📅 **New expiry:** {new_expiry}\n\n"
                            f"An administrator has extended your bot's time!"
                        )
                    
                    await bot.send_message(bot_owner_id, owner_notification)
            except Exception as notify_error:
                logger.error(f"Error notifying bot owner: {notify_error}")
            
        else:
            success_text = (
                f"❌ **Error Extending Bot Time**\n\n"
                f"🤖 **Bot ID:** `{bot_id}`\n\n"
                f"There was an error extending the bot's time. "
                f"Please try again or check the bot logs."
            )
        
        await processing_msg.edit_text(success_text)
        await state.clear()
        
        # Log admin action
        await db.log_admin_action(
            admin_user.user_id,
            "extend_bot_time",
            details=f"Extended bot {bot_id} ({bot_info.get('bot_name', 'Unknown')}) by {days} days"
        )
        
        # Return to bot management after delay
        await asyncio.sleep(3)
        
        # Create return keyboard
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🤖 Back to Bot Management", callback_data="admin_bots")],
            [InlineKeyboardButton(text="🔙 Back to Admin Panel", callback_data="admin_back")]
        ])
        
        await message.answer(
            "⏰ **Bot extension completed.**\n\n"
            "Use the buttons below to continue:",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error processing bot extension: {e}")
        await processing_msg.edit_text(
            f"❌ **Error Processing Extension**\n\n"
            f"There was an error processing the bot extension: {str(e)}\n\n"
            f"Please try again or contact support."
        )
        await state.clear()


@dp.message(UserSearchStates.waiting_for_user_input)
async def user_search_input_received(message: Message, state: FSMContext):
    """Handle user search input from admin."""
    admin_user = await BotService.update_user(message)
    
    # Check admin permissions
    if not admin_user.is_admin:
        await state.clear()
        await message.answer(
            "❌ **Access Denied**\n\nThis feature requires administrator privileges.",
            reply_markup=get_user_keyboard(admin_user.is_admin, admin_user.language or DEFAULT_LANGUAGE)
        )
        return
    
    # Check for cancel
    if message.text and (message.text.lower() in ['/cancel', 'cancel'] or "cancel" in message.text.lower()):
        await state.clear()
        await message.answer(
            "❌ **User Search Cancelled**",
            reply_markup=get_user_keyboard(admin_user.is_admin, admin_user.language or DEFAULT_LANGUAGE)
        )
        return
    
    if not message.text:
        await message.answer(
            "❌ **Invalid Input**\n\nPlease enter a valid user ID or username."
        )
        return
    
    search_query = message.text.strip()
    
    # Show searching message
    searching_msg = await message.answer("🔍 **Searching for user...**")
    
    try:
        # Try to parse as user ID first
        search_user = None
        if search_query.isdigit():
            # Search by user ID
            user_id = int(search_query)
            search_user = await db.get_user(user_id)
        else:
            # Search by username
            username = search_query.replace('@', '')  # Remove @ if present
            search_user = await db.get_user_by_username(username)
        
        if not search_user:
            await searching_msg.edit_text(
                f"❌ **User Not Found**\n\n"
                f"No user found with identifier: `{search_query}`\n\n"
                f"**Tips:**\n"
                f"• Make sure the user ID is correct\n"
                f"• Make sure the username exists\n"
                f"• The user must have interacted with the bot at least once"
            )
            await state.clear()
            return
        
        # Get additional user statistics
        user_stats = await db.get_user_statistics(search_user.user_id)
        
        # Format detailed user information
        from ui.formatters import escape_markdown
        
        # Safely escape user data
        safe_first_name = escape_markdown(search_user.first_name) if search_user.first_name else "N/A"
        safe_last_name = escape_markdown(search_user.last_name) if search_user.last_name else "N/A"
        safe_username = escape_markdown(search_user.username) if search_user.username else "N/A"
        safe_language = escape_markdown(search_user.language) if search_user.language else "Not set"
        
        # User status indicators
        status_emoji = "🟢" if search_user.is_active else "⚪"
        if search_user.is_banned:
            status_emoji = "🔴"
        elif search_user.is_admin:
            status_emoji = "👑"
        
        # Format registration and last activity dates
        created_at = search_user.created_at.strftime("%Y-%m-%d %H:%M:%S") if search_user.created_at else "Unknown"
        updated_at = search_user.updated_at.strftime("%Y-%m-%d %H:%M:%S") if search_user.updated_at else "Unknown"
        
        # Create comprehensive user report
        user_info_text = (
            f"👤 **User Profile**\n\n"
            f"{status_emoji} **Status:** {'Admin' if search_user.is_admin else 'Banned' if search_user.is_banned else 'Active' if search_user.is_active else 'Inactive'}\n\n"
            f"**📋 Basic Information:**\n"
            f"• **User ID:** `{search_user.user_id}`\n"
            f"• **First Name:** {safe_first_name}\n"
            f"• **Last Name:** {safe_last_name}\n"
            f"• **Username:** @{safe_username}\n"
            f"• **Language:** {safe_language}\n\n"
            f"**📊 Statistics:**\n"
            f"• **Messages Sent:** {user_stats.get('total_messages', 0)} messages\n"
            f"• **Bot Creations:** {user_stats.get('total_bots', 0)} bots\n"
            f"• **Active Bots:** {user_stats.get('active_bots', 0)} bots\n\n"
            f"**📅 Timeline:**\n"
            f"• **Registered:** {created_at}\n"
            f"• **Last Activity:** {updated_at}\n\n"
            f"**🔧 Account Settings:**\n"
            f"• **Premium Status:** {'✅ Yes' if getattr(search_user, 'effective_premium_status', False) else '❌ No'}\n"
            f"• **Notifications:** {'✅ Enabled' if not getattr(search_user, 'is_banned', False) else '❌ Disabled (Banned)'}\n\n"
            f"**💡 Additional Notes:**\n"
            f"• Total interactions with main bot: {user_stats.get('total_messages', 0)}\n"
            f"• User engagement level: {'High' if user_stats.get('total_messages', 0) > 10 else 'Medium' if user_stats.get('total_messages', 0) > 3 else 'Low'}"
        )
        
        # Create action keyboard for admin
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        action_buttons = []
        
        # Add ban/unban button
        if search_user.is_banned:
            action_buttons.append([
                InlineKeyboardButton(
                    text="✅ Unban User", 
                    callback_data=f"admin_unban_{search_user.user_id}"
                )
            ])
        elif not search_user.is_admin:
            action_buttons.append([
                InlineKeyboardButton(
                    text="🔴 Ban User", 
                    callback_data=f"admin_ban_{search_user.user_id}"
                )
            ])
        
        # Add make admin/remove admin button (only for super admins)
        if admin_user.user_id in settings.get_admin_ids():
            if search_user.is_admin and search_user.user_id not in settings.get_admin_ids():
                action_buttons.append([
                    InlineKeyboardButton(
                        text="👤 Remove Admin", 
                        callback_data=f"admin_demote_{search_user.user_id}"
                    )
                ])
            elif not search_user.is_admin:
                action_buttons.append([
                    InlineKeyboardButton(
                        text="👑 Make Admin", 
                        callback_data=f"admin_promote_{search_user.user_id}"
                    )
                ])
        
        # Add message user button
        action_buttons.append([
            InlineKeyboardButton(
                text="💬 Send Message", 
                callback_data=f"admin_message_{search_user.user_id}"
            )
        ])
        
        # Add back to admin panel button
        action_buttons.append([
            InlineKeyboardButton(
                text="🔙 Back to Admin Panel", 
                callback_data="admin_back"
            )
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=action_buttons)
        
        await searching_msg.edit_text(
            user_info_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
        # Clear state
        await state.clear()
        
        # Log admin action
        await db.log_admin_action(
            admin_user.user_id,
            "user_search_completed",
            target_user_id=search_user.user_id,
            details=f"Searched and viewed profile of user {search_user.user_id} ({search_user.display_name})"
        )
        
    except ValueError:
        await searching_msg.edit_text(
            f"❌ **Invalid User ID**\n\n"
            f"'{search_query}' is not a valid user ID.\n\n"
            f"User IDs must be numbers only."
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Error in user search: {e}")
        await searching_msg.edit_text(
            f"❌ **Search Error**\n\n"
            f"An error occurred while searching for user.\n\n"
            f"Please try again or contact support if the problem persists."
        )
        await state.clear()


# === ERROR HANDLERS ===

@dp.error()
async def global_error_handler(event):
    """Global error handler for unhandled exceptions."""
    exception = event.exception
    update = event.update
    
    logger.error(f"Unhandled bot error: {type(exception).__name__}: {exception}")
    logger.error(f"Update: {update}")
    
    # Try to notify user about the error if possible
    if update and hasattr(update, 'message') and update.message:
        try:
            await update.message.answer(
                "⚠️ **Temporary Error**\n\n"
                "An unexpected error occurred. Please try again or contact support if the problem persists."
            )
        except Exception:
            pass  # If we can't notify user, just log it
    elif update and hasattr(update, 'callback_query') and update.callback_query:
        try:
            await update.callback_query.answer(
                "❌ An error occurred. Please try again.",
                show_alert=True
            )
        except Exception:
            pass
    
    return True  # Mark error as handled


@dp.message()
async def unknown_message_handler(message: Message):
    """Handle unknown messages with helpful response."""
    user = await BotService.update_user(message)
    
    response_text = get_text("unknown_command", user.language or DEFAULT_LANGUAGE)
    
    await message.answer(
        response_text,
        reply_markup=get_user_keyboard(user.is_admin, user.language or DEFAULT_LANGUAGE)
    )


@dp.callback_query(F.data == "admin_bots_refresh")
async def admin_bots_refresh_callback(callback: CallbackQuery):
    """Handle refresh button in admin bots panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    # Show loading message
    await callback.answer("🔄 Refreshing bot management...", show_alert=False)
    
    # Redirect to admin_bots to refresh the panel
    await admin_bots_callback(callback)


@dp.callback_query(F.data == "admin_view_all_bots")
async def admin_view_all_bots_callback(callback: CallbackQuery):
    """Handle view all bots button in admin panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Get all bots from database
        all_bots = await db.get_all_user_bots()
        
        if not all_bots:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Bot Management", callback_data="admin_bots")]
            ])
            await callback.message.edit_text(
                "📋 **All User Bots**\n\n"
                "❌ No user bots found in the database.",
                reply_markup=keyboard
            )
            await callback.answer()
            return
        
        # Limit to first 20 bots to avoid message length issues
        MAX_BOTS_DISPLAY = 20
        display_bots = all_bots[:MAX_BOTS_DISPLAY]
        
        current_time = datetime.now().strftime("%H:%M:%S")
        
        text_lines = [
            f"📋 **All User Bots** (Updated at {current_time})\n",
            f"📊 **Total Bots:** {len(all_bots)} bots\n"
        ]
        
        for i, bot in enumerate(display_bots, 1):
            status_emoji = "✅" if bot.get('status') == 'approved' else "⏳" if bot.get('status') == 'pending' else "❌"
            expiry = bot.get('expires_at', 'N/A')
            if expiry != 'N/A':
                try:
                    expiry_dt = datetime.fromisoformat(expiry) if isinstance(expiry, str) else expiry
                    days_left = (expiry_dt - datetime.now()).days
                    expiry_text = f"{days_left} days" if days_left > 0 else "Expired"
                except:
                    expiry_text = "Unknown"
            else:
                expiry_text = "N/A"
            
            text_lines.append(
                f"{i}. {status_emoji} **{bot.get('bot_name', 'Unknown')}**\n"
                f"   • ID: `{bot.get('id', 'N/A')}`\n"
                f"   • Owner: {bot.get('user_id', 'Unknown')}\n"
                f"   • Status: {bot.get('status', 'Unknown')}\n"
                f"   • Expires: {expiry_text}\n"
            )
        
        if len(all_bots) > MAX_BOTS_DISPLAY:
            text_lines.append(f"\n... and {len(all_bots) - MAX_BOTS_DISPLAY} more bots")
        
        final_text = "\n".join(text_lines)
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_view_all_bots")],
            [InlineKeyboardButton(text="🔙 Back to Bot Management", callback_data="admin_bots")]
        ])
        
        await callback.message.edit_text(
            final_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        # Log admin action
        await db.log_admin_action(user_id, "view_all_bots", details=f"Viewed all {len(all_bots)} user bots")
        
    except Exception as e:
        logger.error(f"Error in admin_view_all_bots_callback: {e}")
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Bot Management", callback_data="admin_bots")]
        ])
        await callback.message.edit_text(
            "❌ **Error Loading Bots**\n\n"
            "There was an error retrieving bot data. "
            "Please try again or check the bot logs.",
            reply_markup=keyboard
        )
        await callback.answer("❌ Error loading bots", show_alert=True)


@dp.callback_query(F.data == "admin_extend_time")
async def admin_extend_time_callback(callback: CallbackQuery, state: FSMContext):
    """Handle extend bot time button in admin panel."""
    user_id = callback.from_user.id
    
    if not await BotService.check_admin(user_id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    try:
        # Get all bots that can be extended
        all_bots = await db.get_all_user_bots()
        
        if not all_bots:
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Bot Management", callback_data="admin_bots")]
            ])
            await callback.message.edit_text(
                "⏰ **Extend Bot Time**\n\n"
                "❌ No user bots found in the database.",
                reply_markup=keyboard
            )
            await callback.answer()
            return
        
        # Show instructions for extending bot time
        text_lines = [
            "⏰ **Extend Bot Time - Admin Panel**\n",
            "To extend a bot's time, please send the bot ID followed by the number of days to extend.\n",
            "**Format:** `bot_id days`",
            "**Example:** `123 30` (extends bot with ID 123 by 30 days)\n",
            "📋 **Available Bots:**\n"
        ]
        
        # Show first 10 bots with their current expiry
        for i, bot in enumerate(all_bots[:10], 1):
            expiry = bot.get('expires_at', 'N/A')
            if expiry != 'N/A':
                try:
                    expiry_dt = datetime.fromisoformat(expiry) if isinstance(expiry, str) else expiry
                    days_left = (expiry_dt - datetime.now()).days
                    expiry_text = f"{days_left} days left" if days_left > 0 else "Expired"
                except:
                    expiry_text = "Unknown"
            else:
                expiry_text = "No expiry set"
            
            text_lines.append(
                f"{i}. **{bot.get('bot_name', 'Unknown')}** (ID: `{bot.get('id', 'N/A')}`) - {expiry_text}"
            )
        
        if len(all_bots) > 10:
            text_lines.append(f"\n... and {len(all_bots) - 10} more bots")
        
        text_lines.append("\n💡 Send the bot ID and days in the format above, or use the buttons below.")
        
        final_text = "\n".join(text_lines)
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_bots")]
        ])
        
        await callback.message.edit_text(
            final_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
        
        # Set state for waiting for bot extend input
        await state.set_state(BotExtensionStates.waiting_for_bot_extend)
        
        # Log admin action
        await db.log_admin_action(user_id, "start_bot_extend", details="Started bot time extension process")
        
    except Exception as e:
        logger.error(f"Error in admin_extend_time_callback: {e}")
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Back to Bot Management", callback_data="admin_bots")]
        ])
        await callback.message.edit_text(
            "❌ **Error Loading Extension Panel**\n\n"
            "There was an error loading the bot extension panel. "
            "Please try again or check the bot logs.",
            reply_markup=keyboard
        )
        await callback.answer("❌ Error loading extension panel", show_alert=True)


@dp.callback_query()
async def unknown_callback_handler(callback: CallbackQuery):
    """Handle unknown callback queries."""
    await callback.answer("❓ Unknown action", show_alert=True)
    logger.warning(f"Unknown callback: {callback.data}")


# === MAIN FUNCTION ===

async def main():
    """Main bot function with enhanced startup and error handling."""
    try:
        # Log startup
        logger.info("Starting Telegram Constructor Bot...")
        logger.info(f"Bot configuration: {settings.bot.name} v{getattr(settings, 'version', '1.0.0')}")
        
        # Initialize database
        await db.initialize()
        logger.info("Database initialized successfully")
        
        # Add initial admins if configured
        admin_ids = settings.get_admin_ids()
        if admin_ids:
            for admin_id in admin_ids:
                admin_user_data = {
                    'user_id': admin_id,
                    'username': f"admin_{admin_id}",
                    'first_name': "Admin",
                    'last_name': "User"
                }
                await db.add_or_update_user(admin_user_data)
            logger.info(f"Added {len(admin_ids)} initial administrators")
        
        # Initialize user bot manager
        try:
            from bot_manager import bot_manager
            await bot_manager.start_all_approved_bots()
            logger.info("User bots initialization completed")
        except Exception as e:
            logger.error(f"Error starting user bots: {e}")
        
        # Set bot commands for better UX
        from aiogram.types import BotCommand, BotCommandScopeDefault
        
        commands = [
            BotCommand(command="start", description="🚀 Start the bot"),
            BotCommand(command="language", description="🌐 Change language"),
            BotCommand(command="admin", description="👑 Admin panel (admins only)"),
            BotCommand(command="cancel", description="❌ Cancel current operation")
        ]
        
        await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
        logger.info("Bot commands set successfully")
        
        # Start polling
        logger.info("Starting bot polling...")
        await dp.start_polling(
            bot,
            skip_updates=True,  # Skip pending updates on startup
            allowed_updates=["message", "callback_query"]  # Only handle messages and callback queries
        )
        
    except Exception as e:
        logger.error(f"Critical error in main function: {e}")
        raise
    finally:
        # Cleanup
        logger.info("Shutting down bot...")
        try:
            await bot.session.close()
            await db.close()
            logger.info("Bot shutdown completed successfully")
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")


if __name__ == "__main__":
    # This should not be called directly - use run.py instead
    logger.warning("bot.py called directly. Use run.py for proper startup.")
    asyncio.run(main())
