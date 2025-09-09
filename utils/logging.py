"""
Enhanced logging setup for MCP Test Environment
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional
from config.config import LoggingConfig


class MCPLogger:
    """Enhanced logger for MCP Test Environment"""

    def __init__(self, config: LoggingConfig):
        self.config = config
        self._setup_logging()

    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logger
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, self.config.level.upper()))

        # Clear existing handlers
        logger.handlers.clear()

        # Create formatter
        formatter = logging.Formatter(self.config.format)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # File handler (if specified)
        if self.config.file_path:
            log_path = Path(self.config.file_path)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = logging.handlers.RotatingFileHandler(
                log_path,
                maxBytes=self.config.max_file_size,
                backupCount=self.config.backup_count,
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance"""
        return logging.getLogger(name)


def setup_logging(config: LoggingConfig) -> MCPLogger:
    """Setup logging for the application"""
    return MCPLogger(config)


# Convenience function for getting loggers
def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)
