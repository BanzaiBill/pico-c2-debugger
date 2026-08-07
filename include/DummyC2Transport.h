#pragma once

#include "IC2Transport.h"

#include <cstdint>

class DummyC2Transport final : public IC2Transport
{
public:
    void reset() override;

    void addressWrite(std::uint8_t address) override;
    std::uint8_t addressRead() override;

    void dataWrite(std::uint8_t value) override;
    std::uint8_t dataRead() override;

private:
    std::uint8_t selectedAddress_ = 0x00;
    std::uint8_t lastDataWritten_ = 0x00;
};