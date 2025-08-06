# Professional Telegram Bot with Admin Features

A enterprise-grade Telegram bot built with aiogram 3.x featuring advanced user management, comprehensive admin controls, broadcasting capabilities, and robust SQLite database integration. Designed with professional standards including proper logging, error handling, and scalable architecture.

## 🌟 Key Features

### 👤 User Experience
- **Button-Only Interface**: Intuitive navigation without slash commands
- **Smart Profile Management**: Automatic user data collection and updates
- **Professional Help System**: Context-aware help and information
- **Contact Integration**: Built-in support contact system
- **Activity Tracking**: Comprehensive user interaction logging

### 👑 Admin Capabilities
- **Complete User Management**: View, filter, and manage all users
- **Advanced Analytics**: Detailed statistics and engagement metrics
- **Professional Broadcasting**: Mass messaging with delivery tracking
- **Data Export**: CSV exports with advanced user metrics
- **Access Control**: Granular admin privilege management
- **User Moderation**: Ban/unban with reason tracking
- **Admin Action Logging**: Comprehensive audit trail

## 📁 Project Structure

```
Professional-Telegram-Bot/
├── core/                      # Core functionality
│   ├── config.py             # Professional configuration with Pydantic
│   ├── database.py           # Advanced database operations & models
│   ├── logging.py            # Multi-level logging system
│   └── __init__.py
├── ui/                        # User interface components
│   ├── keyboards.py          # Professional keyboard layouts
│   ├── formatters.py         # Message formatting & utilities
│   └── __init__.py
├── bot.py                     # Main bot with button-only interface
├── run.py                     # Professional runner with validation
├── requirements.txt           # Python dependencies
├── .env                       # Environment configuration
├── .env.example              # Environment template
└── README.md                 # This documentation
```

## Installation

### 1. Clone or Download
Download all the files to your desired directory.

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment
Edit the `.env` file with your bot token and admin user IDs:

```env
BOT_TOKEN=your_bot_token_here
ADMIN_USER_IDS=123456789,987654321
```

**How to get your Bot Token:**
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Use `/newbot` command
3. Choose a name and username for your bot
4. Copy the provided token

**How to get your User ID:**
1. Message [@userinfobot](https://t.me/userinfobot) on Telegram
2. It will show your user ID

### 4. Run the Bot
```bash
python run.py
```

Or directly:
```bash
python bot.py
```

## Configuration Options

You can customize the bot by modifying the `.env` file:

```env
# Required
BOT_TOKEN=your_bot_token_here
ADMIN_USER_IDS=123456789,987654321

# Optional
DATABASE_PATH=bot.db
USERS_PER_PAGE=10
BROADCAST_DELAY=0.1
LOG_LEVEL=INFO
SUPPORT_USERNAME=your_support_username
SUPPORT_EMAIL=support@example.com
SUPPORT_WEBSITE=https://example.com
```

## 🎯 Bot Interface

### 📱 Available Commands
- **`/start`** - Initialize the bot and show main menu
- **`/admin`** - Access admin panel (👑 **ADMINS ONLY**)

### 👤 User Interface (Button Navigation)
- **👤 My Profile** - View your account information
- **ℹ️ Information** - Get help and bot information  
- **📞 Contact Support** - Get support contact details
- **📋 Help** - Detailed help and feature guide

### 👑 Admin Interface (After `/admin` command)
- **👥 View All Users** - Browse all registered users
- **✅ View Active Users** - See currently active users
- **👑 View Admins** - List all administrators
- **🚫 View Banned Users** - Review banned user list
- **📊 Bot Statistics** - Comprehensive analytics dashboard
- **📢 Send Broadcast** - Send messages to all users
- **⚙️ Bot Settings** - Configure bot parameters

## Database Schema

The bot uses SQLite with the following tables:

### Users Table
- `user_id` (INTEGER PRIMARY KEY)
- `username` (TEXT)
- `first_name` (TEXT)
- `last_name` (TEXT)
- `is_admin` (BOOLEAN)
- `is_active` (BOOLEAN)
- `join_date` (DATETIME)
- `last_activity` (DATETIME)

### Messages Table
- `id` (INTEGER PRIMARY KEY)
- `user_id` (INTEGER)
- `message_type` (TEXT)
- `message_text` (TEXT)
- `created_at` (DATETIME)

### Broadcasts Table
- `id` (INTEGER PRIMARY KEY)
- `admin_id` (INTEGER)
- `message_text` (TEXT)
- `sent_count` (INTEGER)
- `failed_count` (INTEGER)
- `created_at` (DATETIME)

## Key Features Explained

### 🔐 Role-Based Access Control
- Automatic admin detection based on user IDs
- Different keyboard layouts for admins and regular users
- Protected admin commands and features

### 📊 Statistics Dashboard
- Total users, active users, admin count
- Daily message and registration statistics
- Activity rate calculations

### 📢 Broadcasting System
- Send messages to all active users
- Broadcast confirmation with preview
- Success/failure tracking and reporting
- Rate limiting to avoid Telegram limits

### 👥 User Management
- View all users with pagination
- Filter by active/inactive status
- Export user data to CSV
- User action controls (ban/unban, admin management)

### 📱 Interactive Interface
- Custom keyboards for easy navigation
- Inline keyboards for quick actions
- State machine for multi-step operations
- Cancel options for all operations

## Error Handling

The bot includes comprehensive error handling:
- Database connection errors
- Telegram API errors
- Invalid user inputs
- Configuration validation
- Logging for debugging

## Security Features

- Admin privilege verification
- SQL injection prevention (parameterized queries)
- Rate limiting for broadcasts
- Input validation and sanitization

## Deployment

### Local Development
```bash
python run.py
```

### Production Deployment
1. Use a process manager like `supervisor` or `systemd`
2. Set up proper logging
3. Configure environment variables securely
4. Use a production-grade database if needed

### Example systemd service:
```ini
[Unit]
Description=Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/path/to/bot
ExecStart=/usr/bin/python3 /path/to/bot/run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Common Issues

1. **Bot doesn't respond**
   - Check if BOT_TOKEN is correct
   - Verify bot is running without errors
   - Check Telegram API status

2. **Database errors**
   - Ensure write permissions in bot directory
   - Check if database file is corrupted

3. **Admin features not working**
   - Verify your user ID is in ADMIN_USER_IDS
   - Make sure to restart bot after configuration changes

4. **Broadcast fails**
   - Check for Telegram rate limits
   - Verify users haven't blocked the bot

## Contributing

To extend the bot:
1. Add new handlers in `bot.py`
2. Create corresponding keyboards in `keyboards.py`
3. Add database operations in `database.py`
4. Include utility functions in `utils.py`

## License

This project is open source and available under the MIT License.

## Support

For issues or questions:
- Check the troubleshooting section
- Review the logs in `bot.log`
- Create an issue with detailed information

---

**Made with ❤️ using aiogram 3.x**
