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
    """Bot configuration settings."""
    name: str = Field(default="Professional Bot", description="Bot display name")
    description: str = Field(default="A professional Telegram bot with admin features")
    users_per_page: int = Field(default=5, ge=1, le=20, description="Users per page in lists")
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
    bot_token: str = Field(..., description="Telegram bot token")
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
        "case_sensitive": False
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
        if not v or len(v) < 10:
            raise ValueError("Invalid bot token")
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
settings = Settings()
