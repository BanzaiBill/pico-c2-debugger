"""Console-driven substitute for a physical C2 target."""


class SimulatedC2:
    """Simulate the small portion of C2 needed for target identification."""

    def __init__(self, pi_version=0x02):
        self._selected_address = 0x00
        self._pi_version = pi_version

    def reset(self):
        """Simulate a C2 reset.

        The C2 address register selects Device ID address 0x00 after reset.
        """
        self._selected_address = 0x00
        print("[SIM] C2 reset")

    def address_write(self, address):
        """Select a C2 register address."""
        if not 0x00 <= address <= 0xFF:
            raise ValueError("C2 address must be an 8-bit value")

        self._selected_address = address
        print(f"[SIM] C2 address selected: 0x{address:02X}")

    def data_read(self):
        """Return a simulated value for the selected C2 register."""
        if self._selected_address == 0x00:
            return self._prompt_for_byte("Enter simulated Device ID")

        if self._selected_address == 0x01:
            return self._prompt_for_byte("Enter simulated Derivative ID")

        raise RuntimeError(
            "No simulated value is defined for C2 address "
            f"0x{self._selected_address:02X}"
        )

    def activate_programming_interface(self):
        print("[SIM] Programming Interface activated")
        return self._pi_version

    @staticmethod
    def _prompt_for_byte(prompt):
        while True:
            text = input(f"{prompt} [0x00-0xFF]: ").strip()

            try:
                value = int(text, 0)
            except ValueError:
                print("Invalid number. Examples: 0x16 or 22")
                continue

            if not 0x00 <= value <= 0xFF:
                print("Value must fit in one byte.")
                continue

            return value