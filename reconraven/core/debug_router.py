"""
Debug Router Module
Routes debug messages from components to Central Logger without transformation.
Part of ReconRaven's centralized logging infrastructure.
"""

from typing import Optional

from .central_logger import LogLevel, get_central_logger


class DebugRouter:
    """
    Debug message router - provides single routing API.

    Does NOT filter, transform, or modify messages.
    Simply forwards them to the Central Logger.

    All components should use Debug Helper which calls this router.
    """

    _instance: Optional['DebugRouter'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.central_logger = get_central_logger()

    def route_log(
        self,
        application_name: str,
        component_name: str,
        subcomponent_name: Optional[str],
        function_name: Optional[str],
        message: str,
        log_level: LogLevel,
        is_testing: bool = False,
        **kwargs,
    ):
        """
        Route a log message to Central Logger (no transformation).

        Args:
            application_name: Application identifier
            component_name: Component name
            subcomponent_name: Optional subcomponent name
            function_name: Optional function name
            message: Log message
            log_level: Log level (RFC 5424)
            is_testing: Whether this is a test log
            **kwargs: Additional context
        """
        self.central_logger.emit_log(
            level=log_level,
            message=message,
            application_name=application_name,
            component_name=component_name,
            subcomponent_name=subcomponent_name,
            function_name=function_name,
            is_testing=is_testing,
            **kwargs,
        )


# Singleton accessor
_debug_router_instance: Optional[DebugRouter] = None


def get_debug_router() -> DebugRouter:
    """Get the singleton Debug Router instance"""
    global _debug_router_instance
    if _debug_router_instance is None:
        _debug_router_instance = DebugRouter()
    return _debug_router_instance

