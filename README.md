# 🚀 Telegram Bot Constructor

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![aiogram 3.2.0](https://img.shields.io/badge/aiogram-3.2.0-green.svg)](https://aiogram.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-brightgreen.svg)]()

A **revolutionary** Telegram Bot Constructor that allows users to create and manage their own Telegram bots without any coding knowledge. This platform provides a complete bot-as-a-service solution with multi-language support, comprehensive admin features, and professional architecture.

## 🎯 What Makes This Special?

This isn't just another Telegram bot - it's a **Bot Constructor Platform** where:
- 🤖 **Users can create their own bots** by simply providing a bot token
- 🔧 **No coding required** - everything is handled automatically
- 🌍 **Multi-language support** with Uzbek and Russian languages
- 📊 **Complete bot management** with statistics and user tracking
- 👥 **Professional admin system** for platform management

## ✨ Platform Features

### 🏗️ Bot Constructor Features
- **🤖 Instant Bot Creation** - Users create bots by providing a bot token from @BotFather
- **📱 Auto-Generated Bot Interface** - Each created bot gets a professional interface automatically
- **🌍 Multi-Language Bot Support** - Created bots support Uzbek and Russian languages
- **📊 Individual Bot Statistics** - Each bot tracks its own users and message statistics
- **⚡ Real-Time Bot Management** - Start, stop, and manage user bots dynamically
- **🔧 Template-Based Bot Generation** - Professional bot template with menu system

### 🎯 User Bot Features (Auto-Generated)
Each user-created bot includes:
- **Language Selection** - Uzbek/Russian language choice on first start
- **Professional Menu System** - Profile, Statistics, Settings, Help, Support
- **User Management** - Automatic user registration and tracking
- **Statistics Dashboard** - User count, message statistics, activity tracking
- **Settings Panel** - Language switching and user preferences
- **Support System** - Direct contact with bot creator

### 🛠️ Constructor Platform Features
- **👥 Multi-User Platform** - Multiple users can create their own bots
- **🔐 Token Validation** - Automatic bot token verification via Telegram API
- **📋 Bot Information Display** - Shows bot details before confirmation
- **✅ Creation Confirmation** - Users confirm bot creation with full details
- **🚀 Instant Deployment** - Bots start immediately after creation
- **📊 Platform Statistics** - Track all created bots and their activity

### 🔧 Admin Management System
- **🎛️ Complete Platform Control** - Manage all users and their bots
- **📈 Global Statistics** - Platform-wide analytics and reports
- **👥 User Administration** - Ban, unban, and manage platform users
- **📢 Broadcasting System** - Send announcements to platform users
- **📁 Data Export** - Export user data and platform statistics
- **🔍 Bot Monitoring** - Track and manage all created user bots

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- Your Telegram User ID from [@userinfobot](https://t.me/userinfobot)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/telegram-constructor-bot.git
   cd telegram-constructor-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot:**
   ```bash
   cp .env.example .env
   # Edit .env with your bot token and admin user ID
   ```

4. **Run the bot:**
   ```bash
   python run.py
   ```
   
   **Or on Windows:**
   ```bash
   start.bat
   ```

### Configuration

Edit the `.env` file with your settings:

```env
# Required Configuration
BOT_TOKEN=your_bot_token_from_botfather
ADMIN_USER_IDS=[your_user_id]

# Optional Configuration
DATABASE__PATH=bot.db
BOT__USERS_PER_PAGE=10
BOT__BROADCAST_DELAY=0.1
LOG_LEVEL=INFO
ENVIRONMENT=development

# Contact Information
CONTACT__SUPPORT_USERNAME=support
CONTACT__SUPPORT_EMAIL=support@example.com
CONTACT__WEBSITE=https://example.com
CONTACT__COMPANY_NAME=Your Company
```

## 📖 How It Works

### 🤖 Creating Your Own Bot (For Users)
1. **Start the Constructor Bot** - Send `/start` to begin
2. **Choose Language** - Select your preferred language (English/Russian/Uzbek)
3. **Click "🤖 Create Bot"** - Access the bot creation menu
4. **Get a Bot Token** - Create a new bot via [@BotFather](https://t.me/BotFather) and get the token
5. **Send Your Bot Token** - Paste your bot token to the constructor
6. **Confirm Creation** - Review bot details and confirm creation
7. **Your Bot is Ready!** - Your bot starts automatically with full functionality

### 🎯 Your Created Bot Features
Once created, your bot will have:
- **🌍 Language Selection** - Users can choose Uzbek or Russian
- **👤 Profile Management** - User registration and profile viewing
- **📊 Statistics Dashboard** - View bot statistics and user count
- **⚙️ Settings Panel** - Language switching and preferences
- **❓ Help System** - Built-in help and support
- **📞 Support Contact** - Direct contact with you (bot creator)

### 🛠️ Bot Creation Process
```
1. User sends bot token → 
2. System validates token → 
3. Shows bot information → 
4. User confirms creation → 
5. Bot data saved to database → 
6. User bot starts automatically → 
7. Success message with instructions
```

### 👑 For Platform Administrators
1. **Send `/admin`** - Access the admin panel
2. **Platform Management** - View all users and their created bots
3. **Global Statistics** - Monitor platform usage and performance
4. **User Administration** - Manage platform users (ban/unban)
5. **Broadcasting** - Send announcements to all platform users
6. **Data Export** - Export user data and platform statistics

### 🔧 Available Commands
- `/start` - Start the constructor bot and access main menu
- `/admin` - Access platform admin panel (admins only)
- Any other command on user-created bots depends on their configuration

## 🏗️ Architecture

### Project Structure
```
Telegram-Constructor-bot/
├── core/                    # Core functionality
│   ├── __init__.py
│   ├── config.py           # Pydantic configuration management
│   ├── database.py         # Database operations and models
│   ├── languages.py        # Multi-language support
│   └── logging.py          # Professional logging system
├── ui/                     # User interface components
│   ├── __init__.py
│   ├── keyboards.py        # Telegram keyboards and buttons
│   └── formatters.py       # Message formatting and utilities
├── logs/                   # Auto-generated log files
├── bot.py                  # Main constructor bot application
├── user_bot_template.py    # Template for user-created bots
├── run.py                  # Professional startup script
├── requirements.txt        # Python dependencies
├── .env.example           # Configuration template
├── .gitignore            # Git ignore rules
└── start.bat             # Windows startup script
```

### Key Components

#### Core Modules
- **config.py** - Type-safe configuration with Pydantic validation
- **database.py** - SQLite database with async operations and migrations
- **languages.py** - Multi-language translation system
- **logging.py** - Professional logging with rotation and multiple outputs

#### UI Modules
- **keyboards.py** - Dynamic keyboard generation for different user types
- **formatters.py** - Message formatting, data export, and utilities

#### Bot Logic
- **bot.py** - Main constructor bot with user bot creation handlers and FSM states
- **user_bot_template.py** - Dynamic template for user-created bots with multi-language support
- **run.py** - Professional startup with validation and monitoring

## 🌐 Multi-Language Support

The bot supports multiple languages with automatic detection:

- 🇺🇸 **English** (default)
- 🇷🇺 **Russian** 
- 🇺🇿 **Uzbek**

### Adding New Languages

1. Update `SUPPORTED_LANGUAGES` in `core/languages.py`
2. Add translations to the `TRANSLATIONS` dictionary
3. Test the new language with the language selection interface

## 📊 Database Schema

The bot uses SQLite with the following main tables:

- **users** - User profiles, preferences, and statistics
- **messages** - Message logging and tracking
- **broadcasts** - Broadcast history and analytics
- **admin_actions** - Admin activity logging
- **user_bots** - Bot submission and management
- **admin_messages** - User-to-admin communications
- **bot_settings** - Dynamic bot configuration

## 🔧 Development

### Requirements
- Python 3.8+
- aiogram 3.2.0+
- aiosqlite
- pydantic 2.5.0+
- loguru

### Development Setup

1. **Clone and setup virtual environment:**
   ```bash
   git clone <repository>
   cd telegram-constructor-bot
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure development environment:**
   ```bash
   cp .env.example .env
   # Set DEBUG=true and LOG_LEVEL=DEBUG in .env
   ```

3. **Run in development mode:**
   ```bash
   python run.py
   ```

## 🛡️ Security

### Security Features
- Admin access control with user ID verification
- Rate limiting for broadcast operations
- Input validation and sanitization
- Secure database operations with prepared statements
- Comprehensive logging for audit trails

### Security Best Practices
- Keep your bot token secure and never commit it to version control
- Regularly update dependencies
- Monitor logs for suspicious activity
- Use environment variables for sensitive configuration
- Implement proper backup strategies

## 📈 Performance & Monitoring

### Optimization Features
- Async/await throughout for non-blocking operations
- Connection pooling for database operations
- Efficient pagination for large datasets
- Rate limiting to prevent API abuse
- Memory-efficient data processing

### Log Management
- Automatic log rotation (10MB files)
- 7-day retention for general logs
- 30-day retention for error logs
- 90-day retention for admin action logs

## 💬 Support & Troubleshooting

### Common Issues

1. **"Invalid bot token" error:**
   - Verify your bot token from @BotFather
   - Check for extra spaces or characters in .env file

2. **"No admin users configured" warning:**
   - Ensure ADMIN_USER_IDS contains your actual Telegram user ID
   - Get your ID from @userinfobot

3. **Import errors:**
   - Install all requirements: `pip install -r requirements.txt`
   - Use Python 3.8 or higher

4. **Database issues:**
   - Check file permissions in the project directory
   - Ensure SQLite is available on your system

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ using Python and aiogram**

*This bot is designed for professional use and can handle production workloads. It's been thoroughly tested and optimized for reliability and performance.*
