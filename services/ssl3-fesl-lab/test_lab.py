"""Real loopback transport tests with controlled clients, never the game."""
import hashlib
import json
import os
import socket
import struct
import tempfile
import threading
import time
import unittest
from pathlib import Path
from tlslite import TLSConnection
from server import Lab, Trace, encode, identity, read_frame, settings


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="kwds-lab-")
        cls.directory = Path(cls.temp.name)
        cls.ident = identity(cls.directory)
        cls.events = []
        cls.lab = Lab(("127.0.0.1", 0), cls.ident,
                      lambda event, **kw: cls.events.append(dict(event=event, **kw)))
        cls.thread = threading.Thread(target=cls.lab.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.lab.shutdown()
        cls.lab.server_close()
        cls.thread.join(5)
        # Logs contain protocol metadata only, no decrypted input or private material.
        print("SERVER_EVENTS=" + json.dumps(cls.events), flush=True)
        cls.temp.cleanup()

    def connect(self, config=None):
        raw = socket.create_connection(self.lab.server_address, timeout=6)
        c = TLSConnection(raw)
        try:
            c.handshakeClientCert(settings=config or settings())
        except BaseException:
            raw.close()
            raise
        self.addCleanup(c.close)
        self.assertEqual(c.version, (3, 0))
        self.assertEqual(c.session.cipherSuite, 5)
        # Explicit pin check for this test identity; no EA trust inference.
        der = bytes(c.session.serverCertChain.x509List[0].bytes)
        self.assertEqual(hashlib.sha256(der).hexdigest(), self.ident[2]["fingerprint"])
        return c

    def test_hello_ping_and_unsupported_encrypted(self):
        c = self.connect()
        hello = encode(b"fsys", 0xc0000001, {"TXN": "Hello", "clientString": "controlled-test"})
        # A split header plus coalesced requests exercise stream framing.
        c.write(hello[:3])
        c.write(hello[3:] + encode(b"fsys", 0xc0000002, {"TXN": "Ping"}))
        kind, ident, fields = read_frame(c)
        self.assertEqual((kind, ident, fields["TXN"]), (b"fsys", 0x80000001, "Hello"))
        self.assertEqual(fields["theaterIp"], "127.0.0.1")
        self.assertEqual(fields["domainPartition.subDomain"], "cnc3ep1")
        self.assertTrue(fields["curTime"].startswith('"') and fields["curTime"].endswith('"'))
        mkind, mid, mfields = read_frame(c)
        self.assertEqual((mkind, mid, mfields["TXN"], mfields["memcheck.[]"]),
                         (b"fsys", 0x80000000, "MemCheck", "0"))
        self.assertEqual(read_frame(c), (b"fsys", 0x80000002, {"TXN": "Ping"}))
        c.write(encode(b"fsys", 0x80000000, {"TXN": "MemCheck", "result": ""}))
        c.write(encode(b"acct", 0xc0000007, {"TXN": "NuLogin", "password": "SENTINEL_NEVER_LOG"}))
        rkind, rid, rfields = read_frame(c)
        self.assertEqual((rkind, rid, rfields["TXN"], rfields["errorCode"]),
                         (b"acct", 0x80000007, "NuLogin", "101"))
        self.assertNotIn("SENTINEL_NEVER_LOG", json.dumps(self.events))

    def test_invalid_and_oversized_frames_close_without_response(self):
        for body in (struct.pack("!4sII", b"fsys", 1, 999999),
                     encode(b"fsys", 2, {"TXN": "Hello"}).replace(b"TXN=Hello", b"TXN=H\0llo")):
            c = self.connect()
            c.write(body)
            try:
                self.assertEqual(c.read(min=1, max=1), b"")
            except Exception as error:
                self.assertIn(type(error).__name__, ("TLSAbruptCloseError", "TLSRemoteAlert"))

    def test_wrong_cipher_and_version_rejected(self):
        for variant in ("cipher", "version"):
            s = settings()
            if variant == "cipher":
                s.cipherNames = ["3des"]
            else:
                s.minVersion = s.maxVersion = (3, 1)
            with self.assertRaises(Exception):
                self.connect(s)

    def test_abrupt_close_after_server_hello_done(self):
        start = len(self.events)
        raw = socket.create_connection(self.lab.server_address, timeout=5)
        try:
            hello = b"\x03\x00" + os.urandom(32) + b"\0\0\x02\0\x05\x01\0"
            message = b"\x01" + len(hello).to_bytes(3, "big") + hello
            raw.sendall(b"\x16\x03\x00" + len(message).to_bytes(2, "big") + message)
            observed = []
            trace = Trace(lambda event, **kw: observed.append(dict(event=event, **kw)), "s2c")
            while not any(e.get("message") == "ServerHelloDone" for e in observed):
                chunk = raw.recv(8192)
                self.assertTrue(chunk)
                trace.feed(chunk)
        finally:
            raw.close()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not any(
                e.get("error") == "TLSAbruptCloseError" for e in self.events[start:]):
            time.sleep(.02)
        self.assertTrue(any(e.get("error") == "TLSAbruptCloseError" for e in self.events[start:]))

    def test_identity_reload_and_no_external_bind(self):
        self.assertEqual(identity(self.directory)[2], self.ident[2])
        with self.assertRaisesRegex(ValueError, "loopback"):
            Lab(("0.0.0.0", 18760), self.ident)

    def test_trace_reassembles_and_stops_decoding_after_ccs(self):
        events = []
        trace = Trace(lambda event, **kw: events.append(dict(event=event, **kw)), "c2s")
        data = b"\x10\0\0\x02ab\x0e\0\0\0"
        record = lambda kind, body: struct.pack("!BBBH", kind, 3, 0, len(body)) + body
        wire = record(22, data[:2]) + record(22, data[2:]) + record(20, b"\x01") + record(22, b"\x10junk")
        for byte in wire:
            trace.feed(bytes([byte]))
        self.assertEqual([e["message"] for e in events if e["event"] == "handshake_message"],
                         ["ClientKeyExchange", "ServerHelloDone"])

    def test_successful_handshake_has_wire_key_exchange_and_ccs(self):
        start = len(self.events)
        c = self.connect()
        c.write(encode(b"fsys", 6, {"TXN": "Ping"}))
        read_frame(c)
        events = self.events[start:]
        self.assertTrue(any(e.get("message") == "ClientKeyExchange" for e in events))
        self.assertTrue(any(e.get("kind") == 20 and e.get("direction") == "c2s" for e in events))
        self.assertTrue(any(e["event"] == "handshake_complete" for e in events))


if __name__ == "__main__":
    unittest.main(verbosity=2)
