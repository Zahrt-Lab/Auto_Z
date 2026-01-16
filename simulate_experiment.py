# TODO: Should delete this file for future use

"""
Simulates a running experiment with constant pump flow and temperature.
This script writes to a status log CSV file continuously, mimicking real equipment.
"""
import csv
import time
import os
from datetime import datetime

# Configuration
STATUS_LOG_FILE = "simulated_status_log.csv"
UPDATE_INTERVAL = 5  # seconds between status updates
PUMP_FLOW_RATE = 1000.0  # µL/min (constant)
TEMPERATURE = 25.5  # °C (constant)

def simulate_experiment():
    """Run simulated experiment that writes status updates to CSV."""
    
    # Initialize the CSV file with headers
    start_time = datetime.now()
    print(f"Starting simulated experiment at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Writing to: {STATUS_LOG_FILE}")
    print(f"Update interval: {UPDATE_INTERVAL} seconds")
    print(f"Pump flow rate: {PUMP_FLOW_RATE} µL/min")
    print(f"Temperature: {TEMPERATURE}°C")
    print("\nPress Ctrl+C to stop the simulation\n")
    
    # Create CSV with headers
    with open(STATUS_LOG_FILE, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(['Timestamp', 'Elapsed_Time_s', 'Pump_1', 'Temperature_1'])
    
    try:
        iteration = 0
        while True:
            # Calculate current time
            current_time = datetime.now()
            elapsed_seconds = (current_time - start_time).total_seconds()
            timestamp_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Simulate instrument status (constant values)
            pump_status = f"{PUMP_FLOW_RATE} µL/min"
            temp_status = f"{TEMPERATURE}°C"
            
            # Write status row to CSV
            with open(STATUS_LOG_FILE, mode='a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow([timestamp_str, round(elapsed_seconds, 1), pump_status, temp_status])
            
            iteration += 1
            print(f"[{timestamp_str}] Iteration {iteration}: Elapsed={elapsed_seconds:.1f}s, "
                  f"Pump={pump_status}, Temp={temp_status}")
            
            # Wait before next update
            time.sleep(UPDATE_INTERVAL)
            
    except KeyboardInterrupt:
        print("\n\nSimulation stopped by user")
        print(f"Total elapsed time: {elapsed_seconds:.1f} seconds")
        print(f"Total iterations: {iteration}")
        print(f"Status log saved to: {STATUS_LOG_FILE}")

if __name__ == "__main__":
    # Check if log file already exists
    if os.path.exists(STATUS_LOG_FILE):
        response = input(f"Warning: {STATUS_LOG_FILE} already exists. Overwrite? (y/n): ")
        if response.lower() != 'y':
            print("Simulation cancelled")
            exit(0)
    
    simulate_experiment()
