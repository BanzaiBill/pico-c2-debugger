**DISCLAIMER: This project involves direct hardware interfacing. I am not responsible if you damage your hardware, brick your microcontroller, or experience any other issues. Use at your own risk.**

# RP2040 C2 Programmer for Silicon Labs C8051F340

A MicroPython-based C2 debug interface for programming and debugging Silicon Labs C8051F340 microcontrollers using a Raspberry Pi Pico (RP2040).

## Motivation

This project was born out of impatience and curiosity. Rather than waiting for a piece of bespoke C2 debug hardware to arrive in the mail, I decided to build something from parts I had lying around—a Raspberry Pi Pico, some jumper wires, and Claude to help design and implement it. What started as a quick experiment turned into a surprisingly capable tool.

The interactive debugger in the MicroPython REPL is particularly ergonomic and handy. Being able to read and write Special Function Registers while your code is running, with simple named commands like `dbg.read("P0")` or `dbg.watch("UART0", count=20)`, makes hardware debugging feel almost effortless. No compilation cycles, no flashing new debug firmware—just direct, immediate access to your hardware state.

## Overview

The C2 interface is Silicon Labs' proprietary 2-wire debug protocol used for in-system programming and debugging of their 8051-based microcontrollers. This implementation uses the RP2040's PIO (Programmable I/O) for precise clock timing, providing reliable communication with the target device.

### Features

- **Flash programming**: Erase, program, and verify firmware from Intel HEX files
- **Live SFR debugging**: Read and write Special Function Registers while code runs
- **Memory-efficient**: Streams HEX files directly to flash without loading into RAM
- **Reliable timing**: Uses PIO for precise 2µs clock pulses
- **Complete SFR map**: All C8051F34x registers with categories and names

## Hardware Setup

### Required Components

- Raspberry Pi Pico (or any RP2040 board)
- Target C8051F340 board
- 3 jumper wires (C2CK, C2D, GND)
- Optional: 47-100pF capacitor on C2D for improved stability

### Pin Connections

| RP2040 Pin | Pico Pin # | Signal | C8051F340 Pin | 10-Pin Header | Description |
|------------|------------|--------|---------------|---------------|-------------|
| GPIO 4     | Pin 6      | C2CK   | RST/C2CK      | Pin 7         | Clock (directly on debug header) |
| GPIO 5     | Pin 7      | C2D    | P2.0/C2D      | Pin 4         | Bidirectional data |
| GND        | Pin 3, 8, 13, etc. | GND    | GND           | Pin 3, 5, 9   | Ground (directly on debug header) |

### Silicon Labs 10-Pin Debug Header Pinout

```
         ┌─────────────┐
  VDD  1 │ ●         ● │ 2  NC
  GND  3 │ ●         ● │ 4  C2D
  GND  5 │ ●         ● │ 6  NC
 C2CK  7 │ ●         ● │ 8  NC
  GND  9 │ ●         ● │ 10 NC
         └─────────────┘
           (front view)
```

**Note**: Pin 1 is typically marked with a triangle or dot on the PCB.

### Optional Stability Capacitor

If you experience intermittent communication failures, add a small capacitor between C2D and GND:

- **Recommended value**: 47pF - 100pF ceramic capacitor
- **Placement**: As close to the target's C2D pin as possible
- **Purpose**: Filters noise and dampens ringing on the bidirectional data line

This is especially helpful with longer wires or in electrically noisy environments.

## Installation

### 1. Install MicroPython on your Pico

