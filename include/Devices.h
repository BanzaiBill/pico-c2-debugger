#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string_view>

struct DeviceDescriptor
{
    std::string_view name;
    std::uint8_t deviceId;
    std::uint8_t fpdatAddress;
    std::size_t flashPageSize;
    std::optional<std::size_t> flashSize;
};

inline constexpr std::uint8_t C2_DEVICE_ID_ADDRESS = 0x00;
inline constexpr std::uint8_t C2_DERIVATIVE_ID_ADDRESS = 0x01;

const DeviceDescriptor* findDevice(std::uint8_t deviceId);