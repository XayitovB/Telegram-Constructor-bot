"""
Professional database operations with models and comprehensive error handling.
"""

import asyncio
import aiosqlite
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass
from pathlib import Path
from contextlib import asynccontextmanager

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class User:
    """User model."""
    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True
    is_banned: bool = False
    join_date: datetime = None
    last_activity: datetime = None
    message_count: int = 0
    language: str = None
    ban_until: Optional[datetime] = None
    ban_reason: Optional[str] = None
    is_premium: bool = False
    premium_until: Optional[datetime] = None
    premium_type: Optional[str] = None
    
    def __post_init__(self):
        if self.join_date is None:
            self.join_date = datetime.now()
        if self.last_activity is None:
            self.last_activity = datetime.now()
    
    @property
    def full_name(self) -> str:
        """Get user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or "Unknown"
    
    @property
    def display_name(self) -> str:
        """Get user's display name."""
        if self.username:
            return f"@{self.username}"
        return self.full_name
    
    @property
    def is_ban_expired(self) -> bool:
        """Check if ban has expired."""
        if not self.is_banned or not self.ban_until:
            return False
        return datetime.now() > self.ban_until
    
    @property
    def effective_banned_status(self) -> bool:
        """Get effective banned status considering expiry."""
        if not self.is_banned:
            return False
        if self.ban_until and datetime.now() > self.ban_until:
            return False  # Ban expired
        return True
    
    @property
    def is_premium_expired(self) -> bool:
        """Check if premium has expired."""
        if not self.is_premium or not self.premium_until:
            return False
        return datetime.now() > self.premium_until
    
    @property
    def effective_premium_status(self) -> bool:
        """Get effective premium status considering expiry."""
        if not self.is_premium:
            return False
        if self.premium_until and datetime.now() > self.premium_until:
            return False  # Premium expired
        return True
    
    @property
    def premium_status_text(self) -> str:
        """Get premium status display text."""
        if self.effective_premium_status:
            days_left = None
            if self.premium_until:
                days_left = (self.premium_until - datetime.now()).days
            
            if days_left is not None and days_left > 0:
                return f"💎 Premium ({days_left} days left)"
            else:
                return "💎 Premium"
        return "⚪ Regular"
    
    @property
    def created_at(self) -> datetime:
        """Get user creation date (alias for join_date)."""
        return self.join_date
    
    @property
    def updated_at(self) -> datetime:
        """Get user last update date (alias for last_activity)."""
        return self.last_activity


@dataclass
class BotStats:
    """Bot statistics model."""
    total_users: int
    active_users: int
    banned_users: int
    admin_count: int
    premium_users: int
    active_users_week: int
    messages_today: int
    messages_total: int
    new_users_today: int
    active_rate: float
    premium_rate: float
    
    @classmethod
    def calculate_active_rate(cls, active: int, total: int) -> float:
        """Calculate activity rate percentage."""
        return (active / max(total, 1)) * 100
    
    @classmethod
    def calculate_premium_rate(cls, premium: int, total: int) -> float:
        """Calculate premium rate percentage."""
        return (premium / max(total, 1)) * 100


