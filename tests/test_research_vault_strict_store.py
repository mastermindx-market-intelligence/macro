"""Fail-closed object reads used by immutable research snapshot publication."""
from __future__ import annotations

import copy
import hashlib
import json
import multiprocessing
import subprocess
import sys
from types import ModuleType
from pathlib import Path

import pytest

from engine.research_intelligence.extractor import PROMPT_VERSION, SYSTEM_PROMPT, build_prompt
from engine.research_intelligence.schema import SCHEMA
from engine.research_vault import r2_store as store_mod
from engine.research_vault.r2_store import (
    BoundedStrictReadStore,
    LocalStore,
    R2Store,
    Store,
    StrictBoundedReadStore,
    StrictConditionalWriteStore,
    StrictReadStore,
    VersionedBytes,
)


class _Body:
    def __init__(self, payload: bytes | Exception):
        self.payload = payload
        self.offset = 0
        self.read_sizes: list[int | None] = []
        self.read_limits = self.read_sizes
        self.closed = False

    def read(self, maximum: int | None = None) -> bytes:
        self.read_sizes.append(maximum)
        if isinstance(self.payload, Exception):
            raise self.payload
        if maximum is None:
            content = self.payload[self.offset :]
            self.offset = len(self.payload)
            return content
        content = self.payload[self.offset : self.offset + maximum]
        self.offset += len(content)
        return content

    def close(self) -> None:
        self.closed = True


class _FakeS3:
    def __init__(self, result: bytes | Exception):
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, _Body]:
        self.calls.append((Bucket, Key))
        if isinstance(self.result, Exception):
            raise self.result
        return {"Body": _Body(self.result)}


class _BoundedFakeS3:
    def __init__(self, payload: bytes | Exception, *, content_length: int | None = None):
        self.payload = payload
        self.content_length = content_length
        self.body: _Body | None = None

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        self.body = _Body(self.payload)
        result: dict[str, object] = {"Body": self.body}
        if self.content_length is not None:
            result["ContentLength"] = self.content_length
        return result


class _ShortChunkBody:
    def __init__(self, chunks: list[bytes]):
        self.chunks = list(chunks)
        self.read_sizes: list[int | None] = []
        self.closed = False

    def read(self, maximum: int | None = None) -> bytes:
        self.read_sizes.append(maximum)
        return self.chunks.pop(0) if self.chunks else b""

    def close(self) -> None:
        self.closed = True


class _BodyClient:
    def __init__(self, body, *, content_length: int | None = None):
        self.body = body
        self.content_length = content_length

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, object]:
        result: dict[str, object] = {"Body": self.body}
        if self.content_length is not None:
            result["ContentLength"] = self.content_length
        return result


def _install_fake_botocore(monkeypatch):
    """Install only the ``ClientError`` identity the production guard imports."""
    fake_botocore = ModuleType("botocore")
    fake_exceptions = ModuleType("botocore.exceptions")

    class FakeClientError(Exception):
        def __init__(self, code: str):
            super().__init__(code)
            self.response = {"Error": {"Code": code}}

    fake_exceptions.ClientError = FakeClientError
    fake_botocore.exceptions = fake_exceptions
    monkeypatch.setitem(sys.modules, "botocore", fake_botocore)
    monkeypatch.setitem(sys.modules, "botocore.exceptions", fake_exceptions)
    return FakeClientError


class _LegacyFailOpenStore:
    """The pre-strict structural shape used by existing fail-open consumers."""

    def get_bytes(self, key: str) -> bytes | None:
        return None

    def put_bytes(self, key: str, data: bytes,
                  content_type: str = "application/octet-stream") -> bool:
        return True

    def list_prefix(self, prefix: str) -> list[str]:
        return []

    def exists(self, key: str) -> bool:
        return False

    def upload_time(self, key: str) -> str | None:
        return None


def _local_conditional_worker(root, key, payload, barrier, results):
    """Spawn-safe contender used to prove the LocalStore lock crosses processes."""
    store = LocalStore(root)
    barrier.wait()
    try:
        outcome = store.put_bytes_strict_conditional(
            key, payload, expected_version=None, content_type="application/json",
        )
        results.put((payload, outcome, None))
    except BaseException as exc:  # pragma: no cover - surfaced in the parent assertion
        results.put((payload, None, f"{type(exc).__name__}: {exc}"))


def test_strict_read_protocol_preserves_legacy_store_runtime_compatibility(tmp_path):
    legacy = _LegacyFailOpenStore()
    local = LocalStore(tmp_path / "store")
    remote = R2Store("research", client=_FakeS3(b"payload"))

    assert isinstance(legacy, Store)
    assert not isinstance(legacy, StrictReadStore)
    assert not isinstance(legacy, BoundedStrictReadStore)
    assert not isinstance(legacy, StrictBoundedReadStore)
    assert not isinstance(legacy, StrictConditionalWriteStore)
    assert isinstance(local, Store)
    assert isinstance(local, StrictReadStore)
    assert isinstance(local, StrictBoundedReadStore)
    assert isinstance(local, BoundedStrictReadStore)
    assert isinstance(local, StrictConditionalWriteStore)
    assert isinstance(remote, Store)
    assert isinstance(remote, StrictReadStore)
    assert isinstance(remote, StrictBoundedReadStore)
    assert isinstance(remote, BoundedStrictReadStore)
    assert isinstance(remote, StrictConditionalWriteStore)


def test_local_strict_read_returns_bytes_or_authoritative_missing(tmp_path):
    store = LocalStore(tmp_path / "store")
    store.put_bytes("snapshots/one.json", b'{"version": 1}')

    assert store.get_bytes_strict("snapshots/one.json") == b'{"version": 1}'
    assert store.get_bytes_strict("snapshots/missing.json") is None


def test_local_strict_read_propagates_traversal_and_read_errors(tmp_path, monkeypatch):
    store = LocalStore(tmp_path / "store")
    with pytest.raises(ValueError, match="unsafe key"):
        store.get_bytes_strict("../escape.json")

    store.put_bytes("snapshots/one.json", b"payload")

    real_open = store_mod.os.open

    def denied(path, flags, *args, **kwargs):
        if path == "one.json":
            raise PermissionError("read denied")
        return real_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(store_mod.os, "open", denied)
    with pytest.raises(PermissionError, match="read denied"):
        store.get_bytes_strict("snapshots/one.json")


def test_local_strict_bounded_read_caps_before_buffering_and_keeps_missing_narrow(tmp_path):
    store = LocalStore(tmp_path / "store")
    store.put_bytes("snapshots/exact.bin", b"1234")
    store.put_bytes("snapshots/large.bin", b"12345")

    assert store.get_bytes_strict_bounded("snapshots/exact.bin", 4) == b"1234"
    assert store.get_bytes_strict_bounded("snapshots/missing.bin", 4) is None
    with pytest.raises(ValueError, match="bounded read limit"):
        store.get_bytes_strict_bounded("snapshots/large.bin", 4)
    with pytest.raises(ValueError, match="unsafe key"):
        store.get_bytes_strict_bounded("../escape.bin", 4)


def test_local_strict_reads_reject_symlinks_that_escape_store_root(tmp_path):
    store = LocalStore(tmp_path / "store")
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside-secret")
    (store.root / "linked.bin").symlink_to(outside)

    with pytest.raises(ValueError, match="symlink"):
        store.get_bytes_strict("linked.bin")
    with pytest.raises(ValueError, match="symlink"):
        store.get_bytes_strict_bounded("linked.bin", 64)


def test_r2_strict_read_softens_only_explicit_client_not_found(monkeypatch):
    ClientError = _install_fake_botocore(monkeypatch)
    for code in ("404", "NoSuchKey", "NotFound"):
        store = R2Store("research", client=_FakeS3(ClientError(code)))
        assert store.get_bytes_strict("snapshots/one.json") is None


def test_r2_strict_read_returns_payload_and_propagates_other_failures(monkeypatch):
    ClientError = _install_fake_botocore(monkeypatch)
    client = _FakeS3(b"immutable bytes")
    store = R2Store("research", client=client)
    assert store.get_bytes_strict("snapshots/one.json") == b"immutable bytes"
    assert client.calls == [("research", "snapshots/one.json")]

    with pytest.raises(ClientError):
        R2Store("research", client=_FakeS3(ClientError("AccessDenied"))).get_bytes_strict(
            "snapshots/one.json")
    # The established read primitive remains deliberately fail-open for legacy
    # research ingestion callers; immutable snapshots opt into the strict one.
    assert R2Store("research", client=_FakeS3(ClientError("AccessDenied"))).get_bytes(
        "snapshots/one.json") is None
    with pytest.raises(OSError, match="network down"):
        R2Store("research", client=_FakeS3(OSError("network down"))).get_bytes_strict(
            "snapshots/one.json")
    with pytest.raises(RuntimeError, match="body failed"):
        R2Store("research", client=_FakeS3(RuntimeError("body failed"))).get_bytes_strict(
            "snapshots/one.json")


def test_r2_strict_read_rejects_unavailable_store(monkeypatch):
    monkeypatch.setattr(store_mod, "_r2_client", lambda: None)
    with pytest.raises(RuntimeError, match="unavailable"):
        R2Store("research").get_bytes_strict("snapshots/one.json")


def test_r2_strict_bounded_read_uses_header_then_max_plus_one_and_closes_body():
    exact_client = _BoundedFakeS3(b"1234", content_length=4)
    exact = R2Store("research", client=exact_client)
    assert exact.get_bytes_strict_bounded("snapshots/exact.bin", 4) == b"1234"
    assert exact_client.body is not None
    assert exact_client.body.read_sizes == [5, 1]
    assert exact_client.body.closed

    # A malicious/incorrect header cannot evade the streaming ``max + 1`` cap.
    lied_client = _BoundedFakeS3(b"12345", content_length=4)
    with pytest.raises(ValueError, match="bounded read limit"):
        R2Store("research", client=lied_client).get_bytes_strict_bounded(
            "snapshots/too-large.bin", 4
        )
    assert lied_client.body is not None
    assert lied_client.body.read_sizes == [5]
    assert lied_client.body.closed

    # An honest oversized header is rejected before body buffering, but the
    # response stream is still closed deterministically.
    announced_client = _BoundedFakeS3(b"12345", content_length=5)
    with pytest.raises(ValueError, match="bounded read limit"):
        R2Store("research", client=announced_client).get_bytes_strict_bounded(
            "snapshots/too-large.bin", 4
        )
    assert announced_client.body is not None
    assert announced_client.body.read_sizes == []
    assert announced_client.body.closed


def test_r2_strict_bounded_read_drains_short_chunks_before_accepting_exact_length():
    exact_body = _ShortChunkBody([b"12", b"34", b""])
    assert R2Store(
        "research", client=_BodyClient(exact_body, content_length=4)
    ).get_bytes_strict_bounded("snapshots/exact.bin", 4) == b"1234"
    assert exact_body.read_sizes == [5, 3, 1]
    assert exact_body.closed

    # The first short chunk equals the trusted object and hash prefix, but a
    # trailing byte still has to be observed before exact presence is claimed.
    trailing_body = _ShortChunkBody([b"1234", b"5"])
    with pytest.raises(ValueError, match="bounded read limit"):
        R2Store(
            "research", client=_BodyClient(trailing_body, content_length=4)
        ).get_bytes_strict_bounded("snapshots/trailing.bin", 4)
    assert trailing_body.read_sizes == [5, 1]
    assert trailing_body.closed


def test_r2_strict_reads_require_closeable_response_bodies():
    class NoCloseBody:
        def read(self, maximum=None):
            return b"payload"

    client = _BodyClient(NoCloseBody(), content_length=7)
    with pytest.raises(RuntimeError, match="not closeable"):
        R2Store("research", client=client).get_bytes_strict_bounded("snapshots/one.bin", 7)
    with pytest.raises(RuntimeError, match="not closeable"):
        R2Store("research", client=client).get_bytes_strict("snapshots/one.bin")


def test_r2_strict_bounded_read_rejects_oversized_chunks_and_pathological_fragmentation():
    class OversizedChunkBody:
        closed = False

        def read(self, maximum):
            return b"x" * (maximum + 1)

        def close(self):
            self.closed = True

    oversized = OversizedChunkBody()
    with pytest.raises(RuntimeError, match="more bytes than requested"):
        R2Store("research", client=_BodyClient(oversized)).get_bytes_strict_bounded(
            "snapshots/oversized-chunk.bin", 16
        )
    assert oversized.closed

    class OneByteBody:
        closed = False

        def read(self, maximum):
            return b"x"

        def close(self):
            self.closed = True

    fragmented = OneByteBody()
    with pytest.raises(RuntimeError, match="iteration limit"):
        R2Store("research", client=_BodyClient(fragmented)).get_bytes_strict_bounded(
            "snapshots/fragmented.bin", 16_384
        )
    assert fragmented.closed


def test_r2_strict_bounded_read_propagates_body_failure_after_closing():
    client = _BoundedFakeS3(RuntimeError("timeout"))
    with pytest.raises(RuntimeError, match="timeout"):
        R2Store("research", client=client).get_bytes_strict_bounded(
            "snapshots/one.bin", 16
        )
    assert client.body is not None
    assert client.body.read_sizes == [17]
    assert client.body.closed


