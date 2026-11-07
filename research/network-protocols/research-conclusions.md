# Kane's Wrath - Networking Research Conclusions

Date: 2026-11-07
Issue: #2

## Confirmed local observations

One local Kane's Wrath 1.02 process was observed
with established TCP connections to:
195.60.166.61

Observed destination ports:
16667, 18760, 28910, 29900

Port 29900 contained GameSpy-style
backslash-delimited message fields.

Observed fields included:
status and final.

These are observations, not a complete
protocol specification.

## Local executable evidence

Executable:
RetailExe/1.2/cnc3ep1.dat

SHA256:
14CE459E52366A176CC4B9F1E659089D19DA22404060481B61A1CB35C00286AD

Private capture and endpoint observations
are stored under research/local and excluded
from public version control.

## Existing implementation references

Kirov:
https://github.com/sokie/kirov-server-emulator

Kirov protocol documentation includes:
- FESL authentication
- GameSpy Presence
- Peerchat
- NAT negotiation
- UDP relay
- Game discovery

C&C:Online:
https://cnc-online.net/de/faq/

These are online backend references.
They do not demonstrate server-authoritative
gameplay simulation in this project.

## Technical interpretation

The project must distinguish:
1. Online authentication and presence
2. Lobby and game discovery
3. NAT negotiation and packet relay
4. Gameplay commands and synchronization
5. Server-authoritative deterministic simulation

A GameSpy-compatible backend alone does not
prove that peer-to-peer gameplay can be removed.

A server-authoritative model requires separate
simulation feasibility and client integration
testing in later master steps.

## Prototype evidence

Implementation:
research/prototypes/gamespy-status/server.js

Integration:
research/prototypes/gamespy-status/integration.test.js

Command:
node research/prototypes/gamespy-status/integration.test.js

Expected successful marker:
[RESULT] PROTOTYPE_ACCEPTED_LOCALLY

This verifies localhost framing behavior,
not real game-client protocol compatibility.

## Research acceptance boundary

Established:
- Initial executable and endpoint evidence
- Initial GameSpy-style message framing
- Comparison of existing online backends
- Distribution/build research inventory
- Explicit protocol and architectural limitations

Not established:
- Full SAGE wire protocol specification
- Full GameSpy protocol emulation
- Real game client connection to our server
- Deterministic authoritative simulation
- Gameplay P2P removal
- Disconnect recovery and checkpoints

The unproven items are implementation and
feasibility gates of subsequent master steps.

No credentials or proprietary game files
are included in this research.