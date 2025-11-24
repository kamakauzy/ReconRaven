#!/usr/bin/env python3
"""
ReconRaven Database Module - SIMPLIFIED FLAT SCHEMA
All data in minimal tables, complexity moved to frontend
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

class ReconRavenDB:
    """Simplified SQLite database for ReconRaven"""
    
    def __init__(self, db_path='reconraven.db'):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create simplified flat schema"""
        cursor = self.conn.cursor()
        
        # SINGLE FLAT TABLE for all detected signals
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency_hz REAL NOT NULL,
                band TEXT NOT NULL,
                power_dbm REAL NOT NULL,
                
                -- Baseline comparison
                baseline_power_dbm REAL,
                delta_db REAL,
                is_anomaly BOOLEAN DEFAULT 1,
                is_baseline BOOLEAN DEFAULT 0,
                
                -- Recording info (if recorded)
                recording_file TEXT,
                
                -- Device identification (if identified)
                device_name TEXT,
                device_type TEXT,
                manufacturer TEXT,
                
                -- Analysis results (if analyzed)
                modulation TEXT,
                bit_rate INTEGER,
                confidence REAL,
                analysis_data TEXT,
                
                -- Timestamps
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Simple baseline table (just freq + power averages)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS baseline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency_hz REAL NOT NULL UNIQUE,
                band TEXT NOT NULL,
                power_dbm REAL NOT NULL,
                std_dbm REAL DEFAULT 0,
                sample_count INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Simple recordings table (just metadata)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                frequency_hz REAL NOT NULL,
                band TEXT,
                signal_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_freq ON signals(frequency_hz)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_anomaly ON signals(is_anomaly)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(detected_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_baseline_freq ON baseline(frequency_hz)')
        
        self.conn.commit()
    
    # ========== BASELINE MANAGEMENT (SIMPLE) ==========
    
    def add_baseline_frequency(self, freq: float, band: str, power: float, std: float = 0):
        """Add or update baseline frequency"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO baseline (frequency_hz, band, power_dbm, std_dbm, sample_count)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(frequency_hz) DO UPDATE SET
                power_dbm = ((power_dbm * sample_count) + ?) / (sample_count + 1),
                std_dbm = ?,
                sample_count = sample_count + 1
        ''', (freq, band, power, std, power, std))
        self.conn.commit()
    
    def get_baseline(self, freq: float) -> Optional[Dict]:
        """Get baseline for a frequency"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM baseline WHERE frequency_hz = ?', (freq,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_baseline(self) -> List[Dict]:
        """Get all baseline frequencies"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM baseline ORDER BY frequency_hz')
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== SIGNAL MANAGEMENT (SIMPLE) ==========
    
    def add_signal(self, freq: float, band: str, power: float, 
                   baseline_power: float = None, is_anomaly: bool = True,
                   recording_file: str = None, **kwargs) -> int:
        """Add a detected signal (flat, simple insert)"""
        cursor = self.conn.cursor()
        
        # Calculate delta if we have baseline
        delta = None
        if baseline_power is not None:
            delta = power - baseline_power
        
        cursor.execute('''
            INSERT INTO signals (
                frequency_hz, band, power_dbm, baseline_power_dbm, delta_db,
                is_anomaly, recording_file, device_name, device_type, 
                manufacturer, modulation, bit_rate, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            freq, band, power, baseline_power, delta, is_anomaly, recording_file,
            kwargs.get('device_name'), kwargs.get('device_type'),
            kwargs.get('manufacturer'), kwargs.get('modulation'),
            kwargs.get('bit_rate'), kwargs.get('confidence')
        ))
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_all_signals(self, limit: int = 1000) -> List[Dict]:
        """Get ALL signals (let frontend filter)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM signals 
            ORDER BY detected_at DESC 
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_anomalies(self, limit: int = 100) -> List[Dict]:
        """Get signals marked as anomalies"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM signals 
            WHERE is_anomaly = 1 AND is_baseline = 0
            ORDER BY detected_at DESC 
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_identified_signals(self, limit: int = 100) -> List[Dict]:
        """Get signals that have been identified (have device info)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM signals 
            WHERE device_name IS NOT NULL
            ORDER BY detected_at DESC 
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def update_signal_device(self, signal_id: int, device_name: str, 
                            device_type: str = None, manufacturer: str = None):
        """Add device identification to a signal"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE signals 
            SET device_name = ?, device_type = ?, manufacturer = ?
            WHERE id = ?
        ''', (device_name, device_type, manufacturer, signal_id))
        self.conn.commit()
    
    def update_signal_analysis(self, signal_id: int, modulation: str = None,
                              bit_rate: int = None, confidence: float = None,
                              analysis_data: str = None):
        """Add analysis results to a signal"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE signals 
            SET modulation = ?, bit_rate = ?, confidence = ?, analysis_data = ?
            WHERE id = ?
        ''', (modulation, bit_rate, confidence, analysis_data, signal_id))
        self.conn.commit()
    
    def promote_to_baseline(self, freq: float):
        """Mark frequency as baseline (suppress future anomalies)"""
        cursor = self.conn.cursor()
        # Mark all signals at this frequency as baseline
        cursor.execute('''
            UPDATE signals 
            SET is_baseline = 1, is_anomaly = 0
            WHERE frequency_hz = ?
        ''', (freq,))
        self.conn.commit()
    
    # ========== RECORDINGS (SIMPLE) ==========
    
    def add_recording(self, filename: str, freq: float, band: str, signal_id: int = None):
        """Add recording metadata"""
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO recordings (filename, frequency_hz, band, signal_id)
                VALUES (?, ?, ?, ?)
            ''', (filename, freq, band, signal_id))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            # Recording already exists
            return None
    
    def get_recordings(self, limit: int = 100) -> List[Dict]:
        """Get all recordings"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM recordings 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== STATISTICS (SIMPLE COUNTS) ==========
    
    def get_statistics(self) -> Dict[str, int]:
        """Get simple statistics"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Baseline count
        cursor.execute('SELECT COUNT(*) as count FROM baseline')
        stats['baseline_frequencies'] = cursor.fetchone()['count']
        
        # Total signals
        cursor.execute('SELECT COUNT(*) as count FROM signals')
        stats['total_signals'] = cursor.fetchone()['count']
        
        # Anomalies (not promoted to baseline)
        cursor.execute('SELECT COUNT(*) as count FROM signals WHERE is_anomaly = 1 AND is_baseline = 0')
        stats['anomalies'] = cursor.fetchone()['count']
        
        # Identified devices
        cursor.execute('SELECT COUNT(DISTINCT device_name) as count FROM signals WHERE device_name IS NOT NULL')
        stats['identified_devices'] = cursor.fetchone()['count']
        
        # Recordings
        cursor.execute('SELECT COUNT(*) as count FROM recordings')
        stats['total_recordings'] = cursor.fetchone()['count']
        
        return stats
    
    # ========== LEGACY COMPATIBILITY ==========
    
    def get_devices(self) -> List[Dict]:
        """Get unique identified devices (for backwards compat)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                frequency_hz,
                device_name as name,
                device_type,
                manufacturer,
                modulation,
                bit_rate,
                confidence,
                MAX(detected_at) as last_seen,
                COUNT(*) as detection_count
            FROM signals
            WHERE device_name IS NOT NULL
            GROUP BY frequency_hz, device_name
            ORDER BY MAX(detected_at) DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]
    
    def clear_anomalies(self):
        """Clear all anomaly signals (for fresh start)"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM signals WHERE is_anomaly = 1')
        self.conn.commit()
    
    def clear_all_data(self):
        """Nuclear option - clear everything except baseline"""
        cursor = self.conn.cursor()
        cursor.execute('DELETE FROM signals')
        cursor.execute('DELETE FROM recordings')
        self.conn.commit()
    
    def close(self):
        """Close database connection"""
        self.conn.close()

# Singleton pattern for easy access
_db_instance = None

def get_db(db_path='reconraven.db') -> ReconRavenDB:
    """Get database singleton"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ReconRavenDB(db_path)
    return _db_instance
