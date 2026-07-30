"""
C2 Interface for RP2040 (MicroPython)
Implements Silicon Labs C2 programming interface for C8051F340 and SI1000

Based on AN127: Flash Programming via the C2 Interface

Hardware connections:
  - GPIO 4: C2CK (connect to target RST/C2CK, pin 7 on SiLabs debug header)
  - GPIO 5: C2D  (connect to target C2D, pin 4 on SiLabs debug header)
  - GND:    Ground (pins 2, 3, or 9 on SiLabs debug header)

Uses PIO for precise clock timing (~2µs pulses).
"""

import time

import rp2
from machine import Pin, mem32


# MicroPython doesn't have TimeoutError built-in
class TimeoutError(Exception):
    pass


class FlashLockedError(Exception):
    """Raised when flash read protection is enabled."""

    pass


# RP2040 GPIO registers
GPIO_OUT_SET = const(0xD0000014)
GPIO_OUT_CLR = const(0xD0000018)
GPIO_IN = const(0xD0000004)
GPIO_OE_SET = const(0xD0000024)
GPIO_OE_CLR = const(0xD0000028)

# Hardcoded pins: C2CK = GPIO 4, C2D = GPIO 5
C2CK_MASK = const(1 << 4)
C2D_MASK = const(1 << 5)

# C2 Address Register Status Bits
C2_INBUSY = const(0x02)
C2_OUTREADY = const(0x01)

# Programming Interface Commands
PI_CMD_GET_VERSION = const(0x01)
PI_CMD_GET_DERIVATIVE = const(0x02)
PI_CMD_DEVICE_ERASE = const(0x03)
PI_CMD_BLOCK_READ = const(0x06)
PI_CMD_BLOCK_WRITE = const(0x07)
PI_CMD_PAGE_ERASE = const(0x08)

# Programming Interface Response Codes
PI_OK = const(0x0D)
PI_ERR_INVALID_CMD = const(0x01)
PI_ERR_CMD_FAILED = const(0x02)
PI_ERR_FLASH_ERROR = const(0x03)  # Often indicates locked flash

# C8051F340 specific
C8051F340_DEVID = const(0x0F)
C8051F340_FPDAT = const(0xAD)
C8051F340_PAGE_SIZE = const(512)
C8051F340_FLASH_SIZE = const(64 * 1024)

# SI1000 specific
SI1000_DEVID = const(0x16)
SI1000_FPDAT = const(0x00)
SI1000_PAGE_SIZE = const(512)
SI1000_FLASH_SIZE = const(64 * 1024)



# =============================================================================
# PIO programs for precise clock timing
# =============================================================================


# PIO program: single strobe, sample D after rising edge
@rp2.asm_pio(set_init=rp2.PIO.OUT_HIGH)
def _pio_strobe_read():
    pull(block)  # Wait for trigger (value ignored)
    set(pins, 0)[31]  # CK low, hold 32 cycles = 2us at 16MHz
    set(pins, 1)[15]  # CK high, hold 16 cycles = 1us
    in_(pins, 1)  # Sample D (bit 0 of in_base)
    push(block)  # Push result to FIFO
    nop()[15]  # Hold high a bit more


# PIO program: single strobe for writing (no read)
@rp2.asm_pio(set_init=rp2.PIO.OUT_HIGH)
def _pio_strobe():
    pull(block)  # Wait for trigger
    set(pins, 0)[31]  # CK low, hold 32 cycles = 2us
    set(pins, 1)[31]  # CK high, hold 32 cycles = 2us


# =============================================================================
# C2Interface - PIO-based low-level interface
# =============================================================================


