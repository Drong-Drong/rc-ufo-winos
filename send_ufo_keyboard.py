#!/usr/bin/env python3
"""
Interactive keyboard controller for UFO-03 over UDP/7099 (Windows console).

Controls
  - W / S: c1 axis (+/-)
  - A / D: c2 axis (-/+)
  - Arrow Up / Down: throttle (+/- from base throttle)
  - Arrow Left / Right: c4 axis (-/+)
  - E: send takeoff burst (fastFly flag for ~1s)
  - R: reset channels to neutral
  - Q or ESC: quit

Notes
  - This script depends on Windows `msvcrt` key polling.
  - It reuses the observed 9-byte analog format:
      03 66 c1 c2 thr c4 00 chk 99
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from dataclasses import dataclass

if sys.platform != "win32":
    raise SystemExit("send_ufo_keyboard.py currently supports Windows console only.")

import msvcrt

from send_ufo_control import KEEPALIVE_0101


def _u8(x: int) -> int:
    if not (0 <= x <= 255):
        raise ValueError(f"value out of range 0..255: {x}")
    return x


@dataclass(frozen=True)
class Args:
    dst_ip: str
    dst_port: int
    bind_ip: str
    bind_port: int
    rate_hz: float
    send_keepalive: bool
    keepalive_hz: float
    hold_ms: int
    c1_center: int
    c2_center: int
    c4_center: int
    thr_base: int
    stick_delta: int
    yaw_delta: int
    thr_delta: int
    quiet: bool


def build_analog_with_flags(c1: int, c2: int, thr: int, c4: int, flags: int = 0) -> bytes:
    """
    Build 9-byte control packet with explicit flags byte:
      03 66 c1 c2 thr c4 flags chk 99

    For TC-like format, checksum includes flags:
      chk = c1 ^ c2 ^ thr ^ c4 ^ flags
    """
    c1 = _u8(c1)
    c2 = _u8(c2)
    thr = _u8(thr)
    c4 = _u8(c4)
    flags = _u8(flags)
    chk = (c1 ^ c2 ^ thr ^ c4 ^ flags) & 0xFF
    return bytes([0x03, 0x66, c1, c2, thr, c4, flags, chk, 0x99])


def parse_args(argv: list[str]) -> Args:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dst-ip", default="192.168.1.1")
    p.add_argument("--dst-port", type=int, default=7099)
    p.add_argument("--bind-ip", default="0.0.0.0")
    p.add_argument("--bind-port", type=int, default=0)
    p.add_argument("--rate-hz", type=float, default=20.0, help="Control packet rate")
    p.add_argument("--send-keepalive", action="store_true")
    p.add_argument("--keepalive-hz", type=float, default=1.0)
    p.add_argument(
        "--hold-ms",
        type=int,
        default=180,
        help="How long a key remains active without repeat events",
    )
    p.add_argument("--c1-center", type=int, default=0x80)
    p.add_argument("--c2-center", type=int, default=0x80)
    p.add_argument("--c4-center", type=int, default=0x80)
    p.add_argument("--thr-base", type=int, default=0x00)
    p.add_argument("--stick-delta", type=int, default=35, help="WASD axis offset")
    p.add_argument("--yaw-delta", type=int, default=35, help="Arrow left/right offset")
    p.add_argument("--thr-delta", type=int, default=35, help="Arrow up/down offset")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args(argv)

    if a.rate_hz <= 0:
        raise SystemExit("--rate-hz must be > 0")
    if a.keepalive_hz <= 0:
        raise SystemExit("--keepalive-hz must be > 0")
    if a.hold_ms <= 0:
        raise SystemExit("--hold-ms must be > 0")

    for v in (a.c1_center, a.c2_center, a.c4_center, a.thr_base):
        _u8(int(v))

    return Args(
        dst_ip=a.dst_ip,
        dst_port=int(a.dst_port),
        bind_ip=a.bind_ip,
        bind_port=int(a.bind_port),
        rate_hz=float(a.rate_hz),
        send_keepalive=bool(a.send_keepalive),
        keepalive_hz=float(a.keepalive_hz),
        hold_ms=int(a.hold_ms),
        c1_center=int(a.c1_center),
        c2_center=int(a.c2_center),
        c4_center=int(a.c4_center),
        thr_base=int(a.thr_base),
        stick_delta=int(a.stick_delta),
        yaw_delta=int(a.yaw_delta),
        thr_delta=int(a.thr_delta),
        quiet=bool(a.quiet),
    )


def _clamp_u8(x: int) -> int:
    return 0 if x < 0 else (255 if x > 255 else x)


def _axis_to_extreme(pos_on: bool, neg_on: bool, center: int) -> int:
    """
    Convert digital key states to byte extremes.
      - pos only -> 0xFF
      - neg only -> 0x00
      - both/none -> center
    """
    if pos_on and not neg_on:
        return 0xFF
    if neg_on and not pos_on:
        return 0x00
    return center


def _send_takeoff_burst(
    sock: socket.socket,
    dst: tuple[str, int],
    args: Args,
    duration_s: float = 1.0,
) -> None:
    """Send fastFly flag packets for a short duration."""
    t_takeoff_end = time.monotonic() + duration_s
    takeoff_period = 1.0 / args.rate_hz
    next_takeoff = time.monotonic()
    while True:
        now = time.monotonic()
        if now >= t_takeoff_end:
            break
        if now >= next_takeoff:
            pkt = build_analog_with_flags(
                args.c1_center,
                args.c2_center,
                args.thr_base,
                args.c4_center,
                0x01,  # fastFly
            )
            sock.sendto(pkt, dst)
            next_takeoff += takeoff_period
        else:
            time.sleep(max(0.0, min(0.01, next_takeoff - now)))


def _read_key() -> str | None:
    """Return normalized key tokens: w/a/s/d/up/down/left/right/e/r/quit."""
    if not msvcrt.kbhit():
        return None

    ch = msvcrt.getwch()
    # Legacy Windows extended-key path.
    if ch in ("\x00", "\xe0"):
        ext = msvcrt.getwch()
        return {
            "H": "up",
            "P": "down",
            "K": "left",
            "M": "right",
        }.get(ext)

    # Some terminals emit ANSI escape sequences for arrows:
    #   ESC [ A/B/C/D   or   ESC O A/B/C/D
    # We handle that before treating ESC as quit.
    # Handle that before treating ESC as quit.
    if ch == "\x1b":
        if msvcrt.kbhit():
            ch2 = msvcrt.getwch()
            if ch2 in ("[", "O") and msvcrt.kbhit():
                ch3 = msvcrt.getwch()
                return {
                    "A": "up",
                    "B": "down",
                    "C": "right",
                    "D": "left",
                }.get(ch3)
        return "quit"

    # Some terminals can pass literal unicode arrows.
    if ch in ("↑", "↓", "←", "→"):
        return {
            "↑": "up",
            "↓": "down",
            "←": "left",
            "→": "right",
        }[ch]

    if ch in ("q", "Q"):
        return "quit"
    if ch in ("e", "E"):
        return "e"
    if ch in ("r", "R"):
        return "r"

    c = ch.lower()
    if c in ("w", "a", "s", "d"):
        return c
    return None


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    hold_s = args.hold_ms / 1000.0
    dst = (args.dst_ip, args.dst_port)

    if not args.quiet:
        print(f"dst={args.dst_ip}:{args.dst_port}")
        print(f"bind={args.bind_ip}:{args.bind_port}")
        print("controls: W/S c1, A/D c2, arrows thr/c4, E takeoff, R reset, Q/ESC quit")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((args.bind_ip, args.bind_port))

    # Auto takeoff sequence at startup:
    # send fastFly flag (0x01) for ~1 second, similar to app behavior where
    # takeoff button enables fast-fly briefly.
    if not args.quiet:
        print("auto-takeoff: sending fastFly flag for 1.0s")
    _send_takeoff_burst(sock, dst, args, duration_s=1.0)

    # Last observed key event timestamps. A key is treated as "active" for
    # hold_ms after each repeat event, which makes hold behavior workable in
    # a plain console without explicit key-up events.
    t_last = {
        "w": -1e9,
        "a": -1e9,
        "s": -1e9,
        "d": -1e9,
        "up": -1e9,
        "down": -1e9,
        "left": -1e9,
        "right": -1e9,
    }

    def is_on(name: str, now: float) -> bool:
        return (now - t_last[name]) <= hold_s

    analog_period = 1.0 / args.rate_hz
    ka_period = 1.0 / args.keepalive_hz if args.send_keepalive else None

    t0 = time.monotonic()
    next_analog = t0
    next_ka = t0 if ka_period is not None else None

    try:
        while True:
            now = time.monotonic()

            # Drain all pending key events first.
            while True:
                k = _read_key()
                if k is None:
                    break
                if k == "quit":
                    return 0
                if k == "e":
                    if not args.quiet:
                        print("takeoff: sending fastFly burst for 1.0s")
                    _send_takeoff_burst(sock, dst, args, duration_s=1.0)
                    continue
                if k == "r":
                    for key in t_last:
                        t_last[key] = -1e9
                    continue
                t_last[k] = now

            did = False
            if now >= next_analog:
                w_on = is_on("w", now)
                s_on = is_on("s", now)
                a_on = is_on("a", now)
                d_on = is_on("d", now)
                up_on = is_on("up", now)
                down_on = is_on("down", now)
                left_on = is_on("left", now)
                right_on = is_on("right", now)

                # Digital extreme mode (FF/00): each axis goes to max/min on key.
                c1 = _axis_to_extreme(w_on, s_on, args.c1_center)
                c2 = _axis_to_extreme(d_on, a_on, args.c2_center)
                c4 = _axis_to_extreme(right_on, left_on, args.c4_center)

                # Keep previous request: W also forces full throttle.
                if w_on:
                    thr = 0xFF
                else:
                    thr = _axis_to_extreme(up_on, down_on, args.thr_base)

                pkt = build_analog_with_flags(
                    _clamp_u8(c1),
                    _clamp_u8(c2),
                    _clamp_u8(thr),
                    _clamp_u8(c4),
                    0x00,
                )
                sock.sendto(pkt, dst)
                next_analog += analog_period
                did = True

            if next_ka is not None and now >= next_ka:
                sock.sendto(KEEPALIVE_0101, dst)
                next_ka += ka_period
                did = True

            if not did:
                t_next = next_analog if next_ka is None else min(next_analog, next_ka)
                time.sleep(max(0.0, min(0.01, t_next - now)))
    finally:
        sock.close()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
