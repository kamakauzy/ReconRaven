#!/usr/bin/env python3
from database import get_db

db = get_db()
all_sigs = db.get_anomalies(limit=100)
two_m = [s for s in all_sigs if 144e6 <= s["frequency_hz"] <= 148e6]

print(f"\nFound {len(two_m)} signals in 2m band (144-148 MHz):")
print("="*70)
for s in two_m:
    freq_mhz = s["frequency_hz"] / 1e6
    power = s.get("power_dbm", 0)
    detected = s.get("detected_at", "unknown")
    recording = s.get("recording_file", "none")
    print(f"  {freq_mhz:.3f} MHz | {power:.1f} dBm | {detected} | {recording}")

if not two_m:
    print("  No 2m signals detected yet.")
    print(f"\nTotal anomalies in DB: {len(all_sigs)}")
    if all_sigs:
        print(f"Most recent: {all_sigs[0]['frequency_hz']/1e6:.3f} MHz at {all_sigs[0].get('detected_at', 'unknown')}")

