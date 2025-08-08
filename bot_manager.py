"""
Bot Manager - Handles creation, validation, and management of user bots
"""

import asyncio
import aiohttp
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

from core.config import settings
from core.database import db
from core.logging import get_logger
from user_bot_template import create_user_bot, stop_user_bot, running_bots

logger = get_logger(__name__)


@dataclass
class BotInfo:
    """Bot information from Telegram API."""
    id: int
    username: str
    first_name: str
    can_join_groups: bool
    can_read_all_group_messages: bool
    supports_inline_queries: bool
    is_valid: bool = True
    error_message: str = None


class BotManager:
    """Manages user bot creation, validation, and lifecycle."""
    
    def __init__(self):
        self.validation_timeout = 10  # seconds
        self.max_bots_per_user = 3  # Maximum bots per user
        
    async def validate_bot_token(self, token: str) -> BotInfo:
        """
        Validate bot token with Telegram API.
        Returns BotInfo with validation results.
        """
        try:
            # Create temporary bot instance to test token
            test_bot = Bot(token=token)
            
            # Get bot info from Telegram
            bot_user = await asyncio.wait_for(
                test_bot.get_me(), 
                timeout=self.validation_timeout
            )
            
            await test_bot.session.close()
            
            return BotInfo(
                id=bot_user.id,
                username=bot_user.username,
                first_name=bot_user.first_name,
                can_join_groups=bot_user.can_join_groups,
                can_read_all_group_messages=bot_user.can_read_all_group_messages,
                supports_inline_queries=bot_user.supports_inline_queries,
                is_valid=True
            )
            
        except asyncio.TimeoutError:
            return BotInfo(
                id=0, username="", first_name="", 
                can_join_groups=False, can_read_all_group_messages=False, 
                supports_inline_queries=False, is_valid=False,
                error_message="Token validation timed out"
            )
        except TelegramAPIError as e:
            return BotInfo(
                id=0, username="", first_name="", 
                can_join_groups=False, can_read_all_group_messages=False, 
                supports_inline_queries=False, is_valid=False,
                error_message=f"Invalid token: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Bot token validation error: {e}")
            return BotInfo(
                id=0, username="", first_name="", 
                can_join_groups=False, can_read_all_group_messages=False, 
                supports_inline_queries=False, is_valid=False,
                error_message=f"Validation failed: {str(e)}"
            )
    
    async def check_bot_exists(self, bot_id: int) -> bool:
        """Check if bot already exists in database."""
        try:
            async with db.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM user_bots WHERE bot_username = ? OR bot_token LIKE ?",
                    (str(bot_id), f"%{bot_id}:%")
                )
                count = (await cursor.fetchone())[0]
                return count > 0
        except Exception as e:
            logger.error(f"Error checking bot existence: {e}")
            return False
    
    async def get_user_bot_count(self, user_id: int) -> int:
        """Get number of bots created by user."""
        try:
            async with db.get_connection() as conn:
                cursor = await conn.execute(
                    "SELECT COUNT(*) FROM user_bots WHERE user_id = ? AND status != 'rejected'",
                    (user_id,)
                )
                count = (await cursor.fetchone())[0]
                return count
        except Exception as e:
            logger.error(f"Error getting user bot count: {e}")
            return 0
    
    async def create_bot_request(self, user_id: int, bot_name: str, bot_token: str, 
                               bot_info: BotInfo) -> Tuple[bool, str, int]:
        """
        Create a bot creation request.
        Returns: (success, message, bot_id)
        """
        try:
            # Check if user has reached bot limit
            user_bot_count = await self.get_user_bot_count(user_id)
            if user_bot_count >= self.max_bots_per_user:
                return False, f"Siz maksimal {self.max_bots_per_user} ta bot yarata olasiz!", 0
            
            # Check if bot already exists
            if await self.check_bot_exists(bot_info.id):
                return False, "Bu bot allaqachon ro'yxatdan o'tgan!", 0
            
            # Create bot request in database
            bot_id = await db.add_user_bot(
                user_id=user_id,
                bot_name=bot_name,
                bot_token=bot_token,
                bot_description=f"Bot: @{bot_info.username}"
            )
            
            if not bot_id:
                return False, "Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.", 0
            
            # Update bot with additional info
            await self._update_bot_info(bot_id, bot_info)
            
            # Auto-approve and start the bot
            success = await self.approve_and_start_bot(bot_id, user_id, "Auto-approved")
            
            if success:
                return True, "✅ Bot muvaffaqiyatli yaratildi va ishga tushirildi!", bot_id
            else:
                return False, "Bot yaratildi, lekin ishga tushirishda xatolik yuz berdi.", bot_id
            
        except Exception as e:
            logger.error(f"Error creating bot request: {e}")
            return False, "Xatolik yuz berdi. Iltimos qaytadan urinib ko'ring.", 0
    
    async def _update_bot_info(self, bot_id: int, bot_info: BotInfo):
        """Update bot with additional information from Telegram."""
        try:
            async with db.get_connection() as conn:
                await conn.execute("""
                    UPDATE user_bots 
                    SET bot_username = ?
                    WHERE id = ?
                """, (bot_info.username, bot_id))
                await conn.commit()
        except Exception as e:
            logger.error(f"Error updating bot info: {e}")
    
    async def approve_and_start_bot(self, bot_id: int, admin_id: int, notes: str = "") -> bool:
        """Approve a bot request and start the bot."""
        try:
            # Get bot details
            bot_data = await self._get_bot_data(bot_id)
            if not bot_data:
                return False
            
            # Approve in database
            success = await db.approve_bot(bot_id, admin_id, notes)
            if not success:
                return False
            
            # Start the user bot
            await self._start_user_bot(bot_data)
            
            logger.info(f"Bot {bot_id} approved and started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error approving and starting bot {bot_id}: {e}")
            return False
    
    async def _get_bot_data(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """Get bot data from database."""
        try:
            async with db.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT * FROM user_bots WHERE id = ?
                """, (bot_id,))
                row = await cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Error getting bot data: {e}")
            return None
    
    async def _start_user_bot(self, bot_data: Dict[str, Any]):
        """Start a user bot instance."""
        try:
            bot_id = bot_data['id']
            
            # Don't start if already running
            if bot_id in running_bots:
                logger.info(f"Bot {bot_id} is already running")
                return
            
            # Create and start the user bot
            user_bot = await create_user_bot(
                bot_token=bot_data['bot_token'],
                bot_id=bot_id,
                owner_id=bot_data['user_id'],
                bot_name=bot_data['bot_name']
            )
            
            logger.info(f"User bot {bot_id} ({bot_data['bot_name']}) started successfully")
            
        except Exception as e:
            logger.error(f"Error starting user bot: {e}")
            raise
    
    async def stop_bot(self, bot_id: int) -> bool:
        """Stop a running user bot."""
        try:
            success = await stop_user_bot(bot_id)
            if success:
                # Update status in database
                async with db.get_connection() as conn:
                    await conn.execute("""
                        UPDATE user_bots 
                        SET status = 'stopped' 
                        WHERE id = ?
                    """, (bot_id,))
                    await conn.commit()
                    
                logger.info(f"User bot {bot_id} stopped successfully")
            return success
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {e}")
            return False
    
    async def restart_bot(self, bot_id: int) -> bool:
        """Restart a user bot."""
        try:
            # Stop if running
            if bot_id in running_bots:
                await stop_user_bot(bot_id)
            
            # Get bot data and restart
            bot_data = await self._get_bot_data(bot_id)
            if bot_data and bot_data['status'] == 'approved':
                await self._start_user_bot(bot_data)
                
                # Update status
                async with db.get_connection() as conn:
                    await conn.execute("""
                        UPDATE user_bots 
                        SET status = 'approved' 
                        WHERE id = ?
                    """, (bot_id,))
                    await conn.commit()
                
                return True
            return False
        except Exception as e:
            logger.error(f"Error restarting bot {bot_id}: {e}")
            return False
    
    async def get_user_bots(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all bots for a user."""
        try:
            bots = await db.get_user_bots(user_id)
            
            # Add running status
            for bot in bots:
                bot['is_running'] = bot['id'] in running_bots
            
            return bots
        except Exception as e:
            logger.error(f"Error getting user bots: {e}")
            return []
    
    async def get_all_bots_stats(self) -> Dict[str, Any]:
        """Get statistics for all user bots."""
        try:
            async with db.get_connection() as conn:
                # Total bots
                cursor = await conn.execute("SELECT COUNT(*) FROM user_bots")
                total_bots = (await cursor.fetchone())[0]
                
                # Running bots
                running_count = len(running_bots)
                
                # By status
                cursor = await conn.execute("""
                    SELECT status, COUNT(*) FROM user_bots GROUP BY status
                """)
                status_counts = dict(await cursor.fetchall())
                
                # Recent bots (last 7 days)
                cursor = await conn.execute("""
                    SELECT COUNT(*) FROM user_bots 
                    WHERE created_at > datetime('now', '-7 days')
                """)
                recent_bots = (await cursor.fetchone())[0]
                
                return {
                    'total_bots': total_bots,
                    'running_bots': running_count,
                    'pending_bots': status_counts.get('pending', 0),
                    'approved_bots': status_counts.get('approved', 0),
                    'rejected_bots': status_counts.get('rejected', 0),
                    'recent_bots': recent_bots
                }
        except Exception as e:
            logger.error(f"Error getting bot stats: {e}")
            return {}
    
    async def start_all_approved_bots(self):
        """Start all approved bots on system startup."""
        try:
            async with db.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT * FROM user_bots WHERE status = 'approved'
                """)
                approved_bots = await cursor.fetchall()
            
            logger.info(f"Starting {len(approved_bots)} approved user bots...")
            
            started_count = 0
            for bot_row in approved_bots:
                try:
                    bot_data = dict(bot_row)
                    await self._start_user_bot(bot_data)
                    started_count += 1
                except Exception as e:
                    logger.error(f"Failed to start bot {bot_data['id']}: {e}")
            
            logger.info(f"Successfully started {started_count}/{len(approved_bots)} user bots")
            
        except Exception as e:
            logger.error(f"Error starting approved bots: {e}")
    
    async def cleanup_stopped_bots(self):
        """Clean up any stopped bots and update their status."""
        try:
            # Get all bots marked as approved
            async with db.get_connection() as conn:
                cursor = await conn.execute("""
                    SELECT id FROM user_bots WHERE status = 'approved'
                """)
                approved_bot_ids = [row[0] for row in await cursor.fetchall()]
            
            # Check which ones are actually running
            for bot_id in approved_bot_ids:
                if bot_id not in running_bots:
                    # Mark as stopped
                    async with db.get_connection() as conn:
                        await conn.execute("""
                            UPDATE user_bots 
                            SET status = 'stopped' 
                            WHERE id = ?
                        """, (bot_id,))
                        await conn.commit()
            
        except Exception as e:
            logger.error(f"Error cleaning up stopped bots: {e}")


# Global bot manager instance
bot_manager = BotManager()
