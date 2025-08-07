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
    },
    "ru": {
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
    },
    "uz": {
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
