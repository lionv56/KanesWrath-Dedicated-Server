# Kane's Wrath 1.02 - Network Research Findings

## Target

- Game: Command & Conquer 3: Kane's Wrath
- Target version: 1.02
- Active executable: RetailExe/1.2/cnc3ep1.dat
- Original binary SHA256 verification: PASS

## Observed network endpoints

- Observed remote IP: 195.60.166.61
- Game-owned established TCP ports: 16667, 18760, 28910, 29900
- Process attribution: CONFIRMED
- cnc-online.net resolved to the observed IP in the recorded test
- Exact hostname-to-connection mapping: NOT CONFIRMED

## Protocol observations

- TCP port 29900 contained GameSpy-style text
- Observed fields include status and final
- Final is a message delimiter candidate
- Synthetic parser tests: 4 PASS
- Full TCP-stream reassembly: NOT VALIDATED
- Authentication protocol: NOT VALIDATED

## Local implementation

- Prototype: research/prototypes/gamespy-status/server.js
- Test: research/prototypes/gamespy-status/integration.test.js
- Local TCP integration: PASS
- Real Kane's Wrath client to prototype: NOT TESTED
- Working lobby or authentication: NOT IMPLEMENTED

## Routing and configuration

- Tacitus.ini found in 1.2 and 1.3 directories
- Recognized network-related configuration keys: UseAltPeerChatPort
- No explicit server destination setting was identified
- No matching active hosts-file routing entries observed
- No recognized hook module identified
- Absence of visible hooks does not exclude other routing methods

## Remaining issues

1. Determine the real client routing mechanism in an isolated environment.
2. Demonstrate a TCP connection from the real 1.02 client to a local service.
3. Determine request-response protocol semantics without exposing credentials.
4. Separate lobby service compatibility from authoritative game simulation.
5. Evaluate deterministic simulation feasibility independently.

## Acceptance boundaries

- Networking observations verified: YES
- Local TCP framing prototype accepted: YES
- Complete GameSpy protocol implemented: NO
- Real client compatibility proven: NO
- Gameplay P2P eliminated: NO
- Authoritative simulation implemented: NO
- Production-ready dedicated server: NO

## GitHub workflow

- Review issue #2 acceptance criteria before closing.
- Carry the client routing feasibility work into issue #4.
- Do not commit or push without integrated test acceptance and approval.