#include "ConsoleC2Transport.h"

#include <Arduino.h>
#include <cstdlib>

void ConsoleC2Transport::reset()
{
    selectedAddress_ = 0x00;
    Serial.println("[SIM] C2 reset");
}

void ConsoleC2Transport::addressWrite(
    const std::uint8_t address)
{
    selectedAddress_ = address;

    Serial.print("[SIM] C2 address selected: 0x");
    Serial.println(address, HEX);
}

std::uint8_t ConsoleC2Transport::addressRead()
{
    return selectedAddress_;
}

void ConsoleC2Transport::dataWrite(
    const std::uint8_t value)
{
    Serial.print("[SIM] C2 data write: 0x");
    Serial.println(value, HEX);
}

std::uint8_t ConsoleC2Transport::dataRead()
{
    switch (selectedAddress_)
    {
        case 0x00:
            return promptForByte(
                "Enter simulated Device ID");

        case 0x01:
            return promptForByte(
                "Enter simulated Derivative ID");

        default:
            Serial.println(
                "No simulated value exists for this address");

            return 0x00;
    }
}

std::uint8_t ConsoleC2Transport::promptForByte(
    const char* prompt)
{
    for (;;)
    {
        Serial.print(prompt);
        Serial.print(" [0x00-0xFF]: ");

        while (!Serial.available())
        {
            delay(10);
        }

        String text = Serial.readStringUntil('\n');
        text.trim();

        char* end = nullptr;
        const unsigned long value =
            std::strtoul(text.c_str(), &end, 0);

        if (end != text.c_str() &&
            *end == '\0' &&
            value <= 0xFF)
        {
            return static_cast<std::uint8_t>(value);
        }

        Serial.println(
            "Invalid value. Examples: 0x16 or 22");
    }
}