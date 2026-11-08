"""Bounded wire classification and explicit, evidence-backed bootstrap fixtures."""
import re

METHODS = {b"GET", b"HEAD", b"POST", b"OPTIONS", b"PUT", b"DELETE", b"PATCH", b"CONNECT", b"TRACE"}
PREFIX = "/servserv/cnc3_ep1/"
# Exact 13-byte upstream blob99a9528..., retrieved without UTF-8 replacement.
DRIVER_REFERENCE = bytes.fromhex("7575686577696f366e82700d0a")


class PrefixedSocket:
    def __init__(self, raw, prefix):
        self.raw, self.prefix = raw, bytearray(prefix)
    def __getattr__(self, name):
        return getattr(self.raw, name)
    def recv(self, size, *args):
        if self.prefix:
            n = min(size, len(self.prefix))
            data = bytes(self.prefix[:n]); del self.prefix[:n]
            return data
        return self.raw.recv(size, *args)


def classify(raw, emit):
    # Consume at most eight prefix bytes; replay them to the actual decoder.
    # Never persist bytes, arbitrary method text, query strings or headers.
    prefix = bytearray(raw.recv(1))
    if not prefix:
        emit("wire_classification", protocol="empty")
        return "empty", raw
    if prefix[0] in (20, 21, 22, 23):
        while len(prefix) < 5:
            data = raw.recv(5-len(prefix))
            if not data: break
            prefix.extend(data)
        valid = len(prefix) == 5 and prefix[1] == 3 and 0 < int.from_bytes(prefix[3:5], "big") <= 18432
        protocol = "tls" if valid else "invalid-tls-header"
        emit("wire_classification", protocol=protocol)
        return protocol, PrefixedSocket(raw, prefix)
    if prefix[0] & 128:
        emit("wire_classification", protocol="possible-sslv2-framing")
        return "unsupported", raw
    while len(prefix) < 8 and prefix[-1:] != b" ":
        data = raw.recv(1)
        if not data: break
        prefix.extend(data)
    method = bytes(prefix).rstrip(b" ")
    if prefix[-1:] == b" " and method in METHODS:
        emit("wire_classification", protocol="http", method=method.decode("ascii"))
        return "http", PrefixedSocket(raw, prefix)
    emit("wire_classification", protocol="unknown", inspected_bytes=len(prefix))
    return "unsupported", raw


def serve_bootstrap(raw, emit, bodies):
    data = bytearray()
    while b"\r\n\r\n" not in data:
        if len(data) >= 8192: raise ValueError("bootstrap header limit")
        chunk = raw.recv(min(1024, 8192-len(data)))
        if not chunk: raise ValueError("truncated bootstrap header")
        data.extend(chunk)
    first = bytes(data).split(b"\r\n", 1)[0].decode("ascii")
    method, target, version = first.split(" ", 2)
    if version not in ("HTTP/1.0", "HTTP/1.1"): raise ValueError("HTTP version")
    path = target.split("?", 1)[0]
    name = path[len(PREFIX):] if path.startswith(PREFIX) else ""
    # Unknown paths may contain user data: log only an allowlisted route name.
    known = name in bodies or name in ("maps-65536.txt", "drivers.txt",
             "cnc3ep1_dutch_1.2.patchinfo", "cnc3ep1_english_1.2.patchinfo")
    emit("bootstrap_request", method=method, route=name if known else "unrecognized")
    status, payload = 404, b""
    if method not in ("GET", "HEAD"):
        status = 405
    elif name == "drivers.txt" and name not in bodies:
        # Default remains unresolved. The explicit research fixture is served
        # only when configured; neither mode claims real-client acceptance.
        status = 501
        emit("bootstrap_unresolved", resource="drivers.txt", reason="no-verified-format")
    elif known:
        value = bodies.get(name, "")
        payload = value.encode("ascii") if isinstance(value, str) else value
        status = 200
    reason = {200:"OK", 404:"Not Found", 405:"Method Not Allowed", 501:"Not Implemented"}[status]
    header = (f"HTTP/1.0 {status} {reason}\r\nContent-Type: text/plain\r\n"
              f"Content-Length: {len(payload)}\r\nConnection: close\r\n\r\n")
    raw.sendall(header.encode("ascii") + (b"" if method == "HEAD" else payload))
    emit("bootstrap_response", status=status, length=len(payload), body_sent=method != "HEAD")
