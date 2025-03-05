import logging
import os
import sys
from typing import Optional

# Define log levels
TRACE = 5  # Custom level below DEBUG
DEBUG = logging.DEBUG
INFO = logging.INFO
WARNING = logging.WARNING
ERROR = logging.ERROR

# Register the TRACE level with the logging module
logging.addLevelName(TRACE, "TRACE")

class TraceLogger(logging.Logger):
    """Custom logger with TRACE level support"""
    
    def trace(self, msg, *args, **kwargs):
        """Log at TRACE level (more detailed than DEBUG)"""
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)

# Replace the default logger class
logging.setLoggerClass(TraceLogger)

# Configure the root logger
def configure_logging(level: int = INFO, log_file: Optional[str] = None):
    """
    Configure the logging system.
    
    Args:
        level: The logging level (use constants from this module)
        log_file: Optional path to a log file
    """
    # Get the log level from environment if set
    env_level = os.getenv("LOG_LEVEL", "").upper()
    if env_level == "TRACE":
        level = TRACE
    elif env_level == "DEBUG":
        level = DEBUG
    elif env_level == "INFO":
        level = INFO
    elif env_level == "WARNING":
        level = WARNING
    elif env_level == "ERROR":
        level = ERROR
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Log configuration info
    root_logger.info(f"Logging configured with level: {logging.getLevelName(level)}")
    if log_file:
        root_logger.info(f"Logging to file: {log_file}")

# Get a logger for a specific module
def get_logger(name: str) -> TraceLogger:
    """Get a logger for a specific module"""
    return logging.getLogger(name) 