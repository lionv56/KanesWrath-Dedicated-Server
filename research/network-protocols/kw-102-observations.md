# Kane's Wrath 1.02 - Network Observations

## Target
Kane's Wrath 1.02 only.

## Verified client
RetailExe/1.2/cnc3ep1.dat

## Recorded evidence
- Process count: 1
- Unique UDP endpoint records: 1
- Unique TCP records: 10
- Local UDP ports: 6500
- Remote TCP ports: 0, 16667, 18760, 28910, 29900

## Specific observations
- UDP 6500 detected: True
- TCP 29900 detected: True
- TCP 28910 detected: True

## Protocol reference

Kirov Server Emulator documents:
- FESL authentication
- GameSpy Presence
- Peerchat
- Master Server
- NAT negotiation
- UDP relay
- Heartbeat
- GameStats

Reference:
https://github.com/sokie/kirov-server-emulator

## Evidence boundaries

The Windows measurements show connection endpoints.
They do not reveal packet contents or prove the
exact application protocol for an endpoint.

The measurements do not prove that P2P gameplay
has been replaced with authoritative simulation.

## Next research work

- [x] Locate version 1.02 binary
- [x] Observe 1.02 Windows game process
- [x] Record TCP and UDP endpoints
- [ ] Identify connection message formats
- [ ] Validate lobby protocol against live client
- [ ] Record gameplay traffic in a controlled match
- [ ] Analyze lockstep and command synchronization
- [ ] Complete research acceptance evidence

## Status
IN PROGRESS