#!/usr/bin/env python3
"""
IQ File Player
Play back captured .npy IQ recordings
"""

import sys
import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import os

def analyze_iq_file(filepath):
    """Analyze and visualize IQ recording"""
    
    print("\n" + "="*70)
    print(f"IQ FILE ANALYZER")
    print("="*70)
    print(f"File: {filepath}")
    
    # Load IQ samples
    print("Loading IQ samples...", end='', flush=True)
    samples = np.load(filepath)
    print(f" OK ({len(samples):,} samples)")
    
    # File info
    file_size = os.path.getsize(filepath) / (1024 * 1024)
    duration = len(samples) / 2.4e6  # Assuming 2.4 Msps
    
    print(f"File size: {file_size:.1f} MB")
    print(f"Duration: {duration:.1f} seconds")
    print(f"Sample rate: 2.4 Msps (assumed)")
    
    # Basic signal analysis
    print("\n" + "-"*70)
    print("SIGNAL ANALYSIS")
    print("-"*70)
    
    power = np.mean(np.abs(samples)**2)
    power_db = 10 * np.log10(power)
    peak = np.max(np.abs(samples))
    
    print(f"Average power: {power_db:.1f} dB")
    print(f"Peak amplitude: {peak:.4f}")
    print(f"Mean amplitude: {np.mean(np.abs(samples)):.4f}")
    
    # Create visualizations
    print("\n" + "-"*70)
    print("GENERATING PLOTS")
    print("-"*70)
    
    fig, axes = plt.subplots(3, 1, figsize=(12, 10))
    
    # 1. Time domain (first 10000 samples)
    print("1. Time domain plot...", end='', flush=True)
    plot_samples = min(10000, len(samples))
    time = np.arange(plot_samples) / 2.4e6 * 1000  # milliseconds
    axes[0].plot(time, np.real(samples[:plot_samples]), alpha=0.7, label='I (In-phase)')
    axes[0].plot(time, np.imag(samples[:plot_samples]), alpha=0.7, label='Q (Quadrature)')
    axes[0].set_xlabel('Time (ms)')
    axes[0].set_ylabel('Amplitude')
    axes[0].set_title('Time Domain - IQ Samples')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    print(" done")
    
    # 2. Spectrum (FFT)
    print("2. Frequency spectrum...", end='', flush=True)
    fft_size = 2048
    fft_samples = samples[:fft_size * 100]  # Use first portion
    
    # Compute FFT
    freqs = np.fft.fftshift(np.fft.fftfreq(fft_size, 1/2.4e6)) / 1e6  # MHz
    spectrum = np.fft.fftshift(np.fft.fft(fft_samples[:fft_size]))
    spectrum_db = 20 * np.log10(np.abs(spectrum) + 1e-10)
    
    axes[1].plot(freqs, spectrum_db)
    axes[1].set_xlabel('Frequency Offset (MHz)')
    axes[1].set_ylabel('Power (dB)')
    axes[1].set_title('Frequency Spectrum (FFT)')
    axes[1].grid(True, alpha=0.3)
    print(" done")
    
    # 3. Spectrogram
    print("3. Spectrogram...", end='', flush=True)
    spec_samples = min(500000, len(samples))
    f, t, Sxx = signal.spectrogram(samples[:spec_samples], 
                                     fs=2.4e6, 
                                     nperseg=1024,
                                     noverlap=512)
    
    axes[2].pcolormesh(t, f/1e6, 10*np.log10(Sxx + 1e-10), 
                       shading='gouraud', cmap='viridis')
    axes[2].set_xlabel('Time (seconds)')
    axes[2].set_ylabel('Frequency Offset (MHz)')
    axes[2].set_title('Spectrogram')
    print(" done")
    
    plt.tight_layout()
    
    # Save plot
    plot_file = filepath.replace('.npy', '_analysis.png')
    plt.savefig(plot_file, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved: {plot_file}")
    
    # Show plot
    print("\nDisplaying plot window...")
    print("(Close window to continue)")
    plt.show()
    
    print("\n" + "="*70)
    print("ANALYSIS COMPLETE")
    print("="*70)

def convert_to_wav(filepath, output_mode='FM'):
    """Convert IQ to audio WAV file"""
    print(f"\nConverting to audio ({output_mode} demodulation)...")
    
    # Load samples
    samples = np.load(filepath)
    
    if output_mode == 'FM':
        # FM demodulation
        # Calculate instantaneous phase
        phase = np.unwrap(np.angle(samples))
        # FM demod is derivative of phase
        audio = np.diff(phase)
    elif output_mode == 'AM':
        # AM demodulation - just magnitude
        audio = np.abs(samples)
    else:
        # Raw I channel
        audio = np.real(samples)
    
    # Normalize
    audio = audio / np.max(np.abs(audio))
    
    # Resample to 24 kHz for audio
    from scipy.signal import resample
    audio_rate = 24000
    orig_rate = 2.4e6
    downsample_factor = int(orig_rate / audio_rate)
    audio_resampled = audio[::downsample_factor]
    
    # Save as WAV
    from scipy.io import wavfile
    wav_file = filepath.replace('.npy', f'_{output_mode}.wav')
    wavfile.write(wav_file, audio_rate, audio_resampled.astype(np.float32))
    
    print(f"Audio saved: {wav_file}")
    print(f"You can now play it with any audio player!")
    
    return wav_file

def main():
    print("\n" + "#"*70)
    print("# ReconRaven - IQ File Player & Analyzer")
    print("#"*70)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python play_iq.py <file.npy>              - Analyze and plot")
        print("  python play_iq.py <file.npy> --fm         - Also convert to FM audio")
        print("  python play_iq.py <file.npy> --am         - Also convert to AM audio")
        print("\nExample:")
        print("  python play_iq.py recordings/audio/ISM915_920.000MHz_20251122_165533_FSK.npy")
        sys.exit(1)
    
    filepath = sys.argv[1]
    
    if not os.path.exists(filepath):
        print(f"\nError: File not found: {filepath}")
        sys.exit(1)
    
    try:
        # Analyze the file
        analyze_iq_file(filepath)
        
        # Convert to audio if requested
        if '--fm' in sys.argv:
            convert_to_wav(filepath, 'FM')
        elif '--am' in sys.argv:
            convert_to_wav(filepath, 'AM')
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

