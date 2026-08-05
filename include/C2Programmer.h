#pragma once

#include "Devices.h"
#include "IC2Transport.h"

#include <cstdint>

class C2Programmer
{
public:
    explicit C2Programmer(IC2Transport& transport);

    bool identifyTarget();
    void printTargetSummary() const;

private:
    IC2Transport& transport_;
    const DeviceDescriptor* device_ = nullptr;
    std::uint8_t derivativeId_ = 0;
};