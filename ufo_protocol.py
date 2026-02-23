from __future__ import annotations

# Keepalive packet observed in controller traffic.
KEEPALIVE_0101 = bytes([0x01, 0x01])


def u8(x: int) -> int:
    if not (0 <= x <= 255):
        raise ValueError(f"value out of range 0..255: {x}")
    return x


def clamp_u8(x: int) -> int:
    return 0 if x < 0 else (255 if x > 255 else x)


def axis_to_extreme(pos_on: bool, neg_on: bool, center: int) -> int:
    """
    Convert digital key states to axis byte.
      - pos only -> 0xFF
      - neg only -> 0x00
      - both/none -> center
    """
    center = u8(center)
    if pos_on and not neg_on:
        return 0xFF
    if neg_on and not pos_on:
        return 0x00
    return center


def build_analog_with_flags(c1: int, c2: int, thr: int, c4: int, flags: int = 0) -> bytes:
    """
    Build 9-byte control packet:
      03 66 c1 c2 thr c4 flags chk 99

    Checksum:
      chk = c1 ^ c2 ^ thr ^ c4 ^ flags
    """
    c1 = u8(c1)
    c2 = u8(c2)
    thr = u8(thr)
    c4 = u8(c4)
    flags = u8(flags)
    chk = (c1 ^ c2 ^ thr ^ c4 ^ flags) & 0xFF
    return bytes([0x03, 0x66, c1, c2, thr, c4, flags, chk, 0x99])
