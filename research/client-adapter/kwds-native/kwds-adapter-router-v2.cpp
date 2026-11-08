#define WIN32_LEAN_AND_MEAN
#define _WINSOCK_DEPRECATED_NO_WARNINGS

#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <psapi.h>
#include <cstdint>
#include "kwds-trust-policy.h"
#include "kwds-bootstrap-route.h"
#include <detours.h>

#include <cstdio>
#include <cstring>

#pragma comment(lib, "ws2_32.lib")
#pragma comment(lib, "Psapi.lib")

using ConnectFn = int (WSAAPI*)(SOCKET, const sockaddr*, int);
using DnsFn = hostent* (WSAAPI*)(const char*);

static ConnectFn RealConnect = nullptr;
static DnsFn RealDns = nullptr;

static volatile LONG RouteMode = 0;

static void WriteLog(const char* message)
{
    char temp[MAX_PATH] = {};
    char filename[MAX_PATH] = {};

    DWORD length = GetTempPathA(MAX_PATH, temp);

    if (length == 0 || length >= MAX_PATH)
        return;

    int result = sprintf_s(
        filename,
        "%skwds-tcp-router-%lu.log",
        temp,
        GetCurrentProcessId()
    );

    if (result <= 0)
        return;

    HANDLE file = CreateFileA(
        filename,
        FILE_APPEND_DATA,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        nullptr,
        OPEN_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        nullptr
    );

    if (file == INVALID_HANDLE_VALUE)
        return;

    DWORD written = 0;
    DWORD size = static_cast<DWORD>(strlen(message));

    SYSTEMTIME now = {};
    GetSystemTime(&now);
    char stamp[48] = {};
    int stampLength = sprintf_s(stamp, "%04u-%02u-%02uT%02u:%02u:%02u.%03uZ ",
        now.wYear, now.wMonth, now.wDay, now.wHour, now.wMinute, now.wSecond, now.wMilliseconds);
    if (stampLength > 0) WriteFile(file, stamp, static_cast<DWORD>(stampLength), &written, nullptr);
    WriteFile(file, message, size, &written, nullptr);
    WriteFile(file, "\r\n", 2, &written, nullptr);

    CloseHandle(file);
}

#include "kwds-local-trust-live.h"

//
// KWDS_TRUST_OBSERVER_V1
// Research-only: inspect the main module at the known game RVA.
// Classification is read-only. Explicit local trust adaptation is separately opt-in.
//
static void LogRuntimeFeslTrustKey()
{
    HMODULE gameModule = GetModuleHandleW(nullptr);

    if (!gameModule)
    {
        WriteLog("trust-main-module-missing");
        return;
    }

    MODULEINFO info = {};

    if (!GetModuleInformation(
            GetCurrentProcess(),
            gameModule,
            &info,
            sizeof(info)))
    {
        WriteLog("trust-module-information-unavailable");
        return;
    }

    constexpr std::size_t keyRva = 0x006BA900;

    // An RVA is only meaningful for the researched game build.
    // The exact-build policy in ApplyExplicitLocalTrust gates any opt-in write.
    if (info.SizeOfImage < keyRva ||
        info.SizeOfImage - keyRva < kwds_trust::kModulusLength)
    {
        WriteLog("trust-rva-out-of-range");
        return;
    }

    const unsigned char* key =
        reinterpret_cast<const unsigned char*>(info.lpBaseOfDll)
        + keyRva;

    MEMORY_BASIC_INFORMATION page = {};

    if (VirtualQuery(key, &page, sizeof(page)) != sizeof(page) ||
        page.State != MEM_COMMIT ||
        (page.Protect & (PAGE_NOACCESS | PAGE_GUARD)) != 0)
    {
        WriteLog("trust-memory-not-readable");
        return;
    }

    const std::uintptr_t address =
        reinterpret_cast<std::uintptr_t>(key);

    const std::uintptr_t region =
        reinterpret_cast<std::uintptr_t>(page.BaseAddress);

    if (address < region ||
        address - region > page.RegionSize ||
        page.RegionSize - (address - region) <
            kwds_trust::kModulusLength)
    {
        WriteLog("trust-memory-region-too-small");
        return;
    }

    const auto identity = kwds_trust::IdentifyPublicModulus(
        key,
        kwds_trust::kModulusLength
    );

    switch (identity)
    {
        case kwds_trust::KeyIdentity::OriginalEa:
            WriteLog("trust-runtime-ea-original");
            break;

        case kwds_trust::KeyIdentity::CncOnline:
            WriteLog("trust-runtime-cnc-online");
            break;

        case kwds_trust::KeyIdentity::Unknown:
            WriteLog("trust-runtime-unknown");
            break;

        default:
            WriteLog("trust-runtime-invalid");
            break;
    }
    ApplyExplicitLocalTrust(key, identity);
}

