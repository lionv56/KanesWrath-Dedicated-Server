#pragma once
#include <cstdint>
namespace kwds_route {
constexpr unsigned char AsciiLower(unsigned char c) { return c >= 'A' && c <= 'Z' ? static_cast<unsigned char>(c + ('a'-'A')) : c; }
constexpr bool IsBootstrapDnsName(const char* hostname) {
    if (!hostname) return false;
    const char* expected="servserv.generals.ea.com";
    unsigned int i=0;
    for (;expected[i];++i) if (AsciiLower(static_cast<unsigned char>(hostname[i])) != static_cast<unsigned char>(expected[i])) return false;
    return hostname[i]=='\0';
}
constexpr bool IsBootstrapSocketTarget(std::uint32_t hostAddress, unsigned short port, bool localMode) {
    return port==80 && (hostAddress==0xC33CA63Du || (localMode && hostAddress==0x7F000001u));
}
}
