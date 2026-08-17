from serial_bridge import SerialBridge
from c2_session import C2Session
from device_database import DeviceDatabase
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / "data" / "devices" / "families.json"

PORT = "COM6"


def print_menu(session):
    print()
    print("C2 Toolkit")
    print("==========")
    print("1. Adapter information")
    print("2. Identify target")
    print("3. C2 reset")

    if session.recognized:
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
    print(f"Opening adapter on {PORT}...")

    try:
        bridge = SerialBridge(PORT)
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
                    if require_recognized(session):
                        address = prompt_byte("Address: ")
                        bridge.address_write(address)
                        print(f"Address register written: 0x{address:02X}")

                elif choice == "5":
                    if require_recognized(session):
                        address = bridge.address_read()
                        print(f"Address register: 0x{address:02X}")

                elif choice == "6":
                    if require_recognized(session):
                        value = prompt_byte("Data: ")
                        bridge.data_write(value)
                        print(f"Data written: 0x{value:02X}")

                elif choice == "7":
                    if require_recognized(session):
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