# KWDS native client launcher - Issue #4

Experimental Windows x86 launcher.

## Purpose

Start a specifically selected Kane's Wrath executable with
the existing KWDS DNS adapter explicitly loaded through
Microsoft Detours.

This avoids depending on Windows automatically selecting
a copied winmm.dll from the game directory.

## Requirements

- Windows x86 compilation
- Microsoft Visual C++ compiler
- Microsoft Detours headers and x86 library
- Legally installed Kane's Wrath
- Existing compatible x86 KWDS adapter

## Safety

- Does not overwrite game files
- Does not overwrite Tacitus / dsound.dll
- Does not modify Windows system DLLs
- Does not persistently change environment variables
- Does not unload the adapter from a running game
- Must be tested in an isolated local environment
- No account credentials should be used in diagnostics

## Important limitations

This is source code, not a validated working launcher.

The game may require Steam-specific startup parameters,
launcher initialization or working directory behavior.

Directly starting cnc3ep1.dat may fail.

Detours injection success does not prove that the DNS hook
initialized or that the original client reached the gateway.

The DNS hook currently changes an IP address, not the
destination port or the FESL protocol.

Do not ship or mark issue #4 complete until the actual
client passes its acceptance tests.

## 2026-11-08 isolated feasibility result

The x86 launcher and local adapter successfully started the exact tested 1.2
client in an offline Windows Sandbox with `--windowed`. The actual client
completed SSL3 and sent Hello / MemCheck / Login to a loopback test service.
A scoped in-memory own-public-key trust adjustment was required; this does
not demonstrate a stock client connection or a deployable authentication
backend. See `research/client-adapter/issue4-acceptance-summary.md`.
