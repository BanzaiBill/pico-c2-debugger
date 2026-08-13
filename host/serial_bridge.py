import serial


class SerialBridge:
    def __init__(self, port, baud=115200, timeout=1.0):
        self._serial = serial.Serial(
            port=port,
            baudrate=baud,
            timeout=timeout
        )

    def close(self):
        self._serial.close()

    def get_info(self):
        return self._command("GET_INFO")

    def reset(self):
        response = self._command("RESET")
        self._expect_ok(response)

    def address_write(self, address):
        response = self._command(f"AR_WRITE 0x{address:02X}")
        self._expect_ok(response)

    def address_read(self):
        response = self._command("AR_READ")
        return self._parse_data(response)

    def data_write(self, value):
        response = self._command(f"DR_WRITE 0x{value:02X}")
        self._expect_ok(response)

    def data_read(self):
        response = self._command("DR_READ")
        return self._parse_data(response)

    def _command(self, command):
        self._serial.write((command + "\n").encode("ascii"))
        self._serial.flush()

        response = self._serial.readline().decode(
            "ascii",
            errors="replace"
        ).strip()

        if not response:
            raise RuntimeError(
                f"No response from adapter for command: {command}"
            )

        if response.startswith("ERROR"):
            raise RuntimeError(
                f"Adapter returned: {response}"
            )

        return response

    @staticmethod
    def _expect_ok(response):
        if response != "OK":
            raise RuntimeError(
                f"Expected OK, received: {response}"
            )

    @staticmethod
    def _parse_data(response):
        parts = response.split()

        if len(parts) != 2 or parts[0] != "DATA":
            raise RuntimeError(
                f"Expected DATA response, received: {response}"
            )

        return int(parts[1], 0)