#!/usr/bin/env python3
"""
Professional Telegram Bot Runner
Enhanced startup script with comprehensive validation and monitoring.
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


class BotRunner:
    """Professional bot runner with monitoring and error handling."""
    
    def __init__(self):
        self.logger: Optional = None
        self.startup_time = None
    
    def print_startup_banner(self):
        """Print professional startup banner."""
        from core.config import settings  # Deferred import to ensure .env is loaded
        banner = f"""
╔══════════════════════════════════════════════════════════╗
║                    {settings.bot.name:<35} ║
║              Professional Telegram Bot                   ║
╚══════════════════════════════════════════════════════════╝

🚀 Starting bot with configuration:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Bot Name:       {settings.bot.name}
🌐 Environment:    {settings.environment}
💾 Database:       {settings.database_path}
👑 Admins:         {len(settings.get_admin_ids())} configured
🔧 Debug Mode:     {'Enabled' if settings.debug else 'Disabled'}
📝 Log Level:      {settings.log_level}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏢 Support Information:
• Company:         {settings.contact.company_name}
• Support:         @{settings.contact.support_username}
• Email:           {settings.contact.support_email}
• Website:         {settings.contact.website}

⚙️  Bot Configuration:
• Users Per Page:  {settings.bot.users_per_page}
• Broadcast Delay: {settings.bot.broadcast_delay}s
• Max Message:     {settings.bot.max_message_length} chars
• Security:        {'Enabled' if settings.security.rate_limit_enabled else 'Disabled'}
        """
        print(banner)
    
    def validate_configuration(self) -> bool:
        """Validate bot configuration."""
        from core.config import settings  # Deferred import to ensure .env is loaded
        print("🔍 Validating configuration...")
        
        # Check required settings
        if not settings.bot_token or len(settings.bot_token) < 10:
            print("❌ Invalid or missing BOT_TOKEN")
            print("   Get your token from @BotFather on Telegram")
            return False
        
        if not settings.get_admin_ids():
            print("⚠️  Warning: No admin users configured")
            print("   Set ADMIN_USER_IDS in your .env file")
            print("   Get your user ID from @userinfobot")
        
        # Check database path
        db_path = settings.database_path
        if db_path.exists():
            print(f"📊 Database found: {db_path}")
        else:
            print(f"📊 New database will be created: {db_path}")
        
        # Check write permissions
        try:
            test_file = PROJECT_ROOT / "test_write_permission"
            test_file.touch()
            test_file.unlink()
            print("✅ Write permissions: OK")
        except Exception as e:
            print(f"❌ Write permission error: {e}")
            return False
        
        # Validate required packages
        try:
            import aiosqlite  # noqa: F401
            import aiogram    # noqa: F401
            import loguru     # noqa: F401
            print("✅ Required packages: OK")
        except ImportError as e:
            print(f"❌ Missing package: {e}")
            print("   Run: pip install -r requirements.txt")
            return False
        
        print("✅ Configuration validation passed!")
        return True
    
    def setup_logging_and_monitoring(self):
        """Setup logging and monitoring."""
        print("📝 Setting up logging system...")
        
        try:
            from core.logging import setup_logging, get_logger
            setup_logging()
            self.logger = get_logger("BotRunner")
            print("✅ Logging system initialized")
        except Exception as e:
            print(f"❌ Logging setup failed: {e}")
            sys.exit(1)
    
    def print_startup_complete(self):
        """Print startup completion message."""
        from core.config import settings  # Deferred import to ensure .env is loaded
        success_message = f"""
🎉 {settings.bot.name} Started Successfully!

📱 Bot is now running and ready to accept messages

💡 Quick Start Guide:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
👤 For Users:     Send /start to your bot in Telegram
👑 For Admins:    Send /admin to access admin panel
🛑 To Stop:       Press Ctrl+C

📊 Monitoring:
• Logs Directory: {PROJECT_ROOT / 'logs'}
• Main Log:       logs/bot.log
• Error Log:      logs/errors.log
• Admin Log:      logs/admin_actions.log
        """
        print(success_message)
    
    async def run_bot(self):
        """Run the bot with error handling."""
        if self.logger:
            self.logger.info("Starting bot main function...")
        
        try:
            from bot import main as bot_main  # Deferred import after validation/logging
            await bot_main()
        except KeyboardInterrupt:
            if self.logger:
                self.logger.info("Bot stopped by user (Ctrl+C)")
            print("\n⏹️  Bot stopped by user")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Bot crashed: {e}")
            print(f"\n💥 Bot crashed: {e}")
            raise
    
    def run(self):
        """Main runner method."""
        try:
            # Print banner
            self.print_startup_banner()
            
            # Validate configuration
            if not self.validate_configuration():
                print("\n❌ Configuration validation failed!")
                print("Please check your settings and try again.")
                sys.exit(1)
            
            # Setup logging
            self.setup_logging_and_monitoring()
            
            # Print startup complete
            self.print_startup_complete()
            
            # Run bot
            asyncio.run(self.run_bot())
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            from core.config import settings  # ensure availability for debug flag
            print(f"\n💥 Startup failed: {e}")
            if getattr(settings, 'debug', False):
                import traceback
                traceback.print_exc()
            sys.exit(1)


def main():
    """Main entry point."""
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required")
        sys.exit(1)
    
    # Check if .env exists
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        print("⚠️  .env file not found!")
        print("📝 Please create .env file based on .env.example for production use")
        print("🔧 Copy .env.example to .env and configure your settings")
        print("⚡ Continuing with default configuration for development...")
        print()
    
    # Run bot
    runner = BotRunner()
    runner.run()


if __name__ == "__main__":
    main()
