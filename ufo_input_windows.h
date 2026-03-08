#pragma once
#include <string>

enum class KeyToken {
    None,
    W, A, S, D,
    Up, Down, Left, Right,
    E, R,
    Quit
};

KeyToken read_key();