"""
Professional logging configuration using loguru.
"""

import sys
from pathlib import Path
from loguru import logger
from .config import settings


# Global flag to prevent multiple setup
_logging_configured = False

def setup_logging() -> None:
    """Configure logging for the application."""
    global _logging_configured
    
    if _logging_configured:
        return
    
    # Remove default handler
    logger.remove()
    
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Add custom success level for loguru (if not exists)
    try:
        logger.level("SUCCESS", no=25, color="<green><bold>", icon="✓")
    except (ValueError, TypeError):
        # Level already exists, ignore
        pass
    
    # Console handler
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True
    )
    
    # File handler for all logs
    logger.add(
        logs_dir / "bot.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )
    
    # Error file handler
    logger.add(
        logs_dir / "errors.log",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="5 MB",
        retention="30 days",
        compression="zip"
    )
    
    # Admin actions file handler
    logger.add(
        logs_dir / "admin_actions.log",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {extra[admin_id]} | {extra[action]} | {message}",
        rotation="5 MB",
        retention="90 days",
        filter=lambda record: "admin_action" in record["extra"]
    )
    
    _logging_configured = True
    logger.info(f"Logging configured - Level: {settings.log_level}")


def log_admin_action(admin_id: int, action: str, details: str = "") -> None:
    """Log admin actions with special formatting."""
    logger.bind(admin_action=True, admin_id=admin_id, action=action).info(details)


def get_logger(name: str):
    """Get logger instance for specific module."""
    return logger.bind(module=name)
