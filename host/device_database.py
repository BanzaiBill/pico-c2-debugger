import json
from pathlib import Path


class DeviceDatabase:
    def __init__(self, filename):
        self._families = {}

        path = Path(filename)

        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        for family in data["families"]:
            device_id = int(family["device_id"], 0)
            self._families[device_id] = family

    def find_family(self, device_id):
        return self._families.get(device_id)