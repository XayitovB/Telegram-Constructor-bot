"""
Professional message formatting and utility functions.
"""

import csv
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from aiogram.types import BufferedInputFile

from core.database import User, BotStats
from core.config import settings
from core.languages import get_text, get_language_name, DEFAULT_LANGUAGE


def escape_markdown(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    if not isinstance(text, str):
        return ""
    
    # Simple escape for common markdown characters
    escape_chars = ['*', '_', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in escape_chars:
        text = text.replace(char, f'\\{char}')
    return text


class MessageFormatter:
    """Professional message formatter with consistent styling."""
    
    @staticmethod
    def format_new_user_notification(user: User) -> str:
        """Format notification for new user registration."""
        # Format the user's information
        display_name = escape_markdown(user.display_name)
        full_name = escape_markdown(user.full_name)
        username = f"@{user.username}" if user.username else "No username"
        username = escape_markdown(username)
        
        return f"""🆕 **New User Registered**

👤 **User:** {display_name}
📝 **Full Name:** {full_name}
🔤 **Username:** {username}
🆔 **ID:** `{user.user_id}`
⏰ **Joined:** {user.join_date.strftime('%Y-%m-%d %H:%M:%S')}

🔍 To view details, use admin panel to search for this user."""
    
    @staticmethod
    def format_user_profile(user: User, show_admin_info: bool = False) -> str:
        """Format user profile information."""
        lines = [
            "👤 **User Profile**",
            "",
            f"🆔 **ID:** `{user.user_id}`",
            f"👤 **Name:** {user.full_name}",
        ]
        
        if user.username:
            lines.append(f"📝 **Username:** @{user.username}")
        
        # Role and status
        role_emoji = "👑" if user.is_admin else "👤"
        role_text = "Administrator" if user.is_admin else "User"
        lines.append(f"🏷️ **Role:** {role_emoji} {role_text}")
        
        status_emoji = "🚫" if user.is_banned else ("✅" if user.is_active else "⚪")
        status_text = "Banned" if user.is_banned else ("Active" if user.is_active else "Inactive")
        lines.append(f"📊 **Status:** {status_emoji} {status_text}")
        
        # Dates and activity
        join_date = user.join_date.strftime("%B %d, %Y at %H:%M")
        last_activity = user.last_activity.strftime("%B %d, %Y at %H:%M")
        
        lines.extend([
            f"📅 **Joined:** {join_date}",
            f"⏰ **Last Activity:** {last_activity}",
            f"💬 **Messages:** {user.message_count:,}"
        ])
        
        # Admin-only information
        if show_admin_info and user.is_admin:
            days_since_join = (datetime.now() - user.join_date).days
            avg_messages = user.message_count / max(days_since_join, 1)
            lines.extend([
                "",
                "📊 **Statistics:**",
                f"• Days active: {days_since_join}",
                f"• Avg messages/day: {avg_messages:.1f}"
            ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_user_summary(user: User, include_actions: bool = False) -> str:
        """Format user summary for lists."""
        status_emoji = "🚫" if user.is_banned else ("✅" if user.is_active else "⚪")
        role_emoji = "👑" if user.is_admin else "👤"
        
        name = user.display_name
        if len(name) > 25:
            name = name[:22] + "..."
        
        # Escape markdown characters in name to prevent parsing issues
        name_escaped = name.replace("*", "\\*").replace("_", "\\_").replace("`", "\\`")
        
        summary = f"{status_emoji} {role_emoji} **{name_escaped}**\n"
        summary += f"└ ID: `{user.user_id}` | Messages: {user.message_count}"
        
        if include_actions:
            summary += f"\n└ Actions: /user\\_{user.user_id}"
        
        return summary
    
    @staticmethod
    def format_bot_statistics(stats: BotStats) -> str:
        """Format bot statistics."""
        lines = [
            "📊 **Bot Statistics Dashboard**",
            "",
            "👥 **Users Overview:**",
            f"• Total Users: **{stats.total_users:,}**",
            f"• Active Users: **{stats.active_users:,}**",
            f"• Banned Users: **{stats.banned_users:,}**",
            f"• Administrators: **{stats.admin_count:,}**",
            "",
            "📈 **Activity Metrics:**",
            f"• Activity Rate: **{stats.active_rate:.1f}%**",
            f"• Messages Today: **{stats.messages_today:,}**",
            f"• Total Messages: **{stats.messages_total:,}**",
            f"• New Users Today: **{stats.new_users_today:,}**"
        ]
        
        # Additional calculations
        if stats.total_users > 0:
            ban_rate = (stats.banned_users / stats.total_users) * 100
            admin_rate = (stats.admin_count / stats.total_users) * 100
            
            lines.extend([
                "",
                "📊 **Additional Metrics:**",
                f"• Ban Rate: **{ban_rate:.1f}%**",
                f"• Admin Ratio: **{admin_rate:.1f}%**"
            ])
        
        lines.extend([
            "",
            f"🕐 **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_welcome_message(user_name: str, is_admin: bool = False, language: str = DEFAULT_LANGUAGE) -> str:
        """Format welcome message with language support."""
        admin_hint = ""
        if is_admin:
            admin_hint = get_text("admin_hint", language)
        
        return get_text("welcome_message", language, name=user_name, admin_hint=admin_hint)
    
    @staticmethod
    def format_help_message(is_admin: bool = False) -> str:
        """Format help message."""
        lines = [
            "📋 **Help & Information**",
            "",
            "🤖 **About This Bot**",
            f"This is {settings.bot.name}, a professional Telegram bot with advanced features.",
            "",
            "🎯 **Available Features:**"
        ]
        
        # User features
        lines.extend([
            "",
            "👤 **For All Users:**",
            "• 👤 View and manage your profile",
            "• ℹ️ Get bot information and help",
            "• 📞 Contact support team",
            "• 📋 Access this help menu"
        ])
        
        # Admin features
        if is_admin:
            lines.extend([
                "",
                "👑 **Administrator Features:**",
                "• 👥 View and manage all users",
                "• 📊 Access detailed statistics",
                "• 📢 Send broadcast messages",
                "• ⚙️ Configure bot settings",
                "• 🔍 Search and filter users",
                "• 📊 Export data and reports"
            ])
        
        lines.extend([
            "",
            "🔧 **Navigation Tips:**",
            "• Use the menu buttons for easy navigation",
            "• Inline buttons provide quick actions",
            "• Use 🔙 buttons to go back",
            "",
            "❓ **Need More Help?**",
            f"Contact our support team using the 📞 **Contact Support** button."
        ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_contact_info() -> str:
        """Format contact information."""
        return f"""
📞 **Contact Information**

🏢 **{settings.contact.company_name}**

**Support Channels:**
• 📱 Telegram: @{settings.contact.support_username}
• 📧 Email: {settings.contact.support_email}
• 🌐 Website: {settings.contact.website}

**Business Hours:**
Monday - Friday: 9:00 AM - 6:00 PM (UTC)
Weekend: Limited support available

**Response Time:**
• Urgent issues: Within 2 hours
• General inquiries: Within 24 hours

We're here to help! 🤝
        """.strip()
    
    @staticmethod
    def format_broadcast_preview(message: str, recipient_count: int) -> str:
        """Format broadcast message preview."""
        preview_text = message if len(message) <= 200 else message[:197] + "..."
        
        return f"""
📢 **Broadcast Message Preview**

**Message Content:**
{preview_text}

**Delivery Details:**
• Recipients: **{recipient_count:,}** users
• Estimated time: ~{max(1, recipient_count * 0.1 / 60):.0f} minutes
• Success rate: ~95-98% (typical)

**Ready to send?** Use the buttons below to confirm or cancel.
        """.strip()
    
    @staticmethod
    def format_broadcast_result(sent: int, failed: int, total: int) -> str:
        """Format broadcast result."""
        success_rate = (sent / max(total, 1)) * 100
        
        # Choose a human-readable evaluation line based on success rate
        evaluation = (
            "🎉 Excellent delivery rate!" if success_rate >= 95 else
            "✅ Good delivery rate." if success_rate >= 90 else
            "⚠️ Some delivery issues detected." if success_rate >= 80 else
            "❗ Consider checking your message content."
        )
        
        return f"""
✅ **Broadcast Completed**

**Results Summary:**
• 📤 Successfully sent: **{sent:,}**
• ❌ Failed to send: **{failed:,}**
• 📊 Success rate: **{success_rate:.1f}%**
• ⏱️ Completed: {datetime.now().strftime('%H:%M:%S')}

{evaluation}
        """.strip()
    
    
    @staticmethod
    def format_bot_list(bots: List[Dict[str, Any]], status_filter: str = "all") -> str:
        """Format bot list for display."""
        if not bots:
            status_text = {
                "all": "You haven't added any bots yet.",
                "pending": "No pending bot requests.",
                "approved": "No approved bots.",
                "rejected": "No rejected bot requests."
            }.get(status_filter, "No bots found.")
            
            return f"""
🤖 **My Bots** - {status_filter.title()}

{status_text}

💡 **Get Started:**
• Use ➕ **Add New Bot** to submit your first bot
• Follow our guidelines for faster approval
• Contact admin if you need help
            """.strip()
        
        lines = [f"🤖 **My Bots** - {status_filter.title()}\n"]
        
        for i, bot in enumerate(bots, 1):
            status_emoji = {
                "pending": "⏳",
                "approved": "✅",
                "rejected": "❌"
            }.get(bot['status'], "🤖")
            
            created_date = datetime.fromisoformat(bot['created_at']).strftime('%Y-%m-%d')
            
            lines.append(f"{status_emoji} **{bot['bot_name']}**")
            lines.append(f"└ Status: {bot['status'].title()} | Created: {created_date}")
            if bot.get('bot_description'):
                desc = bot['bot_description'][:50] + "..." if len(bot['bot_description']) > 50 else bot['bot_description']
                lines.append(f"└ Description: {desc}")
            lines.append("")
        
        return "\n".join(lines)
    
    @staticmethod
    def format_bot_details(bot: Dict[str, Any]) -> str:
        """Format detailed bot information."""
        status_emoji = {
            "pending": "⏳",
            "approved": "✅",
            "rejected": "❌"
        }.get(bot['status'], "🤖")
        
        created_date = datetime.fromisoformat(bot['created_at']).strftime('%B %d, %Y at %H:%M')
        
        lines = [
            f"{status_emoji} **Bot Details**",
            "",
            f"🤖 **Name:** {bot['bot_name']}",
            f"🆔 **Status:** {bot['status'].title()}",
            f"📅 **Submitted:** {created_date}"
        ]
        
        if bot.get('bot_username'):
            lines.append(f"📛 **Username:** @{bot['bot_username']}")
        
        if bot.get('bot_description'):
            lines.extend([
                "",
                "📝 **Description:**",
                bot['bot_description']
            ])
        
        if bot.get('approved_at'):
            approved_date = datetime.fromisoformat(bot['approved_at']).strftime('%B %d, %Y at %H:%M')
            lines.append(f"✅ **Approved:** {approved_date}")
        
        if bot.get('notes'):
            lines.extend([
                "",
                "📝 **Admin Notes:**",
                bot['notes']
            ])
        
        return "\n".join(lines)
    
    @staticmethod
    def format_contact_admin_form(message_type: str) -> str:
        """Format contact admin form prompt."""
        prompts = {
            "issue": "🆘 **Report an Issue**\n\nPlease describe the problem you're experiencing:",
            "feature": "💡 **Feature Request**\n\nDescribe the feature you'd like to see:",
            "question": "❓ **General Question**\n\nWhat would you like to know?",
            "bot_approval": "🤖 **Bot Approval Query**\n\nAsk about your bot submission:",
            "custom": "📨 **Custom Message**\n\nWrite your message to the admin:"
        }
        
        base_prompt = prompts.get(message_type, prompts["custom"])
        
        return f"""
{base_prompt}

📝 **Guidelines:**
• Be clear and specific
• Include relevant details
• Maximum 1000 characters
• Please be patient for admin response

💬 **Type your message below:**
        """.strip()
    
    @staticmethod
    def format_bot_guidelines() -> str:
        """Format bot submission guidelines."""
        return f"""
📜 **Bot Submission Guidelines**

🔍 **Before Submitting:**
• Ensure your bot is fully functional
• Test all commands and features
• Have a clear purpose and description
• Follow Telegram's Bot Guidelines

✅ **Requirements:**
• Valid bot token from @BotFather
• Descriptive bot name and purpose
• No spam, adult, or malicious content
• Must comply with our terms of service

🚀 **Approval Process:**
1. Submit your bot with all required info
2. Admin review (usually 24-48 hours)
3. You'll be notified of approval/rejection
4. Approved bots get hosting support

⚠️ **Important Notes:**
• Rejected bots can be resubmitted after fixes
• Keep your bot token secure
• Contact admin for technical support
• Regular maintenance may be required

🤝 **Need Help?**
Use 👨‍💼 **Contact Admin** for questions!
        """.strip()


class DataExporter:
    """Professional data export utilities."""
    
    @staticmethod
    def create_users_csv(users: List[User]) -> BufferedInputFile:
        """Create CSV file from users data."""
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        
        # Enhanced headers
        headers = [
            'User ID', 'Username', 'First Name', 'Last Name', 'Full Name',
            'Role', 'Status', 'Is Admin', 'Is Active', 'Is Banned',
            'Join Date', 'Last Activity', 'Message Count',
            'Days Since Join', 'Messages Per Day'
        ]
        writer.writerow(headers)
        
        # Write user data with calculations
        for user in users:
            days_since_join = (datetime.now() - user.join_date).days or 1
            messages_per_day = user.message_count / days_since_join
            
            writer.writerow([
                user.user_id,
                user.username or '',
                user.first_name or '',
                user.last_name or '',
                user.full_name,
                'Admin' if user.is_admin else 'User',
                'Banned' if user.is_banned else ('Active' if user.is_active else 'Inactive'),
                user.is_admin,
                user.is_active,
                user.is_banned,
                user.join_date.isoformat(),
                user.last_activity.isoformat(),
                user.message_count,
                days_since_join,
                round(messages_per_day, 2)
            ])
        
        # Create file
        output.seek(0)
        csv_content = output.getvalue().encode('utf-8-sig')  # UTF-8 with BOM for Excel
        filename = f"users_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return BufferedInputFile(csv_content, filename=filename)
    
    @staticmethod
    def create_stats_report(stats: BotStats) -> BufferedInputFile:
        """Create detailed statistics report."""
        report_content = f"""
Bot Statistics Report
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Bot: {settings.bot.name}

=== USER OVERVIEW ===
Total Users: {stats.total_users:,}
Active Users: {stats.active_users:,}
Banned Users: {stats.banned_users:,}
Administrator Count: {stats.admin_count:,}

=== ACTIVITY METRICS ===
Activity Rate: {stats.active_rate:.2f}%
Messages Today: {stats.messages_today:,}
Total Messages: {stats.messages_total:,}
New Users Today: {stats.new_users_today:,}

=== CALCULATED METRICS ===
Ban Rate: {(stats.banned_users / max(stats.total_users, 1)) * 100:.2f}%
Admin Ratio: {(stats.admin_count / max(stats.total_users, 1)) * 100:.2f}%
Avg Messages/User: {stats.messages_total / max(stats.total_users, 1):.1f}

=== ENGAGEMENT ANALYSIS ===
Active User Ratio: {stats.active_rate:.1f}%
User Retention: {((stats.total_users - stats.banned_users) / max(stats.total_users, 1)) * 100:.1f}%

=== RECOMMENDATIONS ===
- Monitor users with low activity
- Consider engagement campaigns if activity rate < 70%
- Review ban policies if ban rate > 10%
- Expand admin team if user/admin ratio > 100:1
        """.strip()
        
        filename = f"bot_stats_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        return BufferedInputFile(report_content.encode('utf-8'), filename=filename)


class PaginationHelper:
    """Professional pagination utilities."""
    
    @staticmethod
    def paginate_list(items: List[Any], page: int = 1, per_page: int = None) -> tuple:
        """Paginate a list of items."""
        if per_page is None:
            per_page = settings.bot.users_per_page
        
        total_items = len(items)
        total_pages = max(1, (total_items + per_page - 1) // per_page)
        
        # Ensure page is within bounds
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_items)
        
        return items[start_idx:end_idx], page, total_pages, total_items
    
    @staticmethod
    def create_page_info(current_page: int, total_pages: int, total_items: int) -> str:
        """Create pagination information string."""
        if total_pages <= 1:
            return f"Showing all {total_items} items"
        
        start_item = (current_page - 1) * settings.bot.users_per_page + 1
        end_item = min(current_page * settings.bot.users_per_page, total_items)
        
        return f"Showing {start_item}-{end_item} of {total_items} items (Page {current_page}/{total_pages})"


# Utility functions
def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix




def format_number(number: int) -> str:
    """Format number with appropriate suffixes."""
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}M"
    elif number >= 1_000:
        return f"{number / 1_000:.1f}K"
    return str(number)
