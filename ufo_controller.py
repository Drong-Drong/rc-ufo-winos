from __future__ import annotations

import socket
import sys
import time

from ufo_config import Args, parse_args
from ufo_input_windows import read_key
from ufo_protocol import (
    KEEPALIVE_0101,
    axis_to_extreme,
    build_analog_with_flags,
    clamp_u8,
)


def send_takeoff_burst(
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
                0x01,
            )
            sock.sendto(pkt, dst)
            next_takeoff += takeoff_period
        else:
            time.sleep(max(0.0, min(0.01, next_takeoff - now)))


def run(args: Args) -> int:
    if sys.platform != "win32":
        raise SystemExit("send_ufo_keyboard.py currently supports Windows console only.")

    hold_s = args.hold_ms / 1000.0
    dst = (args.dst_ip, args.dst_port)

    if not args.quiet:
        print(f"dst={args.dst_ip}:{args.dst_port}")
        print(f"bind={args.bind_ip}:{args.bind_port}")
        print("controls: W/S c1, A/D c2, arrows thr/c4, E takeoff, R reset, Q/ESC quit")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((args.bind_ip, args.bind_port))

    if not args.quiet:
        print("auto-takeoff: sending fastFly flag for 1.0s")
    send_takeoff_burst(sock, dst, args, duration_s=1.0)

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

            while True:
                k = read_key()
                if k is None:
                    break
                if k == "quit":
                    return 0
                if k == "e":
                    if not args.quiet:
                        print("takeoff: sending fastFly burst for 1.0s")
                    send_takeoff_burst(sock, dst, args, duration_s=1.0)
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

                c1 = axis_to_extreme(w_on, s_on, args.c1_center)
                c2 = axis_to_extreme(d_on, a_on, args.c2_center)
                c4 = axis_to_extreme(right_on, left_on, args.c4_center)

                if w_on:
                    thr = 0xFF
                else:
                    thr = axis_to_extreme(up_on, down_on, args.thr_base)

                pkt = build_analog_with_flags(
                    clamp_u8(c1),
                    clamp_u8(c2),
                    clamp_u8(thr),
                    clamp_u8(c4),
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


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    return run(args)
