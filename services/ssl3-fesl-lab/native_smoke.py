"""One native Windows acceptance-preparation check. Never starts the game."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from tlslite import TLSConnection
from server import encode, read_frame, settings


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--identity', required=True, type=Path)
    p.add_argument('--evidence', required=True, type=Path)
    args = p.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    # Refuse to overwrite any previous native smoke evidence.
    with (args.evidence / 'native-server.jsonl').open('x', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-u', str(Path(__file__).with_name('server.py')),
                                    '--identity', str(args.identity.resolve()), '--port', '18760'],
                                   stdout=log, stderr=subprocess.STDOUT,
                                   env=dict(os.environ, PYTHONUTF8='1'),
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        conn = None
        try:
            deadline = time.monotonic()+15
            ready = None
            while time.monotonic() < deadline:
                lines = (args.evidence / 'native-server.jsonl').read_text(encoding='utf-8', errors='replace').splitlines()
                for line in lines:
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get('event') == 'ready':
                        ready = event
                if ready:
                    break
                if process.poll() is not None:
                    raise RuntimeError('server startup failed; inspect server log')
                time.sleep(.05)
            if not ready:
                raise RuntimeError('server readiness timeout')
            if os.name == 'nt':
                command = ("Get-NetTCPConnection -LocalPort 18760 -ErrorAction Stop | "
                           "Select-Object LocalAddress,LocalPort,OwningProcess | ConvertTo-Json -Compress")
                result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                                        capture_output=True, text=True, timeout=15,
                                        creationflags=subprocess.CREATE_NO_WINDOW, check=True)
                (args.evidence / 'native-listener.json').write_text(result.stdout, encoding='utf-8')
                owners = json.loads(result.stdout)
                if isinstance(owners, dict):
                    owners = [owners]
                assert owners and all(x['LocalAddress'] == '127.0.0.1' for x in owners)
            raw = socket.create_connection(('127.0.0.1', 18760), timeout=5)
            conn = TLSConnection(raw)
            conn.handshakeClientCert(settings=settings())
            assert conn.version == (3, 0) and conn.session.cipherSuite == 5
            cert = x509.load_pem_x509_certificate((args.identity / 'cert.pem').read_bytes())
            expected = cert.fingerprint(hashes.SHA256()).hex()
            assert expected == ready['identity']['fingerprint']
            assert hashlib.sha256(bytes(conn.session.serverCertChain.x509List[0].bytes)).hexdigest() == expected
            conn.write(encode(b'fsys', 0xc0000001, {'TXN': 'Hello', 'clientString': 'KWDS-native-controlled'}))
            kind, ident, fields = read_frame(conn)
            assert (kind, ident, fields['TXN']) == (b'fsys', 0xc0000001, 'Hello')
            assert fields['theaterIp'] == '127.0.0.1'
            conn.write(encode(b'fsys', 0xc0000002, {'TXN': 'Ping'}))
            assert read_frame(conn) == (b'fsys', 0xc0000002, {'TXN': 'Ping'})
            conn.close()
            conn = None
            time.sleep(.15)
            events = [json.loads(line) for line in
                      (args.evidence / 'native-server.jsonl').read_text(encoding='utf-8').splitlines()]
            assert any(e.get('message') == 'ClientKeyExchange' for e in events)
            assert any(e.get('event') == 'handshake_complete' for e in events)
            result = dict(result='PASS', python=sys.version, executable=sys.executable,
                          launcher_pid=process.pid, protocol='SSL3', suite='0x0005',
                          certificate_sha256=expected, hello='PASS', ping='PASS',
                          scope='controlled native client only; no game compatibility claim')
            (args.evidence / 'native-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(json.dumps(result, indent=2))
        finally:
            if conn is not None:
                conn.close()
            process.terminate()
            process.wait(timeout=10)


if __name__ == '__main__':
    main()