static int WSAAPI HookConnect(
    SOCKET socketHandle,
    const sockaddr* address,
    int addressLength)
{
    if (RealConnect == nullptr)
        return SOCKET_ERROR;

    if (address && addressLength >= static_cast<int>(sizeof(sockaddr_in6)) &&
        address->sa_family == AF_INET6 && InterlockedCompareExchange(&RouteMode, 0, 0) == 2 &&
        !IN6_IS_ADDR_LOOPBACK(&reinterpret_cast<const sockaddr_in6*>(address)->sin6_addr))
    {
        WriteLog("local-test-nonloopback-ipv6-tcp-blocked");
        WSASetLastError(WSAEACCES);
        return SOCKET_ERROR;
    }

    if (address == nullptr ||
        addressLength < static_cast<int>(sizeof(sockaddr_in)) ||
        address->sa_family != AF_INET)
    {
        return RealConnect(socketHandle, address, addressLength);
    }

    const sockaddr_in* ipv4 =
        reinterpret_cast<const sockaddr_in*>(address);

    unsigned short port = ntohs(ipv4->sin_port);

    if (InterlockedCompareExchange(&RouteMode, 0, 0) == 2)
    {
        char entry[96] = {};
        unsigned long ip = ntohl(ipv4->sin_addr.s_addr);
        sprintf_s(entry, "local-tcp-attempt=%lu.%lu.%lu.%lu:%u",
                  (ip >> 24) & 255, (ip >> 16) & 255, (ip >> 8) & 255, ip & 255, port);
        WriteLog(entry);
    }

    const unsigned long targetAddress =
        inet_addr("195.60.166.61");

    const bool localMode = InterlockedCompareExchange(&RouteMode, 0, 0) == 2;
    if ((port != 18760 && !kwds_route::IsBootstrapSocketTarget(ntohl(ipv4->sin_addr.s_addr), port, localMode)) ||
        (InterlockedCompareExchange(&RouteMode, 0, 0) != 2 && ipv4->sin_addr.s_addr != targetAddress))
    {
        if (InterlockedCompareExchange(&RouteMode, 0, 0) == 2 &&
            (ntohl(ipv4->sin_addr.s_addr) >> 24) != 127)
        {
            WriteLog("local-test-nonloopback-tcp-blocked");
            WSASetLastError(WSAEACCES);
            return SOCKET_ERROR;
        }
        return RealConnect(socketHandle, address, addressLength);
    }

    WriteLog(port == 80 ? "bootstrap-http-connect-observed" : "fesl-connect-observed");

    if (InterlockedCompareExchange(&RouteMode, 0, 0) != 2)
    {
        WriteLog("fesl-observe-only");
        return RealConnect(socketHandle, address, addressLength);
    }

    LogRuntimeFeslTrustKey();

    sockaddr_in redirected = *ipv4;
    redirected.sin_addr.s_addr = inet_addr("127.0.0.1");
    redirected.sin_port = htons(18760);

    WriteLog(port == 80 ? "bootstrap-http-redirect-attempt" : "fesl-redirect-attempt");

    int result = RealConnect(
        socketHandle,
        reinterpret_cast<const sockaddr*>(&redirected),
        sizeof(redirected)
    );

    int savedError = WSAGetLastError();

    if (result == 0)
    {
        WriteLog("fesl-redirect-result-success");
    }
    else if (savedError == WSAEWOULDBLOCK ||
             savedError == WSAEINPROGRESS)
    {
        WriteLog("fesl-redirect-result-pending");
    }
    else
    {
        WriteLog("fesl-redirect-result-error");
    }

    WSASetLastError(savedError);
    return result;
}

