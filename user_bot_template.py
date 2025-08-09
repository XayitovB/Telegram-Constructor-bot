"""
Professional Anonymous Chat Bot Template
Advanced anonymous communication platform with intelligent matching, safety features, and professional UI
"""

import asyncio
import aiosqlite
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Set
from pathlib import Path
import json
from enum import Enum

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

from core.logging import get_logger

class Gender(Enum):
    MALE = "male"
    FEMALE = "female"
    ANY = "any"

class AgeGroup(Enum):
    TEEN = "13-17"
    YOUNG = "18-25" 
    ADULT = "26-35"
    MATURE = "36-50"
    SENIOR = "50+"
    ANY = "any"

class BotStates(StatesGroup):
    """Enhanced bot states for anonymous chat"""
    main_menu = State()
    profile_setup = State()
    profile_view = State()
    profile_age = State()
    profile_gender = State()
    profile_interests = State()
    settings_menu = State()
    searching = State()
    select_my_gender = State()
    select_partner_gender = State()
    in_chat = State()
    report_reason = State()
    report_details = State()
    admin_panel = State()
    admin_broadcast = State()
    feedback = State()
    support_chat = State()


class UserBotTemplate:
    """Professional Anonymous Chat Bot Template"""
    
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
        
        # Enhanced chat management
        self.active_chats: Dict[int, int] = {}  # {user_id: partner_id}
        self.waiting_users: List[Dict[str, Any]] = []  # List of users waiting with preferences
        self.banned_pairs: Set[tuple] = set()  # Banned user pairs
        self.chat_start_times: Dict[int, datetime] = {}  # Chat start tracking
        self.user_states: Dict[int, str] = {}  # Manual state tracking
        self.user_gender_prefs: Dict[int, Dict[str, str]] = {}  # User gender preferences
        
        # Available interests for matching
        self.interests = [
            "🎵 Music", "🎬 Movies", "📚 Books", "🎮 Gaming", 
            "⚽ Sports", "🍳 Cooking", "✈️ Travel", "📸 Photography",
            "🎨 Art", "💻 Technology", "🌱 Nature", "🏋️ Fitness",
            "📱 Social Media", "🧘 Meditation", "🎭 Theater", "🎯 Goals"
        ]
        
        # Setup handlers
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup all bot handlers for professional user experience."""
        
        @self.dp.message(CommandStart())
        async def start_handler(message: Message, state: FSMContext):
            """Handle /start command with professional welcome."""
            await self._update_user(message.from_user)
            await state.set_state(BotStates.main_menu)
            
            user_lang = await self._get_user_language(message.from_user.id) or 'uz'
            
            # Professional welcome message
            if user_lang == 'uz':
                welcome_text = (
                    f"👋 <b>Assalomu alaykum!</b>\n\n"
                    f"🎭 <b>{self.bot_name}</b> - Anonim Suhbat Boti!\n\n"
                    "✨ <i>Bu bot orqali siz:</i>\n\n"
                    "🔍 Tasodifiy suhbatdosh topa olasiz\n"
                    "💬 To'liq anonim suhbat qila olasiz\n"
                    "🛡️ Xavfsiz muhitda muloqot qila olasiz\n\n"
                    "🎯 Yangi suhbat boshlash uchun \"🔍 Suhbat qidirish\" tugmasini bosing!"
                )
            else:
                welcome_text = (
                    f"👋 <b>Добро пожаловать!</b>\n\n"
                    f"🎭 <b>{self.bot_name}</b> - Анонимный Чат Бот!\n\n"
                    "✨ <i>С помощью этого бота вы можете:</i>\n\n"
                    "🔍 Найти случайного собеседника\n"
                    "💬 Общаться полностью анонимно\n"
                    "🛡️ Общаться в безопасной среде\n\n"
                    "🎯 Нажмите \"🔍 Поиск чата\" чтобы начать новый разговор!"
                )
            
            keyboard = self._get_main_menu_keyboard(user_lang)
            await message.answer(welcome_text, reply_markup=keyboard)
        
        @self.dp.message(Command("admin"))
        async def admin_command(message: Message, state: FSMContext):
            """Handle /admin command - only for bot owner."""
            if message.from_user.id != self.owner_id:
                return  # Ignore if not owner
            
            await state.set_state(BotStates.admin_panel)
            
            admin_text = (
                "👮‍♂️ <b>Admin Panel</b>\n\n"
                "📊 Bot statistikasi:\n"
                f"👥 Jami foydalanuvchilar: {await self._get_total_users()}\n"
                f"💬 Faol suhbatlar: {len(self.active_chats) // 2}\n"
                f"⏳ Kutayotganlar: {len(self.waiting_users)}"
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
            
            # Check if already waiting using helper method
            if any(isinstance(user, dict) and user.get('user_id') == user_id for user in self.waiting_users):
                await message.answer("⏳ Siz allaqachon suhbatdosh kutmoqdasiz...")
                return
            
            # This command is deprecated - redirect to gender-based search
            await message.answer(
                "🔄 Endi suhbat qidirish gender tanlov orqali amalga oshiriladi.\n\n"
                "Iltimos, quyidagi tugmani bosing:"
            )
            
            # Start gender selection
            await self._start_gender_selection(message, state)
        
        @self.dp.message(Command("stop"))
        async def stop_chat(message: Message, state: FSMContext):
            """Handle /stop command - stop current chat."""
            user_id = message.from_user.id
            action_taken = False
            
            # Check if in waiting queue using new helper method
            if any(isinstance(user, dict) and user.get('user_id') == user_id for user in self.waiting_users):
                self._remove_user_from_waiting(user_id)
                await state.clear()
                self.user_states.pop(user_id, None)
                await message.answer(
                    "✅ Qidiruv bekor qilindi.",
                    reply_markup=self._get_main_chat_keyboard()
                )
                self.logger.info(f"User {user_id} cancelled search")
                action_taken = True
            
            # Check if in active chat
            if user_id in self.active_chats:
                partner_id = self.active_chats.get(user_id)
                
                # Remove chat connections
                self.active_chats.pop(user_id, None)
                if partner_id:
                    self.active_chats.pop(partner_id, None)
                
                # Clear states
                self.user_states.pop(user_id, None)
                if partner_id:
                    self.user_states.pop(partner_id, None)
                
                # Notify current user
                stop_msg = "❌ Suhbat tugatildi."
                keyboard = self._get_main_chat_keyboard()
                await state.clear()
                await message.answer(stop_msg, reply_markup=keyboard)
                
                # Notify partner if exists
                if partner_id:
                    try:
                        await self.bot.send_message(
                            partner_id,
                            "❌ Suhbatdosh suhbatni tark etdi.",
                            reply_markup=keyboard
                        )
                        self.logger.info(f"Chat ended between {user_id} and {partner_id}")
                        
                        # Log chat end
                        await self._log_message(user_id, "chat_end", f"Ended chat with {partner_id}")
                        await self._log_message(partner_id, "chat_end", f"Partner {user_id} left chat")
                        
                    except Exception as e:
                        self.logger.error(f"Error notifying partner {partner_id}: {e}")
                else:
                    self.logger.info(f"Cleaned up orphaned chat state for user {user_id}")
                
                action_taken = True
            
            # If no specific action was taken, still clean up state and provide guidance
            if not action_taken:
                await state.clear()
                self.user_states.pop(user_id, None)
                # Remove from any remaining queues just in case
                self._remove_user_from_waiting(user_id)
                
                await message.answer(
                    "✅ Barcha holatlar tozalandi.\n\n"
                    "💬 Yangi suhbat boshlash uchun /search buyrug'ini yuboring.",
                    reply_markup=self._get_main_chat_keyboard()
                )
                self.logger.info(f"Force cleaned all states for user {user_id}")
        
        @self.dp.message(Command("next"))
        async def next_partner(message: Message, state: FSMContext):
            """Handle /next command - find next partner."""
            # First stop current chat if any
            await stop_chat(message, state)
            # Then search for new partner
            await search_partner(message, state)
        
        # Admin panel handlers
        @self.dp.message(Command("users"), BotStates.admin_panel)
        async def admin_users_list(message: Message, state: FSMContext):
            """Show users list in admin panel."""
            if message.from_user.id != self.owner_id:
                return
            
            users_list = await self._get_users_list()
            await message.answer(users_list)
        
        @self.dp.message(Command("broadcast"), BotStates.admin_panel)
        async def admin_broadcast_start(message: Message, state: FSMContext):
            """Start broadcast in admin panel."""
            if message.from_user.id != self.owner_id:
                return
            
            await state.set_state(BotStates.admin_broadcast)
            await message.answer(
                "📢 <b>Xabar yuborish</b>\n\n"
                "Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:\n\n"
                "❌ Bekor qilish: /cancel"
            )
        
        @self.dp.message(BotStates.admin_broadcast)
        async def admin_broadcast_send(message: Message, state: FSMContext):
            """Send broadcast message."""
            if message.from_user.id != self.owner_id:
                return
            
            if message.text == "/cancel":
                await state.set_state(BotStates.admin_panel)
                
                cancel_text = "❌ Xabar yuborish bekor qilindi."
                keyboard = self._get_admin_keyboard()
                await message.answer(cancel_text, reply_markup=keyboard)
                return
            
            success_count = await self._broadcast_message(message.text)
            await state.set_state(BotStates.admin_panel)
            
            success_text = f"✅ Xabar {success_count} ta foydalanuvchiga yuborildi!"
            keyboard = self._get_admin_keyboard()
            await message.answer(success_text, reply_markup=keyboard)
        
        @self.dp.message(Command("stats"), BotStates.admin_panel)
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
        
        @self.dp.message(Command("exit"), BotStates.admin_panel)
        async def admin_exit(message: Message, state: FSMContext):
            """Exit admin panel."""
            if message.from_user.id != self.owner_id:
                return
            
            await state.clear()
            await message.answer(
                "✅ Admin paneldan chiqdingiz.",
                reply_markup=self._get_main_chat_keyboard()
            )
        
        # Inline Button Handlers
        @self.dp.callback_query(F.data == "start_search")
        async def search_callback_handler(callback: CallbackQuery, state: FSMContext):
            """Handle search chat inline button - start with gender selection."""
            user_id = callback.from_user.id
            user_lang = await self._get_user_language(user_id) or 'uz'
            
            # Check if already in chat
            if user_id in self.active_chats:
                await callback.answer("❌ Siz allaqachon suhbatdasiz! Avval /stop buyrug'ini yuboring.", show_alert=True)
                return
            
            # Check if already waiting - remove from waiting list first
            self._remove_user_from_waiting(user_id)
            
            await state.set_state(BotStates.select_my_gender)
            
            if user_lang == 'uz':
                gender_text = (
                    "🤖 <b>Sizning jinsingiz</b>\n\n"
                    "Iltimos, o'zingizning jinsini tanlang:"
                )
            else:
                gender_text = (
                    "🤖 <b>Ваш пол</b>\n\n"
                    "Пожалуйста, выберите свой пол:"
                )
            
            keyboard = self._get_my_gender_keyboard(user_lang)
            
            # Edit the current message instead of sending a new one
            try:
                await callback.message.edit_text(gender_text, reply_markup=keyboard)
            except Exception as e:
                # If edit fails, send a new message
                await callback.message.answer(gender_text, reply_markup=keyboard)
            
            await callback.answer()
        
        @self.dp.callback_query(F.data == "show_help")
        async def help_callback_handler(callback: CallbackQuery, state: FSMContext):
            """Handle help inline button."""
            await callback.answer()
            user_lang = await self._get_user_language(callback.from_user.id) or 'uz'
            help_text = self._get_help_text(user_lang, callback.from_user.id)
            await callback.message.edit_text(help_text, reply_markup=self._get_back_inline_keyboard(user_lang))
        
        @self.dp.callback_query(F.data == "show_stats")
        async def stats_callback_handler(callback: CallbackQuery, state: FSMContext):
            """Handle stats inline button."""
            await callback.answer()
            user_lang = await self._get_user_language(callback.from_user.id) or 'uz'
            stats = await self._get_bot_stats()
            stats_text = self._format_stats(stats, user_lang)
            await callback.message.edit_text(stats_text, reply_markup=self._get_back_inline_keyboard(user_lang))
        
        @self.dp.callback_query(F.data == "back_to_main")
        async def back_to_main_callback_handler(callback: CallbackQuery, state: FSMContext):
            """Handle back to main menu inline button."""
            await callback.answer()
            user_lang = await self._get_user_language(callback.from_user.id) or 'uz'
            
            if user_lang == 'uz':
                welcome_text = (
                    f"👋 <b>Assalomu alaykum!</b>\n\n"
                    f"🎭 <b>{self.bot_name}</b> - Anonim Suhbat Boti!\n\n"
                    "✨ <i>Bu bot orqali siz:</i>\n\n"
                    "🔍 Tasodifiy suhbatdosh topa olasiz\n"
                    "💬 To'liq anonim suhbat qila olasiz\n"
                    "🛡️ Xavfsiz muhitda muloqot qila olasiz\n\n"
                    "🎯 Yangi suhbat boshlash uchun \"🔍 Suhbat qidirish\" tugmasini bosing!"
                )
            else:
                welcome_text = (
                    f"👋 <b>Добро пожаловать!</b>\n\n"
                    f"🎭 <b>{self.bot_name}</b> - Анонимный Чат Бот!\n\n"
                    "✨ <i>С помощью этого бота вы можете:</i>\n\n"
                    "🔍 Найти случайного собеседника\n"
                    "💬 Общаться полностью анонимно\n"
                    "🛡️ Общаться в безопасной среде\n\n"
                    "🎯 Нажмите \"🔍 Поиск чата\" чтобы начать новый разговор!"
                )
            
            keyboard = self._get_main_menu_keyboard(user_lang)
            await callback.message.edit_text(welcome_text, reply_markup=keyboard)
        
        @self.dp.message(F.text == "❌ Suhbatni tugatish")
        async def stop_button_handler(message: Message, state: FSMContext):
            """Handle stop chat button."""
            await self._force_stop_everything(message, state)
        
        @self.dp.message(F.text == "⏭ Keyingi suhbatdosh")
        async def next_button_handler(message: Message, state: FSMContext):
            """Handle next partner button."""
            await next_partner(message, state)
        
        @self.dp.message(F.text == "❌ Qidirishni bekor qilish")
        async def cancel_search_button_handler(message: Message, state: FSMContext):
            """Handle cancel search button."""
            await self._force_stop_everything(message, state)
        
        # Gender selection callback handlers
        @self.dp.callback_query(F.data.startswith('gender_my_'), BotStates.select_my_gender)
        async def my_gender_selected(callback: CallbackQuery, state: FSMContext):
            """Handle user's own gender selection via inline callback."""
            user_id = callback.from_user.id
            user_lang = await self._get_user_language(user_id) or 'uz'
            
            # Extract gender from callback data
            selected_gender = callback.data.replace('gender_my_', '')
            
            # Store user's gender preference
            if user_id not in self.user_gender_prefs:
                self.user_gender_prefs[user_id] = {}
            self.user_gender_prefs[user_id]['my_gender'] = selected_gender
            
            # Move to partner gender selection
            await state.set_state(BotStates.select_partner_gender)
            
            if user_lang == 'uz':
                partner_text = (
                    "👥 <b>Suhbatdosh jinsi</b>\n\n"
                    "Qaysi jinsli suhbatdosh bilan gaplashishni xohlaysiz?"
                )
            else:
                partner_text = (
                    "👥 <b>Пол собеседника</b>\n\n"
                    "С каким полом собеседника хотите общаться?"
                )
            
            keyboard = self._get_partner_gender_keyboard(user_lang)
            await callback.message.edit_text(partner_text, reply_markup=keyboard)
            await callback.answer()
        
        @self.dp.callback_query(F.data.startswith('gender_partner_'), BotStates.select_partner_gender)
        async def partner_gender_selected(callback: CallbackQuery, state: FSMContext):
            """Handle partner gender selection and start matching via inline callback."""
            user_id = callback.from_user.id
            
            # Extract partner gender preference from callback data
            selected_partner_gender = callback.data.replace('gender_partner_', '')
            
            # Store partner gender preference
            if user_id not in self.user_gender_prefs:
                self.user_gender_prefs[user_id] = {}
            self.user_gender_prefs[user_id]['partner_gender'] = selected_partner_gender
            
            # Clear the inline keyboard
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.answer()
            
            # Now start the actual partner search with gender preferences
            await self._search_partner_with_gender_callback(callback, state)
        
        # Handle regular messages in chat (AFTER button handlers) - using manual tracking
        # Remove this handler since we'll use manual tracking in handle_other_messages
        
        # Admin panel inline button handlers
        @self.dp.callback_query(F.data == "admin_users")
        async def admin_users_callback(callback: CallbackQuery, state: FSMContext):
            """Handle users inline button in admin panel."""
            if callback.from_user.id != self.owner_id:
                await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
                return
            
            await callback.answer()
            users_list = await self._get_users_list()
            
            # Create back button for users list
            back_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Admin panelga qaytish", callback_data="back_to_admin")]
                ]
            )
            
            try:
                await callback.message.edit_text(users_list, reply_markup=back_keyboard)
            except Exception:
                await callback.message.answer(users_list, reply_markup=back_keyboard)
        
        @self.dp.callback_query(F.data == "admin_stats")
        async def admin_stats_callback(callback: CallbackQuery, state: FSMContext):
            """Handle stats inline button in admin panel."""
            if callback.from_user.id != self.owner_id:
                await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
                return
            
            await callback.answer()
            stats = await self._get_bot_stats()
            stats_text = (
                "📊 <b>To'liq statistika</b>\n\n"
                f"👥 Jami foydalanuvchilar: {stats['total_users']}\n"
                f"💬 Bugungi xabarlar: {stats['today_messages']}\n"
                f"📈 Jami xabarlar: {stats['total_messages']}\n"
                f"🔗 Faol suhbatlar: {len(self.active_chats) // 2}\n"
                f"⏳ Kutayotganlar: {len(self.waiting_users)}"
            )
            
            # Create back button for stats
            back_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Admin panelga qaytish", callback_data="back_to_admin")]
                ]
            )
            
            try:
                await callback.message.edit_text(stats_text, reply_markup=back_keyboard)
            except Exception:
                await callback.message.answer(stats_text, reply_markup=back_keyboard)
        
        @self.dp.callback_query(F.data == "admin_broadcast")
        async def admin_broadcast_callback(callback: CallbackQuery, state: FSMContext):
            """Handle broadcast inline button in admin panel."""
            if callback.from_user.id != self.owner_id:
                await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
                return
            
            await callback.answer()
            await state.set_state(BotStates.admin_broadcast)
            
            broadcast_text = (
                "📢 <b>Xabar yuborish</b>\n\n"
                "Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:\n\n"
                "❌ Bekor qilish uchun /cancel yuboring"
            )
            
            # Create cancel button for broadcast
            cancel_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_broadcast_cancel")]
                ]
            )
            
            try:
                await callback.message.edit_text(broadcast_text, reply_markup=cancel_keyboard)
            except Exception:
                await callback.message.answer(broadcast_text, reply_markup=cancel_keyboard)
        
        @self.dp.callback_query(F.data == "admin_broadcast_cancel")
        async def admin_broadcast_cancel_callback(callback: CallbackQuery, state: FSMContext):
            """Handle broadcast cancel inline button."""
            if callback.from_user.id != self.owner_id:
                await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
                return
            
            await callback.answer()
            await state.set_state(BotStates.admin_panel)
            
            # Return to admin panel
            await self._show_admin_panel(callback, state)
        
        @self.dp.callback_query(F.data == "admin_refresh")
        async def admin_refresh_callback(callback: CallbackQuery, state: FSMContext):
            """Handle refresh inline button in admin panel."""
            if callback.from_user.id != self.owner_id:
                await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
                return
            
            await callback.answer("🔄 Ma'lumotlar yangilandi!")
            await self._show_admin_panel(callback, state)
        
        @self.dp.callback_query(F.data == "admin_exit")
        async def admin_exit_callback(callback: CallbackQuery, state: FSMContext):
            """Handle exit inline button in admin panel."""
            if callback.from_user.id != self.owner_id:
                await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
                return
            
            await callback.answer()
            await state.clear()
            
            exit_text = "✅ Admin paneldan chiqdingiz."
            keyboard = self._get_main_chat_keyboard()
            
            try:
                await callback.message.edit_text(exit_text, reply_markup=keyboard)
            except Exception:
                await callback.message.answer(exit_text, reply_markup=keyboard)
        
        @self.dp.callback_query(F.data == "back_to_admin")
        async def back_to_admin_callback(callback: CallbackQuery, state: FSMContext):
            """Handle back to admin panel inline button."""
            if callback.from_user.id != self.owner_id:
                await callback.answer("❌ Ruxsat yo'q!", show_alert=True)
                return
            
            await callback.answer()
            await state.set_state(BotStates.admin_panel)
            await self._show_admin_panel(callback, state)
        
        # Handle all other messages
        @self.dp.message()
        async def handle_other_messages(message: Message, state: FSMContext):
            """Handle messages outside of chat state."""
            user_id = message.from_user.id
            current_state = await state.get_state()
            
            # Check if user is in chat based on our manual tracking
            if user_id in self.active_chats:
                # User is in chat, forward the message
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
                    
                    # Set FSM state to support_chat (used for both chat and waiting)
                    if current_state != BotStates.support_chat:
                        await state.set_state(BotStates.support_chat)
                    
                except Exception as e:
                    self.logger.error(f"Error forwarding message from {user_id} to {partner_id}: {e}")
                    await message.reply("❌ Xabar yuborishda xatolik yuz berdi.")
                
                return
            
            # Normal state handling for users not in chat
            # Check manual states for waiting
            if self.user_states.get(user_id) == 'waiting_for_partner':
                await message.answer(
                    "⏳ Siz hali suhbatdosh kutmoqdasiz..."
                )
            elif current_state == BotStates.admin_panel:
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
        
        # Define supported languages for user bots
        supported_languages = {
            'uz': '🇺🇿 O\'zbek',
            'ru': '🇷🇺 Русский',
            'en': '🇺🇸 English'
        }
        
        buttons = []
        for lang_code, lang_name in supported_languages.items():
            buttons.append([InlineKeyboardButton(text=lang_name, callback_data=f'lang_{lang_code}')])
        
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    
    
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
        """Get main chat keyboard with inline buttons."""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔍 Suhbat qidirish", callback_data="start_search")],
                [InlineKeyboardButton(text="❓ Yordam", callback_data="show_help"),
                 InlineKeyboardButton(text="📊 Statistika", callback_data="show_stats")]
            ]
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
        """Get admin panel inline keyboard."""
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin_users"),
                 InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
                [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data="admin_broadcast")],
                [InlineKeyboardButton(text="🔄 Yangilash", callback_data="admin_refresh")],
                [InlineKeyboardButton(text="🚪 Admin paneldan chiqish", callback_data="admin_exit")]
            ]
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
    
    async def _log_message(self, user_id: int, message_type: str, message_text: str = ""):
        """Log a message to the database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "INSERT INTO messages (user_id, message_type, message_text) VALUES (?, ?, ?)",
                    (user_id, message_type, message_text[:500])  # Limit message length
                )
                await db.commit()
        except Exception as e:
            self.logger.error(f"Error logging message for user {user_id}: {e}")
    
    # Professional Handler Methods
    async def _handle_profile_view(self, message: Message, state: FSMContext):
        """Handle profile view."""
        await state.set_state(BotStates.profile_view)
        user_lang = await self._get_user_language(message.from_user.id) or 'uz'
        user_stats = await self._get_user_stats(message.from_user.id)
        
        profile_text = self._format_profile(message.from_user, user_stats, user_lang)
        keyboard = self._get_back_keyboard(user_lang)
        
        await message.answer(profile_text, reply_markup=keyboard)
    
    async def _handle_stats_view(self, message: Message, state: FSMContext):
        """Handle statistics view."""
        user_lang = await self._get_user_language(message.from_user.id) or 'uz'
        stats = await self._get_bot_stats()
        
        stats_text = self._format_stats(stats, user_lang)
        keyboard = self._get_back_keyboard(user_lang)
        
        await message.answer(stats_text, reply_markup=keyboard)
    
    async def _handle_settings_menu(self, message: Message, state: FSMContext):
        """Handle settings menu."""
        await state.set_state(BotStates.settings_menu)
        user_lang = await self._get_user_language(message.from_user.id) or 'uz'
        
        if user_lang == 'uz':
            settings_text = "⚙️ <b>Sozlamalar</b>\n\nTil va boshqa sozlamalarni o'zgartiring:"
        else:
            settings_text = "⚙️ <b>Настройки</b>\n\nИзменить язык и другие настройки:"
        
        keyboard = self._get_settings_keyboard(user_lang)
        await message.answer(settings_text, reply_markup=keyboard)
    
    async def _handle_support_chat(self, message: Message, state: FSMContext):
        """Handle support chat."""
        await state.set_state(BotStates.support_chat)
        user_lang = await self._get_user_language(message.from_user.id) or 'uz'
        
        if user_lang == 'uz':
            support_text = (
                "📞 <b>Qo'llab-quvvatlash</b>\n\n"
                "💬 Savolingizni yuboring, tez orada javob beramiz!\n\n"
                "⏰ <i>Ish vaqti:</i> 24/7\n"
                "📧 <i>Email:</i> support@example.com"
            )
        else:
            support_text = (
                "📞 <b>Поддержка</b>\n\n"
                "💬 Отправьте ваш вопрос, мы скоро ответим!\n\n"
                "⏰ <i>Время работы:</i> 24/7\n"
                "📧 <i>Email:</i> support@example.com"
            )
        
        keyboard = self._get_back_keyboard(user_lang)
        await message.answer(support_text, reply_markup=keyboard)
    
    def _get_main_menu_keyboard(self, language: str = 'uz'):
        """Get main menu keyboard with inline buttons based on language."""
        if language == 'uz':
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔍 Suhbat qidirish", callback_data="start_search")],
                    [InlineKeyboardButton(text="❓ Yordam", callback_data="show_help"),
                     InlineKeyboardButton(text="📊 Statistika", callback_data="show_stats")]
                ]
            )
        else:  # Russian
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔍 Поиск чата", callback_data="start_search")],
                    [InlineKeyboardButton(text="❓ Помощь", callback_data="show_help"),
                     InlineKeyboardButton(text="📊 Статистика", callback_data="show_stats")]
                ]
            )
        return keyboard
    
    def _get_back_keyboard(self, language: str = 'uz'):
        """Get back button keyboard."""
        if language == 'uz':
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🔙 Orqaga")]
                ],
                resize_keyboard=True
            )
        else:
            keyboard = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="🔙 Назад")]
                ],
                resize_keyboard=True
            )
        return keyboard
    
    def _get_back_inline_keyboard(self, language: str = 'uz'):
        """Get back button inline keyboard."""
        if language == 'uz':
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Bosh menuga qaytish", callback_data="back_to_main")]
                ]
            )
        else:
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Вернуться в главное меню", callback_data="back_to_main")]
                ]
            )
        return keyboard

    # Gender Selection Methods
    async def _start_gender_selection(self, message: Message, state: FSMContext):
        """Start gender selection process."""
        user_id = message.from_user.id
        user_lang = await self._get_user_language(user_id) or 'uz'
        
        # Check if already in chat
        if user_id in self.active_chats:
            await message.answer("❌ Siz allaqachon suhbatdasiz! Avval /stop buyrug'ini yuboring.")
            return
        
        # Check if already waiting - remove from waiting list first
        self._remove_user_from_waiting(user_id)
        
        await state.set_state(BotStates.select_my_gender)
        
        if user_lang == 'uz':
            gender_text = (
                "🤖 <b>Sizning jinsingiz</b>\n\n"
                "Iltimos, o'zingizning jinsini tanlang:"
            )
        else:
            gender_text = (
                "🤖 <b>Ваш пол</b>\n\n"
                "Пожалуйста, выберите свой пол:"
            )
        
        keyboard = self._get_my_gender_keyboard(user_lang)
        await message.answer(gender_text, reply_markup=keyboard)
    
    async def _search_partner_with_gender(self, message: Message, state: FSMContext):
        """Search for partner with gender preferences."""
        user_id = message.from_user.id
        user_prefs = self.user_gender_prefs.get(user_id, {})
        my_gender = user_prefs.get('my_gender', 'not_specified')
        wanted_gender = user_prefs.get('partner_gender', 'any')
        
        # Find matching partner
        matching_partner = None
        for waiting_user in self.waiting_users.copy():
            partner_id = waiting_user['user_id']
            partner_gender = waiting_user.get('my_gender', 'not_specified')
            partner_wants = waiting_user.get('partner_gender', 'any')
            
            # Skip self
            if partner_id == user_id:
                continue
            
            # Check if genders match preferences
            my_gender_matches = (wanted_gender == 'any' or partner_gender == wanted_gender)
            partner_gender_matches = (partner_wants == 'any' or my_gender == partner_wants)
            
            if my_gender_matches and partner_gender_matches:
                matching_partner = waiting_user
                break
        
        if matching_partner:
            partner_id = matching_partner['user_id']
            
            # Remove partner from waiting list
            self.waiting_users.remove(matching_partner)
            
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
            
            # Set states for both users
            await state.set_state(BotStates.support_chat)
            self.user_states[user_id] = 'in_chat'
            self.user_states[partner_id] = 'in_chat'
            
            await message.answer(connect_msg, reply_markup=keyboard)
            
            # Notify partner
            try:
                await self.bot.send_message(partner_id, connect_msg, reply_markup=keyboard)
                self.logger.info(f"Gender-based chat connection established between {user_id} and {partner_id}")
                
                # Log chat start
                await self._log_message(user_id, "chat_start", f"Started gender-matched chat with {partner_id}")
                await self._log_message(partner_id, "chat_start", f"Started gender-matched chat with {user_id}")
                
            except Exception as e:
                self.logger.error(f"Error notifying partner {partner_id}: {e}")
                # Clean up connection on error
                self.active_chats.pop(user_id, None)
                self.active_chats.pop(partner_id, None)
                await message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
                # Return partner to waiting queue
                self.waiting_users.append(matching_partner)
        else:
            # No matching partner found, add to waiting queue
            user_waiting_data = {
                'user_id': user_id,
                'my_gender': my_gender,
                'partner_gender': wanted_gender,
                'timestamp': datetime.now()
            }
            
            self.waiting_users.append(user_waiting_data)
            await state.set_state(BotStates.support_chat)
            self.user_states[user_id] = 'waiting_for_partner'
            
            wait_msg = (
                "🔍 <b>Suhbatdosh qidirilmoqda...</b>\n\n"
                "⏳ Iltimos kuting, tez orada suhbatdosh topiladi."
            )
            
            keyboard = self._get_waiting_keyboard()
            await message.answer(wait_msg, reply_markup=keyboard)
    
    async def _search_partner_with_gender_callback(self, callback: CallbackQuery, state: FSMContext):
        """Search for partner with gender preferences from callback."""
        user_id = callback.from_user.id
        user_prefs = self.user_gender_prefs.get(user_id, {})
        my_gender = user_prefs.get('my_gender', 'not_specified')
        wanted_gender = user_prefs.get('partner_gender', 'any')
        
        # Find matching partner
        matching_partner = None
        for waiting_user in self.waiting_users.copy():
            partner_id = waiting_user['user_id']
            partner_gender = waiting_user.get('my_gender', 'not_specified')
            partner_wants = waiting_user.get('partner_gender', 'any')
            
            # Skip self
            if partner_id == user_id:
                continue
            
            # Check if genders match preferences
            my_gender_matches = (wanted_gender == 'any' or partner_gender == wanted_gender)
            partner_gender_matches = (partner_wants == 'any' or my_gender == partner_wants)
            
            if my_gender_matches and partner_gender_matches:
                matching_partner = waiting_user
                break
        
        if matching_partner:
            partner_id = matching_partner['user_id']
            
            # Remove partner from waiting list
            self.waiting_users.remove(matching_partner)
            
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
            
            # Set states for both users
            await state.set_state(BotStates.support_chat)
            self.user_states[user_id] = 'in_chat'
            self.user_states[partner_id] = 'in_chat'
            
            await callback.message.answer(connect_msg, reply_markup=keyboard)
            
            # Notify partner
            try:
                await self.bot.send_message(partner_id, connect_msg, reply_markup=keyboard)
                self.logger.info(f"Gender-based chat connection established between {user_id} and {partner_id}")
                
                # Log chat start
                await self._log_message(user_id, "chat_start", f"Started gender-matched chat with {partner_id}")
                await self._log_message(partner_id, "chat_start", f"Started gender-matched chat with {user_id}")
                
            except Exception as e:
                self.logger.error(f"Error notifying partner {partner_id}: {e}")
                # Clean up connection on error
                self.active_chats.pop(user_id, None)
                self.active_chats.pop(partner_id, None)
                await callback.message.answer("❌ Xatolik yuz berdi. Qayta urinib ko'ring.")
                # Return partner to waiting queue
                self.waiting_users.append(matching_partner)
        else:
            # No matching partner found, add to waiting queue
            user_waiting_data = {
                'user_id': user_id,
                'my_gender': my_gender,
                'partner_gender': wanted_gender,
                'timestamp': datetime.now()
            }
            
            self.waiting_users.append(user_waiting_data)
            await state.set_state(BotStates.support_chat)
            self.user_states[user_id] = 'waiting_for_partner'
            
            wait_msg = (
                "🔍 <b>Suhbatdosh qidirilmoqda...</b>\n\n"
                "⏳ Iltimos kuting, tez orada suhbatdosh topiladi."
            )
            
            keyboard = self._get_waiting_keyboard()
            await callback.message.answer(wait_msg, reply_markup=keyboard)
    
    def _remove_user_from_waiting(self, user_id: int):
        """Remove user from waiting list."""
        # Remove from new format (dict-based) waiting list
        self.waiting_users = [user for user in self.waiting_users if not (isinstance(user, dict) and user.get('user_id') == user_id)]
        
        # Also clean up any invalid entries (should not happen but safety check)
        self.waiting_users = [user for user in self.waiting_users if isinstance(user, dict)]
        
        self.logger.info(f"Removed user {user_id} from waiting queue")
    
    def _get_my_gender_keyboard(self, language: str = 'uz'):
        """Get inline keyboard for user's own gender selection."""
        if language == 'uz':
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="👨 Erkak", callback_data="gender_my_male"),
                     InlineKeyboardButton(text="👩 Ayol", callback_data="gender_my_female")],
                    [InlineKeyboardButton(text="🚫 Aytmayman", callback_data="gender_my_not_specified")]
                ]
            )
        else:  # Russian
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="👨 Мужчина", callback_data="gender_my_male"),
                     InlineKeyboardButton(text="👩 Женщина", callback_data="gender_my_female")],
                    [InlineKeyboardButton(text="🚫 Не скажу", callback_data="gender_my_not_specified")]
                ]
            )
        return keyboard
    
    def _get_partner_gender_keyboard(self, language: str = 'uz'):
        """Get inline keyboard for partner gender selection."""
        if language == 'uz':
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="👨 Erkak bilan", callback_data="gender_partner_male"),
                     InlineKeyboardButton(text="👩 Ayol bilan", callback_data="gender_partner_female")],
                    [InlineKeyboardButton(text="🤷 Farqi yo'q", callback_data="gender_partner_any")]
                ]
            )
        else:  # Russian
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="👨 С мужчиной", callback_data="gender_partner_male"),
                     InlineKeyboardButton(text="👩 С женщиной", callback_data="gender_partner_female")],
                    [InlineKeyboardButton(text="🤷 Без разницы", callback_data="gender_partner_any")]
                ]
            )
        return keyboard

    async def _force_stop_everything(self, message: Message, state: FSMContext):
        """Force stop all user activities - robust cleanup for cancel search."""
        user_id = message.from_user.id
        
        # Clear FSM state no matter what
        await state.clear()
        
        # Remove from waiting queue if present using helper method
        self._remove_user_from_waiting(user_id)
        
        # Handle active chat cleanup
        if user_id in self.active_chats:
            partner_id = self.active_chats.get(user_id)
            
            # Remove chat connections
            self.active_chats.pop(user_id, None)
            if partner_id:
                self.active_chats.pop(partner_id, None)
                
            # Notify partner if exists
            if partner_id:
                try:
                    await self.bot.send_message(
                        partner_id,
                        "❌ Suhbatdosh suhbatni tark etdi.",
                        reply_markup=self._get_main_chat_keyboard()
                    )
                    self.logger.info(f"Notified partner {partner_id} about chat end")
                    
                    # Log chat end
                    await self._log_message(user_id, "chat_end", f"Force ended chat with {partner_id}")
                    await self._log_message(partner_id, "chat_end", f"Partner {user_id} force left chat")
                    
                except Exception as e:
                    self.logger.error(f"Error notifying partner {partner_id}: {e}")
        
        # Clear manual states
        self.user_states.pop(user_id, None)
        if 'partner_id' in locals() and partner_id:
            self.user_states.pop(partner_id, None)
        
        # Send success message
        await message.answer(
            "✅ Barcha faolliklar bekor qilindi.",
            reply_markup=self._get_main_chat_keyboard()
        )
        
        self.logger.info(f"Force stopped all activities for user {user_id}")
    
    async def _show_admin_panel(self, callback: CallbackQuery, state: FSMContext):
        """Show admin panel with updated statistics."""
        admin_text = (
            "👮‍♂️ <b>Admin Panel</b>\n\n"
            "📊 Bot statistikasi:\n"
            f"👥 Jami foydalanuvchilar: {await self._get_total_users()}\n"
            f"💬 Faol suhbatlar: {len(self.active_chats) // 2}\n"
            f"⏳ Kutayotganlar: {len(self.waiting_users)}"
        )
        
        keyboard = self._get_admin_keyboard()
        
        try:
            await callback.message.edit_text(admin_text, reply_markup=keyboard)
        except Exception:
            await callback.message.answer(admin_text, reply_markup=keyboard)
    
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
