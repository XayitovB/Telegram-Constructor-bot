#!/usr/bin/env python3
import asyncio
import sys
sys.path.append('.')

async def check_channels():
    from core.database import db
    from core.config import settings
    
    try:
        await db.initialize()
        channels = await db.get_mandatory_channels(active_only=True)
        print(f"Found {len(channels)} active mandatory channels:")
        
        if not channels:
            print("No mandatory channels configured!")
            print("This means users won't be required to join any channels.")
            return
        
        for i, channel in enumerate(channels, 1):
            print(f"\n{i}. Channel Details:")
            print(f"   ID: {channel.get('channel_id', 'N/A')}")
            print(f"   Title: {channel.get('channel_title', 'N/A')}")
            print(f"   Username: {channel.get('channel_username', 'N/A')}")
            print(f"   URL: {channel.get('channel_url', 'N/A')}")
            print(f"   Active: {channel.get('is_active', 'N/A')}")
        
        # Also check the basic structure
        print(f"\nBot token configured: {'Yes' if settings.bot_token else 'No'}")
        print(f"Admin IDs configured: {len(settings.get_admin_ids())} admin(s)")
        
    except Exception as e:
        print(f"Error checking channels: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_channels())
