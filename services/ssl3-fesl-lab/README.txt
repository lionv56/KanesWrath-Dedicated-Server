KWDS ISSUE #4 — LOCAL SSL3/FESL LABORATORY
Date: 2026-11-08, Europe/Amsterdam

RESULT
Working local SSL3 transport plus bounded initial FESL request/response
service. Packaged container build EXIT 0; seven integration tests PASS.
GO for controlled server-only experiments. NO-GO for Kane's Wrath acceptance.
No game launched, no DLL injected/loaded into the game, no antivirus changes,
no quarantine restoration, no game writes, no commit/push/issue closure.
The router/launcher build phase was not repeated.

IMPLEMENTATION
server.py replaces neither gateway/fesl-probe.js nor the existing laboratory.
It is a separate executable service listening ONLY on IPv4 127.0.0.1:18760.
No forwarding, DNS lookup or outbound service connection is performed.
Maximum four concurrent connections; four-second socket timeout, maximum
8192-byte FESL frame, 16 requests per connection, bounded record/handshake
buffers. Partial TCP headers, partial handshake messages and coalesced FESL
frames are reassembled. Worker connection IDs are stable and distinct.

TLS: SSL3 only, TLS_RSA_WITH_RC4_128_SHA (0x0005) only, RSA key exchange.
tlslite-ng==0.8.2 and cryptography==44.0.3; Python 3.12.16 in tested image.
SSL3/RC4 are confined to this loopback compatibility laboratory.

Identity: own generated RSA-2048 key, e=65537, self-signed X.509 v3,
SHA256-with-RSA, CN=KWDS Local Lab, SAN localhost/127.0.0.1, CA=false,
seven-day validity. Persisted cert.pem/key.pem in explicit private directory,
never in source or logs. POSIX permissions 0700 directory / 0600 key; on
Windows use a user-private directory with restricted NTFS permissions.
Existing incomplete, mismatched, expired, non-RSA or invalid self-signed
identities cause startup failure. Identity is reused, not silently replaced.
Tests generate temporary identities, explicitly pin the server certificate
fingerprint and remove the private material after the tests. No EA key is
required. No assertion of trust by the original game is made.

FESL: four ASCII type bytes, uint32 big-endian ID, uint32 big-endian total
length including 12-byte header, newline-separated key=value payload;
outgoing payload has final NUL, incoming final NUL is optional. Duplicate
fields, malformed TXN, embedded NUL and oversized frames are rejected.
Type and complete ID word are preserved on responses. fsys/Hello returns
laboratory domain/time/timeout metadata; fsys/Ping is echoed. Other requests,
including account login, get explicit laboratory unsupported error 101.
That error value is a lab convention, not a verified EA/KW error mapping.
No authentication, account storage, login success, theater, lobby or gameplay
is implemented. Hello advertises only loopback addresses, with unavailable
messenger/theater ports set to zero. The KW domain/subdomain, header ID flag
semantics, final-NUL convention, Ping and these Hello fields require a future
real-client check. Port zero must not be mistaken for a working theater.
No invented success is returned for unsupported services.

This is a complete runnable SSL3 + initial-FESL test service, not a complete
EA backend or a claim that every request the game will need is implemented.
The historical game never reached decrypted FESL, so its first TXN and exact
required response remain unknown. Expand the dialogue only from evidence
within issue #4; do not infer login/lobby acceptance from this fixture.

PRIMARY REFERENCE AND LIMIT
https://github.com/abarichello/bfheroesFesl/blob/master/README.md
The project's protocol notes describe a 12-byte FESL header, newline fields,
Hello and response type/ID correlation. They concern Battlefield Heroes,
not Kane's Wrath; they guide this fixture, not KW compatibility proof.
Own implementation; no third-party server code copied into this service.

REPRODUCE THE TESTED PACKAGE (PowerShell from this directory)
docker build --network none --pull=false --build-arg LAB_BASE=kwds-ssl3-lab:rsa-only -t kwds-issue4-fesl:20261108 .
docker run --rm --network none --read-only --tmpfs /tmp:rw,noexec,nosuid,size=16m --cap-drop ALL --security-opt no-new-privileges kwds-issue4-fesl:20261108

These commands use the existing local laboratory image as dependency base,
without downloads. evidence-20261108 records both image IDs and versions.
On a clean machine, the default Dockerfile starts from python:3.12-slim and
installs requirements.txt; that online fresh-base path was NOT exercised.
Base image tags can move: retain the recorded tested image digest locally.
Container tests have --network none: all TCP tests use its private loopback,
no published ports. They do not leave a server or container running.

