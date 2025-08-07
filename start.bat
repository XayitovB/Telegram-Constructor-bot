@echo off
title Telegram Bot Starter
echo ====================================
echo    Telegram Constructor Bot
echo ====================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://python.org
    pause
    exit /b 1
)

:: Check if .env file exists
if not exist ".env" (
    echo ERROR: .env file not found!
    echo Please copy .env.example to .env and configure it with your bot token
    echo.
    echo Steps:
    echo 1. Copy .env.example to .env
    echo 2. Get your bot token from @BotFather
    echo 3. Get your user ID from @userinfobot
    echo 4. Edit .env with your details
    pause
    exit /b 1
)

:: Check if requirements are installed
echo Checking dependencies...
pip show aiogram >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
    echo Dependencies installed successfully!
)

:: Start the bot
echo.
echo Starting Telegram Bot...
echo Press Ctrl+C to stop
echo.
python run.py

pause
