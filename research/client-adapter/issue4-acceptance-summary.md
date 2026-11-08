# Issue #4: Client connection / reversible patch feasibility — GO

Date: 2026-11-08. Tested scope: Kane's Wrath 1.2 exact executable build.

## Real-client proof (isolated Windows Sandbox)

- Genuine client launched using a separately built x86 launcher and local adapter.
- All observed test TCP endpoints were loopback-only (`127.0.0.1:18760`); the Sandbox had networking disabled, with no usable external network adapter or default route.
- Original verifier returned `0` when the separately generated own certificate had `CN=fesl.ea.com` and the narrowly scoped, exact-build, in-memory own-public-key test adaptation was active. No vendor private key was used.
- Real SSL3 ClientHello, ClientKeyExchange, client and server ChangeCipherSpec, encrypted Finished and handshake completion were recorded.
- Decrypted `fsys Hello` was followed by server-tagged Hello + empty MemCheck; the real game answered MemCheck and sent `acct Login`.
- Login was intentionally refused by the laboratory server. Authentication, lobby and multiplayer are **not** accepted.
- Game-profile snapshot and restoration passed; 1,979/1,979 host game files matched the original manifest. Owned test processes stopped.

## Reproducible sources

- Native adapter: `research/client-adapter/kwds-native/` (MSVC x86 / Detours).
- Windows launcher: `apps/launcher/native/` (MSVC x86 / Detours).
- Loopback SSL3/FESL test server, protocol classifier, diagnostics and snapshot tests: `services/ssl3-fesl-lab/`.
- Early FESL identification gateway (not the full authentication backend): `services/gateway/`.

Local acceptance record: `final-live-acceptance-report.txt` under
`research/client-adapter/issue4-sandbox-execution-20261108/` in the private,
**unpublished** test evidence archive. Secret identities, raw run logs, temporary
binaries and the offline Sandbox copy are intentionally excluded from Git.

## Evidence boundary

This is a **client connection feasibility GO**, not a general release. It does
not establish acceptance by a completely unmodified retail/Steam client,
trusted public certificates, a production-ready SSL/TLS design, working
account registration/login, matchmaking, UDP relay, P2P removal or
server-authoritative game simulation. SSL3/RC4/SHA1 behavior remains restricted
to loopback compatibility research, not a secure public service.

Before any further live tests, use a fresh private certificate and an isolated
guest, and recheck trust mapping, snapshot integrity and runtime provenance.
