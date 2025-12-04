#!/usr/bin/env python3
"""
Signal Correlation Engine
Detects temporal relationships, patterns, and behavioral profiles
"""

from collections import defaultdict
from datetime import datetime
from typing import Dict, List

import numpy as np

from database import get_db


class CorrelationEngine:
    """Analyzes signal relationships and behavioral patterns"""

    def __init__(self):
        self.db = get_db()

    # ========== TEMPORAL CORRELATION ==========

    def find_temporal_correlations(self, time_window_seconds: int = 10) -> List[Dict]:
        """Find signals that occur together within a time window

        Args:
            time_window_seconds: Max time difference to consider correlated

        Returns:
            List of correlation pairs with statistics
        """
        cursor = self.db.conn.cursor()

        # Get all signal detections with timestamps
        cursor.execute(
            """
            SELECT 
                s1.frequency_hz as freq1,
                s2.frequency_hz as freq2,
                s1.detected_at as time1,
                s2.detected_at as time2,
                ABS(JULIANDAY(s1.detected_at) - JULIANDAY(s2.detected_at)) * 86400 as time_diff_sec
            FROM signals s1
            INNER JOIN signals s2 ON s1.id < s2.id
            WHERE s1.frequency_hz != s2.frequency_hz
              AND ABS(JULIANDAY(s1.detected_at) - JULIANDAY(s2.detected_at)) * 86400 <= ?
            ORDER BY time_diff_sec
        """,
            (time_window_seconds,),
        )

        correlations = defaultdict(lambda: {'count': 0, 'avg_delay': [], 'std_delay': 0})

        for row in cursor.fetchall():
            freq1, freq2, time1, time2, time_diff = row
            pair = tuple(sorted([freq1, freq2]))  # Normalize pair
            correlations[pair]['count'] += 1
            correlations[pair]['avg_delay'].append(time_diff)

        # Calculate statistics
        results = []
        for (freq1, freq2), data in correlations.items():
            if data['count'] < 3:  # Need at least 3 occurrences to be meaningful
                continue

            delays = data['avg_delay']
            avg_delay = np.mean(delays)
            std_delay = np.std(delays)

            results.append(
                {
                    'frequency1_hz': freq1,
                    'frequency2_hz': freq2,
                    'frequency1_mhz': freq1 / 1e6,
                    'frequency2_mhz': freq2 / 1e6,
                    'occurrences': data['count'],
                    'avg_delay_sec': avg_delay,
                    'std_delay_sec': std_delay,
                    'confidence': min(
                        data['count'] / 10.0, 1.0
                    ),  # More occurrences = higher confidence
                    'pattern_type': self._classify_pattern(avg_delay, std_delay),
                }
            )

        # Sort by confidence
        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results

    def find_sequential_patterns(self, max_sequence_length: int = 5) -> List[Dict]:
        """Find repeated sequences of signals (A→B→C→...)

        Args:
            max_sequence_length: Maximum length of sequence to detect

        Returns:
            List of detected sequences
        """
        cursor = self.db.conn.cursor()

        # Get signals ordered by time
        cursor.execute("""
            SELECT frequency_hz, detected_at
            FROM signals
            ORDER BY detected_at
        """)

        signals = [(row[0], row[1]) for row in cursor.fetchall()]

        # Find repeating sequences
        sequences = defaultdict(int)

        for i in range(len(signals) - max_sequence_length + 1):
            for seq_len in range(2, max_sequence_length + 1):
                seq = tuple([s[0] for s in signals[i : i + seq_len]])
                sequences[seq] += 1

        # Filter and format results
        results = []
        for seq, count in sequences.items():
            if count < 2:  # Need at least 2 occurrences
                continue

            results.append(
                {
                    'sequence': [f'{f/1e6:.3f} MHz' for f in seq],
                    'frequencies_hz': list(seq),
                    'occurrences': count,
                    'length': len(seq),
                    'confidence': min(count / 5.0, 1.0),
                }
            )

        results.sort(key=lambda x: (x['confidence'], x['length']), reverse=True)
        return results

    def _classify_pattern(self, avg_delay: float, std_delay: float) -> str:
        """Classify the type of correlation pattern"""
        if std_delay < 0.5:  # Very consistent timing
            if avg_delay < 1.0:
                return 'synchronized'  # Near-simultaneous
            return 'command-response'  # Consistent delay (command→ack)
        if std_delay < 2.0:
            return 'periodic'  # Regular but with jitter
        return 'associated'  # Co-occur but timing varies

    # ========== BEHAVIORAL PROFILING ==========

    def get_device_behavior_profile(self, frequency_hz: float) -> Dict:
        """Build a behavioral profile for a specific frequency

        Returns:
            Profile with timing patterns, burst characteristics, etc.
        """
        cursor = self.db.conn.cursor()

        # Get all detections for this frequency
        cursor.execute(
            """
            SELECT 
                detected_at,
                power_dbm,
                delta_db
            FROM signals
            WHERE frequency_hz = ?
            ORDER BY detected_at
        """,
            (frequency_hz,),
        )

        detections = cursor.fetchall()

        if len(detections) < 2:
            return {'error': 'Insufficient data'}

        # Parse timestamps
        timestamps = [datetime.fromisoformat(d[0]) for d in detections]
        powers = [d[1] for d in detections]

        # Calculate inter-transmission intervals
        intervals = [
            (timestamps[i + 1] - timestamps[i]).total_seconds() for i in range(len(timestamps) - 1)
        ]

        # Time-of-day analysis
        hours = [t.hour for t in timestamps]
        hour_counts = defaultdict(int)
        for h in hours:
            hour_counts[h] += 1

        # Detect periodicity
        if len(intervals) >= 3:
            avg_interval = np.mean(intervals)
            std_interval = np.std(intervals)
            is_periodic = std_interval < (avg_interval * 0.3)  # Low variance = periodic
        else:
            avg_interval = 0
            std_interval = 0
            is_periodic = False

        # Burst detection (multiple transmissions in quick succession)
        burst_threshold = 2.0  # seconds
        bursts = []
        current_burst = [timestamps[0]]

        for i in range(1, len(timestamps)):
            if intervals[i - 1] < burst_threshold:
                current_burst.append(timestamps[i])
            else:
                if len(current_burst) > 1:
                    bursts.append(current_burst)
                current_burst = [timestamps[i]]

        if len(current_burst) > 1:
            bursts.append(current_burst)

        return {
            'frequency_hz': frequency_hz,
            'frequency_mhz': frequency_hz / 1e6,
            'total_detections': len(detections),
            'first_seen': str(timestamps[0]),
            'last_seen': str(timestamps[-1]),
            'time_span_hours': (timestamps[-1] - timestamps[0]).total_seconds() / 3600,
            # Timing patterns
            'avg_interval_sec': avg_interval,
            'std_interval_sec': std_interval,
            'is_periodic': is_periodic,
            'transmission_rate_per_hour': len(detections)
            / max((timestamps[-1] - timestamps[0]).total_seconds() / 3600, 1),
            # Time-of-day patterns
            'most_active_hour': max(hour_counts, key=hour_counts.get) if hour_counts else None,
            'hour_distribution': dict(hour_counts),
            # Burst characteristics
            'burst_count': len(bursts),
            'avg_burst_size': np.mean([len(b) for b in bursts]) if bursts else 0,
            # Power characteristics
            'avg_power_dbm': np.mean(powers),
            'max_power_dbm': max(powers),
            'min_power_dbm': min(powers),
            'power_variance': np.var(powers),
            # Classification
            'device_type_guess': self._classify_device_behavior(
                avg_interval, is_periodic, len(bursts), len(detections)
            ),
        }

    def _classify_device_behavior(
        self, avg_interval: float, is_periodic: bool, burst_count: int, total_detections: int
    ) -> str:
        """Guess device type from behavioral characteristics"""

        # Sensor (periodic reporting)
        if is_periodic and 30 < avg_interval < 3600:
            return 'Sensor (periodic reporting)'

        # Remote control (burst transmissions, infrequent)
        if burst_count > 0 and total_detections < 20:
            return 'Remote Control (burst)'

        # Always-on beacon
        if is_periodic and avg_interval < 10:
            return 'Beacon (high-rate)'

        # Event-driven (irregular timing)
        if not is_periodic and total_detections > 10:
            return 'Event-Driven Device'

        return 'Unknown Pattern'

    # ========== NETWORK MAPPING ==========

    def build_device_network(self) -> Dict:
        """Build a network graph of device relationships

        Returns:
            Network structure with nodes (devices) and edges (relationships)
        """
        correlations = self.find_temporal_correlations(time_window_seconds=10)

        # Build nodes (unique frequencies)
        nodes = set()
        for corr in correlations:
            nodes.add(corr['frequency1_hz'])
            nodes.add(corr['frequency2_hz'])

        # Get device info for each node
        node_data = []
        for freq in nodes:
            device = self.db.get_device_by_frequency(freq)
            profile = self.get_device_behavior_profile(freq)

            node_data.append(
                {
                    'frequency_hz': freq,
                    'frequency_mhz': freq / 1e6,
                    'name': device.get('name', f'{freq/1e6:.3f} MHz')
                    if device
                    else f'{freq/1e6:.3f} MHz',
                    'device_type': profile.get('device_type_guess', 'Unknown'),
                    'detection_count': profile.get('total_detections', 0),
                    'is_hub': False,  # Will calculate below
                }
            )

        # Build edges (correlations)
        edges = []
        for corr in correlations:
            edges.append(
                {
                    'source': corr['frequency1_hz'],
                    'target': corr['frequency2_hz'],
                    'weight': corr['occurrences'],
                    'avg_delay': corr['avg_delay_sec'],
                    'pattern_type': corr['pattern_type'],
                }
            )

        # Identify hub nodes (most connections)
        connection_count = defaultdict(int)
        for edge in edges:
            connection_count[edge['source']] += 1
            connection_count[edge['target']] += 1

        # Mark top 20% as hubs
        if connection_count:
            hub_threshold = (
                sorted(connection_count.values(), reverse=True)[int(len(connection_count) * 0.2)]
                if len(connection_count) > 5
                else 2
            )
            for node in node_data:
                if connection_count.get(node['frequency_hz'], 0) >= hub_threshold:
                    node['is_hub'] = True

        return {
            'nodes': node_data,
            'edges': edges,
            'summary': {
                'total_devices': len(node_data),
                'total_connections': len(edges),
                'hub_count': sum(1 for n in node_data if n['is_hub']),
            },
        }

    # ========== ANOMALY DETECTION ==========

    def detect_behavioral_anomalies(self) -> List[Dict]:
        """Detect devices with unusual or changed behavior

        Returns:
            List of anomalies with descriptions
        """
        anomalies = []

        # Get all active frequencies
        cursor = self.db.conn.cursor()
        cursor.execute('SELECT DISTINCT frequency_hz FROM signals')
        frequencies = [row[0] for row in cursor.fetchall()]

        for freq in frequencies:
            profile = self.get_device_behavior_profile(freq)

            if 'error' in profile:
                continue

            # Check for anomalies

            # 1. Sudden appearance
            if profile['total_detections'] < 5 and profile['time_span_hours'] < 1:
                anomalies.append(
                    {
                        'frequency_hz': freq,
                        'frequency_mhz': freq / 1e6,
                        'anomaly_type': 'new_device',
                        'severity': 'medium',
                        'description': f"New device appeared recently ({profile['total_detections']} detections)",
                    }
                )

            # 2. High activity burst
            if profile.get('transmission_rate_per_hour', 0) > 60:  # More than 1/minute
                anomalies.append(
                    {
                        'frequency_hz': freq,
                        'frequency_mhz': freq / 1e6,
                        'anomaly_type': 'high_activity',
                        'severity': 'high',
                        'description': f"Very high transmission rate ({profile['transmission_rate_per_hour']:.1f}/hour)",
                    }
                )

            # 3. Unusual timing pattern
            if profile.get('burst_count', 0) > 10 and not profile.get('is_periodic', False):
                anomalies.append(
                    {
                        'frequency_hz': freq,
                        'frequency_mhz': freq / 1e6,
                        'anomaly_type': 'unusual_pattern',
                        'severity': 'medium',
                        'description': f"Irregular burst pattern ({profile['burst_count']} bursts detected)",
                    }
                )

        return anomalies


