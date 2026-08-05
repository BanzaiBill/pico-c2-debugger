#include "Devices.h"

namespace
{
constexpr DeviceDescriptor devices[] = {
    {
        "C8051F34x family",
        0x0F,
        0xAD,
        512,
        64U * 1024U
    },
    {
        "Si1000 / C8051F92x-F93x family",
        0x16,
        0xB4,
        1024,
        std::nullopt
    }
};
}

const DeviceDescriptor* findDevice(const std::uint8_t deviceId)
{
    for (const auto& device : devices)
    {
        if (device.deviceId == deviceId)
        {
            return &device;
        }
    }

    return nullptr;
}