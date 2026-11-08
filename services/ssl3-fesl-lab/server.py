"""Loopback-only SSL3 + initial FESL dialogue laboratory; no authentication."""
import argparse
import ipaddress
import json
import re
import secrets
import socket
import socketserver
import struct
import threading
from tlslite.errors import TLSLocalAlert, TLSRemoteAlert
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.x509.oid import NameOID
from tlslite import TLSConnection, HandshakeSettings, X509, X509CertChain, parsePEMKey

MAX_FRAME = 8192
TIMEOUT = 4
NAMES = {1: "ClientHello", 2: "ServerHello", 11: "Certificate",
         14: "ServerHelloDone", 16: "ClientKeyExchange", 20: "Finished"}


def settings():
    s = HandshakeSettings()
    s.minVersion = s.maxVersion = (3, 0)
    s.cipherNames, s.macNames, s.keyExchangeNames = ["rc4"], ["sha"], ["rsa"]
    return s


def identity(directory, bits=2048):
    """Create once, reload and verify matching local RSA identity. Never print keys."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    cp, kp = directory / "cert.pem", directory / "key.pem"
    if cp.exists() != kp.exists():
        raise ValueError("incomplete identity; refusing overwrite")
    if not cp.exists():
        key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "KWDS Local Lab")])
        now = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                .public_key(key.public_key()).serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(minutes=5))
                .not_valid_after(now + timedelta(days=7))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
                .add_extension(x509.SubjectAlternativeName([
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    x509.DNSName("localhost")]), False)
                .sign(key, hashes.SHA256()))
        # Exclusive creates prevent silently replacing an existing identity.
        with kp.open("xb") as f:
            kp.chmod(0o600)
            f.write(key.private_bytes(serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption()))
        with cp.open("xb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
    cert = x509.load_pem_x509_certificate(cp.read_bytes())
    key = serialization.load_pem_private_key(kp.read_bytes(), password=None)
    if not isinstance(key, rsa.RSAPrivateKey) or not isinstance(cert.public_key(), rsa.RSAPublicKey):
        raise ValueError("RSA identity required")
    if cert.public_key().public_numbers() != key.public_key().public_numbers():
        raise ValueError("certificate/key mismatch")
    issuer_path = directory / "issuer.pem"
    issuer = x509.load_pem_x509_certificate(issuer_path.read_bytes()) if issuer_path.exists() else cert
    if cert.issuer != issuer.subject or issuer.subject != issuer.issuer:
        raise ValueError("local certificate issuer mismatch")
    if not isinstance(issuer.public_key(), rsa.RSAPublicKey):
        raise ValueError("RSA issuer required")
    issuer.public_key().verify(issuer.signature, issuer.tbs_certificate_bytes,
                              padding.PKCS1v15(), issuer.signature_hash_algorithm)
    issuer.public_key().verify(cert.signature, cert.tbs_certificate_bytes,
                              padding.PKCS1v15(), cert.signature_hash_algorithm)
    if issuer_path.exists() and not issuer.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
        raise ValueError("issuer must be a CA")
    if not issuer.not_valid_before_utc <= datetime.now(timezone.utc) <= issuer.not_valid_after_utc:
        raise ValueError("issuer expired or not yet valid")
    now = datetime.now(timezone.utc)
    if not cert.not_valid_before_utc <= now <= cert.not_valid_after_utc:
        raise ValueError("certificate expired or not yet valid")
    tc = X509().parse(cp.read_text())
    info = dict(fingerprint=cert.fingerprint(hashes.SHA256()).hex(),
                rsa_bits=key.key_size, exponent=key.public_key().public_numbers().e,
                signature=cert.signature_hash_algorithm.name, x509_version=cert.version.name,
                not_after=cert.not_valid_after_utc.isoformat(), self_signed=(cert.subject == cert.issuer),
                issuer_fingerprint=issuer.fingerprint(hashes.SHA256()).hex())
    return X509CertChain([tc]), parsePEMKey(kp.read_text(), private=True), info


class Trace:
    """TCP and handshake reassembly; never interpret encrypted Finished as plaintext."""
    def __init__(self, emit, direction):
        self.emit, self.direction = emit, direction
        self.pending, self.handshake = bytearray(), bytearray()
        self.encrypted = False
        self.count = 0

    def feed(self, data):
        self.pending.extend(data)
        while len(self.pending) >= 5:
            kind, major, minor, n = struct.unpack("!BBBH", self.pending[:5])
            if n > 18432:
                raise ValueError("oversized TLS record")
            if len(self.pending) < n + 5:
                return
            body = bytes(self.pending[5:5+n])
            del self.pending[:5+n]
            self.count += 1
            if self.count > 256:
                raise ValueError("record limit")
            self.emit("record", direction=self.direction, kind=kind,
                      version=[major, minor], length=n, encrypted=self.encrypted)
            if kind == 21 and not self.encrypted and len(body) == 2:
                self.emit("alert", direction=self.direction, level=body[0], description=body[1])
            if kind == 20:
                self.encrypted = True
            if kind != 22 or self.encrypted:
                continue
            self.handshake.extend(body)
            if len(self.handshake) > 65536:
                raise ValueError("handshake limit")
            while len(self.handshake) >= 4:
                size = int.from_bytes(self.handshake[1:4], "big")
                if size > 65532:
                    raise ValueError("handshake message limit")
                if len(self.handshake) < size + 4:
                    break
                code = self.handshake[0]
                msg = bytes(self.handshake[4:4+size])
                del self.handshake[:4+size]
                self.emit("handshake_message", direction=self.direction,
                          message=NAMES.get(code, "Other"), code=code, length=size)
                if code == 1 and len(msg) >= 35:
                    pos = 35 + msg[34]
                    if pos + 2 <= len(msg):
                        n = int.from_bytes(msg[pos:pos+2], "big")
                        if n % 2 == 0 and pos+2+n < len(msg):
                            suites = [int.from_bytes(msg[i:i+2], "big")
                                      for i in range(pos+2, pos+2+n, 2)]
                            self.emit("client_hello", version=list(msg[:2]), suites=suites[:64])


def error_metadata(error):
    """Only typed numeric metadata; exception messages may contain input data."""
    fields = {"error": type(error).__name__}
    for name in ("errno", "winerror"):
        value = getattr(error, name, None)
        if isinstance(value, int): fields[name] = value
    if isinstance(error, (TLSLocalAlert, TLSRemoteAlert)):
        fields["alert_source"] = "server" if isinstance(error, TLSLocalAlert) else "peer"
        for name in ("description", "level"):
            value = getattr(error, name, None)
            if type(value) is int and 0 <= value <= 255: fields["alert_"+name] = value
    return fields


class TracedSocket:
    def __init__(self, raw, emit):
        self.raw, self.emit = raw, emit
        self.incoming, self.outgoing = Trace(emit, "c2s"), Trace(emit, "s2c")
    def __getattr__(self, name):
        return getattr(self.raw, name)
    def recv(self, size, *args):
        try:
            data = self.raw.recv(size, *args)
        except OSError as error:
            self.emit("transport_error", direction="c2s", **error_metadata(error))
            raise
        if not data: self.emit("transport_eof", direction="c2s")
        self.incoming.feed(data)
        return data
    def send(self, data, *args):
        n = self.raw.send(data, *args)
        self.outgoing.feed(bytes(data[:n]))
        return n
    def sendall(self, data, *args):
        self.raw.sendall(data, *args)
        self.outgoing.feed(bytes(data))


def encode(kind, ident, fields):
    body = "".join(f"{k}={v}\n" for k, v in fields.items()).encode("ascii") + b"\0"
    if len(body) + 12 > MAX_FRAME:
        raise ValueError("frame too large")
    return struct.pack("!4sII", kind, ident, len(body)+12) + body


def exact(conn, size):
    result = bytearray()
    while len(result) < size:
        chunk = conn.read(min=size-len(result), max=size-len(result))
        if not chunk:
            if not result:
                raise EOFError()
            raise ValueError("truncated frame")
        result.extend(chunk)
    return bytes(result)


def read_frame(conn):
    kind, ident, size = struct.unpack("!4sII", exact(conn, 12))
    if not re.fullmatch(rb"[A-Za-z0-9]{4}", kind) or not 12 < size <= MAX_FRAME:
        raise ValueError("invalid frame header")
    body = exact(conn, size-12)
    if body.endswith(b"\0"):
        body = body[:-1]
    if b"\0" in body:
        raise ValueError("embedded null")
    fields = {}
    for line in body.decode("ascii").splitlines():
        if not line:
            continue
        k, sep, v = line.partition("=")
        if not sep or not re.fullmatch(r"[A-Za-z0-9_.{}\[\]]+", k) or k in fields:
            raise ValueError("invalid field")
        fields[k] = v
    if not re.fullmatch(r"[A-Za-z0-9]{1,48}", fields.get("TXN", "")):
        raise ValueError("invalid transaction")
    return kind, ident, fields


def response(kind, fields):
    txn = fields["TXN"]
    if kind == b"fsys" and txn == "Hello":
        return dict(TXN=txn, **{
            "domainPartition.domain": "eagames",
            "domainPartition.subDomain": "cnc3ep1",
            "curTime": datetime.now(timezone.utc).strftime('"%b-%d-%Y %H:%M:%S UTC"'),
            "activityTimeoutSecs": "0", "messengerIp": "127.0.0.1",
            "messengerPort": "0", "theaterIp": "127.0.0.1", "theaterPort": "0"})
    if kind == b"fsys" and txn == "Ping":
        return {"TXN": txn}
    # An explicit lab rejection, not fabricated login success or an EA error claim.
    return {"TXN": txn, "errorCode": "101", "errorContainer.[]": "0",
            "localizedMessage": "KWDS laboratory: transaction unsupported"}


class Lab(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = False

    def __init__(self, address, cert_identity, emit=None, bootstrap_bodies=None):
        if not ipaddress.ip_address(address[0]).is_loopback:
            raise ValueError("loopback bind required")
        self.chain, self.key, self.info = cert_identity
        self.bootstrap_bodies = dict(BOOTSTRAP_BODIES if bootstrap_bodies is None else bootstrap_bodies)
        sink = emit or (lambda event, **kw: print(json.dumps(dict(event=event, **kw)), flush=True))
        self.emit = lambda event, **kw: sink(event, time=datetime.now(timezone.utc).isoformat(), **kw)
        self.slots = threading.BoundedSemaphore(4)
        self.counter = 0
        self.request_ids = {}
        super().__init__(address, Handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        self.counter += 1
        self.request_ids[request] = self.counter
        try:
            super().process_request(request, address)
        except BaseException:
            self.request_ids.pop(request, None)
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.request_ids.pop(request, None)
            self.slots.release()


from bootstrap import classify, serve_bootstrap, DRIVER_REFERENCE

BOOTSTRAP_BODIES = {
    "config.txt": "<QMMaps>\n</QMMaps>\n<Manglers>\n</Manglers>\n<PingServers>\n127.0.0.1\n</PingServers>\n<PingDuration>\nreps = 0\ntimeout = 1000\nlow = 100\nmed = 400\n</PingDuration>\n<Ladders>\n</Ladders>\n<VIP>\n</VIP>\n<Custom>\nrestricted = 1\n</Custom>\n",
    "languages.txt": "dutch\nenglish\n",
    "MOTD-dutch.txt": "KWDS local compatibility test\n",
    "MOTD-english.txt": "KWDS local compatibility test\n",
}

class Handler(socketserver.BaseRequestHandler):
    def handle(self):
        cid = self.server.request_ids[self.request]
        emit = lambda event, **kw: self.server.emit(event, connection=cid, **kw)
        self.request.settimeout(TIMEOUT)
        conn = None
        phase = "classification"
        emit("connection_open", peer=list(self.client_address), local=list(self.request.getsockname()),
             certificate_sha256=self.server.info["fingerprint"],
             issuer_sha256=self.server.info["issuer_fingerprint"])
        try:
            protocol, wire = classify(self.request, emit)
            if protocol == "http":
                phase = "bootstrap"
                serve_bootstrap(wire, emit, self.server.bootstrap_bodies)
                return
            if protocol != "tls":
                emit("connection_rejected", protocol=protocol)
                return
            conn = TLSConnection(TracedSocket(wire, emit))
            phase = "handshake"
            conn.handshakeServer(certChain=self.server.chain, privateKey=self.server.key, settings=settings())
            if conn.version != (3, 0) or conn.session.cipherSuite != 5:
                raise ValueError("unexpected negotiation")
            emit("handshake_complete", version=list(conn.version), suite=conn.session.cipherSuite)
            phase = "fesl"
            for _ in range(16):
                kind, ident, fields = read_frame(conn)
                txn = fields["TXN"] if fields["TXN"] in ("Hello", "Ping", "MemCheck", "NuLogin", "Login") else "Other"
                # Header metadata is bounded; never emit field values or credentials.
                emit("fesl_request", transaction=txn, command=kind.decode("ascii"),
                     tag=ident >> 24, sequence=ident & 0x00ffffff)
                if kind == b"fsys" and txn == "MemCheck":
                    # This is the reply to our empty protocol challenge, not an
                    # attestation of anti-cheat or arbitrary memory inspection.
                    continue
                reply_id = 0x80000000 | (ident & 0x00ffffff)
                conn.write(encode(kind, reply_id, response(kind, fields)))
                emit("fesl_response", transaction=txn, tag=0x80, sequence=reply_id & 0x00ffffff)
                if kind == b"fsys" and txn == "Hello":
                    # Kirov's pinned KW protocol: Hello reply followed by a
                    # server-initiated MemCheck, packet0, with no memory ranges.
                    conn.write(encode(b"fsys", 0x80000000, {
                        "TXN": "MemCheck", "type": "0",
                        "salt": str(secrets.randbits(32)), "memcheck.[]": "0"}))
                    emit("fesl_response", transaction="MemCheck", tag=0x80, sequence=0)
        except EOFError:
            emit("peer_eof", phase=phase)
        except Exception as error:
            emit("connection_error", phase=phase, **error_metadata(error))
        finally:
            try:
                if conn is not None: conn.close()
            except Exception:
                pass
            self.request.close()
            emit("connection_closed", phase=phase)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", type=int, default=18760)
    p.add_argument("--identity", type=Path, required=True, help="private local directory outside the repository")
    p.add_argument("--driver-reference-fixture", action="store_true", help="Research only: exact upstream driver bytes; compatibility unverified")
    args = p.parse_args()
    bodies = dict(BOOTSTRAP_BODIES)
    if args.driver_reference_fixture: bodies["drivers.txt"] = DRIVER_REFERENCE
    with Lab(("127.0.0.1", args.port), identity(args.identity), bootstrap_bodies=bodies) as lab:
        lab.emit("ready", host="127.0.0.1", port=lab.server_address[1], identity=lab.info,
                 driver_resource="pinned-reference-unverified" if args.driver_reference_fixture else "unresolved-501")
        try:
            lab.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
