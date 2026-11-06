# Kane's Wrath Dedicated Server

An independent community research project for Command & Conquer 3: Kane's Wrath.

## Project vision

Build a self-hosted multiplayer platform with:

- Windows launcher
- Automatic game installation detection
- Reversible compatibility patches
- Account and lobby services
- Multiplayer matchmaking
- Dedicated network gateway
- UDP relay infrastructure
- Authoritative game simulation
- Multiplayer without gameplay P2P dependencies
- Player disconnect isolation
- Player reconnection
- Optional AI takeover
- Server-side match checkpoints
- Match recovery after server failures
- Web-based management dashboard
- Docker development environment
- Linux deployment support

## Architecture

Windows Launcher
    |
    v
Dedicated Gateway
    |
    v
Authoritative Game Server
    |
    +-- Match Simulation
    +-- Match Recovery
    +-- Player Sessions
    +-- AI Takeover
    +-- Monitoring

## Technical limitations

The original Kane's Wrath multiplayer architecture uses
synchronized peer-to-peer simulation.

A UDP relay is not equivalent to an authoritative game server.

Complete authoritative gameplay and original-client compatibility
must be proven by reverse engineering and integration testing.

Full reliability cannot be guaranteed before validation.

## Development requirements

- Use legally installed game copies.
- Never distribute proprietary EA game binaries.
- Do not commit passwords, tokens or private keys.
- Document all protocol research.
- Use reversible and versioned launcher patches.
- Test implementation changes before merging.
- Keep the main branch stable.
- Close issues only after acceptance criteria pass.
- Keep future enhancements separate from the release masterplan.

## Development infrastructure

Primary development:
Windows + PowerShell + Docker Desktop.

Future deployment:
Linux dedicated server.

## Masterplan

GitHub issue #1 contains the complete project checklist.

The implementation issues are executed sequentially.

## Release requirements

The project is only considered complete when real game clients
pass the documented multiplayer, recovery and stability tests.

No unsupported claim of guaranteed crash-free gameplay is made.

## Status

Planning and research phase.
No authoritative game simulation has been validated yet.