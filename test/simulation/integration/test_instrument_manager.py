# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Andrew Zahrt
#
# Contributions by Scott Laverty and Joao Albuquerque are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

"""
Integration tests for InstrumentManager.

Tests cover config loading, device instantiation via the registry, and
connection handling. build_instance is patched so no real serial ports
or hardware are required.
"""

import pytest
from unittest.mock import MagicMock, patch

from methods.instrument_manager import InstrumentManager

_BUILD = "methods.instrument_manager.build_instance"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path, content: str):
    """Write instrument config CSV to a temp file and return its path."""
    p = tmp_path / "instruments.csv"
    p.write_text(content)
    return str(p)


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


class TestLoadInstrumentConfig:

    def test_valid_csv_returns_dataframe(self, tmp_path):
        path = _write_config(
            tmp_path,
            "InstrumentType,DeviceNumber,Name,COMPort\nVICI_M6_Pump,1,Pump,COM1\n",
        )
        with patch(_BUILD, return_value=MagicMock(spec=[])):
            im = InstrumentManager(instrument_config_file=path)
        assert im.instrument_config is not None
        assert len(im.instrument_config) == 1

    def test_bad_path_returns_none_no_crash(self, tmp_path):
        im = InstrumentManager.__new__(InstrumentManager)
        result = im.load_instrument_config("/nonexistent/path/config.csv")
        assert result is None


# ---------------------------------------------------------------------------
# Device instantiation
# ---------------------------------------------------------------------------


class TestInitializeInstruments:

    def test_creates_instruments_dict(self, tmp_path):
        path = _write_config(
            tmp_path,
            "InstrumentType,DeviceNumber,Name,COMPort\nVICI_M6_Pump,1,Pump,COM1\n",
        )
        mock_device = MagicMock(spec=[])
        with patch(_BUILD, return_value=mock_device):
            im = InstrumentManager(instrument_config_file=path)
        assert "VICI_M6_Pump_1" in im.instruments
        assert im.instruments["VICI_M6_Pump_1"] is mock_device

    def test_skips_unknown_instrument_type(self, tmp_path):
        path = _write_config(
            tmp_path,
            "InstrumentType,DeviceNumber,Name,COMPort\nUnknownDevice,1,Dev,COM1\n",
        )
        with patch(_BUILD, side_effect=ValueError("unknown type")):
            im = InstrumentManager(instrument_config_file=path)
        assert im.instruments == {}

    def test_skips_device_that_raises_on_init(self, tmp_path):
        path = _write_config(
            tmp_path,
            "InstrumentType,DeviceNumber,Name,COMPort\nBadDevice,1,Dev,COM1\n",
        )
        with patch(_BUILD, side_effect=RuntimeError("init failed")):
            im = InstrumentManager(instrument_config_file=path)
        assert im.instruments == {}


# ---------------------------------------------------------------------------
# Connection handling
# ---------------------------------------------------------------------------


class TestConnectAllInstruments:

    def test_connect_is_called_on_device(self, tmp_path):
        path = _write_config(
            tmp_path,
            "InstrumentType,DeviceNumber,Name,COMPort\nVICI_M6_Pump,1,Pump,COM1\n",
        )
        mock_device = MagicMock()
        with patch(_BUILD, return_value=mock_device):
            InstrumentManager(instrument_config_file=path)
        mock_device.connect.assert_called_once()

    def test_failed_connect_does_not_crash(self, tmp_path):
        path = _write_config(
            tmp_path,
            "InstrumentType,DeviceNumber,Name,COMPort\nVICI_M6_Pump,1,Pump,COM1\n",
        )
        mock_device = MagicMock()
        mock_device.connect.side_effect = Exception("port not found")
        with patch(_BUILD, return_value=mock_device):
            im = InstrumentManager(instrument_config_file=path)
        # Device is still in instruments dict despite failed connect
        assert "VICI_M6_Pump_1" in im.instruments
