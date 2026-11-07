# Issue #2 - Research Acceptance Review

## Scope

Kane's Wrath 1.02 networking and game-build research.

Review state: PARTIALLY ACCEPTED - ISSUE REMAINS OPEN.

## Reproducible game-build evidence

Verified binary:
RetailExe/1.2/cnc3ep1.dat

Verified SHA256:
14CE459E52366A176CC4B9F1E659089D19DA22404060481B61A1CB35C00286AD

Verification command (PowerShell):

Get-FileHash -Algorithm SHA256 -LiteralPath 'D:\Games\steam\steamapps\common\Command and Conquer 3 - Kane''s Wrath\RetailExe\1.2\cnc3ep1.dat'

### Compatibility matrix

| Distribution/build | Status | Evidence |
|---|---|---|
| Installed Kane's Wrath 1.02 executable | Verified locally | SHA256 matches recorded binary |
| Steam distribution compatibility beyond verified executable | Not established | Separate build checks needed |
| EA App distribution compatibility | Not established | Separate build checks needed |
| Version 1.03 compatibility | Not established | Not tested by this project |

The verified executable path alone does not prove
which distribution originally installed the game.

## Observed networking

The recorded local research identified connections
owned by cnc3ep1.dat to 195.60.166.61.

Observed established TCP destination ports:
16667, 18760, 28910, 29900.

TCP port 29900 showed GameSpy-style
backslash-delimited messages, including
status and final fields.

These findings do not establish full protocol
compatibility or prove gameplay server authority.

## Implementation evidence

Prototype:
research/prototypes/gamespy-status/server.js

Integration test:
research/prototypes/gamespy-status/integration.test.js

Test command from repository root:
node research/prototypes/gamespy-status/integration.test.js

Test results:
[PASS] Buffer framing and fragmentation
[PASS] Real localhost TCP integration
[PASS] Two framed messages received
[PASS] Payload contents not logged
[RESULT] PROTOTYPE_ACCEPTED_LOCALLY
[RESULT] REAL_GAME_COMPATIBILITY_NOT_TESTED

## Existing solution references

Kirov Server Emulator:
https://github.com/sokie/kirov-server-emulator

C&C:Online:
https://cnc-online.net/en/faq/

Both are research references. A complete,
source-verified feature and protocol comparison
is not yet recorded.

No claim is made that these references provide
a server-authoritative Kane's Wrath simulation.

## Evidence documents

- research\game-builds\build-matrix.md
- research\network-protocols\protocol-map.md
- research\network-protocols\kw-102-observations.md
- research\network-protocols\kw-102-runtime-findings.md
- research\references\sources.md


## Acceptance status

- [x] Verified local 1.02 executable and hash
- [x] Recorded TCP endpoint and process evidence
- [x] Recorded initial GameSpy-style message evidence
- [x] Documented technical limitations
- [x] Local TCP integration test passed
- [ ] Full Steam and EA compatibility comparison
- [ ] Source-verified emulator capability comparison
- [ ] Final issue #2 acceptance review

## Explicit boundaries

Real game client to own server: NOT TESTED.
Full authentication: NOT IMPLEMENTED.
Gameplay P2P removal: NOT IMPLEMENTED.
Authoritative simulation: NOT IMPLEMENTED.
Production dedicated server: NOT READY.

No proprietary game files belong in Git.
Local raw captures and credentials remain private.