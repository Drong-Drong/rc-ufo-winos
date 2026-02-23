from __future__ import annotations

import sys

if sys.platform == "win32":
    import msvcrt
else:
    msvcrt = None


def read_key() -> str | None:
    """Return normalized key tokens: w/a/s/d/up/down/left/right/e/r/quit."""
    if msvcrt is None:
        raise RuntimeError("Keyboard polling is supported on Windows console only.")

    if not msvcrt.kbhit():
        return None

    ch = msvcrt.getwch()
    if ch in ("\x00", "\xe0"):
        ext = msvcrt.getwch()
        return {
            "H": "up",
            "P": "down",
            "K": "left",
            "M": "right",
        }.get(ext)

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
