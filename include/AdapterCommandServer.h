#pragma once

#include "IC2Transport.h"

#include <Arduino.h>

class AdapterCommandServer
{
public:
    AdapterCommandServer(
        Stream& stream,
        IC2Transport& transport);

    void begin();
    void service();

private:
    static constexpr const char* FIRMWARE_VERSION = "0.2";

    static constexpr std::size_t COMMAND_BUFFER_SIZE = 96;

    Stream& stream_;
    IC2Transport& transport_;

    char commandBuffer_[COMMAND_BUFFER_SIZE] {};
    std::size_t commandLength_ = 0;

    void processCommand(char* commandLine);
    void sendInfo();
    void handleGetInfo();
    void handleReset();

    void handleAddressWrite(char* argument);
    void handleAddressRead();

    void handleDataWrite(char* argument);
    void handleDataRead();

    static bool parseByte(
        const char* text,
        std::uint8_t& value);

    void sendOk();
    void sendData(std::uint8_t value);
    void sendError(const char* error);
};