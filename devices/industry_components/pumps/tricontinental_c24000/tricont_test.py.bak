import tricont_pyserial as tri

ser = tri.connect(port='COM25', baudrate=9600)

# Step 1: Initialize both pumps
tri.initialize_pump(ser, pump="A", command="N2YZR")  # sends N2YZR by default
tri.initialize_pump(ser, pump="B", command="V1000ZR")

# Step 2: Wait until initialized (blocks until done)
tri.check_until_initialized(ser, pump="A")  # checks for N2YZR response
tri.check_until_initialized(ser, pump="B")  # checks for V1000ZR response

# Step 3: Now move to bottom
tri.send_command(ser, pump="A", command="A192000R")
tri.send_command(ser, pump="B", command="A192000R")

tri.disconnect(ser)