class C2Interface:
    """
    Low-level C2 interface using PIO for precise clock timing.
    Hardcoded to GPIO 4 (C2CK) and GPIO 5 (C2D).
    """

    def __init__(self, sm_id=0):
        self.ck = Pin(4, Pin.OUT, value=1)
        self.d = Pin(5, Pin.IN)

        # State machine for strobe+read: 16MHz = 62.5ns/cycle
        self.sm_read = rp2.StateMachine(
            sm_id, _pio_strobe_read, freq=16_000_000, set_base=Pin(4), in_base=Pin(5)
        )

        # State machine for strobe only
        self.sm_strobe = rp2.StateMachine(
            sm_id + 1, _pio_strobe, freq=16_000_000, set_base=Pin(4)
        )

        self.sm_read.active(1)
        self.sm_strobe.active(1)

    def _strobe(self):
        """Generate one clock strobe using PIO."""
        self.sm_strobe.put(0)
        time.sleep_us(10)

    def _strobe_and_read(self):
        """Single strobe, return D value sampled after rising edge."""
        self.sm_read.put(0)
        result = self.sm_read.get()
        return result & 1

    def _d_out(self, val):
        """Set D as output with value."""
        if val:
            mem32[GPIO_OUT_SET] = C2D_MASK
        else:
            mem32[GPIO_OUT_CLR] = C2D_MASK
        mem32[GPIO_OE_SET] = C2D_MASK

    def _d_in(self):
        """Set D as input (high-Z)."""
        mem32[GPIO_OUT_SET] = C2D_MASK
        mem32[GPIO_OE_CLR] = C2D_MASK

    def reset(self):
        """Reset target by holding CK low for >20us."""
        # Completely deinit the state machines
        self.sm_read.active(0)
        self.sm_strobe.active(0)

        # Reconfigure pin as regular GPIO output
        self.ck = Pin(4, Pin.OUT, value=1)
        time.sleep_ms(10)
        self.ck.value(0)
        time.sleep_ms(100)
        self.ck.value(1)
        time.sleep_ms(100)

        # Reinitialize PIO state machines
        self.sm_read = rp2.StateMachine(
            0, _pio_strobe_read, freq=16_000_000, set_base=Pin(4), in_base=Pin(5)
        )
        self.sm_strobe = rp2.StateMachine(
            1, _pio_strobe, freq=16_000_000, set_base=Pin(4)
        )
        self.sm_read.active(1)
        self.sm_strobe.active(1)

    def address_write(self, addr):
        """Write to C2 Address register."""
        # START
        self._d_in()
        self._strobe()

        # INS = 11 (Address Write) - LSB first
        self._d_out(1)
        self._strobe()
        self._strobe()

        # ADDRESS - 8 bits LSB first
        for i in range(8):
            self._d_out((addr >> i) & 1)
            self._strobe()

        # STOP
        self._d_in()
        self._strobe()
        time.sleep_ms(1)

    def address_read(self):
        """Read C2 Address register (status)."""
        # START
        self._d_in()
        self._strobe()

        # INS = 10 (Address Read) - LSB first
        self._d_out(0)
        self._strobe()
        self._d_out(1)
        self._strobe()

        # ADDRESS - read 8 bits LSB first
        self._d_in()
        val = 0
        for i in range(8):
            if self._strobe_and_read():
                val |= 1 << i

        # STOP
        self._strobe()
        time.sleep_ms(1)
        return val

    def data_write(self, data):
        """Write to C2 Data register."""
        # START
        self._d_in()
        self._strobe()

        # INS = 01 (Data Write) - LSB first
        self._d_out(1)
        self._strobe()
        self._d_out(0)
        self._strobe()

        # LENGTH = 00 (1 byte)
        self._d_out(0)
        self._strobe()
        self._strobe()

        # DATA - 8 bits LSB first
        for i in range(8):
            self._d_out((data >> i) & 1)
            self._strobe()

        # WAIT - release D, poll until high
        self._d_in()
        for _ in range(10000):
            if self._strobe_and_read():
                break

        # STOP
        self._strobe()
        time.sleep_ms(1)

    def data_read(self):
        """Read from C2 Data register."""
        # START
        self._d_in()
        self._strobe()

        # INS = 00 (Data Read) - LSB first
        self._d_out(0)
        self._strobe()
        self._strobe()

        # LENGTH = 00 (1 byte)
        self._strobe()
        self._strobe()

        # WAIT - release D, poll until high
        self._d_in()
        for _ in range(10000):
            if self._strobe_and_read():
                break

        # DATA - read 8 bits LSB first
        val = 0
        for i in range(8):
            if self._strobe_and_read():
                val |= 1 << i

        # STOP
        self._strobe()
        time.sleep_ms(1)
        return val


# =============================================================================
# C2Programmer - High-level programming interface
# =============================================================================


