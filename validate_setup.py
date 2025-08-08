#!/usr/bin/env python3
"""
Setup Validation Script for Telegram Constructor Bot
This script validates that your bot is properly configured and ready to run.
"""

import sys
import os
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    print("🐍 Checking Python version...")
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ is required. Current version:", sys.version)
        return False
    print(f"✅ Python {sys.version.split()[0]} is compatible")
    return True

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("\n📦 Checking dependencies...")
    required_modules = [
        'aiogram',
        'aiosqlite', 
        'pydantic',
        'pydantic_settings',
        'loguru',
        'aiohttp'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - MISSING")
            missing_modules.append(module)
    
    if missing_modules:
        print(f"\n❌ Missing modules: {', '.join(missing_modules)}")
        print("💡 Install with: pip install -r requirements.txt")
        return False
    
    return True

def check_env_file():
    """Check if .env file exists and has required variables."""
    print("\n🔧 Checking configuration...")
    
    env_path = Path(".env")
    if not env_path.exists():
        print("❌ .env file not found")
        print("💡 Copy .env.example to .env and configure it")
        return False
    
    print("✅ .env file exists")
    
    # Check for required variables
    env_content = env_path.read_text()
    required_vars = ['BOT_TOKEN', 'ADMIN_USER_IDS']
    missing_vars = []
    
    for var in required_vars:
        if f"{var}=" not in env_content:
            missing_vars.append(var)
        elif f"{var}=your_bot_token_here" in env_content or f"{var}=123456789" in env_content:
            print(f"⚠️  {var} needs to be configured (still has example value)")
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    return True

def check_project_structure():
    """Check if all required files and directories exist."""
    print("\n📁 Checking project structure...")
    
    required_files = [
        'bot.py',
        'bot_manager.py', 
        'user_bot_template.py',
        'run.py',
        'requirements.txt',
        'core/config.py',
        'core/database.py',
        'core/languages.py',
        'core/logging.py',
        'ui/keyboards.py',
        'ui/formatters.py'
    ]
    
    required_dirs = [
        'core',
        'ui', 
        'logs',
        'user_bots'
    ]
    
    missing_files = []
    missing_dirs = []
    
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
        else:
            print(f"✅ {file_path}")
    
    for dir_path in required_dirs:
        if not Path(dir_path).exists():
            missing_dirs.append(dir_path)
        else:
            print(f"✅ {dir_path}/")
    
    if missing_files:
        print(f"❌ Missing files: {', '.join(missing_files)}")
        return False
        
    if missing_dirs:
        print(f"❌ Missing directories: {', '.join(missing_dirs)}")
        return False
    
    return True

def check_configuration():
    """Check if configuration loads properly."""
    print("\n⚙️  Checking configuration loading...")
    
    try:
        from core.config import settings
        print("✅ Configuration loads successfully")
        
        # Check token format
        if len(settings.bot_token) < 10:
            print("⚠️  Bot token seems too short")
        else:
            print("✅ Bot token format looks correct")
        
        # Check admin IDs
        if not settings.get_admin_ids():
            print("⚠️  No admin user IDs configured")
        else:
            print(f"✅ {len(settings.get_admin_ids())} admin user(s) configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False

def main():
    """Run all validation checks."""
    print("🚀 Telegram Constructor Bot - Setup Validation")
    print("=" * 50)
    
    checks = [
        ("Python Version", check_python_version),
        ("Dependencies", check_dependencies),
        ("Environment File", check_env_file), 
        ("Project Structure", check_project_structure),
        ("Configuration", check_configuration)
    ]
    
    all_passed = True
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
            if not result:
                all_passed = False
        except Exception as e:
            print(f"❌ {check_name} check failed: {e}")
            results.append((check_name, False))
            all_passed = False
    
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{check_name:.<20} {status}")
    
    if all_passed:
        print("\n🎉 All checks passed! Your bot is ready to run.")
        print("🚀 Start the bot with: python run.py")
        return 0
    else:
        print("\n⚠️  Some checks failed. Please fix the issues above.")
        print("📖 Check the README.md for setup instructions.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
