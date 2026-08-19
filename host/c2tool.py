from serial_bridge import SerialBridge
from serial.tools import list_ports
from c2_session import C2Session
from device_database import DeviceDatabase
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / "data" / "devices" / "families.json"

def select_adapter():
    while True:
        ports = list(list_ports.comports())

        if not ports:
            print("No serial ports found.")
            return None

        print()
        print("Available serial ports")
        print("======================")

        for index, port in enumerate(ports, start=1):
            print(
                f"{index}. {port.device:<6} "
                f"{port.description} "
                f"[{port.hwid}]"
            )

        print()
        selection = input("Select port (x to exit): ").strip().lower()

        if selection == "x":
            return None

        try:
            index = int(selection) - 1
        except ValueError:
            print("Please enter a port number.")
            continue

        if not 0 <= index < len(ports):
            print("Invalid selection.")
            continue

        port_name = ports[index].device

        try:
            bridge = SerialBridge(port_name)
            info = bridge.get_info()

            if not info.startswith("INFO C2ADAPTER "):
                print(
                    f"{port_name} did not identify as a C2 adapter."
                )
                bridge.close()
                continue

            print(f"Connected to {port_name}: {info}")
            return bridge

        except Exception as error:
            print(f"Unable to use {port_name}: {error}")

def print_menu(session):
    print()
    print("C2 Toolkit")
    print("==========")
    print("1. Adapter information")
    print("2. Identify target")
    print("3. C2 reset")
    print("4. Address write")
    print("5. Address read")
    print("6. Data write")
    print("7. Data read")
    print("m. Show menu")
    print("x. Exit")
    print()

def require_recognized(session):
    if not session.recognized:
        print("A recognized target must be identified first.")
        return False

    return True

def prompt_byte(prompt):
    while True:
        text = input(prompt).strip()

        try:
            value = int(text, 0)
        except ValueError:
            print("Please enter a valid byte value, for example 0x16 or 22.")
            continue

        if 0 <= value <= 0xFF:
            return value

        print("Value must be between 0x00 and 0xFF.")


def main():
    try:
        bridge = select_adapter()
        if bridge is None:
            return
    except Exception as error:
        print(f"Unable to open adapter: {error}")
        return

   
    try:
        print("Adapter connected.")

        database = DeviceDatabase(DATABASE_FILE)
        session = C2Session(bridge, database)
 
        print_menu(session)

        while True:
            choice = input("c2> ").strip().lower()

            try:
                if choice == "1":
                    print(bridge.get_info())

                elif choice == "2":
                    session.identify()

                    print(f"Device ID:   0x{session.device_id:02X}")
                    print(f"Revision ID: 0x{session.revision_id:02X}")

                    if session.family is not None:
                        print(f"Family:      {session.family['name']}")
                    else:
                        print("Family:      Unknown")

                    print_menu(session)

                elif choice == "3":
                    bridge.reset()
                    print("C2 reset complete.")

                elif choice == "4":
                    address = prompt_byte("Address: ")
                    bridge.address_write(address)
                    print(f"Address register written: 0x{address:02X}")

                elif choice == "5":
                    address = bridge.address_read()
                    print(f"Address register: 0x{address:02X}")

                elif choice == "6":
                    value = prompt_byte("Data: ")
                    bridge.data_write(value)
                    print(f"Data written: 0x{value:02X}")

                elif choice == "7":
                    value = bridge.data_read()
                    print(f"Data read: 0x{value:02X}")

                elif choice == "x":
                    print("Exiting.")
                    break

                elif choice == "m":
                    print_menu(session)

                else:
                    print("Unknown selection. Enter 'm' to show the menu.")

            except Exception:
                raise
    finally:
        bridge.close()


if __name__ == "__main__":
    main()