import sys
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

# Now import and run the methods script
from methods.methods import GeneralExperimentMethod

if __name__ == "__main__":
    # Create experiment instance with temperature test configs
    experiment = GeneralExperimentMethod(
        input_file=str(repo_root / "test_temperature_commands.csv"),
        instrument_config_file=str(repo_root / "instrument_config.csv"),
        output_dir="Experimental_Data/Outputs",
        output_file="Temperature_Test_Run",
        delay=0.5,
        status_interval=60
    )
    
    print("Starting temperature convergence test...")
    experiment.run_experiment()
    print("Temperature test complete!")
