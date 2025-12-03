import sys
from pathlib import Path

# Add repo root to sys.path
repo_root = Path(__file__).parent
sys.path.insert(0, str(repo_root))

# Now import and run the methods script
from methods.methods import GeneralExperimentMethod

if __name__ == "__main__":
    # Create experiment instance with test configs
    experiment = GeneralExperimentMethod(
        input_file=str(repo_root / "test_commands.csv"),
        instrument_config_file=str(repo_root / "instrument_config.csv"),
        output_dir="Experimental_Data/Outputs",
        output_file="Test_Run",
        delay=0.5,
        status_interval=60
    )
    
    print("Starting experiment...")
    experiment.run_experiment()
    print("Experiment complete!")
