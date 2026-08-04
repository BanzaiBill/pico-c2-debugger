"""PC-runnable entry point for the C2 programmer framework."""

from c2_programmer import C2Programmer, UnsupportedDeviceError
from simulated_c2 import SimulatedC2


SIMULATE_TARGET = True


def main():
    if not SIMULATE_TARGET:
        raise RuntimeError(
            "Real hardware transport has not yet been connected "
            "to the refactored framework"
        )

    transport = SimulatedC2()
    programmer = C2Programmer(transport)

    try:
        programmer.identify_target()
    except UnsupportedDeviceError as error:
        print()
        print(f"Identification stopped: {error}")
        print("No further target operations are permitted.")
        return

    programmer.print_target_summary()


if __name__ == "__main__":
    main()