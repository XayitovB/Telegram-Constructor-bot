# 🤖 Professional Telegram Constructor Bot

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![aiogram 3.2.0](https://img.shields.io/badge/aiogram-3.2.0-green.svg)](https://aiogram.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Quality](https://img.shields.io/badge/code%20quality-A-brightgreen.svg)]()

A **production-ready** Telegram bot with comprehensive admin features, multi-language support, and professional architecture. Perfect for bot management, user administration, and broadcasting.

## ✨ Features

### 🔥 Core Features
- **Button-Only Interface** - Intuitive navigation without complex commands
- **Multi-Language Support** - English, Russian, Uzbek with automatic detection
- **Professional Admin Panel** - Complete user and bot management system
- **Advanced Broadcasting** - Rate-limited mass messaging with delivery tracking
- **Comprehensive Statistics** - Detailed analytics and user insights
- **Data Export** - CSV export for users and statistics
- **Professional Logging** - Multi-level logging with rotation and monitoring

### 👥 User Management
- User registration and profile management
- Language preference system
- Activity tracking and statistics
- Ban/unban functionality
- Admin role management
- User search and filtering

### 📊 Analytics & Reporting
- Real-time bot statistics
- User activity metrics
- Message tracking and analytics
- Growth and engagement reports
- Export functionality for all data

### 🛡️ Security & Admin Features
- Secure admin-only access via `/admin` command
- Role-based permissions
- Rate limiting and abuse protection
- Comprehensive action logging
- Database backup and maintenance

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

## 📖 Usage

### For Users
1. Start a conversation with your bot
2. Send `/start` to begin
3. Select your preferred language
4. Use the menu buttons to navigate

### For Administrators
1. Send `/admin` to access the admin panel
2. Use admin buttons to manage users and settings
3. Access broadcasting, statistics, and user management features

### Available Commands
- `/start` - Start the bot and show main menu
- `/admin` - Access admin panel (admins only)

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
├── bot.py                  # Main bot application
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
- **bot.py** - Main bot handlers, FSM states, and business logic
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
