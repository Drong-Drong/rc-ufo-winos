#include "ufo_input_windows.h"
#include <conio.h>      // _kbhit(), _getwch()

KeyToken read_key()
{
    if (!_kbhit())
        return KeyToken::None;

    wint_t ch = _getwch();

    if (ch == 0x00 || ch == 0xE0) {
        wint_t ext = _getwch();
        switch (ext) {
        case 'H': return KeyToken::Up;
        case 'P': return KeyToken::Down;
        case 'K': return KeyToken::Left;
        case 'M': return KeyToken::Right;
        default:  return KeyToken::None;
        }
    }

    // ESC
    if (ch == 0x1B)
        return KeyToken::Quit;

    switch (towlower(static_cast<wint_t>(ch))) {
    case 'q': return KeyToken::Quit;
    case 'w': return KeyToken::W;
    case 'a': return KeyToken::A;
    case 's': return KeyToken::S;
    case 'd': return KeyToken::D;
    case 'e': return KeyToken::E;
    case 'r': return KeyToken::R;
    }
    return KeyToken::None;
}