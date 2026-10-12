"""Behavioral publisher tests using an S3-shaped in-memory provider."""

from __future__ import annotations
import base64
import copy
from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import publish_options_alpha_candidate_r2 as publisher
from publish_options_alpha_candidate_r2 import (
    PAYLOAD_KEY,
    RECEIPT_KEY,
    PublicationConflict,
    PublicationError,
    publish_pair,
    read_pair,
    recover_pending_pair,
)
import test_options_alpha_candidate_feed as feed_tests


class Missing(Exception):
    response = {"Error": {"Code": "NoSuchKey"}}


class Precondition(Exception):
    response = {"Error": {"Code": "PreconditionFailed"}}


class Body:
    def __init__(self, b):
        self.b = b

    def read(self):
        return self.b


class FakeS3:
    def __init__(self):
        self.o = {}
        self.n = 0
        self.fail = None
        self.fail_before = None
        self.race = None
        self.race_body = None
        self.mutate_payload_on_get = False
        self.puts = []

    def _time(self):
        return datetime(2026, 8, 14, tzinfo=timezone.utc) + timedelta(seconds=self.n)

    def get_object(self, **a):
        k = a["Key"]
        if k not in self.o:
            raise Missing()
        if self.mutate_payload_on_get and k == PAYLOAD_KEY:
            self.mutate_payload_on_get = False
            self.n += 1
            self.o[k] = (b'{"mutated":true}', f'"m{self.n}"', self._time())
        x = self.o[k]
        return {"Body": Body(x[0]), "ETag": x[1]}

    def head_object(self, **a):
        if a["Key"] not in self.o:
            raise Missing()
        x = self.o[a["Key"]]
        return {"ETag": x[1], "LastModified": x[2]}

    def put_object(self, **a):
        k = a["Key"]
        old = self.o.get(k)
        if self.fail_before == k:
            self.fail_before = None
            raise RuntimeError("crash before provider effect")
        if self.race == k:
            self.race = None
            body = a["Body"] if self.race_body is None else self.race_body
            self.race_body = None
            self.n += 1
            self.o[k] = (body, f'"r{self.n}"', self._time())
            raise Precondition()
        if ("IfNoneMatch" in a and old) or (
            "IfMatch" in a and (not old or a["IfMatch"] != old[1])
        ):
            raise Precondition()
        self.n += 1
        self.o[k] = (a["Body"], f'"e{self.n}"', self._time())
        self.puts.append((k, a))
        if self.fail == k:
            self.fail = None
            raise RuntimeError("crash after provider effect")


def _clock():
    n = 0

    def f():
        nonlocal n
        n += 1
        return (
            (datetime(2026, 8, 14, tzinfo=timezone.utc) + timedelta(minutes=n))
            .isoformat()
            .replace("+00:00", "Z")
        )

    return f


def _feeds(tmp_path, monkeypatch):
    monkeypatch.setenv("COLLECT_LANE", "nightly")
    return feed_tests._publication_generations(tmp_path, monkeypatch, 4)


def _publish(s, tmp, row):
    return publish_pair(
        client=s,
        bucket="b",
        feed=copy.deepcopy(row["feed"]),
        payload=row["payload"],
        lock_path=tmp / "lock",
        now=_clock(),
    )


def test_four_generations_real_transactions_and_map_continuity(tmp_path, monkeypatch):
    s = FakeS3()
    rows = _feeds(tmp_path, monkeypatch)
    for r in rows:
        assert _publish(s, tmp_path, r) == "published"
    sealed = read_pair(s, "b")
    assert sealed and sealed.payload == rows[-1]["payload"]
    cid = rows[0]["feed"]["formed_candidates"][0]["candidate_id"]
    assert (
        sealed.receipt["candidates"][cid]["first_receipt_id"]
        != sealed.receipt["receipt_id"]
    )
    assert (
        len([x for x in s.puts if x[0] == PAYLOAD_KEY]) == 4
        and len([x for x in s.puts if x[0] == RECEIPT_KEY]) == 4
    )


