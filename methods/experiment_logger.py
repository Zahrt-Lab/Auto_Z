# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2025 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# Do not replicate or redistribute without permission
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Experiment logging utilities for AUTO_ZAHRT.
Handles CSV logging, file management, and control file operations.
"""

import os
import csv
import shutil
from datetime import datetime


class ExperimentLogger:
    """Manages experiment logging and file operations."""
    
    def __init__(self, input_file, output_dir="Experimental_Data//Outputs", 
                 output_file="Experimental_Log"):
        """
        Initialize the experiment logger.
        
        Args:
            input_file: Path to the input CSV method file
            output_dir: Base directory for experimental outputs
            output_file: Base name for output log files
        """
        self.input_file = input_file
        self.start_time = datetime.now()
        
        # Create output directory with the date of the experimental run
        date_str = self.start_time.strftime('%Y_%m_%d')
        self.output_dir = os.path.join(output_dir, date_str)
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Create experiment subdirectory
        self.experiment_subdir = os.path.join(
            self.output_dir,
            f"{self.start_time.strftime('%Y_%m_%d_%H-%M-%S')}_{output_file}"
        )
        os.makedirs(self.experiment_subdir, exist_ok=True)
        
        # Copy the input file to the experiment subdirectory
        shutil.copy(self.input_file, 
                   os.path.join(self.experiment_subdir, os.path.basename(self.input_file)))
        
        # Set log filename with timestamp
        self.log_filename = os.path.join(
            self.experiment_subdir,
            f"{self.start_time.strftime('%Y_%m_%d_%H-%M-%S')}_{output_file}.csv"
        )
        
        # Initialize CSV log file with headers
        with open(self.log_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Time', 'Component', 'Action', 'Parameters', 'Output', "Notes"])
        
        # Set status log filename
        self.status_log_filename = os.path.join(
            self.experiment_subdir,
            f"{self.start_time.strftime('%Y_%m_%d_%H-%M-%S')}_Status_Log.csv"
        )
    
    def log_to_csv(self, component, action, params, output, notes=""):
        """
        Log experimental data to CSV file.
        
        Args:
            component: Name of the component/device
            action: Action being performed
            params: Parameters for the action
            output: Result or output of the action
            notes: Optional notes
        """
        elapsed_time = round((datetime.now() - self.start_time).total_seconds(), 2)
        with open(self.log_filename, mode='a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([elapsed_time, component, action, params, output, notes])
    
    @staticmethod
    def initialize_control_file(path: str):
        """
        Initialize a control file with 'True' value.
        
        Args:
            path: Path to the control file
        """
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('True')
            print(f"Control file '{path}' initialized to True")
        except Exception as e:
            print(f"Warning: Could not initialize control file {path}: {e}")
    
    @staticmethod
    def check_continue_flag(path: str) -> bool:
        """
        Check if experiment should continue based on control file.
        
        Args:
            path: Path to the control file
            
        Returns:
            True if experiment should continue, False otherwise
        """
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip().lower()
                    if content == 'false':
                        return False
                    if content == 'true':
                        return True
            return True
        except Exception as e:
            print(f"Warning: Could not read control file {path}: {e}")
            return True
