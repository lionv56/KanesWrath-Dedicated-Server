#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <windows.h>
#include <detours.h>
#include <cstring>

using gethostbyname_t = hostent* (WSAAPI*)(const char*);

static gethostbyname_t OriginalGetHostByName = nullptr;

extern "C" void CALLBACK KwdsHelper(
    HWND window,
    HINSTANCE instance,
    LPSTR command,
    INT show
) {
    DetourFinishHelperProcess(window, instance, command, show);
}

static hostent* WSAAPI KwdsDnsHook(const char* hostname) {
    if (OriginalGetHostByName == nullptr) {
        return nullptr;
    }

    if (hostname != nullptr &&
        _stricmp(hostname, "cnc3-ep1-pc.fesl.ea.com") == 0) {
        return OriginalGetHostByName("127.0.0.1");
    }

    return OriginalGetHostByName(hostname);
}

static DWORD WINAPI AdapterWorker(LPVOID) {
    char enabled[4] = {};

    DWORD length = GetEnvironmentVariableA(
        "KWDS_ADAPTER_ENABLE",
        enabled,
        sizeof(enabled)
    );

    if (length != 1 || enabled[0] != '1') {
        return 0;
    }

    HMODULE winsock = GetModuleHandleW(L"ws2_32.dll");

    if (!winsock) {
        winsock = LoadLibraryW(L"ws2_32.dll");
    }

    if (!winsock) {
        return 1;
    }

    OriginalGetHostByName =
        reinterpret_cast<gethostbyname_t>(
            GetProcAddress(winsock, "gethostbyname")
        );

    if (!OriginalGetHostByName) {
        return 2;
    }

    LONG error = DetourTransactionBegin();

    if (error != NO_ERROR) {
        return 3;
    }

    error = DetourUpdateThread(GetCurrentThread());

    if (error != NO_ERROR) {
        DetourTransactionAbort();
        return 4;
    }

    error = DetourAttach(
        reinterpret_cast<PVOID*>(&OriginalGetHostByName),
        reinterpret_cast<PVOID>(KwdsDnsHook)
    );

    if (error != NO_ERROR) {
        DetourTransactionAbort();
        return 5;
    }

    error = DetourTransactionCommit();

    if (error != NO_ERROR) {
        return 6;
    }

    return 0;
}

BOOL WINAPI DllMain(
    HINSTANCE module,
    DWORD reason,
    LPVOID
) {
    if (reason == DLL_PROCESS_ATTACH) {
        if (DetourIsHelperProcess()) {
            return TRUE;
        }

        if (!DetourRestoreAfterWith()) {
            return FALSE;
        }

        DisableThreadLibraryCalls(module);

        HANDLE worker = CreateThread(
            nullptr,
            0,
            AdapterWorker,
            nullptr,
            0,
            nullptr
        );

        if (worker) {
            CloseHandle(worker);
        }
    }

    return TRUE;
}
