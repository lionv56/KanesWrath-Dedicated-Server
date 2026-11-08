"use strict";

const net = require("node:net");

const HEADER_SIZE = 12;
const MAX_FRAME = 4096;
const IDLE_TIMEOUT_MS = 10000;

// Diagnostic decoder only. FESL is normally inside TLS.
// Never store payloads, usernames or credentials.

function inspectTlsClientHello(record) {
  const fail = (reason) => ({ ok: false, reason });
  const version = (major, minor) =>
    `0x${major.toString(16).padStart(2, "0")}${minor.toString(16).padStart(2, "0")}`;

  if (!Buffer.isBuffer(record) ||
      record.length < 9 ||
      record[0] !== 0x16 ||
      record[1] !== 0x03) {
    return fail("not-a-tls-handshake-record");
  }

  const recordLength = record.readUInt16BE(3);

  if (recordLength < 4 || recordLength + 5 !== record.length) {
    return fail("invalid-record-length");
  }

  if (record[5] !== 0x01) {
    return fail("not-clienthello");
  }

  const handshakeLength = record.readUIntBE(6, 3);

  const profile = {
    recordVersion: version(record[1], record[2]),
    helloVersion: null,
    cipherSuites: [],
    cipherSuiteCount: 0,
    compressionMethods: [],
    extensionTypes: [],
    status: "partial"
  };

  if (handshakeLength + 4 > recordLength) {
    profile.status = "fragmented-clienthello";
    return { ok: true, profile };
  }

  const end = 9 + handshakeLength;
  let pos = 9;
  const need = (n) => pos + n <= end;

  if (!need(35)) {
    return fail("short-clienthello");
  }

  profile.helloVersion = version(record[pos], record[pos + 1]);

  // Skip protocol version and 32-byte random.
  // Never retain handshake random or session identifiers.
  pos += 34;

  const sessionIdLength = record[pos++];

  if (sessionIdLength > 32 || !need(sessionIdLength + 2)) {
    return fail("invalid-session-id-length");
  }

  pos += sessionIdLength;

  const cipherBytes = record.readUInt16BE(pos);
  pos += 2;

  if (!cipherBytes || cipherBytes % 2 || !need(cipherBytes + 1)) {
    return fail("invalid-cipher-list");
  }

  profile.cipherSuiteCount = cipherBytes / 2;

  // Store only public cipher-suite identifiers, bounded to 64.
  for (let i = 0; i < cipherBytes && i < 128; i += 2) {
    const code = record.readUInt16BE(pos + i);
    profile.cipherSuites.push(
      `0x${code.toString(16).padStart(4, "0")}`
    );
  }

  pos += cipherBytes;

  const compressionCount = record[pos++];

  if (!compressionCount || !need(compressionCount)) {
    return fail("invalid-compression-list");
  }

  for (let i = 0; i < compressionCount && i < 16; i++) {
    profile.compressionMethods.push(record[pos + i]);
  }

  pos += compressionCount;

  if (pos !== end) {
    if (!need(2)) {
      return fail("invalid-extensions-length");
    }

    const extensionBytes = record.readUInt16BE(pos);
    pos += 2;

    if (pos + extensionBytes !== end) {
      return fail("inconsistent-extensions-length");
    }

    while (pos < end) {
      if (!need(4)) {
        return fail("truncated-extension-header");
      }

      const type = record.readUInt16BE(pos);
      const length = record.readUInt16BE(pos + 2);
      pos += 4;

      if (!need(length)) {
        return fail("truncated-extension");
      }

      if (profile.extensionTypes.length < 32) {
        profile.extensionTypes.push(type);
      }

      pos += length;
    }
  }

  profile.status = "parsed";
  return { ok: true, profile };
}

function createFeslProbe() {
  const state = {
    connections: 0,
    activeConnections: 0,
    observations: 0,
    bytesObserved: 0,
    rejectedConnections: 0,
    feslFrames: 0,
    tlsClientHelloCandidates: 0,
    tlsParseFailures: 0,
    tlsProfiles: [],
    lastConnectionAt: null,
    lastFramingAt: null
  };

  const server = net.createServer((socket) => {
    state.connections++;
    state.activeConnections++;
    state.lastConnectionAt = new Date().toISOString();

    let pending = Buffer.alloc(0);
    let classified = false;
    let observed = false;
    let rejected = false;
    let mode = "unknown";

    function reject() {
      if (!rejected) {
        rejected = true;
        state.rejectedConnections++;
      }
      socket.destroy();
    }

    socket.setTimeout(IDLE_TIMEOUT_MS, () => socket.destroy());

    socket.on("data", (chunk) => {
      if (rejected) return;

      state.bytesObserved += chunk.length;

      if (!observed) {
        observed = true;
        state.observations++;
      }

      // Bound all buffered input. This is a diagnostic endpoint,
      // not a complete TLS or FESL server.
      if (pending.length + chunk.length > MAX_FRAME) {
        reject();
        return;
      }

      pending = Buffer.concat([pending, chunk]);

      if (!classified) {
        if (pending.length < 5) return;

        // TLS handshake record:
        // content type 22, version 0x03xx, record body starts
        // with handshake type 1 for ClientHello.
        if (pending[0] === 0x16 && pending[1] === 0x03) {
          const recordLength = pending.readUInt16BE(3);

          if (recordLength < 1 || recordLength > MAX_FRAME - 5) {
            reject();
            return;
          }

          mode = "tls";
          classified = true;
        }
        else {
          mode = "fesl";
          classified = true;
        }
      }

      if (mode === "tls") {
        if (pending.length < 9) return;

        const recordLength = pending.readUInt16BE(3);

        // The existing MAX_FRAME check bounds total input.
        if (pending.length < recordLength + 5) return;

        const result = inspectTlsClientHello(
          pending.subarray(0, recordLength + 5)
        );

        if (!result.ok) {
          state.tlsParseFailures++;
          reject();
          return;
        }

        state.tlsClientHelloCandidates++;
        state.lastFramingAt = new Date().toISOString();

        state.tlsProfiles.push(result.profile);

        if (state.tlsProfiles.length > 5) {
          state.tlsProfiles.shift();
        }

        // Diagnostic only: no TLS termination or fake response.
        socket.end();
        return;
      }

      // Plaintext FESL is useful for isolated framing tests.
      // Original game traffic may require TLS first.
      while (pending.length >= HEADER_SIZE) {
        const type = pending.toString("ascii", 0, 4);
        const length = pending.readUInt32BE(8);

        if (!/^[A-Za-z0-9]{4}$/.test(type) ||
            length < HEADER_SIZE ||
            length > MAX_FRAME) {
          reject();
          return;
        }

        if (pending.length < length) return;

        // Transaction ID is at bytes 4-7 (big endian).
        // Do not log payload data or transaction contents.
        state.feslFrames++;
        state.lastFramingAt = new Date().toISOString();

        pending = pending.subarray(length);
      }
    });

    socket.on("error", () => {});

    socket.on("close", () => {
      state.activeConnections--;
    });
  });

  server.on("error", (error) => {
    console.error("FESL listener error:", error.code);
    process.exitCode = 1;
  });

  return {
    listen(port, host) {
      server.listen(port, host);
    },

    close() {
      server.close();
    },

    stats() {
      return {
        ...state,
        mode: "framing-diagnostics",
        handshakeImplemented: false,
        tlsTerminationImplemented: false
      };
    }
  };
}

module.exports = { createFeslProbe };