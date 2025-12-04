"""
Drone Detection Module
Pattern matching and fingerprinting for drone signals.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class DroneSignature:
    """Drone signal signature."""

    name: str
    frequency_ranges: List[tuple]  # List of (start, end) tuples
    pattern_type: str  # 'burst', 'chirp', 'hopping'
    min_duration_ms: Optional[float] = None
    max_duration_ms: Optional[float] = None
    bandwidth_hz: Optional[float] = None
    hop_rate_hz: Optional[float] = None


class DroneDetector:
    """Detects and classifies drone signals."""

    def __init__(self, config: dict = None):
        """Initialize drone detector."""
        self.config = config or {}
        self.known_signatures = self._load_signatures()
        self.detection_history = []

    def _load_signatures(self) -> List[DroneSignature]:
        """Load known drone signatures."""
        signatures = [
            DroneSignature(
                name='Generic 433MHz Telemetry',
                frequency_ranges=[(433e6, 434.8e6)],
                pattern_type='burst',
                min_duration_ms=10,
                max_duration_ms=500,
            ),
            DroneSignature(
                name='Generic 915MHz Telemetry',
                frequency_ranges=[(902e6, 928e6)],
                pattern_type='burst',
                min_duration_ms=10,
                max_duration_ms=500,
            ),
            DroneSignature(
                name='LoRa Drone Link',
                frequency_ranges=[(868e6, 868.6e6)],
                pattern_type='chirp',
                bandwidth_hz=125000,
            ),
        ]
        return signatures

    def analyze_signal(self, signal_hit, samples: np.ndarray = None) -> Optional[Dict[str, Any]]:
        """Analyze a signal for drone characteristics."""
        freq = signal_hit.frequency_hz
        bandwidth = signal_hit.bandwidth_hz

        matches = []
        for sig in self.known_signatures:
            if self._freq_in_ranges(freq, sig.frequency_ranges):
                confidence = self._calculate_match_confidence(signal_hit, sig, samples)
                if confidence > 0.5:
                    matches.append(
                        {
                            'signature': sig.name,
                            'confidence': confidence,
                            'pattern_type': sig.pattern_type,
                        }
                    )

        if matches:
            best_match = max(matches, key=lambda x: x['confidence'])
            result = {
                'detected': True,
                'timestamp': time.time(),
                'frequency_hz': freq,
                'signature': best_match['signature'],
                'confidence': best_match['confidence'],
                'pattern_type': best_match['pattern_type'],
                'bandwidth_hz': bandwidth,
                'power_dbm': signal_hit.power_dbm,
            }
            self.detection_history.append(result)
            logger.info(f"Drone detected: {best_match['signature']} at {freq/1e6:.3f} MHz")
            return result

        return None

    def _freq_in_ranges(self, freq: float, ranges: List[tuple]) -> bool:
        """Check if frequency is in any of the given ranges."""
        return any(start <= freq <= end for start, end in ranges)

    def _calculate_match_confidence(self, signal_hit, signature: DroneSignature, samples) -> float:
        """Calculate confidence that signal matches signature."""
        confidence = 0.5
        if signature.bandwidth_hz:
            bw_ratio = signal_hit.bandwidth_hz / signature.bandwidth_hz
            if 0.8 <= bw_ratio <= 1.2:
                confidence += 0.2
        if samples is not None and len(samples) > 0:
            pattern_match = self._analyze_pattern(samples, signature)
            confidence += pattern_match * 0.3
        return min(1.0, confidence)

    def _analyze_pattern(self, samples: np.ndarray, signature: DroneSignature) -> float:
        """Analyze temporal pattern of samples."""
        try:
            envelope = np.abs(samples)
            if signature.pattern_type == 'burst':
                threshold = np.mean(envelope) + np.std(envelope)
                bursts = envelope > threshold
                transitions = np.diff(bursts.astype(int))
                num_bursts = np.sum(transitions > 0)
                if num_bursts > 0:
                    return min(1.0, num_bursts / 10.0)
        except Exception as e:
            logger.error(f'Error analyzing pattern: {e}')
        return 0.0
