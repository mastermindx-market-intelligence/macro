"""Consumer-level proofs for the read-only router observatory.

Run: python -m unittest discover -s admin/tests -p 'test_capacity_router.py' -v
All inference below is an in-process scripted transport, never a provider call.
"""
import asyncio
from contextlib import asynccontextmanager
import copy
import json
import os
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from admin import capacity_fabric_observer as observer
from admin.capacity_fabric_schema import MAX_ACTIVE, MAX_BYTES, clean_snapshot, number
from admin.capacity_ingest import ingest
from admin.capacity_router import panel, _percentile

TOKEN = "fixture-observatory-token-not-a-secret"


def route(name="provider-a", model="model-a"):
    return SimpleNamespace(route_id=name, pool=name.split("-")[0], models=(model,), wire_model=lambda value: value,
        wire="anthropic", priority=10, weight=1)


def state_app():
    return SimpleNamespace(state=SimpleNamespace(
        settings=SimpleNamespace(routes=[route()], aliases=(("fabric/fast", ("model-a",)),), proxy_token=TOKEN),
        router_state=SimpleNamespace(per_route={}, routes=SimpleNamespace(available=lambda *a:True, consecutive_failures={}),
                                     served=0, refused=0, attempts=0, failovers=0)))


def payload_events(output=7):
    return [
        {"type":"message_start","message":{"usage":{"input_tokens":11,"cache_read_input_tokens":3}}},
        {"type":"ping"},
        {"type":"content_block_delta","delta":{"type":"text_delta","text":"PRIVATE completion 你好"}},
        {"type":"message_delta","usage":{"output_tokens":3}},
        {"type":"message_delta","usage":{"output_tokens":output}},
        {"type":"message_stop"},
    ]


def wire(events):
    return b"".join(b"data: "+json.dumps(e, ensure_ascii=False).encode()+b"\r\n\r\n" for e in events)


def fake_gateway():
    gateway=SimpleNamespace(_model_candidates=lambda p,a:[(p["model"],"")])
    app=FastAPI()
    app.state.settings=state_app().state.settings
    app.state.router_state=state_app().state.router_state
    app.state.settings.routes=[route("pool-a","model-a"),route("pool-b","model-b")]
    app.state.settings.aliases=(("fabric/fast",("model-a",)),("fallback",("model-a",)))

    class Retryable(Exception):
        reason="CAPACITY_FIXTURE_REFUSAL"

    async def _forward_anthropic(app, route, authorization, payload, wants_stream):
        if route.route_id=="refused-route":
            raise Retryable()
        if payload["model"]=="cancel":
            raise asyncio.CancelledError()
        await asyncio.sleep(.002 if route.route_id=="pool-a" else .001)
        output=7 if route.route_id=="pool-a" else 19
        if wants_stream:
            async def stream():
                data=wire(payload_events(output))
                for pos in range(0,len(data),3):
                    yield data[pos:pos+3]
                    await asyncio.sleep(0)
            return StreamingResponse(stream(), media_type="text/event-stream",headers={"x-fixture":"preserved"})
        return JSONResponse({"content":[{"type":"text","text":"PRIVATE completion"}],
                             "usage":{"input_tokens":11,"output_tokens":output}},headers={"x-fixture":"preserved"})

    async def _forward_openai(app, route, authorization, payload, wants_stream, slug=""):
        return await _forward_anthropic(app,route,authorization,payload,wants_stream)

    async def _forward_responses(app_, route, payload, wants_stream):
        return await _forward_anthropic(app_,route,TOKEN,payload,wants_stream)

    @app.post("/v1/messages")
    async def messages(request:Request):
        if request.headers.get("authorization")!="Bearer "+TOKEN:
            return JSONResponse({"error":"unauthorized"},status_code=401)
        body=await request.json()
        gateway._model_candidates(body,())
        r=route("pool-a","model-a") if body["model"] in ("model-a","fallback","cancel") else route("pool-b","model-b")
        if body["model"]=="fallback":
            try:
                await _forward_anthropic(app,route("refused-route"),TOKEN,body,False)
            except Retryable:
                pass
        if body.get("wire")=="openai":
            return await _forward_openai(app,r,TOKEN,body,body.get("stream",False))
        if body.get("wire")=="responses":
            return await _forward_responses(app,r,body,body.get("stream",False))
        return await _forward_anthropic(app,r,TOKEN,body,body.get("stream",False))
    return app,gateway