def test_r2_strict_bounded_read_softens_only_authoritative_not_found(monkeypatch):
    ClientError = _install_fake_botocore(monkeypatch)
    assert R2Store("research", client=_FakeS3(ClientError("NoSuchKey"))).get_bytes_strict_bounded(
        "snapshots/missing.bin", 16
    ) is None
    with pytest.raises(ClientError):
        R2Store("research", client=_FakeS3(ClientError("AccessDenied"))).get_bytes_strict_bounded(
            "snapshots/forbidden.bin", 16
        )
def test_local_bounded_read_rejects_giant_object_before_read(tmp_path, monkeypatch):
    store = LocalStore(tmp_path / "store")
    store.put_bytes("objects/giant.bin", b"x" * 1024)
    reads = []
    original = store_mod.os.read

    def observed_read(descriptor, amount):
        reads.append((descriptor, amount))
        return original(descriptor, amount)

    monkeypatch.setattr(store_mod.os, "read", observed_read)
    with pytest.raises(RuntimeError, match="exceeds maximum"):
        store.get_bytes_strict_bounded(
            "objects/giant.bin", expected_byte_length=1, max_byte_length=1,
        )
    assert reads == []


def test_local_bounded_read_rejects_leaf_and_parent_symlinks(tmp_path):
    store = LocalStore(tmp_path / "store")
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"safe")
    leaf = store.root / "leaf.bin"
    leaf.symlink_to(outside)
    with pytest.raises(RuntimeError):
        store.get_bytes_strict_bounded(
            "leaf.bin", expected_byte_length=4, max_byte_length=4,
        )

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "object.bin").write_bytes(b"safe")
    (store.root / "linked").symlink_to(outside_dir, target_is_directory=True)
    with pytest.raises(RuntimeError):
        store.get_bytes_strict_bounded(
            "linked/object.bin", expected_byte_length=4, max_byte_length=4,
        )


def test_local_bounded_read_detects_growth_after_fstat(tmp_path, monkeypatch):
    store = LocalStore(tmp_path / "store")
    path = store.root / "object.bin"
    path.write_bytes(b"safe")
    original = store_mod.os.read
    grown = False

    def grow_then_read(descriptor, amount):
        nonlocal grown
        if not grown:
            grown = True
            with path.open("ab") as handle:
                handle.write(b"!")
        return original(descriptor, amount)

    monkeypatch.setattr(store_mod.os, "read", grow_then_read)
    with pytest.raises(RuntimeError, match="changed during read"):
        store.get_bytes_strict_bounded(
            "object.bin", expected_byte_length=4, max_byte_length=4,
        )


class _BoundedS3:
    def __init__(self, *, head, get):
        self.head = head
        self.get = get
        self.head_calls = []
        self.get_calls = []

    def head_object(self, **kwargs):
        self.head_calls.append(kwargs)
        if isinstance(self.head, Exception):
            raise self.head
        return self.head

    def get_object(self, **kwargs):
        self.get_calls.append(kwargs)
        if isinstance(self.get, Exception):
            raise self.get
        return self.get


def test_r2_bounded_read_preflights_head_and_binds_range_to_etag():
    body = _Body(b"safe")
    client = _BoundedS3(
        head={"ContentLength": 4, "ETag": '"etag-1"'},
        get={"ContentLength": 4, "ETag": '"etag-1"', "Body": body},
    )
    store = R2Store("evidence", client=client)
    assert store.get_bytes_strict_bounded(
        "object", expected_byte_length=4, max_byte_length=4,
    ) == b"safe"
    assert client.get_calls == [{
        "Bucket": "evidence", "Key": "object", "Range": "bytes=0-4",
        "IfMatch": '"etag-1"',
    }]
    assert body.read_limits == [5, 1] and body.closed

    mismatch = _BoundedS3(
        head={"ContentLength": 5, "ETag": '"etag-2"'}, get=AssertionError("must not GET"),
    )
    with pytest.raises(RuntimeError, match="exceeds maximum"):
        R2Store("evidence", client=mismatch).get_bytes_strict_bounded(
            "object", expected_byte_length=4, max_byte_length=4,
        )
    assert mismatch.get_calls == []

    for missing_etag in ({"ContentLength": 4}, {"ContentLength": 4, "ETag": ""}):
        unbound = _BoundedS3(head=missing_etag, get=AssertionError("must not GET"))
        with pytest.raises(RuntimeError, match="HEAD lacks a valid ETag"):
            R2Store("evidence", client=unbound).get_bytes_strict_bounded(
                "object", expected_byte_length=4, max_byte_length=4,
            )
        assert unbound.get_calls == []

    for get_etag in (None, '"other"'):
        rebound_body = _Body(b"safe")
        get_response = {"ContentLength": 4, "Body": rebound_body}
        if get_etag is not None:
            get_response["ETag"] = get_etag
        rebound = _BoundedS3(
            head={"ContentLength": 4, "ETag": '"expected"'}, get=get_response,
        )
        with pytest.raises(RuntimeError, match="GET/HEAD ETag mismatch"):
            R2Store("evidence", client=rebound).get_bytes_strict_bounded(
                "object", expected_byte_length=4, max_byte_length=4,
            )
        assert rebound_body.closed


def test_r2_bounded_read_closes_extra_byte_body_and_propagates_failures(monkeypatch):
    extra = _Body(b"extra")
    client = _BoundedS3(
        head={"ContentLength": 4, "ETag": '"etag"'},
        get={"ContentLength": 5, "ETag": '"etag"', "Body": extra},
    )
    with pytest.raises(RuntimeError, match="body length mismatch"):
        R2Store("evidence", client=client).get_bytes_strict_bounded(
            "object", expected_byte_length=4, max_byte_length=5,
        )
    assert extra.closed and extra.read_limits == [5]

    ClientError = _install_fake_botocore(monkeypatch)
    not_found = _BoundedS3(head=ClientError("404"), get=AssertionError("must not GET"))
    assert R2Store("evidence", client=not_found).get_bytes_strict_bounded(
        "object", expected_byte_length=4, max_byte_length=4,
    ) is None
    for failure in (ClientError("AccessDenied"), TimeoutError("head timeout")):
        with pytest.raises(type(failure)):
            R2Store(
                "evidence", client=_BoundedS3(head=failure, get=AssertionError("must not GET")),
            ).get_bytes_strict_bounded(
                "object", expected_byte_length=4, max_byte_length=4,
            )
    for failure in (ClientError("PreconditionFailed"), TimeoutError("get timeout")):
        with pytest.raises(type(failure)):
            R2Store("evidence", client=_BoundedS3(
                head={"ContentLength": 4, "ETag": '"etag"'}, get=failure,
            )).get_bytes_strict_bounded(
                "object", expected_byte_length=4, max_byte_length=4,
            )


class _ConditionalServiceModel:
    def __init__(self, members):
        self.members = members

    def operation_model(self, name):
        assert name == "PutObject"
        return type("Operation", (), {
            "input_shape": type("Shape", (), {"members": self.members})(),
        })()


class _ConditionalS3:
    def __init__(self, *, get=None, put=None, members=None):
        if members is None:
            members = {"IfMatch": object(), "IfNoneMatch": object()}
        self.meta = type("Meta", (), {
            "service_model": _ConditionalServiceModel(members),
        })()
        self.get = get
        self.put = put
        self.get_calls = []
        self.put_calls = []

    def get_object(self, **kwargs):
        self.get_calls.append(kwargs)
        if isinstance(self.get, BaseException):
            raise self.get
        return self.get

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        if isinstance(self.put, BaseException):
            raise self.put
        return self.put if self.put is not None else {}


def test_versioned_bytes_rejects_partial_or_noncanonical_states():
    assert VersionedBytes(data=None, version=None) == VersionedBytes(None, None)
    assert VersionedBytes(data=b"x", version='"etag"').data == b"x"
    with pytest.raises(ValueError, match="wholly present"):
        VersionedBytes(data=b"x", version=None)
    with pytest.raises(ValueError, match="wholly present"):
        VersionedBytes(data=None, version='"etag"')
    with pytest.raises(ValueError, match="exact bytes"):
        VersionedBytes(data=bytearray(b"x"), version='"etag"')
    with pytest.raises(ValueError, match="non-empty version"):
        VersionedBytes(data=b"x", version="")


def test_r2_versioned_read_is_bounded_closes_body_and_preserves_exact_etag():
    body = _Body(b"safe")
    client = _ConditionalS3(get={
        "Body": body, "ContentLength": 4, "ETag": '"quoted-etag"',
    })
    observed = R2Store("evidence", client=client).get_bytes_strict_bounded_versioned(
        "pointer.json", 4,
    )
    assert observed == VersionedBytes(data=b"safe", version='"quoted-etag"')
    assert client.get_calls == [{"Bucket": "evidence", "Key": "pointer.json"}]
    assert body.read_limits == [5, 1]
    assert body.closed


def test_r2_versioned_read_softens_only_404_and_rejects_unversioned_or_oversized_body(
    monkeypatch,
):
    ClientError = _install_fake_botocore(monkeypatch)
    missing = _ConditionalS3(get=ClientError("NoSuchKey"))
    assert R2Store(
        "evidence", client=missing,
    ).get_bytes_strict_bounded_versioned("missing", 16) == VersionedBytes(None, None)

    for response in (
        {"Body": _Body(b"safe"), "ContentLength": 4},
        {"Body": _Body(b"safe"), "ContentLength": 4, "ETag": ""},
    ):
        with pytest.raises(RuntimeError, match="valid ETag"):
            R2Store(
                "evidence", client=_ConditionalS3(get=response),
            ).get_bytes_strict_bounded_versioned("pointer", 4)
        assert response["Body"].closed

    oversized_body = _Body(b"12345")
    with pytest.raises(ValueError, match="bounded read limit"):
        R2Store("evidence", client=_ConditionalS3(get={
            "Body": oversized_body, "ContentLength": 5, "ETag": '"etag"',
        })).get_bytes_strict_bounded_versioned("pointer", 4)
    assert oversized_body.closed and oversized_body.read_limits == []

    denied = ClientError("AccessDenied")
    with pytest.raises(ClientError):
        R2Store(
            "evidence", client=_ConditionalS3(get=denied),
        ).get_bytes_strict_bounded_versioned("pointer", 16)


@pytest.mark.parametrize(
    ("announced", "payload"),
    ((4, b"123"), (3, b"1234")),
    ids=("short-body", "long-body"),
)
def test_r2_versioned_read_rejects_content_length_mismatch_after_closing(
    announced, payload,
):
    body = _Body(payload)
    with pytest.raises(RuntimeError, match="ContentLength/body length mismatch"):
        R2Store("evidence", client=_ConditionalS3(get={
            "Body": body, "ContentLength": announced, "ETag": '"etag"',
        })).get_bytes_strict_bounded_versioned("pointer", 4)
    assert body.closed


def test_r2_conditional_put_uses_mutually_exclusive_exact_predecessor_headers():
    client = _ConditionalS3()
    store = R2Store("evidence", client=client)
    assert store.validate_strict_conditional_write_capability() is None
    assert client.get_calls == [] and client.put_calls == []
    assert store.put_bytes_strict_conditional(
        "pointer", b"first", expected_version=None, content_type="application/json",
    ) is True
    assert store.put_bytes_strict_conditional(
        "pointer", b"second", expected_version='"etag-1"', content_type="application/json",
    ) is True
    assert client.put_calls == [
        {
            "Bucket": "evidence", "Key": "pointer", "Body": b"first",
            "ContentType": "application/json", "IfNoneMatch": "*",
        },
        {
            "Bucket": "evidence", "Key": "pointer", "Body": b"second",
            "ContentType": "application/json", "IfMatch": '"etag-1"',
        },
    ]


@pytest.mark.parametrize(
    "code", ("409", "412", "ConditionalRequestConflict", "PreconditionFailed"),
)
def test_r2_conditional_put_returns_false_only_for_authoritative_conflict(monkeypatch, code):
    ClientError = _install_fake_botocore(monkeypatch)
    store = R2Store("evidence", client=_ConditionalS3(put=ClientError(code)))
    assert store.put_bytes_strict_conditional(
        "pointer", b"candidate", expected_version='"old"',
    ) is False


def test_r2_conditional_put_propagates_operational_and_spoofed_failures(monkeypatch):
    ClientError = _install_fake_botocore(monkeypatch)
    for failure in (ClientError("AccessDenied"), ClientError("InternalError"), TimeoutError("late")):
        with pytest.raises(type(failure)):
            R2Store(
                "evidence", client=_ConditionalS3(put=failure),
            ).put_bytes_strict_conditional("pointer", b"candidate", expected_version=None)

    class SpoofedConflict(RuntimeError):
        response = {"Error": {"Code": "PreconditionFailed"}}

    with pytest.raises(SpoofedConflict):
        R2Store(
            "evidence", client=_ConditionalS3(put=SpoofedConflict("not an SDK response")),
        ).put_bytes_strict_conditional("pointer", b"candidate", expected_version=None)


