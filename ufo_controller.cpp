#include "ufo_controller.h"
#include "ufo_config.h"
#include "ufo_input_windows.h"
#include "ufo_protocol.h"

#define NOMINMAX
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <algorithm>
#include <cstdio>
#include <chrono>
#include <thread>
#include <unordered_map>
#include <string>
#include <stdexcept>

#pragma comment(lib, "Ws2_32.lib")

using Clock    = std::chrono::steady_clock;
using TimePoint= Clock::time_point;
using Dur      = std::chrono::duration<double>;

static double now_s() {
    static auto t0 = Clock::now();
    return Dur(Clock::now() - t0).count();
}

static void sleep_s(double s) {
    if (s > 0.0)
        std::this_thread::sleep_for(
            std::chrono::microseconds(static_cast<long long>(s * 1e6)));
}

// UDP 전송 헬퍼
static void udp_send(SOCKET sock, const sockaddr_in& dst,
                     const uint8_t* data, int len)
{
    sendto(sock, reinterpret_cast<const char*>(data), len, 0,
           reinterpret_cast<const sockaddr*>(&dst), sizeof(dst));
}

static void send_takeoff_burst(SOCKET sock, const sockaddr_in& dst,
                               const UfoArgs& args, double duration_s = 1.0)
{
    double end      = now_s() + duration_s;
    double period   = 1.0 / args.rate_hz;
    double next_pkt = now_s();

    while (true) {
        double n = now_s();
        if (n >= end) break;
        if (n >= next_pkt) {
            auto pkt = build_analog_with_flags(
                static_cast<uint8_t>(args.c1_center),
                static_cast<uint8_t>(args.c2_center),
                static_cast<uint8_t>(args.thr_base),
                static_cast<uint8_t>(args.c4_center),
                0x01);
            udp_send(sock, dst, pkt.data(), static_cast<int>(pkt.size()));
            next_pkt += period;
        } else {
            sleep_s(std::min(0.01, next_pkt - n));
        }
    }
}

int run(const UfoArgs& args)
{
    // Winsock 초기화
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0)
        throw std::runtime_error("WSAStartup failed");

    SOCKET sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock == INVALID_SOCKET) {
        WSACleanup();
        throw std::runtime_error("socket() failed");
    }

    // SO_REUSEADDR
    int reuse = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR,
               reinterpret_cast<const char*>(&reuse), sizeof(reuse));

    // 바인드
    sockaddr_in bind_addr{};
    bind_addr.sin_family = AF_INET;
    bind_addr.sin_port   = htons(static_cast<u_short>(args.bind_port));
    inet_pton(AF_INET, args.bind_ip.c_str(), &bind_addr.sin_addr);
    if (bind(sock, reinterpret_cast<sockaddr*>(&bind_addr), sizeof(bind_addr)) != 0) {
        closesocket(sock); WSACleanup();
        throw std::runtime_error("bind() failed");
    }

    // 목적지
    sockaddr_in dst{};
    dst.sin_family = AF_INET;
    dst.sin_port   = htons(static_cast<u_short>(args.dst_port));
    inet_pton(AF_INET, args.dst_ip.c_str(), &dst.sin_addr);

    if (!args.quiet)
        printf("dst=%s:%d  bind=%s:%d\n"
               "controls: W/S c1, A/D c2, arrows thr/c4, E takeoff, R reset, Q/ESC quit\n",
               args.dst_ip.c_str(), args.dst_port,
               args.bind_ip.c_str(), args.bind_port);

    // 자동 테이크오프
    if (!args.quiet) printf("auto-takeoff: sending fastFly flag for 1.0s\n");
    send_takeoff_burst(sock, dst, args, 1.0);

    // 키 타임스탬프 (마지막으로 눌린 시각)
    const double NEG_INF = -1e9;
    std::unordered_map<int, double> t_last;
    auto KE = [](KeyToken k) { return static_cast<int>(k); };
    for (auto k : { KeyToken::W, KeyToken::A, KeyToken::S, KeyToken::D,
                    KeyToken::Up, KeyToken::Down, KeyToken::Left, KeyToken::Right })
        t_last[KE(k)] = NEG_INF;

    double hold_s      = args.hold_ms / 1000.0;
    double analog_period = 1.0 / args.rate_hz;
    double ka_period   = args.send_keepalive ? 1.0 / args.keepalive_hz : -1.0;

    double next_analog = now_s();
    double next_ka     = (ka_period > 0) ? now_s() : 1e18;

    int ret = 0;
    __try {
        while (true) {
            double n = now_s();

            // 키 폴링
            while (true) {
                KeyToken k = read_key();
                if (k == KeyToken::None) break;
                if (k == KeyToken::Quit) { ret = 0; goto done; }
                if (k == KeyToken::E) {
                    if (!args.quiet) printf("takeoff: sending fastFly burst\n");
                    send_takeoff_burst(sock, dst, args, 1.0);
                    continue;
                }
                if (k == KeyToken::R) {
                    for (auto& kv : t_last) kv.second = NEG_INF;
                    continue;
                }
                t_last[KE(k)] = n;
            }

            bool did = false;

            if (n >= next_analog) {
                auto is_on = [&](KeyToken k) {
                    auto it = t_last.find(KE(k));
                    return it != t_last.end() && (n - it->second) <= hold_s;
                };

                bool w_on    = is_on(KeyToken::W);
                bool s_on    = is_on(KeyToken::S);
                bool a_on    = is_on(KeyToken::A);
                bool d_on    = is_on(KeyToken::D);
                bool up_on   = is_on(KeyToken::Up);
                bool down_on = is_on(KeyToken::Down);
                bool left_on = is_on(KeyToken::Left);
                bool right_on= is_on(KeyToken::Right);

                uint8_t c1  = clamp_u8(axis_to_extreme(w_on,     s_on,    args.c1_center));
                uint8_t c2  = clamp_u8(axis_to_extreme(d_on,     a_on,    args.c2_center));
                uint8_t c4  = clamp_u8(axis_to_extreme(right_on, left_on, args.c4_center));
                uint8_t thr;
                if (w_on) thr = 0xFF;
                else      thr = clamp_u8(axis_to_extreme(up_on, down_on, args.thr_base));

                auto pkt = build_analog_with_flags(c1, c2, thr, c4, 0x00);
                udp_send(sock, dst, pkt.data(), static_cast<int>(pkt.size()));
                next_analog += analog_period;
                did = true;
            }

            if (ka_period > 0 && n >= next_ka) {
                udp_send(sock, dst, KEEPALIVE_0101, KEEPALIVE_0101_LEN);
                next_ka += ka_period;
                did = true;
            }

            if (!did) {
                double t_next = std::min(next_analog, next_ka);
                sleep_s(std::min(0.01, t_next - n));
            }
        }
    }
    __finally {
        closesocket(sock);
        WSACleanup();
    }

done:
    closesocket(sock);
    WSACleanup();
    return ret;
}

int ufo_main(int argc, char* argv[])
{
    try {
        UfoArgs args = parse_args(argc, argv);
        return run(args);
    } catch (const std::exception& e) {
        fprintf(stderr, "Error: %s\n", e.what());
        return 1;
    }
}