class ObserverSemantics(unittest.TestCase):
    def test_retry_does_not_inherit_usage_and_failed_attempt_closes(self):
        store=observer.ObservationStore();rid=store.begin({})
        store.attempt(rid,route(),{"model":"model-a"});store.usage(rid,{"output_tokens":17})
        second=store.attempt(rid,route("provider-b"),{"model":"model-a"})
        self.assertIsNone(store.active[rid]["usage"]["output_tokens"])
        second.update(state="failed",status_code=400)
        store.active[rid]["status_code"]=400;store.finish(rid)
        self.assertIsNotNone(second["ended_at"])

    def test_latest_usage_replaces_provisional_and_rejects_huge_integer(self):
        store=observer.ObservationStore();rid=store.begin({})
        store.usage(rid,{"output_tokens":10});store.usage(rid,{"output_tokens":8})
        self.assertEqual(store.active[rid]["usage"]["output_tokens"],8)
        self.assertIsNone(number(10**1000))
        self.assertEqual(_percentile([100,1000],.95),955)

    def test_unsupported_model_and_translator_zero_remain_unknown(self):
        store=observer.ObservationStore(["model-a"]);rid=store.begin({})
        store.input(rid,{"model":"VALID_LOOKING_PRIVATE_CONTENT"})
        store.active[rid]["_translated_usage"]=True
        store.event(rid,{"type":"message_start","message":{"usage":{"input_tokens":0,"output_tokens":0}}})
        self.assertIsNone(store.active[rid]["usage"]["output_tokens"])
        self.assertNotIn("VALID_LOOKING_PRIVATE_CONTENT",json.dumps(store.snapshot(state_app())))

    def test_maximum_shape_is_deliverable_with_explicit_compaction(self):
        store=observer.ObservationStore();rid=store.begin({})
        snap=store.snapshot(state_app());record=snap["active"][0]
        for key in ("requested_model","served_model","wire_model","route_id","provider","lane"):
            record[key]="m"*128
        attempt={"route_id":"r"*128,"model":"m"*128,"started_at":time.time(),"ended_at":None,
                 "state":"waiting","reason":"e"*128,"status_code":None}
        record["attempts"]=[dict(attempt) for _ in range(12)]
        snap["active"]=[copy.deepcopy(record) for _ in range(256)]
        snap["recent"]=[copy.deepcopy(record) for _ in range(400)]
        sample=snap["routes"][0];sample["models"]=["m"*128 for _ in range(64)]
        snap["routes"]=[copy.deepcopy(sample) for _ in range(128)]
        data=observer.serialize_snapshot(snap)
        self.assertLessEqual(len(data),MAX_BYTES)
        received=json.loads(data)
        self.assertEqual(len(received["active"]),256)
        self.assertGreater(received["truncated"]["recent"],0)

    def test_fragmentation_cumulative_usage_and_private_content(self):
        data=wire(payload_events())
        for size in (1,2,3,7,31,len(data)):
            with self.subTest(size=size):
                store=observer.ObservationStore();rid=store.begin({"user-agent":"claude-cli"})
                parser=observer.StreamObserver(store,rid,True)
                for pos in range(0,len(data),size):parser.feed(data[pos:pos+size])
                parser.feed(b"",True)
                store.active[rid]["streaming"]=True
                store.finish(rid)
                r=store.recent[0]
                self.assertEqual(r["state"],"completed")
                self.assertEqual(r["usage"],{"input_tokens":11,"output_tokens":7,"cache_read_tokens":3,"cache_write_tokens":None})
                self.assertTrue(r["usage_final"])
                self.assertEqual(r["content_events"],1)
                self.assertIsNotNone(r["first_content_at"])
                self.assertNotIn("PRIVATE",json.dumps(store.snapshot(state_app())))

    def test_ping_and_role_are_not_first_content(self):
        store=observer.ObservationStore();rid=store.begin({})
        store.event(rid,{"type":"ping"})
        store.event(rid,{"type":"message_start","message":{"role":"assistant"}})
        self.assertIsNone(store.active[rid]["first_content_at"])

    def test_unterminated_stream_and_missing_usage_remain_unknown(self):
        store=observer.ObservationStore();rid=store.begin({})
        store.active[rid]["streaming"]=True
        observer.StreamObserver(store,rid,True).feed(b'data: {"type":"message_stop"}',True)
        store.finish(rid)
        self.assertEqual(store.recent[0]["state"],"interrupted")
        self.assertIsNone(store.recent[0]["usage"]["output_tokens"])

    def test_oversized_event_recovers_without_counting_payload(self):
        store=observer.ObservationStore();rid=store.begin({})
        p=observer.StreamObserver(store,rid,True)
        p.feed(b'data: '+b'x'*(observer._FRAME_LIMIT+100)+b'\n\n')
        p.feed(wire(payload_events()))
        self.assertEqual(store.active[rid]["usage"]["output_tokens"],7)
        self.assertGreater(store.totals["observer_errors"],0)
        self.assertLessEqual(len(p.buffer),observer._FRAME_LIMIT)

    def test_explicit_lineage_and_sdk_identity_are_pseudonymized(self):
        store=observer.ObservationStore();rid=store.begin({"x-fabric-agent-id":"private-agent","x-fabric-parent-agent-id":"private-parent"})
        store.input(rid,{"model":"model-a","metadata":{"fabric":{"project_id":"private-project","session_id":"private-session","client":"T3"},"prompt":"DO NOT EXPORT"}})
        r=store.active[rid]
        self.assertEqual(r["client"],"T3")
        self.assertEqual(r["parent_agent_id"],observer._opaque("private-parent"))
        exported=json.dumps(store.snapshot(state_app()))
        self.assertNotIn("private-",exported);self.assertNotIn("DO NOT EXPORT",exported)
        sdk=store.begin({})
        store.input(sdk,{"model":"model-a","metadata":{"user_id":json.dumps({"session_id":"sdk-session","account_uuid":"private-account"})}})
        self.assertEqual(store.active[sdk]["session_id"],observer._opaque("sdk-session"))
        self.assertEqual(store.active[sdk]["identity_source"],"sdk_session")
        unknown=store.begin({})
        store.input(unknown,{"model":"model-a","metadata":{"user_id":"a-user-is-not-a-session"}})
        self.assertIsNone(store.active[unknown]["session_id"])
        self.assertEqual(store.active[unknown]["identity_source"],"unattributed")

    def test_configured_aliases_survive_projection(self):
        self.assertEqual(observer.ObservationStore().snapshot(state_app())["aliases"],
                         {"fabric/fast":["model-a"]})

    def test_active_overflow_is_counted_and_never_evicts_live_work(self):
        store=observer.ObservationStore()
        ids=[store.begin({}) for _ in range(MAX_ACTIVE)]
        self.assertIsNone(store.begin({}))
        self.assertEqual(len(store.active),MAX_ACTIVE)
        self.assertEqual(store.totals["overflow_active"],1)
        store.finish(None)
        self.assertEqual(store.totals["overflow_active"],0)
        self.assertIn(ids[0],store.active)

    def test_snapshot_allowlist_drops_secrets_and_unknown_fields(self):
        store=observer.ObservationStore();rid=store.begin({})
        snapshot=store.snapshot(state_app())
        snapshot["secret"]="secret-canary"
        snapshot["routes"][0]["api_key"]="secret-canary"
        snapshot["active"][0]["prompt"]="secret-canary"
        self.assertNotIn("secret-canary",json.dumps(clean_snapshot(snapshot)))
        snapshot["routes"][0]["id"]='<script>alert(1)</script>'
        self.assertEqual(clean_snapshot(snapshot)["routes"][0]["id"],"unknown")


