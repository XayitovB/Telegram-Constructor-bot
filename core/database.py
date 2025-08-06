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


@dataclass
class BotStats:
    """Bot statistics model."""
    total_users: int
    active_users: int
    banned_users: int
    admin_count: int
    messages_today: int
    messages_total: int
    new_users_today: int
    active_rate: float
    
    @classmethod
    def calculate_active_rate(cls, active: int, total: int) -> float:
        """Calculate activity rate percentage."""
        return (active / max(total, 1)) * 100


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
                            ban_reason TEXT NULL
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
                            notes TEXT,
                            FOREIGN KEY (user_id) REFERENCES users (user_id),
                            FOREIGN KEY (approved_by) REFERENCES users (user_id)
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
                    await db.execute("""
                        UPDATE users 
                        SET username = ?, first_name = ?, last_name = ?, 
                            last_activity = ?, message_count = message_count + 1
                        WHERE user_id = ?
                    """, (
                        user_data.get('username'),
                        user_data.get('first_name'),
                        user_data.get('last_name'),
                        datetime.now(),
                        user_data['user_id']
                    ))
                else:
                    # Insert new user
                    is_admin = user_data['user_id'] in settings.get_admin_ids()
                    await db.execute("""
                        INSERT INTO users 
                        (user_id, username, first_name, last_name, is_admin, message_count)
                        VALUES (?, ?, ?, ?, ?, 1)
                    """, (
                        user_data['user_id'],
                        user_data.get('username'),
                        user_data.get('first_name'),
                        user_data.get('last_name'),
                        is_admin
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
                        message_count=row_dict.get('message_count', 0)
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
                
                return [
                    User(
                        user_id=row['user_id'],
                        username=row['username'],
                        first_name=row['first_name'],
                        last_name=row['last_name'],
                        is_admin=bool(row['is_admin']),
                        is_active=bool(row['is_active']),
                        is_banned=bool(row['is_banned']),
                        join_date=datetime.fromisoformat(row['join_date']),
                        last_activity=datetime.fromisoformat(row['last_activity']),
                        message_count=row['message_count']
                    ) for row in rows
                ]
                
        except Exception as e:
            logger.error(f"Error getting users: {e}")
            return []
    
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
                
                return BotStats(
                    total_users=total_users,
                    active_users=active_users,
                    banned_users=banned_users,
                    admin_count=admin_count,
                    messages_today=messages_today,
                    messages_total=messages_total,
                    new_users_today=new_users_today,
                    active_rate=active_rate
                )
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return BotStats(0, 0, 0, 0, 0, 0, 0, 0.0)
    
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
        """Log admin action."""
        try:
            async with self.get_connection() as db:
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
            logger.error(f"Error getting bots for user {user_id}: {e}")
            return []
    
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


# Global database instance
db = DatabaseManager()
