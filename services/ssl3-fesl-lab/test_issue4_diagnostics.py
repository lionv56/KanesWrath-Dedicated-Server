import json
from pathlib import Path
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import state_snapshot as snapshots
from server import Lab, identity, error_metadata, TracedSocket
from tlslite.errors import TLSLocalAlert
from tlslite.messages import Alert

class Repairs(unittest.TestCase):
    def test_restore_prevalidates_all_directories_without_writes(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'game';root.mkdir();(root/'gp.info').write_bytes(b'before')
            snap=Path(t)/'snapshot';snapshots.capture([root],snap)
            manifest=json.loads((snap/'manifest.json').read_text())
            manifest['directories'][0]=['created-before-invalid','../outside']
            (snap/'manifest.json').write_text(json.dumps(manifest))
            (root/'gp.info').write_bytes(b'current')
            with self.assertRaises(ValueError):snapshots.restore([root],snap)
            self.assertFalse((root/'created-before-invalid').exists())
            self.assertEqual((root/'gp.info').read_bytes(),b'current')

    def test_capture_detects_empty_directory_change(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'game';root.mkdir();(root/'Tacitus.log').write_bytes(b'private')
            snap=Path(t)/'snapshot';original=snapshots.shutil.copy2
            def changing_copy(*a,**kw):
                result=original(*a,**kw);(root/'late-directory').mkdir();return result
            with patch.object(snapshots.shutil,'copy2',side_effect=changing_copy):
                with self.assertRaises(ValueError):snapshots.capture([root],snap)
            self.assertFalse((snap/'manifest.json').exists())

    def test_restore_rejects_negative_root_index(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'game';root.mkdir();(root/'gp.info').write_bytes(b'before')
            snap=Path(t)/'snapshot';snapshots.capture([root],snap)
            m=json.loads((snap/'manifest.json').read_text());m['files'][0]['root']=-1
            (snap/'manifest.json').write_text(json.dumps(m))
            with self.assertRaises(ValueError):snapshots.restore([root],snap)

    def test_root_junction_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)/'game';root.mkdir()
            # Simulate Windows' directory-junction attribute without changing OS settings.
            original=Path.lstat
            def attrs(p,*a,**kw):
                value=original(p,*a,**kw)
                if p == root:
                    class Junction:
                        st_file_attributes=0x400
                    return Junction()
                return value
            with patch.object(Path,'lstat',attrs):
                with self.assertRaises(ValueError):snapshots.roots_checked([root])

    def test_game_and_user_profile_restore_together(self):
        with tempfile.TemporaryDirectory() as t:
            game=Path(t)/'game';profile=Path(t)/'profile'
            game.mkdir();profile.mkdir();(profile/'Profiles').mkdir()
            expected={game/'gp.info':b'gp-before',game/'Tacitus.log':b'log-before',
                      profile/'Profiles'/'Options.ini':b'options-before'}
            for p,data in expected.items():p.write_bytes(data)
            snap=Path(t)/'snapshot';self.assertEqual(snapshots.capture([game,profile],snap),3)
            for p in expected:p.write_bytes(b'changed')
            with self.assertRaises(ValueError):snapshots.restore([profile,game],snap)
            self.assertEqual(snapshots.restore([game,profile],snap),3)
            for p,data in expected.items():self.assertEqual(p.read_bytes(),data)

    def test_error_metadata_never_logs_messages(self):
        event=error_metadata(TLSLocalAlert(Alert().create(47,2),'SENTINEL_SECRET'))
        self.assertEqual(event['alert_source'],'server')
        self.assertEqual(event['alert_description'],47)
        self.assertNotIn('SENTINEL_SECRET',json.dumps(event))
        events=[]
        class ResetSocket:
            def recv(self,*args):raise ConnectionResetError(10054,'SENTINEL_SECRET')
        traced=TracedSocket(ResetSocket(),lambda event,**kw:events.append(dict(event=event,**kw)))
        with self.assertRaises(ConnectionResetError):traced.recv(10)
        self.assertEqual(events[0]['errno'],10054)
        self.assertNotIn('SENTINEL_SECRET',json.dumps(events))

    def test_controlled_eof_after_server_hello_done_is_identifiable(self):
        with tempfile.TemporaryDirectory() as t:
            events=[];closed=threading.Event()
            def emit(event,**kw):
                events.append(dict(event=event,**kw))
                if event=='connection_closed':closed.set()
            lab=Lab(('127.0.0.1',0),identity(Path(t)/'identity'),emit)
            thread=threading.Thread(target=lab.serve_forever,daemon=True);thread.start()
            try:
                with socket.create_connection(lab.server_address,timeout=5) as s:
                    hello=b'\x03\x00'+bytes(32)+b'\x00\x00\x02\x00\x05\x01\x00'
                    handshake=b'\x01'+len(hello).to_bytes(3,'big')+hello
                    s.sendall(b'\x16\x03\x00'+len(handshake).to_bytes(2,'big')+handshake)
                    def exact_bytes(n):
                        result=b''
                        while len(result)<n:
                            chunk=s.recv(n-len(result))
                            self.assertTrue(chunk);result+=chunk
                        return result
                    # Synchronize on received records, not a racing server log callback.
                    done=False;pending=b''
                    while not done:
                        header=exact_bytes(5)
                        self.assertEqual(header[0],22)
                        pending+=exact_bytes(int.from_bytes(header[3:5],'big'))
                        while len(pending)>=4:
                            size=int.from_bytes(pending[1:4],'big')
                            if len(pending)<size+4:break
                            done=done or pending[0]==14
                            pending=pending[size+4:]
                    s.shutdown(socket.SHUT_WR)
                    while s.recv(4096):pass
                self.assertTrue(closed.wait(5))
                self.assertTrue(any(e['event']=='transport_eof' for e in events))
                error=next(e for e in events if e['event']=='connection_error')
                self.assertEqual(error['phase'],'handshake')
                self.assertFalse(any(e.get('message')=='ClientKeyExchange' for e in events))
            finally:
                lab.shutdown();lab.server_close();thread.join()
                print('CONTROLLED_FAILURE_EVENTS='+json.dumps([e for e in events if e['event'] in ('connection_open','connection_error','transport_eof','connection_closed')]))

    def test_actual_remote_tls_alert_has_safe_failure_context(self):
        with tempfile.TemporaryDirectory() as t:
            events=[];closed=threading.Event()
            def emit(event,**kw):
                events.append(dict(event=event,**kw))
                if event=='connection_closed':closed.set()
            lab=Lab(('127.0.0.1',0),identity(Path(t)/'identity'),emit)
            thread=threading.Thread(target=lab.serve_forever,daemon=True);thread.start()
            try:
                with socket.create_connection(lab.server_address,timeout=5) as s:
                    s.sendall(b'\x15\x03\x00\x00\x02\x02\x2a')
                    try:s.recv(100)
                    except ConnectionResetError:pass
                self.assertTrue(closed.wait(5))
                error=next(x for x in events if x['event']=='connection_error')
                self.assertEqual(error['phase'],'handshake')
                self.assertEqual(error['alert_source'],'peer')
                self.assertEqual(error['alert_description'],42)
                opening=next(x for x in events if x['event']=='connection_open')
                self.assertEqual(opening['certificate_sha256'],lab.info['fingerprint'])
            finally:
                lab.shutdown();lab.server_close();thread.join()
                print('CONTROLLED_FAILURE_EVENTS='+json.dumps([e for e in events if e['event'] in ('connection_open','connection_error','transport_eof','connection_closed')]))

if __name__=='__main__':unittest.main(verbosity=2)