def test_same_pair_noop_never_rewrites_receipt(tmp_path, monkeypatch):
    s = FakeS3()
    r = _feeds(tmp_path, monkeypatch)[0]
    assert _publish(s, tmp_path, r) == "published"
    stamp = s.o[RECEIPT_KEY][2]
    puts = len(s.puts)
    assert (
        _publish(s, tmp_path, r) == "noop"
        and s.o[RECEIPT_KEY][2] == stamp
        and len(s.puts) == puts
    )


@pytest.mark.parametrize("failed_key", [PAYLOAD_KEY, RECEIPT_KEY])
def test_crash_after_provider_effect_recovers_from_fsynced_exact_journal(
    tmp_path, monkeypatch, failed_key
):
    s = FakeS3()
    r = _feeds(tmp_path, monkeypatch)[0]
    s.fail = failed_key
    with pytest.raises(PublicationError):
        _publish(s, tmp_path, r)
    assert _publish(s, tmp_path, r) in {"published", "noop"}
    assert read_pair(s, "b")


@pytest.mark.parametrize("failed_key", [PAYLOAD_KEY, RECEIPT_KEY])
def test_continuation_crash_recovers_then_allows_next_generation(
    tmp_path, monkeypatch, failed_key
):
    s = FakeS3()
    a, b, c = _feeds(tmp_path, monkeypatch)[:3]
    assert _publish(s, tmp_path, a) == "published"
    s.fail = failed_key
    with pytest.raises(PublicationError):
        _publish(s, tmp_path, b)
    assert _publish(s, tmp_path, b) in {"published", "noop"}
    assert (
        _publish(s, tmp_path, c) == "published"
        and read_pair(s, "b").payload == c["payload"]
    )


def test_invalid_pre_effect_payload_causes_zero_provider_writes(tmp_path, monkeypatch):
    s = FakeS3()
    r = _feeds(tmp_path, monkeypatch)[0]
    with pytest.raises(PublicationError):
        publish_pair(
            client=s,
            bucket="b",
            feed=copy.deepcopy(r["feed"]),
            payload=r["payload"] + b"x",
            lock_path=tmp_path / "lock",
            now=_clock(),
        )
    assert s.puts == []


def test_wrong_payload_etag_and_duplicate_receipt_are_unsealed(tmp_path, monkeypatch):
    s = FakeS3()
    r = _feeds(tmp_path, monkeypatch)[0]
    assert _publish(s, tmp_path, r) == "published"
    import json

    receipt = json.loads(s.o[RECEIPT_KEY][0])
    receipt["r2"]["etag"] = '"wrong"'
    s.o[RECEIPT_KEY] = (
        json.dumps(receipt, separators=(",", ":")).encode(),
        s.o[RECEIPT_KEY][1],
        s.o[RECEIPT_KEY][2],
    )
    with pytest.raises(PublicationError):
        read_pair(s, "b")
    s.o[RECEIPT_KEY] = (
        b'{"schema":"x","schema":"x"}',
        s.o[RECEIPT_KEY][1],
        s.o[RECEIPT_KEY][2],
    )
    with pytest.raises(PublicationError):
        read_pair(s, "b")


def test_invalid_prior_anchor_is_rejected_before_any_put(tmp_path, monkeypatch):
    s = FakeS3()
    a, b = _feeds(tmp_path, monkeypatch)[:2]
    assert _publish(s, tmp_path, a) == "published"
    before = len(s.puts)
    bad = copy.deepcopy(b["feed"])
    bad["source_receipts"]["prior_feed"]["feed_id"] = "forged"
    bad["header"]["header_digest_sha256"] = ""
    from engine.options_alpha_candidate_feed import canonical_bytes
    import hashlib

    bad["header"]["header_digest_sha256"] = hashlib.sha256(
        canonical_bytes(bad)
    ).hexdigest()
    with pytest.raises(PublicationError):
        publish_pair(
            client=s,
            bucket="b",
            feed=bad,
            payload=canonical_bytes(bad),
            lock_path=tmp_path / "lock",
            now=_clock(),
        )
    assert len(s.puts) == before


