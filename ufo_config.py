from __future__ import annotations

import argparse
from dataclasses import dataclass

from ufo_protocol import u8


HELP_TEXT = """Interactive keyboard controller for UFO-03 over UDP/7099 (Windows console).

Controls
  - W / S: c1 axis (+/-)
  - A / D: c2 axis (-/+)
  - Arrow Up / Down: throttle (+/- from base throttle)
  - Arrow Left / Right: c4 axis (-/+)
  - E: send takeoff burst (fastFly flag for ~1s)
  - R: reset channels to neutral
  - Q or ESC: quit
"""


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


def parse_args(argv: list[str]) -> Args:
    p = argparse.ArgumentParser(
        description=HELP_TEXT,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
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
        u8(int(v))

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