@pytest.mark.parametrize(
    "members",
    ({"IfMatch": object()}, {"IfNoneMatch": object()}, {}, None),
)
def test_r2_conditional_put_fails_before_io_without_full_sdk_capability(members):
    if members is None:
        class NoModelClient:
            def put_object(self, **kwargs):
                raise AssertionError("must not PUT")

        client = NoModelClient()
    else:
        client = _ConditionalS3(members=members)
    with pytest.raises(RuntimeError, match="capability is unavailable"):
        R2Store("evidence", client=client).put_bytes_strict_conditional(
            "pointer", b"candidate", expected_version=None,
        )
    assert not getattr(client, "put_calls", [])


@pytest.mark.parametrize(
    "members", ({"IfMatch": object()}, {"IfNoneMatch": object()}, {}),
)
def test_r2_explicit_capability_preflight_requires_both_conditional_headers(members):
    client = _ConditionalS3(members=members)
    with pytest.raises(RuntimeError, match="capability is unavailable"):
        R2Store(
            "evidence", client=client,
        ).validate_strict_conditional_write_capability()
    assert client.get_calls == [] and client.put_calls == []


def test_conditional_put_validates_nominals_before_any_r2_io():
    client = _ConditionalS3()
    store = R2Store("evidence", client=client)
    with pytest.raises(TypeError, match="exact bytes"):
        store.put_bytes_strict_conditional("pointer", bytearray(b"x"), expected_version=None)
    with pytest.raises(ValueError, match="expected_version"):
        store.put_bytes_strict_conditional("pointer", b"x", expected_version="")
    with pytest.raises(ValueError, match="content_type"):
        store.put_bytes_strict_conditional(
            "pointer", b"x", expected_version=None, content_type="",
        )
    assert client.put_calls == []


def test_local_versioned_read_and_conditional_update_are_exact(tmp_path):
    store = LocalStore(tmp_path / "store")
    assert store.validate_strict_conditional_write_capability() is None
    assert store.get_bytes_strict_bounded_versioned("pointer", 16) == VersionedBytes(None, None)
    assert store.put_bytes_strict_conditional(
        "pointer", b"first", expected_version=None, content_type="application/json",
    ) is True
    first = store.get_bytes_strict_bounded_versioned("pointer", 16)
    assert first.data == b"first" and first.version
    assert store.put_bytes_strict_conditional(
        "pointer", b"lost", expected_version=None,
    ) is False
    assert store.put_bytes_strict_conditional(
        "pointer", b"second", expected_version=first.version,
    ) is True
    assert store.put_bytes_strict_conditional(
        "pointer", b"stale", expected_version=first.version,
    ) is False
    assert store.get_bytes_strict_bounded("pointer", 16) == b"second"
    with pytest.raises(ValueError, match="bounded read limit"):
        store.get_bytes_strict_bounded_versioned("pointer", 3)
    with pytest.raises(ValueError, match="unsafe key"):
        store.put_bytes_strict_conditional("../escape", b"x", expected_version=None)


def test_local_conditional_predecessor_rejects_oversize_before_hash_read(
    tmp_path, monkeypatch,
):
    store = LocalStore(tmp_path / "store")
    store.put_bytes(
        "pointer",
        b"x" * (store_mod.HARD_MAX_STRICT_CONDITIONAL_OBJECT_BYTES + 1),
    )
    reads = []
    original_read = store_mod.os.read

    def observed_read(descriptor, amount):
        reads.append((descriptor, amount))
        return original_read(descriptor, amount)

    monkeypatch.setattr(store_mod.os, "read", observed_read)
    with pytest.raises(RuntimeError, match="predecessor exceeds its byte safety limit"):
        store.put_bytes_strict_conditional(
            "pointer", b"candidate", expected_version="sha256:" + "0" * 64,
        )
    assert reads == []


def test_local_conditional_create_has_one_cross_process_winner(tmp_path):
    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(2)
    results = context.Queue()
    root = tmp_path / "store"
    LocalStore(root)
    contenders = [
        context.Process(
            target=_local_conditional_worker,
            args=(root, "snapshots/latest.json", payload, barrier, results),
        )
        for payload in (b"candidate-a", b"candidate-b")
    ]
    for contender in contenders:
        contender.start()
    outcomes = [results.get(timeout=10) for _ in contenders]
    for contender in contenders:
        contender.join(timeout=10)
        assert not contender.is_alive()
        assert contender.exitcode == 0
    assert all(error is None for _payload, _won, error in outcomes)
    assert sorted(won for _payload, won, _error in outcomes) == [False, True]
    winner = next(payload for payload, won, _error in outcomes if won)
    assert LocalStore(root).get_bytes_strict("snapshots/latest.json") == winner


def test_local_conditional_write_rejects_symlink_leaf_and_lock(tmp_path):
    store = LocalStore(tmp_path / "store")
    outside = tmp_path / "outside"
    outside.write_bytes(b"outside")
    (store.root / "pointer").symlink_to(outside)
    with pytest.raises(OSError):
        store.put_bytes_strict_conditional("pointer", b"candidate", expected_version=None)
    (store.root / "pointer").unlink()
    lock = store.root / ".strict-conditional-write.lock"
    lock.unlink()
    lock.symlink_to(outside)
    with pytest.raises(OSError):
        store.put_bytes_strict_conditional("pointer", b"candidate", expected_version=None)


# ---------------------------------------------------------------------------
# Qualitative Research Intelligence v1 contract
# ---------------------------------------------------------------------------
RIO_BODY = (
    "Goldman says real yields rose to 2.1%. Higher real yields are tightening "
    "financial conditions and pressuring long-duration assets. The thesis would "
    "weaken if real yields reverse."
)


def _rio_sample(doc_id="r1", *, body=RIO_BODY):
    import hashlib
    from engine.research_intelligence.schema import SCHEMA

    return {
        "schema": SCHEMA,
        "document": {
            "id": doc_id,
            "source_type": "institutional_research",
            "source_name": "GS",
            "institution": "Goldman Sachs",
            "desk": "Macro",
            "title": "Rates",
            "published_at": "2026-09-12T12:00:00Z",
            "content_sha256": hashlib.sha256(body.strip().encode("utf-8")).hexdigest(),
        },
        "claims": [
            {
                "statement": "Goldman says real yields rose to 2.1%.",
                "evidence": [{"quote_span": "Goldman says real yields rose to 2.1%.", "location": "opening"}],
                "numbers": ["2.1%", "99%"],
                "entities": ["real_yields"],
                "horizon": "current",
                "explicit": True,
            },
            {
                "statement": "Higher real yields are tightening financial conditions and pressuring long-duration assets.",
                "evidence": [{
                    "quote_span": "Higher real yields are tightening financial conditions and pressuring long-duration assets.",
                    "location": "opening",
                }],
                "numbers": [],
                "entities": ["real_yields", "TLT"],
                "horizon": "weeks",
                "explicit": True,
            },
        ],
        "analysis": {
            "thesis": {
                "summary": "Higher real yields are the key transmission pressure on long duration.",
                "direction": "bearish",
                "mechanism": ["higher real yields -> tighter financial conditions -> duration pressure"],
                "conviction": "moderate",
                "support_claim_indices": [0, 1],
            },
            "assumptions": [{
                "statement": "Real yields remain elevated.",
                "support_claim_indices": [0],
            }],
            "forecasts": [{
                "statement": "Long-duration assets remain pressured.",
                "horizon": "weeks",
                "confidence": "moderate",
                "support_claim_indices": [1],
            }],
            "catalysts": [],
            "falsifiers": [{
                "statement": "A reversal in real yields would weaken the thesis.",
                "support_claim_indices": [0, 1],
            }],
            "counterarguments": [],
            "implications": [{
                "statement": "TLT remains exposed to duration pressure.",
                "assets": ["TLT"],
                "direction": "bearish",
                "order": 1,
                "support_claim_indices": [1],
            }],
            "belief_delta": {"statement": "", "support_claim_indices": []},
            "consensus_relation": {"statement": "", "support_claim_indices": []},
            "uncertainties": [{
                "statement": "The future path of real yields remains uncertain.",
                "support_claim_indices": [0],
            }],
        },
        "authority": "descriptive_research_only",
    }


def _rio_from_extraction_prompt(user: str, *, body=RIO_BODY):
    import json
    identity_text = user.split("DOCUMENT IDENTITY:\n", 1)[1].split("\n\nOUTPUT SHAPE:", 1)[0]
    obj = _rio_sample(body=body)
    obj["document"] = json.loads(identity_text)
    return obj


def test_rio_validate_forces_descriptive_authority():
    from engine.research_intelligence.schema import validate_rio
    obj = _rio_sample(); obj["authority"] = "trade_now"
    assert validate_rio(obj)["authority"] == "descriptive_research_only"


def test_rio_identity_mismatch_rejected():
    from engine.research_intelligence.schema import validate_rio
    with pytest.raises(ValueError, match="does not match"):
        validate_rio(_rio_sample("wrong"), expected_document_id="expected")


def test_rio_requires_substantive_claim():
    from engine.research_intelligence.schema import validate_rio
    obj = _rio_sample(); obj["claims"] = []
    with pytest.raises(ValueError, match="substantive claim"):
        validate_rio(obj)


def test_rio_prompt_binds_digest_and_quote_grounding_contract():
    from engine.research_intelligence.extractor import build_prompt
    from engine.research_intelligence.schema import SCHEMA
    system, user = build_prompt(
        {"id": "r1", "source_type": "institutional_research", "title": "Rates"},
        RIO_BODY,
    )
    assert SCHEMA in system
    assert "quote_span" in system
    assert "support_claim_indices" in system
    assert "untrusted source content" in system
    assert "content_sha256" in user
    assert RIO_BODY in user


def test_rio_parser_accepts_json_fence_and_verifies_quotes():
    import json
    from engine.research_intelligence.extractor import parse_model_output
    obj = _rio_sample()
    raw = "```json\n" + json.dumps(obj) + "\n```"
    out = parse_model_output(
        raw,
        expected_document_id="r1",
        expected_document=obj["document"],
        source_body=RIO_BODY,
    )
    assert out["document"]["id"] == "r1"
    assert len(out["claims"]) == 2
    assert out["claims"][0]["numbers"] == ["2.1%"]


def test_rio_projections_are_descriptive_only_and_preserve_epistemic_layers():
    from engine.research_intelligence.projection import claim_edges, summary_points

    points = summary_points(_rio_sample())
    assert points[0]["epistemic_layer"] == "model_synthesis"
    assert points[0]["text"].startswith("Higher real yields")
    assert points[0]["support_claim_indices"] == [0, 1]
    assert [point["epistemic_layer"] for point in points[1:]] == [
        "source_claim", "source_claim"
    ]
    assert [point["support_claim_indices"] for point in points[1:]] == [[0], [1]]
    assert all(point["authority"] == "descriptive_research_only" for point in points)
    assert all(point["source_document_id"] == "r1" for point in points)
    assert all(
        point["source_content_sha256"] == _rio_sample()["document"]["content_sha256"]
        for point in points
    )

    edges = claim_edges(_rio_sample())
    assert {e["entity"] for e in edges} == {"real_yields"}
    assert all(e["authority"] == "descriptive_research_only" for e in edges)
    assert all(e["epistemic_layer"] == "source_claim" for e in edges)
    assert all(e["entity_grounding"] == "quote_mention" for e in edges)
    assert all(e["entity"] != "TLT" for e in edges)
    assert all(e["source_content_sha256"] == _rio_sample()["document"]["content_sha256"] for e in edges)
    assert all(e["evidence_sha256"] for e in edges)
    assert all("quote_span" not in e for e in edges)


def test_rio_projections_reject_claims_without_grounded_evidence():
    from engine.research_intelligence.projection import claim_edges, summary_points

    obj = _rio_sample()
    obj["claims"][0]["evidence"] = []
    for project in (summary_points, claim_edges):
        with pytest.raises(ValueError, match="grounded evidence"):
            project(obj)


def test_rio_projections_redact_private_source_claim_text():
    import json
    from engine.research_intelligence.projection import claim_edges, summary_points

    obj = _rio_sample()
    points = summary_points(obj)
    source_rows = [row for row in points if row["epistemic_layer"] == "source_claim"]
    assert len(source_rows) == len(obj["claims"])
    assert all(row["text"] == "" for row in source_rows)
    assert all(row["text_visibility"] == "private_rio_only" for row in source_rows)
    assert all(len(row["claim_statement_sha256"]) == 64 for row in source_rows)

    edges = claim_edges(obj)
    assert all("statement" not in row for row in edges)
    assert all(len(row["statement_sha256"]) == 64 for row in edges)
    encoded = json.dumps({"points": points, "edges": edges})
    assert "Real yields rose to 2.1%." not in encoded
    assert "Higher real yields are tightening financial conditions." not in encoded