static hostent* WSAAPI HookDns(const char* hostname)
{
    if (RealDns == nullptr)
        return nullptr;

    if (kwds_route::IsBootstrapDnsName(hostname)) {
        WriteLog("dns-bootstrap-request");
        if (InterlockedCompareExchange(&RouteMode, 0, 0) == 2) {
            WriteLog("dns-bootstrap-local-redirect");
            return RealDns("127.0.0.1");
        }
    }

    if (hostname != nullptr &&
        (_stricmp(hostname, "cnc3-ep1-pc.fesl.ea.com") == 0 ||
         _stricmp(hostname, "login.server.cnc-online.net") == 0))
    {
        WriteLog("dns-target-request");

        if (InterlockedCompareExchange(&RouteMode, 0, 0) == 2)
        {
            WriteLog("dns-local-redirect");

            // KWDS_TRUST_DNS_OBSERVE_V1
            // Observe the runtime key before local DNS redirection.
            // Optional local trust policy applies after classification.
            LogRuntimeFeslTrustKey();

            return RealDns("127.0.0.1");
        }
    }

    hostent* result = RealDns(hostname);
    const int error = WSAGetLastError();
    static volatile LONG otherDnsEvents = 0;
    if (InterlockedCompareExchange(&RouteMode, 0, 0) == 2 &&
        InterlockedIncrement(&otherDnsEvents) <= 32) {
        char entry[96] = {};
        sprintf_s(entry, "dns-other-result=%s error=%d", result ? "resolved" : "failed", error);
        WriteLog(entry); // Never log arbitrary DNS names or returned addresses.
    }
    WSASetLastError(error);
    return result;
}

// Exact-build diagnostic wrapper: preserve all four arguments and return value.
using CertificateFn = int (__cdecl*)(const void*, void*, const void*, unsigned int);
static CertificateFn RealCertificate = nullptr;
// Observe only exact public fixture names from the verified build's structures.
// Unknown text, credentials and arbitrary memory are never written to logs.
static const char* CertificateNameClass(const void* address, char (&publicName)[64])
{
    char value[64] = {}; SIZE_T read = 0;
    if (!address || !ReadProcessMemory(GetCurrentProcess(), address, value, sizeof(value)-1, &read)) return "unreadable";
    if (!memchr(value, 0, read)) return "unclassified";
    if (value[0] == 0) return "empty";
    const size_t length = strlen(value);
    for (size_t i = 0; i < length; ++i) {
        const unsigned char c = static_cast<unsigned char>(value[i]);
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == '.' || c == '-')) return "unclassified";
    }
    const char* suffixes[] = {".ea.com", ".gamespy.com", ".cnc-online.net"};
    bool permitted = strcmp(value, "127.0.0.1") == 0;
    for (const char* suffix : suffixes) {
        const size_t n = strlen(suffix);
        if (length > n && _stricmp(value + length - n, suffix) == 0) permitted = true;
    }
    if (!permitted) return "unclassified";
    strcpy_s(publicName, value);
    return publicName;
}
static int __cdecl ObserveCertificate(const void* a, void* b, const void* c, unsigned int d)
{
    const int result = RealCertificate(a, b, c, d);
    char message[192] = {};
    sprintf_s(message, "client-certificate-result=%d", result);
    // Certificate DER is public; never log raw bytes or application payload.
    // A fingerprint correlates this result to the actually served identity.
    if (c && d > 0 && d <= 16384) {
        unsigned char der[16384] = {}, digest[32] = {};
        SIZE_T read = 0;
        BCRYPT_ALG_HANDLE alg = nullptr;
        if (ReadProcessMemory(GetCurrentProcess(), c, der, d, &read) && read == d &&
            BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) == 0) {
            if (BCryptHash(alg, nullptr, 0, der, d, digest, sizeof(digest)) == 0) {
                char hex[65] = {};
                for (unsigned int i = 0; i < 32; ++i) sprintf_s(hex + i*2, 65-i*2, "%02x", digest[i]);
                sprintf_s(message, "client-certificate-result=%d der-sha256=%s der-length=%u", result, hex, d);
            }
            BCryptCloseAlgorithmProvider(alg, 0);
        }
    }
    WriteLog(message);
    char names[224] = {}, expectedName[64] = {}, subjectName[64] = {};
    sprintf_s(names, "certificate-name-check expected=%s subject=%s",
        CertificateNameClass(a ? reinterpret_cast<const unsigned char*>(a) + 12 : nullptr, expectedName),
        CertificateNameClass(b ? reinterpret_cast<const unsigned char*>(b) + 0x164 : nullptr, subjectName));
    WriteLog(names);
    return result;
}

