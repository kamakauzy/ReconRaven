"""
Debug Helper Module
Provides hierarchical debug-enabled checking and logging interface for components.
Part of ReconRaven's centralized logging infrastructure.
"""

import inspect
import os
from typing import Optional

from .central_logger import LogLevel
from .debug_router import get_debug_router


class DebugConfig:
    """
    Application-level debug configuration.
    Stores global debug state and minimum log level.
    """

    def __init__(self):
        self.debug_enabled: bool = os.getenv('RECONRAVEN_DEBUG', '0') == '1'
        self.min_log_level: LogLevel = LogLevel.INFO
        self.application_name: str = 'reconraven'

    def set_debug_enabled(self, enabled: bool):
        """Set global debug flag"""
        self.debug_enabled = enabled

    def set_min_log_level(self, level: LogLevel):
        """Set minimum log level"""
        self.min_log_level = level


# Global debug configuration
_debug_config = DebugConfig()


def get_debug_config() -> DebugConfig:
    """Get global debug configuration"""
    return _debug_config


class DebugHelper:
    """
    Debug Helper mixin for components and subcomponents.

    Implements hierarchical debug-enabled checks and delegates to Debug Router.

    Usage:
        class MyComponent(DebugHelper):
            def __init__(self):
                super().__init__(component_name='MyComponent')
                self.debug_enabled = True

            def do_something(self):
                self.log_debug('Doing something')
                self.log_info('Operation complete')
    """

    def __init__(
        self,
        component_name: str,
        subcomponent_name: Optional[str] = None,
        parent_debug_helper: Optional['DebugHelper'] = None,
    ):
        """
        Initialize Debug Helper.

        Args:
            component_name: Name of this component
            subcomponent_name: Optional subcomponent name
            parent_debug_helper: Parent component's debug helper (for subcomponents)
        """
        self.component_name = component_name
        self.subcomponent_name = subcomponent_name
        self.parent_debug_helper = parent_debug_helper

        # Component-level debug flags
        self.debug_enabled: bool = False
        self.debug_process: bool = False  # For high-frequency logging

        # Get debug router
        self._debug_router = get_debug_router()
        self._debug_config = get_debug_config()

    def _should_log(self, log_level: LogLevel, is_process: bool = False) -> bool:
        """
        Check if logging should occur based on hierarchical debug flags.

        Args:
            log_level: Log level to check
            is_process: Whether this is high-frequency process logging

        Returns:
            True if logging should occur
        """
        # Check log level
        if log_level < self._debug_config.min_log_level:
            return False

        # For high-frequency logging, check debug_process
        if is_process and not self.debug_process:
            return False

        # Check local debug_enabled
        if not self.debug_enabled:
            return False

        # Check parent debug_enabled (for subcomponents)
        if self.parent_debug_helper and not self.parent_debug_helper.debug_enabled:
            return False

        # Check application debug_enabled
        if not self._debug_config.debug_enabled:
            return False

        # Check environment restrictions (no logs in editor/test unless explicitly allowed)
        return not os.getenv('RECONRAVEN_NO_LOGS')

    def _get_caller_function(self) -> Optional[str]:
        """Get the name of the calling function"""
        try:
            frame = inspect.currentframe()
            if frame and frame.f_back and frame.f_back.f_back:
                return frame.f_back.f_back.f_code.co_name
        except Exception:
            pass
        return None

    def _log(
        self,
        level: LogLevel,
        message: str,
        is_process: bool = False,
        is_testing: bool = False,
        **kwargs,
    ):
        """
        Internal logging method that performs all checks.

        Args:
            level: Log level
            message: Log message
            is_process: Whether this is high-frequency process logging
            is_testing: Whether this is a test log
            **kwargs: Additional context
        """
        if not self._should_log(level, is_process):
            return

        # Get calling function
        function_name = self._get_caller_function()

        # Prepend component name to message if configured
        if self.subcomponent_name:
            prefixed_message = f'[{self.subcomponent_name}] {message}'
        elif self.component_name:
            prefixed_message = f'[{self.component_name}] {message}'
        else:
            prefixed_message = message

        # Route to Debug Router
        self._debug_router.route_log(
            application_name=self._debug_config.application_name,
            component_name=self.component_name,
            subcomponent_name=self.subcomponent_name,
            function_name=function_name,
            message=prefixed_message,
            log_level=level,
            is_testing=is_testing,
            **kwargs,
        )

    # Convenience methods for each log level

    def log_debug(self, message: str, is_process: bool = False, **kwargs):
        """Log DEBUG message"""
        self._log(LogLevel.DEBUG, message, is_process=is_process, **kwargs)

    def log_info(self, message: str, is_process: bool = False, **kwargs):
        """Log INFO message"""
        self._log(LogLevel.INFO, message, is_process=is_process, **kwargs)

    def log_notice(self, message: str, is_process: bool = False, **kwargs):
        """Log NOTICE message"""
        self._log(LogLevel.NOTICE, message, is_process=is_process, **kwargs)

    def log_warning(self, message: str, is_process: bool = False, **kwargs):
        """Log WARNING message"""
        self._log(LogLevel.WARNING, message, is_process=is_process, **kwargs)

    def log_error(self, message: str, is_process: bool = False, **kwargs):
        """Log ERROR message"""
        self._log(LogLevel.ERROR, message, is_process=is_process, **kwargs)

    def log_alert(self, message: str, is_process: bool = False, **kwargs):
        """Log ALERT message"""
        self._log(LogLevel.ALERT, message, is_process=is_process, **kwargs)

    def log_critical(self, message: str, is_process: bool = False, **kwargs):
        """Log CRITICAL message"""
        self._log(LogLevel.CRITICAL, message, is_process=is_process, **kwargs)

    def log_emergency(self, message: str, is_process: bool = False, **kwargs):
        """Log EMERGENCY message"""
        self._log(LogLevel.EMERGENCY, message, is_process=is_process, **kwargs)
