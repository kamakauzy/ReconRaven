# ROE Compliance & Spec Sheet Implementation Plan

## Overview
Address all ROE violations (missing Ruff linting, improper logging/debug infrastructure, excessive print statements) and implement missing spec sheet functionality (REST API, touchscreen app, enhanced features) while completing the ongoing refactoring into a proper Python package structure.

---

## Phase 1: Critical ROE Violations - Linting Infrastructure

**Problem:** Python ROE mandates ZERO errors/warnings from Ruff linter. Currently no `pyproject.toml` or Ruff configuration exists, and the codebase has not been linted.

**Actions:**
1. Create `pyproject.toml` with Ruff configuration matching ROE requirements
2. Add `ruff>=0.8.4` to `requirements.txt`
3. Run `ruff check .` to identify all violations across codebase
4. Run `ruff check --fix .` for auto-fixable issues
5. Manually fix remaining violations (imports, unused vars, type issues)
6. Run `ruff format .` to ensure consistent formatting
7. Verify ZERO errors/warnings before proceeding

**Files affected:** All Python files (38 total), `requirements.txt`, new `pyproject.toml`

---

## Phase 2: Debug & Logging Contract Violations

**Problem:** Generic Debug Contract requires centralized logging with Debug Helper → Debug Router → Central Logger hierarchy. Current codebase has 470+ `print()` statements and inconsistent `logging.getLogger(__name__)` usage without centralized control.

**Actions:**
1. Create `reconraven/core/central_logger.py` - Single source for all log emission with RFC 5424 levels (DEBUG/INFO/NOTICE/WARNING/ERROR/ALERT/CRITICAL/EMERGENCY)
2. Create `reconraven/core/debug_router.py` - Routing API that forwards to Central Logger without transformation
3. Create `reconraven/core/debug_helper.py` - Mixin/utility for components to implement hierarchical debug-enabled checks
4. Update `config/hardware.yaml` logging section to include debug_enabled flags and min_log_level
5. Replace all 470+ `print()` statements with proper logging calls through Debug Helper
6. Add mandatory logging at: function entry/exit for critical ops, error conditions, state changes, external I/O (SDR/GPS/DB)
7. Ensure no component calls `print()` or Central Logger directly - must go through Debug Helper

**Files affected:** All 38 Python files, `config/hardware.yaml`

---

## Phase 3: Complete Package Refactoring (Resume In-Progress Work)

**Problem:** Refactoring 40% complete - need to move all standalone scripts into `reconraven/` package and update imports.

**Actions:**
1. **Move core files:**
   - `advanced_scanner.py` → `reconraven/core/scanner.py`
   
2. **Move analysis files:**
   - `binary_decoder.py` → `reconraven/analysis/binary.py`
   - `correlation_engine.py` → `reconraven/analysis/correlation.py`
   - `field_analyzer.py` → `reconraven/analysis/field.py`
   - `rtl433_integration.py` → `reconraven/analysis/rtl433.py`

3. **Move voice files:**
   - `voice_detector.py` → `reconraven/voice/detector.py`
   - `voice_monitor.py` → `reconraven/voice/monitor.py`
   - `voice_transcriber.py` → `reconraven/voice/transcriber.py`

4. **Move utility files:**
   - `recording_manager.py` → `reconraven/utils/recording_manager.py`

5. **Update all imports** throughout codebase:
   - `from database import get_db` → `from reconraven.core.database import get_db`
   - `from voice_detector import VoiceDetector` → `from reconraven.voice import VoiceDetector`
   - Similar for all moved modules

6. **Delete original standalone scripts** after confirming imports work

**Files affected:** 15 standalone scripts + all files importing them

---

## Phase 4: Unified CLI Expansion

**Problem:** CLI in `reconraven.py` lacks commands for voice operations, correlation analysis, and recording management per spec sheet requirements.

**Actions:**
1. Expand `reconraven.py` CLI with new subcommands:
   ```
   reconraven voice monitor --freq 146.52 --mode FM --record
   reconraven voice scan --band 2m --dwell 5
   reconraven voice transcribe --file recording.wav [--model base|small|medium]
   reconraven voice batch-transcribe [--untranscribed-only]
   
   reconraven analyze correlation --time-window 10 [--min-occurrences 3]
   reconraven analyze sequences [--max-length 5]
   reconraven analyze profile --freq 433.92
   reconraven analyze network [--output graph.json]
   reconraven analyze field --file recording.npy [--offline]
   
   reconraven recording list [--limit 100] [--format table|json]
   reconraven recording export --id 123 --format wav
   reconraven recording cleanup --type ism|old|voice [--days 7]
   
   reconraven db migrate [--from-version X]
   ```

2. Remove/integrate functionality from:
   - `launch_demo.py` → `reconraven dashboard --demo`
   - `migrate_database.py` → `reconraven db migrate`
   - `batch_transcribe.py` → `reconraven voice batch-transcribe`

**Files affected:** `reconraven.py`, 3 standalone scripts to delete

---

## Phase 5: REST API Implementation (Spec Requirement)

**Problem:** Spec sheet requires REST API at `http://localhost:5000/api/v1/` with JWT/API key auth for integration with Securit360 and touchscreen app.

**Actions:**
1. Create `reconraven/api/` module structure:
   - `__init__.py`
   - `auth.py` - API key/JWT generation and validation (local-only)
   - `routes_scan.py` - Scan endpoints (start/stop/status)
   - `routes_demod.py` - Demodulation/decoding endpoints
   - `routes_df.py` - Direction finding endpoints
   - `routes_db.py` - Database query/export endpoints
   - `routes_transcribe.py` - Transcription endpoints
   - `websocket.py` - WebSocket for real-time updates

