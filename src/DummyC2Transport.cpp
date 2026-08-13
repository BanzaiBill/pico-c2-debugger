#include "DummyC2Transport.h"

void DummyC2Transport::reset()
{
    selectedAddress_ = 0x00;
    lastDataWritten_ = 0x00;

    simulatedTarget_++;
    if (simulatedTarget_ >= 3)
    {
        simulatedTarget_ = 0;
    }
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
    if (selectedAddress_ == 0x00)
    {
        switch (simulatedTarget_)
        {
            case 0:
                return 0x16; // Si1000 family

            case 1:
                return 0x0F; // C8051F34x family

            default:
                return 0xFE; // unknown device
        }
    }

    if (selectedAddress_ == 0x01)
    {
        return 0x01; // simulated revision ID
    }

    return lastDataWritten_;
}