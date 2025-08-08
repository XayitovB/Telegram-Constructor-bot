"""
Language configuration and translations for the Telegram bot.
"""

from typing import Dict, Any

# Supported languages
SUPPORTED_LANGUAGES = {
    "uz": "🇺🇿 O'zbek",
    "ru": "🇷🇺 Русский", 
    "en": "🇺🇸 English"
}

# Default language
DEFAULT_LANGUAGE = "en"

# Translation dictionary
TRANSLATIONS = {
    "en": {
        # Main messages
        "welcome_message": "🌟 **Welcome to Professional Bot!**\n\nHi {name}! Welcome to our professional bot management platform.\n\n🚀 **What can you do here?**\n• View and manage your submitted bots\n• Submit new bots for approval and hosting\n• Get professional bot hosting services\n• Track your bot statuses and analytics\n\n💡 Use the buttons below to navigate through the bot.\n\n{admin_hint}",
        "admin_hint": "🔑 **Admin Access:** Use /admin for administrator tools.\n\n",
        "select_language": "🌍 **Language Selection**\n\nPlease select your preferred language:",
        "language_selected": "✅ **Language Updated**\n\nYour language has been set to **{language_name}**.\n\nWelcome! Use the menu buttons below to get started.",
        "my_bots_title": "🤖 **My Bots**",
        "my_bots_text": "Here you can view and manage your submitted bots.\n\n📊 **Bot Status:**\n• ✅ **Approved:** Bot is live and running\n• ⏳ **Pending:** Under review by admins\n• ❌ **Rejected:** Needs fixes before approval\n\n🚀 **No bots yet?** Use ➕ **Add Bots** to get started!",
        "add_bots_title": "➕ **Add New Bot**",
        "add_bots_text": "Submit your bot for approval and hosting!\n\n📋 **Requirements:**\n• Valid bot token from @BotFather\n• Clear description of bot functionality\n• Bot must comply with Telegram's terms\n• No spam, adult, or malicious content\n\n⏱️ **Review Process:**\n• Submit your bot details\n• Admin review (24-48 hours)\n• Get approval notification\n• Your bot goes live!\n\n📞 **Need help?** Contact our support team.",
        "unknown_command": "🤔 **Unknown Command**\n\nI don't understand that message. Please use the buttons below to navigate the bot.\n\n💡 **Quick Help:**\n• Use menu buttons for navigation\n• Admins can access admin panel with /admin\n• Press 📋 Help for more information",
        "back_main_menu": "🏠 **Main Menu**\n\nWelcome back! Choose an option below:",
        
        # Admin messages
        "access_denied": "❌ **Access Denied**\n\nThis command requires administrator privileges.",
        "admin_panel": "👑 **Administrator Panel**\n\nWelcome to the admin control center. Choose an option below:",
        "bot_statistics": "📊 **Bot Statistics**",
        "detailed_analytics": "📈 **Detailed Analytics Dashboard**",
        "bot_settings": "⚙️ **Bot Settings & Configuration**",
        "broadcast_management": "📢 **Broadcast Management**\n\nChoose your broadcast option:",
        "compose_broadcast": "📝 **Compose Broadcast Message**\n\nPlease send me the message you want to broadcast to all users.\n\n💡 **Tips:**\n• Keep messages clear and concise\n• Use markdown formatting if needed\n• Maximum length: 4000 characters",
        "broadcast_cancelled": "❌ **Broadcast Cancelled**",
        "invalid_message": "❌ **Invalid Message**\n\nMessage must be text and under {max_length} characters.",
        "sending_broadcast": "📤 **Sending Broadcast**\n\nPlease wait while the message is being sent to all users...",
        
        # User management
        "all_users": "👥 **All Users**",
        "active_users": "✅ **Active Users**",
        "view_admins": "👑 **Bot Administrators**",
        "no_users_found": "👥 **No Users Found**\n\nThe database is empty.",
        "no_active_users": "✅ **No Active Users Found**",
        "no_admins_found": "👑 **No Administrators Found**",
        "user_details": "👤 **User Details**",
        
        # Buttons - Main
        "btn_my_bots": "🤖 My Bots",
        "btn_add_bots": "➕ Add Bots",
        "btn_change_language": "🌍 Change Language",
        "btn_back_main": "🔙 Back to Main Menu",
        
        # Buttons - Admin
        "btn_view_all_users": "👥 View All Users",
        "btn_view_active_users": "✅ View Active Users",
        "btn_view_admins": "👑 View Admins",
        "btn_bot_statistics": "📊 Bot Statistics",
        "btn_detailed_analytics": "📈 Detailed Analytics",
        "btn_send_broadcast": "📢 Send Broadcast",
        "btn_bot_settings": "⚙️ Bot Settings",
        "btn_back_admin": "🔙 Back to Admin Panel",
        "btn_compose_message": "📝 Compose Message",
        "btn_cancel_operation": "❌ Cancel Operation",
    },
    "ru": {
        # Main messages
        "welcome_message": "🌟 **Добро пожаловать в Professional Bot!**\n\nПривет, {name}! Добро пожаловать на нашу профессиональную платформу управления ботами.\n\n🚀 **Что вы можете делать здесь?**\n• Просматривать и управлять вашими ботами\n• Отправлять новых ботов на одобрение и хостинг\n• Получать профессиональные услуги хостинга ботов\n• Отслеживать статусы и аналитику ваших ботов\n\n💡 Используйте кнопки ниже для навигации по боту.\n\n{admin_hint}",
        "admin_hint": "🔑 **Доступ администратора:** Используйте /admin для инструментов администратора.\n\n",
        "select_language": "🌍 **Выбор языка**\n\nПожалуйста, выберите предпочитаемый язык:",
        "language_selected": "✅ **Язык обновлен**\n\nВаш язык установлен на **{language_name}**.\n\nДобро пожаловать! Используйте кнопки меню ниже для начала работы.",
        "my_bots_title": "🤖 **Мои боты**",
        "my_bots_text": "Здесь вы можете просматривать и управлять вашими ботами.\n\n📊 **Статус бота:**\n• ✅ **Одобрен:** Бот работает\n• ⏳ **На рассмотрении:** Проверяется администраторами\n• ❌ **Отклонен:** Требует исправлений\n\n🚀 **Еще нет ботов?** Используйте ➕ **Добавить ботов**!",
        "add_bots_title": "➕ **Добавить нового бота**",
        "add_bots_text": "Отправьте вашего бота на одобрение и хостинг!\n\n📋 **Требования:**\n• Действительный токен бота от @BotFather\n• Четкое описание функциональности бота\n• Бот должен соответствовать условиям Telegram\n• Запрещен спам, взрослый или вредоносный контент\n\n⏱️ **Процесс рассмотрения:**\n• Отправьте детали бота\n• Проверка администратором (24-48 часов)\n• Получите уведомление об одобрении\n• Ваш бот запущен!\n\n📞 **Нужна помощь?** Свяжитесь с нашей службой поддержки.",
        "unknown_command": "🤔 **Неизвестная команда**\n\nЯ не понимаю это сообщение. Пожалуйста, используйте кнопки ниже для навигации по боту.\n\n💡 **Быстрая помощь:**\n• Используйте кнопки меню для навигации\n• Администраторы могут получить доступ к панели администратора через /admin\n• Нажмите 📋 Помощь для получения дополнительной информации",
        "back_main_menu": "🏠 **Главное меню**\n\nДобро пожаловать обратно! Выберите опцию ниже:",
        
        # Admin messages
        "access_denied": "❌ **Доступ запрещен**\n\nЭта команда требует прав администратора.",
        "admin_panel": "👑 **Панель администратора**\n\nДобро пожаловать в центр управления администратора. Выберите опцию:",
        "bot_statistics": "📊 **Статистика бота**",
        "detailed_analytics": "📈 **Подробная панель аналитики**",
        "bot_settings": "⚙️ **Настройки и конфигурация бота**",
        "broadcast_management": "📢 **Управление рассылкой**\n\nВыберите вариант рассылки:",
        "compose_broadcast": "📝 **Составить сообщение для рассылки**\n\nПожалуйста, отправьте сообщение, которое вы хотите разослать всем пользователям.\n\n💡 **Советы:**\n• Пишите ясно и кратко\n• Используйте markdown форматирование при необходимости\n• Максимальная длина: 4000 символов",
        "broadcast_cancelled": "❌ **Рассылка отменена**",
        "invalid_message": "❌ **Недопустимое сообщение**\n\nСообщение должно быть текстом и не превышать {max_length} символов.",
        "sending_broadcast": "📤 **Отправка рассылки**\n\nПожалуйста, подождите, пока сообщение отправляется всем пользователям...",
        
        # User management
        "all_users": "👥 **Все пользователи**",
        "active_users": "✅ **Активные пользователи**",
        "view_admins": "👑 **Администраторы бота**",
        "no_users_found": "👥 **Пользователи не найдены**\n\nБаза данных пуста.",
        "no_active_users": "✅ **Активные пользователи не найдены**",
        "no_admins_found": "👑 **Администраторы не найдены**",
        "user_details": "👤 **Информация о пользователе**",
        
        # Buttons - Main
        "btn_my_bots": "🤖 Мои боты",
        "btn_add_bots": "➕ Добавить ботов",
        "btn_change_language": "🌍 Сменить язык",
        "btn_back_main": "🔙 Назад в главное меню",
        
        # Buttons - Admin
        "btn_view_all_users": "👥 Все пользователи",
        "btn_view_active_users": "✅ Активные пользователи",
        "btn_view_admins": "👑 Администраторы",
        "btn_bot_statistics": "📊 Статистика бота",
        "btn_detailed_analytics": "📈 Подробная аналитика",
        "btn_send_broadcast": "📢 Отправить рассылку",
        "btn_bot_settings": "⚙️ Настройки бота",
        "btn_back_admin": "🔙 Назад в панель админа",
        "btn_compose_message": "📝 Написать сообщение",
        "btn_cancel_operation": "❌ Отменить операцию",
    },
    "uz": {
        # Main messages  
        "welcome_message": "🌟 **Professional Bot'ga xush kelibsiz!**\n\nSalom, {name}! Bizning professional bot boshqaruv platformamizga xush kelibsiz.\n\n🚀 **Bu yerda nima qilishingiz mumkin?**\n• Yuborilgan botlaringizni ko'rish va boshqarish\n• Tasdiqlash va hosting uchun yangi botlar yuborish\n• Professional bot hosting xizmatlarini olish\n• Bot holatlari va analitikani kuzatish\n\n💡 Bot bo'ylab navigatsiya qilish uchun quyidagi tugmalardan foydalaning.\n\n{admin_hint}",
        "admin_hint": "🔑 **Administrator kirishishi:** Administrator vositalari uchun /admin dan foydalaning.\n\n",
        "select_language": "🌍 **Til tanlash**\n\nIltimos, afzal ko'rgan tilingizni tanlang:",
        "language_selected": "✅ **Til yangilandi**\n\nTilingiz **{language_name}** ga o'rnatildi.\n\nXush kelibsiz! Ishni boshlash uchun quyidagi menyu tugmalaridan foydalaning.",
        "my_bots_title": "🤖 **Mening botlarim**",
        "my_bots_text": "Bu yerda yuborilgan botlaringizni ko'rishingiz va boshqarishingiz mumkin.\n\n📊 **Bot holati:**\n• ✅ **Tasdiqlangan:** Bot ishlayapti\n• ⏳ **Kutilmoqda:** Administratorlar tomonidan ko'rib chiqilmoqda\n• ❌ **Rad etilgan:** Tuzatishlar talab qilinadi\n\n🚀 **Hali botlar yo'qmi?** ➕ **Botlar qo'shish** dan foydalaning!",
        "add_bots_title": "➕ **Yangi bot qo'shish**",
        "add_bots_text": "Botingizni tasdiqlash va hosting uchun yuboring!\n\n📋 **Talablar:**\n• @BotFather dan haqiqiy bot tokeni\n• Bot funksiyalarining aniq tavsifi\n• Bot Telegram shartlariga mos kelishi kerak\n• Spam, kattalar yoki zararli kontent taqiqlangan\n\n⏱️ **Ko'rib chiqish jarayoni:**\n• Bot tafsilotlarini yuboring\n• Administrator tekshiruvi (24-48 soat)\n• Tasdiqlash xabarini oling\n• Botingiz ishga tushadi!\n\n📞 **Yordam kerakmi?** Qo'llab-quvvatlash guruhimizga murojaat qiling.",
        "unknown_command": "🤔 **Noma'lum buyruq**\n\nMen bu xabarni tushunmayapman. Iltimos, bot bo'ylab navigatsiya qilish uchun quyidagi tugmalardan foydalaning.\n\n💡 **Tezkor yordam:**\n• Navigatsiya uchun menyu tugmalaridan foydalaning\n• Administratorlar /admin orqali administrator paneliga kirishlari mumkin\n• Qo'shimcha ma'lumot olish uchun 📋 Yordam tugmasini bosing",
        "back_main_menu": "🏠 **Asosiy menyu**\n\nXush kelibsiz! Quyidagi variantdan birini tanlang:",
        
        # Admin messages
        "access_denied": "❌ **Kirish rad etildi**\n\nBu buyruq administrator huquqlarini talab qiladi.",
        "admin_panel": "👑 **Administrator paneli**\n\nAdministrator boshqaruv markaziga xush kelibsiz. Quyidagi variantni tanlang:",
        "bot_statistics": "📊 **Bot statistikasi**",
        "detailed_analytics": "📈 **Batafsil analitika paneli**",
        "bot_settings": "⚙️ **Bot sozlamalari va konfiguratsiyasi**",
        "broadcast_management": "📢 **Xabar yuborish boshqaruvi**\n\nXabar yuborish variantini tanlang:",
        "compose_broadcast": "📝 **Ommaviy xabar yozish**\n\nIltimos, barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yuboring.\n\n💡 **Maslahatlar:**\n• Aniq va qisqa yozing\n• Kerak bo'lsa markdown formatlashdan foydalaning\n• Maksimal uzunlik: 4000 belgi",
        "broadcast_cancelled": "❌ **Xabar yuborish bekor qilindi**",
        "invalid_message": "❌ **Noto'g'ri xabar**\n\nXabar matn bo'lishi va {max_length} belgidan oshmasligi kerak.",
        "sending_broadcast": "📤 **Xabar yuborilmoqda**\n\nIltimos kuting, xabar barcha foydalanuvchilarga yuborilmoqda...",
        
        # User management
        "all_users": "👥 **Barcha foydalanuvchilar**",
        "active_users": "✅ **Faol foydalanuvchilar**",
        "view_admins": "👑 **Bot administratorlari**",
        "no_users_found": "👥 **Foydalanuvchilar topilmadi**\n\nMa'lumotlar bazasi bo'sh.",
        "no_active_users": "✅ **Faol foydalanuvchilar topilmadi**",
        "no_admins_found": "👑 **Administratorlar topilmadi**",
        "user_details": "👤 **Foydalanuvchi ma'lumotlari**",
        
        # Buttons - Main
        "btn_my_bots": "🤖 Mening botlarim",
        "btn_add_bots": "➕ Bot qo'shish",
        "btn_change_language": "🌍 Tilni o'zgartirish",
        "btn_back_main": "🔙 Asosiy menyuga qaytish",
        
        # Buttons - Admin
        "btn_view_all_users": "👥 Barcha foydalanuvchilar",
        "btn_view_active_users": "✅ Faol foydalanuvchilar",
        "btn_view_admins": "👑 Administratorlar",
        "btn_bot_statistics": "📊 Bot statistikasi",
        "btn_detailed_analytics": "📈 Batafsil analitika",
        "btn_send_broadcast": "📢 Xabar yuborish",
        "btn_bot_settings": "⚙️ Bot sozlamalari",
        "btn_back_admin": "🔙 Admin paneliga qaytish",
        "btn_compose_message": "📝 Xabar yozish",
        "btn_cancel_operation": "❌ Bekor qilish",
    }
}

def get_text(key: str, language: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """Get translated text for a given key and language."""
    # Fallback to default language if requested language not available
    lang = language if language in TRANSLATIONS else DEFAULT_LANGUAGE
    
    # Get text from translations
    text = TRANSLATIONS.get(lang, {}).get(key, "")
    
    # Fallback to English if text not found
    if not text and lang != DEFAULT_LANGUAGE:
        text = TRANSLATIONS.get(DEFAULT_LANGUAGE, {}).get(key, f"Missing translation: {key}")
    
    # Format text with provided arguments
    if text and kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            # If formatting fails, return original text
            pass
    
    return text

def get_language_name(language_code: str) -> str:
    """Get display name for language code."""
    return SUPPORTED_LANGUAGES.get(language_code, language_code)
