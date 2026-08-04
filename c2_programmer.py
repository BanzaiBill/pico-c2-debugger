"""Platform-independent Silicon Labs C2 programmer logic."""

from devices import (
    C2_DERIVATIVE_ID_ADDRESS,
    C2_DEVICE_ID_ADDRESS,
    DEVICES_BY_ID,
)


class UnsupportedDeviceError(RuntimeError):
    """Raised when the connected C2 device family is not supported."""


class C2Programmer:
    """C2 programmer logic operating through an injected transport object."""

    def __init__(self, transport):
        self.transport = transport
        self.device = None
        self.derivative_id = None

    def identify_target(self):
        """Identify and validate the connected target.

        This performs only read-only C2 identification operations.
        """
        self.transport.reset()

        self.transport.address_write(C2_DEVICE_ID_ADDRESS)
        device_id = self.transport.data_read()

        device = DEVICES_BY_ID.get(device_id)

        if device is None:
            raise UnsupportedDeviceError(
                f"Unsupported C2 Device ID 0x{device_id:02X}"
            )

        self.transport.address_write(C2_DERIVATIVE_ID_ADDRESS)
        derivative_id = self.transport.data_read()

        self.device = device
        self.derivative_id = derivative_id

        return device

    def print_target_summary(self):
        if self.device is None:
            raise RuntimeError("No target has been identified")

        flash_size = self.device["flash_size"]

        if flash_size is None:
            flash_size_text = "not yet resolved"
        else:
            flash_size_text = f"{flash_size} bytes"

        print()
        print("Target identified")
        print("-----------------")
        print(f"Family:        {self.device['name']}")
        print(f"Device ID:     0x{self.device['device_id']:02X}")
        print(f"Derivative ID: 0x{self.derivative_id:02X}")
        print(f"FPDAT address: 0x{self.device['fpdat_address']:02X}")
        print(f"Page size:     {self.device['flash_page_size']} bytes")
        print(f"Flash size:    {flash_size_text}")