import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from admin import capacity_stream as stream
from admin.tests.test_capacity_history import snapshot,NOW
from admin.capacity_router import panel

class Handler:
    def __init__(self):
        self.wfile=io.BytesIO();self.connection=self;self.headers={};self.status=None;self.close_connection=False
    def settimeout(self,timeout):self.timeout=timeout
    def send_response(self,status):self.status=status
    def send_header(self,name,value):self.headers[name]=value
    def end_headers(self):pass
    def _json(self,data,code):self.status=code;self.json=data

class Streaming(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'snapshot.json';self.path.write_text(json.dumps(snapshot()))
        self.data=panel(15,path=self.path,now=NOW)
    def tearDown(self):self.tmp.cleanup()
    def test_initial_and_epoch_changes_are_complete_snapshots(self):
        self.assertEqual(stream.delta(None,self.data),('snapshot',self.data))
        prior=dict(self.data,epoch='f'*32);self.assertEqual(stream.delta(prior,self.data)[0],'snapshot')
    def test_incremental_updates_and_removals(self):
        second=copy.deepcopy(self.data);second['sequence']+=1;second['recent'][0]['usage']['output_tokens']=9
        event,d=stream.delta(self.data,second);self.assertEqual(event,'delta');self.assertEqual(len(d['recent_upsert']),1)
        self.assertNotIn('routes',d);self.assertNotIn('aliases',d)
        third=copy.deepcopy(second);third['recent']=[];d=stream.delta(second,third)[1]
        self.assertEqual(d['recent_ids'],[]);self.assertEqual(d['recent_upsert'],[])
    def test_unchanged_large_fields_not_retransmitted(self):
        d=stream.delta(self.data,dict(self.data,sequence=2))[1]
        self.assertEqual(d['recent_upsert'],[])
        for field in ['routes','aliases','series','controls','claude','overflow']:self.assertNotIn(field,d)
    def test_stream_headers_snapshot_and_bounded_close(self):
        h=Handler()
        with patch.dict('os.environ',{'CAPACITY_OBSERVATORY_PATH':str(self.path)}):
            stream.serve(h,15,duration=1,interval=.1)
        self.assertEqual(h.status,200);self.assertEqual(h.headers['X-Accel-Buffering'],'no')
        self.assertIn('no-transform',h.headers['Cache-Control']);self.assertTrue(h.close_connection)
        output=h.wfile.getvalue();self.assertIn(b'event: snapshot',output);self.assertEqual(output.count(b'event: snapshot'),1)
    def test_authorization_expiration_precedes_data(self):
        h=Handler();stream.serve(h,authorized=lambda:False,duration=1)
        self.assertIn(b'event: auth-expired',h.wfile.getvalue());self.assertNotIn(b'event: snapshot',h.wfile.getvalue())
    def test_admission_cap_does_not_leak_slots(self):
        held=[]
        try:
            while stream._STREAM_SLOTS.acquire(blocking=False):held.append(True)
            h=Handler();stream.serve(h,duration=1);self.assertEqual(h.status,429)
        finally:
            for _ in held:stream._STREAM_SLOTS.release()
        self.assertTrue(stream._STREAM_SLOTS.acquire(blocking=False));stream._STREAM_SLOTS.release()
    def test_disconnect_releases_slot(self):
        class Closed(io.BytesIO):
            def write(self,value):raise BrokenPipeError()
        h=Handler();h.wfile=Closed();stream.serve(h,duration=1)
        self.assertTrue(stream._STREAM_SLOTS.acquire(blocking=False));stream._STREAM_SLOTS.release()

if __name__=='__main__':unittest.main()