2. Update `reconraven/web/server.py` to register API blueprint at `/api/v1/`

3. Add dependencies: `flask-restful`, `flask-jwt-extended`, `flask-limiter` to `requirements.txt`

4. Implement rate limiting (10 req/s per spec)

5. Add API documentation in `docs/API.md`

6. Add `reconraven api generate-key` CLI command for key generation

**Files affected:** New `reconraven/api/` directory, `reconraven/web/server.py`, `requirements.txt`, `reconraven.py`

---

## Phase 6: Touchscreen Application (Spec Requirement)

**Problem:** Spec requires Kivy-based touchscreen app for 7" Raspberry Pi display with API client architecture.

**Actions:**
1. Create `touch_app/` directory structure:
   - `main.py` - Kivy app entry point with fullscreen config
   - `screens/` - Signal/Network/Voice/Transcripts/Timeline tabs
   - `api_client.py` - API request wrapper with auth
   - `themes.yaml` - Dark theme config per spec

2. Add Kivy dependencies to `requirements.txt`: `kivy>=2.3.0`, `kivymd>=1.1.1`

3. Implement features:
   - Large glove-friendly buttons (min 60px touch targets)
   - Swipe navigation between tabs
   - API polling every 5-10s with offline caching
   - Haptic/visual alerts for anomalies
   - Dark theme by default

4. Create systemd service for autostart: `install/reconraven-touch.service`

5. Add CLI command: `reconraven touch start [--fullscreen] [--theme dark]`

6. Fallback to CLI dashboard if no display detected

**Files affected:** New `touch_app/` directory, `requirements.txt`, `reconraven.py`, new `install/` directory

---

## Phase 7: Missing Spec Features

**Problem:** Spec sheet requires several features not yet implemented:

**Actions:**
1. **Location-aware frequency database** (spec section 4 - Data Management):
   - Implement `reconraven setup --auto` with IP geolocation
   - Download repeater/NOAA/public safety data from RepeaterBook/RadioReference
   - Cache locally in `frequency_cache/` for offline use
   - Auto-identify known frequencies during scans

2. **Enhanced DF calibration** (spec section 4 - Direction Finding):
   - Already exists in `reconraven.py` as `test df-cal`
   - Add Kalman filtering for motion compensation (future enhancement)

3. **Batch operations** (spec section 4):
   - Already implemented via CLI
   - Ensure cleanup operations work correctly

4. **Export formats** (spec section 4):
   - Add JSON/CSV/TXT export for transcripts in DB routes
   - Implement in `reconraven/core/database.py`

**Files affected:** `reconraven.py`, `reconraven/core/database.py`, new location services module

---

## Phase 8: Testing & Documentation Updates

**Actions:**
1. Update `tests/` to work with new package structure:
   - Fix imports: `from reconraven.core import *`
   - Add API endpoint tests
   - Add touchscreen app mock tests

2. Update documentation:
   - `README.md` - New CLI commands, API usage, touchscreen setup
   - `docs/RF_SETUP_GUIDE.md` - Verify still accurate
   - `docs/DF_SETUP_GUIDE.md` - Verify still accurate
   - `docs/TEST_COMMANDS.md` - Update all test commands
   - New `docs/API.md` - Full API documentation
   - New `docs/ARCHITECTURE.md` - Package structure explanation

3. Validate all functionality:
   - Run `reconraven test sdr`
   - Run `reconraven test noise`
   - Run `reconraven test freq --freq 146.52 --duration 60`
   - Verify dashboard loads
   - Test API endpoints with curl
   - Test touchscreen app on Pi (or simulator)

**Files affected:** `tests/` directory, all `docs/` files

---

## Phase 9: Final ROE Compliance Verification

**Actions:**
1. Run `ruff check .` - must return ZERO errors/warnings
2. Run `ruff format --check .` - must pass
3. Verify no `print()` statements remain (except in CLI output functions)
4. Verify all logging uses Debug Helper → Debug Router → Central Logger
5. Verify debug_enabled checks exist for high-frequency logging
6. Run full test suite: `pytest tests/`
7. Commit with message: "ROE compliance + spec sheet implementation complete"

---

## Summary

**ROE Violations to Fix:**
- Missing Ruff linter configuration and validation (470+ potential issues)
- 470+ print() statements instead of proper logging
- No centralized logging infrastructure (Debug Helper/Router/Logger)
- Missing debug_enabled hierarchical checks

**Spec Features to Implement:**
- REST API with authentication (6 endpoint groups)
- Kivy touchscreen application
- Location-aware frequency database
- Enhanced CLI commands (voice, analyze, recording)
- Complete package refactoring

**Estimated Impact:**
- 50+ files modified
- ~3000-4000 lines of new code
- ~1000 lines refactored
- All standalone scripts consolidated

---

## Implementation Todos

1. Create pyproject.toml with Ruff config and run initial linting
2. Implement Central Logger, Debug Router, and Debug Helper
3. Replace 470+ print statements with proper logging
4. Move all standalone scripts to reconraven/ package
5. Update all imports across codebase for new structure
6. Add voice/analyze/recording commands to unified CLI
7. Build REST API with all required endpoints
8. Create Kivy touchscreen application
9. Implement location-aware frequency database
10. Update tests and documentation for new structure
11. Run full test suite and verify ROE compliance

