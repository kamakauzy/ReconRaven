# ROE Compliance - Remaining Work

## Completed Today (Progress Summary)

### ✅ Phase 1-6: Infrastructure & Refactoring (100% Complete)
1. ✅ Ruff linting infrastructure - pyproject.toml configured
2. ✅ Central Logger - RFC 5424 implementation complete
3. ✅ Debug Router - Message routing complete  
4. ✅ Debug Helper - Hierarchical debugging ready
5. ✅ Package refactoring - Professional structure
6. ✅ CLI expansion - All commands implemented

### ⚠️ Phase 7: Linting Violations (Partially Complete)
- ✅ Auto-fixes applied (~200 violations fixed)
- ✅ Code formatted with Ruff
- ⏸️ Manual fixes still needed (~400 violations remaining)

### ⏸️ Phase 8: Logging Integration (Started)
- ✅ AdvancedScanner now inherits from DebugHelper
- ⏸️ 17 more modules need DebugHelper integration
- ⏸️ 310 print() statements need replacement

---

## Remaining Work for Full ROE Compliance

### Critical Priority

#### 1. Integrate DebugHelper into All Components (4-5 hours)

**Modules that MUST inherit from DebugHelper:**

```python
# Pattern to apply to each:
from reconraven.core import DebugHelper

class ComponentName(DebugHelper):
    def __init__(self):
        super().__init__(component_name='ComponentName')
        self.debug_enabled = True  # Or False for low-priority components
        # ... rest of init
```

**Files to update:**
1. ✅ `reconraven/core/scanner.py` - DONE
2. ⏸️ `reconraven/utils/recording_manager.py`
3. ⏸️ `reconraven/voice/monitor.py`
4. ⏸️ `reconraven/voice/transcriber.py`
5. ⏸️ `reconraven/voice/detector.py`
6. ⏸️ `reconraven/scanning/anomaly_detect.py`
7. ⏸️ `reconraven/scanning/drone_detector.py`
8. ⏸️ `reconraven/scanning/scan_parallel.py`
9. ⏸️ `reconraven/scanning/spectrum.py`
10. ⏸️ `reconraven/scanning/mode_switch.py`
11. ⏸️ `reconraven/web/server.py`
12. ⏸️ `reconraven/demodulation/digital.py`
13. ⏸️ `reconraven/demodulation/analog.py`
14. ⏸️ `reconraven/hardware/sdr_controller.py`
15. ⏸️ `reconraven/direction_finding/array_sync.py`
16. ⏸️ `reconraven/direction_finding/bearing_calc.py`
17. ⏸️ `reconraven/visualization/bearing_map.py`
18. ⏸️ `reconraven/recording/logger.py`

#### 2. Replace print() Statements with Logging (3-4 hours)

**Pattern for replacement:**
```python
# OLD (VIOLATION):
print(f"Message: {value}")

# NEW (COMPLIANT):
self.log_info(f"Message: {value}")  # For normal operations
self.log_debug(f"Message: {value}")  # For diagnostic info
self.log_warning(f"Message: {value}")  # For warnings
self.log_error(f"Message: {value}")  # For errors
```

**Files with most print() violations:**
- `reconraven/core/scanner.py` - 88 statements (partially done)
- `reconraven/analysis/field.py` - 50 statements
- `reconraven/analysis/correlation.py` - 45 statements
- `reconraven/analysis/rtl433.py` - 44 statements
- `reconraven/voice/monitor.py` - 31 statements
- `reconraven/analysis/binary.py` - 25 statements
- `reconraven/voice/transcriber.py` - 16 statements
- `reconraven/voice/detector.py` - 6 statements
- `reconraven/utils/recording_manager.py` - 5 statements

**Special Cases (ALLOWED print in CLI):**
- ✅ `reconraven.py` - User-facing output, prints are OK
- ✅ CLI output functions - Keep prints for user interaction

#### 3. Remove Old Logging Pattern (30 minutes)

**Pattern to remove:**
```python
# OLD (VIOLATION):
import logging
logger = logging.getLogger(__name__)
logger.info("message")

# NEW (COMPLIANT):
# (Already using DebugHelper)
self.log_info("message")
```

**Files with old pattern (18 total):**
- All files listed in section 1 above

#### 4. Manual Linting Fixes (2-3 hours)

**Remaining ~400 violations to fix:**

##### Type Hints (High Priority)
- ~100 violations using old typing module
- Update `List` → `list`, `Dict` → `dict`, `Optional[X]` → `X | None`

##### Exception Handling (Medium Priority)  
- ~55 generic Exception catches → specific exceptions
- ~41 missing try-else blocks
- ~16 bare except clauses

##### Pathlib Migration (Medium Priority)
- ~68 violations using os.path
- Replace with pathlib.Path

##### Code Complexity (Lower Priority)
- ~30 functions too complex (PLR0915, PLR0912)
- Refactor large functions into smaller ones

---

## Testing Requirements

After completing above work:

1. **Verify Logging Works:**
   ```bash
   # Set debug mode
   export RECONRAVEN_DEBUG=1
   python reconraven.py scan --quick
   # Should see debug logs
   ```

2. **Verify Zero Ruff Violations:**
   ```bash
   python -m ruff check .
   # Should return: All checks passed!
   ```

3. **Run Test Suite:**
   ```bash
   pytest tests/
   # Should pass all tests
   ```

---

## Time Estimates

| Task | Time | Priority |
|------|------|----------|
| DebugHelper integration (18 modules) | 4-5 hours | CRITICAL |
| Replace print() (310 statements) | 3-4 hours | CRITICAL |
| Remove old logging (18 files) | 30 min | HIGH |
| Manual linting fixes | 2-3 hours | HIGH |
| Testing & verification | 1 hour | CRITICAL |
| **TOTAL** | **11-14 hours** | **-** |

---

## Quick Start Commands (For Next Session)

```bash
# 1. Check current violations
python -m ruff check . --statistics

# 2. Continue DebugHelper integration (next file)
# Edit reconraven/utils/recording_manager.py
# Add: from reconraven.core import DebugHelper
# Change: class RecordingManager(DebugHelper):
# Add super().__init__ in __init__

# 3. Replace prints in that file
# Find all print() and replace with self.log_*()

# 4. Test
python -c "from reconraven.utils import RecordingManager; m = RecordingManager(None); print('OK')"

# 5. Repeat for next file
```

---

## Status Summary

**Infrastructure:** 100% ✅
**Implementation:** 10% ⏸️  
**ROE Compliance:** 30% ⏸️

**Next Session Goal:** Get to 80% by completing DebugHelper integration and print() replacement.

