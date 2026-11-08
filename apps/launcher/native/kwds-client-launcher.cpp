#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <windows.h>
#include <iphlpapi.h>
#pragma comment(lib, "iphlpapi.lib")
#include <detours.h>

#include <iostream>
#include <string>
#include <vector>

static bool FileExists(const std::wstring& path) {
    DWORD attributes = GetFileAttributesW(path.c_str());

    return attributes != INVALID_FILE_ATTRIBUTES &&
           !(attributes & FILE_ATTRIBUTE_DIRECTORY);
}

static std::string ToAnsi(const std::wstring& input) {
    int length = WideCharToMultiByte(
        CP_ACP, WC_NO_BEST_FIT_CHARS,
        input.c_str(), -1,
        nullptr, 0, nullptr, nullptr
    );

    if (length <= 0) return {};

    std::vector<char> output(static_cast<size_t>(length));

    BOOL usedDefault = FALSE;

    int written = WideCharToMultiByte(
        CP_ACP, WC_NO_BEST_FIT_CHARS,
        input.c_str(), -1,
        output.data(), length,
        nullptr, &usedDefault
    );

    if (written <= 0 || usedDefault) return {};

    return std::string(output.data());
}

static std::wstring ParentDirectory(const std::wstring& path) {
    size_t separator = path.find_last_of(L"\\/");

    if (separator == std::wstring::npos) return L"";

    return path.substr(0, separator);
}

