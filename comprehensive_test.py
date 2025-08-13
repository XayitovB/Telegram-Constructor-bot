#!/usr/bin/env python3
"""
Comprehensive test script for Telegram Constructor Bot
Tests all major components and functionality
"""

import asyncio
import sys
from datetime import datetime

# Import bot components
from bot import bot, db
from core.config import settings
from core.database import DatabaseManager


async def test_configuration():
    """Test configuration loading"""
    print("🔧 Testing Configuration...")
    try:
        assert settings.bot_token, "Bot token should not be empty"
        assert len(settings.admin_user_ids) > 0, "At least one admin should be configured"
        print(f"✅ Bot token: {'*' * 10}...{settings.bot_token[-4:]}")
        print(f"✅ Admin users: {len(settings.admin_user_ids)}")
        print(f"✅ Database path: {settings.database.path}")
        return True
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False


async def test_database():
    """Test database initialization and operations"""
    print("\n📊 Testing Database...")
    try:
        db_manager = DatabaseManager(settings.database.path)
        await db_manager.initialize()
        
        # Test basic operations
        users = await db_manager.get_all_users()
        channels = await db_manager.get_mandatory_channels()
        stats = await db_manager.get_bot_stats()
        
        print(f"✅ Database initialized successfully")
        print(f"✅ Total users: {len(users)}")
        print(f"✅ Mandatory channels: {len(channels)}")
        print(f"✅ Bot stats: {stats['total_users']} users, {stats['messages_total']} messages")
        return True
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False


async def test_bot_connection():
    """Test bot connection to Telegram API"""
    print("\n🤖 Testing Bot Connection...")
    try:
        bot_info = await bot.get_me()
        print(f"✅ Connected to Telegram API")
        print(f"✅ Bot name: {bot_info.first_name}")
        print(f"✅ Bot username: @{bot_info.username}")
        print(f"✅ Bot ID: {bot_info.id}")
        return True
    except Exception as e:
        print(f"❌ Bot connection test failed: {e}")
        return False
    finally:
        # Close bot session to prevent unclosed session warning
        try:
            await bot.session.close()
        except:
            pass


async def test_channel_functionality():
    """Test channel membership checking functionality"""
    print("\n📺 Testing Channel Functionality...")
    try:
        channels = await db.get_mandatory_channels()
        if channels:
            print(f"✅ Found {len(channels)} mandatory channels")
            
            # Test membership check for admin user (should pass)
            admin_id = settings.admin_user_ids[0]
            membership_status = await db.check_user_channel_membership(admin_id, settings.bot_token)
            print(f"✅ Channel membership check working: {membership_status['all_joined']}")
            
            # Test join buttons generation with missing channels
            if membership_status.get('missing_channels'):
                buttons = await db.get_channel_join_buttons(membership_status['missing_channels'])
                print(f"✅ Join buttons generation working: {len(buttons)} buttons")
            else:
                print("✅ Join buttons generation working: user already joined all channels")
        else:
            print("⚠️  No mandatory channels configured - adding test channel...")
            await db.add_mandatory_channel(-1001234567890, "testchannel", "Test Channel", "https://t.me/testchannel", admin_id)
            print("✅ Test channel added")
        
        return True
    except Exception as e:
        print(f"❌ Channel functionality test failed: {e}")
        return False


async def test_admin_functionality():
    """Test admin-only features"""
    print("\n👑 Testing Admin Functionality...")
    try:
        # Test admin check
        admin_id = settings.admin_user_ids[0]
        is_admin = settings.is_admin(admin_id)
        print(f"✅ Admin check working: User {admin_id} is admin: {is_admin}")
        
        # Test database admin functions
        all_bots = await db.get_all_user_bots()
        messages = await db.get_open_messages()
        
        print(f"✅ Admin stats: {len(all_bots)} user bots, {len(messages)} open messages")
        return True
    except Exception as e:
        print(f"❌ Admin functionality test failed: {e}")
        return False


async def test_fsm_states():
    """Test FSM state management"""
    print("\n🔄 Testing FSM States...")
    try:
        # Import FSM states
        from bot import UserStates, AdminStates, ChannelStates, BotExtensionStates
        
        # Check that all states are properly defined
        user_states = [attr for attr in dir(UserStates) if not attr.startswith('_')]
        admin_states = [attr for attr in dir(AdminStates) if not attr.startswith('_')]
        channel_states = [attr for attr in dir(ChannelStates) if not attr.startswith('_')]
        bot_extension_states = [attr for attr in dir(BotExtensionStates) if not attr.startswith('_')]
        
        print(f"✅ UserStates: {len(user_states)} states defined")
        print(f"✅ AdminStates: {len(admin_states)} states defined")  
        print(f"✅ ChannelStates: {len(channel_states)} states defined")
        print(f"✅ BotExtensionStates: {len(bot_extension_states)} states defined")
        return True
    except Exception as e:
        print(f"❌ FSM states test failed: {e}")
        return False


async def run_comprehensive_test():
    """Run all tests"""
    print("🚀 Starting Comprehensive Bot Test")
    print("=" * 50)
    
    tests = [
        test_configuration,
        test_database,
        test_bot_connection,
        test_channel_functionality,
        test_admin_functionality,
        test_fsm_states
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📊 Success Rate: {(passed / (passed + failed)) * 100:.1f}%")
    
    if failed == 0:
        print("\n🎉 ALL TESTS PASSED! Bot is ready to run.")
        print("🚀 Start the bot with: python run.py")
        return True
    else:
        print(f"\n⚠️  {failed} tests failed. Please review the errors above.")
        return False


if __name__ == "__main__":
    try:
        result = asyncio.run(run_comprehensive_test())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n❌ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        sys.exit(1)
