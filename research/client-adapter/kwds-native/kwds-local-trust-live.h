#pragma once
#include <bcrypt.h>
#pragma comment(lib, "bcrypt.lib")

// Opt-in issuer-key replacement for the exact researched build, in memory only.
// Does not bypass signature checking or change the game file on disk.
static bool KnownGameOnDisk()
{
    wchar_t path[MAX_PATH] = {};
    const DWORD n = GetModuleFileNameW(nullptr, path, MAX_PATH);
    if (!n || n >= MAX_PATH) return false;
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, nullptr,
                              OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) return false;
    BCRYPT_ALG_HANDLE alg = nullptr;
    BCRYPT_HASH_HANDLE hash = nullptr;
    unsigned char digest[32] = {}, buffer[65536];
    bool ok = BCryptOpenAlgorithmProvider(&alg, BCRYPT_SHA256_ALGORITHM, nullptr, 0) == 0;
    if (ok) ok = BCryptCreateHash(alg, &hash, nullptr, 0, nullptr, 0, 0) == 0;
    DWORD read = 0;
    while (ok) {
        if (!ReadFile(file, buffer, sizeof(buffer), &read, nullptr)) { ok = false; break; }
        if (!read) break;
        ok = BCryptHashData(hash, buffer, read, 0) == 0;
    }
    if (ok) ok = BCryptFinishHash(hash, digest, sizeof(digest), 0) == 0;
    if (hash) BCryptDestroyHash(hash);
    if (alg) BCryptCloseAlgorithmProvider(alg, 0);
    CloseHandle(file);
    static const unsigned char expected[32] = {
        0x14,0xce,0x45,0x9e,0x52,0x36,0x6a,0x17,0x6c,0xc4,0xb9,0xf1,0xe6,0x59,0x08,0x9d,
        0x19,0xda,0x22,0x40,0x40,0x60,0x48,0x1b,0x61,0xa1,0xcb,0x35,0xc0,0x02,0x86,0xad
    };
    return ok && memcmp(digest, expected, sizeof(expected)) == 0;
}

static void ApplyExplicitLocalTrust(const unsigned char* key,
                                    kwds_trust::KeyIdentity identity)
{
    char mode[64] = {};
    if (!GetEnvironmentVariableA("KWDS_ROUTE_MODE", mode, sizeof(mode)) ||
        strcmp(mode, "local-fesl") != 0) return;
    wchar_t path[MAX_PATH] = {};
    DWORD n = GetEnvironmentVariableW(L"KWDS_LOCAL_TRUST_MODULUS", path, MAX_PATH);
    if (!n) return; // Existing router behavior remains the default.
    if (n >= MAX_PATH) { WriteLog("local-trust-path-rejected"); return; }
    unsigned char replacement[129] = {};
    HANDLE file = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, nullptr,
                              OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file == INVALID_HANDLE_VALUE) { WriteLog("local-trust-file-missing"); return; }
    DWORD read = 0;
    bool ok = ReadFile(file, replacement, sizeof(replacement), &read, nullptr) != 0;
    CloseHandle(file);
    if (!ok || read != 128 || !(replacement[0] & 0x80) || !(replacement[127] & 1)) {
        WriteLog("local-trust-modulus-rejected"); return;
    }
    if (!KnownGameOnDisk()) { WriteLog("local-trust-build-rejected"); return; }
    if (memcmp(key, replacement, 128) == 0) { WriteLog("local-trust-already-matched"); return; }
    if (!kwds_trust::MayPrepareLocalTrustAdaptation(true, true, identity)) {
        WriteLog("local-trust-unknown-key-rejected"); return;
    }
    DWORD old = 0;
    void* destination = const_cast<unsigned char*>(key);
    if (!VirtualProtect(destination, 128, PAGE_READWRITE, &old)) {
        WriteLog("local-trust-protection-failed"); return;
    }
    memcpy(destination, replacement, 128);
    DWORD ignored = 0;
    if (!VirtualProtect(destination, 128, old, &ignored)) {
        WriteLog("local-trust-protection-restore-failed");
        // Stop instead of running with unexpectedly changed page protection.
        TerminateProcess(GetCurrentProcess(), 0xE004);
        return;
    }
    WriteLog("local-trust-own-public-key-installed");
}
