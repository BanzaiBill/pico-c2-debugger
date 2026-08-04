"""Descriptions of supported Silicon Labs C2 device families."""

C2_DEVICE_ID_ADDRESS = 0x00
C2_DERIVATIVE_ID_ADDRESS = 0x01


DEVICES_BY_ID = {
    0x0F: {
        "name": "C8051F34x family",
        "device_id": 0x0F,
        "fpdat_address": 0xAD,
        "flash_page_size": 512,
        "flash_size": 64 * 1024,
    },

    0x16: {
        "name": "Si1000 / C8051F92x-F93x family",
        "device_id": 0x16,
        "fpdat_address": 0xB4,
        "flash_page_size": 1024,
        # Exact capacity will eventually be resolved from the derivative.
        "flash_size": None,
    },
}