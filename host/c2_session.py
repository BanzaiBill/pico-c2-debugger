class C2Session:
    def __init__(self, bridge, device_database):
        self.bridge = bridge
        self.device_database = device_database

        self.identified = False
        self.recognized = False
        self.device_id = None
        self.revision_id = None
        self.family = None

    def identify(self):
        self.identified = False
        self.recognized = False
        self.device_id = None
        self.revision_id = None
        self.family = None

        self.bridge.reset()

        self.bridge.address_write(0x00)
        self.device_id = self.bridge.data_read()

        self.bridge.address_write(0x01)
        self.revision_id = self.bridge.data_read()

        self.family = self.device_database.find_family(self.device_id)
        self.recognized = self.family is not None

        self.identified = True