def test_rio_projection_rejects_verbatim_text_from_non_supporting_claim():
    from engine.research_intelligence.projection import summary_points

    obj = _rio_sample()
    obj["analysis"]["thesis"].update({
        "summary": obj["claims"][1]["evidence"][0]["quote_span"],
        "support_claim_indices": [0],
    })
    with pytest.raises(ValueError, match="verbatim private evidence"):
        summary_points(obj)


def test_rio_claim_edges_use_structural_unresolved_entity_state():
    from engine.research_intelligence.projection import claim_edges

    obj = _rio_sample()
    obj["claims"][0]["entities"] = []
    unresolved = [row for row in claim_edges(obj) if row["claim_index"] == 0]
    assert len(unresolved) == 1
    assert unresolved[0]["entity"] is None
    assert unresolved[0]["entity_grounding"] == "unresolved"

    obj = _rio_sample()
    obj["claims"][0].update({
        "statement": "Unresolved exposure.",
        "evidence": [{"quote_span": "unresolved exposure"}],
        "entities": ["__unresolved__"],
    })
    literal = [row for row in claim_edges(obj) if row["claim_index"] == 0]
    assert literal[0]["entity"] == "__unresolved__"
    assert literal[0]["entity_grounding"] == "quote_mention"


def test_rio_bad_model_output_fails_closed():
    from engine.research_intelligence.extractor import analyze_document
    def call(*args, **kwargs):
        return "not-json", "fake", "m"
    out = analyze_document(
        {"id": "r1", "source_type": "institutional_research"},
        RIO_BODY, model_id="m", call=call,
    )
    assert out["state"] == "invalid_model_output"
    assert out["rio"] is None


def test_rio_valid_model_output_is_validated():
    import json
    from engine.research_intelligence.extractor import analyze_document
    def call(_system, user, **kwargs):
        return json.dumps(_rio_from_extraction_prompt(user)), "fake", "m"
    out = analyze_document(
        {"id": "r1", "source_type": "institutional_research"},
        RIO_BODY, model_id="m", call=call,
    )
    assert out["state"] == "ok"
    assert out["rio"]["authority"] == "descriptive_research_only"
    assert out["requested_model"] == "m"
    assert out["prompt_version"] == "mastermind.research_intelligence.extractor.v1"
    assert len(out["prompt_contract_sha256"]) == 64
    assert len(out["prompt_sha256"]) == 64


def test_rio_vault_adapter_preserves_report_identity():
    import json
    from engine.research_intelligence.vault_adapter import analyze_vault_report
    def call(_system, user, **kwargs):
        return json.dumps(_rio_from_extraction_prompt(user)), "fake", "m"
    out = analyze_vault_report(
        {"id": "r1", "institution": "Goldman Sachs", "desk": "Macro", "title": "Rates"},
        RIO_BODY, model_id="m", call=call,
    )
    assert out["state"] == "ok"
    assert out["rio"]["document"]["id"] == "r1"
    assert out["rio"]["document"]["institution"] == "Goldman Sachs"


def test_rio_default_call_records_actual_fallback_model(monkeypatch):
    from types import SimpleNamespace
    from engine import llm_auth
    from engine.research_intelligence.extractor import _default_call

    class Messages:
        def create(self, **kwargs):
            return SimpleNamespace(content=[SimpleNamespace(type="text", text="{}")], usage=None)
    client = SimpleNamespace(messages=Messages())
    monkeypatch.setattr(llm_auth, "build_providers", lambda *a, **k: [{"name": "fallback"}])
    def make_call(_providers, fn, **_kwargs):
        text, reason, _resp = fn(client, "served-fallback-model")
        return text, reason, "deepseek"
    monkeypatch.setattr(llm_auth, "make_call", make_call)
    raw, provider, model = _default_call(
        "system", "user", model_id="requested-model", max_tokens=64,
    )
    assert raw == "{}"
    assert provider == "deepseek"
    assert model == "served-fallback-model"


def test_rio_rejects_model_mutation_of_canonical_document_identity():
    from engine.research_intelligence.schema import validate_rio
    obj = _rio_sample()
    expected = dict(obj["document"])
    obj["document"]["title"] = "Different report"
    with pytest.raises(ValueError, match="document.title does not match"):
        validate_rio(obj, expected_document_id="r1", expected_document=expected)


def test_rio_non_boolean_explicit_never_becomes_explicit():
    from engine.research_intelligence.schema import validate_rio
    obj = _rio_sample()
    obj["claims"][0]["explicit"] = "false"
    assert validate_rio(obj)["claims"][0]["explicit"] is False


def test_rio_drops_fabricated_statement_even_with_real_quote():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    obj = _rio_sample()
    obj["claims"][0]["statement"] = "GS recommends clients sell ALL equities immediately."
    out = parse_model_output(
        json.dumps(obj),
        expected_document_id="r1",
        expected_document=obj["document"],
        source_body=RIO_BODY,
    )
    assert len(out["claims"]) == 1
    assert out["claims"][0]["statement"].startswith("Higher real yields")
    assert out["analysis"]["thesis"]["support_claim_indices"] == [0]


def test_rio_drops_statement_backed_by_unrelated_real_evidence():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    obj = _rio_sample()
    obj["claims"][0]["statement"] = obj["claims"][1]["statement"]
    out = parse_model_output(
        json.dumps(obj),
        expected_document_id="r1",
        expected_document=obj["document"],
        source_body=RIO_BODY,
    )
    assert len(out["claims"]) == 1
    assert out["claims"][0]["statement"].startswith("Higher real yields")


def test_rio_rejects_negation_stripped_from_inner_evidence():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    body = "Goldman does not expect inflation to rise this year."
    obj = _rio_sample(body=body)
    obj["claims"] = [{
        "statement": "inflation to rise this year",
        "evidence": [{"quote_span": "inflation to rise this year"}],
        "numbers": [], "entities": ["inflation"], "horizon": "current", "explicit": True,
    }]
    obj["analysis"]["thesis"]["support_claim_indices"] = [0]
    with pytest.raises(ValueError, match="no source claim survived"):
        parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=body,
        )


def test_rio_rejects_negation_stripped_even_from_full_sentence_evidence():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    body = "Goldman does not expect inflation to rise this year."
    obj = _rio_sample(body=body)
    obj["claims"] = [{
        "statement": "inflation to rise this year",
        "evidence": [{"quote_span": body}],
        "numbers": [], "entities": ["inflation"], "horizon": "current", "explicit": True,
    }]
    obj["analysis"]["thesis"]["support_claim_indices"] = [0]
    with pytest.raises(ValueError, match="no source claim survived"):
        parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=body,
        )


def test_rio_rejects_denial_modality_and_uncertainty_stripping():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    cases = [
        ("The report denies that revenue increased sharply.", "revenue increased sharply"),
        ("Management may reduce guidance next quarter.", "reduce guidance next quarter"),
        ("Policymakers cannot rule out a recession.", "a recession"),
        ("The report denies, based on new evidence, that revenue increased sharply.", "that revenue increased sharply"),
        ("Management may, subject to board approval, reduce guidance next quarter.", "reduce guidance next quarter"),
        ("We cannot rule out: a recession in 2027.", "a recession in 2027"),
        ("The report denies that\nrevenue increased sharply.", "revenue increased sharply"),
        ("Management may\nreduce guidance next quarter.", "reduce guidance next quarter"),
        ("We cannot rule out:\na recession in 2027.", "a recession in 2027"),
        ("We do not... expect inflation to rise this year.", "expect inflation to rise this year"),
        ("Aug. inflation rose sharply.", "inflation rose sharply"),
        ("See et al. for methods. Recession is unlikely.", "for methods"),
        ("Management may not, per Distrib. Guidance, raise prices.", "Guidance, raise prices"),
        ("Management may not, per distrib. Guidance, raise prices.", "Guidance, raise prices"),
        ("The filing does not say Yahoo!Finance overstated revenue.", "Finance overstated revenue"),
        ("Revenue did not exceed the prior figure, per ibid. Q3 guidance was reiterated.", "Q3 guidance was reiterated"),
        ("Management may not, per cont. Guidance, raise prices.", "Guidance, raise prices"),
        ("Der Umsatz ist nicht gestiegen im 2. Quartal 2025.", "Quartal 2025"),
    ]
    for body, stripped in cases:
        obj = _rio_sample(body=body)
        obj["claims"] = [{
            "statement": stripped,
            "evidence": [{"quote_span": stripped}],
            "numbers": [], "entities": [], "horizon": "current", "explicit": True,
        }]
        obj["analysis"]["thesis"]["support_claim_indices"] = [0]
        with pytest.raises(ValueError, match="no source claim survived"):
            parse_model_output(
                json.dumps(obj),
                expected_document_id="r1",
                expected_document=obj["document"],
                source_body=body,
            )



def test_rio_accepts_individual_claim_after_common_sentence_endings():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    cases = [
        "Demand weakened in China. Revenue fell sharply.",
        "The outlook is bad. Revenue fell sharply.",
        "The cycle ended in 2027. Revenue fell sharply.",
        "The estimate was 2.1. Revenue fell sharply.",
    ]
    for body in cases:
        obj = _rio_sample(body=body)
        obj["claims"] = [{
            "statement": "Revenue fell sharply.",
            "evidence": [{"quote_span": "Revenue fell sharply."}],
            "numbers": [], "entities": ["Revenue"], "horizon": "current", "explicit": True,
        }]
        obj["analysis"]["thesis"].update({
            "summary": "Revenue momentum deteriorated.",
            "support_claim_indices": [0],
        })
        out = parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=body,
        )
        assert out["claims"][0]["statement"] == "Revenue fell sharply."



def test_rio_accepts_finance_prefixed_sentence_claims():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    cases = [
        ("Revenue fell. $AAPL dropped 5%.", "$AAPL dropped 5%."),
        ("Revenue fell. -5% margin pressure persisted.", "-5% margin pressure persisted."),
        ("Revenue fell! €100 million was impaired.", "€100 million was impaired."),
        ("Revenue fell? +2.1% growth followed.", "+2.1% growth followed."),
        ("The price was $2. Revenue fell sharply.", "Revenue fell sharply."),
        ("The change was -2. Revenue fell sharply.", "Revenue fell sharply."),
    ]
    for body, statement in cases:
        obj = _rio_sample(body=body)
        obj["claims"] = [{
            "statement": statement,
            "evidence": [{"quote_span": statement}],
            "numbers": [], "entities": [], "horizon": "current", "explicit": True,
        }]
        obj["analysis"]["thesis"].update({
            "summary": "Market conditions changed materially.",
            "support_claim_indices": [0],
        })
        out = parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=body,
        )
        assert out["claims"][0]["statement"] == statement

def test_rio_rejects_two_sentences_collapsed_into_one_source_claim():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    body = "Demand weakened in China. Revenue fell sharply."
    obj = _rio_sample(body=body)
    obj["claims"] = [{
        "statement": body,
        "evidence": [{"quote_span": body}],
        "numbers": [], "entities": ["China", "Revenue"], "horizon": "current", "explicit": True,
    }]
    obj["analysis"]["thesis"].update({
        "summary": "Demand and revenue momentum weakened.",
        "support_claim_indices": [0],
    })
    with pytest.raises(ValueError, match="no source claim survived"):
        parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=body,
        )

def test_rio_accepts_complete_source_context_with_finance_abbreviations_and_commas():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    body = "U.S. management may, subject to board approval, reduce guidance next quarter."
    obj = _rio_sample(body=body)
    obj["claims"] = [{
        "statement": body,
        "evidence": [{"quote_span": body}],
        "numbers": [], "entities": ["U.S."], "horizon": "next quarter", "explicit": True,
    }]
    obj["analysis"]["thesis"]["support_claim_indices"] = [0]
    out = parse_model_output(
        json.dumps(obj),
        expected_document_id="r1",
        expected_document=obj["document"],
        source_body=body,
    )
    assert out["claims"][0]["statement"] == body


def test_validate_rio_rejects_partial_statement_evidence_overlap():
    from engine.research_intelligence.schema import validate_rio

    obj = _rio_sample()
    obj["claims"][0]["statement"] = "real yields rose to 2.1%."
    obj["claims"][0]["evidence"] = [{
        "quote_span": "Goldman says real yields rose to 2.1%.",
        "location": "opening",
    }]
    with pytest.raises(ValueError, match="not grounded by its evidence"):
        validate_rio(obj)


def test_rio_rejects_short_verbatim_thesis_summary_before_projection():
    import json
    from engine.research_intelligence.extractor import parse_model_output
    from engine.research_intelligence.projection import summary_points

    body = "Rates rose."
    obj = _rio_sample(body=body)
    obj["claims"] = [{
        "statement": body,
        "evidence": [{"quote_span": body}],
        "numbers": [], "entities": ["rates"], "horizon": "current", "explicit": True,
    }]
    obj["analysis"]["thesis"].update({
        "summary": body,
        "support_claim_indices": [0],
    })
    with pytest.raises(ValueError, match="thesis.*verbatim"):
        parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=body,
        )
    with pytest.raises(ValueError, match="verbatim private evidence"):
        summary_points(obj)