Download the latest MicroPython UF2 from [micropython.org](https://micropython.org/download/rp2-pico/) and copy it to your Pico in BOOTSEL mode.

### 2. Copy the C2 interface to your Pico

```bash
# Using mpremote (install with: pip install mpremote)
mpremote cp c2_interface.py :

# Or copy your firmware file too
mpremote cp your_firmware.ihx :
```

### 3. Connect to the Pico REPL

```bash
mpremote
```

## Usage

### Programming Firmware

The simplest way to program a device:

```python
from c2_interface import program_hex_file

# Erase, program, and verify
program_hex_file("firmware.ihx")

# Program without verification (faster)
program_hex_file("firmware.ihx", verify=False)
```

Example output:
```
=== Initializing programmer ===
Device ID: 0x0F
Revision ID: 0x02
C2 Programming Interface initialized

=== Erasing device ===
Erasing... done!

=== Re-initializing after erase ===
Device ID: 0x0F
Revision ID: 0x02
C2 Programming Interface initialized

=== Programming firmware.ihx ===
Programming: 8192 bytes
Programming complete! (8192 bytes)

=== Verifying ===
Verifying: 8192 bytes
Verification PASSED!

=== Programming successful! ===
```

### Live Debugging (CPU Running)

Debug SFRs while your code is running:

```python
from c2_interface import init_debug_only

dbg = init_debug_only()

# Read registers
dbg.read("P0")          # Read by name
dbg.read(0x80)          # Read by address

# Write registers
dbg.write("P1MDOUT", 0xFF)
dbg.write(0xA5, 0xFF)

# Modify specific bits
dbg.set_bits("P1", 0x08)      # Set bit 3
dbg.clear_bits("P1", 0x08)    # Clear bit 3
dbg.toggle_bits("P1", 0x08)   # Toggle bit 3

# Dump registers by category
dbg.dump_all()                          # All registers
dbg.dump_all(["port", "crossbar"])      # Just ports and crossbar
dbg.dump_all(["uart"])                  # Just UART registers

# Watch a register change over time
dbg.watch("P0", count=20, delay_ms=100)

# Reset the target
dbg.reset()
```

### Programming Mode (CPU Halted)

For flash operations, the CPU must be halted:

```python
from c2_interface import init_debugger

prog, dbg = init_debugger()

# Read flash
data = prog.read_flash_block(0x0000, 256)

# Erase entire device
prog.erase_device()

# Write flash (must erase first)
prog.write_flash_block(0x0000, b'\x02\x00\x03...')

# Get device info
info = prog.get_device_info()
print(f"Version: {info['version']}, Derivative: {info['derivative']}")
```

### Quick Connection Test

```python
from c2_interface import quick_test

quick_test()
```

Expected output:
```
Device ID: 0x0F
Revision ID: 0x02
C2 Programming Interface initialized
SUCCESS: C8051F340 detected!
FPI Version: 0x02
Derivative: 0x1A
```

## API Reference

### High-Level Functions

| Function | Description |
|----------|-------------|
| `program_hex_file(filename, verify=True)` | Erase, program, and optionally verify from Intel HEX file |
| `init_debug_only(retries=5)` | Connect for live debugging (CPU keeps running) |
| `init_debugger(retries=5)` | Connect for programming (halts CPU) |
| `quick_test()` | Verify C2 communication is working |

### C2Debugger Methods

| Method | Description |
|--------|-------------|
| `read(addr)` | Read SFR by address (int) or name (string) |
| `write(addr, value)` | Write SFR |
| `set_bits(addr, bits)` | Set specific bits (read-modify-write) |
| `clear_bits(addr, bits)` | Clear specific bits (read-modify-write) |
| `toggle_bits(addr, bits)` | Toggle specific bits (read-modify-write) |
| `dump(addrs, title)` | Dump list of registers |
| `dump_all(categories=None)` | Dump registers by category |
| `watch(addr, count, delay_ms)` | Monitor a register for changes |
| `reset()` | Reset the target device |

### C2Programmer Methods

| Method | Description |
|--------|-------------|
| `reset_and_init()` | Reset target and initialize programming interface |
| `get_device_info()` | Get FPI version and derivative ID |
| `erase_device()` | Full device erase (unlocks read protection) |
| `read_flash_block(addr, length)` | Read up to 256 bytes of flash |
| `read_flash(addr, length)` | Read arbitrary length of flash |
| `write_flash_block(addr, data)` | Write up to 256 bytes to flash |

### Register Categories

Available categories for `dump_all()`:

| Category | Description |
|----------|-------------|
| `system` | Power control, reset, VDD monitor |
| `cpu` | ACC, B, PSW, SP, DPTR |
| `oscillator` | Clock configuration |
| `flash` | Flash control registers |
| `interrupt` | Interrupt enable/priority |
| `port` | GPIO ports and configuration |
| `crossbar` | Pin crossbar settings |
| `emif` | External memory interface |
| `timer` | Timer 0, 1, 2, 3 |
| `pca` | Programmable Counter Array |
| `uart` | UART0 and UART1 |
| `smbus` | SMBus/I2C interface |
| `spi` | SPI interface |
| `usb` | USB controller |
| `adc` | ADC and analog mux |
| `comparator` | Comparators 0 and 1 |
| `voltage_ref` | Voltage reference |

## Troubleshooting

### "No device detected (got 0xFF)"

- Check wiring: C2CK to pin 7, C2D to pin 4, GND to pin 3/5/9
- Ensure target is powered
- Try shorter wires
- Add a 47-100pF capacitor on C2D

### Intermittent failures

- Add capacitor on C2D line
- Use shorter wires
- Ensure solid ground connection
- Check for loose connections

### "Flash read returned error 0x03"

The device has read protection enabled. You must erase the device to unlock it:

```python
prog, dbg = init_debugger()
prog.erase_device()
```

**Warning**: This erases all flash contents!

### Device ID shows wrong value after reset

This is normal on first connection. The programming sequence will re-read the correct ID.

## Technical Details

### C2 Protocol

The C2 interface uses two signals:
- **C2CK**: Clock signal, active low pulses (<5µs). Holding low >20µs resets the target.
- **C2D**: Bidirectional data, directly with port SFRs while CPU runs, or via flash programming interface when halted.

This implementation uses RP2040 PIO state machines to generate precise 2µs clock pulses (4µs total period), well within the C2 specification.

### Memory Usage

The Intel HEX parser streams the file line-by-line, only holding one record (~16-32 bytes) in memory at a time. This allows programming large firmware files even with limited RAM.

## License

MIT License - feel free to use, modify, and distribute.

## Acknowledgments

- Based on Silicon Labs AN127: Flash Programming via the C2 Interface
- Inspired by various open-source C2 implementations

## Related Projects

- **[SiLabs AN127](https://www.silabs.com/documents/public/application-notes/AN127.pdf)**: Silicon Labs' official application note on Flash Programming via the C2 Interface. The definitive reference for the C2 protocol.
- **[C8051F34x_Glitch](https://github.com/debug-silicon/C8051F34x_Glitch)**: A code protection bypass project for SiLabs C8051F34x chips, featuring Arduino-based hardware and Python host software. Includes a super useful C2 protocol decoder for PulseView/sigrok that was invaluable during development.
- **[c2gen](https://github.com/merbanan/c2gen)**: Another Arduino-based C2 programmer implementation, providing an alternative approach to C2 interfacing.