RUN THE SERVICE ON WINDOWS LOOPBACK (for future controlled use)
Use Python 3.12 and a user-private environment outside the repository:
py -3.12 -m venv "$env:LOCALAPPDATA\KWDS-SSL3-Lab\venv"
& "$env:LOCALAPPDATA\KWDS-SSL3-Lab\venv\Scripts\python.exe" -m pip install -r requirements.txt
& "$env:LOCALAPPDATA\KWDS-SSL3-Lab\venv\Scripts\python.exe" -u server.py --identity "$env:LOCALAPPDATA\KWDS-SSL3-Lab\identity" --port 18760
Stop with Ctrl+C. To test that Python environment without the game:
& "$env:LOCALAPPDATA\KWDS-SSL3-Lab\venv\Scripts\python.exe" test_lab.py
The Windows Python3.12/venv path is documented but NOT executed in this run;
the actual executed runtime was the Linux container with the versions above.
No Windows Python3.12 availability is assumed. The host currently has 3.14
without tlslite installed. No global packages were changed.
Check port ownership first; never stop an unrelated process or replace a
listener silently. A Docker container bound to its own 127.0.0.1 cannot be
used by the Windows game through port publishing. Use native Windows Python
for that future live test; do not widen this service's bind address.

ACTUAL TESTS (seven test methods, packaged-tests.txt)
1. Deliberate raw-client EOF after ServerHelloDone: server reports
   TLSAbruptCloseError, survives and handles subsequent connections.
2. SSL3/0x0005 full handshake with pinned own certificate; encrypted Hello,
   split header, coalesced Ping; matching IDs; unsupported NuLogin rejection.
   A sentinel password is asserted absent from server events.
3. Identity reload retains fingerprint; wildcard bind is refused.
4. Oversized frame and embedded NUL rejected after encrypted handshake.
5. Successful trace contains ClientKeyExchange, ChangeCipherSpec and
   handshake_complete, followed by encrypted application data.
6. One-byte TCP fragmentation and split/coalesced handshake messages traced;
   after ChangeCipherSpec ciphertext is never decoded as handshake messages.
7. No common cipher (3DES-only client) fails; TLS1-only client cannot complete
   a session. In the latter case the server offers SSL3 and client alerts 70;
   this is client rejection of a lower version, not a server early alert.

Initial integration run exposed rejection of legitimate [] field names.
Fixed the field-name validator and reran: 7/7 PASS. Packaged final version
also 7/7 PASS. No syntax-only success substituted for integration tests.

OBSERVED HISTORICAL GAME WIRE EXCHANGE
Prior evidence remains unmodified:
research/client-adapter/issue4-evidence-20261108/historical-handshake.txt
and historical-sha1-handshake.txt (paths relative to repository).
c2s: SSL3 record 47 bytes, ClientHello.
s2c: ServerHello (42), Certificate (740), ServerHelloDone (4).
c2s: TCP EOF; no recorded ClientKeyExchange, CCS or TLS alert.
SHA1 variant: Certificate record 825 bytes; same EOF and failure class.
The old trace logged only the first handshake type in each record. It did
not dump payloads, full cipher lists, alert values or certificate DER.
The original lab source limits negotiation to SSL3/RSA/RC4/SHA. That alone
does NOT prove the full suite list offered by the game. The saved trace
establishes record version 3.0, not every ClientHello field.
Original lab: self-signed RSA2048, SHA256, CN KWDS Local SSL3 Laboratory,
one-day validity, no explicitly added X.509 extensions; closes after handshake.
Old SHA1 variant generates own self-signed RSA2048 via openssl req -x509.
No certificate DER from those sessions was saved, so do not claim a current
fingerprint/serial/validity window for those historical ephemeral identities.

PROVEN ERRORS VERSUS HYPOTHESES
Proven: gateway probe cannot complete TLS; old lab cannot respond to FESL;
historical client closes before key exchange; SHA1-only change did not fix it.
TLSAbruptCloseError describes the socket ending, not a TLS certificate error.
A raw controlled client reproduces it without evaluating certificate trust.
Unproven: trust-key pin mismatch, certificate profile/parser limits, runtime
Tacitus replacement key, key-size constraint, hook timing and game-internal
error. No speculative trust patch or validation bypass has been added.

LATER LIVE TEST: RELEASE GATE AND EXACT CHECKPOINTS
Do NOT execute these game steps until both incident clearance and explicit
user permission for game execution/adapter injection have been obtained.
1. Review F-Secure incident provenance and vendor/security verdict without
   restoring quarantine or creating exceptions. Preserve prior evidence.
