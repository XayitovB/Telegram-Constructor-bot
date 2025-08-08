"""
User Bot Template - Dynamic bot generation for user-created bots
This template creates fully functional bots for users with multi-language support.
"""

import asyncio
import aiosqlite
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from core.logging import get_logger

class UserBotTemplate:
    """Template class for creating user bots with standard functionality."""
    
    def __init__(self, bot_token: str, bot_id: int, owner_id: int, bot_name: str):
        self.bot_token = bot_token
        self.bot_id = bot_id
        self.owner_id = owner_id
        self.bot_name = bot_name
        self.logger = get_logger(f"UserBot-{bot_id}")
        
        # Initialize bot and dispatcher
        self.bot = Bot(token=bot_token, parse_mode="HTML")
        self.dp = Dispatcher(storage=MemoryStorage())
        
        # Database path for this bot
        self.db_path = Path(f"user_bots/bot_{bot_id}.db")
        self.db_path.parent.mkdir(exist_ok=True)
        
        # Bot settings
        self.settings = {
            'default_language': 'uz',
            'supported_languages': {'uz': 'O\'zbek', 'ru': 'Русский'},
            'welcome_messages': {
                'uz': f"👋 <b>Salom!</b>\n\n🤖 <b>{bot_name}</b> botiga xush kelibsiz!\n\nTilni tanlang:",
                'ru': f"👋 <b>Привет!</b>\n\n🤖 Добро пожаловать в бота <b>{bot_name}</b>!\n\nВыберите язык:"
            },
            'main_menu_messages': {
                'uz': f"🏠 <b>Bosh menyu</b>\n\n👤 Profil ma'lumotlarini ko'rish\n📊 Statistikalar\n⚙️ Sozlamalar",
                'ru': f"🏠 <b>Главное меню</b>\n\n👤 Просмотр профиля\n📊 Статистика\n⚙️ Настройки"
            },
            'buttons': {
                'uz': {
                    'profile': '👤 Profil',
                    'stats': '📊 Statistika',
                    'settings': '⚙️ Sozlamalar',
                    'help': '❓ Yordam',
                    'support': '📞 Qo\'llab-quvvatlash',
                    'language': '🌐 Til',
                    'back': '⬅️ Orqaga'
                },
                'ru': {
                    'profile': '👤 Профиль',
                    'stats': '📊 Статистика',
                    'settings': '⚙️ Настройки',
                    'help': '❓ Помощь',
                    'support': '📞 Поддержка',
                    'language': '🌐 Язык',
                    'back': '⬅️ Назад'
                }
            }
        }
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup all bot handlers."""
        
        @self.dp.message(CommandStart())
        async def start_handler(message: Message):
            """Handle /start command."""
            await self._update_user(message.from_user)
            
            user_lang = await self._get_user_language(message.from_user.id)
            if not user_lang:
                # Show language selection for new users
                keyboard = self._get_language_keyboard()
                await message.answer(
                    self.settings['welcome_messages']['uz'],
                    reply_markup=keyboard
                )
            else:
                # Show main menu for existing users
                await self._send_main_menu(message, user_lang)
        
        @self.dp.callback_query(F.data.startswith('lang_'))
        async def language_selection(callback: CallbackQuery):
            """Handle language selection."""
            language = callback.data.split('_')[1]
            await self._set_user_language(callback.from_user.id, language)
            
            await callback.message.edit_text(
                self.settings['main_menu_messages'][language],
                reply_markup=self._get_main_keyboard(language)
            )
            await callback.answer(f"✅ Til o'rnatildi!" if language == 'uz' else "✅ Язык установлен!")
        
        @self.dp.message(F.text.in_(['👤 Profil', '👤 Профиль']))
        async def profile_handler(message: Message):
            """Handle profile button."""
            user_lang = await self._get_user_language(message.from_user.id)
            stats = await self._get_user_stats(message.from_user.id)
            
            profile_text = self._format_profile(message.from_user, stats, user_lang)
            await message.answer(profile_text, reply_markup=self._get_main_keyboard(user_lang))
        
        @self.dp.message(F.text.in_(['📊 Statistika', '📊 Статистика']))
        async def stats_handler(message: Message):
            """Handle statistics button."""
            user_lang = await self._get_user_language(message.from_user.id)
            bot_stats = await self._get_bot_stats()
            
            stats_text = self._format_stats(bot_stats, user_lang)
            await message.answer(stats_text, reply_markup=self._get_main_keyboard(user_lang))
        
        @self.dp.message(F.text.in_(['⚙️ Sozlamalar', '⚙️ Настройки']))
        async def settings_handler(message: Message):
            """Handle settings button."""
            user_lang = await self._get_user_language(message.from_user.id)
            
            settings_text = "⚙️ <b>Sozlamalar</b>" if user_lang == 'uz' else "⚙️ <b>Настройки</b>"
            keyboard = self._get_settings_keyboard(user_lang)
            
            await message.answer(settings_text, reply_markup=keyboard)
        
        @self.dp.message(F.text.in_(['❓ Yordam', '❓ Помощь']))
        async def help_handler(message: Message):
            """Handle help button."""
            user_lang = await self._get_user_language(message.from_user.id)
            help_text = self._get_help_text(user_lang)
            
            await message.answer(help_text, reply_markup=self._get_main_keyboard(user_lang))
        
        @self.dp.message(F.text.in_(['📞 Qo\'llab-quvvatlash', '📞 Поддержка']))
        async def support_handler(message: Message):
            """Handle support button."""
            user_lang = await self._get_user_language(message.from_user.id)
            
            support_text = (
                f"📞 <b>Qo'llab-quvvatlash</b>\n\n"
                f"Bot egasi bilan bog'laning: @{await self._get_owner_username()}\n"
                f"Yoki bu botning yaratuvchisiga murojaat qiling."
                if user_lang == 'uz' else
                f"📞 <b>Поддержка</b>\n\n"
                f"Свяжитесь с владельцем бота: @{await self._get_owner_username()}\n"
                f"Или обратитесь к создателю этого бота."
            )
            
            await message.answer(support_text, reply_markup=self._get_main_keyboard(user_lang))
        
        # Add error handler
        @self.dp.error()
        async def error_handler(event):
            """Handle errors."""
            self.logger.error(f"Bot error: {event.exception}")
            return True
    
    async def _init_database(self):
        """Initialize bot database."""
        async with aiosqlite.connect(self.db_path) as db:
            # Users table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    language TEXT DEFAULT 'uz',
                    join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                    message_count INTEGER DEFAULT 0
                )
            """)
            
            # Messages table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    message_type TEXT NOT NULL,
                    message_text TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            
            await db.commit()
    
    async def _update_user(self, user):
        """Update user information in database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, last_activity)
                VALUES (?, ?, ?, ?, ?)
            """, (user.id, user.username, user.first_name, user.last_name, datetime.now()))
            
            await db.execute("""
                UPDATE users SET message_count = message_count + 1 
                WHERE user_id = ?
            """, (user.id,))
            
            await db.commit()
    
    async def _get_user_language(self, user_id: int) -> str:
        """Get user's language preference."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,))
            row = await cursor.fetchone()
            return row[0] if row else None
    
    async def _set_user_language(self, user_id: int, language: str):
        """Set user's language preference."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET language = ? WHERE user_id = ?", 
                (language, user_id)
            )
            await db.commit()
    
    async def _get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT join_date, message_count, last_activity 
                FROM users WHERE user_id = ?
            """, (user_id,))
            row = await cursor.fetchone()
            
            if row:
                return {
                    'join_date': row[0],
                    'message_count': row[1],
                    'last_activity': row[2]
                }
            return {}
    
    async def _get_bot_stats(self) -> Dict[str, Any]:
        """Get bot statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            # Total users
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]
            
            # Today's messages
            cursor = await db.execute("""
                SELECT COUNT(*) FROM messages 
                WHERE date(created_at) = date('now')
            """)
            today_messages = (await cursor.fetchone())[0]
            
            # Total messages
            cursor = await db.execute("SELECT COUNT(*) FROM messages")
            total_messages = (await cursor.fetchone())[0]
            
            return {
                'total_users': total_users,
                'today_messages': today_messages,
                'total_messages': total_messages
            }
    
    async def _get_owner_username(self) -> str:
        """Get bot owner's username."""
        try:
            # This would fetch from main constructor bot database
            # For now, return placeholder
            return "bot_owner"
        except:
            return "bot_owner"
    
    def _get_language_keyboard(self):
        """Get language selection keyboard."""
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        buttons = []
        for lang_code, lang_name in self.settings['supported_languages'].items():
            buttons.append([InlineKeyboardButton(text=lang_name, callback_data=f'lang_{lang_code}')])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def _get_main_keyboard(self, language: str):
        """Get main menu keyboard."""
        from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
        
        buttons_config = self.settings['buttons'][language]
        buttons = [
            [KeyboardButton(text=buttons_config['profile']), KeyboardButton(text=buttons_config['stats'])],
            [KeyboardButton(text=buttons_config['settings']), KeyboardButton(text=buttons_config['help'])],
            [KeyboardButton(text=buttons_config['support'])]
        ]
        
        return ReplyKeyboardMarkup(
            keyboard=buttons,
            resize_keyboard=True,
            one_time_keyboard=False
        )
    
    def _get_settings_keyboard(self, language: str):
        """Get settings keyboard."""
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        lang_text = "🌐 Tilni o'zgartirish" if language == 'uz' else "🌐 Изменить язык"
        
        buttons = [
            [InlineKeyboardButton(text=lang_text, callback_data='change_language')],
        ]
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    def _format_profile(self, user, stats: Dict[str, Any], language: str) -> str:
        """Format user profile information."""
        if language == 'uz':
            unknown_uz = "Noma'lum"
            none_uz = "Yo'q"
            join_date = stats.get('join_date', unknown_uz)[:10] if stats.get('join_date') else unknown_uz
            last_activity = stats.get('last_activity', unknown_uz)[:16] if stats.get('last_activity') else unknown_uz
            return f"""👤 <b>Profil ma'lumotlari</b>

📝 <i>Ism:</i> {user.first_name or unknown_uz}
👤 <i>Username:</i> @{user.username or none_uz}
📅 <i>Qo'shilgan sana:</i> {join_date}
💬 <i>Xabarlar soni:</i> {stats.get('message_count', 0)}
⏰ <i>So'ngi faollik:</i> {last_activity}"""
        else:
            unknown_ru = 'Неизвестно'
            none_ru = 'Нет'
            join_date = stats.get('join_date', unknown_ru)[:10] if stats.get('join_date') else unknown_ru
            last_activity = stats.get('last_activity', unknown_ru)[:16] if stats.get('last_activity') else unknown_ru
            return f"""👤 <b>Информация профиля</b>

📝 <i>Имя:</i> {user.first_name or unknown_ru}
👤 <i>Username:</i> @{user.username or none_ru}
📅 <i>Дата присоединения:</i> {join_date}
💬 <i>Количество сообщений:</i> {stats.get('message_count', 0)}
⏰ <i>Последняя активность:</i> {last_activity}"""
    
    def _format_stats(self, stats: Dict[str, Any], language: str) -> str:
        """Format bot statistics."""
        if language == 'uz':
            return f"""📊 <b>Bot statistikasi</b>

👥 <i>Jami foydalanuvchilar:</i> {stats.get('total_users', 0)}
💬 <i>Bugungi xabarlar:</i> {stats.get('today_messages', 0)}
📈 <i>Jami xabarlar:</i> {stats.get('total_messages', 0)}
🤖 <i>Bot nomi:</i> {self.bot_name}"""
        else:
            return f"""📊 <b>Статистика бота</b>

👥 <i>Всего пользователей:</i> {stats.get('total_users', 0)}
💬 <i>Сообщений сегодня:</i> {stats.get('today_messages', 0)}
📈 <i>Всего сообщений:</i> {stats.get('total_messages', 0)}
🤖 <i>Имя бота:</i> {self.bot_name}"""
    
    def _get_help_text(self, language: str) -> str:
        """Get help text."""
        if language == 'uz':
            return f"""❓ <b>Yordam</b>

🤖 <b>{self.bot_name}</b> botidan foydalanish:

👤 <i>Profil</i> - Shaxsiy ma'lumotlaringizni ko'rish
📊 <i>Statistika</i> - Bot statistikasini ko'rish  
⚙️ <i>Sozlamalar</i> - Bot sozlamalarini o'zgartirish
📞 <i>Qo'llab-quvvatlash</i> - Yordam olish

🔄 Istalgan vaqt /start buyrug'ini yuboring."""
        else:
            return f"""❓ <b>Помощь</b>

🤖 Использование бота <b>{self.bot_name}</b>:

👤 <i>Профиль</i> - Просмотр личной информации
📊 <i>Статистика</i> - Просмотр статистики бота
⚙️ <i>Настройки</i> - Изменение настроек бота
📞 <i>Поддержка</i> - Получить помощь

🔄 Отправьте команду /start в любое время."""
    
    async def _send_main_menu(self, message: Message, language: str):
        """Send main menu to user."""
        await message.answer(
            self.settings['main_menu_messages'][language],
            reply_markup=self._get_main_keyboard(language)
        )
    
    async def start(self):
        """Start the user bot."""
        try:
            await self._init_database()
            self.logger.info(f"Starting user bot {self.bot_name} (ID: {self.bot_id})")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            self.logger.error(f"Error starting user bot {self.bot_id}: {e}")
            raise
    
    async def stop(self):
        """Stop the user bot."""
        try:
            await self.bot.session.close()
            self.logger.info(f"Stopped user bot {self.bot_name} (ID: {self.bot_id})")
        except Exception as e:
            self.logger.error(f"Error stopping user bot {self.bot_id}: {e}")


# Global storage for running user bots
running_bots: Dict[int, UserBotTemplate] = {}


async def create_user_bot(bot_token: str, bot_id: int, owner_id: int, bot_name: str) -> UserBotTemplate:
    """Create and start a new user bot."""
    user_bot = UserBotTemplate(bot_token, bot_id, owner_id, bot_name)
    
    # Start bot in background
    task = asyncio.create_task(user_bot.start())
    
    # Store the running bot
    running_bots[bot_id] = user_bot
    
    return user_bot


async def stop_user_bot(bot_id: int) -> bool:
    """Stop a running user bot."""
    if bot_id in running_bots:
        try:
            await running_bots[bot_id].stop()
            del running_bots[bot_id]
            return True
        except Exception as e:
            logger = get_logger(__name__)
            logger.error(f"Error stopping user bot {bot_id}: {e}")
            return False
    return False


def get_running_bots() -> List[int]:
    """Get list of running bot IDs."""
    return list(running_bots.keys())
