"""Single-attempt producer transport: hidden SDK PUT retries become explicit.

Discriminating transport tests drive the ACTUAL boto3 client (built by the store
itself from the dedicated ``R2_RESEARCH_*`` family) against a loopback-only fake
HTTP service with fake credentials. No network package install, no real store,
no real credentials — everything stays on 127.0.0.1.

Where boto3 is unavailable, the transport tests skip with an honest reason; the
refusal / validation / wiring tests never needed boto3 and still run everywhere.
"""
import http.server
import sys
import threading

import pytest

from engine.research_vault import r2_store
from scripts import ingest_research as cli

FAKE_ACCESS_KEY = "AKIAFAKEFAKEFAKEFAKE"
FAKE_SECRET_KEY = "fake-secret-not-a-real-credential"
FAKE_BUCKET = "fake-research-bucket"

_XML_500 = (b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Error><Code>InternalError</Code><Message>synthetic</Message></Error>')
_XML_503 = (b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Error><Code>ServiceUnavailable</Code><Message>synthetic</Message></Error>')
_XML_412 = (b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<Error><Code>PreconditionFailed</Code><Message>synthetic</Message></Error>')
_XML_REDIRECT = (b'<?xml version="1.0" encoding="UTF-8"?>'
                 b'<Error><Code>PermanentRedirect</Code><Message>synthetic</Message>'
                 b'<Bucket>fake-research-bucket</Bucket>'
                 b'<Endpoint>fake-research-bucket.s3.eu-west-1.amazonaws.com</Endpoint>'
                 b'</Error>')

# Planned PUT outcomes beyond the plain status codes: a regional redirect
# (botocore's S3RegionRedirectorv2 retries these outside the retry budget) and
# a fully transmitted request whose response is lost before it is answered.
_REDIRECT_STATUSES = (301, 307)
_LOST_RESPONSE = 0


class _FakeR2Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):  # noqa: A002 — keep test output clean
        pass

    def _respond(self, status: int, body: bytes, extra: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/xml")
        self.send_header("Content-Length", str(len(body)))
        # Announce the close so the client's pool never reuses a socket this
        # fixture is about to drop; a silent close races a subsequent request
        # onto an already-closed connection.
        self.send_header("Connection", "close")
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()
        if body:
            self.wfile.write(body)
        self.close_connection = True

    def _consume_body(self) -> None:
        try:
            remaining = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            remaining = 0
        while remaining > 0:
            chunk = self.rfile.read(min(remaining, 65536))
            if not chunk:
                break
            remaining -= len(chunk)

    def _object_key(self) -> str:
        prefix = f"/{FAKE_BUCKET}/"
        path = self.path
        return path[len(prefix):] if path.startswith(prefix) else path

    def _next_status(self, method: str, key: str) -> int:
        with self.server.lock:
            plan = self.server.plans.get(method) or [200]
            served = self.server.served.get(method, 0)
            self.server.served[method] = served + 1
            token = f"{method}\0{key}"
            self.server.key_served[token] = self.server.key_served.get(token, 0) + 1
            if key in self.server.redirect_keys:
                return 301
            return plan[min(served, len(plan) - 1)]

    def do_PUT(self):
        self._consume_body()
        status = self._next_status("PUT", self._object_key())
        if status == _LOST_RESPONSE:
            # The request was fully received, but the response is lost: close
            # without answering anything.
            self.close_connection = True
            return
        if status in _REDIRECT_STATUSES:
            extra = {"x-amz-bucket-region": "eu-west-1"} if self.server.region_header else {}
            self._respond(status, _XML_REDIRECT, extra)
        elif status == 412:
            self._respond(status, _XML_412)
        elif status >= 400:
            self._respond(status, _XML_503 if status == 503 else _XML_500)
        else:
            self._respond(status, b"", {"ETag": '"fake-etag-1"'})

    def do_HEAD(self):
        # Only ever reached by botocore's redirector probing for the bucket
        # region after a redirect lacked the x-amz-bucket-region header.
        with self.server.lock:
            self.server.heads += 1
        self._respond(200, b"", {"x-amz-bucket-region": "eu-west-1"})

    def do_GET(self):
        self._consume_body()
        status = self._next_status("GET", self._object_key())
        if status >= 400:
            self._respond(status, _XML_503 if status == 503 else _XML_500)
        else:
            self._respond(status, b"fake-transport-payload", {"ETag": '"fake-etag-1"'})


class _FakeR2Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self):
        super().__init__(("127.0.0.1", 0), _FakeR2Handler)
        self.plans: dict[str, list[int]] = {}
        self.served: dict[str, int] = {}
        self.key_served: dict[str, int] = {}
        self.redirect_keys: set[str] = set()
        self.region_header = True
        self.heads = 0
        self.lock = threading.Lock()

    def plan(self, method: str, statuses: list[int], *, region_header: bool = True) -> None:
        with self.lock:
            self.plans[method] = list(statuses)
            self.served[method] = 0
            self.region_header = region_header

    def count(self, method: str) -> int:
        with self.lock:
            return self.served.get(method, 0)

    def key_count(self, method: str, key: str) -> int:
        with self.lock:
            return self.key_served.get(f"{method}\0{key}", 0)

    def head_count(self) -> int:
        with self.lock:
            return self.heads


@pytest.fixture
def fake_r2(monkeypatch):
    pytest.importorskip("boto3")
    server = _FakeR2Server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("R2_RESEARCH_ENDPOINT", f"http://127.0.0.1:{server.server_port}")
        monkeypatch.setenv("R2_RESEARCH_ACCESS_KEY_ID", FAKE_ACCESS_KEY)
        monkeypatch.setenv("R2_RESEARCH_SECRET_ACCESS_KEY", FAKE_SECRET_KEY)
        monkeypatch.setenv("R2_RESEARCH_BUCKET", FAKE_BUCKET)
        monkeypatch.delenv("R2_BUCKET", raising=False)
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        assert not thread.is_alive()


def _single_attempt_store() -> r2_store.R2Store:
    return r2_store.R2Store(FAKE_BUCKET, single_attempt_writes=True)


# ---------------------------------------------------------------------------
# actual boto3 transport behaviour against the loopback fake service
# ---------------------------------------------------------------------------

def test_ordinary_put_still_retries_hidden_by_sdk(fake_r2):
    fake_r2.plan("PUT", [503, 200])
    store = r2_store.R2Store(FAKE_BUCKET)
    assert store.available
    assert store._write_s3 is store._s3  # legacy stores keep the ordinary client
    assert store.put_bytes("research_inbox/x.json", b"{}") is True
    assert fake_r2.count("PUT") == 2  # the hidden adaptive SDK retry, as before


def test_generation_put_503_is_exactly_one_request_and_fails(fake_r2):
    fake_r2.plan("PUT", [503])
    store = _single_attempt_store()
    assert store.available
    assert store._write_s3 is not store._s3  # a distinct single-attempt client
    assert store.put_bytes("research_inbox/x.json", b"{}") is False
    assert fake_r2.count("PUT") == 1
    assert store.last_put_error is not None


def test_generation_put_200_is_exactly_one_request(fake_r2):
    fake_r2.plan("PUT", [200])
    store = _single_attempt_store()
    assert store.put_bytes("research_inbox/x.json", b"{}") is True
    assert fake_r2.count("PUT") == 1


def test_generation_conditional_503_raises_after_exactly_one_request(fake_r2):
    from botocore.exceptions import ClientError
    fake_r2.plan("PUT", [503])
    store = _single_attempt_store()
    with pytest.raises(ClientError):
        store.put_bytes_strict_conditional(
            "research_inbox/_processed/x.json", b"{}", expected_version=None)
    assert fake_r2.count("PUT") == 1


def test_generation_conditional_412_keeps_conflict_false_after_one_request(fake_r2):
    fake_r2.plan("PUT", [412])
    store = _single_attempt_store()
    store.validate_strict_conditional_write_capability()
    assert store.put_bytes_strict_conditional(
        "research_inbox/_processed/x.json", b"{}", expected_version='"stale-etag"') is False
    assert fake_r2.count("PUT") == 1


def test_generation_conditional_200_succeeds_after_exactly_one_request(fake_r2):
    fake_r2.plan("PUT", [200])
    store = _single_attempt_store()
    assert store.put_bytes_strict_conditional(
        "research_inbox/_processed/x.json", b"{}", expected_version=None) is True
    assert fake_r2.count("PUT") == 1


def test_read_client_keeps_its_configured_adaptive_retries(fake_r2):
    fake_r2.plan("GET", [503, 200])
    store = _single_attempt_store()
    assert store.get_bytes("research_inbox/x.json") == b"fake-transport-payload"
    assert fake_r2.count("GET") == 2  # GETs still retry transparently
    read_retries = store._s3.meta.config.retries
    write_retries = store._write_s3.meta.config.retries
    # Constructed botocore clients normalize five retries to six total attempts.
    assert read_retries.get("total_max_attempts") == 6
    assert read_retries.get("mode") == "adaptive"
    assert write_retries.get("total_max_attempts") == 1
    assert write_retries.get("mode") == "standard"


# ---------------------------------------------------------------------------
# the S3 regional redirect path must not become a hidden second PUT
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("redirect_status", list(_REDIRECT_STATUSES))
def test_generation_redirect_never_sends_a_second_put(fake_r2, redirect_status):
    # botocore's S3RegionRedirectorv2 retries a 301/307 OUTSIDE the retry
    # budget: even with total_max_attempts=1 the supplied code produced two
    # real PUTs and reported True. The guarded store must stop after one.
    fake_r2.plan("PUT", [redirect_status, 200])
    store = _single_attempt_store()
    assert store.put_bytes("research_inbox/x.json", b"{}") is False
    assert fake_r2.count("PUT") == 1
    assert isinstance(store.last_put_error, r2_store.SingleAttemptTransportViolation)


def test_generation_redirect_without_region_header_refuses_head_bucket_probe(fake_r2):
    # A 301 without x-amz-bucket-region drives the SDK redirector into its
    # HeadBucket region-probe fallback: the supplied code produced two PUTs
    # plus one HEAD. The guarded store must refuse that probe before the wire.
    fake_r2.plan("PUT", [301], region_header=False)
    store = _single_attempt_store()
    assert store.put_bytes("research_inbox/x.json", b"{}") is False
    assert fake_r2.count("PUT") == 1
    assert fake_r2.head_count() == 0
    assert isinstance(store.last_put_error, r2_store.SingleAttemptTransportViolation)


def test_generation_conditional_redirect_raises_after_one_request(fake_r2):
    fake_r2.plan("PUT", [301, 200])
    store = _single_attempt_store()
    with pytest.raises(r2_store.SingleAttemptTransportViolation):
        store.put_bytes_strict_conditional(
            "research_inbox/_processed/x.json", b"{}", expected_version=None)
    assert fake_r2.count("PUT") == 1


def test_generation_lost_response_is_one_request_and_unknown_outcome(fake_r2):
    # The PUT is fully transmitted, then the connection closes with no answer:
    # the outcome is unknown, so the store reports failure without a second
    # request — it never reinterprets that failure as "no effect".
    fake_r2.plan("PUT", [_LOST_RESPONSE])
    store = _single_attempt_store()
    assert store.put_bytes("research_inbox/x.json", b"{}") is False
    assert fake_r2.count("PUT") == 1
    assert isinstance(store.last_put_error, Exception)
    assert not isinstance(store.last_put_error, r2_store.SingleAttemptTransportViolation)


def test_generation_sequential_writes_each_get_one_fresh_attempt(fake_r2):
    fake_r2.plan("PUT", [200])
    store = _single_attempt_store()
    assert store.put_bytes("research_inbox/a.json", b"1") is True
    assert store.put_bytes("research_inbox/b.json", b"2") is True
    assert fake_r2.count("PUT") == 2
    # No attempt budget lingers in this context: the same client called
    # directly, outside a store write invocation, is refused before the wire.
    with pytest.raises(r2_store.SingleAttemptTransportViolation):
        store._write_s3.put_object(Bucket=FAKE_BUCKET, Key="research_inbox/c.json",
                                   Body=b"3")
    assert fake_r2.count("PUT") == 2


def test_concurrent_generation_writes_stay_isolated_per_call(fake_r2):
    fake_r2.plan("PUT", [200])
    store = _single_attempt_store()
    threads = 8
    results: list[bool | None] = [None] * threads
    barrier = threading.Barrier(threads)

    def write(index: int) -> None:
        barrier.wait()
        results[index] = store.put_bytes(f"research_inbox/t{index}.json", b"{}")

    workers = [threading.Thread(target=write, args=(index,)) for index in range(threads)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=30)
        assert not worker.is_alive()
    assert results == [True] * threads
    assert fake_r2.count("PUT") == threads  # exactly one request per call


def test_concurrent_redirect_write_does_not_poison_other_writes(fake_r2):
    # One thread writes a key the fake service always redirects; another writes
    # a normally served key through the SAME store and client concurrently.
    # The redirecting call fails alone, the other keeps exactly its one request.
    fake_r2.plan("PUT", [200])
    fake_r2.redirect_keys.add("research_inbox/redirect.json")
    store = _single_attempt_store()
    barrier = threading.Barrier(2)
    outcomes: dict[str, bool | None] = {}

    def write(name: str, key: str) -> None:
        barrier.wait()
        outcomes[name] = store.put_bytes(key, b"{}")

    redirected = threading.Thread(target=write, args=("redirect", "research_inbox/redirect.json"))
    plain = threading.Thread(target=write, args=("plain", "research_inbox/plain.json"))
    redirected.start(); plain.start()
    redirected.join(timeout=30); plain.join(timeout=30)
    assert outcomes == {"redirect": False, "plain": True}
    assert fake_r2.count("PUT") == 2
    assert fake_r2.key_count("PUT", "research_inbox/plain.json") == 1
    assert fake_r2.key_count("PUT", "research_inbox/redirect.json") == 1


def test_env_retry_settings_cannot_override_the_single_attempt_client(fake_r2, monkeypatch):
    monkeypatch.setenv("AWS_MAX_ATTEMPTS", "5")
    monkeypatch.setenv("AWS_RETRY_MODE", "adaptive")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")
    fake_r2.plan("PUT", [503])
    store = _single_attempt_store()
    resolved = store._write_s3.meta.config.retries
    assert resolved.get("total_max_attempts") == 1
    assert resolved.get("mode") == "standard"
    assert store.put_bytes("research_inbox/x.json", b"{}") is False
    assert fake_r2.count("PUT") == 1  # the environment did not buy SDK retries back


def test_corrupted_resolved_retry_policy_refuses_the_write_client(monkeypatch):
    pytest.importorskip("boto3")
    from botocore.config import Config
    monkeypatch.setenv("R2_RESEARCH_ENDPOINT", "http://127.0.0.1:9")
    monkeypatch.setenv("R2_RESEARCH_ACCESS_KEY_ID", FAKE_ACCESS_KEY)
    monkeypatch.setenv("R2_RESEARCH_SECRET_ACCESS_KEY", FAKE_SECRET_KEY)
    unusable_policies = (
        {"max_attempts": 5, "mode": "adaptive"},   # hidden retries again
        {"total_max_attempts": 3, "mode": "standard"},
        {"total_max_attempts": 1, "mode": "legacy"},
    )
    for policy in unusable_policies:
        monkeypatch.setattr(
            r2_store, "_research_s3_config",
            lambda retries, _policy=policy: Config(retries=dict(_policy)))
        with pytest.raises(RuntimeError, match="retry policy"):
            r2_store.R2Store(FAKE_BUCKET, single_attempt_writes=True)


def test_single_attempt_store_without_credentials_stays_gracefully_unavailable(monkeypatch):
    for name in ("R2_RESEARCH_ENDPOINT", "R2_RESEARCH_ACCESS_KEY_ID",
                 "R2_RESEARCH_SECRET_ACCESS_KEY", "R2_RESEARCH_BUCKET"):
        monkeypatch.delenv(name, raising=False)
    store = r2_store.R2Store(FAKE_BUCKET, single_attempt_writes=True)
    assert store.available is False
    assert store._s3 is None and store._write_s3 is None
    assert store.put_bytes("k", b"v") is False


# ---------------------------------------------------------------------------
# refusals and validation (no boto3 required — clients are never constructed)
# ---------------------------------------------------------------------------

def test_injected_client_with_single_attempt_refuses(monkeypatch):
    def unconstructed():
        raise AssertionError("no client may be built for an injected client")
    monkeypatch.setattr(r2_store, "_r2_client", unconstructed)
    monkeypatch.setattr(r2_store, "_r2_write_client", unconstructed)
    with pytest.raises(ValueError, match="injected"):
        r2_store.R2Store(FAKE_BUCKET, client=object(), single_attempt_writes=True)


def test_missing_write_client_never_falls_back_to_read_client(monkeypatch):
    monkeypatch.setenv("R2_RESEARCH_ENDPOINT", "http://127.0.0.1:9")
    monkeypatch.setenv("R2_RESEARCH_ACCESS_KEY_ID", FAKE_ACCESS_KEY)
    monkeypatch.setenv("R2_RESEARCH_SECRET_ACCESS_KEY", FAKE_SECRET_KEY)
    ordinary = object()  # the ordinary read client DID build...
    monkeypatch.setattr(r2_store, "_r2_client", lambda: ordinary)
    monkeypatch.setattr(r2_store, "_r2_write_client", lambda: None)  # ...the write one did not
    with pytest.raises(RuntimeError, match="single-attempt"):
        r2_store.R2Store(FAKE_BUCKET, single_attempt_writes=True)
    # And a legacy store in the same situation keeps its existing soft degradation.
    assert r2_store.R2Store(FAKE_BUCKET)._s3 is ordinary


@pytest.mark.parametrize("bad", [1, 0, "true", "False", None, ["False"]])
def test_single_attempt_flag_is_strict_bool(monkeypatch, bad):
    def unconstructed():
        raise AssertionError("flag validation must precede any client construction")
    monkeypatch.setattr(r2_store, "_r2_client", unconstructed)
    monkeypatch.setattr(r2_store, "_r2_write_client", unconstructed)
    with pytest.raises(ValueError, match="exact bool"):
        r2_store.R2Store(FAKE_BUCKET, single_attempt_writes=bad)
    with pytest.raises(ValueError, match="exact bool"):
        r2_store.build_store(single_attempt_writes=bad)


def test_legacy_store_selects_the_ordinary_client_dynamically():
    puts = []

    class _Injected:
        def put_object(self, **kwargs):
            puts.append(kwargs)
            return {}

    injected = _Injected()
    store = r2_store.R2Store(FAKE_BUCKET, client=injected)
    assert store._s3 is injected
    assert store._write_s3 is store._s3  # existing injection semantics preserved
    assert store.put_bytes("k", b"v") is True  # writes go through the injected client
    assert puts == [{"Bucket": FAKE_BUCKET, "Key": "k", "Body": b"v",
                     "ContentType": "application/octet-stream"}]


def test_legacy_write_client_follows_replaced_s3():
    first_puts: list[dict] = []
    second_puts: list[dict] = []

    class _Recorder:
        def __init__(self, sink):
            self.sink = sink

        def put_object(self, **kwargs):
            self.sink.append(kwargs)
            return {}

    first, second = _Recorder(first_puts), _Recorder(second_puts)
    store = r2_store.R2Store(FAKE_BUCKET, client=first)
    assert store.put_bytes("k1", b"v") is True
    assert len(first_puts) == 1 and not second_puts
    store._s3 = second  # the ordinary client is replaced after construction
    assert store._write_s3 is second  # selection follows the CURRENT _s3
    assert store.put_bytes("k2", b"v") is True
    assert len(second_puts) == 1 and len(first_puts) == 1


def _write_model_stub(members):
    from types import SimpleNamespace
    return SimpleNamespace(
        meta=SimpleNamespace(service_model=SimpleNamespace(
            operation_model=lambda name: SimpleNamespace(
                input_shape=SimpleNamespace(members=members)))))


def test_conditional_capability_inspects_the_actual_selected_write_client():
    store = r2_store.R2Store(FAKE_BUCKET, client=object())  # no SDK model at all
    with pytest.raises(RuntimeError, match="capability"):
        store.put_bytes_strict_conditional(
            "research_inbox/_processed/x.json", b"{}", expected_version=None)
    # After the injection is replaced, capability is judged on the replacement.
    store._s3 = _write_model_stub({"IfMatch": object(), "IfNoneMatch": object()})
    store.validate_strict_conditional_write_capability()


def test_conditional_capability_refuses_a_model_without_cas_members():
    store = r2_store.R2Store(FAKE_BUCKET, client=_write_model_stub({"Body": object()}))
    with pytest.raises(RuntimeError, match="capability"):
        store.put_bytes_strict_conditional(
            "research_inbox/_processed/x.json", b"{}", expected_version=None)


def test_build_store_wiring_selects_the_distinct_write_client(monkeypatch):
    read_stub, write_stub = object(), object()
    monkeypatch.setattr(r2_store, "_r2_client", lambda: read_stub)
    monkeypatch.setattr(r2_store, "_r2_write_client", lambda: write_stub)
    monkeypatch.setenv("R2_RESEARCH_BUCKET", FAKE_BUCKET)
    monkeypatch.setenv("R2_RESEARCH_ENDPOINT", "http://127.0.0.1:9")
    monkeypatch.setenv("R2_RESEARCH_ACCESS_KEY_ID", FAKE_ACCESS_KEY)
    monkeypatch.setenv("R2_RESEARCH_SECRET_ACCESS_KEY", FAKE_SECRET_KEY)
    monkeypatch.delenv("RESEARCH_LOCAL_STORE", raising=False)
    monkeypatch.delenv("R2_BUCKET", raising=False)
    store = r2_store.build_store(single_attempt_writes=True)
    assert store._s3 is read_stub and store._write_s3 is write_stub
    legacy = r2_store.build_store()
    assert legacy._s3 is read_stub and legacy._write_s3 is legacy._s3


# ---------------------------------------------------------------------------
# the identified generation CLI requests the flag; nobody else does
# ---------------------------------------------------------------------------

_SUMMARY = {"ingested": 0, "skipped": 0, "failed": 0, "needs_metadata": 0,
            "corpus_published": True, "catalog_published": True,
            "catalog_bytes": b"", "error": None, "receipts_unflushed": 0}


def test_cli_requests_single_attempt_writes_only_for_valid_generation(monkeypatch, tmp_path):
    from engine.research_vault import ingest
    observed = []
    monkeypatch.setattr(ingest, "run", lambda store, path, **kwargs: dict(_SUMMARY))

    def build(**kwargs):
        observed.append(kwargs)
        return object()

    monkeypatch.setattr(r2_store, "build_store", build)
    monkeypatch.setattr(cli, "_repo_snapshot_dir", lambda _: tmp_path / "mirror")
    monkeypatch.setattr(sys, "argv", ["ingest_research", "--generation-source-commit", "a" * 40,
                                      "--generation-run", "original-run",
                                      "--generation-evidence-path", str(tmp_path / "journal.jsonl")])
    assert cli.main() == 0
    assert observed == [{"local_dir": None, "single_attempt_writes": True}]

    observed.clear()
    monkeypatch.setattr(sys, "argv", ["ingest_research"])
    assert cli.main() == 0
    assert observed == [{"local_dir": None}]  # legacy signature, no transport option


@pytest.mark.parametrize("args", [
    ["--generation-source-commit", "a" * 39, "--generation-run", "original-run"],
    ["--generation-source-commit", "G" * 40, "--generation-run", "original-run"],
    ["--generation-source-commit", "a" * 40, "--generation-run", " original-run"],
    ["--generation-source-commit", "a" * 40],
])
def test_cli_rejects_invalid_identity_before_store(monkeypatch, tmp_path, args):
    monkeypatch.setattr(r2_store, "build_store",
                        lambda **kwargs: pytest.fail("store opened before argument validation"))
    monkeypatch.setattr(sys, "argv", ["ingest_research", *args])
    with pytest.raises(SystemExit) as exc:
        cli.main()
    assert exc.value.code == 2


def test_missing_dedicated_writer_never_becomes_available_via_read_replacement(monkeypatch):
    monkeypatch.setattr(r2_store, "_r2_client", lambda: None)
    store = _single_attempt_store()
    store._s3 = _write_model_stub({"IfMatch": object(), "IfNoneMatch": object()})
    assert store.available is False
    assert store.put_bytes("k", b"v") is False
    with pytest.raises(RuntimeError):
        store.put_bytes_strict_conditional("k", b"v", expected_version=None)


def test_generation_capability_inspects_dedicated_writer_not_read_client(monkeypatch):
    read = _write_model_stub({"IfMatch": object(), "IfNoneMatch": object()})
    write = _write_model_stub({"Body": object()})
    monkeypatch.setattr(r2_store, "_r2_client", lambda: read)
    monkeypatch.setattr(r2_store, "_r2_write_client", lambda: write)
    store = _single_attempt_store()
    with pytest.raises(RuntimeError, match="capability"):
        store.validate_strict_conditional_write_capability()


@pytest.mark.parametrize("versioned", [False, True])
def test_generation_bounded_reads_keep_existing_retry_behavior(fake_r2, versioned):
    fake_r2.plan("GET", [503, 200])
    store = _single_attempt_store()
    expected = b"fake-transport-payload"
    method = (store.get_bytes_strict_bounded_versioned if versioned
              else store.get_bytes_strict_bounded)
    result = method("research_inbox/x.json", maximum_bytes=len(expected))
    assert (result.data if versioned else result) == expected
    assert fake_r2.count("GET") == 2


def test_generation_store_factory_without_credentials_returns_none(monkeypatch):
    for name in ("R2_RESEARCH_ENDPOINT", "R2_RESEARCH_ACCESS_KEY_ID",
                 "R2_RESEARCH_SECRET_ACCESS_KEY", "RESEARCH_LOCAL_STORE", "R2_BUCKET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("R2_RESEARCH_BUCKET", FAKE_BUCKET)
    assert r2_store.build_store(single_attempt_writes=True) is None
