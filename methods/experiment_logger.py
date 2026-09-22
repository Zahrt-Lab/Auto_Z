# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Experiment logging utilities for General Methods.
Handles CSV logging, file management, and control file operations.
"""

from __future__ import annotations

import os
import csv
import shutil
from datetime import datetime


class ExperimentLogger:
    """Manages experiment logging and file operations."""

    def __init__(
        self,
        input_file: str,
        output_dir: str = "Experimental_Data//Outputs",
        output_file: str = "Experimental_Log",
    ) -> None:
        """
        Initialize the experiment logger.

        Parameters:
         - input_file: Path to the input CSV method file
         - output_dir: Base directory for experimental outputs
         - output_file: Base name for output log files

        Returns:
         - None
        """
        self.input_file: str = input_file
        self.start_time: datetime = datetime.now()

        # Create output directory with the date of the experimental run if it doesn't exist
        date_str = self.start_time.strftime("%Y_%m_%d")
        self.output_dir: str = os.path.join(output_dir, date_str)
        os.makedirs(self.output_dir, exist_ok=True)

        # For each new experiment in a day,
        # a new experiment subdirectory is created with a timestamp
        self.experiment_subdir: str = os.path.join(
            self.output_dir,
            f"{self.start_time.strftime('%Y_%m_%d_%H-%M-%S')}_{output_file}",
        )
        os.makedirs(self.experiment_subdir, exist_ok=True)

        # Copy the input file to the experiment subdirectory as a reference for the experimental run
        shutil.copy(
            self.input_file,
            os.path.join(self.experiment_subdir, os.path.basename(self.input_file)),
        )

        # Set log filename with timestamp
        self.log_filename: str = os.path.join(
            self.experiment_subdir,
            f"{self.start_time.strftime('%Y_%m_%d_%H-%M-%S')}_{output_file}.csv",
        )

        # Initialize CSV log file with headers
        with open(self.log_filename, mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(
                ["Time", "Component", "Action", "Parameters", "Output", "Notes"]
            )

        # Set status log filename
        self.status_log_filename: str = os.path.join(
            self.experiment_subdir,
            f"{self.start_time.strftime('%Y_%m_%d_%H-%M-%S')}_Status_Log.csv",
        )

    def log_to_csv(self, component: str, action: str, params: str, output: str, notes: str = "") -> None:
        """
        Log experimental data to CSV file.

        Parameters:
            component: Name of the component/device
            action: Action being performed
            params: Parameters for the action
            output: Result or output of the action
            notes: Optional notes
        """
        elapsed_time = round((datetime.now() - self.start_time).total_seconds(), 2)
        with open(self.log_filename, mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([elapsed_time, component, action, params, output, notes])

    @staticmethod
    def initialize_control_file(path: str) -> None:
        """
        Initialize a control file with 'True' value.

        Parameters:
            path: Path to the control file
        """
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("True")
            print(f"Control file '{path}' initialized to True")
        except Exception as e:
            print(f"Warning: Could not initialize control file {path}: {e}")

    @staticmethod
    def check_continue_flag(path: str) -> bool:
        """
        Check if experiment should continue based on control file.

        Parameters:
            path: Path to the control file

        Returns:
            True if experiment should continue, False otherwise
        """
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read().strip().lower()
                    if content == "false":
                        return False
                    if content == "true":
                        return True
            return True
        except Exception as e:
            print(f"Warning: Could not read control file {path}: {e}")
            return True
