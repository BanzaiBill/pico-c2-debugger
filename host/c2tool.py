from serial_bridge import SerialBridge


PORT = "COM6"


def print_menu():
    print()
    print("C2 Toolkit")
    print("==========")
    print("1. Adapter information")
    print("2. C2 reset")
    print("3. Address write")
    print("4. Address read")
    print("5. Data write")
    print("6. Data read")
    print("7. Exit")
    print("m. Show menu")
    print()


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

        print_menu()

        while True:
            choice = input("c2> ").strip().lower()

            try:
                if choice == "1":
                    print(bridge.get_info())

                elif choice == "2":
                    bridge.reset()
                    print("C2 reset complete.")

                elif choice == "3":
                    address = prompt_byte("Address: ")
                    bridge.address_write(address)
                    print(f"Address register written: 0x{address:02X}")

                elif choice == "4":
                    address = bridge.address_read()
                    print(f"Address register: 0x{address:02X}")

                elif choice == "5":
                    value = prompt_byte("Data: ")
                    bridge.data_write(value)
                    print(f"Data written: 0x{value:02X}")

                elif choice == "6":
                    value = bridge.data_read()
                    print(f"Data read: 0x{value:02X}")

                elif choice == "7":
                    print("Exiting.")
                    break

                elif choice == "m":
                    print_menu()

                else:
                    print("Unknown selection. Enter 'm' to show the menu.")

            except Exception as error:
                print(f"Error: {error}")
    finally:
        bridge.close()


if __name__ == "__main__":
    main()