class DatabaseManager:
    """Professional database manager with connection pooling and error handling."""
    
    def __init__(self, db_path: Union[str, Path] = None):
        self.db_path = Path(db_path) if db_path else settings.database_path
        self._init_lock = asyncio.Lock()
        self._initialized = False
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection with proper error handling."""
        connection = None
        try:
            connection = await aiosqlite.connect(str(self.db_path))
            connection.row_factory = aiosqlite.Row
            await connection.execute("PRAGMA foreign_keys = ON")
            yield connection
        except Exception as e:
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if connection:
                await connection.close()
    
    async def initialize(self) -> None:
        """Initialize database with all required tables."""
        async with self._init_lock:
            if self._initialized:
                return
            
            logger.info("Initializing database...")
            
            try:
                async with self.get_connection() as db:
                    # Users table
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS users (
                            user_id INTEGER PRIMARY KEY,
                            username TEXT,
                            first_name TEXT,
                            last_name TEXT,
                            is_admin BOOLEAN DEFAULT FALSE,
                            is_active BOOLEAN DEFAULT TRUE,
                            is_banned BOOLEAN DEFAULT FALSE,
                            join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                            last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
                            message_count INTEGER DEFAULT 0,
                            ban_until DATETIME NULL,
                            ban_reason TEXT NULL,
                            language TEXT DEFAULT NULL
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
                    
                    # Broadcasts table
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS broadcasts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            admin_id INTEGER NOT NULL,
                            message_text TEXT NOT NULL,
                            sent_count INTEGER DEFAULT 0,
                            failed_count INTEGER DEFAULT 0,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (admin_id) REFERENCES users (user_id)
                        )
                    """)
                    
                    # Admin actions table
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS admin_actions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            admin_id INTEGER NOT NULL,
                            action_type TEXT NOT NULL,
                            target_user_id INTEGER,
                            details TEXT,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (admin_id) REFERENCES users (user_id),
                            FOREIGN KEY (target_user_id) REFERENCES users (user_id)
                        )
                    """)
                    
                    # Bot settings table
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS bot_settings (
                            key TEXT PRIMARY KEY,
                            value TEXT NOT NULL,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    
                    # User bots table
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS user_bots (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            bot_name TEXT NOT NULL,
                            bot_token TEXT NOT NULL,
                            bot_username TEXT,
                            bot_description TEXT,
                            status TEXT DEFAULT 'pending',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            approved_at DATETIME NULL,
                            approved_by INTEGER NULL,
                            expires_at DATETIME NULL,
                            time_extended_by INTEGER NULL,
                            notes TEXT,
                            FOREIGN KEY (user_id) REFERENCES users (user_id),
                            FOREIGN KEY (approved_by) REFERENCES users (user_id),
                            FOREIGN KEY (time_extended_by) REFERENCES users (user_id)
                        )
                    """)
                    
                    # Admin messages table
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS admin_messages (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            subject TEXT NOT NULL,
                            message TEXT NOT NULL,
                            status TEXT DEFAULT 'open',
                            priority TEXT DEFAULT 'normal',
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            responded_at DATETIME NULL,
                            responded_by INTEGER NULL,
                            admin_response TEXT,
                            FOREIGN KEY (user_id) REFERENCES users (user_id),
                            FOREIGN KEY (responded_by) REFERENCES users (user_id)
                        )
                    """)
                    
                    # Mandatory channels table
                    await db.execute("""
                        CREATE TABLE IF NOT EXISTS mandatory_channels (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            channel_id INTEGER NOT NULL UNIQUE,
                            channel_username TEXT,
                            channel_title TEXT NOT NULL,
                            channel_url TEXT NOT NULL,
                            is_active BOOLEAN DEFAULT TRUE,
                            added_by INTEGER NOT NULL,
                            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (added_by) REFERENCES users (user_id)
                        )
                    """)
                    
                    await db.commit()
                    
                    # Run migrations to add missing columns
                    await self._run_migrations(db)
                    
                self._initialized = True
                logger.success("Database initialized successfully")
                
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                raise
    
    async def _run_migrations(self, db) -> None:
        """Run database migrations to add missing columns."""
        try:
            # Check existing columns
            cursor = await db.execute("PRAGMA table_info(users)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]
            
            # Add missing columns
            if 'message_count' not in column_names:
                logger.info("Adding message_count column to users table")
                await db.execute("ALTER TABLE users ADD COLUMN message_count INTEGER DEFAULT 0")
            
            if 'is_active' not in column_names:
                logger.info("Adding is_active column to users table")
                await db.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
            
            if 'is_banned' not in column_names:
                logger.info("Adding is_banned column to users table")
                await db.execute("ALTER TABLE users ADD COLUMN is_banned BOOLEAN DEFAULT FALSE")
            
            if 'ban_until' not in column_names:
                logger.info("Adding ban_until column to users table")
                await db.execute("ALTER TABLE users ADD COLUMN ban_until DATETIME NULL")
            
            if 'ban_reason' not in column_names:
                logger.info("Adding ban_reason column to users table")
                await db.execute("ALTER TABLE users ADD COLUMN ban_reason TEXT NULL")
            
            if 'language' not in column_names:
                logger.info("Adding language column to users table")
                await db.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT NULL")
            
            # Premium user columns
            if 'is_premium' not in column_names:
                logger.info("Adding is_premium column to users table")
                await db.execute("ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT FALSE")
            
            if 'premium_until' not in column_names:
                logger.info("Adding premium_until column to users table")
                await db.execute("ALTER TABLE users ADD COLUMN premium_until DATETIME NULL")
            
            if 'premium_type' not in column_names:
                logger.info("Adding premium_type column to users table")
                await db.execute("ALTER TABLE users ADD COLUMN premium_type TEXT DEFAULT NULL")
            
            # Check existing columns for user_bots table
            cursor = await db.execute("PRAGMA table_info(user_bots)")
            bot_columns = await cursor.fetchall()
            bot_column_names = [col[1] for col in bot_columns] if bot_columns else []
            
            # Add missing bot expiration columns
            if 'expires_at' not in bot_column_names:
                logger.info("Adding expires_at column to user_bots table")
                await db.execute("ALTER TABLE user_bots ADD COLUMN expires_at DATETIME NULL")
            
            if 'time_extended_by' not in bot_column_names:
                logger.info("Adding time_extended_by column to user_bots table")
                await db.execute("ALTER TABLE user_bots ADD COLUMN time_extended_by INTEGER NULL")
            
            await db.commit()
            logger.info("Database migrations completed")
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            # Don't raise - continue with existing schema
    
    async def add_or_update_user(self, user_data: Dict[str, Any]) -> User:
        """Add or update user in database."""
        try:
            async with self.get_connection() as db:
                # Check if user exists
                cursor = await db.execute(
                    "SELECT * FROM users WHERE user_id = ?",
                    (user_data['user_id'],)
                )
                existing_user = await cursor.fetchone()
                
                if existing_user:
                    # Update existing user
                    update_query = """
                        UPDATE users 
                        SET username = ?, first_name = ?, last_name = ?, 
                            last_activity = ?
                    """
                    update_params = [
                        user_data.get('username'),
                        user_data.get('first_name'),
                        user_data.get('last_name'),
                        datetime.now(),
                    ]
                    
                    # Only increment message count if this isn't just a language update
                    if 'language' not in user_data or len(user_data) > 2:  # more than just user_id and language
                        update_query += ", message_count = message_count + 1"
                    
                    # Only update language if provided
                    if 'language' in user_data:
                        update_query += ", language = ?"
                        update_params.append(user_data['language'])
                    
                    update_query += " WHERE user_id = ?"
                    update_params.append(user_data['user_id'])
                    
                    await db.execute(update_query, update_params)
                else:
                    # Insert new user
                    is_admin = user_data['user_id'] in settings.get_admin_ids()
                    await db.execute("""
                        INSERT INTO users 
                        (user_id, username, first_name, last_name, is_admin, message_count, language)
                        VALUES (?, ?, ?, ?, ?, 1, ?)
                    """, (
                        user_data['user_id'],
                        user_data.get('username'),
                        user_data.get('first_name'),
                        user_data.get('last_name'),
                        is_admin,
                        user_data.get('language')
                    ))
                
                await db.commit()
                
                # Return updated user
                return await self.get_user(user_data['user_id'])
                
        except Exception as e:
            logger.error(f"Error adding/updating user {user_data.get('user_id')}: {e}")
            raise
    
    async def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "SELECT * FROM users WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                
                if row:
                    # Convert row to dict for safer access
                    row_dict = dict(row)
                    
                    return User(
                        user_id=row_dict['user_id'],
                        username=row_dict.get('username'),
                        first_name=row_dict.get('first_name'),
                        last_name=row_dict.get('last_name'),
                        is_admin=bool(row_dict.get('is_admin', False)),
                        is_active=bool(row_dict.get('is_active', True)),
                        is_banned=bool(row_dict.get('is_banned', False)),
                        join_date=datetime.fromisoformat(row_dict['join_date']),
                        last_activity=datetime.fromisoformat(row_dict['last_activity']),
                        message_count=row_dict.get('message_count', 0),
                        language=row_dict.get('language'),
                        ban_until=datetime.fromisoformat(row_dict['ban_until']) if row_dict.get('ban_until') else None,
                        ban_reason=row_dict.get('ban_reason'),
                        is_premium=bool(row_dict.get('is_premium', False)),
                        premium_until=datetime.fromisoformat(row_dict['premium_until']) if row_dict.get('premium_until') else None,
                        premium_type=row_dict.get('premium_type')
                    )
                return None
                
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def get_users(self, 
                       active_only: bool = False, 
                       admin_only: bool = False,
                       limit: int = None,
                       offset: int = 0) -> List[User]:
        """Get users with filtering options."""
        try:
            query = "SELECT * FROM users WHERE 1=1"
            params = []
            
            if active_only:
                query += " AND is_active = TRUE AND is_banned = FALSE"
            if admin_only:
                query += " AND is_admin = TRUE"
            
            query += " ORDER BY join_date DESC"
            
            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])
            
            async with self.get_connection() as db:
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                users_list = []
                for row in rows:
                    # Convert row to dict for safe access
                    row_dict = dict(row)
                    users_list.append(User(
                        user_id=row_dict['user_id'],
                        username=row_dict.get('username'),
                        first_name=row_dict.get('first_name'),
                        last_name=row_dict.get('last_name'),
                        is_admin=bool(row_dict.get('is_admin', False)),
                        is_active=bool(row_dict.get('is_active', True)),
                        is_banned=bool(row_dict.get('is_banned', False)),
                        join_date=datetime.fromisoformat(row_dict['join_date']),
                        last_activity=datetime.fromisoformat(row_dict['last_activity']),
                        message_count=row_dict.get('message_count', 0),
                        language=row_dict.get('language'),
                        ban_until=datetime.fromisoformat(row_dict['ban_until']) if row_dict.get('ban_until') else None,
                        ban_reason=row_dict.get('ban_reason'),
                        is_premium=bool(row_dict.get('is_premium', False)),
                        premium_until=datetime.fromisoformat(row_dict['premium_until']) if row_dict.get('premium_until') else None,
                        premium_type=row_dict.get('premium_type')
                    ))
                return users_list
                
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
    async def get_all_users(self) -> List[User]:
        """Get all users (alias for get_users with no filters)."""
        return await self.get_users()
    
    async def get_active_users_this_week(self) -> int:
        """Get count of users who were active in the past week."""
        try:
            async with self.get_connection() as db:
                # Users active in the last 7 days
                week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE last_activity >= ? AND is_active = TRUE AND is_banned = FALSE",
                    (week_ago,)
                )
                return (await cursor.fetchone())[0]
        except Exception as e:
            logger.error(f"Error getting active users this week: {e}")
            return 0
    
    async def get_active_users_today(self) -> int:
        """Get count of users who were active in the past 24 hours."""
        try:
            async with self.get_connection() as db:
                # Users active in the last 24 hours
                day_ago = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE last_activity >= ? AND is_active = TRUE AND is_banned = FALSE",
                    (day_ago,)
                )
                return (await cursor.fetchone())[0]
        except Exception as e:
            logger.error(f"Error getting active users today: {e}")
            return 0
    
    async def get_new_users_today(self) -> int:
        """Get count of new users who joined today."""
        try:
            async with self.get_connection() as db:
                # Users who joined today
                today = datetime.now().strftime('%Y-%m-%d')
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE DATE(join_date) = ?",
                    (today,)
                )
                return (await cursor.fetchone())[0]
        except Exception as e:
            logger.error(f"Error getting new users today: {e}")
            return 0
    
    async def get_daily_statistics(self) -> Dict[str, int]:
        """Get comprehensive daily statistics."""
        try:
            async with self.get_connection() as db:
                # Get all daily stats in one transaction for consistency
                today = datetime.now().strftime('%Y-%m-%d')
                day_ago = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
                
                # Active users in last 24 hours
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE last_activity >= ? AND is_active = TRUE AND is_banned = FALSE",
                    (day_ago,)
                )
                active_users_24h = (await cursor.fetchone())[0]
                
                # New users today
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE DATE(join_date) = ?",
                    (today,)
                )
                new_users_today = (await cursor.fetchone())[0]
                
                # Messages sent today
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM messages WHERE DATE(created_at) = ?",
                    (today,)
                )
                messages_today = (await cursor.fetchone())[0]
                
                # Active bots today (if applicable)
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM user_bots WHERE status = 'approved' AND DATE(created_at) = ?",
                    (today,)
                )
                new_bots_today = (await cursor.fetchone())[0]
                
                return {
                    'active_users_24h': active_users_24h,
                    'new_users_today': new_users_today,
                    'messages_today': messages_today,
                    'new_bots_today': new_bots_today
                }
                
        except Exception as e:
            logger.error(f"Error getting daily statistics: {e}")
            return {
                'active_users_24h': 0,
                'new_users_today': 0,
                'messages_today': 0,
                'new_bots_today': 0
            }
    
    async def get_statistics(self) -> BotStats:
        """Get comprehensive bot statistics."""
        try:
            async with self.get_connection() as db:
                # Total users
                cursor = await db.execute("SELECT COUNT(*) FROM users")
                total_users = (await cursor.fetchone())[0]
                
                # Active users
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE is_active = TRUE AND is_banned = FALSE"
                )
                active_users = (await cursor.fetchone())[0]
                
                # Banned users
                cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_banned = TRUE")
                banned_users = (await cursor.fetchone())[0]
                
                # Admin count
                cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_admin = TRUE")
                admin_count = (await cursor.fetchone())[0]
                
                # Premium users count (active premium only)
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE is_premium = TRUE AND (premium_until IS NULL OR premium_until > datetime('now'))"
                )
                premium_users = (await cursor.fetchone())[0]
                
                # Active users this week
                week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE last_activity >= ? AND is_active = TRUE AND is_banned = FALSE",
                    (week_ago,)
                )
                active_users_week = (await cursor.fetchone())[0]
                
                # Messages today
                today = datetime.now().strftime('%Y-%m-%d')
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM messages WHERE DATE(created_at) = ?",
                    (today,)
                )
                messages_today = (await cursor.fetchone())[0]
                
                # Total messages
                cursor = await db.execute("SELECT COUNT(*) FROM messages")
                messages_total = (await cursor.fetchone())[0]
                
                # New users today
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM users WHERE DATE(join_date) = ?",
                    (today,)
                )
                new_users_today = (await cursor.fetchone())[0]
                
                active_rate = BotStats.calculate_active_rate(active_users, total_users)
                premium_rate = BotStats.calculate_premium_rate(premium_users, total_users)
                
                return BotStats(
                    total_users=total_users,
                    active_users=active_users,
                    banned_users=banned_users,
                    admin_count=admin_count,
                    premium_users=premium_users,
                    active_users_week=active_users_week,
                    messages_today=messages_today,
                    messages_total=messages_total,
                    new_users_today=new_users_today,
                    active_rate=active_rate,
                    premium_rate=premium_rate
                )
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return BotStats(0, 0, 0, 0, 0, 0, 0, 0, 0, 0.0, 0.0)
    
    async def get_bot_stats(self) -> Dict[str, Any]:
        """Get bot statistics in dictionary format (alias for compatibility)."""
        try:
            stats = await self.get_statistics()
            return {
                'total_users': stats.total_users,
                'active_users': stats.active_users,
                'banned_users': stats.banned_users,
                'admin_count': stats.admin_count,
                'premium_users': stats.premium_users,
                'active_users_week': stats.active_users_week,
                'messages_today': stats.messages_today,
                'messages_total': stats.messages_total,
                'new_users_today': stats.new_users_today,
                'active_rate': stats.active_rate,
                'premium_rate': stats.premium_rate
            }
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            return {
                'total_users': 0,
                'active_users': 0,
                'banned_users': 0,
                'admin_count': 0,
                'premium_users': 0,
                'active_users_week': 0,
                'messages_today': 0,
                'messages_total': 0,
                'new_users_today': 0,
                'active_rate': 0.0,
                'premium_rate': 0.0
            }
    
    async def log_message(self, user_id: int, message_type: str, message_text: str = "") -> None:
        """Log user message."""
        try:
            async with self.get_connection() as db:
                await db.execute(
                    "INSERT INTO messages (user_id, message_type, message_text) VALUES (?, ?, ?)",
                    (user_id, message_type, message_text[:500])  # Limit text length
                )
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error logging message for user {user_id}: {e}")
    
    async def log_admin_action(self, admin_id: int, action_type: str, 
                              target_user_id: Optional[int] = None, 
                              details: str = "") -> None:
        """Log admin action with safe foreign key handling."""
        try:
            async with self.get_connection() as db:
                # Ensure admin user exists before logging action
                if admin_id != 0:  # Skip check for system actions (admin_id = 0)
                    cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (admin_id,))
                    admin_exists = await cursor.fetchone()
                    if not admin_exists:
                        logger.warning(f"Admin user {admin_id} not found, skipping action log")
                        return
                
                # Ensure target user exists if specified
                if target_user_id:
                    cursor = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (target_user_id,))
                    target_exists = await cursor.fetchone()
                    if not target_exists:
                        logger.warning(f"Target user {target_user_id} not found, setting to NULL")
                        target_user_id = None
                
                await db.execute("""
                    INSERT INTO admin_actions 
                    (admin_id, action_type, target_user_id, details) 
                    VALUES (?, ?, ?, ?)
                """, (admin_id, action_type, target_user_id, details))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error logging admin action: {e}")
    
    async def toggle_user_ban(self, user_id: int, banned: bool, reason: str = "") -> bool:
        """Ban or unban user."""
        try:
            async with self.get_connection() as db:
                ban_until = None
                if banned:
                    ban_until = datetime.now() + timedelta(hours=settings.security.ban_duration_hours)
                
                await db.execute("""
                    UPDATE users 
                    SET is_banned = ?, ban_until = ?, ban_reason = ?, is_active = ?
                    WHERE user_id = ?
                """, (banned, ban_until, reason, not banned, user_id))
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error toggling ban for user {user_id}: {e}")
            return False
    
    async def set_admin_status(self, user_id: int, is_admin: bool) -> bool:
        """Set user admin status."""
        try:
            async with self.get_connection() as db:
                await db.execute(
                    "UPDATE users SET is_admin = ? WHERE user_id = ?",
                    (is_admin, user_id)
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error setting admin status for user {user_id}: {e}")
            return False
    
    async def get_broadcast_users(self) -> List[int]:
        """Get user IDs for broadcasting."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "SELECT user_id FROM users WHERE is_active = TRUE AND is_banned = FALSE"
                )
                rows = await cursor.fetchall()
                return [row[0] for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting broadcast users: {e}")
            return []
    
    async def log_broadcast(self, admin_id: int, message_text: str, 
                           sent_count: int, failed_count: int) -> None:
        """Log broadcast operation."""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    INSERT INTO broadcasts 
                    (admin_id, message_text, sent_count, failed_count) 
                    VALUES (?, ?, ?, ?)
                """, (admin_id, message_text[:1000], sent_count, failed_count))
                await db.commit()
                
        except Exception as e:
            logger.error(f"Error logging broadcast: {e}")
    
    # Bot Management Methods
    
    async def add_user_bot(self, user_id: int, bot_name: str, bot_token: str, 
                          bot_description: str = "") -> int:
        """Add new bot request from user."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    INSERT INTO user_bots 
                    (user_id, bot_name, bot_token, bot_description) 
                    VALUES (?, ?, ?, ?)
                """, (user_id, bot_name, bot_token, bot_description))
                await db.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error adding bot for user {user_id}: {e}")
            return None
    
    async def get_user_bots(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all bots for a specific user."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    SELECT * FROM user_bots 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC
                """, (user_id,))
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting user bots: {e}")
            return []
    
    async def delete_user_bot(self, bot_id: int, user_id: int) -> bool:
        """Delete a user bot (only if owned by the user)."""
        try:
            async with self.get_connection() as db:
                # First check if the user owns this bot
                cursor = await db.execute(
                    "SELECT user_id FROM user_bots WHERE id = ?",
                    (bot_id,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    logger.warning(f"Bot {bot_id} not found")
                    return False
                
                if row[0] != user_id:
                    logger.warning(f"User {user_id} attempted to delete bot {bot_id} owned by {row[0]}")
                    return False
                
                # Delete the bot
                await db.execute(
                    "DELETE FROM user_bots WHERE id = ? AND user_id = ?",
                    (bot_id, user_id)
                )
                await db.commit()
                
                logger.info(f"Bot {bot_id} deleted by user {user_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting user bot {bot_id}: {e}")
            return False
    
    async def get_pending_bots(self) -> List[Dict[str, Any]]:
        """Get all pending bot requests for admin review."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    SELECT ub.*, u.first_name, u.last_name, u.username
                    FROM user_bots ub
                    JOIN users u ON ub.user_id = u.user_id
                    WHERE ub.status = 'pending'
                    ORDER BY ub.created_at ASC
                """)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting pending bots: {e}")
            return []
    
    async def approve_bot(self, bot_id: int, admin_id: int, notes: str = "") -> bool:
        """Approve a bot request."""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    UPDATE user_bots 
                    SET status = 'approved', approved_at = ?, approved_by = ?, notes = ?
                    WHERE id = ?
                """, (datetime.now(), admin_id, notes, bot_id))
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error approving bot {bot_id}: {e}")
            return False
    
    async def reject_bot(self, bot_id: int, admin_id: int, notes: str = "") -> bool:
        """Reject a bot request."""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    UPDATE user_bots 
                    SET status = 'rejected', approved_at = ?, approved_by = ?, notes = ?
                    WHERE id = ?
                """, (datetime.now(), admin_id, notes, bot_id))
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error rejecting bot {bot_id}: {e}")
            return False
    
    # Bot Expiration Management Methods
    
    async def set_bot_expiration(self, bot_id: int, expires_at: datetime, 
                                admin_id: int = None) -> bool:
        """Set bot expiration date."""
        try:
            async with self.get_connection() as db:
                if admin_id:
                    await db.execute("""
                        UPDATE user_bots 
                        SET expires_at = ?, time_extended_by = ?
                        WHERE id = ?
                    """, (expires_at, admin_id, bot_id))
                else:
                    await db.execute("""
                        UPDATE user_bots 
                        SET expires_at = ?
                        WHERE id = ?
                    """, (expires_at, bot_id))
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error setting bot expiration for bot {bot_id}: {e}")
            return False
    
    async def extend_bot_time(self, bot_id: int, days: int, admin_id: int) -> bool:
        """Extend bot working time by specified days."""
        try:
            async with self.get_connection() as db:
                # Get current expiration
                cursor = await db.execute(
                    "SELECT expires_at FROM user_bots WHERE id = ?",
                    (bot_id,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return False
                
                current_expires = row[0]
                if current_expires:
                    # Extend from current expiry date
                    current_expires = datetime.fromisoformat(current_expires)
                    new_expires = current_expires + timedelta(days=days)
                else:
                    # Set expiration from now if not set
                    new_expires = datetime.now() + timedelta(days=days)
                
                await db.execute("""
                    UPDATE user_bots 
                    SET expires_at = ?, time_extended_by = ?
                    WHERE id = ?
                """, (new_expires, admin_id, bot_id))
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error extending bot time for bot {bot_id}: {e}")
            return False
    
    async def get_expired_bots(self) -> List[Dict[str, Any]]:
        """Get all bots that have expired."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    SELECT * FROM user_bots 
                    WHERE expires_at IS NOT NULL 
                    AND expires_at < datetime('now') 
                    AND status = 'approved'
                    ORDER BY expires_at ASC
                """)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting expired bots: {e}")
            return []
    
    async def get_expiring_bots(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get bots that will expire within specified hours."""
        try:
            async with self.get_connection() as db:
                expiry_threshold = datetime.now() + timedelta(hours=hours)
                cursor = await db.execute("""
                    SELECT * FROM user_bots 
                    WHERE expires_at IS NOT NULL 
                    AND expires_at > datetime('now')
                    AND expires_at < ?
                    AND status = 'approved'
                    ORDER BY expires_at ASC
                """, (expiry_threshold,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting expiring bots: {e}")
            return []
    
    async def check_bot_expired(self, bot_id: int) -> bool:
        """Check if a specific bot has expired."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    SELECT expires_at FROM user_bots 
                    WHERE id = ? AND expires_at IS NOT NULL
                """, (bot_id,))
                row = await cursor.fetchone()
                
                if not row or not row[0]:
                    return False  # No expiration set
                
                expires_at = datetime.fromisoformat(row[0])
                return datetime.now() > expires_at
                
        except Exception as e:
            logger.error(f"Error checking bot expiration for bot {bot_id}: {e}")
            return False
    
    async def get_bot_time_left(self, bot_id: int) -> Optional[timedelta]:
        """Get remaining time for a bot."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    SELECT expires_at FROM user_bots 
                    WHERE id = ? AND expires_at IS NOT NULL
                """, (bot_id,))
                row = await cursor.fetchone()
                
                if not row or not row[0]:
                    return None  # No expiration set
                
                expires_at = datetime.fromisoformat(row[0])
                time_left = expires_at - datetime.now()
                return time_left if time_left.total_seconds() > 0 else timedelta(0)
                
        except Exception as e:
            logger.error(f"Error getting time left for bot {bot_id}: {e}")
            return None
    
    async def get_all_user_bots(self) -> List[Dict[str, Any]]:
        """Get all user bots from database for admin management."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    SELECT ub.*, u.username as owner_username, u.first_name as owner_first_name,
                           u.last_name as owner_last_name
                    FROM user_bots ub
                    LEFT JOIN users u ON ub.user_id = u.user_id
                    ORDER BY ub.created_at DESC
                """)
                
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting all user bots: {e}")
            return []
    
    async def get_user_bot(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific user bot by ID."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "SELECT * FROM user_bots WHERE id = ?",
                    (bot_id,)
                )
                row = await cursor.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Error getting user bot {bot_id}: {e}")
            return None
    
    # Admin Messages Methods
    
    async def create_admin_message(self, user_id: int, subject: str, message: str,
                                  priority: str = "normal") -> int:
        """Create a new message to admin."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    INSERT INTO admin_messages 
                    (user_id, subject, message, priority) 
                    VALUES (?, ?, ?, ?)
                """, (user_id, subject, message, priority))
                await db.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error creating admin message for user {user_id}: {e}")
            return None
    
    async def get_user_messages(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all messages from a specific user."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    SELECT * FROM admin_messages 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC
                """, (user_id,))
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting messages for user {user_id}: {e}")
            return []
    
    async def get_open_messages(self) -> List[Dict[str, Any]]:
        """Get all open admin messages."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    SELECT am.*, u.first_name, u.last_name, u.username
                    FROM admin_messages am
                    JOIN users u ON am.user_id = u.user_id
                    WHERE am.status = 'open'
                    ORDER BY 
                        CASE am.priority 
                            WHEN 'urgent' THEN 1 
                            WHEN 'high' THEN 2 
                            WHEN 'normal' THEN 3 
                            WHEN 'low' THEN 4 
                        END,
                        am.created_at ASC
                """)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting open messages: {e}")
            return []
    
    async def respond_to_message(self, message_id: int, admin_id: int, 
                                response: str) -> bool:
        """Respond to an admin message."""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    UPDATE admin_messages 
                    SET status = 'responded', responded_at = ?, responded_by = ?, 
                        admin_response = ?
                    WHERE id = ?
                """, (datetime.now(), admin_id, response, message_id))
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error responding to message {message_id}: {e}")
            return False
    
    # Premium User Management Methods
    
    async def set_premium_status(self, user_id: int, is_premium: bool, 
                                premium_type: str = None, days: int = 30) -> bool:
        """Set user premium status."""
        try:
            async with self.get_connection() as db:
                premium_until = None
                if is_premium:
                    premium_until = datetime.now() + timedelta(days=days)
                
                await db.execute(
                    "UPDATE users SET is_premium = ?, premium_until = ?, premium_type = ? WHERE user_id = ?",
                    (is_premium, premium_until, premium_type, user_id)
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error setting premium status for user {user_id}: {e}")
            return False
    
    async def extend_premium(self, user_id: int, days: int) -> bool:
        """Extend premium subscription by additional days."""
        try:
            async with self.get_connection() as db:
                # Get current premium status
                cursor = await db.execute(
                    "SELECT premium_until FROM users WHERE user_id = ?",
                    (user_id,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return False
                
                current_until = row[0]
                if current_until:
                    # Extend from current expiry date
                    current_until = datetime.fromisoformat(current_until)
                    new_until = current_until + timedelta(days=days)
                else:
                    # Start premium from now
                    new_until = datetime.now() + timedelta(days=days)
                
                await db.execute(
                    "UPDATE users SET is_premium = TRUE, premium_until = ? WHERE user_id = ?",
                    (new_until, user_id)
                )
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error extending premium for user {user_id}: {e}")
            return False
    
    async def get_premium_users(self, active_only: bool = True) -> List[User]:
        """Get all premium users."""
        try:
            query = "SELECT * FROM users WHERE is_premium = TRUE"
            if active_only:
                query += " AND (premium_until IS NULL OR premium_until > datetime('now'))"
            query += " ORDER BY premium_until DESC"
            
            async with self.get_connection() as db:
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                
                users_list = []
                for row in rows:
                    row_dict = dict(row)
                    users_list.append(User(
                        user_id=row_dict['user_id'],
                        username=row_dict.get('username'),
                        first_name=row_dict.get('first_name'),
                        last_name=row_dict.get('last_name'),
                        is_admin=bool(row_dict.get('is_admin', False)),
                        is_active=bool(row_dict.get('is_active', True)),
                        is_banned=bool(row_dict.get('is_banned', False)),
                        join_date=datetime.fromisoformat(row_dict['join_date']),
                        last_activity=datetime.fromisoformat(row_dict['last_activity']),
                        message_count=row_dict.get('message_count', 0),
                        language=row_dict.get('language'),
                        ban_until=datetime.fromisoformat(row_dict['ban_until']) if row_dict.get('ban_until') else None,
                        ban_reason=row_dict.get('ban_reason'),
                        is_premium=bool(row_dict.get('is_premium', False)),
                        premium_until=datetime.fromisoformat(row_dict['premium_until']) if row_dict.get('premium_until') else None,
                        premium_type=row_dict.get('premium_type')
                    ))
                return users_list
                
        except Exception as e:
            logger.error(f"Error getting premium users: {e}")
            return []
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "SELECT * FROM users WHERE username = ? COLLATE NOCASE",
                    (username,)
                )
                row = await cursor.fetchone()
                
                if row:
                    # Convert row to dict for safer access
                    row_dict = dict(row)
                    
                    return User(
                        user_id=row_dict['user_id'],
                        username=row_dict.get('username'),
                        first_name=row_dict.get('first_name'),
                        last_name=row_dict.get('last_name'),
                        is_admin=bool(row_dict.get('is_admin', False)),
                        is_active=bool(row_dict.get('is_active', True)),
                        is_banned=bool(row_dict.get('is_banned', False)),
                        join_date=datetime.fromisoformat(row_dict['join_date']),
                        last_activity=datetime.fromisoformat(row_dict['last_activity']),
                        message_count=row_dict.get('message_count', 0),
                        language=row_dict.get('language'),
                        ban_until=datetime.fromisoformat(row_dict['ban_until']) if row_dict.get('ban_until') else None,
                        ban_reason=row_dict.get('ban_reason'),
                        is_premium=bool(row_dict.get('is_premium', False)),
                        premium_until=datetime.fromisoformat(row_dict['premium_until']) if row_dict.get('premium_until') else None,
                        premium_type=row_dict.get('premium_type')
                    )
                return None
                
        except Exception as e:
            logger.error(f"Error getting user by username {username}: {e}")
            return None
    
    async def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get detailed statistics for a specific user."""
        try:
            async with self.get_connection() as db:
                # Get total messages sent by this user
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM messages WHERE user_id = ?",
                    (user_id,)
                )
                total_messages = (await cursor.fetchone())[0]
                
                # Get total bots created by this user
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM user_bots WHERE user_id = ?",
                    (user_id,)
                )
                total_bots = (await cursor.fetchone())[0]
                
                # Get active bots (approved status)
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM user_bots WHERE user_id = ? AND status = 'approved'",
                    (user_id,)
                )
                active_bots = (await cursor.fetchone())[0]
                
                # Get pending bots
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM user_bots WHERE user_id = ? AND status = 'pending'",
                    (user_id,)
                )
                pending_bots = (await cursor.fetchone())[0]
                
                # Get messages sent in the last 7 days
                week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM messages WHERE user_id = ? AND created_at >= ?",
                    (user_id, week_ago)
                )
                messages_week = (await cursor.fetchone())[0]
                
                # Get messages sent today
                today = datetime.now().strftime('%Y-%m-%d')
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM messages WHERE user_id = ? AND DATE(created_at) = ?",
                    (user_id, today)
                )
                messages_today = (await cursor.fetchone())[0]
                
                # Get admin actions performed by this user (if admin)
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM admin_actions WHERE admin_id = ?",
                    (user_id,)
                )
                admin_actions = (await cursor.fetchone())[0]
                
                return {
                    'total_messages': total_messages,
                    'total_bots': total_bots,
                    'active_bots': active_bots,
                    'pending_bots': pending_bots,
                    'messages_week': messages_week,
                    'messages_today': messages_today,
                    'admin_actions': admin_actions
                }
                
        except Exception as e:
            logger.error(f"Error getting user statistics for user {user_id}: {e}")
            return {
                'total_messages': 0,
                'total_bots': 0,
                'active_bots': 0,
                'pending_bots': 0,
                'messages_week': 0,
                'messages_today': 0,
                'admin_actions': 0
            }
    
    # Mandatory Channels Management Methods
    
    async def add_mandatory_channel(self, channel_id: int, channel_username: str,
                                   channel_title: str, channel_url: str, 
                                   added_by: int) -> int:
        """Add a new mandatory channel."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute("""
                    INSERT INTO mandatory_channels 
                    (channel_id, channel_username, channel_title, channel_url, added_by) 
                    VALUES (?, ?, ?, ?, ?)
                """, (channel_id, channel_username, channel_title, channel_url, added_by))
                await db.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Error adding mandatory channel {channel_id}: {e}")
            return None
    
    async def get_mandatory_channels(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """Get all mandatory channels."""
        try:
            query = "SELECT * FROM mandatory_channels"
            if active_only:
                query += " WHERE is_active = TRUE"
            query += " ORDER BY created_at DESC"
            
            async with self.get_connection() as db:
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error getting mandatory channels: {e}")
            return []
    
    async def update_mandatory_channel(self, channel_id: int, channel_username: str = None,
                                      channel_title: str = None, channel_url: str = None,
                                      is_active: bool = None) -> bool:
        """Update mandatory channel information."""
        try:
            async with self.get_connection() as db:
                updates = []
                params = []
                
                if channel_username is not None:
                    updates.append("channel_username = ?")
                    params.append(channel_username)
                
                if channel_title is not None:
                    updates.append("channel_title = ?")
                    params.append(channel_title)
                
                if channel_url is not None:
                    updates.append("channel_url = ?")
                    params.append(channel_url)
                
                if is_active is not None:
                    updates.append("is_active = ?")
                    params.append(is_active)
                
                updates.append("updated_at = ?")
                params.append(datetime.now())
                
                if not updates:
                    return False
                
                query = f"UPDATE mandatory_channels SET {', '.join(updates)} WHERE channel_id = ?"
                params.append(channel_id)
                
                await db.execute(query, params)
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating mandatory channel {channel_id}: {e}")
            return False
    
    async def delete_mandatory_channel(self, channel_id: int) -> bool:
        """Delete a mandatory channel."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "DELETE FROM mandatory_channels WHERE channel_id = ?",
                    (channel_id,)
                )
                await db.commit()
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"Error deleting mandatory channel {channel_id}: {e}")
            return False
    
    async def remove_mandatory_channel(self, channel_id: int) -> bool:
        """Remove a mandatory channel (alias for delete_mandatory_channel)."""
        return await self.delete_mandatory_channel(channel_id)
    
    async def get_mandatory_channel(self, channel_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific mandatory channel."""
        try:
            async with self.get_connection() as db:
                cursor = await db.execute(
                    "SELECT * FROM mandatory_channels WHERE channel_id = ?",
                    (channel_id,)
                )
                row = await cursor.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"Error getting mandatory channel {channel_id}: {e}")
            return None
    
    async def toggle_channel_status(self, channel_id: int, is_active: bool) -> bool:
        """Toggle channel active status."""
        try:
            async with self.get_connection() as db:
                await db.execute("""
                    UPDATE mandatory_channels 
                    SET is_active = ?, updated_at = ?
                    WHERE channel_id = ?
                """, (is_active, datetime.now(), channel_id))
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error toggling channel status {channel_id}: {e}")
            return False
    
    async def fetch_channel_title_from_invite_link(self, invite_url: str, bot_token: str) -> Optional[str]:
        """Fetch actual channel title from invite link using Telegram API."""
        from aiogram import Bot
        from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
        
        try:
            # Only process invite links
            if not invite_url.startswith("https://t.me/+"):
                return None
            
            # Create bot instance for fetching channel info
            check_bot = Bot(token=bot_token)
            
            try:
                # Try to get chat info from the invite link
                # Extract invite hash from URL
                invite_hash = invite_url.replace("https://t.me/+", "")
                
                # Try using get_chat with the full URL first
                try:
                    chat_info = await check_bot.get_chat(invite_url)
                    if hasattr(chat_info, 'title'):
                        return chat_info.title
                except:
                    # If that fails, try alternative methods
                    pass
                
                # Alternative: Try to get invite link info (if available in the API)
                # Note: This might not work for all bots depending on permissions
                try:
                    # Some bots might be able to get invite link info
                    chat_info = await check_bot.get_chat(f"@{invite_hash}")
                    if hasattr(chat_info, 'title'):
                        return chat_info.title
                except:
                    pass
                    
            except (TelegramBadRequest, TelegramForbiddenError) as e:
                logger.debug(f"Could not fetch channel info from invite link {invite_url}: {e}")
            except Exception as e:
                logger.warning(f"Error fetching channel title from {invite_url}: {e}")
            finally:
                # Close the check bot
                try:
                    await check_bot.session.close()
                except:
                    pass
            
            return None
            
        except Exception as e:
            logger.error(f"Error in fetch_channel_title_from_invite_link: {e}")
            return None
    
    async def enhance_channel_titles(self, channels: List[Dict], bot_token: str) -> List[Dict]:
        """Enhance channel information by fetching real titles for private channels."""
        enhanced_channels = []
        
        for channel in channels:
            enhanced_channel = channel.copy()
            
            # Check if this is a private channel with an invite link
            channel_url = channel.get('channel_url', '')
            if channel_url.startswith('https://t.me/+'):
                # Try to fetch the real channel title
                real_title = await self.fetch_channel_title_from_invite_link(channel_url, bot_token)
                if real_title:
                    enhanced_channel['channel_title'] = real_title
                    logger.info(f"Enhanced channel title for {channel_url}: {real_title}")
                else:
                    # Keep the original title but log that we couldn't enhance it
                    logger.debug(f"Could not enhance title for private channel: {channel_url}")
            
            enhanced_channels.append(enhanced_channel)
        
        return enhanced_channels

    async def check_user_channel_membership(self, user_id: int, bot_token: str) -> Dict[str, Any]:
        """Check if user has joined all mandatory channels."""
        from aiogram import Bot
        from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
        
        try:
            # Get all active mandatory channels
            channels = await self.get_mandatory_channels(active_only=True)
            if not channels:
                return {'all_joined': True, 'missing_channels': [], 'errors': []}
            
            # Create bot instance for checking membership
            check_bot = Bot(token=bot_token)
            
            missing_channels = []
            errors = []
            
            for channel in channels:
                try:
                    # Check membership using channel ID or username
                    channel_identifier = channel.get('channel_id')
                    if not channel_identifier:
                        channel_username = channel.get('channel_username')
                        if channel_username:
                            channel_identifier = f"@{channel_username}"
                    
                    if not channel_identifier:
                        logger.warning(f"No valid identifier for channel {channel}")
                        continue
                    
                    # Get chat member info
                    member = await check_bot.get_chat_member(channel_identifier, user_id)
                    
                    # Check if user is NOT a valid member
                    # Valid statuses: 'member', 'administrator', 'creator', 'restricted'
                    # Invalid statuses: 'left', 'kicked'
                    if member.status in ['left', 'kicked']:
                        # User is not a member - add to missing channels
                        missing_channel = {
                            'channel_id': channel.get('channel_id'),
                            'channel_title': channel.get('channel_title'),
                            'channel_username': channel.get('channel_username'),
                            'channel_url': channel.get('channel_url')
                        }
                        
                        # Try to enhance the title for private channels
                        if channel.get('channel_url', '').startswith('https://t.me/+'):
                            real_title = await self.fetch_channel_title_from_invite_link(
                                channel.get('channel_url'), bot_token
                            )
                            if real_title:
                                missing_channel['channel_title'] = real_title
                        
                        missing_channels.append(missing_channel)
                        logger.debug(f"User {user_id} not in channel {channel_identifier}: status={member.status}")
                    else:
                        # User is a valid member (member, administrator, creator, or restricted)
                        logger.debug(f"User {user_id} is a valid member of channel {channel_identifier}: status={member.status}")
                    
                except (TelegramBadRequest, TelegramForbiddenError) as e:
                    # User not found in channel or channel not accessible
                    # This happens when user is not a member or channel is private/inaccessible
                    missing_channel = {
                        'channel_id': channel.get('channel_id'),
                        'channel_title': channel.get('channel_title'),
                        'channel_username': channel.get('channel_username'),
                        'channel_url': channel.get('channel_url')
                    }
                    
                    # Try to enhance the title for private channels
                    if channel.get('channel_url', '').startswith('https://t.me/+'):
                        real_title = await self.fetch_channel_title_from_invite_link(
                            channel.get('channel_url'), bot_token
                        )
                        if real_title:
                            missing_channel['channel_title'] = real_title
                    
                    missing_channels.append(missing_channel)
                    logger.debug(f"User {user_id} not in channel {channel_identifier}: {e}")
                    
                except Exception as e:
                    error_msg = f"Error checking channel {channel_identifier}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            # Close the check bot
            try:
                await check_bot.session.close()
            except:
                pass
            
            return {
                'all_joined': len(missing_channels) == 0,
                'missing_channels': missing_channels,
                'errors': errors,
                'total_channels': len(channels),
                'missing_count': len(missing_channels)
            }
            
        except Exception as e:
            logger.error(f"Error checking user channel membership for user {user_id}: {e}")
            return {
                'all_joined': True,  # Allow access on error to prevent blocking
                'missing_channels': [],
                'errors': [str(e)],
                'total_channels': 0,
                'missing_count': 0
            }
    
    async def get_channel_join_buttons(self, missing_channels: List[Dict]) -> List[List[Dict]]:
        """Generate channel join buttons for inline keyboard."""
        buttons = []
        
        for channel in missing_channels:
            channel_title = channel.get('channel_title', 'Unknown Channel')
            channel_url = channel.get('channel_url')
            channel_username = channel.get('channel_username')
            
            # Create button URL
            if channel_url:
                button_url = channel_url
            elif channel_username:
                button_url = f"https://t.me/{channel_username}"
            else:
                continue  # Skip if no valid URL
            
            # Truncate long titles for button display
            if len(channel_title) > 30:
                display_title = channel_title[:27] + "..."
            else:
                display_title = channel_title
            
            buttons.append([{
                'text': f"📺 {display_title}",
                'url': button_url
            }])
        
        return buttons
    
    async def close(self) -> None:
        """Close database connections and cleanup."""
        try:
            # Since we use context managers, connections are automatically closed
            # This method is here for compatibility and future cleanup needs
            logger.info("Database manager cleanup completed")
            self._initialized = False
        except Exception as e:
            logger.error(f"Error during database cleanup: {e}")


# Global database instance
db = DatabaseManager()
