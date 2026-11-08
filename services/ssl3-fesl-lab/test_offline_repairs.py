"""Focused controlled-client checks; never starts or inspects a game."""
import json
from pathlib import Path
import socket
import tempfile
import threading
import unittest
from server import Lab, identity, settings, encode, read_frame
from tlslite import TLSConnection
from state_snapshot import capture, restore


class Repairs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.events = []
        cls.lab = Lab(('127.0.0.1',0), identity(Path(cls.temp.name)/'identity'),
                      lambda event, **kw: cls.events.append(dict(event=event, **kw)))
        cls.thread = threading.Thread(target=cls.lab.serve_forever, daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.lab.shutdown(); cls.lab.server_close(); cls.thread.join()
        print('CONTROLLED_EVENTS='+json.dumps(cls.events))
        cls.temp.cleanup()
    def http(self, method, path):
        with socket.create_connection(self.lab.server_address,timeout=5) as s:
            request=(f'{method} {path} HTTP/1.1\r\nAuthorization: SENTINEL_SECRET\r\nHost: localhost\r\n\r\n').encode()
            s.sendall(request[:2]); s.sendall(request[2:])
            result=b''
            while True:
                b=s.recv(4096)
                if not b: break
                result+=b
            return result
    def test_maps_and_head(self):
        a=self.http('GET','/servserv/cnc3_ep1/maps-65536.txt')
        self.assertTrue(a.startswith(b'HTTP/1.0 200'))
        self.assertEqual(a.split(b'\r\n\r\n',1)[1],b'')
        a=self.http('HEAD','/servserv/cnc3_ep1/config.txt')
        self.assertIn(b'Content-Length: 224',a)
        self.assertEqual(a.split(b'\r\n\r\n',1)[1],b'')
    def test_unknown_driver_is_explicitly_unresolved(self):
        self.assertTrue(self.http('GET','/servserv/cnc3_ep1/drivers.txt').startswith(b'HTTP/1.0 501'))
    def test_metadata_redaction_and_methods(self):
        self.assertTrue(self.http('POST','/servserv/cnc3_ep1/config.txt?SENTINEL_QUERY').startswith(b'HTTP/1.0 405'))
        self.assertTrue(self.http('GET','/SENTINEL_PATH').startswith(b'HTTP/1.0 404'))
        text=json.dumps(self.events)
        for token in ['SENTINEL_SECRET','SENTINEL_QUERY','SENTINEL_PATH']: self.assertNotIn(token,text)
    def test_unknown_wire_not_misreported_as_client_hello(self):
        with socket.create_connection(self.lab.server_address,timeout=5) as s:
            s.sendall(b'password-SECRET')
            try:self.assertEqual(s.recv(100),b'')
            except ConnectionResetError:pass  # Close with unread bytes is a reset on Windows.
        self.assertNotIn('SECRET',json.dumps(self.events))
    def test_tls_prefix_replay_and_encrypted_hello(self):
        c=TLSConnection(socket.create_connection(self.lab.server_address,timeout=5))
        try:
            c.handshakeClientCert(settings=settings())
            self.assertEqual((c.version,c.session.cipherSuite),((3,0),5))
            c.write(encode(b'fsys',7,{'TXN':'Hello'}))
            self.assertEqual(read_frame(c)[2]['TXN'],'Hello')
        finally:c.close()
    def test_complete_content_snapshot_and_restoration(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'game';root.mkdir();(root/'empty').mkdir()
            (root/'gp.info').write_bytes(b'before-gp')
            (root/'Tacitus.log').write_bytes(b'before-log')
            backup=Path(t)/'snapshot'
            self.assertEqual(capture([root],backup),2)
            (root/'gp.info').write_bytes(b'after-gp')
            (root/'Tacitus.log').unlink();(root/'empty').rmdir()
            (root/'new').mkdir();(root/'new'/'test-owned.txt').write_bytes(b'new')
            with self.assertRaises(ValueError):restore([root],backup)
            self.assertEqual(restore([root],backup,remove_new=True),2)
            self.assertEqual((root/'gp.info').read_bytes(),b'before-gp')
            self.assertEqual((root/'Tacitus.log').read_bytes(),b'before-log')
            self.assertTrue((root/'empty').is_dir());self.assertFalse((root/'new').exists())


if __name__=='__main__':unittest.main(verbosity=2)