def test_rio_multi_evidence_statement_may_match_one_verified_context_unit():
    from engine.research_intelligence.schema import validate_rio

    obj = _rio_sample()
    obj["claims"][0]["evidence"].append({
        "quote_span": "Higher real yields are tightening financial conditions and pressuring long-duration assets."
    })
    out = validate_rio(obj)
    assert len(out["claims"][0]["evidence"]) == 2


def test_rio_clause_mode_rejects_multi_sentence_evidence():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    obj = _rio_sample()
    combined = RIO_BODY
    obj["claims"] = [{
        "statement": combined,
        "evidence": [{"quote_span": combined}],
        "numbers": ["2.1%"], "entities": [], "horizon": "current", "explicit": True,
    }]
    obj["analysis"]["thesis"]["support_claim_indices"] = [0]
    with pytest.raises(ValueError, match="no source claim survived"):
        parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=RIO_BODY,
        )


def test_rio_rejects_verbatim_thesis_summary_before_projection():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    obj = _rio_sample()
    obj["analysis"]["thesis"]["summary"] = (
        "Higher real yields are tightening financial conditions and pressuring long-duration assets."
    )
    with pytest.raises(ValueError, match="thesis.*verbatim"):
        parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=RIO_BODY,
        )


def test_rio_drops_uncited_claim_and_remaps_synthesis_support():
    import json
    from engine.research_intelligence.extractor import parse_model_output
    obj = _rio_sample()
    obj["claims"].insert(0, {
        "statement": "Fabricated unsupported claim.",
        "evidence": [{"quote_span": "this sentence does not exist", "location": "fake"}],
        "numbers": [], "entities": ["FAKE"], "horizon": "", "explicit": True,
    })
    obj["analysis"]["thesis"]["support_claim_indices"] = [0, 1, 2]
    obj["analysis"]["forecasts"][0]["support_claim_indices"] = [0, 2]
    raw = json.dumps(obj)
    out = parse_model_output(
        raw,
        expected_document_id="r1",
        expected_document=obj["document"],
        source_body=RIO_BODY,
    )
    assert len(out["claims"]) == 2
    assert all("Fabricated" not in claim["statement"] for claim in out["claims"])
    assert out["analysis"]["thesis"]["support_claim_indices"] == [0, 1]
    assert out["analysis"]["forecasts"][0]["support_claim_indices"] == [1]


def test_rio_refuses_document_when_no_claim_has_verified_quote():
    import json
    from engine.research_intelligence.extractor import parse_model_output
    obj = _rio_sample()
    for claim in obj["claims"]:
        claim["evidence"] = [{"quote_span": "not in source", "location": "fake"}]
    with pytest.raises(ValueError, match="no source claim survived"):
        parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=RIO_BODY,
        )


def test_shared_qualitative_quote_verifier_is_reused():
    from engine.qual_extraction import citation_normalize, quote_span_verified
    assert quote_span_verified(RIO_BODY, "real yields rose to 2.1%")
    assert not quote_span_verified(RIO_BODY, "a made up sentence")
    assert citation_normalize("2.1%") == "2.1%"


def test_rio_uncertainty_requires_grounded_claim_support():
    from engine.research_intelligence.schema import validate_rio
    obj = _rio_sample()
    obj["analysis"]["uncertainties"] = [
        {"statement": "Supported uncertainty", "support_claim_indices": [0]},
        {"statement": "Unsupported uncertainty", "support_claim_indices": [999]},
    ]
    out = validate_rio(obj)
    assert out["analysis"]["uncertainties"] == [
        {"statement": "Supported uncertainty", "support_claim_indices": [0]}
    ]


def test_rio_no_provider_configuration_has_distinct_typed_state(monkeypatch):
    from engine import llm_auth
    from engine.research_intelligence.extractor import analyze_document

    monkeypatch.setattr(llm_auth, "build_providers", lambda *_args, **_kwargs: [])
    out = analyze_document(
        {"id": "r1", "source_type": "institutional_research"},
        RIO_BODY,
        model_id="requested-model",
    )
    assert out["state"] == "providers_unavailable"
    assert out["rio"] is None
    assert out["error_code"] == "NO_PROVIDER_AVAILABLE"
    assert out["provider"] == ""
    assert out["model"] == ""


def test_rio_provider_exception_is_typed_without_leaking_message():
    import json
    from engine.research_intelligence.extractor import analyze_document

    def call(*args, **kwargs):
        raise RuntimeError("provider down; api_key=sk-secret-value")

    out = analyze_document(
        {"id": "r1", "source_type": "institutional_research"},
        RIO_BODY, model_id="m", call=call,
    )
    assert out["state"] == "call_failed"
    assert out["rio"] is None
    assert out["requested_model"] == "m"
    assert out["error_class"] == "RuntimeError"
    assert "error" not in out
    encoded = json.dumps(out)
    assert "provider down" not in encoded
    assert "sk-secret-value" not in encoded


def test_rio_document_hash_binds_exact_input_bytes():
    import hashlib, json
    from engine.research_intelligence.extractor import build_prompt
    body = "  leading space\n" + RIO_BODY + "\ntrailing space  "
    _system, user = build_prompt(
        {"id": "r1", "source_type": "institutional_research"}, body,
    )
    identity_text = user.split("DOCUMENT IDENTITY:\n", 1)[1].split("\n\nOUTPUT SHAPE:", 1)[0]
    identity = json.loads(identity_text)
    assert identity["content_sha256"] == hashlib.sha256(body.encode("utf-8")).hexdigest()
    assert user.endswith(body)


def test_rio_accepts_exact_han_quote_grounding():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    body = "中国流动性正在改善，但房地产风险仍然存在。"
    obj = _rio_sample(body=body)
    obj["claims"] = [{
        "statement": body,
        "evidence": [{"quote_span": body}],
        "numbers": [],
        "entities": ["中国流动性"],
        "horizon": "current",
        "explicit": True,
    }]
    obj["analysis"] = {
        "thesis": {
            "summary": "流动性改善，但房地产风险仍在。",
            "direction": "mixed",
            "mechanism": [],
            "conviction": "",
            "support_claim_indices": [0],
        },
        "assumptions": [], "forecasts": [], "catalysts": [],
        "falsifiers": [], "counterarguments": [], "implications": [],
        "belief_delta": {"statement": "", "support_claim_indices": []},
        "consensus_relation": {"statement": "", "support_claim_indices": []},
        "uncertainties": [],
    }
    out = parse_model_output(
        json.dumps(obj, ensure_ascii=False),
        expected_document_id="r1",
        expected_document=obj["document"],
        source_body=body,
    )
    assert out["claims"][0]["evidence"] == [{"quote_span": body}]


def test_rio_rejects_quote_that_is_only_a_substring_of_another_token():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    body = "Corporate earnings improved."
    obj = _rio_sample(body=body)
    obj["claims"] = [{
        "statement": "Rates improved.",
        "evidence": [{"quote_span": "rate"}],
        "numbers": [], "entities": [], "horizon": "", "explicit": True,
    }]
    obj["analysis"]["thesis"]["support_claim_indices"] = [0]
    with pytest.raises(ValueError, match="no source claim survived"):
        parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=body,
        )


def test_rio_valid_output_requires_explicit_serving_provenance():
    import json
    from engine.research_intelligence.extractor import analyze_document

    for provider, served_model in (("fake", ""), ("", "served-model")):
        def call(_system, user, **_kwargs):
            return json.dumps(_rio_from_extraction_prompt(user)), provider, served_model

        out = analyze_document(
            {"id": "r1", "source_type": "institutional_research"},
            RIO_BODY,
            model_id="requested-model",
            call=call,
        )
        assert out["state"] == "model_provenance_unavailable"
        assert out["rio"] is None
        assert out["provider"] == provider
        assert out["model"] == served_model


def test_rio_analyze_uses_normalized_canonical_document_id():
    import json
    from engine.research_intelligence.extractor import analyze_document

    def call(_system, user, **_kwargs):
        return json.dumps(_rio_from_extraction_prompt(user)), "fake", "served-model"

    out = analyze_document(
        {"id": " r1 ", "source_type": "institutional_research"},
        RIO_BODY,
        model_id="requested-model",
        call=call,
    )
    assert out["state"] == "ok"
    assert out["rio"]["document"]["id"] == "r1"


def test_rio_numbers_require_complete_numeric_tokens_inside_verified_evidence():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    body = "Revenue rose 20% in 2026."
    obj = _rio_sample(body=body)
    obj["claims"] = [{
        "statement": "Revenue rose 20% in 2026.",
        "evidence": [{"quote_span": body}],
        "numbers": ["2", "20%", "26", "2026"],
        "entities": [], "horizon": "current", "explicit": True,
    }]
    obj["analysis"]["thesis"]["support_claim_indices"] = [0]
    out = parse_model_output(
        json.dumps(obj),
        expected_document_id="r1",
        expected_document=obj["document"],
        source_body=body,
    )
    assert out["claims"][0]["numbers"] == ["20%", "2026"]


def test_rio_requires_nonempty_requested_model_before_dispatch():
    from engine.research_intelligence.extractor import analyze_document

    called = False

    def call(*_args, **_kwargs):
        nonlocal called
        called = True
        raise AssertionError("provider dispatch must not occur")

    with pytest.raises(ValueError, match="model_id is required"):
        analyze_document(
            {"id": "r1", "source_type": "institutional_research"},
            RIO_BODY,
            model_id="  ",
            call=call,
        )
    assert called is False


def test_rio_preserves_verbatim_evidence_text():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    body = "Revenue  rose\t20%."
    obj = _rio_sample(body=body)
    obj["claims"] = [{
        "statement": "Revenue rose 20%.",
        "evidence": [{"quote_span": body}],
        "numbers": ["20%"], "entities": [], "horizon": "current", "explicit": True,
    }]
    obj["analysis"]["thesis"]["support_claim_indices"] = [0]
    out = parse_model_output(
        json.dumps(obj),
        expected_document_id="r1",
        expected_document=obj["document"],
        source_body=body,
    )
    assert out["claims"][0]["evidence"] == [{"quote_span": body}]


def test_rio_rejects_overlong_evidence_instead_of_truncating_it():
    import json
    from engine.research_intelligence.extractor import parse_model_output

    body = "x" * 1601
    obj = _rio_sample(body=body)
    obj["claims"] = [{
        "statement": "Long quoted content.",
        "evidence": [{"quote_span": body}],
        "numbers": [], "entities": [], "horizon": "", "explicit": True,
    }]
    obj["analysis"]["thesis"]["support_claim_indices"] = [0]
    with pytest.raises(ValueError, match="no source claim survived"):
        parse_model_output(
            json.dumps(obj),
            expected_document_id="r1",
            expected_document=obj["document"],
            source_body=body,
        )


def test_rio_invalid_model_output_is_typed_without_raw_detail():
    import json
    from engine.research_intelligence.extractor import analyze_document

    def call(*_args, **_kwargs):
        return '{"secret":"sk-model-output"}', "fake", "served-model"

    out = analyze_document(
        {"id": "r1", "source_type": "institutional_research"},
        RIO_BODY,
        model_id="requested-model",
        call=call,
    )
    assert out["state"] == "invalid_model_output"
    assert out["rio"] is None
    assert out["error_class"] == "ValueError"
    assert "error" not in out
    assert "sk-model-output" not in json.dumps(out)

# --------------------------------------------------------------------------- #
# Qualitative Research Intelligence W2 private artifact persistence
# --------------------------------------------------------------------------- #
ROOT = Path(__file__).resolve().parents[1]
BODY = "Rates rose 2.1%. Higher rates pressure duration assets."


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _rio(document_id: str = "vault/desk/report-1", *, body: str = BODY) -> dict:
    return {
        "schema": SCHEMA,
        "document": {
            "id": document_id,
            "source_type": "institutional_research",
            "source_name": "GS",
            "institution": "Goldman Sachs",
            "desk": "Macro",
            "title": "Rates",
            "published_at": "2026-09-16T12:00:00Z",
            "content_sha256": _sha(body),
        },
        "claims": [
            {
                "statement": "Rates rose 2.1%.",
                "evidence": [{"quote_span": "Rates rose 2.1%."}],
                "numbers": ["2.1%"],
                "entities": ["rates"],
                "horizon": "current",
                "explicit": True,
            }
        ],
        "analysis": {
            "thesis": {
                "summary": "Rates are a headwind for duration assets.",
                "direction": "bearish",
                "mechanism": ["rates -> financial conditions -> duration"],
                "conviction": "moderate",
                "support_claim_indices": [0],
            },
            "assumptions": [],
            "forecasts": [],
            "catalysts": [],
            "falsifiers": [],
            "counterarguments": [],
            "implications": [],
            "belief_delta": {"statement": "", "support_claim_indices": []},
            "consensus_relation": {"statement": "", "support_claim_indices": []},
            "uncertainties": [],
        },
        "authority": "descriptive_research_only",
    }


