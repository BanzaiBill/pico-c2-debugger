#pragma once

#include "IC2Transport.h"
#include <cstdint>
#include "hardware/pio.h"

class PicoC2Transport final : public IC2Transport
{
public:
    PicoC2Transport(std::uint8_t c2ckPin, std::uint8_t c2dPin);

    void begin();

    void reset() override;
    void addressWrite(std::uint8_t address) override;
    std::uint8_t addressRead() override;
    void dataWrite(std::uint8_t value) override;
    std::uint8_t dataRead() override;

private:
    void initializePio();
    void strobe();
    uint8_t strobeAndRead();

    uint8_t c2ckPin_;
    uint8_t c2dPin_;

    PIO pio_ = pio0;

    uint smStrobe_ = 0;
    uint smRead_ = 1;

    uint strobeOffset_ = 0;
    uint strobeReadOffset_ = 0;
};