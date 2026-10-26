# ------------------------------------------------------------------------------
# Software: Auto_Z
# Copyright (c) 2026 Zahrt Research Group
#
# Contributions by Scott Laverty are acknowledged.
#
# Licensed under the MIT License. See the LICENSE file in the repository root.
# ------------------------------------------------------------------------------

'''
The purpose of this code is to feed into our liquid handler ender 3 class
which we can use as a 3D printer to control the xyz coordinates of our 3D printer

'''

from __future__ import annotations

import time
import serial
import re

class ender3:
    def __init__(self, port="COM14", baud=115200, timeout=2, verbose=False):
        self.verbose = verbose
        self.s = serial.Serial(port, baudrate=baud, timeout=timeout)
        time.sleep(2)  # allow Marlin to reset on connect
        self._drain()

        # Query limits so we can clamp feeds (M203 is in mm/s; F is mm/min)
        self._max_feed_mm_s = {"X": 9000, "Y": 9000, "Z": 9000}
        # Query limits so we clamp location if a position is invalid
        self._max_location_mm = {"X": 235, "Y": 235, "Z": 250}
        self._read_max_feeds()

        # Minimal init
        self.cmd("M17")      # steppers on
        self.cmd("G21")      # mm units
        self.absolute()      # absolute by default
        self.cmd("M211 S1")  # soft endstops ON (safer)

    # ---------- low-level comms ----------
    def _drain(self):
        try:
            while self.s.in_waiting:
                self.s.readline()
        except Exception:
            pass

    def cmd(self, line, wait_ok=True):
        """Send a G/M-code and wait for 'ok'. Tolerant of 'wait', 'busy:', 'ok T:...'."""
        if self.verbose:
            print(">>", line)
        self.s.write((line.strip() + "\n").encode("ascii"))
        if not wait_ok:
            return
        while True:
            resp = self.s.readline().decode("latin1", "ignore").strip()
            if not resp:
                continue
            low = resp.lower()
            if self.verbose:
                print("<<", resp)
            if low.startswith("echo:") or low.startswith("busy:") or low == "wait":
                continue
            if low.startswith("error"):
                raise RuntimeError(f"Printer error: {resp}")
            if low.startswith("ok"):
                return

    # ---------- helpers ----------
    def sync(self):
        """Wait for all queued moves to finish."""
        self.cmd("M400")  # finish moves

    def home(self, axes="XYZ"):
        self.move(x=0,y=0, feed=9000, wait=True) 
        axes = "".join(sorted(set(axes.upper())))
        suffix = " " + " ".join(a for a in ["X", "Y", "Z"] if a in axes) if axes else ""
        self.cmd("G28" + suffix)

    def absolute(self):
        self.cmd("G90")

    def relative(self):
        self.cmd("G91")

    def move(self, x=None, y=None, z=None, feed=3000, wait=True):
        """
        Absolute move (unless you've called relative()).
        feed: mm/min. Will be clamped to axis max feedrates.
        """
        # clamp feed (convert axis mm/s to mm/min, pick the slowest axis being moved)
        feed_mm_min = int(feed)
        candidate_axes = []
        if x is not None: candidate_axes.append("X")
        if y is not None: candidate_axes.append("Y")
        if z is not None: candidate_axes.append("Z")
        if candidate_axes:
            limits = []
            for ax in candidate_axes:
                vmax = self._max_feed_mm_s.get(ax)
                if vmax:
                    limits.append(vmax * 60.0)  # mm/min
            if limits:
                feed_mm_min = min(feed_mm_min, int(min(limits)))

        parts = ["G1"]
        if x is not None: parts.append(f"X{float(x)}")
        if y is not None: parts.append(f"Y{float(y)}")
        if z is not None: parts.append(f"Z{float(z)}")
        parts.append(f"F{feed_mm_min}")
        self.cmd(" ".join(parts))
        if wait:
            self.sync()

    def rapid(self, x=None, y=None, z=None, feed=3000, wait=True):
        parts = ["G0"]
        if x is not None: parts.append(f"X{float(x)}")
        if y is not None: parts.append(f"Y{float(y)}")
        if z is not None: parts.append(f"Z{float(z)}")
        parts.append(f"F{int(feed)}")
        self.cmd(" ".join(parts))
        if wait:
            self.sync()

    def location(self):
        """
        Return current coordinates as a dict: {"X": float, "Y": float, "Z": float, "E": float}
        """

        try:
            self.s.reset_input_buffer()
        except Exception:
            pass

        # ask for position
        self.s.write(b"M114\n")

        x = y = z = e = None
        while True:
            line = self.s.readline().decode("latin1", "ignore").strip()
            if not line:
                continue
            low = line.lower()
            if self.verbose:
                print("<<", line)
            if low.startswith("error"):
                raise RuntimeError(line)
            if low.startswith("ok"):
                break

            # First line usually has X:, Y:, Z:, E:
            m = re.search(r"X:([-\d.]+)\s+Y:([-\d.]+)\s+Z:([-\d.]+).*?E:([-\d.]+)", line)
            if m:
                x, y, z, e = map(float, m.groups())

        return {"X": x, "Y": y, "Z": z, "E": e}

    def soft_endstops(self, on=True):
        self.cmd(f"M211 S{1 if on else 0}")

    def _read_max_feeds(self):
        """Parse M503 to set per-axis max feed (mm/s)."""
        # Ask for a fresh dump so we parse current values
        self.s.reset_input_buffer()
        self.cmd("M503")
        # We just sent M503, so the lines were printed. Ask again and harvest until ok.
        # Easiest: send a no-op and parse buffered echo lines, but we already printed them.
        # Instead, query again and capture lines until 'ok' here:
        self.s.write(b"M503\n")
        x = y = z = None
        while True:
            line = self.s.readline().decode("latin1", "ignore").strip()
            if not line:
                continue
            low = line.lower()
            if low.startswith("ok"):
                break
            if "M203" in line:
                # Example: 'echo:  M203 X500.00 Y500.00 Z5.00 E25.00'
                m = re.search(r"X([0-9.]+)\s+Y([0-9.]+)\s+Z([0-9.]+)", line)
                if m:
                    x = float(m.group(1))
                    y = float(m.group(2))
                    z = float(m.group(3))
        if x: self._max_feed_mm_s["X"] = x
        if y: self._max_feed_mm_s["Y"] = y
        if z: self._max_feed_mm_s["Z"] = z

    def close(self):
        try:
            self.s.close()
        except Exception:
            pass


# ---------------------- minimal example ----------------------
'''
if __name__ == "__main__":
    e = ender3(port="COM23", baud=115200, timeout=2, verbose=False)
    try:
        e.home()
        e.move(z=250, feed=300)            # lift Z first (<= 300 mm/min is safest)
        e.move(x=10, y=10, feed=9000)
        e.move(x=100, feed=9000)
        e.move(y=210, feed=9000)
        e.move(z=200, feed=300)
        e.location()
    finally:
        e.close()
'''
