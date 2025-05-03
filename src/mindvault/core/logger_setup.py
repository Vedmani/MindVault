"""Logging configuration for the MindVault Twitter application.

This module configures Loguru for application-wide logging with proper formatting
and file output.
"""

import sys
from pathlib import Path

from loguru import logger

# Remove default handler
logger.remove()

# Add console handler with custom format
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{file.name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# Add rotating file handler
# log_file = Path(f'mindvault_twitter_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
log_file = Path('mindvault_twitter.log')

logger.add(
    log_file,
    rotation="100 MB",
    retention="10 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {file.name}:{function}:{line} - {message}",
    level="INFO",
    serialize=True
)

# Function to get logger for a module
def get_logger(name: str):
    """Get a logger instance for the specified module.
    
    Args:
        name: The module name (typically __name__)
        
    Returns:
        A configured logger instance
    """
    return logger.bind(name=name) 