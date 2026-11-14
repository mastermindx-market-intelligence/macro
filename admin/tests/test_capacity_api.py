"""Actual admin HTTP/auth/SSE/control round trips on isolated local fixtures."""
from __future__ import annotations
import copy
import functools
import http.client
from http.cookies import SimpleCookie
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from admin import auth, server, capacity_stream, capacity_history
from admin import capacity_control_owner as owner, capacity_control_transport as transport
from admin.capacity_ingest import ingest
from admin.tests.test_capacity_controls import Route, Refresh, read_document
from admin.tests.test_capacity_history import snapshot


class CapacityAPI(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.path=self.root/'snapshot.json';self.config=self.root/'routes.json';self.sequence=0
        self.config.write_text(json.dumps({'routes':[{'route_id':'r1','models':['m1'],'priority':10,'weight':1}],
                                          'aliases':{'fabric/fast':['m1']}}))
        self.gateway=SimpleNamespace(read_document=read_document,_routes_from_document=lambda d:tuple(Route(r) for r in d['routes']))
        self.native=Refresh(self.config);self.app=SimpleNamespace(state=SimpleNamespace(config_refresh=self.native))
        self.native.refresh(self.app,self.gateway._routes_from_document)
        self.env=patch.dict(os.environ,{'ADMIN_PASSWORD':'isolated-api-fixture','ADMIN_SESSION_SECRET':'isolated-capacity-api-session-key-32','ADMIN_DEPLOYED':'0','CAPACITY_OBSERVATORY_PATH':str(self.path)})
        self.env.start();self.addCleanup(self.env.stop)
        original=capacity_stream.serve
        self.stream_patch=patch.object(capacity_stream,'serve',functools.partial(original,duration=2,interval=.05))
        self.stream_patch.start();self.addCleanup(self.stream_patch.stop)
        self.publish();self.start_server();self.cookies='';self.csrf=''
    def start_server(self):
        self.httpd=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        self.httpd.daemon_threads=True
        self.thread=threading.Thread(target=self.httpd.serve_forever,daemon=True);self.thread.start()
        self.port=self.httpd.server_address[1]
    def stop_server(self):
        self.httpd.shutdown();self.httpd.server_close();self.thread.join(3)
    def tearDown(self):
        self.stop_server();self.tmp.cleanup()
    def publish(self,output=7):
        now=time.time();self.sequence+=1
        s=snapshot(self.sequence,at=now,started=now-100,output=output)
        s['controls']=owner.projection(self.app,self.gateway,enabled=True)
        ingest(json.dumps(s).encode(),self.path,now=now)
    def request(self,method,path,body=None,headers=None,authenticated=True):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=12)
        h={'Content-Type':'application/json','Origin':f'http://127.0.0.1:{self.port}'}
        if authenticated and self.cookies:h['Cookie']=self.cookies;h[auth.CSRF_HEADER]=self.csrf
        h.update(headers or {})
        try:
            conn.request(method,path,json.dumps(body) if body is not None else None,h)
            response=conn.getresponse();raw=response.read();meta=dict(response.getheaders());status=response.status
            if path=='/api/login' and status==200:
                cookies=SimpleCookie()
                for key,value in response.getheaders():
                    if key.lower()=='set-cookie':cookies.load(value)
                self.cookies='; '.join(f'{k}={v.value}' for k,v in cookies.items())
                self.csrf=cookies[auth.CSRF_COOKIE].value
            return status,json.loads(raw),meta
        finally:
            conn.close()
    def login(self):
        self.assertEqual(self.request('POST','/api/login',{'password':'isolated-api-fixture'},authenticated=False)[0],200)
    def worker(self,*,deliver=True):
        errors=[]
        def run():
            try:
                end=time.monotonic()+5
                while time.monotonic()<end:
                    intent=transport.next_request('a'*32,path=self.path)
                    if intent:
                        result=owner.handle(intent,self.app,self.gateway,epoch='a'*32,enabled=True)
                        result['request_id']=intent.get('request_id') or intent['operation_id']
                        self.publish()
                        if deliver:transport.accept_result(result,path=self.path)
                        return
                    time.sleep(.01)
                errors.append('control request did not arrive')
            except BaseException as e:errors.append(repr(e))
        thread=threading.Thread(target=run,daemon=True);thread.start()
        return thread,errors
    def control(self,action,patch_,*,deliver=True):
        thread,errors=self.worker(deliver=deliver)
        try:
            result=self.request('POST','/api/capacity-router/settings',{'action':action,'expected_revision':self.native.digest,'patch':patch_})
        finally:
            thread.join(6)
        self.assertFalse(thread.is_alive());self.assertFalse(errors,errors)
        return result
    def event_stream(self):
        conn=http.client.HTTPConnection('127.0.0.1',self.port,timeout=5)
        conn.request('GET','/api/capacity-router/events',headers={'Cookie':self.cookies})
        response=conn.getresponse();self.assertEqual(response.status,200)
        return conn,response
    @staticmethod
    def next_event(response):
        lines=[]
        while True:
            line=response.readline()
            if not line:return b''.join(lines)
            lines.append(line)
            if line==b'\n':
                event=b''.join(lines)
                if b'event:' in event:return event
                lines=[]
    def test_all_new_routes_require_real_session_and_private_responses(self):
        paths=['','/history?minutes=0','/intelligence','/settings','/events']
        for suffix in paths:
            status,body,headers=self.request('GET','/api/capacity-router'+suffix,authenticated=False)
            self.assertEqual(status,401);self.assertNotIn('routes',body);self.assertEqual(headers['Cache-Control'],'no-store')
        self.login()
        for suffix in paths[:-1]:
            status,body,headers=self.request('GET','/api/capacity-router'+suffix)
            self.assertEqual(status,200);self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertEqual(self.request('GET','/api/capacity-router/history?from=nan')[0],400)
    def test_writes_require_origin_content_type_and_csrf_before_transport(self):
        self.login();body={'action':'apply','expected_revision':self.native.digest,'patch':{'interval_s':.5}}
        cases=[({'Origin':'https://untrusted.invalid'},403),({'Content-Type':'text/plain'},415),({auth.CSRF_HEADER:''},403),({'Cookie':'admin_session=invalid'},401)]
        for headers,expected in cases:
            self.assertEqual(self.request('POST','/api/capacity-router/settings',body,headers)[0],expected)
        self.assertFalse(transport.paths(self.path)[0].exists());self.assertNotIn('observability',read_document(self.config)[0])
    def test_real_http_control_validation_apply_and_effective_readback(self):
        self.login();before=self.config.read_bytes()
        status,result,_=self.control('validate',{'interval_s':.5})
        self.assertEqual(status,200);self.assertEqual(result['state'],'VALIDATED');self.assertEqual(self.config.read_bytes(),before)
        status,result,_=self.control('apply',{'interval_s':.5})
        self.assertEqual(status,200);self.assertEqual(result['state'],'APPLIED')
        status,settings,_=self.request('GET','/api/capacity-router/settings')
        self.assertEqual(settings['interval_s'],.5);self.assertEqual(settings['revision'],settings['effective_revision'])
    def test_lost_reply_recovers_from_native_receipt_without_config_replay(self):
        self.login();original=transport.submit
        with patch.object(transport,'submit',functools.partial(original,timeout=.2)):
            status,result,_=self.control('apply',{'interval_s':.5},deliver=False)
        self.assertEqual(status,202);stamp=self.config.stat().st_mtime_ns
        status,result,_=self.request('POST','/api/capacity-router/settings',{'action':'reconcile','operation_id':result['operation_id']})
        self.assertEqual(status,200);self.assertEqual(result['state'],'APPLIED')
        self.assertEqual(self.config.stat().st_mtime_ns,stamp)
    def test_sse_real_socket_delta_reconnect_and_no_proxy_buffering(self):
        self.login();conn,response=self.event_stream()
        try:
            self.assertEqual(response.getheader('X-Accel-Buffering'),'no')
            self.assertIn('no-transform',response.getheader('Cache-Control'))
            first=self.next_event(response);self.assertIn(b'event: snapshot',first)
            self.publish(output=9)
            second=self.next_event(response)
            self.assertIn(b'event: delta',second)
        finally:response.close();conn.close()
        conn,response=self.event_stream()
        try:self.assertIn(b'event: snapshot',self.next_event(response))
        finally:response.close();conn.close()
    def test_history_survives_actual_http_server_restart(self):
        self.login();status,before,_=self.request('GET','/api/capacity-router/history?minutes=0')
        self.assertEqual(status,200);self.assertEqual(before['summary']['output_tokens'],7)
        self.stop_server();self.start_server()
        status,after,_=self.request('GET','/api/capacity-router/history?minutes=0')
        self.assertEqual(status,200);self.assertEqual(after['summary'],before['summary'])
        self.assertEqual(after['coverage']['epochs'],before['coverage']['epochs'])

if __name__=='__main__':unittest.main()