class ASGITransparency(unittest.IsolatedAsyncioTestCase):
    async def test_untrusted_exception_reason_does_not_change_or_leak_error(self):
        for reason in ("VALID_LOOKING_PRIVATE_CONTENT", ["malformed"]):
            store=observer.ObservationStore();rid=store.begin({})
            error=RuntimeError("private message");error.reason=reason
            async def original(app,route,payload):
                raise error
            context=observer._CONTEXT.set((store,rid))
            try:
                with self.assertRaises(RuntimeError) as caught:
                    await observer._wrap_forwarder(original,"_forward_anthropic",frozenset())(None,route(),{"model":"model-a"})
                self.assertIs(caught.exception,error)
            finally:
                observer._CONTEXT.reset(context)
            self.assertNotIn("PRIVATE",json.dumps(store.snapshot(state_app())))

    async def test_non_ascii_bad_auth_remains_incumbent_rejection(self):
        app,gateway=fake_gateway();observer.instrument_app(app,gateway)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=("127.0.0.1",42)),base_url="http://local") as client:
            response=await client.post("/v1/messages",json={"model":"model-a"},headers={b"authorization":b"Bearer \xff"})
        self.assertEqual(response.status_code,401)
        self.assertEqual(app.state.capacity_observer.totals["started"],0)

    async def request(self,app,body,authorized=True):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app,client=("127.0.0.1",42)),base_url="http://local") as client:
            return await client.post("/v1/messages",json=body,headers={"authorization":"Bearer "+TOKEN} if authorized else {})

    async def test_json_and_stream_status_headers_bytes_preserved(self):
        for stream in (False,True):
            plain,gw=fake_gateway();instrumented,gw2=fake_gateway()
            observer.instrument_app(instrumented,gw2)
            body={"model":"model-a","stream":stream,"messages":[{"content":"PRIVATE prompt"}]}
            before=await self.request(plain,body);after=await self.request(instrumented,body)
            self.assertEqual(before.status_code,after.status_code)
            self.assertEqual(dict(before.headers),dict(after.headers))
            self.assertEqual(before.content,after.content)
            r=instrumented.state.capacity_observer.recent[0]
            self.assertEqual(r["usage"]["output_tokens"],7)
            self.assertEqual(r["state"],"completed")
            self.assertEqual(r["route_id"],"pool-a")
            self.assertIsNone(observer._CONTEXT.get())

    async def test_parallel_requests_and_fallback_keep_exact_identity(self):
        app,gw=fake_gateway();observer.instrument_app(app,gw)
        responses=await asyncio.gather(*[self.request(app,{"model":m,"stream":True,"metadata":{"fabric":{"agent_id":m}}}) for m in ("model-a","model-b","fallback")])
        self.assertEqual([r.status_code for r in responses],[200,200,200])
        records={r["requested_model"]:r for r in app.state.capacity_observer.recent}
        self.assertEqual(records["model-a"]["usage"]["output_tokens"],7)
        self.assertEqual(records["model-b"]["usage"]["output_tokens"],19)
        self.assertEqual(records["model-b"]["route_id"],"pool-b")
        self.assertEqual(records["fallback"]["agent_id"],observer._opaque("fallback"))
        self.assertEqual([a["route_id"] for a in records["fallback"]["attempts"]],["refused-route","pool-a"])
        self.assertEqual(records["fallback"]["attempts"][0]["state"],"failed")
        self.assertFalse(app.state.capacity_observer.active)

    async def test_auth_failure_not_observed_and_not_changed(self):
        app,gw=fake_gateway();observer.instrument_app(app,gw)
        response=await self.request(app,{"model":"model-a"},False)
        self.assertEqual(response.status_code,401)
        self.assertEqual(app.state.capacity_observer.totals["started"],0)

    async def test_parser_failure_does_not_break_inference(self):
        app,gw=fake_gateway();observer.instrument_app(app,gw)
        def broken(*args):raise RuntimeError("observer fixture")
        app.state.capacity_observer.event=broken
        response=await self.request(app,{"model":"model-a","stream":True})
        self.assertEqual(response.status_code,200)
        self.assertIn(b'message_stop',response.content)
        self.assertGreater(app.state.capacity_observer.totals["observer_errors"],0)

    async def test_cancellation_cleans_context_and_active_records(self):
        app,gw=fake_gateway();observer.instrument_app(app,gw)
        with self.assertRaises(asyncio.CancelledError):
            await self.request(app,{"model":"cancel"})
        self.assertFalse(app.state.capacity_observer.active)
        self.assertEqual(app.state.capacity_observer.recent[0]["state"],"cancelled")
        self.assertIsNone(observer._CONTEXT.get())

    async def test_duplicate_install_is_idempotent(self):
        app,gw=fake_gateway();observer.instrument_app(app,gw)
        first=app.state.capacity_observer
        observer.instrument_app(app,gw)
        await self.request(app,{"model":"model-a"})
        self.assertIs(app.state.capacity_observer,first)
        self.assertEqual(first.totals["started"],1)
        self.assertEqual(len(first.recent[0]["attempts"]),1)

    async def test_contract_drift_refuses_before_installation(self):
        app=FastAPI();gw=SimpleNamespace(_model_candidates=lambda p,a:[])
        original=gw._model_candidates
        with self.assertRaises(RuntimeError):observer.instrument_app(app,gw)
        self.assertIs(gw._model_candidates,original)
        self.assertFalse(hasattr(app.state,"capacity_observer"))


