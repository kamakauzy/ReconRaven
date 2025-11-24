#!/usr/bin/env python3
"""
ReconRaven Database Module
Centralized storage for all signal data, analysis, and devices
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any

class ReconRavenDB:
    """SQLite database for ReconRaven data management"""
    
    def __init__(self, db_path='reconraven.db'):
        """Initialize database connection"""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create database schema"""
        cursor = self.conn.cursor()
        
        # Baseline frequencies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS baseline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency_hz REAL NOT NULL UNIQUE,
                band TEXT NOT NULL,
                power_dbm REAL NOT NULL,
                std_dbm REAL,
                user_promoted INTEGER DEFAULT 0,
                sample_count INTEGER DEFAULT 1,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Detected signals/anomalies table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency_hz REAL NOT NULL,
                band TEXT NOT NULL,
                power_dbm REAL NOT NULL,
                baseline_power_dbm REAL,
                delta_db REAL,
                is_anomaly BOOLEAN DEFAULT 0,
                recorded BOOLEAN DEFAULT 0,
                recording_file TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Identified devices table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS devices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                frequency_hz REAL NOT NULL,
                name TEXT NOT NULL,
                manufacturer TEXT,
                device_type TEXT,
                modulation TEXT,
                bit_rate INTEGER,
                confidence REAL,
                ignored BOOLEAN DEFAULT 0,
                first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                seen_count INTEGER DEFAULT 1,
                UNIQUE(frequency_hz, name)
            )
        ''')
        
        # Recordings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recordings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                frequency_hz REAL NOT NULL,
                band TEXT,
                power_dbm REAL,
                duration_sec REAL,
                file_size_mb REAL,
                analyzed BOOLEAN DEFAULT 0,
                device_id INTEGER,
                captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_id) REFERENCES devices(id)
            )
        ''')
        
        # Analysis results table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS analysis_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER NOT NULL,
                analysis_type TEXT NOT NULL,
                modulation TEXT,
                bit_rate INTEGER,
                preambles TEXT,
                results_json TEXT,
                confidence REAL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recording_id) REFERENCES recordings(id)
            )
        ''')
        
        # Scan sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_name TEXT,
                mode TEXT,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMP,
                frequencies_scanned INTEGER DEFAULT 0,
                anomalies_detected INTEGER DEFAULT 0,
                recordings_made INTEGER DEFAULT 0
            )
        ''')
        
        # Voice transcripts table (NEW)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcripts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                recording_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                language TEXT,
                confidence REAL,
                duration_sec REAL,
                segments_json TEXT,
                transcribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (recording_id) REFERENCES recordings(id)
            )
        ''')
        
        # Transcript keywords table for search (NEW)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcript_keywords (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transcript_id INTEGER NOT NULL,
                keyword TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                FOREIGN KEY (transcript_id) REFERENCES transcripts(id)
            )
        ''')
        
        # Create indexes for better search performance
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transcript_keywords ON transcript_keywords(keyword)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transcripts_recording ON transcripts(recording_id)')
        
        self.conn.commit()
    
    # ========== BASELINE MANAGEMENT ==========
    
    def add_baseline_frequency(self, freq: float, band: str, power: float, std: float = None, user_promoted: bool = False):
        """Add or update baseline frequency"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO baseline (frequency_hz, band, power_dbm, std_dbm, user_promoted)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(frequency_hz) DO UPDATE SET
                power_dbm = ?,
                std_dbm = ?,
                user_promoted = ?,
                sample_count = sample_count + 1,
                last_updated = CURRENT_TIMESTAMP
        ''', (freq, band, power, std, 1 if user_promoted else 0, power, std, 1 if user_promoted else 0))
        self.conn.commit()
    
    def get_baseline(self) -> List[Dict]:
        """Get all baseline frequencies"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM baseline ORDER BY frequency_hz')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_baseline_for_frequency(self, freq: float) -> Optional[Dict]:
        """Get baseline for specific frequency"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM baseline WHERE frequency_hz = ?', (freq,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ========== SIGNAL DETECTION ==========
    
    def add_signal(self, freq: float, band: str, power: float, 
                   baseline_power: float = None, is_anomaly: bool = False,
                   recording_file: str = None) -> int:
        """Record detected signal"""
        delta = (power - baseline_power) if baseline_power else None
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO signals (frequency_hz, band, power_dbm, baseline_power_dbm,
                               delta_db, is_anomaly, recorded, recording_file)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (freq, band, power, baseline_power, delta, is_anomaly, 
              recording_file is not None, recording_file))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_anomalies(self, limit: int = 100) -> List[Dict]:
        """Get recent anomalies with analysis data (GROUPED by signature: freq+modulation+bitrate)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                s.frequency_hz,
                s.band,
                MAX(s.power_dbm) as power_dbm,
                MAX(s.delta_db) as delta_db,
                MAX(s.detected_at) as detected_at,
                COUNT(*) as detection_count,
                MAX(s.recording_file) as recording_file,
                MAX(r.filename) as recording_filename,
                MAX(r.analyzed) as recording_analyzed,
                MAX(a.modulation) as analysis_modulation,
                MAX(a.bit_rate) as analysis_bit_rate,
                MAX(a.preambles) as analysis_preambles,
                MAX(a.results_json) as analysis_results,
                MAX(a.confidence) as analysis_confidence,
                MAX(d.name) as device_name,
                MAX(d.manufacturer) as device_manufacturer,
                MAX(d.device_type) as device_type,
                COALESCE(MAX(a.modulation), 'Unknown') as signature_modulation,
                COALESCE(MAX(a.bit_rate), 0) as signature_bitrate
            FROM signals s
            LEFT JOIN recordings r ON s.recording_file = r.filename
            LEFT JOIN analysis_results a ON r.id = a.recording_id
            LEFT JOIN devices d ON s.frequency_hz = d.frequency_hz
            WHERE s.is_anomaly = 1 
                AND s.frequency_hz NOT IN (SELECT frequency_hz FROM baseline WHERE user_promoted = 1)
                AND d.id IS NULL
            GROUP BY s.frequency_hz, COALESCE(a.modulation, 'Unknown'), COALESCE(a.bit_rate, 0)
            ORDER BY MAX(s.detected_at) DESC 
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_signals_by_frequency(self, freq: float) -> List[Dict]:
        """Get all signals for a frequency"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM signals 
            WHERE frequency_hz = ? 
            ORDER BY detected_at DESC
        ''', (freq,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== DEVICE MANAGEMENT ==========
    
    def add_device(self, freq: float, name: str, manufacturer: str = None,
                   device_type: str = None, modulation: str = None,
                   bit_rate: int = None, confidence: float = 0.0) -> int:
        """Add or update identified device"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO devices (frequency_hz, name, manufacturer, device_type,
                               modulation, bit_rate, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(frequency_hz, name) DO UPDATE SET
                last_seen = CURRENT_TIMESTAMP,
                seen_count = seen_count + 1,
                confidence = MAX(confidence, ?)
        ''', (freq, name, manufacturer, device_type, modulation, bit_rate, confidence, confidence))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_devices(self) -> List[Dict]:
        """Get all identified devices with recording status and analysis data"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                d.*,
                b.id as is_baselined,
                COUNT(DISTINCT s.id) as signal_count,
                MAX(s.detected_at) as last_detection,
                MAX(s.recorded) as has_recording,
                MAX(s.recording_file) as latest_recording,
                MAX(r.analyzed) as recording_analyzed,
                MAX(a.results_json) as analysis_results,
                MAX(a.confidence) as analysis_confidence
            FROM devices d
            LEFT JOIN baseline b ON d.frequency_hz = b.frequency_hz
            LEFT JOIN signals s ON d.frequency_hz = s.frequency_hz
            LEFT JOIN recordings r ON s.recording_file = r.filename
            LEFT JOIN analysis_results a ON r.id = a.recording_id
            GROUP BY d.id
            ORDER BY b.id IS NULL DESC, d.confidence DESC, d.last_seen DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]
    
    def auto_promote_devices_to_baseline(self) -> int:
        """Automatically promote identified devices to baseline"""
        cursor = self.conn.cursor()
        
        # Get all identified devices not yet in baseline
        cursor.execute('''
            SELECT d.frequency_hz, d.name, d.manufacturer, d.device_type
            FROM devices d
            WHERE d.frequency_hz NOT IN (SELECT frequency_hz FROM baseline)
              AND d.confidence > 0.5
        ''')
        
        devices_to_promote = cursor.fetchall()
        promoted_count = 0
        
        for device in devices_to_promote:
            # Get band for this frequency
            freq_info = self.get_frequency_range_info(device['frequency_hz'])
            band = freq_info['name'] if freq_info else 'Unknown'
            
            # Add to baseline with user_promoted flag
            try:
                self.add_baseline_frequency(
                    freq=device['frequency_hz'],
                    band=band,
                    power=-60.0,
                    std=5.0,
                    user_promoted=True  # Auto-promoted identified device
                )
                promoted_count += 1
            except:
                pass  # Already in baseline
        
        return promoted_count
    
    def ignore_device(self, frequency_hz: float):
        """Ignore/suppress a device (won't show in anomalies)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE devices 
            SET ignored = 1 
            WHERE frequency_hz = ?
        ''', (frequency_hz,))
        
        # Also add to baseline to suppress anomalies
        freq_info = self.get_frequency_range_info(frequency_hz)
        band = freq_info['name'] if freq_info else 'Unknown'
        
        try:
            self.add_baseline_frequency(
                freq=frequency_hz,
                band=band,
                power=-60.0,
                std=5.0,
                user_promoted=True
            )
        except:
            pass  # Already in baseline
        
        self.conn.commit()
    
    def unignore_device(self, frequency_hz: float):
        """Un-ignore a device"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE devices 
            SET ignored = 0 
            WHERE frequency_hz = ?
        ''', (frequency_hz,))
        self.conn.commit()
    
    def get_device_by_frequency(self, freq: float) -> Optional[Dict]:
        """Get device at specific frequency"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM devices 
            WHERE frequency_hz = ? 
            ORDER BY confidence DESC 
            LIMIT 1
        ''', (freq,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # ========== RECORDING MANAGEMENT ==========
    
    def add_recording(self, filename: str, freq: float, band: str = None,
                     power: float = None, duration: float = None,
                     file_size_mb: float = None, device_id: int = None) -> int:
        """Record captured file"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO recordings 
            (filename, frequency_hz, band, power_dbm, duration_sec, file_size_mb, device_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (filename, freq, band, power, duration, file_size_mb, device_id))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_recordings(self, analyzed_only: bool = False) -> List[Dict]:
        """Get all recordings"""
        cursor = self.conn.cursor()
        query = 'SELECT * FROM recordings'
        if analyzed_only:
            query += ' WHERE analyzed = 1'
        query += ' ORDER BY captured_at DESC'
        cursor.execute(query)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_recording_by_id(self, recording_id: int) -> Optional[Dict]:
        """Get specific recording by ID"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM recordings WHERE id = ?', (recording_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_recording_audio(self, recording_id: int, audio_filename: str):
        """Update recording with audio filename (WAV)"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE recordings 
            SET filename = ? 
            WHERE id = ?
        ''', (audio_filename, recording_id))
        self.conn.commit()
    
    def mark_recording_analyzed(self, recording_id: int, device_id: int = None):
        """Mark recording as analyzed"""
        cursor = self.conn.cursor()
        cursor.execute('''
            UPDATE recordings 
            SET analyzed = 1, device_id = ? 
            WHERE id = ?
        ''', (device_id, recording_id))
        self.conn.commit()
    
    # ========== ANALYSIS RESULTS ==========
    
    def add_analysis_result(self, recording_id: int, analysis_type: str,
                           modulation: str = None, bit_rate: int = None,
                           preambles: List[str] = None, results: Dict = None,
                           confidence: float = 0.0) -> int:
        """Store analysis results"""
        preamble_str = json.dumps(preambles) if preambles else None
        results_str = json.dumps(results) if results else None
        
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO analysis_results 
            (recording_id, analysis_type, modulation, bit_rate, preambles, 
             results_json, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (recording_id, analysis_type, modulation, bit_rate, 
              preamble_str, results_str, confidence))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_analysis_results(self, recording_id: int) -> List[Dict]:
        """Get all analysis results for a recording"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM analysis_results 
            WHERE recording_id = ? 
            ORDER BY confidence DESC
        ''', (recording_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    # ========== STATISTICS ==========
    
    def get_frequency_range_info(self, freq: float) -> Optional[Dict]:
        """Get frequency range information for a given frequency"""
        cursor = self.conn.cursor()
        
        # First check if frequency_ranges table exists and has data
        cursor.execute('''
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='frequency_ranges'
        ''')
        
        if cursor.fetchone():
            cursor.execute('''
                SELECT name, type, band, mode, description 
                FROM frequency_ranges 
                WHERE start_hz <= ? AND end_hz >= ?
                ORDER BY (end_hz - start_hz) ASC
                LIMIT 1
            ''', (freq, freq))
            row = cursor.fetchone()
            if row:
                return dict(row)
        
        # Fallback to basic band detection
        if 144e6 <= freq <= 148e6:
            return {'name': '2m', 'type': 'Ham', 'band': '2m', 'mode': 'FM', 'description': '2m Amateur Band'}
        elif 420e6 <= freq <= 450e6:
            return {'name': '70cm', 'type': 'Ham', 'band': '70cm', 'mode': 'FM', 'description': '70cm Amateur Band'}
        elif 433e6 <= freq <= 435e6:
            return {'name': 'ISM433', 'type': 'ISM', 'band': '433MHz', 'mode': 'ASK/OOK', 'description': '433MHz ISM Band'}
        elif 902e6 <= freq <= 928e6:
            return {'name': 'ISM915', 'type': 'ISM', 'band': '915MHz', 'mode': 'FSK', 'description': '915MHz ISM Band'}
        
        return None
    
    def get_statistics(self) -> Dict:
        """Get overall statistics"""
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Baseline count
        cursor.execute('SELECT COUNT(*) as count FROM baseline')
        stats['baseline_frequencies'] = cursor.fetchone()['count']
        
        # Signal counts
        cursor.execute('SELECT COUNT(*) as count FROM signals')
        stats['total_signals'] = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM signals WHERE is_anomaly = 1')
        stats['anomalies'] = cursor.fetchone()['count']
        
        # Device count
        cursor.execute('SELECT COUNT(*) as count FROM devices')
        stats['identified_devices'] = cursor.fetchone()['count']
        
        # Recording counts
        cursor.execute('SELECT COUNT(*) as count FROM recordings')
        stats['total_recordings'] = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM recordings WHERE analyzed = 1')
        stats['analyzed_recordings'] = cursor.fetchone()['count']
        
        # Total file size
        cursor.execute('SELECT SUM(file_size_mb) as total FROM recordings')
        stats['total_storage_mb'] = cursor.fetchone()['total'] or 0
        
        # Transcript counts
        cursor.execute('SELECT COUNT(*) as count FROM transcripts')
        stats['total_transcripts'] = cursor.fetchone()['count']
        
        return stats
    
    # ========== TRANSCRIPT MANAGEMENT ==========
    
    def add_transcript(self, recording_id: int, text: str, language: str = None,
                      confidence: float = 0.0, duration: float = 0.0,
                      segments: List[Dict] = None) -> int:
        """Add voice transcript"""
        cursor = self.conn.cursor()
        segments_json = json.dumps(segments) if segments else None
        
        cursor.execute('''
            INSERT INTO transcripts (recording_id, text, language, confidence, duration_sec, segments_json)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (recording_id, text, language, confidence, duration, segments_json))
        
        transcript_id = cursor.lastrowid
        
        # Extract keywords for search
        keywords = self._extract_keywords(text)
        for keyword, freq in keywords.items():
            cursor.execute('''
                INSERT INTO transcript_keywords (transcript_id, keyword, frequency)
                VALUES (?, ?, ?)
            ''', (transcript_id, keyword, freq))
        
        self.conn.commit()
        return transcript_id
    
    def _extract_keywords(self, text: str) -> Dict[str, int]:
        """Extract keywords from text for search indexing"""
        # Remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                    'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'were', 'be',
                    'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                    'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this',
                    'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they'}
        
        words = text.lower().split()
        keywords = {}
        
        for word in words:
            # Clean word
            word = ''.join(c for c in word if c.isalnum())
            if len(word) > 2 and word not in stopwords:
                keywords[word] = keywords.get(word, 0) + 1
        
        return keywords
    
    def get_transcript(self, recording_id: int) -> Optional[Dict]:
        """Get transcript for a recording"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM transcripts
            WHERE recording_id = ?
            ORDER BY transcribed_at DESC
            LIMIT 1
        ''', (recording_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def get_all_transcripts(self, limit: int = 100) -> List[Dict]:
        """Get all transcripts with recording info"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                t.*,
                r.filename as recording_filename,
                r.frequency_hz,
                r.band,
                r.captured_at
            FROM transcripts t
            JOIN recordings r ON t.recording_id = r.id
            ORDER BY t.transcribed_at DESC
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
    
    def search_transcripts(self, keyword: str, limit: int = 50) -> List[Dict]:
        """Search transcripts by keyword"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT
                t.*,
                r.filename as recording_filename,
                r.frequency_hz,
                r.band,
                r.captured_at,
                tk.frequency as keyword_frequency
            FROM transcripts t
            JOIN recordings r ON t.recording_id = r.id
            JOIN transcript_keywords tk ON t.id = tk.transcript_id
            WHERE tk.keyword LIKE ?
            ORDER BY tk.frequency DESC, t.transcribed_at DESC
            LIMIT ?
        ''', (f'%{keyword.lower()}%', limit))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_transcripts_by_frequency(self, frequency_hz: float) -> List[Dict]:
        """Get all transcripts for a specific frequency"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                t.*,
                r.filename as recording_filename,
                r.captured_at
            FROM transcripts t
            JOIN recordings r ON t.recording_id = r.id
            WHERE r.frequency_hz = ?
            ORDER BY t.transcribed_at DESC
        ''', (frequency_hz,))
        return [dict(row) for row in cursor.fetchall()]
    
    def get_untranscribed_recordings(self) -> List[Dict]:
        """Get recordings that haven't been transcribed yet"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT r.*
            FROM recordings r
            LEFT JOIN transcripts t ON r.id = t.recording_id
            WHERE t.id IS NULL
              AND r.filename LIKE 'voice_%'
            ORDER BY r.captured_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]
    
    def get_dashboard_data(self) -> Dict:
        """Get comprehensive data for dashboard"""
        return {
            'statistics': self.get_statistics(),
            'baseline': self.get_baseline(),
            'devices': self.get_devices(),
            'recent_anomalies': self.get_anomalies(limit=20),
            'recent_recordings': self.get_recordings()[:20]
        }
    
    def close(self):
        """Close database connection"""
        self.conn.close()

# Singleton instance
_db_instance = None

def get_db(db_path='reconraven.db') -> ReconRavenDB:
    """Get database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = ReconRavenDB(db_path)
    return _db_instance

if __name__ == "__main__":
    # Test database creation
    db = ReconRavenDB('test.db')
    print("Database created successfully!")
    print("\nTables created:")
    cursor = db.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for row in cursor.fetchall():
        print(f"  - {row[0]}")
    
    print("\nStatistics:", db.get_statistics())
    db.close()

