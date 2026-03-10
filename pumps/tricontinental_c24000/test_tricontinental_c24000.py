"""
Test script for Tricontinental C24000 Dual Syringe Pump
Tests all major functionality to ensure proper operation
"""

import sys
import os
import time

# Add parent directories to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from pumps.tricontinental_c24000.tricontinental_c24000 import TricontinentalC24000

def print_header(title):
    """Print a formatted test header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def test_connection(port="COM5"):
    """Test 1: Connection"""
    print_header("TEST 1: Connection")
    
    try:
        print(f"Creating pump instance on {port}...")
        pump = TricontinentalC24000(port=port, baudrate=9600, name="TestPump")
        print(f"[OK] Pump instance created")
        print(f"     Name: {pump.name}")
        print(f"     Port: {pump.port}")
        print(f"     Baudrate: {pump.baudrate}")
        
        print(f"\nConnecting to pump...")
        pump.connect()
        print(f"[OK] Connected successfully")
        
        return pump
    
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_status(pump):
    """Test 2: Status Check"""
    if pump is None:
        print("Skipping - no pump connection")
        return False
    
    print_header("TEST 2: Status Check")
    
    try:
        print("Checking pump status...")
        status = pump.status()
        print(f"[OK] Status: {status}")
        return True
    
    except Exception as e:
        print(f"[ERROR] Status check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parameters(pump):
    """Test 3: Parameter Display"""
    if pump is None:
        print("Skipping - no pump connection")
        return False
    
    print_header("TEST 3: Parameter Display")
    
    try:
        print("Getting pump parameters...")
        pump.get_pump_parameters()
        print(f"[OK] Parameters displayed")
        return True
    
    except Exception as e:
        print(f"[ERROR] Parameter display failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_flow_rate_conversion(pump):
    """Test 4: Flow Rate Conversion"""
    if pump is None:
        print("Skipping - no pump connection")
        return False
    
    print_header("TEST 4: Flow Rate Conversion")
    
    try:
        test_rates = [100, 200, 500, 1000, 1500, 2000]
        print("Testing flow rate conversions:")
        print(f"  {'Flow Rate (µL/min)':<20} {'Device Speed (counts/s)':<25}")
        print("-" * 70)
        
        for rate in test_rates:
            device_speed = pump._convert_flow_rate(rate)
            print(f"  {rate:<20} {device_speed:<25}")
        
        print(f"\n[OK] Flow rate conversions working")
        return True
    
    except Exception as e:
        print(f"[ERROR] Flow rate conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_volume_conversion(pump):
    """Test 5: Volume Conversion"""
    if pump is None:
        print("Skipping - no pump connection")
        return False
    
    print_header("TEST 5: Volume Conversion")
    
    try:
        test_volumes = [10, 50, 100, 500, 1000]
        print("Testing volume conversions:")
        print(f"  {'Volume (µL)':<20} {'Device Counts':<25}")
        print("-" * 70)
        
        for vol in test_volumes:
            counts = pump._convert_volume_to_counts(vol)
            print(f"  {vol:<20} {counts:<25}")
        
        print(f"\n[OK] Volume conversions working")
        return True
    
    except Exception as e:
        print(f"[ERROR] Volume conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_pump_time_calculation(pump):
    """Test 6: Pump Time Calculation"""
    if pump is None:
        print("Skipping - no pump connection")
        return False
    
    print_header("TEST 6: Pump Time Calculation")
    
    try:
        test_cases = [
            (100, 100),   # 100 µL at 100 µL/min = 60 sec
            (200, 100),   # 200 µL at 100 µL/min = 120 sec
            (100, 200),   # 100 µL at 200 µL/min = 30 sec
            (500, 1000),  # 500 µL at 1000 µL/min = 30 sec
        ]
        
        print("Testing pump time calculations:")
        print(f"  {'Volume (µL)':<15} {'Flow Rate (µL/min)':<20} {'Pump Time (s)':<20} {'Total Wait (s)':<20}")
        print("-" * 70)
        
        for volume, flow_rate in test_cases:
            pump_time, total_wait = pump._calculate_pump_time(volume, flow_rate)
            print(f"  {volume:<15} {flow_rate:<20} {pump_time:<20.2f} {total_wait:<20.2f}")
        
        print(f"\n[OK] Pump time calculations working")
        return True
    
    except Exception as e:
        print(f"[ERROR] Pump time calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_stop(pump):
    """Test 7: Stop Function"""
    if pump is None:
        print("Skipping - no pump connection")
        return False
    
    print_header("TEST 7: Stop Function")
    
    try:
        print("Calling stop() to ensure pump is stopped...")
        pump.stop()
        print(f"[OK] Stop command executed")
        time.sleep(2)
        
        print("\nChecking status after stop...")
        status = pump.status()
        print(f"[OK] Status: {status}")
        return True
    
    except Exception as e:
        print(f"[ERROR] Stop test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_small_dispense(pump):
    """Test 8: Small Volume Dispense (OPTIONAL - user must confirm)"""
    if pump is None:
        print("Skipping - no pump connection")
        return False
    
    print_header("TEST 8: Small Volume Dispense (OPTIONAL)")
    
    print("\n⚠ WARNING: This test will dispense a small volume of liquid!")
    print("  Volume: 50 µL")
    print("  Flow Rate: 100 µL/min")
    print("  Duration: ~30 seconds")
    print("\nMake sure:")
    print("  1. Pump syringes are filled")
    print("  2. Output tubing is connected to waste container")
    print("  3. Safe to run pump")
    
    try:
        response = input("\nRun dispense test? (yes/no): ").strip().lower()
        if response != 'yes':
            print("[SKIPPED] User declined dispense test")
            return True
        
        print("\nStarting dispense test...")
        pump.dispense(flow_rate_ul_min=100, volume_ul=50)
        print(f"[OK] Dispense test completed")
        return True
    
    except Exception as e:
        print(f"[ERROR] Dispense test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("=" * 70)
    print("  Tricontinental C24000 Comprehensive Test Suite")
    print("=" * 70)
    
    # Get COM port from user
    print("\nEnter the COM port for the pump (e.g., COM5):")
    try:
        port = input("Port: ").strip()
        if not port:
            port = "COM5"  # Default
            print(f"Using default port: {port}")
    except:
        port = "COM5"
        print(f"Using default port: {port}")
    
    pump = None
    test_results = []
    
    try:
        # Run tests
        pump = test_connection(port)
        test_results.append(("Connection", pump is not None))
        
        if pump:
            test_results.append(("Status Check", test_status(pump)))
            test_results.append(("Parameter Display", test_parameters(pump)))
            test_results.append(("Flow Rate Conversion", test_flow_rate_conversion(pump)))
            test_results.append(("Volume Conversion", test_volume_conversion(pump)))
            test_results.append(("Pump Time Calculation", test_pump_time_calculation(pump)))
            test_results.append(("Stop Function", test_stop(pump)))
            test_results.append(("Small Dispense", test_small_dispense(pump)))
        
        # Summary
        print("\n" + "=" * 70)
        print("  TEST SUMMARY")
        print("=" * 70)
        
        passed = 0
        failed = 0
        
        for test_name, result in test_results:
            status = "[PASS]" if result else "[FAIL]"
            print(f"  {status} {test_name}")
            if result:
                passed += 1
            else:
                failed += 1
        
        print("\n" + "-" * 70)
        print(f"  Total: {passed + failed} tests")
        print(f"  Passed: {passed}")
        print(f"  Failed: {failed}")
        print("=" * 70)
        
        if failed == 0:
            print("\n✓ ALL TESTS PASSED!")
        else:
            print(f"\n⚠ {failed} TEST(S) FAILED")
    
    except KeyboardInterrupt:
        print("\n\n*** Tests interrupted by user ***")
    
    except Exception as e:
        print(f"\n\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if pump:
            print("\n" + "=" * 70)
            print("  Cleanup")
            print("=" * 70)
            try:
                print("Stopping pump...")
                pump.stop()
                print("[OK] Pump stopped")
                
                print("Closing connection...")
                pump.close()
                print("[OK] Connection closed")
            except Exception as e:
                print(f"[ERROR] Cleanup failed: {e}")

if __name__ == "__main__":
    main()
