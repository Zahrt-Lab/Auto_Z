# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Integration tests for ExperimentLogger.

Tests cover directory creation, CSV logging, control file initialization,
and control flag checking. No hardware or serial connections required.
"""

import csv
import os

from methods.experiment_logger import ExperimentLogger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_logger(tmp_path) -> ExperimentLogger:
    """Create an ExperimentLogger backed by a temporary input CSV."""
    input_csv = tmp_path / "method.csv"
    input_csv.write_text("Component,Action,Parameters,Notes,delay\n")
    return ExperimentLogger(
        input_file=str(input_csv),
        output_dir=str(tmp_path / "output"),
        output_file="TestLog",
    )


# ---------------------------------------------------------------------------
# Directory and file creation
# ---------------------------------------------------------------------------


class TestInitialization:

    def test_creates_output_dirs(self, tmp_path):
        logger = _make_logger(tmp_path)
        assert os.path.isdir(logger.output_dir)
        assert os.path.isdir(logger.experiment_subdir)

    def test_copies_input_file_to_subdir(self, tmp_path):
        input_csv = tmp_path / "method.csv"
        input_csv.write_text("Component,Action,Parameters,Notes,delay\n")
        logger = ExperimentLogger(
            input_file=str(input_csv),
            output_dir=str(tmp_path / "output"),
            output_file="TestLog",
        )
        copied = os.path.join(logger.experiment_subdir, "method.csv")
        assert os.path.isfile(copied)

    def test_log_file_has_header_row(self, tmp_path):
        logger = _make_logger(tmp_path)
        with open(logger.log_filename, newline="") as f:
            header = next(csv.reader(f))
        assert header == ["Time", "Component", "Action", "Parameters", "Output", "Notes"]

    def test_status_log_filename_set(self, tmp_path):
        logger = _make_logger(tmp_path)
        assert logger.status_log_filename.endswith("_Status_Log.csv")


# ---------------------------------------------------------------------------
# CSV logging
# ---------------------------------------------------------------------------


class TestLogToCsv:

    def test_log_to_csv_appends_row(self, tmp_path):
        logger = _make_logger(tmp_path)
        logger.log_to_csv("Pump_1", "aspirate", "volume=500", "OK", "note")
        with open(logger.log_filename, newline="") as f:
            rows = list(csv.reader(f))
        # rows[0] is the header
        assert len(rows) == 2
        _, component, action, params, output, notes = rows[1]
        assert component == "Pump_1"
        assert action == "aspirate"
        assert params == "volume=500"
        assert output == "OK"
        assert notes == "note"

    def test_log_to_csv_elapsed_time_is_numeric(self, tmp_path):
        logger = _make_logger(tmp_path)
        logger.log_to_csv("TC720_1", "get_temperature", "", "25.0")
        with open(logger.log_filename, newline="") as f:
            rows = list(csv.reader(f))
        assert float(rows[1][0]) >= 0

    def test_log_to_csv_multiple_rows(self, tmp_path):
        logger = _make_logger(tmp_path)
        logger.log_to_csv("A", "action1", "", "out1")
        logger.log_to_csv("B", "action2", "", "out2")
        with open(logger.log_filename, newline="") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 3  # header + 2 data rows


# ---------------------------------------------------------------------------
# Control file operations
# ---------------------------------------------------------------------------


class TestControlFile:

    def test_initialize_control_file_writes_true(self, tmp_path):
        path = str(tmp_path / "control.txt")
        ExperimentLogger.initialize_control_file(path)
        assert open(path).read() == "True"

    def test_check_continue_flag_true(self, tmp_path):
        path = tmp_path / "control.txt"
        path.write_text("True")
        assert ExperimentLogger.check_continue_flag(str(path)) is True

    def test_check_continue_flag_false(self, tmp_path):
        path = tmp_path / "control.txt"
        path.write_text("False")
        assert ExperimentLogger.check_continue_flag(str(path)) is False

    def test_check_continue_flag_missing_file_returns_true(self, tmp_path):
        path = str(tmp_path / "nonexistent.txt")
        assert ExperimentLogger.check_continue_flag(path) is True
