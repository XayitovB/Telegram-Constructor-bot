#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('.')

async def test_membership_check():
    from core.database import db
    from core.config import settings
    from aiogram import Bot
    from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
    
    try:
        await db.initialize()
        
        # Get mandatory channels
        channels = await db.get_mandatory_channels(active_only=True)
        print(f"Testing membership check for {len(channels)} channels...\n")
        
        if not channels:
            print("No mandatory channels to test!")
            return
        
        # Create bot instance
        bot_instance = Bot(token=settings.bot_token)
        
        # Test with a sample user ID (use a known admin user)
        admin_ids = settings.get_admin_ids()
        test_user_id = admin_ids[0] if admin_ids else None
        
        if not test_user_id:
            print("No admin user ID found to test with!")
            return
        
        print(f"Testing membership for user ID: {test_user_id}")
        
        for channel in channels:
            print(f"\n--- Testing Channel: {channel.get('channel_title', 'Unknown')} ---")
            
            # Debug channel data
            channel_id = channel.get('channel_id')
            channel_username = channel.get('channel_username')
            channel_url = channel.get('channel_url')
            
            print(f"Channel ID: {channel_id}")
            print(f"Channel Username: {channel_username}")
            print(f"Channel URL: {channel_url}")
            
            # Determine identifier to use
            channel_identifier = None
            if channel_id:
                channel_identifier = channel_id
            elif channel_username:
                channel_identifier = f"@{channel_username}"
            
            print(f"Using identifier: {channel_identifier}")
            
            if not channel_identifier:
                print("❌ No valid identifier found for this channel!")
                continue
            
            try:
                # Try to get chat member info
                member = await bot_instance.get_chat_member(channel_identifier, test_user_id)
                print(f"✅ Member status: {member.status}")
                
                if member.status in ['left', 'kicked']:
                    print("⚠️  User is NOT a member (left or kicked)")
                elif member.status in ['member', 'administrator', 'creator']:
                    print("✅ User IS a member")
                else:
                    print(f"❓ Unknown status: {member.status}")
                    
            except TelegramBadRequest as e:
                print(f"❌ TelegramBadRequest: {e}")
            except TelegramForbiddenError as e:
                print(f"❌ TelegramForbiddenError: {e}")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
        
        # Close the bot session
        await bot_instance.session.close()
        
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_membership_check())