class C2Programmer:
    """
    High-level programming interface for C8051F340.
    Uses GPIO 4 (C2CK) and GPIO 5 (C2D).
    """

    def __init__(self):
        self.c2 = C2Interface()
        self.fpdat_addr = C8051F340_FPDAT
        self.initialized = False

    def _poll_outready(self, timeout_ms=100):
        """Poll until OutReady sets. Returns status byte."""
        deadline = time.ticks_add(time.ticks_ms(), timeout_ms)
        while time.ticks_diff(deadline, time.ticks_ms()) > 0:
            status = self.c2.address_read()
            if status & C2_OUTREADY:
                return status
            time.sleep_ms(1)
        raise TimeoutError("OutReady timeout")

    def _send_command(self, cmd):
        """Send a command byte and wait for acknowledgment."""
        self.c2.data_write(cmd)
        self._poll_outready()
        ack = self.c2.data_read()
        return ack

    def _read_response(self):
        """Wait for and read a response byte."""
        self._poll_outready()
        return self.c2.data_read()

    def reset_and_init(self):
        """Reset device and initialize programming interface."""
        # Reset target
        self.c2.reset()
        time.sleep_ms(10)

        # Read Device ID - address register defaults to 0x00 after reset
        # Need to write address first, then read data
        self.c2.address_write(0x00)
        device_id = self.c2.data_read()
        print(f"Device ID: 0x{device_id:02X}")

        if device_id != C8051F340_DEVID:
            print(f"Warning: Expected 0x{C8051F340_DEVID:02X}, got 0x{device_id:02X}")

        if device_id == 0xFF:
            raise RuntimeError("No device detected (got 0xFF). Check wiring.")

        # Read Revision ID
        self.c2.address_write(0x01)
        rev_id = self.c2.data_read()
        print(f"Revision ID: 0x{rev_id:02X}")

        # Initialize Programming Interface
        # Write key sequence to FPCTL (address 0x02)
        self.c2.address_write(0x02)
        self.c2.data_write(0x02)  # First key
        self.c2.data_write(0x04)  # Second key - halts CPU
        self.c2.data_write(0x01)  # Third key - activates FPI

        time.sleep_ms(30)  # Wait for flash programming interface to activate

        self.initialized = True
        print("C2 Programming Interface initialized")

        return device_id, rev_id

    def get_device_info(self):
        """Get device version and derivative info."""
        if not self.initialized:
            raise RuntimeError("Call reset_and_init() first")

        self.c2.address_write(self.fpdat_addr)
        time.sleep_ms(1)

        # Get Version
        ack = self._send_command(PI_CMD_GET_VERSION)
        if ack != PI_OK:
            raise RuntimeError(f"GET_VERSION failed: 0x{ack:02X}")
        version = self._read_response()

        # Get Derivative
        ack = self._send_command(PI_CMD_GET_DERIVATIVE)
        if ack != PI_OK:
            raise RuntimeError(f"GET_DERIVATIVE failed: 0x{ack:02X}")
        derivative = self._read_response()

        return {"version": version, "derivative": derivative}

    def read_flash_block(self, address, length):
        """
        Read a block of flash memory.

        Args:
            address: 16-bit start address
            length: number of bytes to read (1-256, 0=256)

        Returns: bytes object with flash contents

        Raises:
            FlashLockedError: If flash read protection is enabled
        """
        if not self.initialized:
            raise RuntimeError("Call reset_and_init() first")

        self.c2.address_write(self.fpdat_addr)
        time.sleep_ms(1)

        # Send Block Read command
        ack = self._send_command(PI_CMD_BLOCK_READ)
        if ack != PI_OK:
            raise RuntimeError(f"BLOCK_READ command failed: 0x{ack:02X}")

        # Send address high byte
        self.c2.data_write((address >> 8) & 0xFF)
        time.sleep_ms(1)

        # Send address low byte
        self.c2.data_write(address & 0xFF)
        time.sleep_ms(1)

        # Send length (0 = 256 bytes)
        self.c2.data_write(length & 0xFF)
        time.sleep_ms(1)

        # Read status/ack byte first - should be 0x0D if OK, 0x03 if locked
        self._poll_outready()
        status = self.c2.data_read()

        # Check if this is an error response
        if status == PI_ERR_FLASH_ERROR:
            raise FlashLockedError(
                "Flash read returned error 0x03. The device likely has "
                "read protection enabled. Erase the device to unlock."
            )
        elif status != PI_OK:
            raise RuntimeError(f"BLOCK_READ failed with status: 0x{status:02X}")

        # Now read the actual data bytes
        actual_length = 256 if length == 0 else length
        data = bytearray()

        for i in range(actual_length):
            self._poll_outready()
            byte = self.c2.data_read()
            data.append(byte)

        return bytes(data)

    def read_flash(self, start_address, total_length, progress_callback=None):
        """
        Read arbitrary amount of flash memory.
        """
        data = bytearray()
        address = start_address
        remaining = total_length

        while remaining > 0:
            chunk_size = min(256, remaining)
            chunk_length = 0 if chunk_size == 256 else chunk_size

            chunk = self.read_flash_block(address, chunk_length)
            data.extend(chunk)

            address += chunk_size
            remaining -= chunk_size

            if progress_callback:
                progress_callback(len(data), total_length)
            else:
                pct = len(data) * 100 // total_length
                print(f"\rRead {len(data)}/{total_length} bytes ({pct}%)", end="")

        print()
        return bytes(data)

    def erase_device(self):
        raise RuntimeError("Flash erase disbled in read only build")
        """
        Perform full device erase.
        WARNING: This erases ALL flash memory!
        """
