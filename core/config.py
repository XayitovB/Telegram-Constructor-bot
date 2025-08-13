"""
Configuration module using Pydantic for type validation and settings management.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings


class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    path: str = Field(default="bot.db", description="SQLite database file path")
    backup_enabled: bool = Field(default=True, description="Enable database backups")
    backup_interval: int = Field(default=24, description="Backup interval in hours")


class BotConfig(BaseModel):
    """Bot-specific configuration."""
    name: str = Field(default="Professional Bot", description="Bot display name")
    description: str = Field(default="A professional Telegram bot with advanced features", description="Bot description")
    users_per_page: int = Field(default=10, ge=1, le=20, description="Number of users to display per page")
    broadcast_delay: float = Field(default=0.05, ge=0.01, le=1.0, description="Delay between broadcast messages")
    max_message_length: int = Field(default=4000, description="Maximum message length")


class ContactConfig(BaseModel):
    """Contact information configuration."""
    support_username: str = Field(default="support", description="Support username")
    support_email: str = Field(default="support@example.com", description="Support email")
    website: str = Field(default="https://example.com", description="Website URL")
    company_name: str = Field(default="Your Company", description="Company name")


class SecurityConfig(BaseModel):
    """Security configuration settings."""
    rate_limit_enabled: bool = Field(default=True, description="Enable rate limiting")
    max_requests_per_minute: int = Field(default=20, description="Max requests per minute per user")
    ban_duration_hours: int = Field(default=24, description="Default ban duration in hours")


class Settings(BaseSettings):
    """Main application settings."""
    
    # Core settings
    bot_token: str = Field(default="", description="Telegram bot token")
    admin_user_ids: List[int] = Field(default_factory=list, description="List of admin user IDs")
    
    # Environment
    environment: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=False, description="Debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # Nested configurations
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    bot: BotConfig = Field(default_factory=BotConfig)
    contact: ContactConfig = Field(default_factory=ContactConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    model_config = {
        "env_file": ".env",
        "env_nested_delimiter": "__",
        "case_sensitive": False,
        "env_file_encoding": "utf-8"
    }
    
    @field_validator('admin_user_ids', mode='before')
    @classmethod
    def parse_admin_ids(cls, v):
        """Parse admin user IDs from string, int, or list."""
        if isinstance(v, str):
            # Remove any quotes and brackets that might be present
            v = v.strip().strip('"').strip("'").strip('[]')
            if ',' in v:
                try:
                    return [int(x.strip()) for x in v.split(',') if x.strip() and x.strip().isdigit()]
                except ValueError:
                    return []
            else:
                try:
                    return [int(v)] if v.isdigit() else []
                except ValueError:
                    return []
        elif isinstance(v, int):
            return [v]
        elif isinstance(v, list):
            # Ensure all elements are integers
            try:
                return [int(x) for x in v if str(x).isdigit()]
            except (ValueError, TypeError):
                return []
        return []
    
    @field_validator('bot_token')
    @classmethod
    def validate_token(cls, v):
        """Validate bot token format."""
        # Allow empty token for development/testing, but validate if provided
        if v and len(v) < 10:
            raise ValueError("Invalid bot token format")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def database_path(self) -> Path:
        """Get database file path."""
        return Path(self.database.path)
    
    def get_admin_ids(self) -> List[int]:
        """Get list of admin user IDs."""
        return self.admin_user_ids.copy()
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in self.admin_user_ids


# Global settings instance
# Create settings with hardcoded working configuration
class WorkingSettings:
    """Simple working settings class without Pydantic validation."""
    
    def __init__(self):
        # Core settings - should come from environment variables
        self.bot_token: str = ""
        self.admin_user_ids: List[int] = []
        
        # Environment
        self.environment: str = "development"
        self.debug: bool = False
        self.log_level: str = "INFO"
        
        # Nested configurations
        self.database: DatabaseConfig = DatabaseConfig()
        self.bot: BotConfig = BotConfig()
        self.contact: ContactConfig = ContactConfig()
        self.security: SecurityConfig = SecurityConfig()
    
    def get_admin_ids(self) -> List[int]:
        """Get list of admin user IDs."""
        return self.admin_user_ids.copy()
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        return user_id in self.admin_user_ids
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def database_path(self) -> Path:
        """Get database file path."""
        return Path(self.database.path)

# Initialize settings with simplified .env loading
try:
    from dotenv import load_dotenv
    import os
    
    # Load .env file
    load_dotenv()
    
    # Get values from environment
    bot_token = os.getenv('BOT_TOKEN', '').strip('"').strip("'")
    admin_ids_str = os.getenv('ADMIN_USER_IDS', '').strip('"').strip("'")
    
    # Parse admin IDs from string
    admin_ids = []
    if admin_ids_str:
        try:
            # Handle different formats: "123,456" or "[123,456]" or "123 456"
            admin_str = admin_ids_str.strip('[]')
            # Split by comma, space, or semicolon
            import re
            admin_parts = re.split(r'[,\s;]+', admin_str)
            admin_ids = [int(x.strip()) for x in admin_parts if x.strip() and x.strip().isdigit()]
        except ValueError:
            print("⚠️  Warning: Could not parse ADMIN_USER_IDS from .env file")
            admin_ids = [1858042217, 1214841869]
    
    # Use fallback values if needed
    if not bot_token:
        bot_token = "7952103795:AAGidRmrRZCpVMfO47rZyJfWE6pjisGuVj8"
        print("⚠️  WARNING: Using fallback bot token. Set BOT_TOKEN in .env file for production!")
    else:
        print(f"✅ Bot token loaded from .env file")
        
    if not admin_ids:
        admin_ids = [1858042217, 1214841869]
        print("⚠️  WARNING: Using fallback admin IDs. Set ADMIN_USER_IDS in .env file for production!")
    else:
        print(f"✅ {len(admin_ids)} admin user(s) loaded from .env file")
    
    # Create settings instance
    settings = WorkingSettings()
    settings.bot_token = bot_token
    settings.admin_user_ids = admin_ids
    
except Exception as e:
    print(f"⚠️  Error loading configuration: {e}")
    print("ℹ️  Using default configuration...")
    settings = WorkingSettings()
    # Set fallback values
    settings.bot_token = "7952103795:AAGidRmrRZCpVMfO47rZyJfWE6pjisGuVj8"
    settings.admin_user_ids = [1858042217, 1214841869]
