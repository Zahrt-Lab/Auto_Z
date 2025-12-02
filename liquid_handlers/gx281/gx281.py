# ------------------------------------------------------------------------------
# Software: AUTO_ZAHRT
# Copyright: (C) 2024 by Professor Andrew Zahrt
# This software is the intellectual property of Professor Andrew Zahrt
# Contributions by graduate students Scott Laverty and David Polefrone are acknowledged.
# All rights reserved.
# ------------------------------------------------------------------------------

import ctypes
import time
from ctypes import *

from liquid_handlers.liquid_handlers import LiquidHandler


# You can reuse the immediate() and buffered() functions from Approach 1.
def immediate(unitid, command):
    try:
        lib = windll.gsioc32
        icmd = lib.ICmd

        rsp = ctypes.create_string_buffer(256)
        rsplen = ctypes.c_int(256)

        icmd(unitid, command.encode('utf-8'), rsp, rsplen)
        return rsp.value
    except OSError as ex:
        print("WARNING:", ex)
        return "Error"


def buffered(unitid, command):
    try:
        lib = windll.gsioc32
        bcmd = lib.BCmd

        rsp = ctypes.create_string_buffer(256)
        rsplen = ctypes.c_int(256)

        bcmd(unitid, command.encode('utf-8'), rsp, rsplen)
        return rsp.value
    except OSError as ex:
        print("WARNING:", ex)
        return "Error"


# Replace the gsioc_cmd() with a function call that uses the correct direct function

class GX281(LiquidHandler):
    def __init__(self, uid=25):
        self.uid = uid
        self.XMIN = 0
        self.XMAX = 700
        self.YMIN = 0
        self.YMAX = 380
        self.ZMIN = 0
        self.ZMAX = 125

        # Default 204: 27 28x57mm 20mL scin vials.
        self.rack1 = '204'
        self.rack2 = '204'
        self.rack3 = '204'
        self.rack4 = '204'
        self.rack5 = '204'
        self.rack6 = '204'

    ######################################################################
    ### Core movement functions - using direct function calls

    def home(self):
        print("-" * 50)
        print("Moving GX281 home")
        print("-" * 50)
        return buffered(self.uid, 'SH')

    def get_xy(self):
        print("-" * 50)
        print("Locating X and Y")
        print("-" * 50)
        return immediate(self.uid, 'X')

    def move_xy(self, x, y):
        print("-" * 50)
        print(f"Moving GX281 X and Y location {x} and {y}")
        print("-" * 50)
        if x < self.XMIN: x = self.XMIN
        if x > self.XMAX: x = self.XMAX
        if y < self.YMIN: y = self.YMIN
        if y > self.YMAX: y = self.YMAX

        current_z = self.get_z()
        if current_z != 125:
            self.move_z(125)

        print(f"Moving to X: {x}, Y: {y}")
        return buffered(self.uid, f'SX{x}/{y}')

    def get_z(self):
        print("-" * 50)
        print("Get Z axis of needle")
        print("-" * 50)
        return immediate(self.uid, 'Z')

    def move_z(self, z):
        print("-" * 50)
        print(f"Moving to Z: {z}")
        print("-" * 50)
        if z < self.ZMIN: z = self.ZMIN
        if z > self.ZMAX: z = self.ZMAX
        return buffered(self.uid, f'SZ{z}')

    ######################################################################
    ### Base-level commands; use with caution.

    def reset_handler(self):
        return immediate(self.uid, '$')

    def read_current_nvram(self):
        # return "AA=xxxx"; see NVMM for more info.
        return immediate(self.uid, '@')

    def set_nvram(self, addr, val):
        return immediate(self.uid, 'S@AA=' + str(val))

    def reset_nvram(self):
        # Omitting other test modes [0, 1, 2, 7].
        return buffered( self.uid, 'S~9')

    def read_id_strings(self):
        # 1 XY, 2 Z, 3 GX Prep, 4 GX Z IM, 5/6 GX Dir IM [L/R]
        return immediate(self.uid, '~')

    def enable_xyz_motors(self):
        return buffered(self.uid, 'SE111')

    def read_diverter_state(self):
        return immediate(self.uid, 'F')

    def set_diverter_state(self, s=0):
        return buffered(self.uid, 'SF' + str(s))

    def read_input_contacts(self):
        return immediate(self.uid, 'I')

    def read_output_contacts(self):
        return immediate(self.uid, 'J')

    ######################################################################
    ### Fun commands.

    def beep(self, t=0.1):
        return buffered(self.uid, 'SA' + str(t))

    def write_display(self, msg, line=2):
        # or line=1
        return buffered(self.uid, 'SW' + str(line) + '=' + msg)

    ######################################################################
    ### Core device commands.

    def get_device(self):
        print("-" * 50)
        print("Getting GX281 Device is available")
        print("-" * 50)
        return immediate(self.uid, '%')

    def read_motor_status(self):
        print("-" * 50)
        print("Reading Motor Status")
        print("-" * 50)
        # xyzp. P parked, R running, E error, I not initialized, X no pump.
        # RRRR while commands pending in buffered S command FIFO.
        return immediate(self.uid, 'M')

    def read_travel_ranges(self):
        # 0/700, 0/380, 0/125.
        return immediate(self.uid, 'Q')

    def read_buffer(self):
        # Buffer holds up to 21 commands.
        return immediate(self.uid, 'S')

    def read_error(self):
        print("-" * 50)
        print("Reading Errors")
        print("-" * 50)
        return immediate(self.uid, 'e')

    def clear_error(self):
        print("-" * 50)
        print("Clearing Errors")
        print("-" * 50)
        # Optional n to raise error for testing.
        return buffered(self.uid, 'Se')

    ######################################################################