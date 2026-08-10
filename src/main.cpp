#include <Arduino.h>

#include "AdapterCommandServer.h"
#include "DummyC2Transport.h"

namespace
{
DummyC2Transport transport;

AdapterCommandServer commandServer(
    Serial,
    transport);
}

void setup()
{
    Serial.begin(115200);

    delay(2000);

    Serial.println();
    Serial.println("RP2040 C2 Adapter starting...");

    commandServer.begin();
}

void loop()
{
    commandServer.service();
}