"""        if not self.initialized:
            raise RuntimeError("Call reset_and_init() first")

        self.c2.address_write(self.fpdat_addr)

        ack = self._send_command(PI_CMD_DEVICE_ERASE)
        if ack != PI_OK:
            raise RuntimeError(f"DEVICE_ERASE command failed: 0x{ack:02X}")

        self.c2.data_write(0xDE)
        self.c2.data_write(0xAD)
        self.c2.data_write(0xA5)

        print("Erasing... ", end="")
        time.sleep_ms(3000)
        print("done!")
"""        

    def write_flash_block(self, address, data):
        raise RuntimeError("Flash write disabled in read only build")
        """
        Write a block of data to flash.
        """
"""
        if not self.initialized:
            raise RuntimeError("Call reset_and_init() first")

        length = len(data)
        if length > 256:
            raise ValueError("Maximum block size is 256 bytes")
        if length == 0:
            return

        self.c2.address_write(self.fpdat_addr)
        time.sleep_ms(1)

        ack = self._send_command(PI_CMD_BLOCK_WRITE)
        if ack != PI_OK:
            raise RuntimeError(f"BLOCK_WRITE command failed: 0x{ack:02X}")

        self.c2.data_write((address >> 8) & 0xFF)
        time.sleep_ms(1)
        self.c2.data_write(address & 0xFF)
        time.sleep_ms(1)
        self.c2.data_write(length & 0xFF)
        time.sleep_ms(1)

        for byte in data:
            self.c2.data_write(byte)
            time.sleep_ms(1)

        self._poll_outready(timeout_ms=1000)
        status = self.c2.data_read()

        if status != PI_OK:
            raise RuntimeError(f"Block Write failed: 0x{status:02X}")
"""

# =============================================================================
# Intel HEX file parser (memory-efficient streaming)
# =============================================================================


def program_hex_file(filename, verify=True):
    raise RuntimeError("Programming disabled in read only build")
    """Erase device and program it with contents of Intel HEX file."""
