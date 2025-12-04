"""
Mode Switching Module
Handles dynamic switching between parallel scan and DF modes.
"""

import time
from enum import Enum
from typing import Optional

from reconraven.core.debug_helper import DebugHelper


class SwitchMode(Enum):
    """Mode switching states."""

    PARALLEL_SCAN = 'parallel_scan'
    TRANSITIONING = 'transitioning'
    DF_MODE = 'df_mode'


class ModeSwitcher(DebugHelper):
    """Manages dynamic mode switching for SDR array."""

    def __init__(self, sdr_controller, parallel_scanner, df_array):
        super().__init__(component_name='ModeSwitcher')
        self.debug_enabled = True
        """Initialize mode switcher.

        Args:
            sdr_controller: SDRController instance
            parallel_scanner: ParallelScanner instance
            df_array: SDRArraySync instance
        """
        self.sdr = sdr_controller
        self.parallel_scanner = parallel_scanner
        self.df_array = df_array
        self.current_mode = SwitchMode.PARALLEL_SCAN
        self.df_frequency = None
        self.switch_count = 0

    def switch_to_df(self, frequency_hz: float) -> bool:
        """Switch from parallel scan to DF mode.

        Args:
            frequency_hz: Frequency to perform DF on

        Returns:
            True if switch successful
        """
        if self.current_mode == SwitchMode.DF_MODE:
            self.log_warning('Already in DF mode')
            return False

        self.log_info(f'Switching to DF mode for {frequency_hz/1e6:.3f} MHz...')
        self.current_mode = SwitchMode.TRANSITIONING
        self.switch_count += 1

        try:
            # Step 1: Stop all parallel scanning
            self.parallel_scanner.stop_parallel_scan()
            time.sleep(0.5)  # Allow threads to stop

            # Step 2: Retune all SDRs to target frequency
            self.log_info(f'Retuning all SDRs to {frequency_hz/1e6:.3f} MHz')
            for sdr in self.sdr.sdrs:
                sdr.center_freq = int(frequency_hz)

            time.sleep(0.2)  # Allow tuning to settle

            # Step 3: Ensure phase coherence (if hardware sync available)
            # Note: Software calibration done separately via df_array.calibrate_phase()

            self.df_frequency = frequency_hz
            self.current_mode = SwitchMode.DF_MODE

            self.log_info('Successfully switched to DF mode')
            return True

        except Exception as e:
            self.log_error(f'Error switching to DF mode: {e}')
            self.current_mode = SwitchMode.PARALLEL_SCAN
            return False

    def switch_to_parallel(self) -> bool:
        """Switch from DF mode back to parallel scan.

        Returns:
            True if switch successful
        """
        if self.current_mode == SwitchMode.PARALLEL_SCAN:
            self.log_warning('Already in parallel scan mode')
            return False

        self.log_info('Switching back to parallel scan mode...')
        self.current_mode = SwitchMode.TRANSITIONING

        try:
            # Step 1: Clear DF frequency
            self.df_frequency = None

            # Step 2: Restore band assignments
            # The parallel scanner will retune SDRs when restarted

            # Step 3: Restart parallel scanning
            self.parallel_scanner.start_parallel_scan()

            self.current_mode = SwitchMode.PARALLEL_SCAN

            self.log_info('Successfully switched to parallel scan mode')
            return True

        except Exception as e:
            self.log_error(f'Error switching to parallel scan: {e}')
            return False

    def quick_df_check(self, frequency_hz: float, duration_s: float = 2.0) -> Optional[dict]:
        """Perform a quick DF check and return to scanning.

        Args:
            frequency_hz: Frequency to check
            duration_s: How long to spend in DF mode

        Returns:
            DF results dictionary or None
        """
        try:
            # Switch to DF
            if not self.switch_to_df(frequency_hz):
                return None

            # Brief delay for stabilization
            time.sleep(0.5)

            # DF calculation handled by caller
            # This just manages the mode switching timing

            # Hold DF mode for specified duration
            time.sleep(duration_s)

            # Switch back
            self.switch_to_parallel()

            return {'success': True, 'frequency_hz': frequency_hz}

        except Exception as e:
            self.log_error(f'Error in quick DF check: {e}')
            # Ensure we return to parallel scan
            if self.current_mode != SwitchMode.PARALLEL_SCAN:
                self.switch_to_parallel()
            return None

    def is_ready_for_df(self) -> bool:
        """Check if system is ready for DF operation.

        Returns:
            True if ready for DF
        """
        if self.current_mode != SwitchMode.DF_MODE:
            return False

        # Check all SDRs are at same frequency
        if len(self.sdr.sdrs) < 4:
            return False

        freq = self.sdr.sdrs[0].center_freq
        return all(abs(sdr.center_freq - freq) <= 1000 for sdr in self.sdr.sdrs[1:])

    def get_status(self) -> dict:
        """Get mode switcher status.

        Returns:
            Status dictionary
        """
        return {
            'current_mode': self.current_mode.value,
            'df_frequency_hz': self.df_frequency,
            'df_frequency_mhz': self.df_frequency / 1e6 if self.df_frequency else None,
            'switch_count': self.switch_count,
            'ready_for_df': self.is_ready_for_df(),
        }

    def force_parallel_scan(self):
        """Force return to parallel scan mode (emergency/cleanup)."""
        self.log_warning('Force returning to parallel scan mode')

        try:
            if self.parallel_scanner.running:
                self.parallel_scanner.stop_parallel_scan()
                time.sleep(0.5)

            self.parallel_scanner.start_parallel_scan()
            self.current_mode = SwitchMode.PARALLEL_SCAN
            self.df_frequency = None

        except Exception as e:
            self.log_error(f'Error force switching to parallel: {e}')
