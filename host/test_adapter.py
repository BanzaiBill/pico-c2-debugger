from serial_bridge import SerialBridge


bridge = SerialBridge("COM6")

try:
    print("Adapter:", bridge.get_info())

    bridge.reset()
    print("Reset: OK")

    bridge.address_write(0x00)
    print(f"Address: 0x{bridge.address_read():02X}")
    print(f"Device ID: 0x{bridge.data_read():02X}")

    bridge.address_write(0x01)
    print(f"Derivative ID: 0x{bridge.data_read():02X}")

finally:
    bridge.close()