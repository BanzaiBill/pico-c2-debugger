#include "DummyC2Transport.h"

void DummyC2Transport::reset()
{
    selectedAddress_ = 0x00;
    lastDataWritten_ = 0x00;
}

void DummyC2Transport::addressWrite(
    const std::uint8_t address)
{
    selectedAddress_ = address;
}

std::uint8_t DummyC2Transport::addressRead()
{
    return selectedAddress_;
}

void DummyC2Transport::dataWrite(
    const std::uint8_t value)
{
    lastDataWritten_ = value;
}

std::uint8_t DummyC2Transport::dataRead()
{
    switch (selectedAddress_)
    {
        case 0x00:
            // Simulated Device ID:
            // Si1000 / C8051F92x-F93x family
            return 0x16;

        case 0x01:
            // Simulated derivative ID:
            // Si1000
            return 0xD0;

        default:
            return lastDataWritten_;
    }
}