#pragma once
#include <string>

struct UfoArgs {
    std::string dst_ip       = "192.168.1.1";
    int         dst_port     = 7099;
    std::string bind_ip      = "0.0.0.0";
    int         bind_port    = 0;
    double      rate_hz      = 20.0;
    bool        send_keepalive = false;
    double      keepalive_hz = 1.0;
    int         hold_ms      = 180;
    int         c1_center    = 0x80;
    int         c2_center    = 0x80;
    int         c4_center    = 0x80;
    int         thr_base     = 0x00;
    int         stick_delta  = 35;
    int         yaw_delta    = 35;
    int         thr_delta    = 35;
    bool        quiet        = false;
};

// 파싱 실패 시 std::invalid_argument 또는 std::runtime_error
UfoArgs parse_args(int argc, char* argv[]);