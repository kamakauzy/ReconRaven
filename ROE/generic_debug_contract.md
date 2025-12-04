# ========================================================================
# Unified Debug & Logging Contract (Language- and Framework-Agnostic)
# ========================================================================

# ------------------------------------------------------------------------
# 1. Purpose
# ------------------------------------------------------------------------
The unified debug and logging system defines a centralized, hierarchical
logging pipeline suitable for any application architecture:

    Debug Helper → Debug Router → Central Logger

It guarantees consistent behavior, consistent metadata, central control,
and hierarchical opt-in debugging (application → component → subcomponent).

This contract also defines mandatory logging placement requirements to
ensure essential operational events are never left uninstrumented.

# ------------------------------------------------------------------------
# 2. Core Entities
# ------------------------------------------------------------------------

Central Logger:
    The only module allowed to emit logs. Defines log levels, manages
    filtering, formatting, timestamping, and output sinks.

Debug Router:
    Provides a single routing API. Does not filter, transform, or modify
    messages. Simply forwards them to the Central Logger.

Debug Helper:
    Implemented by Components and Subcomponents. Performs local filtering,
    hierarchical debug-enabled checks, environment checks, and delegates
    to the Debug Router. Never logs directly.

Application-Level Debug Context:
    Stores:
        - debug_enabled (global switch)
        - min_log_level
    This object may propagate min_log_level to the Central Logger at
    startup. Otherwise, no programmatic mutation of debug flags.

Component:
    Defines debug_enabled and debug_process (for high-frequency logging).
    Cannot mutate debug flags programmatically. Must use a Debug Helper.

Subcomponent:
    Same requirements as Component, but adds one more level of hierarchy:
        subcomponent.debug_enabled AND component.debug_enabled AND
        application.debug_enabled must all be true before logging.

# ------------------------------------------------------------------------
# 3. Log Levels (RFC 5424 aligned)
# ------------------------------------------------------------------------
DEBUG       Detailed diagnostic data.
INFO        Confirmation of normal operations.
NOTICE      Significant but not problematic events.
WARNING     Potential issues or degraded performance.
ERROR       Operation failed but system is still operational.
ALERT       Immediate action required.
CRITICAL    System is degraded or unstable.
EMERGENCY   System unusable.

Filtering is performed by comparing log_level >= min_log_level.

# ------------------------------------------------------------------------
# 4. Debug Helper Contract
# ------------------------------------------------------------------------
Every Component and Subcomponent MUST implement a Debug Helper function
with this behavior:

    1. Check local debug_enabled
    2. Check parent component debug_enabled (for subcomponents)
    3. Check application.debug_enabled
    4. Check environment restrictions (e.g., no editor/test logs)
    5. Check log_level >= application.min_log_level
    6. Call Debug Router with:
           - application_name
           - component_name
           - subcomponent_name
           - function_name
           - message
           - log_level
           - is_testing flag

Debug Helper MAY prepend "[Component]" or "[Subcomponent]" to message.

Debug Helper MUST NOT:
    - call print/console directly
    - call Central Logger directly
    - modify debug configuration

# ------------------------------------------------------------------------
# 5. High-Frequency Logging Rules
# ------------------------------------------------------------------------
For per-request/per-frame/per-loop logging:

    debug_process must be true
    AND all debug_enabled l