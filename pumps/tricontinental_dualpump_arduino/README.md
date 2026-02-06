# Tricontinental C24000 Dual Pump Controller

Arduino-based controller for operating two Tricontinental C24000 syringe pumps in a continuous flow configuration via RS-485 communication.

## Overview

This firmware enables control of two C24000 syringe pumps (Pump A and Pump B) through an Arduino with a MAX485 RS-485 transceiver. The pumps operate in a coordinated manner for continuous flow applications, using the DT (Data Terminal) protocol.

## Hardware Requirements

- Arduino (Uno, Nano, or compatible)
- MAX485 RS-485 transceiver module
- Two Tricontinental C24000 syringe pumps

### Wiring Configuration

| MAX485 Pin | Arduino Pin | Description |
|------------|-------------|-------------|
| RO         | Pin 10      | Receiver Output (to Arduino RX) |
| DI         | Pin 11      | Driver Input (from Arduino TX) |
| RE         | Pin 2       | Receiver Enable (active LOW) |
| DE         | Pin 3       | Driver Enable (active HIGH) |

### Pump Addresses

- **Pump A**: Address `/1`
- **Pump B**: Address `/2`

### Communication Settings

- **Pump Bus Baud Rate**: 9600
- **Serial Monitor Baud Rate**: 115200

## Commands

### Parameter Configuration

Set pump operating parameters before starting:

| Command | Description | Example |
|---------|-------------|---------|
| `initial_speed <value>` | Set aspirate speed (0-65535) | `initial_speed 8000` |
| `initial_volume <value>` | Set stroke volume in increments | `initial_volume 192000` |
| `output_speed <value>` | Set dispense speed | `output_speed 4000` |
| `input_speed <value>` | Set refill speed | `input_speed 8000` |
| `jDispense <value>` | Set j-dispense threshold | `jDispense 800` |
| `params` | Display current parameter values | `params` |

### Default Parameters

| Parameter | Default Value |
|-----------|---------------|
| `initial_speed` | 8000 |
| `initial_volume` | 192000 |
| `output_speed` | 4000 |
| `input_speed` | 8000 |
| `jDispense` | 800 |

### Pump Control Commands

| Command | Description |
|---------|-------------|
| `initialize` | Home both pumps (mechanical initialization). Sends `N2YZR` to both pumps. |
| `start` | Program and run both pumps in continuous flow mode (assumes syringes are already filled) |
| `restart` | Program and run both pumps with an initial refill cycle |
| `fill_A` | Fill Pump A only with an initial refill |
| `stop` | Immediately stop both pumps (sends `T` command) |
| `status` | Query the current status of both pumps (sends `Q` command) |
| `init_status` | Query initialization status. Returns 0 if not initialized, 1 if initialized |
| `help` | Display available commands |

### Raw Command Interface

Send raw DT protocol commands directly to pumps:

```
send <A|B|*> <command>
```

| Target | Description |
|--------|-------------|
| `A` | Send to Pump A only |
| `B` | Send to Pump B only |
| `*` | Send to both pumps |

**Examples:**
- `send A Q` - Query status of Pump A
- `send B ZR` - Initialize Pump B and wait for completion
- `send * T` - Stop both pumps

## Program Flow

### `start` Command Sequence

1. Builds EEPROM programs for both pumps using current parameters
2. Stores programs in pump EEPROM (slot `s0` for Pump A, `s1` for Pump B)
3. Starts Pump B first (waits on handshake `H0`)
4. Starts Pump A (begins dispensing, triggering Pump B handshake)

### `restart` Command Sequence

Same as `start`, but includes an initial aspiration cycle to fill the syringes before beginning continuous flow.

## Pump Program Structure

The pumps are programmed with command strings that include:

| Command | Description |
|---------|-------------|
| `N2` | Set the resolution to 192000 steps |
| `J7` | Set all the auxiliary outputs HIGH |
| `V<n>` | Set velocity/speed |
| `I` | Switch valve to input position |
| `O` | Switch valve to output position |
| `A<n>` | Move plunger to absolute position |
| `j<n>` | Treshhold of absolute position to start the other pump |
| `g` | Mark loop start |
| `G` | Jump back to loop start |
| `H0` | Wait the signal from the other pump for handshake signal 0 |
| `R` | Execute command string |

## Status Responses

When querying status (`Q` command), the pump returns status codes:

- **`@`** - Pump is idle/ready
- **Busy indicators** - Various characters indicate the pump is executing a command

The `init_status` command parses the initialization flag:
- `0` - Pump not initialized
- `1` - Pump initialized and ready

## Typical Usage

1. **Connect and power up** the Arduino and pumps
2. **Open Serial Monitor** at 115200 baud
3. **Initialize pumps** (if needed): `initialize`
4. **Set parameters** (optional): Adjust speeds and volumes as needed
5. **Start pumping**: Use `start` or `restart` depending on syringe state
6. **Monitor**: Use `status` to check pump operation
7. **Stop**: Use `stop` when finished

## Troubleshooting

- **No response from pumps**: Check RS-485 wiring and pump addresses
- **Garbled responses**: Verify baud rate settings (9600 for pump bus)
- **Pump not initializing**: Ensure mechanical path is clear, use `initialize` command
- **Handshake timeout**: Check that both pumps are properly addressed and running

## Notes

- The code avoids using Arduino `String` class to prevent memory fragmentation
- All string literals are stored in FLASH memory using `F()` macro to conserve RAM
- Timing delays between commands (`BETWEEN_CMDS_MS = 30ms`) ensure proper RS-485 bus handling
- Read timeout is set to 1200ms by default (`READ_TIMEOUT_MS`)