class SnapshotDelivery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)/"snapshot.json"
        self.store=observer.ObservationStore();self.snapshot=self.store.snapshot(state_app())
    def tearDown(self):self.temp.cleanup()
    def send(self,value,now=None):return ingest(json.dumps(value).encode(),self.path,now=now)

    def test_atomic_file_and_epoch_sequence_fence(self):
        self.assertTrue(self.send(self.snapshot));self.assertFalse(self.send(self.snapshot))
        self.assertEqual(os.stat(self.path).st_mode & 0o777,0o600)
        newer=copy.deepcopy(self.snapshot);newer["epoch"]="f"*32;newer["started_at"]+=.01;newer["generated_at"]+=.02
        self.assertTrue(self.send(newer))
        old=copy.deepcopy(self.snapshot);old["sequence"]+=200;old["generated_at"]+=.03
        self.assertFalse(self.send(old))
        self.assertEqual(json.loads(self.path.read_text())["epoch"],newer["epoch"])

    def test_stale_and_malformed_frames_preserve_last_good(self):
        self.send(self.snapshot);before=self.path.read_bytes()
        old=copy.deepcopy(self.snapshot);old["generated_at"]-=500;old["started_at"]-=1000
        self.assertFalse(self.send(old))
        with self.assertRaises(ValueError):ingest(b'{"schema":"wrong"}',self.path)
        self.assertEqual(self.path.read_bytes(),before)

    def test_admin_read_fresh_stale_missing_and_unknown_usage(self):
        self.assertEqual(panel(path=self.path)["state"],"disconnected")
        self.send(self.snapshot)
        d=panel(path=self.path,now=self.snapshot["generated_at"]+1)
        self.assertEqual(d["state"],"live")
        self.assertIsNone(d["summary"]["output_tokens_per_s"])
        self.assertIsNone(d["summary"]["output_tokens"])
        self.assertEqual(panel(path=self.path,now=self.snapshot["generated_at"]+20)["state"],"stale")

    def test_agent_and_session_with_same_id_remain_distinct_consumers(self):
        session=self.store.begin({"x-fabric-session-id":"same-run-id"})
        agent=self.store.begin({"x-fabric-agent-id":"same-run-id"})
        self.assertNotEqual(session,agent)
        self.assertEqual(self.store.active[session]["session_id"],
                         self.store.active[agent]["agent_id"])
        snapshot=self.store.snapshot(state_app())
        self.send(snapshot)
        result=panel(path=self.path,now=snapshot["generated_at"]+1)
        self.assertEqual(result["summary"]["active_requests"],2)
        self.assertEqual(result["summary"]["active_consumers"],2)

    def test_stale_snapshot_preserves_its_measured_window(self):
        rid=self.store.begin({})
        self.store.input(rid,{"model":"model-a"})
        self.store.event(rid,{"content":[{"type":"text","text":"fixture"}],
                              "usage":{"input_tokens":2,"output_tokens":7}})
        self.store.finish(rid)
        snapshot=self.store.snapshot(state_app())
        self.send(snapshot)
        fresh=panel(5,path=self.path,now=snapshot["generated_at"]+1)
        stale=panel(5,path=self.path,now=snapshot["generated_at"]+1800)
        self.assertEqual(stale["state"],"stale")
        self.assertEqual(stale["recent"],fresh["recent"])
        self.assertEqual(stale["series"],fresh["series"])
        self.assertEqual(stale["summary"],fresh["summary"])
        self.assertEqual(stale["summary"]["output_tokens"],7)

    def test_symlink_is_rejected(self):
        target=Path(self.temp.name)/"target";target.write_text("untouched")
        self.path.symlink_to(target)
        with self.assertRaises(ValueError):self.send(self.snapshot)
        self.assertEqual(panel(path=self.path)["state"],"disconnected")
        self.assertEqual(target.read_text(),"untouched")


if __name__=="__main__":unittest.main()

