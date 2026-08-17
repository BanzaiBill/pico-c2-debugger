#include "AdapterCommandServer.h"

#include <cerrno>
#include <cstdlib>
#include <cstring>

AdapterCommandServer::AdapterCommandServer(
    Stream& stream,
    IC2Transport& transport)
    : stream_(stream),
      transport_(transport)
{
}

void AdapterCommandServer::sendInfo()
{
    stream_.print("INFO C2ADAPTER 0.1 ");
    stream_.println(transport_.name());
}

void AdapterCommandServer::begin()
{
    sendInfo();
}

void AdapterCommandServer::service()
{
    while (stream_.available() > 0)
    {
        const char ch =
            static_cast<char>(stream_.read());

        if (ch == '\r')
        {
            continue;
        }

        if (ch == '\n')
        {
            commandBuffer_[commandLength_] = '\0';

            if (commandLength_ > 0)
            {
                processCommand(commandBuffer_);
            }

            commandLength_ = 0;
            continue;
        }

        if (commandLength_ <
            COMMAND_BUFFER_SIZE - 1)
        {
            commandBuffer_[commandLength_++] = ch;
        }
        else
        {
            commandLength_ = 0;
            sendError("COMMAND_TOO_LONG");
        }
    }
}

void AdapterCommandServer::processCommand(
    char* commandLine)
{
    char* command =
        std::strtok(commandLine, " \t");

    if (command == nullptr)
    {
        return;
    }

    if (std::strcmp(command, "GET_INFO") == 0)
    {
        handleGetInfo();
        return;
    }

    if (std::strcmp(command, "RESET") == 0)
    {
        handleReset();
        return;
    }

    if (std::strcmp(command, "AR_WRITE") == 0)
    {
        handleAddressWrite(
            std::strtok(nullptr, " \t"));

        return;
    }

    if (std::strcmp(command, "AR_READ") == 0)
    {
        handleAddressRead();
        return;
    }

    if (std::strcmp(command, "DR_WRITE") == 0)
    {
        handleDataWrite(
            std::strtok(nullptr, " \t"));

        return;
    }

    if (std::strcmp(command, "DR_READ") == 0)
    {
        handleDataRead();
        return;
    }

    sendError("UNKNOWN_COMMAND");
}

void AdapterCommandServer::handleGetInfo()
{
    sendInfo();
}

void AdapterCommandServer::handleReset()
{
    transport_.reset();
    sendOk();
}

void AdapterCommandServer::handleAddressWrite(
    char* argument)
{
    std::uint8_t value = 0;

    if (!parseByte(argument, value))
    {
        sendError("BAD_ARGUMENT");
        return;
    }

    transport_.addressWrite(value);
    sendOk();
}

void AdapterCommandServer::handleAddressRead()
{
    sendData(
        transport_.addressRead());
}

void AdapterCommandServer::handleDataWrite(
    char* argument)
{
    std::uint8_t value = 0;

    if (!parseByte(argument, value))
    {
        sendError("BAD_ARGUMENT");
        return;
    }

    transport_.dataWrite(value);
    sendOk();
}

void AdapterCommandServer::handleDataRead()
{
    sendData(
        transport_.dataRead());
}

bool AdapterCommandServer::parseByte(
    const char* text,
    std::uint8_t& value)
{
    if (text == nullptr)
    {
        return false;
    }

    errno = 0;

    char* end = nullptr;

    const unsigned long parsed =
        std::strtoul(text, &end, 0);

    if (errno != 0)
    {
        return false;
    }

    if (end == text || *end != '\0')
    {
        return false;
    }

    if (parsed > 0xFF)
    {
        return false;
    }

    value =
        static_cast<std::uint8_t>(parsed);

    return true;
}

void AdapterCommandServer::sendOk()
{
    stream_.println("OK");
}

void AdapterCommandServer::sendData(
    const std::uint8_t value)
{
    stream_.print("DATA 0x");

    if (value < 0x10)
    {
        stream_.print('0');
    }

    stream_.println(value, HEX);
}

void AdapterCommandServer::sendError(
    const char* error)
{
    stream_.print("ERROR ");
    stream_.println(error);
}