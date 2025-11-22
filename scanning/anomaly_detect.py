"""
Anomaly Detection Module
Detects signal anomalies that warrant deeper investigation or DF.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from collections import defaultdict, deque
import time

logger = logging.getLogger(__name__)


class SignalTracker:
    """Tracks signal persistence and characteristics over time."""
    
    def __init__(self, history_duration: float = 300):
        """Initialize signal tracker.
        
        Args:
            history_duration: How long to track signals (seconds)
        """
        self.history_duration = history_duration
        self.signal_history = defaultdict(lambda: deque(maxlen=100))
        self.persistent_signals = {}
        
    def update(self, frequency_hz: float, power_dbm: float, timestamp: float):
        """Update signal history.
        
        Args:
            frequency_hz: Signal frequency
            power_dbm: Signal power
            timestamp: Detection timestamp
        """
        # Round frequency to 10kHz bins for tracking
        freq_key = int(frequency_hz / 10000) * 10000
        
        self.signal_history[freq_key].append({
            'power': power_dbm,
            'timestamp': timestamp
        })
        
        # Update persistent signals
        history = self.signal_history[freq_key]
        if len(history) >= 3:
            # Signal seen multiple times
            avg_power = np.mean([h['power'] for h in history])
            self.persistent_signals[freq_key] = {
                'frequency_hz': frequency_hz,
                'avg_power_dbm': avg_power,
                'detections': len(history),
                'last_seen': timestamp
            }
    
    def is_new_signal(self, frequency_hz: float) -> bool:
        """Check if signal is newly detected.
        
        Args:
            frequency_hz: Signal frequency
            
        Returns:
            True if signal is new
        """
        freq_key = int(frequency_hz / 10000) * 10000
        return freq_key not in self.signal_history or len(self.signal_history[freq_key]) <= 1
    
    def cleanup_old_signals(self):
        """Remove old signal history."""
        current_time = time.time()
        
        for freq_key in list(self.signal_history.keys()):
            history = self.signal_history[freq_key]
            
            # Remove old entries
            while history and current_time - history[0]['timestamp'] > self.history_duration:
                history.popleft()
            
            # Remove empty histories
            if not history:
                del self.signal_history[freq_key]
                if freq_key in self.persistent_signals:
                    del self.persistent_signals[freq_key]


class AnomalyDetector:
    """Detects anomalous signals that warrant investigation."""
    
    def __init__(self, config: dict = None):
        """Initialize anomaly detector.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or {}
        self.threshold_dbm = self.config.get('strong_signal_dbm', -40)
        self.tracker = SignalTracker()
        self.anomaly_count = 0
        
    def check_anomalies(
        self,
        signals: List[Dict[str, Any]],
        enable_df_trigger: bool = True
    ) -> List[Dict[str, Any]]:
        """Check signals for anomalies.
        
        Args:
            signals: List of detected signals
            enable_df_trigger: Whether to flag signals for DF
            
        Returns:
            List of anomaly dictionaries
        """
        anomalies = []
        
        # Cleanup old signals
        self.tracker.cleanup_old_signals()
        
        for signal in signals:
            freq = signal.get('frequency_hz')
            power = signal.get('power_dbm')
            timestamp = signal.get('timestamp', time.time())
            
            if freq is None or power is None:
                continue
            
            # Update tracking
            self.tracker.update(freq, power, timestamp)
            
            # Check for anomalies
            anomaly_reasons = []
            trigger_df = False
            
            # 1. Strong signal detection
            if power > self.threshold_dbm:
                anomaly_reasons.append('strong_signal')
                trigger_df = enable_df_trigger
            
            # 2. New signal (not seen before)
            if self.tracker.is_new_signal(freq):
                anomaly_reasons.append('new_signal')
                if power > -50:  # Only trigger DF for strong new signals
                    trigger_df = enable_df_trigger
            
            # 3. Burst pattern detection
            if self._detect_burst_pattern(signal):
                anomaly_reasons.append('burst_pattern')
                trigger_df = enable_df_trigger
            
            # 4. Frequency hopping detection
            if self._detect_hopping_pattern(freq):
                anomaly_reasons.append('frequency_hopping')
                trigger_df = enable_df_trigger
            
            # 5. Power surge (significantly stronger than before)
            if self._detect_power_surge(freq, power):
                anomaly_reasons.append('power_surge')
                trigger_df = enable_df_trigger
            
            # Create anomaly entry if any reasons found
            if anomaly_reasons:
                self.anomaly_count += 1
                
                anomaly = {
                    'id': self.anomaly_count,
                    'frequency_hz': freq,
                    'power_dbm': power,
                    'bandwidth_hz': signal.get('bandwidth_hz', 25000),
                    'timestamp': timestamp,
                    'reasons': anomaly_reasons,
                    'trigger_df': trigger_df,
                    'priority': self._calculate_priority(anomaly_reasons, power),
                    'sdr_index': signal.get('sdr_index'),
                    'band_name': signal.get('band_name', 'unknown'),
                    'source': signal.get('source', 'unknown')
                }
                
                anomalies.append(anomaly)
                
                logger.info(
                    f"Anomaly #{self.anomaly_count}: {freq/1e6:.3f} MHz, "
                    f"{power:.1f} dBm, reasons: {', '.join(anomaly_reasons)}"
                )
        
        # Sort by priority
        anomalies.sort(key=lambda x: x['priority'], reverse=True)
        
        return anomalies
    
    def _detect_burst_pattern(self, signal: Dict[str, Any]) -> bool:
        """Detect if signal exhibits burst characteristics.
        
        Args:
            signal: Signal dictionary
            
        Returns:
            True if burst pattern detected
        """
        # Check bandwidth - bursts typically have wider bandwidth
        bandwidth = signal.get('bandwidth_hz', 0)
        if 10000 < bandwidth < 200000:
            return True
        
        # Could add more sophisticated burst detection with sample analysis
        return False
    
    def _detect_hopping_pattern(self, frequency_hz: float) -> bool:
        """Detect frequency hopping patterns.
        
        Args:
            frequency_hz: Signal frequency
            
        Returns:
            True if hopping pattern detected
        """
        # Check for multiple signals in nearby frequencies
        freq_key = int(frequency_hz / 10000) * 10000
        
        # Count nearby signals
        nearby_count = 0
        for tracked_freq in self.tracker.signal_history.keys():
            if abs(tracked_freq - freq_key) < 100000:  # Within 100kHz
                nearby_count += 1
        
        # Hopping if multiple nearby frequencies active
        return nearby_count >= 3
    
    def _detect_power_surge(self, frequency_hz: float, current_power: float) -> bool:
        """Detect sudden power increase.
        
        Args:
            frequency_hz: Signal frequency
            current_power: Current power level
            
        Returns:
            True if power surge detected
        """
        freq_key = int(frequency_hz / 10000) * 10000
        
        if freq_key in self.tracker.persistent_signals:
            avg_power = self.tracker.persistent_signals[freq_key]['avg_power_dbm']
            
            # Surge if 15dB or more increase
            if current_power - avg_power >= 15:
                return True
        
        return False
    
    def _calculate_priority(self, reasons: List[str], power_dbm: float) -> int:
        """Calculate anomaly priority score.
        
        Args:
            reasons: List of anomaly reasons
            power_dbm: Signal power
            
        Returns:
            Priority score (higher = more important)
        """
        priority = 0
        
        # Base priority from power
        priority += int((power_dbm + 100) / 10)  # 0-10 based on power
        
        # Add for each reason
        reason_scores = {
            'strong_signal': 5,
            'new_signal': 3,
            'burst_pattern': 4,
            'frequency_hopping': 5,
            'power_surge': 4
        }
        
        for reason in reasons:
            priority += reason_scores.get(reason, 1)
        
        return priority
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get anomaly detection statistics.
        
        Returns:
            Dictionary with statistics
        """
        return {
            'total_anomalies': self.anomaly_count,
            'tracked_signals': len(self.tracker.signal_history),
            'persistent_signals': len(self.tracker.persistent_signals),
            'persistent_list': list(self.tracker.persistent_signals.values())
        }

