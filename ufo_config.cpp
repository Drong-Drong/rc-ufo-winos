#include "ufo_config.h"
#include "ufo_protocol.h"
#include <stdexcept>
#include <cstring>
#include <cstdlib>

static const char* HELP =
"Interactive keyboard controller for UFO-03 over UDP/7099 (Windows console).\n\n"
"Controls\n"
"  W/S        : c1 axis (+/-)\n"
"  A/D        : c2 axis (-/+)\n"
"  Arrow Up/Down  : throttle (+/- from base)\n"
"  Arrow Left/Right : c4 axis (-/+)\n"
"  E          : takeoff burst (fastFly ~1s)\n"
"  R          : reset channels to neutral\n"
"  Q / ESC    : quit\n";

static bool arg_eq(const char* a, const char* b) { return strcmp(a, b) == 0; }

UfoArgs parse_args(int argc, char* argv[])
{
    UfoArgs a;
    for (int i = 1; i < argc; ++i) {
        if (arg_eq(argv[i], "--help") || arg_eq(argv[i], "-h")) {
            puts(HELP); exit(0);
        }
#define NEXT (i + 1 < argc ? argv[++i] : (throw std::invalid_argument("missing value"), ""))
        else if (arg_eq(argv[i], "--dst-ip"))       a.dst_ip       = NEXT;
        else if (arg_eq(argv[i], "--dst-port"))     a.dst_port     = atoi(NEXT);
        else if (arg_eq(argv[i], "--bind-ip"))      a.bind_ip      = NEXT;
        else if (arg_eq(argv[i], "--bind-port"))    a.bind_port    = atoi(NEXT);
        else if (arg_eq(argv[i], "--rate-hz"))      a.rate_hz      = atof(NEXT);
        else if (arg_eq(argv[i], "--send-keepalive")) a.send_keepalive = true;
        else if (arg_eq(argv[i], "--keepalive-hz")) a.keepalive_hz = atof(NEXT);
        else if (arg_eq(argv[i], "--hold-ms"))      a.hold_ms      = atoi(NEXT);
        else if (arg_eq(argv[i], "--c1-center"))    a.c1_center    = strtol(NEXT, nullptr, 0);
        else if (arg_eq(argv[i], "--c2-center"))    a.c2_center    = strtol(NEXT, nullptr, 0);
        else if (arg_eq(argv[i], "--c4-center"))    a.c4_center    = strtol(NEXT, nullptr, 0);
        else if (arg_eq(argv[i], "--thr-base"))     a.thr_base     = strtol(NEXT, nullptr, 0);
        else if (arg_eq(argv[i], "--stick-delta"))  a.stick_delta  = atoi(NEXT);
        else if (arg_eq(argv[i], "--yaw-delta"))    a.yaw_delta    = atoi(NEXT);
        else if (arg_eq(argv[i], "--thr-delta"))    a.thr_delta    = atoi(NEXT);
        else if (arg_eq(argv[i], "--quiet"))        a.quiet        = true;
#undef NEXT
    }

    if (a.rate_hz     <= 0) throw std::invalid_argument("--rate-hz must be > 0");
    if (a.keepalive_hz<= 0) throw std::invalid_argument("--keepalive-hz must be > 0");
    if (a.hold_ms     <= 0) throw std::invalid_argument("--hold-ms must be > 0");

    // 범위 검사
    u8(a.c1_center); u8(a.c2_center);
    u8(a.c4_center); u8(a.thr_base);

    return a;
}