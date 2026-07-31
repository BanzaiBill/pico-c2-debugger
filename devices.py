# devices.py

C2_DEVICE_ID_ADDR = 0x00
C2_DERIVATIVE_ID_ADDR = 0x01

DEVICES_BY_ID = {
    0x0F: {
        "name": "C8051F340",
        "fpdat_addr": 0xAD,
        "page_size": 512,
        "flash_size": 64 * 1024,
    },

    0x16: {
        "name": "Si1000 family",
        "fpdat_addr": 0xB4,
        "page_size": 1024,
        "flash_size": None,
    },
}