def test_unknown_foreign_partial_and_old_receipt_new_payload_fail_closed(
    tmp_path, monkeypatch
):
    s = FakeS3()
    a, b = _feeds(tmp_path, monkeypatch)[:2]
    s.o[PAYLOAD_KEY] = (
        b["payload"],
        '"foreign"',
        datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    with pytest.raises(PublicationError):
        _publish(s, tmp_path, a)
    s = FakeS3()
    assert _publish(s, tmp_path / "x", a) == "published"
    s.o[PAYLOAD_KEY] = (
        b["payload"],
        '"bad"',
        datetime(2026, 8, 14, tzinfo=timezone.utc),
    )
    with pytest.raises(PublicationError):
        _publish(s, tmp_path / "x", b)


def test_payload_cas_race_does_not_retry_stale_plan(tmp_path, monkeypatch):
    s = FakeS3()
    a, b = _feeds(tmp_path, monkeypatch)[:2]
    assert _publish(s, tmp_path, a) == "published"
    s.race = PAYLOAD_KEY
    with pytest.raises((PublicationError, PublicationConflict)):
        _publish(s, tmp_path, b)


def test_receipt_412_with_matching_sealed_pair_heals_then_next_generation(
    tmp_path, monkeypatch
):
    s = FakeS3()
    a, b, c = _feeds(tmp_path, monkeypatch)[:3]
    assert _publish(s, tmp_path, a) == "published"
    # The conditional receipt write loses to a peer that wrote the identical
    # sealed receipt body. The publisher must accept that sealed pair, not retry
    # or overwrite it, and the immediate-prior chain must remain usable.
    s.race = RECEIPT_KEY
    assert _publish(s, tmp_path, b) == "healed"
    assert read_pair(s, "b").payload == b["payload"]
    assert _publish(s, tmp_path, c) == "published"
    assert read_pair(s, "b").payload == c["payload"]


def test_receipt_412_with_foreign_pair_refuses_without_overwrite(tmp_path, monkeypatch):
    s = FakeS3()
    a, b = _feeds(tmp_path, monkeypatch)[:2]
    assert _publish(s, tmp_path, a) == "published"
    s.race = RECEIPT_KEY
    s.race_body = b'{"schema":"foreign"}'
    before = len(s.puts)
    with pytest.raises(PublicationError):
        _publish(s, tmp_path, b)
    assert (
        len(s.puts) == before + 1
    )  # payload transition landed; receipt was never overwritten
    assert s.o[RECEIPT_KEY][0] == b'{"schema":"foreign"}'


def test_payload_readback_mutation_refuses_before_receipt_factory_put(
    tmp_path, monkeypatch
):
    s = FakeS3()
    r = _feeds(tmp_path, monkeypatch)[0]
    s.mutate_payload_on_get = True
    with pytest.raises(PublicationConflict, match="payload readback"):
        _publish(s, tmp_path, r)
    assert [key for key, _ in s.puts] == [PAYLOAD_KEY]
    assert RECEIPT_KEY not in s.o


@pytest.mark.parametrize("failed_key", [PAYLOAD_KEY, RECEIPT_KEY])
def test_pre_effect_failure_recovers_exact_journal_then_allows_next_generation(
    tmp_path, monkeypatch, failed_key
):
    s = FakeS3()
    a, b = _feeds(tmp_path, monkeypatch)[:2]
    s.fail_before = failed_key
    with pytest.raises(PublicationError):
        _publish(s, tmp_path, a)
    assert _publish(s, tmp_path, a) in {"published", "noop"}
    assert read_pair(s, "b").payload == a["payload"]
    assert _publish(s, tmp_path, b) == "published"
    assert read_pair(s, "b").payload == b["payload"]


def test_new_host_remote_prior_payload_crash_recovers_then_advances(
    tmp_path, monkeypatch
):
    s = FakeS3()
    a, b, c = _feeds(tmp_path, monkeypatch)[:3]
    old_host, new_host = tmp_path / "old-host", tmp_path / "new-host"
    assert _publish(s, old_host, a) == "published"
    assert not new_host.with_suffix(".sealed.json").exists()

    # New host has no local cache, so it must persist remote A before overwriting
    # payload B. A provider-effect crash after that payload is recoverable.
    s.fail = PAYLOAD_KEY
    with pytest.raises(PublicationError):
        _publish(s, new_host, b)
    assert _publish(s, new_host, b) in {"published", "noop"}
    sealed_b = read_pair(s, "b")
    assert sealed_b is not None and sealed_b.payload == b["payload"]

    assert _publish(s, new_host, c) == "published"
    sealed_c = read_pair(s, "b")
    assert sealed_c is not None and sealed_c.payload == c["payload"]
    cid = a["feed"]["formed_candidates"][0]["candidate_id"]
    assert (
        sealed_c.receipt["candidates"][cid]["first_receipt_id"]
        == sealed_b.receipt["candidates"][cid]["first_receipt_id"]
    )
    assert (
        sealed_c.receipt["candidates"][cid]["first_consumer_published_at"]
        == sealed_b.receipt["candidates"][cid]["first_consumer_published_at"]
    )


def test_crash_after_sealed_cache_before_journal_unlink_recovers_then_advances(
    tmp_path, monkeypatch
):
    s = FakeS3()
    a, b, c = _feeds(tmp_path, monkeypatch)[:3]
    lock = tmp_path / "lock"
    assert _publish(s, tmp_path, a) == "published"

    cache_path = lock.with_suffix(".sealed.json")
    target = base64.b64encode(b["payload"]).decode("ascii")
    real_record = publisher._record
    crash_once = True

    def crash_after_b_cache(path, value):
        nonlocal crash_once
        real_record(path, value)
        if (
            crash_once
            and path == cache_path
            and value.get("sealed", {}).get("payload") == target
        ):
            crash_once = False
            raise RuntimeError("crash after sealed cache before journal unlink")

    monkeypatch.setattr(publisher, "_record", crash_after_b_cache)
    with pytest.raises(RuntimeError, match="sealed cache"):
        _publish(s, tmp_path, b)
    assert cache_path.exists()
    assert lock.with_suffix(".transaction.json").exists()

    # Recovery must accept the locally sealed B cache despite the retained
    # B journal's A predecessor, clear that journal, and preserve the first
    # external receipt identity/time into C.
    assert _publish(s, tmp_path, b) in {"published", "noop"}
    sealed_b = read_pair(s, "b")
    assert sealed_b is not None and sealed_b.payload == b["payload"]
    assert _publish(s, tmp_path, c) == "published"
    sealed_c = read_pair(s, "b")
    assert sealed_c is not None and sealed_c.payload == c["payload"]
    cid = a["feed"]["formed_candidates"][0]["candidate_id"]
    assert (
        sealed_c.receipt["candidates"][cid]["first_receipt_id"]
        == sealed_b.receipt["candidates"][cid]["first_receipt_id"]
    )
    assert (
        sealed_c.receipt["candidates"][cid]["first_consumer_published_at"]
        == sealed_b.receipt["candidates"][cid]["first_consumer_published_at"]
    )


def test_recovery_helper_replays_only_the_fsynced_pending_bytes(tmp_path, monkeypatch):
    s = FakeS3()
    row = _feeds(tmp_path, monkeypatch)[0]
    lock = tmp_path / "lock"
    s.fail = PAYLOAD_KEY
    with pytest.raises(PublicationError):
        publish_pair(
            client=s,
            bucket="b",
            feed=copy.deepcopy(row["feed"]),
            payload=row["payload"],
            lock_path=lock,
            now=_clock(),
        )
    assert recover_pending_pair(client=s, bucket="b", lock_path=lock, now=_clock()) in {
        "published",
        "noop",
    }
    sealed = read_pair(s, "b")
    assert sealed is not None and sealed.payload == row["payload"]
    assert (
        recover_pending_pair(client=s, bucket="b", lock_path=lock, now=_clock()) is None
    )
