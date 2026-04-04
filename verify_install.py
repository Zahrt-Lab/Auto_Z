#!/usr/bin/env python3
"""
Verify AUTO_ZAHRT installation
"""

def verify_installation():
    """Check if AUTO_ZAHRT is properly installed."""
    print("Verifying AUTO_ZAHRT installation...\n")
    
    try:
        # Test import of main module
        from methods import GeneralExperimentMethod
        print("✓ Core module imported successfully")
        
        # Test import of submodules
        from methods.parameter_parser import parse_params
        print("✓ Parameter parser imported")
        
        from methods.experiment_logger import ExperimentLogger
        print("✓ Experiment logger imported")
        
        from methods.status_monitor import StatusMonitor
        print("✓ Status monitor imported")
        
        from methods.instrument_manager import InstrumentManager
        print("✓ Instrument manager imported")
        
        from methods.device_executors import DeviceExecutor
        print("✓ Device executors imported")
        
        # Check dependencies
        import pandas
        print(f"✓ pandas {pandas.__version__}")
        
        import serial
        print(f"✓ pyserial {serial.__version__}")
        
        print("\n✅ AUTO_ZAHRT installation verified successfully!")
        print(f"   Version: 3.0.0")
        return True
        
    except ImportError as e:
        print(f"\n❌ Installation verification failed: {e}")
        return False


if __name__ == "__main__":
    import sys
    sys.exit(0 if verify_installation() else 1)
