"""
Professional keyboard layouts for button-only interface.
"""

from typing import Optional, List
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from core.config import settings


class KeyboardBuilder:
    """Professional keyboard builder with consistent styling."""
    
    @staticmethod
    def create_reply_keyboard(buttons: List[List[str]], 
                             resize: bool = True, 
                             one_time: bool = False) -> ReplyKeyboardMarkup:
        """Create reply keyboard from button text lists."""
        keyboard = [
            [KeyboardButton(text=text) for text in row]
            for row in buttons
        ]
        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=resize,
            one_time_keyboard=one_time
        )
    
    @staticmethod
    def create_inline_keyboard(buttons: List[List[tuple]]) -> InlineKeyboardMarkup:
        """Create inline keyboard from (text, callback_data) tuples."""
        keyboard = [
            [InlineKeyboardButton(text=text, callback_data=callback) 
             for text, callback in row]
            for row in buttons
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)


class MainKeyboards:
    """Main application keyboards."""
    
    @staticmethod
    def get_user_main_menu() -> ReplyKeyboardMarkup:
        """Get main menu for regular users."""
        buttons = [
            ["👤 My Profile", "ℹ️ Information"],
            ["📞 Contact Support", "📋 Help"]
        ]
        return KeyboardBuilder.create_reply_keyboard(buttons)
    
    @staticmethod
    def get_admin_main_menu() -> ReplyKeyboardMarkup:
        """Get main menu for admin users."""
        buttons = [
            ["👤 My Profile"],
            ["👑 Admin Panel", "📊 Statistics"],
            ["👥 User Management", "📢 Broadcast"]
        ]
        return KeyboardBuilder.create_reply_keyboard(buttons)
    
    @staticmethod
    def get_back_button() -> ReplyKeyboardMarkup:
        """Get simple back button."""
        buttons = [["🔙 Back to Main Menu"]]
        return KeyboardBuilder.create_reply_keyboard(buttons, one_time=True)
    
    @staticmethod
    def get_cancel_button() -> ReplyKeyboardMarkup:
        """Get cancel button for operations."""
        buttons = [["❌ Cancel Operation"]]
        return KeyboardBuilder.create_reply_keyboard(buttons, one_time=True)


