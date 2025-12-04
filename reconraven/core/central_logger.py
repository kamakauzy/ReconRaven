"""
Central Logger Module
Single source for all log emission with RFC 5424 log levels.
Part of ReconRaven's centralized logging infrastructure.
"""

import logging
import sys
from enum import IntEnum
from pathlib import Path
from typing import Optional


class LogLevel(IntEnum):
    """RFC 5424 aligned log levels"""

    DEBUG = logging.DEBUG  # 10
    INFO = logging.INFO  # 20
    NOTICE = 25  # Custom level between INFO and WARNING
    WARNING = logging.WARNING  # 30
    ERROR = logging.ERROR  # 40
    ALERT = 45  # Custom level between ERROR and CRITICAL
    CRITICAL = logging.CRITICAL  # 50
    EMERGENCY = 60  # Custom level above CRITICAL


class CentralLogger:
    """
    Central logging facility - the ONLY module allowed to emit logs.

    Manages log levels, filtering, formatting, timestamping, and output sinks.
    All components must route through Debug Router to reach this logger.
    """

    _instance: Optional['CentralLogger'] = None
    _initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.logger = logging.getLogger('reconraven')
        self.logger.setLevel(logging.DEBUG)  # Capture everything, filter at handler level
        self.logger.propagate = False  # Don't propagate to root logger

        # Add custom log levels
        logging.addLevelName(LogLevel.NOTICE, 'NOTICE')
        logging.addLevelName(LogLevel.ALERT, 'ALERT')
        logging.addLevelName(LogLevel.EMERGENCY, 'EMERGENCY')

        # Default configuration
        self.min_log_level = LogLevel.INFO
        self.console_enabled = True
        self.file_enabled = False
        self.log_file_path: Optional[Path] = None

        # Setup default console handler
        self._setup_console_handler()

        CentralLogger._initialized = True

    def _setup_console_handler(self):
        """Setup console output handler"""
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.min_log_level)

        # Detailed format with component context
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
        )
        console_handler.setFormatter(formatter)

        # Clear existing handlers and add new one
        self.logger.handlers.clear()
        self.logger.addHandler(console_handler)

    def _setup_file_handler(self, log_file: Path):
        """Setup file output handler"""
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(self.min_log_level)

        # More detailed format for file logs
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S.%f',
        )
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.log_file_path = log_file

    def configure(
        self,
        min_log_level: LogLevel = LogLevel.INFO,
        console_enabled: bool = True,
        log_file: Optional[str] = None,
    ):
        """
        Configure the central logger.

        Args:
            min_log_level: Minimum log level to emit
            console_enabled: Enable console output
            log_file: Optional file path for log output
        """
        self.min_log_level = min_log_level
        self.console_enabled = console_enabled

        # Reconfigure handlers
        self.logger.handlers.clear()

        if console_enabled:
            self._setup_console_handler()

        if log_file:
            self.file_enabled = True
            self._setup_file_handler(Path(log_file))

    def emit_log(
        self,
        level: LogLevel,
        message: str,
        application_name: str,
        component_name: str,
        subcomponent_name: Optional[str] = None,
        function_name: Optional[str] = None,
        is_testing: bool = False,
        **kwargs,
    ):
        """
        Emit a log message (called by Debug Router only).

        Args:
            level: Log level
            message: Log message
            application_name: Application name
            component_name: Component name
            subcomponent_name: Optional subcomponent name
            function_name: Optional function name
            is_testing: Whether this is a test log
            **kwargs: Additional context
        """
        # Build context string
        context_parts = [application_name, component_name]
        if subcomponent_name:
            context_parts.append(subcomponent_name)
        if function_name:
            context_parts.append(function_name)

        context = '.'.join(context_parts)

        # Create logger with context
        context_logger = logging.getLogger(f'reconraven.{context}')

        # Filter test logs if not in testing mode
        if is_testing and not kwargs.get('allow_test_logs', False):
            return

        # Emit the log
        context_logger.log(level, message, extra=kwargs)

    def debug(self, message: str, **kwargs):
        """Convenience method for DEBUG logs"""
        self.emit_log(
            LogLevel.DEBUG, message, 'reconraven', 'system', function_name='debug', **kwargs
        )

    def info(self, message: str, **kwargs):
        """Convenience method for INFO logs"""
        self.emit_log(
            LogLevel.INFO, message, 'reconraven', 'system', function_name='info', **kwargs
        )

    def notice(self, message: str, **kwargs):
        """Convenience method for NOTICE logs"""
        self.emit_log(
            LogLevel.NOTICE, message, 'reconraven', 'system', function_name='notice', **kwargs
        )

    def warning(self, message: str, **kwargs):
        """Convenience method for WARNING logs"""
        self.emit_log(
            LogLevel.WARNING, message, 'reconraven', 'system', function_name='warning', **kwargs
        )

    def error(self, message: str, **kwargs):
        """Convenience method for ERROR logs"""
        self.emit_log(
            LogLevel.ERROR, message, 'reconraven', 'system', function_name='error', **kwargs
        )

    def alert(self, message: str, **kwargs):
        """Convenience method for ALERT logs"""
        self.emit_log(
            LogLevel.ALERT, message, 'reconraven', 'system', function_name='alert', **kwargs
        )

    def critical(self, message: str, **kwargs):
        """Convenience method for CRITICAL logs"""
        self.emit_log(
            LogLevel.CRITICAL, message, 'reconraven', 'system', function_name='critical', **kwargs
        )

    def emergency(self, message: str, **kwargs):
        """Convenience method for EMERGENCY logs"""
        self.emit_log(
            LogLevel.EMERGENCY,
            message,
            'reconraven',
            'system',
            function_name='emergency',
            **kwargs,
        )


# Singleton accessor
_central_logger_instance: Optional[CentralLogger] = None


def get_central_logger() -> CentralLogger:
    """Get the singleton Central Logger instance"""
    global _central_logger_instance
    if _central_logger_instance is None:
        _central_logger_instance = CentralLogger()
    return _central_logger_instance