// Socket hooks cannot contain UDP, dynamic APIs or middleware startup traffic.
// No security settings are changed: refuse local tests while any non-loopback
// network interface is operational. Use an externally isolated test machine.
static bool LocalNetworkIsIsolated() {
    ULONG size = 0;
    ULONG error = GetAdaptersAddresses(AF_UNSPEC, 0, nullptr, nullptr, &size);
    if (error == ERROR_NO_DATA) return true;
    if (error != ERROR_BUFFER_OVERFLOW || size == 0) return false;
    std::vector<unsigned char> data(size);
    auto adapters = reinterpret_cast<IP_ADAPTER_ADDRESSES*>(data.data());
    error = GetAdaptersAddresses(AF_UNSPEC, 0, nullptr, adapters, &size);
    if (error != NO_ERROR) return false;
    for (auto a = adapters; a; a = a->Next) {
        if (a->OperStatus == IfOperStatusUp && a->IfType != IF_TYPE_SOFTWARE_LOOPBACK)
            return false;
    }
    return true;
}
int wmain(int argc, wchar_t** argv) {
    if (argc == 2 && std::wstring(argv[1]) == L"--check-local-containment") {
        const bool ok = LocalNetworkIsIsolated();
        std::wcout << (ok ? L"[PASS] Loopback isolation preflight\n" : L"[BLOCKED] Operational non-loopback interface or uncertain status\n");
        return ok ? 0 : 22;
    }
    if (argc < 3 || argc > 5) {
        std::wcerr
            << L"Usage: kwds-client-launcher.exe "
            << L"<game-executable> <adapter-dll> [observe|local-fesl] [--windowed]\n";
        return 2;
    }

    std::wstring game = argv[1];
    std::wstring adapter = argv[2];

    // KWDS_LAUNCHER_ROUTE_MODE_V1
    // Legacy two-argument invocation defaults to observe.
    // Local server redirection requires an explicit mode.
    std::wstring routeMode =
        argc >= 4 ? argv[3] : L"observe";

    const bool windowed = argc == 5;
    if (windowed && std::wstring(argv[4]) != L"--windowed") {
        std::wcerr << L"[BLOCKED] Invalid display mode.\n";
        return 23;
    }

    if (routeMode != L"observe" &&
        routeMode != L"local-fesl") {
        std::wcerr
            << L"[BLOCKED] Invalid route mode.\n";
        return 10;
    }

    if (routeMode == L"local-fesl" && !LocalNetworkIsIsolated()) {
        std::wcerr << L"[BLOCKED] Local test requires external loopback isolation; no game started.\n";
        return 22;
    }
    if (!FileExists(game)) {
        std::wcerr << L"[BLOCKED] Game executable missing.\n";
        return 3;
    }

    if (!FileExists(adapter)) {
        std::wcerr << L"[BLOCKED] Adapter missing.\n";
        return 4;
    }

    std::string adapterAnsi = ToAnsi(adapter);

    if (adapterAnsi.empty()) {
        std::wcerr << L"[BLOCKED] Adapter path encoding unsupported.\n";
        return 5;
    }

    std::wstring directory = ParentDirectory(game);

    if (directory.empty()) {
        std::wcerr << L"[BLOCKED] Invalid game directory.\n";
        return 6;
    }

    STARTUPINFOW startup = {};
    startup.cb = sizeof(startup);

    PROCESS_INFORMATION process = {};

    std::wstring sku = ParentDirectory(
        ParentDirectory(ParentDirectory(game))
    ) + L"\\CNC3EP1_dutch_1.2.SkuDef";

    if (!FileExists(sku)) {
        std::wcerr << L"[BLOCKED] Game SKU configuration missing.\n";
        return 8;
    }

    std::wstring commandLine =
        L"\"" + game + L"\" -config \"" + sku + L"\"";
    // Optional, reversible CLI-only workaround for fullscreen initialization.
    // No game file or graphics driver is patched.
    if (windowed) commandLine += L" -win -xres 800 -yres 600";
    std::vector<wchar_t> command(
        commandLine.begin(), commandLine.end()
    );
    command.push_back(L'\0');

    std::wcout << L"[INFO] Explicit Detours launch\n";
    std::wcout << L"[INFO] Game: " << game << L"\n";
    std::wcout << L"[INFO] Adapter: " << adapter << L"\n";

    DWORD oldLength = GetEnvironmentVariableW(
        L"KWDS_ADAPTER_ENABLE", nullptr, 0
    );

    std::wstring oldValue;
    bool hadOldValue = oldLength > 0;

    if (hadOldValue) {
        std::vector<wchar_t> previous(oldLength);

        GetEnvironmentVariableW(
            L"KWDS_ADAPTER_ENABLE",
            previous.data(),
            oldLength
        );

        oldValue = previous.data();
    }

    // Preserve the parent's existing route configuration.
    DWORD previousRouteLength = GetEnvironmentVariableW(
        L"KWDS_ROUTE_MODE", nullptr, 0
    );

    std::wstring previousRouteValue;
    bool hadPreviousRoute = previousRouteLength > 0;

    if (hadPreviousRoute) {
        std::vector<wchar_t> previousRoute(
            previousRouteLength
        );

        DWORD copied = GetEnvironmentVariableW(
            L"KWDS_ROUTE_MODE",
            previousRoute.data(),
            previousRouteLength
        );

        if (copied == 0 || copied >= previousRouteLength) {
            std::wcerr
                << L"[BLOCKED] Could not read previous route mode.\n";
            return 11;
        }

        previousRouteValue = previousRoute.data();
    }

    if (!SetEnvironmentVariableW(
        L"KWDS_ADAPTER_ENABLE", L"1"
    )) {
        std::wcerr << L"[BLOCKED] Could not enable adapter.\n";
        return 7;
    }

    // Only the selected child process inherits the route mode.
    if (!SetEnvironmentVariableW(
            L"KWDS_ROUTE_MODE",
            routeMode.c_str())) {

        // Restore the legacy adapter setting on failure.
        if (hadOldValue) {
            SetEnvironmentVariableW(
                L"KWDS_ADAPTER_ENABLE",
                oldValue.c_str()
            );
        } else {
            SetEnvironmentVariableW(
                L"KWDS_ADAPTER_ENABLE",
                nullptr
            );
        }

        std::wcerr
            << L"[BLOCKED] Could not set KWDS_ROUTE_MODE.\n";
        return 12;
    }

    std::wcout << L"[INFO] Route mode: "
               << routeMode << L"\n";

    BOOL started = DetourCreateProcessWithDllExW(
        game.c_str(),
        command.data(),
        nullptr,
        nullptr,
        FALSE,
        0,
        nullptr,
        directory.c_str(),
        &startup,
        &process,
        adapterAnsi.c_str(),
        nullptr
    );

    DWORD launchError = started ? ERROR_SUCCESS : GetLastError();

    // Restore the launcher process environment after creation.
    BOOL restoredRoute = hadPreviousRoute
        ? SetEnvironmentVariableW(
            L"KWDS_ROUTE_MODE",
            previousRouteValue.c_str()
          )
        : SetEnvironmentVariableW(
            L"KWDS_ROUTE_MODE",
            nullptr
          );

    if (!restoredRoute) {
        std::wcerr
            << L"[WARNING] Route environment restoration failed.\n";
    }

    if (hadOldValue) {
        SetEnvironmentVariableW(
            L"KWDS_ADAPTER_ENABLE", oldValue.c_str()
        );
    } else {
        SetEnvironmentVariableW(
            L"KWDS_ADAPTER_ENABLE", nullptr
        );
    }

    if (!started) {
        std::wcerr
            << L"[BLOCKED] Detours process creation failed: "
            << launchError << L"\n";
        return 8;
    }

    std::wcout
        << L"[INFO] Process created. PID: "
        << process.dwProcessId << L"\n";

    CloseHandle(process.hThread);

    DWORD waitResult = WaitForSingleObject(
        process.hProcess, INFINITE
    );

    DWORD exitCode = 0;

    if (waitResult == WAIT_OBJECT_0) {
        GetExitCodeProcess(process.hProcess, &exitCode);
    } else {
        std::wcerr << L"[WARNING] Process wait failed.\n";
    }

    CloseHandle(process.hProcess);

    std::wcout
        << L"[INFO] Game process ended. Exit code: "
        << exitCode << L"\n";

    return waitResult == WAIT_OBJECT_0 ? 0 : 9;
}