"""
    print(f"\n=== Initializing programmer ===")
    prog = C2Programmer()
    prog.reset_and_init()

    print("\n=== Erasing device ===")
    prog.erase_device()

    print("\n=== Re-initializing after erase ===")
    prog = C2Programmer()
    prog.reset_and_init()

    print(f"\n=== Programming {filename} ===")
    bytes_written = 0
    base_address = 0

    # Stream through the hex file, programming as we go
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line[0] != ":":
                continue

            try:
                byte_count = int(line[1:3], 16)
                address = int(line[3:7], 16)
                record_type = int(line[7:9], 16)

                if record_type == 0x00:  # Data record
                    data_hex = line[9 : 9 + byte_count * 2]
                    data = bytes(
                        int(data_hex[i : i + 2], 16) for i in range(0, len(data_hex), 2)
                    )
                    full_address = base_address + address

                    # Write this chunk directly
                    prog.write_flash_block(full_address, data)
                    bytes_written += len(data)
                    print(f"\rProgramming: {bytes_written} bytes", end="")

                elif record_type == 0x01:  # EOF
                    break
                elif record_type == 0x02:  # Extended Segment Address
                    data_hex = line[9 : 9 + byte_count * 2]
                    base_address = int(data_hex, 16) << 4
                elif record_type == 0x04:  # Extended Linear Address
                    data_hex = line[9 : 9 + byte_count * 2]
                    base_address = int(data_hex, 16) << 16

            except (ValueError, IndexError) as e:
                print(f"\nWarning: parse error: {e}")
                continue

    print(f"\nProgramming complete! ({bytes_written} bytes)")

    if verify:
        print(f"\n=== Verifying ===")
        errors = 0
        bytes_verified = 0
        base_address = 0

        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line[0] != ":":
                    continue

                try:
                    byte_count = int(line[1:3], 16)
                    address = int(line[3:7], 16)
                    record_type = int(line[7:9], 16)

                    if record_type == 0x00:  # Data record
                        data_hex = line[9 : 9 + byte_count * 2]
                        expected = bytes(
                            int(data_hex[i : i + 2], 16)
                            for i in range(0, len(data_hex), 2)
                        )
                        full_address = base_address + address

                        actual = prog.read_flash_block(full_address, len(expected))

                        if actual != expected:
                            for i, (e, a) in enumerate(zip(expected, actual)):
                                if e != a:
                                    print(
                                        f"\nMismatch at 0x{full_address + i:04X}: expected 0x{e:02X}, got 0x{a:02X}"
                                    )
                                    errors += 1
                                    if errors > 10:
                                        print("Too many errors!")
                                        return False

                        bytes_verified += len(expected)
                        print(f"\rVerifying: {bytes_verified} bytes", end="")

                    elif record_type == 0x01:  # EOF
                        break
                    elif record_type == 0x02:
                        data_hex = line[9 : 9 + byte_count * 2]
                        base_address = int(data_hex, 16) << 4
                    elif record_type == 0x04:
                        data_hex = line[9 : 9 + byte_count * 2]
                        base_address = int(data_hex, 16) << 16

                except (ValueError, IndexError):
                    continue

        print()
        if errors == 0:
            print("Verification PASSED!")
        else:
            print(f"Verification FAILED with {errors} errors")
            return False

    print("\n=== Programming successful! ===")
    return True
"""

# =============================================================================
# C2Debugger - SFR Debug Helper Class
# =============================================================================

