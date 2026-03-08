#pragma once
#include <cstdint>
#include <array>
#include <stdexcept>
#include <string>

inline constexpr uint8_t KEEPALIVE_0101[] = { 0x01, 0x01 };
inline constexpr size_t  KEEPALIVE_0101_LEN = 2;

inline uint8_t u8(int x) {
    if (x < 0 || x > 255)
        throw std::out_of_range("value out of range 0..255: " + std::to_string(x));
    return static_cast<uint8_t>(x);
}

inline uint8_t clamp_u8(int x) {
    if (x < 0)   return 0;
    if (x > 255) return 255;
    return static_cast<uint8_t>(x);
}

uint8_t axis_to_extreme(bool pos_on, bool neg_on, int center);

std::array<uint8_t, 9> build_analog_with_flags(
    uint8_t c1, uint8_t c2, uint8_t thr, uint8_t c4, uint8_t flags = 0x00);