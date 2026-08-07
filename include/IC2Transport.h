#pragma once

#include <cstdint>

class IC2Transport
{
public:
    virtual ~IC2Transport() = default;

    virtual void reset() = 0;

    virtual void addressWrite(std::uint8_t address) = 0;
    virtual std::uint8_t addressRead() = 0;

    virtual void dataWrite(std::uint8_t value) = 0;
    virtual std::uint8_t dataRead() = 0;
};