// Exact-build game import slots verified against the PE imports and live IAT.
// Calling the saved Winsock entries preserves installed middleware behavior.
static bool InstallLocalImportRouting()
{
    if (!KnownGameOnDisk()) return false;
    auto base = reinterpret_cast<unsigned char*>(GetModuleHandleW(nullptr));
    auto dnsSlot = reinterpret_cast<PVOID*>(base + 0x0060B7C8);
    auto connectSlot = reinterpret_cast<PVOID*>(base + 0x0060B7E4);
    if (*dnsSlot != reinterpret_cast<PVOID>(RealDns) ||
        *connectSlot != reinterpret_cast<PVOID>(RealConnect)) return false;
    DWORD old = 0;
    if (!VirtualProtect(dnsSlot, 0x20, PAGE_READWRITE, &old)) return false;
    InterlockedExchangePointer(dnsSlot, reinterpret_cast<PVOID>(HookDns));
    InterlockedExchangePointer(connectSlot, reinterpret_cast<PVOID>(HookConnect));
    DWORD ignored = 0;
    if (!VirtualProtect(dnsSlot, 0x20, old, &ignored)) return false;
    WriteLog("local-game-import-routing-active");
    return true;
}

static DWORD WINAPI AdapterWorker(LPVOID)
{
    WriteLog("worker-start");

    char mode[64] = {};

    DWORD modeLength = GetEnvironmentVariableA(
        "KWDS_ROUTE_MODE",
        mode,
        sizeof(mode)
    );

    if (modeLength > 0 && modeLength < sizeof(mode))
    {
        if (_stricmp(mode, "local-fesl") == 0)
        {
            InterlockedExchange(&RouteMode, 2);
            WriteLog("mode-local-fesl");
        }
        else if (_stricmp(mode, "observe") == 0)
        {
            InterlockedExchange(&RouteMode, 1);
            WriteLog("mode-observe");
        }
        else
        {
            WriteLog("mode-disabled-unknown");
        }
    }
    else
    {
        WriteLog("mode-disabled");
    }

    // KWDS_ROUTER_SOURCE_HARDENING_V1
    // Disabled or unknown routing modes must not install hooks.
    // Supported explicit modes: observe and local-fesl.
    if (InterlockedCompareExchange(&RouteMode, 0, 0) == 0)
    {
        WriteLog("hook-skipped-disabled");
        return 0;
    }

    // Installed middleware also detours Winsock. Wait until its key update,
    // which follows its socket-hook initialization, before chaining our hooks.
    if (InterlockedCompareExchange(&RouteMode, 0, 0) == 2 && KnownGameOnDisk())
    {
        wchar_t path[MAX_PATH] = {};
        GetModuleFileNameW(nullptr, path, MAX_PATH);
        wchar_t* slash = wcsrchr(path, L'\\');
        if (slash) wcscpy_s(slash + 1, MAX_PATH - (slash + 1 - path), L"dsound.dll");
        if (slash && GetFileAttributesW(path) != INVALID_FILE_ATTRIBUTES)
        {
            const auto key = reinterpret_cast<const unsigned char*>(GetModuleHandleW(nullptr)) + 0x006BA900;
            unsigned int attempt = 0;
            for (; attempt < 1000; ++attempt)
            {
                if (kwds_trust::IdentifyPublicModulus(key, 128) == kwds_trust::KeyIdentity::CncOnline) break;
                Sleep(10);
            }
            if (attempt == 1000) { WriteLog("middleware-readiness-timeout"); return 8; }
            WriteLog("middleware-key-ready-before-hooks");
        }
    }

    HMODULE winsock = GetModuleHandleW(L"ws2_32.dll");

    if (!winsock)
        winsock = LoadLibraryW(L"ws2_32.dll");

    if (!winsock)
    {
        WriteLog("hook-error-winsock");
        return 1;
    }

    RealConnect = reinterpret_cast<ConnectFn>(
        GetProcAddress(winsock, "connect")
    );

    RealDns = reinterpret_cast<DnsFn>(
        GetProcAddress(winsock, "gethostbyname")
    );

    if (!RealConnect || !RealDns)
    {
        WriteLog("hook-error-export");
        return 2;
    }

    LONG error = DetourTransactionBegin();

    if (error != NO_ERROR)
    {
        WriteLog("hook-error-transaction");
        return 3;
    }

    error = DetourUpdateThread(GetCurrentThread());

    if (error == NO_ERROR && InterlockedCompareExchange(&RouteMode, 0, 0) != 2)
    {
        error = DetourAttach(
            reinterpret_cast<PVOID*>(&RealConnect),
            reinterpret_cast<PVOID>(HookConnect)
        );
    }

    if (error == NO_ERROR && InterlockedCompareExchange(&RouteMode, 0, 0) != 2)
    {
        error = DetourAttach(
            reinterpret_cast<PVOID*>(&RealDns),
            reinterpret_cast<PVOID>(HookDns)
        );
    }

    if (error != NO_ERROR)
    {
        DetourTransactionAbort();
        WriteLog("hook-error-attach");
        return 4;
    }

    char diagnostics[8] = {};
    if (InterlockedCompareExchange(&RouteMode, 0, 0) == 2 &&
        GetEnvironmentVariableA("KWDS_CERT_DIAGNOSTICS", diagnostics, sizeof(diagnostics)) == 1 &&
        diagnostics[0] == '1')
    {
        const unsigned char prefix[] = { 0x81, 0xec, 0xa0, 0x00, 0x00, 0x00 };
        auto target = reinterpret_cast<unsigned char*>(GetModuleHandleW(nullptr)) + 0x004FA540;
        if (!KnownGameOnDisk() || memcmp(target, prefix, sizeof(prefix)) != 0)
        {
            DetourTransactionAbort();
            WriteLog("certificate-observer-build-rejected");
            return 6;
        }
        RealCertificate = reinterpret_cast<CertificateFn>(target);
        error = DetourAttach(reinterpret_cast<PVOID*>(&RealCertificate),
                             reinterpret_cast<PVOID>(ObserveCertificate));
        if (error != NO_ERROR)
        {
            DetourTransactionAbort();
            WriteLog("certificate-observer-attach-failed");
            return 7;
        }
        WriteLog("certificate-observer-prepared");
    }

    error = DetourTransactionCommit();

    if (error != NO_ERROR)
    {
        WriteLog("hook-error-commit");
        return 5;
    }

    if (InterlockedCompareExchange(&RouteMode, 0, 0) == 2 && !InstallLocalImportRouting())
    {
        WriteLog("local-import-routing-failed");
        TerminateProcess(GetCurrentProcess(), 0xE005);
        return 9;
    }

    WriteLog("hook-active");
    return 0;
}



extern "C" void CALLBACK KwdsHelper(
    HWND window,
    HINSTANCE instance,
    LPSTR command,
    INT show)
{
    DetourFinishHelperProcess(
        window,
        instance,
        command,
        show
    );
}

BOOL WINAPI DllMain(
    HINSTANCE instance,
    DWORD reason,
    LPVOID)
{
    if (DetourIsHelperProcess())
        return TRUE;

    if (reason == DLL_PROCESS_ATTACH)
    {
        DisableThreadLibraryCalls(instance);

        if (!DetourRestoreAfterWith())
            return FALSE;

        HANDLE worker = CreateThread(
            nullptr,
            0,
            AdapterWorker,
            nullptr,
            0,
            nullptr
        );

        if (!worker)
            return FALSE;

        CloseHandle(worker);
    }

    return TRUE;
}