#include "PicoC2Transport.h"

#include <Arduino.h>

#include "hardware/clocks.h"
#include "hardware/gpio.h"
#include "hardware/pio.h"
#include "hardware/pio_instructions.h"


namespace
{
constexpr float PIO_FREQUENCY = 16'000'000.0f;

const uint16_t strobeInstructions[] =
{
    static_cast<uint16_t>(
        pio_encode_pull(false, true)),

    static_cast<uint16_t>(
        pio_encode_set(pio_pins, 0) |
        pio_encode_delay(31)),

    static_cast<uint16_t>(
        pio_encode_set(pio_pins, 1) |
        pio_encode_delay(31)),

    static_cast<uint16_t>(
        pio_encode_push(false, true))
};

const pio_program_t strobeProgram =
{
    .instructions = strobeInstructions,
    .length = 4,
    .origin = -1
};


const uint16_t strobeReadInstructions[] =
{
    static_cast<uint16_t>(
        pio_encode_pull(false, true)),

    static_cast<uint16_t>(
        pio_encode_set(pio_pins, 0) |
        pio_encode_delay(31)),

    static_cast<uint16_t>(
        pio_encode_set(pio_pins, 1) |
        pio_encode_delay(15)),

    static_cast<uint16_t>(
        pio_encode_in(pio_pins, 1)),

    static_cast<uint16_t>(
        pio_encode_push(false, true)),

    static_cast<uint16_t>(
        pio_encode_nop() |
        pio_encode_delay(15))
};

const pio_program_t strobeReadProgram =
{
    .instructions = strobeReadInstructions,
    .length = 6,
    .origin = -1
};

} // namespace

PicoC2Transport::PicoC2Transport(std::uint8_t c2ckPin,
                                 std::uint8_t c2dPin)
    : c2ckPin_(c2ckPin),
      c2dPin_(c2dPin)
{
}


void PicoC2Transport::begin()
{
    pinMode(c2ckPin_, OUTPUT);
    digitalWrite(c2ckPin_, HIGH);

    pinMode(c2dPin_, INPUT);

    initializePio();
}


void PicoC2Transport::initializePio()
{
    strobeOffset_ =
        pio_add_program(pio_, &strobeProgram);

    strobeReadOffset_ =
        pio_add_program(pio_, &strobeReadProgram);

    pio_gpio_init(pio_, c2ckPin_);
    pio_gpio_init(pio_, c2dPin_);

    const float divider =
        static_cast<float>(clock_get_hz(clk_sys)) /
        PIO_FREQUENCY;

    //
    // Plain strobe state machine
    //
    pio_sm_config strobeConfig =
        pio_get_default_sm_config();

    sm_config_set_wrap(
        &strobeConfig,
        strobeOffset_,
        strobeOffset_ + strobeProgram.length - 1);

    sm_config_set_set_pins(
        &strobeConfig,
        c2ckPin_,
        1);

    sm_config_set_clkdiv(
        &strobeConfig,
        divider);

    pio_sm_init(
        pio_,
        smStrobe_,
        strobeOffset_,
        &strobeConfig);

    pio_sm_set_consecutive_pindirs(
        pio_,
        smStrobe_,
        c2ckPin_,
        1,
        true);

    pio_sm_set_pins_with_mask(
        pio_,
        smStrobe_,
        1u << c2ckPin_,
        1u << c2ckPin_);

    //
    // Strobe-and-read state machine
    //
    pio_sm_config readConfig =
        pio_get_default_sm_config();

    sm_config_set_wrap(
        &readConfig,
        strobeReadOffset_,
        strobeReadOffset_ + strobeReadProgram.length - 1);

    sm_config_set_set_pins(
        &readConfig,
        c2ckPin_,
        1);

    sm_config_set_in_pins(
        &readConfig,
        c2dPin_);

    sm_config_set_clkdiv(
        &readConfig,
        divider);

    pio_sm_init(
        pio_,
        smRead_,
        strobeReadOffset_,
        &readConfig);

    pio_sm_set_consecutive_pindirs(
        pio_,
        smRead_,
        c2ckPin_,
        1,
        true);

    pio_sm_set_pins_with_mask(
        pio_,
        smRead_,
        1u << c2ckPin_,
        1u << c2ckPin_);

    pio_sm_set_enabled(
        pio_,
        smStrobe_,
        true);

    pio_sm_set_enabled(
        pio_,
        smRead_,
        true);
}

void PicoC2Transport::strobe()
{
    pio_sm_put_blocking(
        pio_,
        smStrobe_,
        0);

    (void)pio_sm_get_blocking(
        pio_,
        smStrobe_);
}


std::uint8_t PicoC2Transport::strobeAndRead()
{
    pio_sm_put_blocking(
        pio_,
        smRead_,
        0);

    const std::uint32_t result =
        pio_sm_get_blocking(
            pio_,
            smRead_);

    return static_cast<std::uint8_t>(
        result & 0x01);
}

void PicoC2Transport::reset()
{
    // Neither PIO state machine may drive C2CK while SIO generates reset.
    pio_sm_set_enabled(pio_, smStrobe_, false);
    pio_sm_set_enabled(pio_, smRead_, false);

    // Temporarily give C2CK back to normal GPIO control.
    gpio_set_function(c2ckPin_, GPIO_FUNC_SIO);
    gpio_set_dir(c2ckPin_, GPIO_OUT);

    // Match the deliberately generous reset timing used by the
    // original MicroPython implementation.
    gpio_put(c2ckPin_, 1);
    delay(10);

    gpio_put(c2ckPin_, 0);
    delay(100);

    gpio_put(c2ckPin_, 1);
    delay(100);

    // Return C2CK to PIO control.
    gpio_set_function(c2ckPin_, GPIO_FUNC_PIO0);

    pio_sm_set_enabled(pio_, smStrobe_, true);
    pio_sm_set_enabled(pio_, smRead_, true);
}

void PicoC2Transport::addressWrite(std::uint8_t address)
{
    // Release C2D before beginning the transaction.
    gpio_set_dir(c2dPin_, GPIO_IN);

    // START
    strobe();

    // INS = 0b11, transmitted LSB first.
    gpio_put(c2dPin_, 1);
    gpio_set_dir(c2dPin_, GPIO_OUT);

    strobe();
    strobe();

    // Address byte, LSB first.
    for (std::uint8_t bit = 0; bit < 8; ++bit)
    {
        gpio_put(
            c2dPin_,
            (address >> bit) & 0x01);

        strobe();
    }

    // Release C2D before STOP.
    gpio_set_dir(c2dPin_, GPIO_IN);

    // STOP
    strobe();

    delayMicroseconds(1000);
}

std::uint8_t PicoC2Transport::addressRead()
{
    return 0;
}

void PicoC2Transport::dataWrite(std::uint8_t value)
{
    (void)value;
}

std::uint8_t PicoC2Transport::dataRead()
{
    return 0;
}