"""
Spectrum Scanner Module
Performs FFT-based spectrum sweeps and signal detection.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from scipy import signal
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)


@dataclass
class SignalHit:
    """Represents a detected signal."""
    frequency_hz: float
    power_dbm: float
    bandwidth_hz: float
    timestamp: float
    center_freq: float  # SDR center frequency when detected
    confidence: float = 1.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'frequency_hz': self.frequency_hz,
            'power_dbm': self.power_dbm,
            'bandwidth_hz': self.bandwidth_hz,
            'timestamp': self.timestamp,
            'center_freq': self.center_freq,
            'confidence': self.confidence
        }


class SpectrumScanner:
    """FFT-based spectrum scanner for signal detection."""
    
    def __init__(self, sdr_controller, config: dict = None):
        """Initialize spectrum scanner.
        
        Args:
            sdr_controller: SDRController instance
            config: Scanning configuration dictionary
        """
        self.sdr = sdr_controller
        self.config = config or {}
        self.num_sdrs = len(self.sdr.sdrs) if hasattr(self.sdr, 'sdrs') else 1
        
        # Scanning parameters
        self.fft_size = self.config.get('fft_size', 1024)
        self.fft_step_hz = self.config.get('fft_step_hz', 25000)
        self.threshold_dbm = self.config.get('detection_threshold_dbm', -60.0)
        self.integration_time_ms = self.config.get('integration_time_ms', 100)
        self.num_averages = max(1, int(self.integration_time_ms / 10))
        
        # Noise floor estimation
        self.noise_floor_dbm = -100.0
        self.noise_floor_calibrated = False
        
        logger.info(f"SpectrumScanner initialized with {self.num_sdrs} SDR(s)")
        
    def calibrate_noise_floor(self, num_samples: int = 100) -> float:
        """Calibrate noise floor by measuring ambient noise.
        
        Args:
            num_samples: Number of samples for calibration
            
        Returns:
            Noise floor in dBm
        """
        logger.info("Calibrating noise floor...")
        
        try:
            power_samples = []
            
            for _ in range(num_samples):
                samples = self.sdr.read_samples(self.fft_size)
                if not samples or len(samples[0]) == 0:
                    continue
                
                # Use first SDR for noise floor
                psd = self._compute_psd(samples[0])
                power_samples.append(np.mean(psd))
            
            if power_samples:
                self.noise_floor_dbm = np.median(power_samples)
                self.noise_floor_calibrated = True
                logger.info(f"Noise floor calibrated: {self.noise_floor_dbm:.2f} dBm")
            else:
                logger.warning("Failed to calibrate noise floor, using default")
                self.noise_floor_dbm = -100.0
                
        except Exception as e:
            logger.error(f"Error calibrating noise floor: {e}")
            self.noise_floor_dbm = -100.0
        
        return self.noise_floor_dbm
    
    def _compute_psd(self, samples: np.ndarray) -> np.ndarray:
        """Compute power spectral density.
        
        Args:
            samples: Complex IQ samples
            
        Returns:
            Power spectral density in dBm
        """
        # Compute FFT
        fft_result = np.fft.fft(samples)
        fft_shifted = np.fft.fftshift(fft_result)
        
        # Convert to power (magnitude squared)
        power = np.abs(fft_shifted) ** 2
        
        # Convert to dBm (assuming 50 ohm impedance)
        # Power in dBm = 10 * log10(power) - calibration_offset
        with np.errstate(divide='ignore', invalid='ignore'):
            power_dbm = 10 * np.log10(power) - 60  # Rough calibration
            power_dbm[np.isinf(power_dbm)] = -120  # Handle -inf
        
        return power_dbm
    
    def scan_frequency_range(
        self,
        start_hz: float,
        end_hz: float,
        step_hz: Optional[float] = None
    ) -> List[SignalHit]:
        """Scan a frequency range and detect signals.
        
        Args:
            start_hz: Start frequency in Hz
            end_hz: End frequency in Hz
            step_hz: Step size (uses config default if None)
            
        Returns:
            List of detected signals
        """
        step_hz = step_hz or self.fft_step_hz
        detected_signals = []
        
        logger.info(f"Scanning {start_hz/1e6:.3f} - {end_hz/1e6:.3f} MHz")
        
        try:
            # Calculate sweep parameters
            bandwidth = self.sdr.sample_rate
            num_steps = int((end_hz - start_hz) / step_hz) + 1
            
            for step in range(num_steps):
                center_freq = start_hz + (step * step_hz) + (bandwidth / 2)
                
                # Don't scan beyond end frequency
                if center_freq - bandwidth/2 > end_hz:
                    break
                
                # Tune SDR
                self.sdr.set_frequency(int(center_freq))
                time.sleep(0.01)  # Allow tuning to settle
                
                # Collect and average multiple samples
                psd_avg = np.zeros(self.fft_size)
                
                for _ in range(self.num_averages):
                    samples = self.sdr.read_samples(self.fft_size)
                    if not samples or len(samples[0]) == 0:
                        continue
                    
                    psd = self._compute_psd(samples[0])
                    psd_avg += psd
                
                psd_avg /= self.num_averages
                
                # Detect peaks in this frequency chunk
                hits = self._detect_peaks(psd_avg, center_freq)
                detected_signals.extend(hits)
                
                if step % 10 == 0:
                    progress = (step / num_steps) * 100
                    logger.debug(f"Scan progress: {progress:.1f}%")
        
        except Exception as e:
            logger.error(f"Error during frequency scan: {e}")
        
        logger.info(f"Scan complete: {len(detected_signals)} signals detected")
        return detected_signals
    
    def _detect_peaks(
        self,
        psd: np.ndarray,
        center_freq: float
    ) -> List[SignalHit]:
        """Detect signal peaks in power spectral density.
        
        Args:
            psd: Power spectral density array in dBm
            center_freq: Center frequency of the PSD
            
        Returns:
            List of detected signal hits
        """
        hits = []
        
        try:
            # Find peaks above threshold
            threshold = max(self.threshold_dbm, self.noise_floor_dbm + 10)
            
            # Use scipy to find peaks
            peak_indices, properties = signal.find_peaks(
                psd,
                height=threshold,
                distance=5,  # Minimum 5 bins between peaks
                prominence=5  # Minimum 5 dB prominence
            )
            
            if len(peak_indices) == 0:
                return hits
            
            # Convert peak indices to frequencies
            freq_span = self.sdr.sample_rate
            freqs = np.linspace(
                center_freq - freq_span/2,
                center_freq + freq_span/2,
                len(psd)
            )
            
            for idx in peak_indices:
                # Estimate bandwidth by finding -3dB points
                peak_power = psd[idx]
                bandwidth = self._estimate_bandwidth(psd, idx, peak_power)
                
                hit = SignalHit(
                    frequency_hz=freqs[idx],
                    power_dbm=float(peak_power),
                    bandwidth_hz=bandwidth,
                    timestamp=time.time(),
                    center_freq=center_freq,
                    confidence=self._calculate_confidence(peak_power)
                )
                
                hits.append(hit)
                logger.debug(
                    f"Signal detected: {hit.frequency_hz/1e6:.6f} MHz, "
                    f"{hit.power_dbm:.1f} dBm, BW: {hit.bandwidth_hz/1e3:.1f} kHz"
                )
        
        except Exception as e:
            logger.error(f"Error detecting peaks: {e}")
        
        return hits
    
    def _estimate_bandwidth(
        self,
        psd: np.ndarray,
        peak_idx: int,
        peak_power: float
    ) -> float:
        """Estimate signal bandwidth using -3dB method.
        
        Args:
            psd: Power spectral density array
            peak_idx: Index of peak
            peak_power: Peak power in dBm
            
        Returns:
            Estimated bandwidth in Hz
        """
        threshold = peak_power - 3  # -3dB point
        
        # Find left edge
        left_idx = peak_idx
        while left_idx > 0 and psd[left_idx] > threshold:
            left_idx -= 1
        
        # Find right edge
        right_idx = peak_idx
        while right_idx < len(psd) - 1 and psd[right_idx] > threshold:
            right_idx += 1
        
        # Calculate bandwidth
        bin_width = self.sdr.sample_rate / len(psd)
        bandwidth = (right_idx - left_idx) * bin_width
        
        return float(bandwidth)
    
    def _calculate_confidence(self, signal_power: float) -> float:
        """Calculate detection confidence based on signal power.
        
        Args:
            signal_power: Signal power in dBm
            
        Returns:
            Confidence value between 0 and 1
        """
        # Higher power = higher confidence
        snr = signal_power - self.noise_floor_dbm
        confidence = min(1.0, max(0.1, snr / 50.0))
        return confidence
    
    def scan_band_list(self, bands: List[Dict[str, Any]]) -> Dict[str, List[SignalHit]]:
        """Scan multiple frequency bands.
        
        If multiple SDRs available (mobile_multi mode), distributes bands across SDRs.
        
        Args:
            bands: List of band dictionaries with 'start_hz' and 'end_hz'
            
        Returns:
            Dictionary mapping band names to lists of detected signals
        """
        results = {}
        
        # If multiple SDRs available, distribute the work
        if self.num_sdrs > 1:
            logger.info(f"Mobile Multi: Distributing {len(bands)} bands across {self.num_sdrs} SDRs")
            return self._scan_band_list_multi(bands)
        
        # Single SDR - sequential scanning
        for band in bands:
            band_name = band.get('name', 'Unknown')
            start_hz = band.get('start_hz')
            end_hz = band.get('end_hz')
            
            if start_hz is None or end_hz is None:
                logger.warning(f"Invalid band definition: {band}")
                continue
            
            logger.info(f"Scanning band: {band_name}")
            hits = self.scan_frequency_range(start_hz, end_hz)
            results[band_name] = hits
        
        return results
    
    def _scan_band_list_multi(self, bands: List[Dict[str, Any]]) -> Dict[str, List[SignalHit]]:
        """Scan bands using multiple SDRs in mobile_multi mode.
        
        Each SDR scans a subset of bands sequentially, but all SDRs work simultaneously.
        This is faster than single SDR but simpler than parallel mode.
        
        Args:
            bands: List of band dictionaries
            
        Returns:
            Dictionary mapping band names to lists of detected signals
        """
        import threading
        from queue import Queue
        
        results = {}
        result_queue = Queue()
        
        # Distribute bands across SDRs
        bands_per_sdr = [[] for _ in range(self.num_sdrs)]
        for i, band in enumerate(bands):
            sdr_idx = i % self.num_sdrs
            bands_per_sdr[sdr_idx].append(band)
        
        def scan_worker(sdr_idx, assigned_bands):
            """Worker thread for one SDR."""
            for band in assigned_bands:
                band_name = band.get('name', 'Unknown')
                start_hz = band.get('start_hz')
                end_hz = band.get('end_hz')
                
                if start_hz is None or end_hz is None:
                    continue
                
                logger.info(f"SDR{sdr_idx}: Scanning {band_name}")
                
                # Temporarily tune this SDR
                original_freq = self.sdr.sdrs[sdr_idx].center_freq if sdr_idx < len(self.sdr.sdrs) else None
                
                try:
                    # Scan the band using this specific SDR
                    hits = self._scan_with_specific_sdr(sdr_idx, start_hz, end_hz)
                    result_queue.put((band_name, hits))
                except Exception as e:
                    logger.error(f"SDR{sdr_idx} error scanning {band_name}: {e}")
                finally:
                    # Restore original frequency if needed
                    if original_freq and sdr_idx < len(self.sdr.sdrs):
                        try:
                            self.sdr.sdrs[sdr_idx].center_freq = original_freq
                        except:
                            pass
        
        # Start worker threads
        threads = []
        for sdr_idx, assigned_bands in enumerate(bands_per_sdr):
            if assigned_bands:  # Only start thread if SDR has bands to scan
                t = threading.Thread(target=scan_worker, args=(sdr_idx, assigned_bands))
                t.start()
                threads.append(t)
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Collect results
        while not result_queue.empty():
            band_name, hits = result_queue.get()
            results[band_name] = hits
        
        return results
    
    def _scan_with_specific_sdr(self, sdr_idx: int, start_hz: float, end_hz: float) -> List[SignalHit]:
        """Scan using a specific SDR from the array.
        
        Args:
            sdr_idx: SDR index to use
            start_hz: Start frequency
            end_hz: End frequency
            
        Returns:
            List of detected signals
        """
        detected_signals = []
        
        try:
            if sdr_idx >= len(self.sdr.sdrs):
                return detected_signals
            
            sdr = self.sdr.sdrs[sdr_idx]
            bandwidth = sdr.sample_rate
            num_steps = int((end_hz - start_hz) / self.fft_step_hz) + 1
            
            for step in range(num_steps):
                center_freq = start_hz + (step * self.fft_step_hz) + (bandwidth / 2)
                
                if center_freq - bandwidth/2 > end_hz:
                    break
                
                # Tune this specific SDR
                sdr.center_freq = int(center_freq)
                time.sleep(0.01)
                
                # Collect and average samples
                psd_avg = np.zeros(self.fft_size)
                
                for _ in range(self.num_averages):
                    samples = sdr.read_samples(self.fft_size)
                    if len(samples) == 0:
                        continue
                    
                    psd = self._compute_psd(samples)
                    psd_avg += psd
                
                psd_avg /= self.num_averages
                
                # Detect peaks
                hits = self._detect_peaks(psd_avg, center_freq)
                detected_signals.extend(hits)
        
        except Exception as e:
            logger.error(f"Error scanning with SDR{sdr_idx}: {e}")
        
        return detected_signals
    
    def quick_scan(self, frequencies: List[float], bandwidth: float = 100000) -> List[SignalHit]:
        """Quickly scan specific frequencies.
        
        Args:
            frequencies: List of frequencies to check in Hz
            bandwidth: Bandwidth around each frequency to scan
            
        Returns:
            List of detected signals
        """
        detected_signals = []
        
        for freq in frequencies:
            start = freq - bandwidth / 2
            end = freq + bandwidth / 2
            hits = self.scan_frequency_range(start, end)
            detected_signals.extend(hits)
        
        return detected_signals