# Full C8051F34x SFR definitions with categories
C8051F34X_SFRS = {
    # CPU Core Registers
    0x81: {"name": "SP", "category": "cpu"},
    0x82: {"name": "DPL", "category": "cpu"},
    0x83: {"name": "DPH", "category": "cpu"},
    0xD0: {"name": "PSW", "category": "cpu"},
    0xE0: {"name": "ACC", "category": "cpu"},
    0xF0: {"name": "B", "category": "cpu"},
    # Interrupt Registers
    0xA8: {"name": "IE", "category": "interrupt"},
    0xB8: {"name": "IP", "category": "interrupt"},
    0xE4: {"name": "IT01CF", "category": "interrupt"},
    0xE6: {"name": "EIE1", "category": "interrupt"},
    0xE7: {"name": "EIE2", "category": "interrupt"},
    0xF6: {"name": "EIP1", "category": "interrupt"},
    0xF7: {"name": "EIP2", "category": "interrupt"},
    # Port I/O Registers
    0x80: {"name": "P0", "category": "port"},
    0x90: {"name": "P1", "category": "port"},
    0xA0: {"name": "P2", "category": "port"},
    0xB0: {"name": "P3", "category": "port"},
    0xC7: {"name": "P4", "category": "port"},
    0xF1: {"name": "P0MDIN", "category": "port"},
    0xF2: {"name": "P1MDIN", "category": "port"},
    0xF3: {"name": "P2MDIN", "category": "port"},
    0xF4: {"name": "P3MDIN", "category": "port"},
    0xF5: {"name": "P4MDIN", "category": "port"},
    0xA4: {"name": "P0MDOUT", "category": "port"},
    0xA5: {"name": "P1MDOUT", "category": "port"},
    0xA6: {"name": "P2MDOUT", "category": "port"},
    0xA7: {"name": "P3MDOUT", "category": "port"},
    0xAE: {"name": "P4MDOUT", "category": "port"},
    0xD4: {"name": "P0SKIP", "category": "port"},
    0xD5: {"name": "P1SKIP", "category": "port"},
    0xD6: {"name": "P2SKIP", "category": "port"},
    0xDF: {"name": "P3SKIP", "category": "port"},
    # Crossbar Registers
    0xE1: {"name": "XBR0", "category": "crossbar"},
    0xE2: {"name": "XBR1", "category": "crossbar"},
    0xE3: {"name": "XBR2", "category": "crossbar"},
    # Timer Registers
    0x88: {"name": "TCON", "category": "timer"},
    0x89: {"name": "TMOD", "category": "timer"},
    0x8A: {"name": "TL0", "category": "timer"},
    0x8B: {"name": "TL1", "category": "timer"},
    0x8C: {"name": "TH0", "category": "timer"},
    0x8D: {"name": "TH1", "category": "timer"},
    0x8E: {"name": "CKCON", "category": "timer"},
    0xC8: {"name": "TMR2CN", "category": "timer"},
    0xCA: {"name": "TMR2RLL", "category": "timer"},
    0xCB: {"name": "TMR2RLH", "category": "timer"},
    0xCC: {"name": "TMR2L", "category": "timer"},
    0xCD: {"name": "TMR2H", "category": "timer"},
    0x91: {"name": "TMR3CN", "category": "timer"},
    0x92: {"name": "TMR3RLL", "category": "timer"},
    0x93: {"name": "TMR3RLH", "category": "timer"},
    0x94: {"name": "TMR3L", "category": "timer"},
    0x95: {"name": "TMR3H", "category": "timer"},
    # PCA Registers
    0xD8: {"name": "PCA0CN", "category": "pca"},
    0xD9: {"name": "PCA0MD", "category": "pca"},
    0xDA: {"name": "PCA0CPM0", "category": "pca"},
    0xDB: {"name": "PCA0CPM1", "category": "pca"},
    0xDC: {"name": "PCA0CPM2", "category": "pca"},
    0xDD: {"name": "PCA0CPM3", "category": "pca"},
    0xDE: {"name": "PCA0CPM4", "category": "pca"},
    0xF9: {"name": "PCA0L", "category": "pca"},
    0xFA: {"name": "PCA0H", "category": "pca"},
    0xFB: {"name": "PCA0CPL0", "category": "pca"},
    0xFC: {"name": "PCA0CPH0", "category": "pca"},
    0xE9: {"name": "PCA0CPL1", "category": "pca"},
    0xEA: {"name": "PCA0CPH1", "category": "pca"},
    0xEB: {"name": "PCA0CPL2", "category": "pca"},
    0xEC: {"name": "PCA0CPH2", "category": "pca"},
    0xED: {"name": "PCA0CPL3", "category": "pca"},
    0xEE: {"name": "PCA0CPH3", "category": "pca"},
    0xFD: {"name": "PCA0CPL4", "category": "pca"},
    0xFE: {"name": "PCA0CPH4", "category": "pca"},
    # UART Registers
    0x98: {"name": "SCON0", "category": "uart"},
    0x99: {"name": "SBUF0", "category": "uart"},
    0xD2: {"name": "SCON1", "category": "uart"},
    0xD3: {"name": "SBUF1", "category": "uart"},
    0xE5: {"name": "SMOD1", "category": "uart"},
    0xAC: {"name": "SBCON1", "category": "uart"},
    0xB4: {"name": "SBRLL1", "category": "uart"},
    0xB5: {"name": "SBRLH1", "category": "uart"},
    # SMBus Registers
    0xC0: {"name": "SMB0CN", "category": "smbus"},
    0xC1: {"name": "SMB0CF", "category": "smbus"},
    0xC2: {"name": "SMB0DAT", "category": "smbus"},
    # SPI Registers
    0xA1: {"name": "SPI0CFG", "category": "spi"},
    0xA2: {"name": "SPI0CKR", "category": "spi"},
    0xA3: {"name": "SPI0DAT", "category": "spi"},
    0xF8: {"name": "SPI0CN", "category": "spi"},
    # ADC Registers
    0xBA: {"name": "AMX0N", "category": "adc"},
    0xBB: {"name": "AMX0P", "category": "adc"},
    0xBC: {"name": "ADC0CF", "category": "adc"},
    0xBD: {"name": "ADC0L", "category": "adc"},
    0xBE: {"name": "ADC0H", "category": "adc"},
    0xC3: {"name": "ADC0GTL", "category": "adc"},
    0xC4: {"name": "ADC0GTH", "category": "adc"},
    0xC5: {"name": "ADC0LTL", "category": "adc"},
    0xC6: {"name": "ADC0LTH", "category": "adc"},
    0xE8: {"name": "ADC0CN", "category": "adc"},
    # Comparator Registers
    0x9A: {"name": "CPT1CN", "category": "comparator"},
    0x9B: {"name": "CPT0CN", "category": "comparator"},
    0x9C: {"name": "CPT1MD", "category": "comparator"},
    0x9D: {"name": "CPT0MD", "category": "comparator"},
    0x9E: {"name": "CPT1MX", "category": "comparator"},
    0x9F: {"name": "CPT0MX", "category": "comparator"},
    # Voltage Reference and Regulator Registers
    0xD1: {"name": "REF0CN", "category": "voltage_ref"},
    0xC9: {"name": "REG0CN", "category": "voltage_ref"},
    # Oscillator and Clock Registers
    0xB1: {"name": "OSCXCN", "category": "oscillator"},
    0xB2: {"name": "OSCICN", "category": "oscillator"},
    0xB3: {"name": "OSCICL", "category": "oscillator"},
    0x86: {"name": "OSCLCN", "category": "oscillator"},
    0xA9: {"name": "CLKSEL", "category": "oscillator"},
    0xB9: {"name": "CLKMUL", "category": "oscillator"},
    # Flash Memory Registers
    0x8F: {"name": "PSCTL", "category": "flash"},
    0xB6: {"name": "FLSCL", "category": "flash"},
    0xB7: {"name": "FLKEY", "category": "flash"},
    # External Memory Interface Registers
    0x84: {"name": "EMI0TC", "category": "emif"},
    0x85: {"name": "EMI0CF", "category": "emif"},
    0xAA: {"name": "EMI0CN", "category": "emif"},
    # USB Registers
    0x96: {"name": "USB0ADR", "category": "usb"},
    0x97: {"name": "USB0DAT", "category": "usb"},
    0xD7: {"name": "USB0XCN", "category": "usb"},
    # System Registers
    0x87: {"name": "PCON", "category": "system"},
    0xAF: {"name": "PFE0CN", "category": "system"},
    0xEF: {"name": "RSTSRC", "category": "system"},
    0xFF: {"name": "VDM0CN", "category": "system"},
}

