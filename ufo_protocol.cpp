#include "ufo_protocol.h"

uint8_t axis_to_extreme(bool pos_on, bool neg_on, int center)
{
    uint8_t c = u8(center);
    if (pos_on && !neg_on) return 0xFF;
    if (neg_on && !pos_on) return 0x00;
    return c;
}

std::array<uint8_t, 9> build_analog_with_flags(
    uint8_t c1, uint8_t c2, uint8_t thr, uint8_t c4, uint8_t flags)
{
    uint8_t chk = static_cast<uint8_t>((c1 ^ c2 ^ thr ^ c4 ^ flags) & 0xFF);
    return { 0x03, 0x66, c1, c2, thr, c4, flags, chk, 0x99 };
}