2. Snapshot game file manifest, configuration, installed middleware and hashes.
   Verify original RetailExe/1.2/cnc3ep1.dat SHA256 remains
   14CE459E52366A176CC4B9F1E659089D19DA22404060481B61A1CB35C00286AD.
   Do not restore the differently hashed existing .bak.
3. Establish a tested native Python3.12 environment as above. Record Python
   version, requirements, code hashes and certificate metadata fingerprint.
   Start server with a fresh timestamped output log; require ready event and
   confirm listener owner/local address with Get-NetTCPConnection.
4. The following launch is ONLY a future authorized operation:
   & '<verified-x86-launcher-path>' '<game>\RetailExe\1.2\cnc3ep1.dat' '<verified-x86-router-path>' local-fesl
   Record PID/start time, executable path and original hash. Correlate that
   PID's TCP local/remote ports to server connection order and timestamps.
5. Inspect that exact process's loaded main module path/base/size and the
   loaded adapter and Tacitus/dsound modules. Record paths/hashes. The current
   observer inspects the main module at RVA 0x006BA900; this is insufficient
   to prove which trust code/module actually validates the certificate.
6. Preserve kwds-tcp-router-<PID>.log and require hook-active BEFORE the first
   login/network action. Correlate dns-local-redirect or fesl-redirect with
   server connection_open. If hooks activate too late, stop and diagnose
   timing before changing trust behavior. Do not infer acceptance from DNS.
7. Require logged ClientHello version/suites; ServerHello, Certificate,
   ServerHelloDone; then real ClientKeyExchange, both CCS and a successful
   handshake_complete event. Encrypted Finished is verified by TLS handshake
   completion, never by interpreting its ciphertext's first byte.
8. Only after handshake completion inspect a safe metadata description of
   the real first FESL request, response type/ID and TXN. Default logs redact
   IDs and payload. Add narrowly reviewed metadata logging if an unknown
   TXN prevents diagnosis; never log credentials. The current response is a
   fixture and must be checked against actual client acceptance/UI behavior
   and the next client request. A written server response alone is not proof.
9. Stop only owned test processes. Launch without adapter only if separately
   authorized; verify original hash and full snapshot manifest, configuration
   and routing unchanged. Never restore quarantined DLLs. Preserve logs.

DIAGNOSIS PLAN FOR EOF AFTER SERVERHELLODONE
A. First prove PID/build/module and hook readiness as above, then record the
   actual offered suites and the served own certificate profile. Without
   ClientKeyExchange do not debug FESL application framing as root cause.
B. Distinguish explicit TLS Alert (numeric level/description), EOF, reset,
   timeout and process exit. The new trace logs cleartext alerts and catches
   exception class without leaking payload. Preserve server connection order
   and correlate timestamps/PID from the Windows process/launcher evidence.
C. Locate the active verifier and RSA trust identity using read-only runtime
   inspection after authorization. A known key pattern at an RVA establishes
   bytes, not execution of the validation path. Do not infer EA private key
   availability or replace validation generally.
D. Compare own-certificate variants one variable per run only after a baseline:
   key size (2048 vs 1024), signature hash, extensions/encoding, validity/CN.
   Use independent own identities and record fingerprints. Old SHA1 test was
   already negative; it does not by itself eliminate all certificate issues.
   A change accepted by a controlled client proves only that server variant.
E. If trust pin mismatch is directly established, report the narrow reversible
   adaptation needed and seek its specific authorization before any memory
   modification. The present service cannot establish game trust by itself.
F. Once ClientKeyExchange appears, compare negotiated premaster version,
   server key match and alert progression; once handshake completes, diagnose
   the actual FESL transaction and response acceptance independently.

EVIDENCE AND FINAL ACCEPTANCE
evidence-20261108/integration-tests.txt: pre-package corrected integration run.
evidence-20261108/packaged-tests.txt: final packaged run, 7 tests OK, wire events.
image-build.txt, runtime-image.txt, packaged-image.txt, runtime-versions.txt,
source-hashes.json: exact local package/runtime identity and verification.
No private keys, randoms, session IDs, credentials or decrypted payloads saved.
Old evidence was preserved. No long-running listener left active by tests.

Issue #4 remains OPEN and NO-GO for official acceptance: no new real-client
handshake, no real-client-accepted FESL response, no authorized runtime
rollback test. Human security review and explicit live-test permission remain
required. A successful controlled-client handshake cannot clear either gate.

