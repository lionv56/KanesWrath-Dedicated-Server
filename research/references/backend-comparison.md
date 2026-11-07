# Kane's Wrath - Existing Backend Comparison

Research review: 2026-11-07
Scope: issue #2, technical reference research.

## Sources

Kirov Server Emulator:
https://github.com/sokie/kirov-server-emulator

Kirov releases:
https://github.com/sokie/kirov-server-emulator/releases

C&C:Online:
https://cnc-online.net/en/setup/

Tacitus announcement:
https://kaneswrath.com/cconline-tacitus/

C&C Community installation guide:
https://cnc.community/command-and-conquer-3/how-to-play

## Kirov capabilities

The Kirov project's README describes support for
Kane's Wrath, Tiberium Wars, Red Alert 3 and other games.

The project describes implemented services for:

- FESL authentication and sessions
- GameSpy Presence
- Peerchat and lobby coordination
- Master Server game discovery
- NAT negotiation
- UDP relay fallback
- Heartbeat registration
- GameStats
- Matchmaking features

These are upstream implementation claims.
They have not been independently integrated
or tested in our Kane's Wrath project.

Kirov documentation describes client-side
P2P negotiation during match startup.

This does not demonstrate a central server
executing the authoritative game simulation.

## C&C:Online and Tacitus

C&C:Online provides a community online service
for Command & Conquer games, including Kane's Wrath.

Tacitus is its supported client integration.
The 2025 announcement describes support for
newer game versions.

C&C:Online service compatibility must not be
confused with compatibility of our own implementation.

## Comparison with our project

| Capability | Kirov documented | Our implementation |
|---|---|---|
| Authentication | Yes | No |
| Presence | Yes | Framing prototype only |
| Lobby/chat | Yes | No |
| Game discovery | Yes | No |
| NAT negotiation | Yes | No |
| UDP relay | Yes | No |
| Server-authoritative simulation | Not established | No |
| Gameplay P2P removed | Not established | No |
| Disconnect AI takeover | Not established | No |
| Checkpoint recovery | Not established | No |

"Not established" means the reviewed sources do not
provide sufficient evidence for that capability.

It is not a claim that implementation is impossible.

## Build compatibility matrix

| Build/distribution | Local verification |
|---|---|
| Installed 1.02 game binary | Verified via SHA256 |
| Other Steam builds | Not tested |
| EA App builds | Not tested |
| Version 1.03 | Not tested |
| Disc builds other than installed binary | Not tested |

External sources describe support for multiple
distribution versions, but do not establish
compatibility with our custom server.

## Architecture consequence

A lobby, matchmaking backend or UDP relay alone
does not provide an authoritative simulation.

The key feasibility milestone remains proving
that the server can execute or validate the
game's deterministic state transitions.

That feasibility belongs to the later
deterministic simulation and authoritative
gameplay development steps.

## Research status

- Existing emulator reference reviewed: YES
- Major backend capabilities compared: YES
- External reference URLs recorded: YES
- Local 1.02 version evidence recorded: YES
- Other builds tested: NO
- Real client to custom backend tested: NO
- Authoritative simulation established: NO

This is documentation evidence for issue #2.
It does not by itself close the issue.

## Safety and licensing boundaries

Do not commit proprietary EA game binaries,
private credentials or raw sensitive captures.

Review third-party licenses before reusing code.
Protocol research alone does not grant rights
to reuse another project's implementation.