class AdminKeyboards:
    """Admin-specific keyboards."""
    
    @staticmethod
    def get_admin_panel() -> ReplyKeyboardMarkup:
        """Get admin panel main menu."""
        buttons = [
            ["👥 View All Users", "✅ View Active Users"],
            ["👑 View Admins"],
            ["📊 Bot Statistics", "📈 Detailed Analytics"],
            ["📢 Send Broadcast", "⚙️ Bot Settings"],
            ["🔙 Back to Main Menu"]
        ]
        return KeyboardBuilder.create_reply_keyboard(buttons)
    
    @staticmethod
    def get_user_management() -> InlineKeyboardMarkup:
        """Get user management inline keyboard."""
        buttons = [
            [("👥 All Users", "users_all"), ("✅ Active Users", "users_active")],
            [("👑 Admins Only", "users_admins")],
            [("📊 Export CSV", "users_export"), ("🔄 Refresh", "users_refresh")]
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def get_user_actions(user_id: int, is_admin: bool = False, is_banned: bool = False) -> InlineKeyboardMarkup:
        """Get user action keyboard."""
        buttons = []
        
        # Admin controls
        if is_admin:
            buttons.append([("👤 Remove Admin", f"remove_admin_{user_id}")])
        else:
            buttons.append([("👑 Make Admin", f"make_admin_{user_id}")])
        
        # Ban controls
        if is_banned:
            buttons.append([("✅ Unban User", f"unban_{user_id}")])
        else:
            buttons.append([("🚫 Ban User", f"ban_{user_id}")])
        
        # Additional actions
        buttons.extend([
            [("📝 Send Message", f"message_{user_id}"), ("📊 User Stats", f"stats_{user_id}")],
            [("🔙 Back to Users", "users_all")]
        ])
        
        return KeyboardBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def get_broadcast_confirmation(recipient_count: int) -> InlineKeyboardMarkup:
        """Get broadcast confirmation keyboard."""
        buttons = [
            [("✅ Send to All", "broadcast_confirm"), ("❌ Cancel", "broadcast_cancel")],
            [("👁️ Preview Message", "broadcast_preview")]
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def get_statistics_menu() -> InlineKeyboardMarkup:
        """Get statistics menu."""
        buttons = [
            [("📊 Basic Stats", "stats_basic"), ("📈 Detailed Stats", "stats_detailed")],
            [("👥 User Analytics", "stats_users"), ("📢 Broadcast History", "stats_broadcasts")],
            [("📱 Activity Report", "stats_activity"), ("📋 Export Report", "stats_export")],
            [("🔄 Refresh Data", "stats_refresh")]
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons)


class NavigationKeyboards:
    """Navigation and utility keyboards."""
    
    @staticmethod
    def get_pagination(current_page: int, total_pages: int, callback_prefix: str) -> InlineKeyboardMarkup:
        """Get pagination keyboard."""
        buttons = []
        
        # Navigation buttons
        nav_buttons = []
        if current_page > 1:
            nav_buttons.append(("⬅️ Previous", f"{callback_prefix}_page_{current_page - 1}"))
        
        nav_buttons.append((f"📄 {current_page}/{total_pages}", "page_info"))
        
        if current_page < total_pages:
            nav_buttons.append(("➡️ Next", f"{callback_prefix}_page_{current_page + 1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # Additional controls
        buttons.append([
            ("🔄 Refresh", f"{callback_prefix}_refresh"),
            ("🔙 Back", f"{callback_prefix}_back")
        ])
        
        return KeyboardBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def get_confirmation(action: str, item_id: str = "") -> InlineKeyboardMarkup:
        """Get confirmation dialog."""
        suffix = f"_{item_id}" if item_id else ""
        buttons = [
            [("✅ Confirm", f"confirm_{action}{suffix}"), ("❌ Cancel", f"cancel_{action}{suffix}")]
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons)


class BroadcastKeyboards:
    """Broadcast-specific keyboards."""
    
    @staticmethod
    def get_broadcast_menu() -> ReplyKeyboardMarkup:
        """Get broadcast menu."""
        buttons = [
            ["📝 Compose Message", "📋 Message Templates"],
            ["📊 Broadcast History", "⚙️ Broadcast Settings"],
            ["🔙 Back to Admin Panel"]
        ]
        return KeyboardBuilder.create_reply_keyboard(buttons)
    
    @staticmethod
    def get_message_options() -> InlineKeyboardMarkup:
        """Get message composition options."""
        buttons = [
            [("📝 Text Message", "compose_text"), ("🖼️ With Image", "compose_image")],
            [("🎥 With Video", "compose_video"), ("📎 With Document", "compose_document")],
            [("📋 Use Template", "compose_template"), ("❌ Cancel", "compose_cancel")]
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def get_broadcast_targets() -> InlineKeyboardMarkup:
        """Get broadcast target selection."""
        buttons = [
            [("👥 All Users", "target_all"), ("✅ Active Only", "target_active")],
            [("👑 Admins Only", "target_admins"), ("🎯 Custom Filter", "target_custom")]
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons)


class SettingsKeyboards:
    """Settings and configuration keyboards."""
    
    @staticmethod
    def get_settings_menu() -> InlineKeyboardMarkup:
        """Get settings menu."""
        buttons = [
            [("🤖 Bot Settings", "settings_bot"), ("📊 Statistics Settings", "settings_stats")],
            [("🔒 Security Settings", "settings_security"), ("📢 Broadcast Settings", "settings_broadcast")],
            [("💾 Database Settings", "settings_database"), ("🔄 Reset Settings", "settings_reset")],
            [("💾 Save Changes", "settings_save"), ("❌ Cancel Changes", "settings_cancel")]
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons)
    
    @staticmethod
    def get_toggle_setting(setting_name: str, current_value: bool) -> InlineKeyboardMarkup:
        """Get toggle setting keyboard."""
        status = "✅ Enabled" if current_value else "❌ Disabled"
        action = "disable" if current_value else "enable"
        
        buttons = [
            [("🔄 Toggle", f"toggle_{setting_name}_{action}")],
            [("ℹ️ Info", f"info_{setting_name}"), ("🔙 Back", "settings_back")]
        ]
        return KeyboardBuilder.create_inline_keyboard(buttons)


# Helper functions for dynamic keyboards
def get_user_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Get user keyboard - same for all users."""
    return MainKeyboards.get_user_main_menu()


def create_user_list_keyboard(users: List, page: int, total_pages: int) -> InlineKeyboardMarkup:
    """Create keyboard for user list with actions."""
    buttons = []
    
    # User action buttons (max 5 per page)
    for user in users[:5]:
        user_info = f"{user.display_name} ({'Admin' if user.is_admin else 'User'})"
        if len(user_info) > 30:
            user_info = user_info[:27] + "..."
        buttons.append([(user_info, f"user_detail_{user.user_id}")])
    
    # Pagination
    if total_pages > 1:
        nav_buttons = []
        if page > 1:
            nav_buttons.append(("⬅️", f"users_page_{page - 1}"))
        nav_buttons.append((f"{page}/{total_pages}", "page_info"))
        if page < total_pages:
            nav_buttons.append(("➡️", f"users_page_{page + 1}"))
        buttons.append(nav_buttons)
    
    # Control buttons
    buttons.append([
        ("🔄 Refresh", "users_refresh"),
        ("📊 Export", "users_export"),
        ("🔙 Back", "admin_panel")
    ])
    
    return KeyboardBuilder.create_inline_keyboard(buttons)