NATIVE WINDOWS UPDATE — 2026-11-08
The native Windows environment is now prepared and its targeted SSL3/FESL
loopback scenario passed on Python 3.14.4 in an isolated venv. See
native-evidence-20261108/final-acceptance-preparation.txt for the actual
environment, preserved failed attempts, PASS evidence, DLL provenance and
ready-to-use native start/live-diagnosis commands. Start-NativeLab.ps1 starts
only the loopback lab; it never launches the game or loads an adapter.
Earlier statements above about native testing not yet being performed describe
the prior assessment and are superseded by this update. Security clearance
and explicit live-test permission are still absent.

CONSOLIDATED ACCEPTANCE UPDATE — 2026-11-08
See research/client-adapter/issue4-final-assessment-20261108-025930/
consolidated-acceptance-report.txt (repository-relative) for the current
security gate and complete acceptance status. The latest user instruction
conditionally authorizes a live test after adequate security assessment;
older statements that all live-test permission is absent are superseded.
The security gate is still NOT satisfied: new vendor metadata identifies
the suspect DLL SHA256 and records exclusion additions. No exclusion was
changed or relied upon. No new game/adapter execution occurred. Prior
build, container and native successes were preserved without repetition.

CONTROLLED LIVE UPDATE — 2026-11-08
See research/client-adapter/issue4-live-evidence-20261108-031053/
final-live-acceptance-report.txt for the consolidated outcome. Real-client
attempts were performed; official acceptance remains NO-GO. Runtime trust,
certificate-return diagnostics, exact-game import routing and minimal local
HTTP bootstrap were added as experimental candidates. No actual real-game
ClientKeyExchange or accepted decrypted FESL response was proven. Computer
Use was stopped by the user; owned test processes were stopped and gateway
restored. gp.info and Tacitus.log differ from baseline; original executable
and other compared installation files match. No commit or push performed.

POST-INTERRUPTION NON-GAME UPDATE — 2026-11-08
Current report: research/client-adapter/issue4-offline-repair-20261108-035426/offline-repair-report.txt.
New bounded classifier and HEAD support; maps-65536.txt is an empty reference
fixture. drivers.txt is explicitly unresolved (501), not a fabricated 200.
Six focused controlled tests pass. Snapshot restoration tested on temporary
files only. New launcher refuses local-fesl while non-loopback adapters are
operational (current host: exit22). Socket hooks alone do not isolate all
TCP/UDP/middleware paths. Use the NEW launcher and a separately isolated
environment; renewed game/Computer Use permission remains required.
No new game session was run. Official issue4 acceptance remains NO-GO.

DEVELOPMENT CONTINUATION — 2026-11-08
See research/client-adapter/issue4-development-20261108-1620/development-report.txt.
Changed classifier/handler preserve numeric TLS-alert origin, phase, transport
EOF/reset and served certificate identity without payload/error-message logging.
Snapshot restores prevalidate all manifest paths and indices before mutation;
root junctions and changing empty-directory inventories now fail closed.
Eight new targeted checks and three affected integrations PASS; Python compile
PASS. No unchanged native/container builds repeated. No game or injection.
Original sealed package retained; separate reviewed offline source overlay
prepared and hash/config checked, not executed in a guest. drivers501 and real
local verifier/handshake acceptance remain unresolved. Issue4 remains NO-GO.

DEFINITIEVE GEISOLEERDE LIVE-ACCEPTATIE — 2026-11-08
Current report: research/client-adapter/issue4-sandbox-execution-20261108/final-live-acceptance-report.txt.
GO for issue4 client connection/reversible adapter feasibility. Real gamePID7632
verifier0; actual SSL3 ClientKeyExchange, bothCCS, encrypted handshake, decrypted
Hello, client MemCheck reply and subsequent Login prove initial FESL acceptance.
No account-authentication/lobby/multiplayer success claimed; Login stays an
explicit laboratory rejection. Host1979files unchanged; guest four-root restore
PASS; owned processes/listener stopped. Original sealed package preserved.
For KW the own leaf CN must be fesl.ea.com in the tested runtime. Use the exact
known-build runtime own-public-key option; stock EA trust is not demonstrated.
FESL responses now use server tag0x80 and Hello followed by empty MemCheck,
subDomaincnc3ep1. Only bounded header/transaction metadata is logged.
--driver-reference-fixture explicitly opts into exact pinned13byte Kirov fixture;
default drivers501 remains. New separate accepted overlay receipt in evidence.
Old findings/logs remain preserved; old NOT RUN/NO-GO statuses above are historical.
No commit, push, merge or GitHub issue modification performed.