CATEGORY_ORDER = [
    "system",
    "cpu",
    "oscillator",
    "flash",
    "interrupt",
    "port",
    "crossbar",
    "emif",
    "timer",
    "pca",
    "uart",
    "smbus",
    "spi",
    "usb",
    "adc",
    "comparator",
    "voltage_ref",
]


class C2Debugger:
    """Debug helper for reading/writing SFRs."""

    # Reverse lookup: name -> address
    SFR_BY_NAME = {info["name"]: addr for addr, info in C8051F34X_SFRS.items()}

    def __init__(self, prog_or_c2):
        if isinstance(prog_or_c2, C2Programmer):
            self.prog = prog_or_c2
            self.c2 = prog_or_c2.c2
        else:
            self.prog = None
            self.c2 = prog_or_c2

    def _resolve_addr(self, addr):
        """Convert address (int or string name) to int."""
        if isinstance(addr, str):
            name_upper = addr.upper()
            if name_upper in self.SFR_BY_NAME:
                return self.SFR_BY_NAME[name_upper]
            raise ValueError(f"Unknown SFR name: {addr}")
        return addr

    def reset(self):
        """Reset the target."""
        self.c2.reset()

    def name(self, addr):
        addr = self._resolve_addr(addr)
        if addr in C8051F34X_SFRS:
            return C8051F34X_SFRS[addr]["name"]
        return f"0x{addr:02X}"

    def read(self, addr):
        addr = self._resolve_addr(addr)
        self.c2.address_write(addr)
        return self.c2.data_read()

    def write(self, addr, value):
        addr = self._resolve_addr(addr)
        self.c2.address_write(addr)
        self.c2.data_write(value)

    def set_bits(self, addr, bits):
        addr = self._resolve_addr(addr)
        val = self.read(addr)
        self.write(addr, val | bits)

    def clear_bits(self, addr, bits):
        addr = self._resolve_addr(addr)
        val = self.read(addr)
        self.write(addr, val & (~bits & 0xFF))

    def toggle_bits(self, addr, bits):
        addr = self._resolve_addr(addr)
        val = self.read(addr)
        self.write(addr, val ^ bits)

    def dump(self, addrs, title=None):
        if title:
            print(f"=== {title} ===")
        print("Addr  Name       Hex   Binary")
        print("-" * 40)
        for addr in addrs:
            addr = self._resolve_addr(addr)
            try:
                value = self.read(addr)
                print(f"0x{addr:02X}  {self.name(addr):10s} 0x{value:02X}  {value:08b}")
            except Exception as e:
                print(f"0x{addr:02X}  {self.name(addr):10s} ERROR: {e}")

    def dump_all(self, categories=None):
        """
        Dump SFRs by category.

        Args:
            categories: List of category names to dump, or None for all.
        """
        if categories is None:
            categories = CATEGORY_ORDER

        first = True
        for cat in CATEGORY_ORDER:
            if cat not in categories:
                continue

            # Get all SFRs in this category, sorted by address
            addrs = sorted(
                [
                    addr
                    for addr, info in C8051F34X_SFRS.items()
                    if info["category"] == cat
                ]
            )

            if not addrs:
                continue

            if not first:
                print()
            first = False

            self.dump(addrs, cat.upper())

    def watch(self, addr, count=10, delay_ms=500):
        addr = self._resolve_addr(addr)
        name = self.name(addr)
        print(f"Watching 0x{addr:02X} ({name})... Ctrl+C to stop")
        last_val = None
        for i in range(count):
            try:
                val = self.read(addr)
                if val != last_val:
                    print(f"  [{i:3d}] 0x{val:02X}  {val:08b}")
                    last_val = val
            except Exception as e:
                print(f"  [{i:3d}] ERROR: {e}")
            time.sleep_ms(delay_ms)


