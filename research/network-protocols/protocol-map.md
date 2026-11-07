# Kane's Wrath Network Protocol Research

## Current understanding

The game uses a synchronized multiplayer architecture
with peer-to-peer gameplay dependencies.

The following layers need separate investigation.

| Layer | Research focus | Status |
|---|---|---|
| Authentication | EA / GameSpy protocols | Research |
| Presence | Online players | Research |
| Lobby | Chat and rooms | Research |
| Matchmaking | Game discovery | Research |
| NAT | Connectivity negotiation | Research |
| Relay | UDP packet forwarding | Research |
| Gameplay | Commands and lockstep | Unproven |
| Simulation | Deterministic state | Unproven |
| Recovery | Disconnect and reconnect | Unproven |

## Server architecture goal

Game client
    |
    v
Custom Launcher / Client Adapter
    |
    v
Dedicated Gateway
    |
    v
Authoritative Game Simulation
    |
    +-- Match state
    +-- Simulation ticks
    +-- Command validation
    +-- Player sessions
    +-- Recovery

## Required evidence

- Supported executable identification.
- Reproducible connection traces.
- Protocol message descriptions.
- Legal and technical compatibility review.
- Real-client integration results.

## Acceptance

This document alone does not complete the research issue.
Actual protocol investigation and reproducible evidence
are still required.