def _analysis(
    document_id: str = "vault/desk/report-1",
    *,
    body: str = BODY,
    rio: dict | None = None,
) -> dict:
    payload = copy.deepcopy(rio or _rio(document_id, body=body))
    system, user = build_prompt(payload["document"], body)
    identity_text = user.split("DOCUMENT IDENTITY:\n", 1)[1].split("\n\nOUTPUT SHAPE:", 1)[0]
    return {
        "state": "ok",
        "document": json.loads(identity_text),
        "rio": payload,
        "provider": "fake-provider",
        "model": "served-model",
        "requested_model": "requested-model",
        "prompt_version": PROMPT_VERSION,
        "prompt_contract_sha256": _sha(PROMPT_VERSION + "\n" + SYSTEM_PROMPT),
        "prompt_sha256": _sha(system + "\n" + user),
    }


def _rio_from_prompt(user: str) -> dict:
    identity_text = user.split("DOCUMENT IDENTITY:\n", 1)[1].split("\n\nOUTPUT SHAPE:", 1)[0]
    identity = json.loads(identity_text)
    return _rio(identity["id"], body=BODY) | {"document": identity}


class _GuardedStore(LocalStore):
    def __init__(self, root: Path):
        super().__init__(root)
        self.block_writes = False

    def put_bytes_strict_conditional(self, *args, **kwargs):
        if self.block_writes:
            raise AssertionError("idempotent persistence must not write again")
        return super().put_bytes_strict_conditional(*args, **kwargs)


class _AmbiguousPointerStore(LocalStore):
    def __init__(self, root: Path):
        super().__init__(root)
        self.raise_after_pointer_write = False

    def put_bytes_strict_conditional(self, key, data, **kwargs):
        result = super().put_bytes_strict_conditional(key, data, **kwargs)
        if self.raise_after_pointer_write and key.endswith("/latest.json"):
            self.raise_after_pointer_write = False
            raise OSError("reply lost after committed pointer write")
        return result


class _RejectPointerStore(LocalStore):
    def __init__(self, root: Path):
        super().__init__(root)
        self.reject_pointer = False
        self.pointer_calls = 0

    def put_bytes_strict_conditional(self, key, data, **kwargs):
        if self.reject_pointer and key.endswith("/latest.json"):
            self.pointer_calls += 1
            return False
        return super().put_bytes_strict_conditional(key, data, **kwargs)


def test_artifact_store_create_and_latest_round_trip(tmp_path):
    from engine.research_intelligence.store import (
        artifact_object_key,
        latest_pointer_key,
        load_latest_research_intelligence,
        persist_analysis,
    )

    store = LocalStore(tmp_path / "store")
    receipt = persist_analysis(store, _analysis(), source_body=BODY)
    assert receipt.state == "created"
    assert receipt.previous_artifact_sha256 is None
    assert receipt.reconciled is False
    assert receipt.pointer_key == latest_pointer_key("vault/desk/report-1")
    assert "vault/desk/report-1" not in receipt.pointer_key
    assert receipt.artifact_key == artifact_object_key(
        "vault/desk/report-1",
        receipt.artifact_sha256,
    )

    stored = load_latest_research_intelligence(store, "vault/desk/report-1")
    assert stored is not None
    assert stored.rio == _rio()
    assert stored.receipt["requested_model"] == "requested-model"
    assert stored.receipt["provider"] == "fake-provider"
    assert stored.receipt["model"] == "served-model"
    assert stored.artifact_sha256 == receipt.artifact_sha256
    assert stored.rio_sha256 == receipt.rio_sha256
    assert stored.artifact_key == receipt.artifact_key
    assert stored.pointer_key == receipt.pointer_key
    assert stored.is_latest is True
    assert isinstance(stored.pointer_version, str) and stored.pointer_version


def test_artifact_store_same_content_is_noop_without_second_write(tmp_path):
    from engine.research_intelligence.store import persist_analysis

    store = _GuardedStore(tmp_path / "store")
    first = persist_analysis(store, _analysis(), source_body=BODY)
    store.block_writes = True
    second = persist_analysis(store, copy.deepcopy(_analysis()), source_body=BODY)
    assert second.state == "unchanged"
    assert second.artifact_sha256 == first.artifact_sha256
    assert second.previous_artifact_sha256 == first.artifact_sha256


def test_artifact_store_correction_requires_exact_predecessor_and_preserves_versions(tmp_path):
    from engine.research_intelligence.store import (
        ResearchIntelligenceConflict,
        ResearchIntelligenceCorrectionRequired,
        load_latest_research_intelligence,
        load_research_intelligence_version,
        persist_analysis,
    )

    store = LocalStore(tmp_path / "store")
    first = persist_analysis(store, _analysis(), source_body=BODY)
    corrected = _analysis()
    corrected["rio"]["analysis"]["thesis"][
        "summary"
    ] = "Corrected duration-pressure interpretation."

    with pytest.raises(ResearchIntelligenceCorrectionRequired) as missing:
        persist_analysis(store, corrected, source_body=BODY)
    assert missing.value.code == "correction_requires_predecessor"

    with pytest.raises(ResearchIntelligenceConflict) as stale:
        persist_analysis(
            store,
            corrected,
            source_body=BODY,
            expected_current_artifact_sha256="0" * 64,
        )
    assert stale.value.code == "predecessor_mismatch"

    second = persist_analysis(
        store,
        corrected,
        source_body=BODY,
        expected_current_artifact_sha256=first.artifact_sha256,
    )
    assert second.state == "corrected"
    assert second.previous_artifact_sha256 == first.artifact_sha256
    latest = load_latest_research_intelligence(store, corrected["rio"]["document"]["id"])
    assert latest is not None and latest.rio == corrected["rio"]
    historical = load_research_intelligence_version(
        store,
        corrected["rio"]["document"]["id"],
        first.artifact_sha256,
    )
    assert historical.rio == _rio()
    assert historical.is_latest is False


def test_artifact_store_stale_correction_is_refused_without_rewind(tmp_path):
    from engine.research_intelligence.store import (
        ResearchIntelligenceConflict,
        load_latest_research_intelligence,
        persist_analysis,
    )

    store = LocalStore(tmp_path / "store")
    first = persist_analysis(store, _analysis(), source_body=BODY)
    second_analysis = _analysis()
    second_analysis["rio"]["analysis"]["thesis"]["summary"] = "Second interpretation."
    second = persist_analysis(
        store,
        second_analysis,
        source_body=BODY,
        expected_current_artifact_sha256=first.artifact_sha256,
    )
    third_analysis = _analysis()
    third_analysis["rio"]["analysis"]["thesis"]["summary"] = "Stale third interpretation."

    with pytest.raises(ResearchIntelligenceConflict) as conflict:
        persist_analysis(
            store,
            third_analysis,
            source_body=BODY,
            expected_current_artifact_sha256=first.artifact_sha256,
        )
    assert conflict.value.code == "predecessor_mismatch"
    latest = load_latest_research_intelligence(store, _rio()["document"]["id"])
    assert latest is not None and latest.artifact_sha256 == second.artifact_sha256


def test_artifact_duplicate_replay_reconciles_after_predecessor_advanced(tmp_path):
    from engine.research_intelligence.store import persist_analysis

    store = _GuardedStore(tmp_path / "store")
    first = persist_analysis(store, _analysis(), source_body=BODY)
    corrected = _analysis()
    corrected["rio"]["analysis"]["thesis"]["summary"] = "Corrected interpretation."
    second = persist_analysis(
        store,
        corrected,
        source_body=BODY,
        expected_current_artifact_sha256=first.artifact_sha256,
    )
    store.block_writes = True

    replay = persist_analysis(
        store,
        copy.deepcopy(corrected),
        source_body=BODY,
        expected_current_artifact_sha256=first.artifact_sha256,
    )
    assert replay.state == "unchanged"
    assert replay.artifact_sha256 == second.artifact_sha256
    assert replay.previous_artifact_sha256 == second.artifact_sha256


def test_artifact_store_reconciles_exact_ambiguous_pointer_completion(tmp_path):
    from engine.research_intelligence.store import (
        load_latest_research_intelligence,
        persist_analysis,
    )

    store = _AmbiguousPointerStore(tmp_path / "store")
    first = persist_analysis(store, _analysis(), source_body=BODY)
    corrected = _analysis()
    corrected["rio"]["analysis"]["thesis"]["summary"] = "Ambiguous but committed correction."
    store.raise_after_pointer_write = True

    receipt = persist_analysis(
        store,
        corrected,
        source_body=BODY,
        expected_current_artifact_sha256=first.artifact_sha256,
    )
    assert receipt.state == "corrected"
    assert receipt.reconciled is True
    latest = load_latest_research_intelligence(store, corrected["rio"]["document"]["id"])
    assert latest is not None and latest.artifact_sha256 == receipt.artifact_sha256


def test_artifact_pointer_conflict_is_not_retried_or_overwritten(tmp_path):
    from engine.research_intelligence.store import (
        ResearchIntelligenceConflict,
        load_latest_research_intelligence,
        persist_analysis,
    )

    store = _RejectPointerStore(tmp_path / "store")
    first = persist_analysis(store, _analysis(), source_body=BODY)
    corrected = _analysis()
    corrected["rio"]["analysis"]["thesis"]["summary"] = "Rejected correction."
    store.reject_pointer = True

    with pytest.raises(ResearchIntelligenceConflict) as conflict:
        persist_analysis(
            store,
            corrected,
            source_body=BODY,
            expected_current_artifact_sha256=first.artifact_sha256,
        )
    assert conflict.value.code == "pointer_conflict"
    assert store.pointer_calls == 1
    latest = load_latest_research_intelligence(store, corrected["rio"]["document"]["id"])
    assert latest is not None and latest.artifact_sha256 == first.artifact_sha256


def test_artifact_store_fails_closed_on_malformed_or_dangling_state(tmp_path):
    from engine.research_intelligence.store import (
        ResearchIntelligenceInvalid,
        latest_pointer_key,
        load_latest_research_intelligence,
        persist_analysis,
    )

    malformed = LocalStore(tmp_path / "malformed")
    pointer_path = malformed.root / latest_pointer_key(_rio()["document"]["id"])
    pointer_path.parent.mkdir(parents=True, exist_ok=True)
    pointer_path.write_bytes(b'{"not":"a lawful pointer"}')
    with pytest.raises(ResearchIntelligenceInvalid) as invalid:
        load_latest_research_intelligence(malformed, _rio()["document"]["id"])
    assert invalid.value.code == "pointer_invalid"

    dangling = LocalStore(tmp_path / "dangling")
    receipt = persist_analysis(dangling, _analysis(), source_body=BODY)
    (dangling.root / receipt.artifact_key).unlink()
    with pytest.raises(ResearchIntelligenceInvalid) as missing:
        load_latest_research_intelligence(dangling, _rio()["document"]["id"])
    assert missing.value.code == "artifact_missing"


