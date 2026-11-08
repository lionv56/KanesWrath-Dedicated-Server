import hashlib,unittest
from bootstrap import serve_bootstrap,DRIVER_REFERENCE
class Socket:
    def __init__(self,method):self.data=f'{method} /servserv/cnc3_ep1/drivers.txt HTTP/1.0\r\n\r\n'.encode();self.sent=b''
    def recv(self,size):chunk=self.data[:size];self.data=self.data[size:];return chunk
    def sendall(self,data):self.sent+=data
class ReferenceFixture(unittest.TestCase):
    def test_exact_upstream_bytes(self):
        self.assertEqual(len(DRIVER_REFERENCE),13)
        self.assertEqual(hashlib.sha1(b'blob 13\0'+DRIVER_REFERENCE).hexdigest(),'99a9528f2846a7b5f3c573e50a4919f297beed91')
    def test_default_is_still_unresolved(self):
        s=Socket('GET');serve_bootstrap(s,lambda *a,**k:None,{})
        self.assertTrue(s.sent.startswith(b'HTTP/1.0 501'))
    def test_reference_get_and_head_are_exact_and_do_not_log_body(self):
        for method in ('GET','HEAD'):
            events=[];s=Socket(method)
            serve_bootstrap(s,lambda e,**k:events.append((e,k)),{'drivers.txt':DRIVER_REFERENCE})
            header,body=s.sent.split(b'\r\n\r\n',1)
            self.assertTrue(header.startswith(b'HTTP/1.0 200'));self.assertIn(b'Content-Length: 13',header)
            self.assertEqual(body,DRIVER_REFERENCE if method=='GET' else b'')
            self.assertNotIn(DRIVER_REFERENCE.hex(),str(events))
if __name__=='__main__':unittest.main(verbosity=2)