# =============================================================================
# Initialization functions
# =============================================================================


def init_debugger(retries=5):
    """
    Initialize programmer and debugger. Halts the CPU.
    Returns: (C2Programmer, C2Debugger) tuple
    """
    for attempt in range(retries):
        try:
            prog = C2Programmer()
            prog.reset_and_init()
            prog.c2.address_write(0x00)
            dev_id = prog.c2.data_read()
            if dev_id == C8051F340_DEVID:
                return prog, C2Debugger(prog)
            print(f"Attempt {attempt + 1}: Bad device ID 0x{dev_id:02X}")
        except Exception as e:
            print(f"Attempt {attempt + 1}: {e}")
        time.sleep_ms(500)
    raise RuntimeError(f"Failed to initialize after {retries} attempts")


def init_debug_only(retries=5):
    """
    Initialize debugger WITHOUT halting the CPU.
    Returns: C2Debugger instance
    """
    for attempt in range(retries):
        try:
            c2 = C2Interface()
            c2.address_write(0x00)
            dev_id = c2.data_read()

            if dev_id == C8051F340_DEVID:
                print(f"Device ID: 0x{dev_id:02X} (connected, CPU running)")
                return C2Debugger(c2)
            print(f"Attempt {attempt + 1}: Bad device ID 0x{dev_id:02X}")
        except Exception as e:
            print(f"Attempt {attempt + 1}: {e}")
        time.sleep_ms(500)
    raise RuntimeError(f"Failed to connect after {retries} attempts")


def quick_test():
    """Quick test to verify C2 communication."""
    prog = C2Programmer()
    device_id, rev_id = prog.reset_and_init()

    if device_id == C8051F340_DEVID:
        print("SUCCESS: C8051F340 detected!")
    else if device_id == SI1000_DEVID:
        print("SUCCESS: SI1000 detected!")

    try:
        info = prog.get_device_info()
        print(f"FPI Version: 0x{info['version']:02X}")
        print(f"Derivative: 0x{info['derivative']:02X}")
    except Exception as e:
        print(f"Could not get device info: {e}")

    return device_id, rev_id


if __name__ == "__main__":
    quick_test()
