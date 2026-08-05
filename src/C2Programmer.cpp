#include "C2Programmer.h"

#include <iomanip>
#include <iostream>

C2Programmer::C2Programmer(IC2Transport& transport)
    : transport_(transport)
{
}

bool C2Programmer::identifyTarget()
{
    transport_.reset();

    transport_.addressWrite(C2_DEVICE_ID_ADDRESS);
    const std::uint8_t deviceId = transport_.dataRead();

    device_ = findDevice(deviceId);

    if (device_ == nullptr)
    {
        std::cerr
            << "Unsupported C2 Device ID 0x"
            << std::hex
            << static_cast<unsigned>(deviceId)
            << std::dec
            << '\n';

        return false;
    }

    transport_.addressWrite(C2_DERIVATIVE_ID_ADDRESS);
    derivativeId_ = transport_.dataRead();

    return true;
}

void C2Programmer::printTargetSummary() const
{
    if (device_ == nullptr)
    {
        std::cout << "No target has been identified.\n";
        return;
    }

    std::cout
        << "\nTarget identified\n"
        << "-----------------\n"
        << "Family:        " << device_->name << '\n'
        << "Device ID:     0x"
        << std::hex << static_cast<unsigned>(device_->deviceId) << '\n'
        << "Derivative ID: 0x"
        << static_cast<unsigned>(derivativeId_) << '\n'
        << "FPDAT address: 0x"
        << static_cast<unsigned>(device_->fpdatAddress) << '\n'
        << std::dec
        << "Page size:     "
        << device_->flashPageSize << " bytes\n";

    if (device_->flashSize.has_value())
    {
        std::cout
            << "Flash size:    "
            << *device_->flashSize << " bytes\n";
    }
    else
    {
        std::cout
            << "Flash size:    not yet resolved\n";
    }
}