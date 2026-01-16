# TODO : Should delete this in the future

"""
Test script to simulate UV detector continuous monitoring.
Generates a CSV file with mock UV-Vis data to test uv_plot_gui.py
"""

import csv
import time
from pathlib import Path
from datetime import datetime
import numpy as np

def simulate_uv_continuous_monitoring(duration_seconds=60000, interval_seconds=5, 
                                      target_wavelengths=[409.0, 450.0, 500.0]):
    """
    Simulate UV detector continuous monitoring by writing CSV data.
    
    Args:
        duration_seconds: How long to run the simulation
        interval_seconds: Time between measurements
        target_wavelengths: List of wavelengths to monitor
    """
    output_file = Path("simulated_uv_data.csv")
    spectrum_file = Path("absorbance_simulated.csv")
    
    print(f"Simulating UV detector for {duration_seconds}s...")
    print(f"Target wavelengths: {target_wavelengths}")
    print(f"Measurement interval: {interval_seconds}s")
    print(f"Output file: {output_file}")
    print(f"Spectrum file: {spectrum_file}")
    
    # Full wavelength range for spectrum (typical UV-Vis range: 200-800 nm)
    wavelengths_full = np.linspace(200, 800, 601)  # 1 nm resolution
    
    def generate_spectrum(elapsed_time):
        """Generate evolving spectrum based on elapsed time."""
        # Peak intensities change over time (simulate reaction progress)
        # Peak 1 at 409 nm: grows (product formation)
        peak1_intensity = 0.2 + 0.6 * (1 - np.exp(-elapsed_time / 30))
        
        # Peak 2 at 450 nm: decays (reactant consumption)
        peak2_intensity = 0.9 - 0.5 * (1 - np.exp(-elapsed_time / 40))
        
        # Peak 3 at 500 nm: sigmoid (intermediate)
        peak3_intensity = 0.3 + 0.3 / (1 + np.exp(-(elapsed_time - 30) / 10))
        
        # Build full spectrum with evolving peaks
        absorbance_full = (
            0.05 +  # baseline
            peak1_intensity * np.exp(-((wavelengths_full - 409) ** 2) / (2 * 20 ** 2)) +
            peak2_intensity * np.exp(-((wavelengths_full - 450) ** 2) / (2 * 25 ** 2)) +
            peak3_intensity * np.exp(-((wavelengths_full - 500) ** 2) / (2 * 30 ** 2))
        )
        
        # Add small noise
        absorbance_full += np.random.normal(0, 0.005, len(absorbance_full))
        absorbance_full = np.clip(absorbance_full, 0, 2)
        
        return absorbance_full
    
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        
        # Write header
        header = ["Time(s)"] + [str(wl) for wl in target_wavelengths]
        writer.writerow(header)
        f.flush()
        
        start_time = time.time()
        measurement_count = 0
        
        try:
            while True:
                elapsed = time.time() - start_time
                
                if elapsed > duration_seconds:
                    break
                
                # Generate synthetic absorbance data
                # Wavelength 1: Exponential rise (product formation)
                abs1 = 0.1 + 0.6 * (1 - np.exp(-elapsed / 30))
                
                # Wavelength 2: Exponential decay (reactant consumption)
                abs2 = 0.9 - 0.5 * (1 - np.exp(-elapsed / 40))
                
                # Wavelength 3: Sigmoid curve (intermediate)
                abs3 = 0.4 + 0.3 / (1 + np.exp(-(elapsed - 30) / 10))
                
                # Add small random noise
                noise = np.random.normal(0, 0.01, 3)
                absorbances = [abs1 + noise[0], abs2 + noise[1], abs3 + noise[2]]
                
                # Clip to valid range
                absorbances = [max(0, min(2, a)) for a in absorbances]
                
                # Write row
                row = [elapsed] + absorbances[:len(target_wavelengths)]
                writer.writerow(row)
                f.flush()
                
                measurement_count += 1
                print(f"  t={elapsed:.1f}s: {', '.join(f'{wl}nm={abs:.3f}' for wl, abs in zip(target_wavelengths, absorbances[:len(target_wavelengths)]))}")
                
                # Update full spectrum snapshot (simulates device capturing new spectrum)
                absorbance_full = generate_spectrum(elapsed)
                with open(spectrum_file, 'w', newline='') as spec_f:
                    spec_f.write("Wavelength (nm),Absorbance\n")
                    for wl, abs_val in zip(wavelengths_full, absorbance_full):
                        spec_f.write(f"{wl:.1f},{abs_val:.6f}\n")
                
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            print("\nSimulation interrupted by user")
        
        print(f"\nSimulation complete: {measurement_count} measurements written to {output_file}")


if __name__ == "__main__":
    import sys
    
    # Default parameters
    duration = 60000
    interval = 5
    wavelengths = [409.0, 450.0, 500.0]
    
    # Simple command-line argument parsing
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            print(f"Invalid duration: {sys.argv[1]}, using default {duration}s")
    
    if len(sys.argv) > 2:
        try:
            interval = int(sys.argv[2])
        except ValueError:
            print(f"Invalid interval: {sys.argv[2]}, using default {interval}s")
    
    simulate_uv_continuous_monitoring(duration, interval, wavelengths)
