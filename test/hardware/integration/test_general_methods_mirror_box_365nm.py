# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2026 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

"""
Hardware integration tests for GeneralExperimentMethod with a 365nm mirror box light source.

Every test goes through run_experiment() with a real mirror box device.
InstrumentManager is patched to inject the real mirror_box_365nm_device fixture.
StatusMonitor is patched to suppress background polling.
time.sleep is NOT patched — real delays are needed for serial I/O.

Safety constraints:
  - No high-intensity or long-duration exposures (365nm can be harmful)

These tests are auto-skipped if no 365nm mirror box is detected.
"""

import re
import pytest
import pandas as pd
from unittest.mock import patch 

from methods.methods import GeneralExperimentMethod

pytestmark = [pytest.mark.hardware, pytest.mark.mirror_box_365nm]

_IM_INIT = "methods.instrument_manager.InstrumentManager.__init__"
_SM_START = "methods.status_monitor.StatusMonitor.start"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_gm(tmp_path, mirror_box_365nm_device, method_rows: str) -> GeneralExperimentMethod:
    """Create a GeneralExperimentMethod with InstrumentManager patched to inject mirror_box_365nm_device."""
    method_csv = tmp_path / "method.csv"
    method_csv.write_text("Component,Action,Parameters,Notes,delay\n" + method_rows)
    config_csv = tmp_path / "instruments.csv"
    config_csv.write_text("InstrumentType,DeviceNumber,Name,COMPort,OtherParams\n")

    def _fake_im_init(self_im, instrument_config_file, experiment_subdir=None):
        self_im.instrument_config_file = instrument_config_file
        self_im.experiment_subdir = experiment_subdir
        self_im.instruments = {"MIRROR_BOX_365NM_1": mirror_box_365nm_device}
        self_im.instrument_types = {"MIRROR_BOX_365NM_1": "LightSource"}
        self_im.instrument_config = None

    with patch(_IM_INIT, _fake_im_init):
        return GeneralExperimentMethod(
            input_file=str(method_csv),
            instrument_config_file=str(config_csv),
            output_dir=str(tmp_path / "output"),
            instrument_control_file=str(tmp_path / "instrument_control.txt"),
            dh2000_light_source_control_file=str(tmp_path / "dh2000_light_source_control.txt"),
        )
    
def _run(gm) -> pd.DataFrame:
    """Run the experiment and return the logged data as a DataFrame."""
    with patch(_SM_START):
        gm.run_experiment()
    return pd.read_csv(gm.logger.log_filename)


# ---------------------------------------------------------------------------
# Safety test
# ---------------------------------------------------------------------------


class TestSafetyHardware:

    def test_full_run_completes_without_exception(self, tmp_path, mirror_box_365nm_device):
        """Full experiment with 365nm exposure must not raise."""
        gm = _build_gm(
            tmp_path,
            mirror_box_365nm_device,
            method_rows='MIRROR_BOX_365NM_1,expose,"duration=1.0",,0.5\n',
        )
        _run(gm)
        