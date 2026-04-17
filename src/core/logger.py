"""
Logging configuration using Loguru.

Provides structured, timestamped logging with rotation and formatting
for all bot operations including trades, errors, and debug information.
"""

import sys
from pathlib import Path
from loguru import logger
from .config import settings


def setup_logger() -> None:
    """
    Configure Loguru logger with appropriate settings.
    
    Sets up console and file logging with proper formatting,
    rotation, and log levels based on configuration.
    """
    # Remove default handler
    logger.remove()
    
    # Console logging
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
    )
    
    # File logging (if enabled)
    if settings.log_to_file:
        # Ensure log directory exists
        log_path = Path(settings.log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            settings.log_file_path,
            level=settings.log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            rotation="100 MB",  # Rotate when file reaches 100MB
            retention="30 days",  # Keep logs for 30 days
            compression="zip",  # Compress rotated logs
            encoding="utf-8",
        )
    
    # Log startup
    logger.info("Logger initialized with level: {}", settings.log_level)
    if settings.log_to_file:
        logger.info("File logging enabled: {}", settings.log_file_path)


def get_logger(name: str = None):
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Optional name for the logger. If None, uses the caller's module name.
        
    Returns:
        Configured logger instance.
    """
    if name:
        return logger.bind(name=name)
    return logger


# Trading-specific logging helpers
class TradingLogger:
    """Helper class for trading-specific logging with structured data."""
    
    @staticmethod
    def log_signal(signal_type: str, symbol: str, **kwargs) -> None:
        """Log trading signal generation."""
        logger.info(
            "[SIGNAL] {} signal for {} | {}",
            signal_type.upper(),
            symbol,
            " | ".join(f"{k}={v}" for k, v in kwargs.items())
        )
    
    @staticmethod
    def log_order(action: str, symbol: str, side: str, size: float, price: float = None, **kwargs) -> None:
        """Log order placement or execution."""
        price_str = f" @ {price}" if price else ""
        logger.info(
            "[ORDER] {} {} {} {}{} | {}",
            action.upper(),
            side.upper(),
            size,
            symbol,
            price_str,
            " | ".join(f"{k}={v}" for k, v in kwargs.items())
        )
    
    @staticmethod
    def log_position_update(symbol: str, action: str, **kwargs) -> None:
        """Log position management actions."""
        logger.info(
            "[POSITION] {} {} | {}",
            action.upper(),
            symbol,
            " | ".join(f"{k}={v}" for k, v in kwargs.items())
        )
    
    @staticmethod
    def log_data_update(source: str, symbol: str, **kwargs) -> None:
        """Log market data updates."""
        logger.debug(
            "[DATA] {} {} | {}",
            source.upper(),
            symbol,
            " | ".join(f"{k}={v}" for k, v in kwargs.items())
        )
    
    @staticmethod
    def log_error(operation: str, error: Exception, **context) -> None:
        """Log errors with context."""
        logger.error(
            "[ERROR] {} failed: {} | {}",
            operation,
            str(error),
            " | ".join(f"{k}={v}" for k, v in context.items())
        )
    
    @staticmethod
    def log_performance(period: str, **metrics) -> None:
        """Log performance metrics."""
        logger.info(
            "[PERFORMANCE] {} | {}",
            period,
            " | ".join(f"{k}={v}" for k, v in metrics.items())
        )


# Initialize logger on import
setup_logger()

# Export commonly used loggers
trading_logger = TradingLogger()
main_logger = get_logger("main") 