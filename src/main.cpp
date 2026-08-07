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

    while (!Serial)
    {
        delay(10);
    }

    commandServer.begin();
}

void loop()
{
    commandServer.service();
}