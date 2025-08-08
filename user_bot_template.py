"""
Anonymous Chat Bot Template - Creates anonymous chat bots with admin functionality
"""

import asyncio
import aiosqlite
import random
from datetime import datetime
from typing import Dict, Any, Optional, List
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from core.logging import get_logger

class ChatStates(StatesGroup):
    """Chat states for anonymous chat"""
    waiting_for_partner = State()
    in_chat = State()
    admin_panel = State()
    admin_broadcast = State()


class UserBotTemplate:
    """Anonymous chat bot template with admin functionality"""
    
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
        
        # Active chats storage
        self.active_chats = {}  # {user_id: partner_id}
        self.waiting_users = []  # Queue of users waiting for chat
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup all bot handlers for anonymous chat."""
        
        @self.dp.message(CommandStart())
        async def start_handler(message: Message, state: FSMContext):
            """Handle /start command."""
            await self._update_user(message.from_user)
            await state.clear()
            
            # Welcome message for anonymous chat
            welcome_text = (
                "🎭 <b>Anonim Chat Botiga xush kelibsiz!</b>\n\n"
                "💬 Bu bot orqali boshqa foydalanuvchilar bilan anonim suhbatlashishingiz mumkin.\n\n"
                "🔍 Suhbat boshlash uchun /search buyrug'ini yuboring\n"
                "❌ Suhbatni tugatish uchun /stop buyrug'ini yuboring\n\n"
                "📋 Barcha buyruqlar:\n"
                "/search - Suhbatdosh qidirish\n"
                "/stop - Joriy suhbatni tugatish\n"
                "/next - Keyingi suhbatdoshni qidirish"
            )
            
            keyboard = self._get_main_chat_keyboard()
            await message.answer(welcome_text, reply_markup=keyboard)
        
        @self.dp.message(Command("admin"))
        async def admin_command(message: Message, state: FSMContext):
            """Handle /admin command - only for bot owner."""
            if message.from_user.id != self.owner_id:
                return  # Ignore if not owner
            
            await state.set_state(ChatStates.admin_panel)
            
            admin_text = (
                "👮‍♂️ <b>Admin Panel</b>\n\n"
                "📊 Bot statistikasi:\n"
                f"👥 Jami foydalanuvchilar: {await self._get_total_users()}\n"
                f"💬 Faol suhbatlar: {len(self.active_chats) // 2}\n"
                f"⏳ Kutayotganlar: {len(self.waiting_users)}\n\n"
                "🛠 Admin buyruqlari:\n"
                "/users - Foydalanuvchilar ro'yxati\n"
                "/broadcast - Xabar yuborish\n"
                "/stats - To'liq statistika\n"
                "/exit - Admin paneldan chiqish"
            )
            
            keyboard = self._get_admin_keyboard()
            await message.answer(admin_text, reply_markup=keyboard)
        
        @self.dp.message(Command("search"))
        async def search_partner(message: Message, state: FSMContext):
            """Handle /search command - find chat partner."""
            user_id = message.from_user.id
            
            # Check if already in chat
            if user_id in self.active_chats:
                await message.answer("❌ Siz allaqachon suhbatdasiz! Avval /stop buyrug'ini yuboring.")
                return
            
            # Check if already waiting
            if user_id in self.waiting_users:
                await message.answer("⏳ Siz allaqachon suhbatdosh kutmoqdasiz...")
                return
            
            # Try to find a partner
            if self.waiting_users:
                partner_id = self.waiting_users.pop(0)
                
                # Create chat connection
                self.active_chats[user_id] = partner_id
                self.active_chats[partner_id] = user_id
                
                # Notify both users
                connect_msg = (
                    "✅ <b>Suhbatdosh topildi!</b>\n\n"
                    "💬 Suhbat boshlandi. Xabar yuboring!\n"
                    "❌ Suhbatni tugatish: /stop"
                )
                
                keyboard = self._get_in_chat_keyboard()
                
                await state.set_state(ChatStates.in_chat)
                await message.answer(connect_msg, reply_markup=keyboard)
                
                try:
                    partner_state = FSMContext(
                        bot=self.bot,
                        storage=self.dp.storage,
                        key=self.dp.storage.get_key(
                            bot_id=self.bot.id,
                            chat_id=partner_id,
                            user_id=partner_id
                        )
                    )
                    await partner_state.set_state(ChatStates.in_chat)
                    await self.bot.send_message(partner_id, connect_msg, reply_markup=keyboard)
                except Exception as e:
                    self.logger.error(f"Error notifying partner {partner_id}: {e}")
                    # Clean up connection
                    del self.active_chats[user_id]
                    if partner_id in self.active_chats:
                        del self.active_chats[partner_id]
                    await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
            else:
                # Add to waiting queue
                self.waiting_users.append(user_id)
                await state.set_state(ChatStates.waiting_for_partner)
                
                wait_msg = (
                    "🔍 <b>Suhbatdosh qidirilmoqda...</b>\n\n"
                    "⏳ Iltimos kuting, tez orada suhbatdosh topiladi.\n"
                    "❌ Qidirishni bekor qilish: /stop"
                )
                
                keyboard = self._get_waiting_keyboard()
                await message.answer(wait_msg, reply_markup=keyboard)
        
        @self.dp.message(Command("stop"))
        async def stop_chat(message: Message, state: FSMContext):
            """Handle /stop command - stop current chat."""
            user_id = message.from_user.id
            
            # Check if in waiting queue
            if user_id in self.waiting_users:
                self.waiting_users.remove(user_id)
                await state.clear()
                await message.answer(
                    "✅ Qidiruv bekor qilindi.",
                    reply_markup=self._get_main_chat_keyboard()
                )
                return
            
            # Check if in active chat
            if user_id in self.active_chats:
                partner_id = self.active_chats[user_id]
                
                # Remove chat connection
                del self.active_chats[user_id]
                del self.active_chats[partner_id]
                
                # Notify both users
                stop_msg = "❌ Suhbat tugatildi."
                keyboard = self._get_main_chat_keyboard()
                
                await state.clear()
                await message.answer(stop_msg, reply_markup=keyboard)
                
                try:
                    partner_state = FSMContext(
                        bot=self.bot,
                        storage=self.dp.storage,
                        key=self.dp.storage.get_key(
                            bot_id=self.bot.id,
                            chat_id=partner_id,
                            user_id=partner_id
                        )
                    )
                    await partner_state.clear()
                    await self.bot.send_message(
                        partner_id,
                        "❌ Suhbatdosh suhbatni tark etdi.",
                        reply_markup=keyboard
                    )
                except Exception as e:
                    self.logger.error(f"Error notifying partner {partner_id}: {e}")
            else:
                await message.answer("❌ Siz hozir suhbatda emassiz.")
        
        @self.dp.message(Command("next"))
        async def next_partner(message: Message, state: FSMContext):
            """Handle /next command - find next partner."""
            # First stop current chat if any
            await stop_chat(message, state)
            # Then search for new partner
            await search_partner(message, state)
        
        # Admin panel handlers
        @self.dp.message(Command("users"), ChatStates.admin_panel)
        async def admin_users_list(message: Message, state: FSMContext):
            """Show users list in admin panel."""
            if message.from_user.id != self.owner_id:
                return
            
            users_list = await self._get_users_list()
            await message.answer(users_list)
        
        @self.dp.message(Command("broadcast"), ChatStates.admin_panel)
        async def admin_broadcast_start(message: Message, state: FSMContext):
            """Start broadcast in admin panel."""
            if message.from_user.id != self.owner_id:
                return
            
            await state.set_state(ChatStates.admin_broadcast)
            await message.answer(
                "📢 <b>Xabar yuborish</b>\n\n"
                "Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:\n\n"
                "❌ Bekor qilish: /cancel"
            )
        
        @self.dp.message(ChatStates.admin_broadcast)
        async def admin_broadcast_send(message: Message, state: FSMContext):
            """Send broadcast message."""
            if message.from_user.id != self.owner_id:
                return
            
            if message.text == "/cancel":
                await state.set_state(ChatStates.admin_panel)
                await message.answer("❌ Xabar yuborish bekor qilindi.", reply_markup=self._get_admin_keyboard())
                return
            
            success_count = await self._broadcast_message(message.text)
            await state.set_state(ChatStates.admin_panel)
            await message.answer(
                f"✅ Xabar {success_count} ta foydalanuvchiga yuborildi!",
                reply_markup=self._get_admin_keyboard()
            )
        
        @self.dp.message(Command("stats"), ChatStates.admin_panel)
        async def admin_stats(message: Message, state: FSMContext):
            """Show detailed stats in admin panel."""
            if message.from_user.id != self.owner_id:
                return
            
            stats = await self._get_bot_stats()
            stats_text = (
                "📊 <b>To'liq statistika</b>\n\n"
                f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
                f"💬 Bugungi xabarlar: {stats['today_messages']}\n"
                f"📈 Jami xabarlar: {stats['total_messages']}\n"
                f"🔗 Faol suhbatlar: {len(self.active_chats) // 2}\n"
                f"⏳ Kutayotganlar: {len(self.waiting_users)}"
            )
            await message.answer(stats_text)
        
        @self.dp.message(Command("exit"), ChatStates.admin_panel)
        async def admin_exit(message: Message, state: FSMContext):
            """Exit admin panel."""
            if message.from_user.id != self.owner_id:
                return
            
            await state.clear()
            await message.answer(
                "✅ Admin paneldan chiqdingiz.",
                reply_markup=self._get_main_chat_keyboard()
            )
        
        # Handle regular messages in chat
        @self.dp.message(ChatStates.in_chat)
        async def handle_chat_message(message: Message, state: FSMContext):
            """Forward messages between chat partners."""
            user_id = message.from_user.id
            
            if user_id not in self.active_chats:
                await state.clear()
                await message.answer(
                    "❌ Suhbat topilmadi. Yangi suhbat boshlash uchun /search buyrug'ini yuboring.",
                    reply_markup=self._get_main_chat_keyboard()
                )
                return
            
            partner_id = self.active_chats[user_id]
            
            try:
                # Forward different types of messages
                if message.text:
                    await self.bot.send_message(partner_id, f"👤 <i>Suhbatdosh:</i>\n{message.text}")
                elif message.photo:
                    await self.bot.send_photo(
                        partner_id,
                        message.photo[-1].file_id,
                        caption=f"👤 <i>Suhbatdosh:</i>\n{message.caption or ''}"
                    )
                elif message.video:
                    await self.bot.send_video(
                        partner_id,
                        message.video.file_id,
                        caption=f"👤 <i>Suhbatdosh:</i>\n{message.caption or ''}"
                    )
                elif message.voice:
                    await self.bot.send_voice(partner_id, message.voice.file_id)
                elif message.sticker:
                    await self.bot.send_sticker(partner_id, message.sticker.file_id)
                else:
                    await message.reply("❌ Bu turdagi xabar qo'llab-quvvatlanmaydi.")
                
                # Update message count
                await self._update_message_count(user_id)
                
            except Exception as e:
                self.logger.error(f"Error forwarding message from {user_id} to {partner_id}: {e}")
                await message.reply("❌ Xabar yuborishda xatolik yuz berdi.")
        
        # Handle keyboard buttons
        @self.dp.message(F.text == "🔍 Suhbat qidirish")
        async def search_button_handler(message: Message, state: FSMContext):
            """Handle search button."""
            await search_partner(message, state)
        
        @self.dp.message(F.text == "❓ Yordam")
        async def help_button_handler(message: Message, state: FSMContext):
            """Handle help button."""
            help_text = (
                "🎭 <b>Anonim Chat Bot</b>\n\n"
                "💬 Bu bot orqali boshqa foydalanuvchilar bilan anonim suhbatlashishingiz mumkin.\n\n"
                "<b>Buyruqlar:</b>\n"
                "/start - Botni boshlash\n"
                "/search - Suhbatdosh qidirish\n"
                "/stop - Suhbatni tugatish\n"
                "/next - Keyingi suhbatdosh\n\n"
                "<i>Bot egasi /admin buyrug'i orqali admin panelga kirishi mumkin.</i>"
            )
            await message.answer(help_text)
        
        @self.dp.message(F.text == "❌ Suhbatni tugatish")
        async def stop_button_handler(message: Message, state: FSMContext):
            """Handle stop chat button."""
            await stop_chat(message, state)
        
        @self.dp.message(F.text == "⏭ Keyingi suhbatdosh")
        async def next_button_handler(message: Message, state: FSMContext):
            """Handle next partner button."""
            await next_partner(message, state)
        
        @self.dp.message(F.text == "❌ Qidirishni bekor qilish")
        async def cancel_search_button_handler(message: Message, state: FSMContext):
            """Handle cancel search button."""
            await stop_chat(message, state)
        
        # Admin panel button handlers
        @self.dp.message(F.text == "👥 Foydalanuvchilar", ChatStates.admin_panel)
        async def admin_users_button(message: Message, state: FSMContext):
            """Handle users button in admin panel."""
            await admin_users_list(message, state)
        
        @self.dp.message(F.text == "📊 Statistika", ChatStates.admin_panel)
        async def admin_stats_button(message: Message, state: FSMContext):
            """Handle stats button in admin panel."""
            await admin_stats(message, state)
        
        @self.dp.message(F.text == "📢 Xabar yuborish", ChatStates.admin_panel)
        async def admin_broadcast_button(message: Message, state: FSMContext):
            """Handle broadcast button in admin panel."""
            await admin_broadcast_start(message, state)
        
        @self.dp.message(F.text == "🚪 Admin paneldan chiqish", ChatStates.admin_panel)
        async def admin_exit_button(message: Message, state: FSMContext):
            """Handle exit button in admin panel."""
            await admin_exit(message, state)
        
        # Handle all other messages
        @self.dp.message()
        async def handle_other_messages(message: Message, state: FSMContext):
            """Handle messages outside of chat state."""
            current_state = await state.get_state()
            
            if current_state == ChatStates.waiting_for_partner:
                await message.answer(
                    "⏳ Siz hali suhbatdosh kutmoqdasiz...\n"
                    "❌ Qidirishni bekor qilish: /stop"
                )
            elif current_state == ChatStates.admin_panel:
                await message.answer("❓ Admin panelda mavjud buyruqlardan foydalaning.")
            else:
                keyboard = self._get_main_chat_keyboard()
                await message.answer(
                    "💬 Suhbat boshlash uchun /search buyrug'ini yuboring.",
                    reply_markup=keyboard
                )
        
        # Error handler
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
    
    async def _get_users_list(self) -> str:
        """Get formatted list of all users."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT user_id, username, first_name, last_name, join_date, message_count 
                FROM users 
                ORDER BY join_date DESC
            """)
            rows = await cursor.fetchall()
            
            if not rows:
                return "📭 Hali foydalanuvchilar yo'q"
            
            users_text = "👥 <b>Foydalanuvchilar ro'yxati:</b>\n\n"
            for i, (user_id, username, first_name, last_name, join_date, msg_count) in enumerate(rows, 1):
                name = first_name or "Noma'lum"
                if last_name:
                    name += f" {last_name}"
                username_text = f"@{username}" if username else "username yo'q"
                join_date_text = join_date[:10] if join_date else "noma'lum"
                
                users_text += f"{i}. <b>{name}</b>\n"
                users_text += f"   🆔 ID: <code>{user_id}</code>\n"
                users_text += f"   👤 {username_text}\n"
                users_text += f"   📅 Qo'shilgan: {join_date_text}\n"
                users_text += f"   💬 Xabarlar: {msg_count}\n\n"
            
            users_text += f"<i>Jami: {len(rows)} ta foydalanuvchi</i>"
            return users_text
    
    async def _broadcast_message(self, text: str) -> int:
        """Broadcast message to all users."""
        success_count = 0
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT user_id FROM users")
            user_ids = await cursor.fetchall()
            
            for (user_id,) in user_ids:
                try:
                    await self.bot.send_message(user_id, text, parse_mode="HTML")
                    success_count += 1
                    await asyncio.sleep(0.05)  # Small delay to avoid rate limits
                except Exception as e:
                    self.logger.error(f"Failed to send broadcast to user {user_id}: {e}")
            
        return success_count
    
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
    
    def _get_help_text(self, language: str, user_id: int = None) -> str:
        """Get help text."""
        admin_text_uz = ""
        admin_text_ru = ""
        
        # Add admin commands info if user is owner
        if user_id and user_id == self.owner_id:
            admin_text_uz = """\n\n👮 <b>Admin buyruqlari:</b>\n/users - Foydalanuvchilar ro'yxati\n/broadcast <xabar> - Barcha foydalanuvchilarga xabar yuborish"""
            admin_text_ru = """\n\n👮 <b>Команды администратора:</b>\n/users - Список пользователей\n/broadcast <сообщение> - Отправить сообщение всем пользователям"""
        
        if language == 'uz':
            return f"""❓ <b>Yordam</b>

🤖 <b>{self.bot_name}</b> botidan foydalanish:

👤 <i>Profil</i> - Shaxsiy ma'lumotlaringizni ko'rish
📊 <i>Statistika</i> - Bot statistikasini ko'rish  
⚙️ <i>Sozlamalar</i> - Bot sozlamalarini o'zgartirish
📞 <i>Qo'llab-quvvatlash</i> - Yordam olish

🔄 Istalgan vaqt /start buyrug'ini yuboring.{admin_text_uz}"""
        else:
            return f"""❓ <b>Помощь</b>

🤖 Использование бота <b>{self.bot_name}</b>:

👤 <i>Профиль</i> - Просмотр личной информации
📊 <i>Статистика</i> - Просмотр статистики бота
⚙️ <i>Настройки</i> - Изменение настроек бота
📞 <i>Поддержка</i> - Получить помощь

🔄 Отправьте команду /start в любое время."""
    
    def _get_main_chat_keyboard(self):
        """Get main chat keyboard."""
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔍 Suhbat qidirish")],
                [KeyboardButton(text="❓ Yordam")]
            ],
            resize_keyboard=True
        )
        return keyboard
    
    def _get_in_chat_keyboard(self):
        """Get keyboard for active chat."""
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="❌ Suhbatni tugatish")],
                [KeyboardButton(text="⏭ Keyingi suhbatdosh")]
            ],
            resize_keyboard=True
        )
        return keyboard
    
    def _get_waiting_keyboard(self):
        """Get keyboard for waiting state."""
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="❌ Qidirishni bekor qilish")]
            ],
            resize_keyboard=True
        )
        return keyboard
    
    def _get_admin_keyboard(self):
        """Get admin panel keyboard."""
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="👥 Foydalanuvchilar"), KeyboardButton(text="📊 Statistika")],
                [KeyboardButton(text="📢 Xabar yuborish")],
                [KeyboardButton(text="🚪 Admin paneldan chiqish")]
            ],
            resize_keyboard=True
        )
        return keyboard
    
    async def _get_total_users(self) -> int:
        """Get total number of users."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            return (await cursor.fetchone())[0]
    
    async def _update_message_count(self, user_id: int):
        """Update user's message count."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE users SET message_count = message_count + 1 WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()
    
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