# ========== CLI INTERFACE ==========

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Signal Correlation Analysis')
    parser.add_argument('--correlations', action='store_true', help='Find temporal correlations')
    parser.add_argument('--sequences', action='store_true', help='Find sequential patterns')
    parser.add_argument('--profile', type=float, help='Get behavior profile for frequency (MHz)')
    parser.add_argument('--network', action='store_true', help='Build device network graph')
    parser.add_argument('--anomalies', action='store_true', help='Detect behavioral anomalies')

    args = parser.parse_args()

    engine = CorrelationEngine()

    if args.correlations:
        print('\n' + '=' * 70)
        print('TEMPORAL CORRELATIONS')
        print('=' * 70)
        results = engine.find_temporal_correlations()
        for i, corr in enumerate(results[:20], 1):  # Top 20
            print(f"\n{i}. {corr['frequency1_mhz']:.3f} MHz ↔ {corr['frequency2_mhz']:.3f} MHz")
            print(f"   Pattern: {corr['pattern_type']}")
            print(f"   Occurrences: {corr['occurrences']}")
            print(f"   Avg Delay: {corr['avg_delay_sec']:.2f}s (±{corr['std_delay_sec']:.2f}s)")
            print(f"   Confidence: {corr['confidence']*100:.0f}%")

    elif args.sequences:
        print('\n' + '=' * 70)
        print('SEQUENTIAL PATTERNS')
        print('=' * 70)
        results = engine.find_sequential_patterns()
        for i, seq in enumerate(results[:10], 1):
            print(f"\n{i}. {' → '.join(seq['sequence'])}")
            print(f"   Occurrences: {seq['occurrences']}")
            print(f"   Confidence: {seq['confidence']*100:.0f}%")

    elif args.profile:
        freq_hz = args.profile * 1e6
        print('\n' + '=' * 70)
        print(f'BEHAVIORAL PROFILE: {args.profile:.3f} MHz')
        print('=' * 70)
        profile = engine.get_device_behavior_profile(freq_hz)

        if 'error' in profile:
            print(f"\nError: {profile['error']}")
        else:
            print(f"\nDevice Type: {profile['device_type_guess']}")
            print(f"Total Detections: {profile['total_detections']}")
            print(f"Time Span: {profile['time_span_hours']:.1f} hours")
            print(f"Transmission Rate: {profile['transmission_rate_per_hour']:.1f} per hour")

            if profile['is_periodic']:
                print('\nPeriodic Transmission:')
                print(
                    f"  Interval: {profile['avg_interval_sec']:.1f}s (±{profile['std_interval_sec']:.1f}s)"
                )

            if profile['burst_count'] > 0:
                print('\nBurst Activity:')
                print(f"  Burst Count: {profile['burst_count']}")
                print(f"  Avg Burst Size: {profile['avg_burst_size']:.1f} transmissions")

            if profile['most_active_hour'] is not None:
                print(f"\nMost Active: {profile['most_active_hour']:02d}:00")

    elif args.network:
        print('\n' + '=' * 70)
        print('DEVICE NETWORK ANALYSIS')
        print('=' * 70)
        network = engine.build_device_network()

        print(f"\nDevices: {network['summary']['total_devices']}")
        print(f"Connections: {network['summary']['total_connections']}")
        print(f"Hubs: {network['summary']['hub_count']}")

        print('\n' + '-' * 70)
        print('HUB DEVICES (Most Connected)')
        print('-' * 70)
        hubs = [n for n in network['nodes'] if n['is_hub']]
        for hub in sorted(hubs, key=lambda x: x['detection_count'], reverse=True):
            print(f"  {hub['frequency_mhz']:.3f} MHz - {hub['name']}")
            print(f"    Type: {hub['device_type']}")

    elif args.anomalies:
        print('\n' + '=' * 70)
        print('BEHAVIORAL ANOMALIES')
        print('=' * 70)
        anomalies = engine.detect_behavioral_anomalies()

        if not anomalies:
            print('\nNo anomalies detected. All devices showing normal behavior.')
        else:
            for anomaly in anomalies:
                severity_emoji = {'low': '🟡', 'medium': '🟠', 'high': '🔴'}
                emoji = severity_emoji.get(anomaly['severity'], '⚪')
                print(
                    f"\n{emoji} {anomaly['frequency_mhz']:.3f} MHz - {anomaly['anomaly_type'].upper()}"
                )
                print(f"   {anomaly['description']}")

    else:
        parser.print_help()
