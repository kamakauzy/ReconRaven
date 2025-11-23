#!/usr/bin/env python3
"""
ReconRaven - Master Signal Analyzer
Combines all analysis tools for complete signal identification
"""

import sys
import os
import subprocess

def banner():
    print("\n" + "#"*70)
    print("# ReconRaven - Master Signal Analyzer")
    print("# Complete signal identification and analysis")
    print("#"*70)

def run_analysis(filepath):
    """Run all analysis tools in sequence"""
    
    if not os.path.exists(filepath):
        print(f"\nError: File not found: {filepath}")
        return False
        
    print(f"\nAnalyzing: {os.path.basename(filepath)}\n")
    
    tools = [
        ("ISM Band Analyzer", "ism_analyzer.py"),
        ("Remote Decoder", "decode_remote.py"),
        ("URH-Style Analysis", "urh_analyze.py"),
    ]
    
    results = {}
    
    for name, script in tools:
        print("\n" + "="*70)
        print(f"Running: {name}")
        print("="*70)
        
        try:
            result = subprocess.run(
                ['python', script, filepath],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                print(result.stdout)
                results[name] = 'SUCCESS'
            else:
                print(f"Error running {name}")
                print(result.stderr[:500])  # First 500 chars of error
                results[name] = 'FAILED'
                
        except subprocess.TimeoutExpired:
            print(f"{name} timed out (>60s)")
            results[name] = 'TIMEOUT'
        except Exception as e:
            print(f"Error: {e}")
            results[name] = 'ERROR'
    
    # Summary
    print("\n" + "="*70)
    print("ANALYSIS SUMMARY")
    print("="*70)
    
    for tool, status in results.items():
        symbol = "✓" if status == 'SUCCESS' else "✗"
        print(f"  [{symbol}] {tool}: {status}")
    
    # Check for generated files
    print("\n" + "="*70)
    print("GENERATED FILES")
    print("="*70)
    
    base = filepath.replace('.npy', '')
    generated = [
        f"{base}_bursts.png",
        f"{base}_decoded.png",
        f"{base}_analysis.png",
        f"{base}_urh_analysis.txt",
        f"{base}_fingerprint.txt",
    ]
    
    for f in generated:
        if os.path.exists(f):
            size = os.path.getsize(f) / 1024
            print(f"  ✓ {os.path.basename(f)} ({size:.1f} KB)")
    
    print("\n" + "="*70)
    print("RECOMMENDATIONS")
    print("="*70)
    print("""
Based on your signal analysis, here are next steps:

1. IMMEDIATE:
   - Review the generated PNG plots
   - Check the text reports for device identification
   
2. FOR MORE DETAIL:
   - Install rtl_433: https://github.com/merbanan/rtl_433/releases
   - Use: rtl_433 -r yourfile.cu8 -A
   
3. FOR VISUAL ANALYSIS:
   - Install URH GUI: https://github.com/jopohl/urh/releases
   - Load your .npy file directly
   
4. FOR DATABASE LOOKUP:
   - Visit: https://www.sigidwiki.com/
   - Search by 925 MHz frequency
   - Compare your spectrogram

5. FOR FCC ID LOOKUP:
   - Visit: https://fccid.io/
   - Search devices near 925 MHz
   - Look for matching characteristics
""")
    
    return True

def analyze_all_recordings():
    """Analyze all recorded signals"""
    recordings_dir = "recordings/audio"
    
    if not os.path.exists(recordings_dir):
        print(f"\nNo recordings found in {recordings_dir}")
        return
    
    npy_files = [f for f in os.listdir(recordings_dir) if f.endswith('.npy')]
    
    if not npy_files:
        print(f"\nNo .npy files found in {recordings_dir}")
        return
    
    print(f"\nFound {len(npy_files)} recordings to analyze")
    print("\nAnalyze all? (y/n): ", end='')
    
    # Auto-yes for now
    response = 'y'
    
    if response.lower() == 'y':
        for i, filename in enumerate(npy_files, 1):
            print(f"\n{'='*70}")
            print(f"ANALYZING RECORDING {i}/{len(npy_files)}")
            print(f"{'='*70}")
            
            filepath = os.path.join(recordings_dir, filename)
            run_analysis(filepath)

def main():
    banner()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python analyze_all.py <file.npy>     - Analyze single file")
        print("  python analyze_all.py --all          - Analyze all recordings")
        print("\nExample:")
        print("  python analyze_all.py recordings/audio/ISM915_925.000MHz_20251122_173249_FSK.npy")
        print("  python analyze_all.py --all")
        sys.exit(1)
    
    if sys.argv[1] == '--all':
        analyze_all_recordings()
    else:
        filepath = sys.argv[1]
        run_analysis(filepath)

if __name__ == "__main__":
    main()

