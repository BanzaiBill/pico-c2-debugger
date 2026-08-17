#include <Arduino.h>

#include "AdapterCommandServer.h"

#define USE_PICO_C2_TRANSPORT 1

#if USE_PICO_C2_TRANSPORT
#include "PicoC2Transport.h"
#else
#include "DummyC2Transport.h"
#endif

namespace
{
#if USE_PICO_C2_TRANSPORT

constexpr std::uint8_t C2CK_PIN = 4;
constexpr std::uint8_t C2D_PIN  = 5;

PicoC2Transport transport(C2CK_PIN, C2D_PIN);

#else

DummyC2Transport transport;

#endif

AdapterCommandServer commandServer(Serial, transport);
}

void setup()
{
    Serial.begin(115200);

#if USE_PICO_C2_TRANSPORT
    transport.begin();
#endif

    delay(2000);

    Serial.println();
    Serial.println("RP2040 C2 Adapter starting...");

    commandServer.begin();
}

void loop()
{
    commandServer.service();
}