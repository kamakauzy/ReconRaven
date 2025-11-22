"""
Digital Demodulation Module
Handles DMR, P25, NXDN, ProVoice, and Fusion using DSD.
"""

import logging
import subprocess
import threading
import queue
from typing import Optional, Callable
from enum import Enum

logger = logging.getLogger(__name__)


class DigitalMode(Enum):
    """Digital demodulation modes."""
    DMR = "dmr"
    P25 = "p25"
    NXDN = "nxdn"
    PROVOICE = "provoice"
    FUSION = "fusion"
    AUTO = "auto"


class DigitalDemodulator:
    """Demodulates digital signals using DSD."""
    
    def __init__(self, config: dict = None):
        """Initialize digital demodulator."""
        self.config = config or {}
        self.rtl_process: Optional[subprocess.Popen] = None
        self.dsd_process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.data_callback: Optional[Callable] = None
        
    def start_demodulation(
        self,
        frequency_hz: float,
        mode: DigitalMode = DigitalMode.AUTO,
        output_file: Optional[str] = None
    ) -> bool:
        """Start demodulating a digital signal.
        
        Args:
            frequency_hz: Frequency to demodulate
            mode: Digital mode (or AUTO for auto-detection)
            output_file: Optional output file
            
        Returns:
            True if started successfully
        """
        if self.is_running:
            logger.warning("Digital demodulator already running")
            return False
        
        try:
            # Start rtl_fm to provide raw audio to DSD
            rtl_cmd = [
                'rtl_fm',
                '-f', str(int(frequency_hz)),
                '-M', 'raw',
                '-s', '240k',
                '-'
            ]
            
            self.rtl_process = subprocess.Popen(
                rtl_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Build DSD command based on mode
            dsd_cmd = ['dsd', '-i', '-']
            
            if mode == DigitalMode.AUTO:
                dsd_cmd.extend(['-fa'])  # Auto frame type
            elif mode == DigitalMode.DMR:
                dsd_cmd.extend(['-fd'])
            elif mode == DigitalMode.P25:
                dsd_cmd.extend(['-fp'])
            elif mode == DigitalMode.NXDN:
                dsd_cmd.extend(['-fn'])
            
            if output_file:
                dsd_cmd.extend(['-w', output_file])
            
            # Start DSD process
            self.dsd_process = subprocess.Popen(
                dsd_cmd,
                stdin=self.rtl_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_running = True
            
            # Start monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_output,
                daemon=True
            )
            monitor_thread.start()
            
            logger.info(f"Digital demodulation started: {frequency_hz/1e6:.6f} MHz, mode: {mode.value}")
            return True
            
        except FileNotFoundError as e:
            logger.error(f"Required tool not found: {e}. Install rtl-sdr and dsd.")
            return False
        except Exception as e:
            logger.error(f"Error starting digital demodulation: {e}")
            return False
    
    def _monitor_output(self):
        """Monitor DSD output."""
        try:
            while self.is_running and self.dsd_process:
                line = self.dsd_process.stderr.readline()
                if not line:
                    break
                
                decoded = line.decode('utf-8', errors='ignore').strip()
                if decoded:
                    logger.debug(f"DSD: {decoded}")
                    
                    if self.data_callback:
                        self.data_callback(decoded)
        
        except Exception as e:
            logger.error(f"Error monitoring DSD output: {e}")
    
    def stop_demodulation(self):
        """Stop demodulation."""
        self.is_running = False
        
        for process in [self.dsd_process, self.rtl_process]:
            if process:
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except:
                    process.kill()
        
        self.dsd_process = None
        self.rtl_process = None
    
    def __del__(self):
        self.stop_demodulation()