def test_artifact_store_rejects_valid_but_noncanonical_pointer(tmp_path):
    from engine.research_intelligence.store import (
        ResearchIntelligenceInvalid,
        load_latest_research_intelligence,
        persist_analysis,
    )

    store = LocalStore(tmp_path / "store")
    receipt = persist_analysis(store, _analysis(), source_body=BODY)
    pointer_path = store.root / receipt.pointer_key
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    pointer_path.write_text(
        json.dumps(pointer, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with pytest.raises(ResearchIntelligenceInvalid) as invalid:
        load_latest_research_intelligence(store, receipt.document_id)
    assert invalid.value.code == "pointer_noncanonical"


def test_artifact_store_rejects_duplicate_pointer_keys(tmp_path):
    from engine.research_intelligence.store import (
        ResearchIntelligenceInvalid,
        load_latest_research_intelligence,
        persist_analysis,
    )

    store = LocalStore(tmp_path / "store")
    receipt = persist_analysis(store, _analysis(), source_body=BODY)
    pointer_path = store.root / receipt.pointer_key
    raw = pointer_path.read_text(encoding="utf-8")
    pointer_path.write_text(
        raw[:-1] + ',"schema":"mastermind.research_intelligence.pointer.v1"}',
        encoding="utf-8",
    )

    with pytest.raises(ResearchIntelligenceInvalid) as invalid:
        load_latest_research_intelligence(store, receipt.document_id)
    assert invalid.value.code == "pointer_invalid"


def test_artifact_store_rejects_fabricated_grounding_before_io(tmp_path):
    from engine.research_intelligence.store import ResearchIntelligenceInvalid, persist_analysis

    analysis = _analysis()
    analysis["rio"]["claims"][0]["statement"] = "The Fed cut rates immediately."
    analysis["rio"]["claims"][0]["evidence"] = [{"quote_span": "The Fed cut rates immediately."}]
    store = LocalStore(tmp_path / "store")

    with pytest.raises(ResearchIntelligenceInvalid) as invalid:
        persist_analysis(store, analysis, source_body=BODY)
    assert invalid.value.code == "grounding_invalid"
    assert list(store.root.rglob("*.json")) == []


def test_artifact_store_rejects_prompt_receipt_mismatch_before_io(tmp_path):
    from engine.research_intelligence.store import ResearchIntelligenceInvalid, persist_analysis

    analysis = _analysis()
    analysis["prompt_sha256"] = "0" * 64
    store = LocalStore(tmp_path / "store")

    with pytest.raises(ResearchIntelligenceInvalid) as invalid:
        persist_analysis(store, analysis, source_body=BODY)
    assert invalid.value.code == "analysis_receipt_mismatch"
    assert list(store.root.rglob("*.json")) == []


def test_artifact_store_rejects_non_success_analysis_before_io(tmp_path):
    from engine.research_intelligence.store import ResearchIntelligenceInvalid, persist_analysis

    analysis = _analysis()
    analysis["state"] = "invalid_model_output"
    analysis["rio"] = None
    store = LocalStore(tmp_path / "store")

    with pytest.raises(ResearchIntelligenceInvalid) as invalid:
        persist_analysis(store, analysis, source_body=BODY)
    assert invalid.value.code == "analysis_not_successful"
    assert list(store.root.rglob("*.json")) == []


def test_artifact_store_rejects_oversized_private_rio_before_io(tmp_path):
    from engine.research_intelligence.store import RIO_MAX_BYTES, ResearchIntelligenceInvalid
    from engine.research_intelligence.store import persist_analysis

    sentences = [f"Claim {index} " + ("x" * 900) + "." for index in range(90)]
    body = " ".join(sentences)
    rio = _rio(body=body)
    rio["claims"] = [
        {
            "statement": sentence,
            "evidence": [{"quote_span": sentence}],
            "numbers": [],
            "entities": ["claim"],
            "horizon": "current",
            "explicit": True,
        }
        for sentence in sentences
    ]
    rio["analysis"]["thesis"]["support_claim_indices"] = [0]
    analysis = _analysis(body=body, rio=rio)
    store = LocalStore(tmp_path / "store")

    with pytest.raises(ResearchIntelligenceInvalid) as too_large:
        persist_analysis(store, analysis, source_body=body)
    assert too_large.value.code == "rio_too_large"
    assert RIO_MAX_BYTES <= 1024 * 1024
    assert list(store.root.rglob("*.json")) == []


def test_vault_adapter_persists_full_success_receipt_only(tmp_path):
    from engine.research_intelligence.store import load_latest_research_intelligence
    from engine.research_intelligence.vault_adapter import analyze_and_persist_vault_report

    store = LocalStore(tmp_path / "store")

    def good_call(_system, user, **_kwargs):
        return json.dumps(_rio_from_prompt(user)), "fake-provider", "served-model"

    result = analyze_and_persist_vault_report(
        {
            "id": "vault/desk/report-1",
            "institution": "Goldman Sachs",
            "title": "Rates",
        },
        BODY,
        model_id="requested-model",
        store=store,
        call=good_call,
    )
    assert result["state"] == "ok"
    assert result["persistence"]["state"] == "created"
    stored = load_latest_research_intelligence(store, "vault/desk/report-1")
    assert stored is not None
    assert stored.receipt["requested_model"] == "requested-model"
    assert stored.receipt["provider"] == "fake-provider"
    assert stored.receipt["model"] == "served-model"

    def bad_call(*_args, **_kwargs):
        return "not-json", "fake-provider", "served-model"

    failed = analyze_and_persist_vault_report(
        {
            "id": "vault/desk/report-2",
            "institution": "Goldman Sachs",
            "title": "Rates",
        },
        BODY,
        model_id="requested-model",
        store=store,
        call=bad_call,
    )
    assert failed["state"] == "invalid_model_output"
    assert failed["persistence"] is None
    assert load_latest_research_intelligence(store, "vault/desk/report-2") is None


def test_research_intelligence_store_cli_put_and_read_views(tmp_path):
    store_dir = tmp_path / "store"
    analysis_path = tmp_path / "analysis.json"
    body_path = tmp_path / "report.md"
    analysis_path.write_text(json.dumps(_analysis(), ensure_ascii=False), encoding="utf-8")
    body_path.write_text(BODY, encoding="utf-8")
    base = [
        sys.executable,
        "-m",
        "scripts.research_intelligence_store",
        "--local",
        str(store_dir),
    ]

    put = subprocess.run(
        [
            *base,
            "put",
            "--analysis",
            str(analysis_path),
            "--source-body",
            str(body_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert put.returncode == 0, put.stderr
    receipt = json.loads(put.stdout)
    assert receipt["state"] == "created"
    assert receipt["document_id"] == "vault/desk/report-1"

    safe = subprocess.run(
        [*base, "show", "--document-id", "vault/desk/report-1"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert safe.returncode == 0, safe.stderr
    safe_view = json.loads(safe.stdout)
    assert safe_view["schema"] == "mastermind.research_intelligence.read.v1"
    assert safe_view["view"] == "safe_summary"
    assert safe_view["artifact_sha256"] == receipt["artifact_sha256"]
    assert safe_view["receipt"]["provider"] == "fake-provider"
    assert "Rates rose 2.1%." not in safe.stdout
    assert safe_view["summary_points"]

    private = subprocess.run(
        [
            *base,
            "show",
            "--document-id",
            "vault/desk/report-1",
            "--private-rio",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert private.returncode == 0, private.stderr
    private_view = json.loads(private.stdout)
    assert private_view["view"] == "private_rio"
    assert private_view["rio"]["claims"][0]["statement"] == "Rates rose 2.1%."
    assert private_view["receipt"]["model"] == "served-model"

    historical = subprocess.run(
        [
            *base,
            "show",
            "--document-id",
            "vault/desk/report-1",
            "--artifact-sha256",
            receipt["artifact_sha256"],
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert historical.returncode == 0, historical.stderr
    historical_view = json.loads(historical.stdout)
    assert historical_view["artifact_sha256"] == receipt["artifact_sha256"]
    assert historical_view["is_latest"] is False


def test_artifact_preserves_exact_prompt_identity_while_rio_stays_normalized(tmp_path):
    from engine.research_intelligence.extractor import analyze_document
    from engine.research_intelligence.store import (
        load_latest_research_intelligence,
        persist_analysis,
    )

    document = {
        "id": "vault/desk/report-identity",
        "source_type": "institutional_research",
        "source_name": "GS  Global",
        "institution": "Goldman  Sachs",
        "desk": "Macro",
        "title": "Rates  Outlook",
        "published_at": "2026-09-16T12:00:00Z",
    }

    def call(_system, user, **_kwargs):
        identity_text = user.split("DOCUMENT IDENTITY:\n", 1)[1].split("\n\nOUTPUT SHAPE:", 1)[0]
        identity = json.loads(identity_text)
        rio = _rio(identity["id"], body=BODY)
        rio["document"] = identity
        return json.dumps(rio), "fake-provider", "served-model"

    analysis = analyze_document(
        document,
        BODY,
        model_id="requested-model",
        call=call,
    )
    assert analysis["state"] == "ok"
    assert analysis["document"]["source_name"] == "GS  Global"
    assert analysis["rio"]["document"]["source_name"] == "GS Global"

    store = LocalStore(tmp_path / "store")
    receipt = persist_analysis(store, analysis, source_body=BODY)
    stored = load_latest_research_intelligence(store, document["id"])
    assert stored is not None
    assert stored.artifact_sha256 == receipt.artifact_sha256
    assert stored.receipt["document"]["source_name"] == "GS  Global"
    assert stored.rio["document"]["source_name"] == "GS Global"


def test_artifact_store_requires_exact_w1_analyzed_body_bytes(tmp_path):
    from engine.research_intelligence.store import (
        ResearchIntelligenceInvalid,
        persist_analysis,
    )

    padded_body = f"\n  {BODY}  \n"
    with pytest.raises(ResearchIntelligenceInvalid) as mismatch:
        persist_analysis(
            LocalStore(tmp_path / "store"),
            _analysis(body=BODY),
            source_body=padded_body,
        )
    assert mismatch.value.code == "source_body_mismatch"


def test_vault_adapter_preserves_exact_source_bytes_through_persistence(tmp_path):
    from engine.research_intelligence.store import load_latest_research_intelligence
    from engine.research_intelligence.vault_adapter import (
        analyze_and_persist_vault_report,
    )

    body = f"\n  {BODY}  \n"
    store = LocalStore(tmp_path / "store")

    def good_call(_system, user, **_kwargs):
        return json.dumps(_rio_from_prompt(user)), "fake-provider", "served-model"

    result = analyze_and_persist_vault_report(
        {
            "id": "vault/desk/exact-bytes",
            "institution": "Example Bank",
            "title": "Exact bytes",
        },
        body,
        model_id="requested-model",
        store=store,
        call=good_call,
    )
    assert result["state"] == "ok"
    assert result["persistence"]["state"] == "created"

    stored = load_latest_research_intelligence(store, "vault/desk/exact-bytes")
    assert stored is not None
    assert stored.source_content_sha256 == _sha(body)
    assert stored.rio["document"]["content_sha256"] == _sha(body)


def test_artifact_lost_reply_and_unavailable_status_stays_effect_unknown(tmp_path):
    from engine.research_intelligence.store import (
        ResearchIntelligenceEffectUnknown,
        latest_pointer_key,
        persist_analysis,
    )

    class LostArtifactReplyAndStatus(LocalStore):
        def __init__(self, root):
            super().__init__(root)
            self.unavailable_key = None
            self.artifact_write_calls = 0

        def put_bytes_strict_conditional(self, key, data, **kwargs):
            if "/objects/" not in key:
                return super().put_bytes_strict_conditional(key, data, **kwargs)
            self.artifact_write_calls += 1
            result = super().put_bytes_strict_conditional(key, data, **kwargs)
            self.unavailable_key = key
            raise OSError("reply lost after committed artifact write")

        def get_bytes_strict_bounded(self, key, maximum_bytes):
            if key == self.unavailable_key:
                raise OSError("artifact status unavailable")
            return super().get_bytes_strict_bounded(key, maximum_bytes)

    store = LostArtifactReplyAndStatus(tmp_path / "store")
    with pytest.raises(ResearchIntelligenceEffectUnknown) as unknown:
        persist_analysis(store, _analysis(), source_body=BODY)

    assert unknown.value.code == "artifact_effect_unknown"
    assert store.artifact_write_calls == 1
    assert not (store.root / latest_pointer_key(_rio()["document"]["id"])).exists()


def test_pointer_lost_reply_and_unavailable_status_stays_effect_unknown(tmp_path):
    from engine.research_intelligence.store import (
        ResearchIntelligenceEffectUnknown,
        persist_analysis,
    )

    class LostPointerReplyAndStatus(LocalStore):
        def __init__(self, root):
            super().__init__(root)
            self.trigger = False
            self.status_unavailable = False
            self.pointer_write_calls = 0

        def put_bytes_strict_conditional(self, key, data, **kwargs):
            result = super().put_bytes_strict_conditional(key, data, **kwargs)
            if self.trigger and key.endswith("/latest.json"):
                self.trigger = False
                self.pointer_write_calls += 1
                self.status_unavailable = True
                raise OSError("reply lost after committed pointer write")
            return result

        def get_bytes_strict_bounded_versioned(self, key, maximum_bytes):
            if self.status_unavailable and key.endswith("/latest.json"):
                raise OSError("pointer status unavailable")
            return super().get_bytes_strict_bounded_versioned(key, maximum_bytes)

    store = LostPointerReplyAndStatus(tmp_path / "store")
    first = persist_analysis(store, _analysis(), source_body=BODY)
    corrected = _analysis()
    corrected["rio"]["analysis"]["thesis"]["summary"] = "Corrected interpretation."
    store.trigger = True

    with pytest.raises(ResearchIntelligenceEffectUnknown) as unknown:
        persist_analysis(
            store,
            corrected,
            source_body=BODY,
            expected_current_artifact_sha256=first.artifact_sha256,
        )

    assert unknown.value.code == "pointer_effect_unknown"
    assert store.pointer_write_calls == 1


def test_pointer_lost_reply_then_different_winner_stays_effect_unknown(tmp_path):
    from engine.research_intelligence.store import (
        POINTER_MAX_BYTES,
        ResearchIntelligenceEffectUnknown,
        persist_analysis,
    )

    class LostPointerReplyThenSuperseded(LocalStore):
        def __init__(self, root):
            super().__init__(root)
            self.trigger = False
            self.candidate_pointer_writes = 0

        def put_bytes_strict_conditional(self, key, data, **kwargs):
            if not (self.trigger and key.endswith("/latest.json")):
                return super().put_bytes_strict_conditional(key, data, **kwargs)
            prior = super().get_bytes_strict_bounded_versioned(key, POINTER_MAX_BYTES)
            self.candidate_pointer_writes += 1
            accepted = super().put_bytes_strict_conditional(key, data, **kwargs)
            assert accepted is True
            current = super().get_bytes_strict_bounded_versioned(key, POINTER_MAX_BYTES)
            restored = super().put_bytes_strict_conditional(
                key,
                prior.data,
                expected_version=current.version,
                content_type="application/json",
            )
            assert restored is True
            self.trigger = False
            raise OSError("candidate pointer reply lost before concurrent supersession")

    store = LostPointerReplyThenSuperseded(tmp_path / "store")
    first = persist_analysis(store, _analysis(), source_body=BODY)
    corrected = _analysis()
    corrected["rio"]["analysis"]["thesis"]["summary"] = "Transient correction."
    store.trigger = True

    with pytest.raises(ResearchIntelligenceEffectUnknown) as unknown:
        persist_analysis(
            store,
            corrected,
            source_body=BODY,
            expected_current_artifact_sha256=first.artifact_sha256,
        )

    assert unknown.value.code == "pointer_effect_unknown"
    assert store.candidate_pointer_writes == 1


def test_research_intelligence_cli_rejects_duplicate_analysis_keys_before_io(tmp_path):
    store_dir = tmp_path / "store"
    analysis_path = tmp_path / "analysis.json"
    body_path = tmp_path / "report.md"
    raw = json.dumps(_analysis(), ensure_ascii=False)
    analysis_path.write_text(raw[:-1] + ',"state":"ok"}', encoding="utf-8")
    body_path.write_text(BODY, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.research_intelligence_store",
            "--local",
            str(store_dir),
            "put",
            "--analysis",
            str(analysis_path),
            "--source-body",
            str(body_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert json.loads(result.stderr)["code"] == "analysis_input_invalid"
    assert list(store_dir.rglob("*.json")) == []


def test_research_intelligence_cli_rejects_nonfinite_json_before_io(tmp_path):
    store_dir = tmp_path / "store"
    analysis_path = tmp_path / "analysis.json"
    body_path = tmp_path / "report.md"
    raw = json.dumps(_analysis(), ensure_ascii=False)
    prompt_sha = _analysis()["prompt_sha256"]
    analysis_path.write_text(
        raw.replace(f'"prompt_sha256": "{prompt_sha}"', '"prompt_sha256": NaN'),
        encoding="utf-8",
    )
    body_path.write_text(BODY, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.research_intelligence_store",
            "--local",
            str(store_dir),
            "put",
            "--analysis",
            str(analysis_path),
            "--source-body",
            str(body_path),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert json.loads(result.stderr)["code"] == "analysis_input_invalid"
    assert list(store_dir.rglob("*.json")) == []


def test_research_intelligence_cli_rejects_invalid_input_before_store_construction(
    tmp_path, monkeypatch, capsys
):
    import scripts.research_intelligence_store as cli

    analysis_path = tmp_path / "analysis.json"
    body_path = tmp_path / "report.md"
    raw = json.dumps(_analysis(), ensure_ascii=False)
    analysis_path.write_text(raw[:-1] + ',"state":"ok"}', encoding="utf-8")
    body_path.write_text(BODY, encoding="utf-8")
    store_calls = []

    def forbidden_store(*_args, **_kwargs):
        store_calls.append(True)
        raise AssertionError("invalid input must fail before store construction")

    monkeypatch.setattr(cli, "build_store", forbidden_store)
    result = cli.main(
        [
            "--local",
            str(tmp_path / "store"),
            "put",
            "--analysis",
            str(analysis_path),
            "--source-body",
            str(body_path),
        ]
    )

    assert result == 2
    assert store_calls == []
    assert json.loads(capsys.readouterr().err)["code"] == "analysis_input_invalid"
    assert not (tmp_path / "store").exists()


def test_research_intelligence_cli_regrounds_before_store_construction(
    tmp_path, monkeypatch, capsys
):
    import scripts.research_intelligence_store as cli

    analysis = _analysis()
    analysis["rio"]["claims"][0]["statement"] = "The Fed cut rates immediately."
    analysis["rio"]["claims"][0]["evidence"] = [
        {"quote_span": "The Fed cut rates immediately."}
    ]
    analysis_path = tmp_path / "analysis.json"
    body_path = tmp_path / "report.md"
    analysis_path.write_text(json.dumps(analysis), encoding="utf-8")
    body_path.write_text(BODY, encoding="utf-8")
    store_calls = []

    def forbidden_store(*_args, **_kwargs):
        store_calls.append(True)
        raise AssertionError("ungrounded analysis must fail before store construction")

    monkeypatch.setattr(cli, "build_store", forbidden_store)
    result = cli.main(
        [
            "--local",
            str(tmp_path / "store"),
            "put",
            "--analysis",
            str(analysis_path),
            "--source-body",
            str(body_path),
        ]
    )

    assert result == 2
    assert store_calls == []
    assert json.loads(capsys.readouterr().err)["code"] == "grounding_invalid"
    assert not (tmp_path / "store").exists()


@pytest.mark.parametrize(
    "body",
    [
        "Rates rose 2.1%.\nHigher rates pressure duration assets.\n",
        "Rates rose 2.1%.\r\nHigher rates pressure duration assets.\r\n",
        "Rates rose 2.1%.\rHigher rates pressure duration assets.\r",
        "\r\nRates rose 2.1%.\rHigher rates pressure duration assets.\n東京 €\r\n",
    ],
    ids=["lf", "crlf", "cr", "mixed-unicode"],
)
def test_research_intelligence_cli_preserves_source_file_newlines(tmp_path, body):
    """The file-path CLI must persist the bytes W1 actually analyzed."""
    store_dir = tmp_path / "store"
    analysis_path = tmp_path / "analysis.json"
    body_path = tmp_path / "report.md"
    analysis_path.write_text(json.dumps(_analysis(body=body)), encoding="utf-8")
    body_path.write_bytes(body.encode("utf-8"))
    base = [
        sys.executable,
        str(ROOT / "scripts/research_intelligence_store.py"),
        "--local",
        str(store_dir),
    ]
    put_args = [
        *base, "put", "--analysis", str(analysis_path),
        "--source-body", str(body_path),
    ]
    put = subprocess.run(
        put_args, cwd=tmp_path, text=True, capture_output=True, timeout=30,
    )
    assert put.returncode == 0, put.stderr
    receipt = json.loads(put.stdout)
    assert receipt["state"] == "created"

    show = subprocess.run(
        [*base, "show", "--document-id", "vault/desk/report-1"],
        cwd=tmp_path, text=True, capture_output=True, timeout=30,
    )
    assert show.returncode == 0, show.stderr
    view = json.loads(show.stdout)
    assert view["source_content_sha256"] == hashlib.sha256(body_path.read_bytes()).hexdigest()
    assert view["source_content_sha256"] == _sha(body)
    assert view["artifact_sha256"] == receipt["artifact_sha256"]
    assert view["view"] == "safe_summary"
    assert "Rates rose 2.1%." not in show.stdout

    replay = subprocess.run(
        put_args, cwd=tmp_path, text=True, capture_output=True, timeout=30,
    )
    assert replay.returncode == 0, replay.stderr
    assert json.loads(replay.stdout)["state"] == "unchanged"
    assert json.loads(replay.stdout)["artifact_sha256"] == receipt["artifact_sha256"]


@pytest.mark.parametrize("newline", ["\r\n", "\r", "\r\n\r"], ids=["crlf", "cr", "mixed"])
def test_research_intelligence_cli_rejects_newline_rewritten_receipt_before_io(
    tmp_path, monkeypatch, capsys, newline
):
    """A receipt for normalized text must not authorize the actual file bytes."""
    import scripts.research_intelligence_store as cli

    body = f"Rates rose 2.1%.{newline}Higher rates pressure duration assets.{newline}"
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    analysis_path = tmp_path / "analysis.json"
    body_path = tmp_path / "report.md"
    analysis_path.write_text(json.dumps(_analysis(body=normalized)), encoding="utf-8")
    body_path.write_bytes(body.encode("utf-8"))
    store_dir = tmp_path / "store"

    def forbidden_store(*_args, **_kwargs):
        raise AssertionError("newline-rewritten receipt reached store construction")

    monkeypatch.setattr(cli, "build_store", forbidden_store)
    result = cli.main([
        "--local", str(store_dir), "put", "--analysis", str(analysis_path),
        "--source-body", str(body_path),
    ])
    assert result == 2
    assert json.loads(capsys.readouterr().err)["code"] == "source_body_mismatch"
    assert not store_dir.exists()


# R26: synthetic research conclusions must retain their exact claim identities.
def _rio_claim_index_case():
    import hashlib
    from engine.research_intelligence.schema import SCHEMA

    sentences = [
        "Factory utilization increased sharply.",
        "Inventory accumulated across distributors.",
    ]
    body = " ".join(sentences)
    obj = {
        "schema": SCHEMA,
        "document": {
            "id": "r26-synthetic-only",
            "source_type": "institutional_research",
            "source_name": "Fictional Test Desk",
            "institution": "Fictional Test Desk",
            "desk": "",
            "title": "Synthetic claim-index control",
            "published_at": "2026-09-19",
            "content_sha256": hashlib.sha256(body.encode()).hexdigest(),
        },
        "claims": [
            {"statement": sentence, "evidence": [{"quote_span": sentence}],
             "numbers": [], "entities": [], "horizon": "", "explicit": True}
            for sentence in sentences
        ],
        "analysis": {
            "thesis": {"summary": "Operating activity strengthened.",
                       "direction": "neutral", "mechanism": [], "conviction": "",
                       "support_claim_indices": [0]},
            "assumptions": [], "forecasts": [], "catalysts": [],
            "falsifiers": [], "counterarguments": [], "implications": [],
            "belief_delta": {}, "consensus_relation": {}, "uncertainties": [],
        },
        "authority": "descriptive_research_only",
    }
    return obj, body


@pytest.mark.parametrize("bad", [None, {}, {"statement": "  "}, "not a claim", []])
@pytest.mark.parametrize("require_grounded", [False, True])
def test_rio_claim_indices_reject_structural_gaps(bad, require_grounded):
    from engine.research_intelligence.schema import validate_rio

    obj, _body = _rio_claim_index_case()
    obj["claims"].insert(0, bad)
    obj["analysis"]["thesis"]["support_claim_indices"] = [1]
    with pytest.raises(ValueError, match=r"claims\[0\]"):
        validate_rio(obj, require_grounded_claims=require_grounded)


def test_rio_claim_indices_reject_blank_middle():
    from engine.research_intelligence.schema import validate_rio

    obj, _body = _rio_claim_index_case()
    obj["claims"].insert(1, {"statement": ""})
    obj["analysis"]["thesis"]["support_claim_indices"] = [1]
    with pytest.raises(ValueError, match=r"claims\[1\]"):
        validate_rio(obj)


def test_rio_claim_indices_reject_trailing_malformed():
    from engine.research_intelligence.schema import validate_rio

    obj, _body = _rio_claim_index_case()
    obj["claims"].append(None)
    with pytest.raises(ValueError, match=r"claims\[2\]"):
        validate_rio(obj)


def test_rio_claim_indices_parser_does_not_retarget_conclusion():
    from engine.research_intelligence.extractor import parse_model_output

    obj, body = _rio_claim_index_case()
    obj["claims"].insert(0, None)
    obj["analysis"]["thesis"]["support_claim_indices"] = [1]
    with pytest.raises(ValueError, match=r"claims\[0\]"):
        parse_model_output(json.dumps(obj), expected_document_id=obj["document"]["id"],
                           expected_document=obj["document"], source_body=body)


def test_rio_claim_indices_missing_claim_cannot_gain_real_evidence():
    from engine.research_intelligence.extractor import parse_model_output

    obj, body = _rio_claim_index_case()
    obj["claims"].insert(0, {})
    obj["analysis"]["thesis"]["support_claim_indices"] = [0]
    with pytest.raises(ValueError, match=r"claims\[0\]"):
        parse_model_output(json.dumps(obj), expected_document_id=obj["document"]["id"],
                           expected_document=obj["document"], source_body=body)


def test_rio_claim_indices_analyzer_returns_typed_invalid_without_rio():
    from engine.research_intelligence.extractor import analyze_document

    obj, body = _rio_claim_index_case()
    obj["claims"].insert(0, None)
    obj["analysis"]["thesis"]["support_claim_indices"] = [1]
    calls = []

    def fake_call(*_args, **_kwargs):
        calls.append(1)
        return json.dumps(obj), "synthetic-test-provider", "synthetic-test-model"

    result = analyze_document(obj["document"], body, model_id="synthetic-test-model", call=fake_call)
    assert len(calls) == 1
    assert result["state"] == "invalid_model_output"
    assert result["rio"] is None
    assert result["error_class"] == "ValueError"
    assert "error" not in result


def test_rio_claim_indices_valid_analysis_keeps_links_and_input_unchanged():
    import copy
    from engine.research_intelligence.extractor import parse_model_output
    from engine.research_intelligence.schema import validate_rio

    obj, body = _rio_claim_index_case()
    obj["analysis"]["counterarguments"] = [
        {"statement": "Inventory growth warrants caution.", "support_claim_indices": [1]}
    ]
    original = copy.deepcopy(obj)
    result = parse_model_output(json.dumps(obj), expected_document_id=obj["document"]["id"],
                                expected_document=obj["document"], source_body=body)
    assert obj == original
    assert result["analysis"]["thesis"]["support_claim_indices"] == [0]
    assert result["analysis"]["counterarguments"][0]["support_claim_indices"] == [1]
    assert result["claims"][0]["statement"] == original["claims"][0]["statement"]
    assert result["claims"][1]["statement"] == original["claims"][1]["statement"]
    assert validate_rio(result) == result
