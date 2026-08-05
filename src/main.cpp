#include "C2Programmer.h"
#include "ConsoleC2Transport.h"

#include <Arduino.h>

namespace
{
ConsoleC2Transport transport;
C2Programmer programmer(transport);
}

void setup()
{
    Serial.begin(115200);

    while (!Serial)
    {
        delay(10);
    }

    Serial.println();
    Serial.println("C2 Programmer");

    if (!programmer.identifyTarget())
    {
        Serial.println(
            "No further target operations are permitted."
        );

        return;
    }

    programmer.printTargetSummary();
}

void loop()
{
}