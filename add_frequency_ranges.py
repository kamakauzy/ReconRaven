#!/usr/bin/env python3
"""
Add frequency range definitions for smart matching
"""

from database import get_db
import sqlite3

def add_frequency_ranges():
    """Add table for frequency range definitions"""
    db = get_db()
    cursor = db.conn.cursor()
    
    # Create frequency ranges table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS frequency_ranges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_hz REAL NOT NULL,
            end_hz REAL NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            band TEXT NOT NULL,
            mode TEXT,
            description TEXT
        )
    ''')
    
    # US Ham Repeater Ranges
    ranges = [
        # 2m Repeater Ranges
        (145.100e6, 145.500e6, '2m Repeater Output', 'ham_repeater', '2m', 'FM', 'US 2m repeater outputs'),
        (146.400e6, 147.000e6, '2m Repeater Output', 'ham_repeater', '2m', 'FM', 'US 2m repeater outputs'),
        (144.500e6, 145.000e6, '2m Repeater Input', 'ham_repeater', '2m', 'FM', 'US 2m repeater inputs'),
        (146.000e6, 146.400e6, '2m Repeater Input', 'ham_repeater', '2m', 'FM', 'US 2m repeater inputs'),
        (146.520e6, 146.580e6, '2m Simplex', 'ham_simplex', '2m', 'FM', 'US 2m simplex calling/chat'),
        
        # 70cm Repeater Ranges
        (442.000e6, 445.000e6, '70cm Repeater Output', 'ham_repeater', '70cm', 'FM', 'US 70cm repeater outputs'),
        (447.000e6, 450.000e6, '70cm Repeater Input', 'ham_repeater', '70cm', 'FM', 'US 70cm repeater inputs'),
        (446.000e6, 446.100e6, '70cm Simplex', 'ham_simplex', '70cm', 'FM', 'US 70cm simplex'),
        
        # ISM Bands
        (902.000e6, 928.000e6, '915 MHz ISM Band', 'ism', 'ISM915', 'Various', 'US ISM unlicensed band'),
        (433.050e6, 434.790e6, '433 MHz ISM Band', 'ism', 'ISM433', 'Various', 'ISM unlicensed band'),
        
        # Public Safety (approximate ranges)
        (154.000e6, 155.000e6, 'VHF Public Safety', 'public_safety', 'VHF', 'FM', 'Fire/Police/EMS'),
        (156.000e6, 158.000e6, 'VHF Marine', 'marine', 'VHF', 'FM', 'Marine VHF channels'),
        (162.400e6, 162.550e6, 'NOAA Weather Radio', 'weather', 'VHF', 'FM', 'NOAA WX broadcasts'),
        
        # Business/Commercial
        (450.000e6, 470.000e6, 'UHF Business Band', 'commercial', 'UHF', 'FM', 'Commercial/Business radios'),
    ]
    
    print("="*70)
    print("Adding Frequency Range Definitions")
    print("="*70)
    
    for start, end, name, ftype, band, mode, desc in ranges:
        cursor.execute('''
            INSERT INTO frequency_ranges 
            (start_hz, end_hz, name, type, band, mode, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (start, end, name, ftype, band, mode, desc))
        
        print(f"\n{name}")
        print(f"  Range: {start/1e6:.3f} - {end/1e6:.3f} MHz")
        print(f"  Type: {ftype}")
        print(f"  {desc}")
    
    db.conn.commit()
    
    print("\n" + "="*70)
    print(f"Added {len(ranges)} frequency ranges")
    print("="*70)
    
    return True

def test_range_matching():
    """Test the range matching"""
    db = get_db()
    
    test_freqs = [
        442.027e6,  # Should match 70cm repeater
        145.234e6,  # Should match 2m repeater
        146.520e6,  # Should match 2m simplex
        915.123e6,  # Should match ISM915
        123.456e6,  # Should match nothing
    ]
    
    print("\n" + "="*70)
    print("Testing Range Matching")
    print("="*70)
    
    cursor = db.conn.cursor()
    
    for freq in test_freqs:
        cursor.execute('''
            SELECT name, type, band, mode, description 
            FROM frequency_ranges 
            WHERE start_hz <= ? AND end_hz >= ?
            LIMIT 1
        ''', (freq, freq))
        
        result = cursor.fetchone()
        
        print(f"\n{freq/1e6:.3f} MHz:")
        if result:
            print(f"  Identified as: {result[0]}")
            print(f"  Type: {result[1]}")
            print(f"  Band: {result[2]}")
        else:
            print(f"  Not in any known range")

if __name__ == "__main__":
    add_frequency_ranges()
    test_range_matching()

