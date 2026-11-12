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


# Optional expression commitments retain the original v2/v1 JSON bodies.
class MetadataS3(FakeS3):
    def __init__(self):
        super().__init__()
        self.metadata = {}

    def get_object(self, **args):
        result = super().get_object(**args)
        result['Metadata'] = copy.deepcopy(self.metadata.get(args['Key'], {}))
        return result

    def head_object(self, **args):
        result = super().head_object(**args)
        result['Metadata'] = copy.deepcopy(self.metadata.get(args['Key'], {}))
        return result

    def put_object(self, **args):
        key, old = args['Key'], self.o.get(args['Key'])
        try:
            return super().put_object(**args)
        finally:
            if self.o.get(key) != old:
                self.metadata[key] = copy.deepcopy(args.get('Metadata', {}))


def _expression_intent(rows, source_root, *, decision='2026-08-13T14:32:01Z'):
    from engine import options_signal_campaign as campaigns
    from engine.options_alpha_expression_formation import prepare_expression_sources
    from engine.options_alpha_expression_intent import make_expression_intent
    snapshot = campaigns.load_ledger(source_root / campaigns.CAMPAIGNS_PATH,
                                     campaigns.CAMPAIGNS_PATH)
    preparation = prepare_expression_sources(
        rows[0]['payload'], campaigns=snapshot,
        source_observed_at='2026-08-13T14:31:00Z',
        campaigns_observed_at='2026-08-13T14:31:01Z',
        selection_started_at='2026-08-13T14:32:00Z',
        decision_at='2026-08-13T14:32:01Z')['records'][0]
    terms = dict(schema='options.contract_terms_observation/v1',
                 contract=copy.deepcopy(preparation['binding']['contract']),
                 multiplier=100, standard_deliverable=True,
                 deliverable_description='synthetic observed 100 shares; not actual source admission',
                 effective_from='2026-08-13T13:30:00Z', effective_until='2026-08-21T20:00:00Z',
                 source_available_at='2026-08-13T14:29:00Z',
                 source_observed_at='2026-08-13T14:29:01Z', source_id='synthetic-source-fixture',
                 raw_source_sha256='a' * 64, raw_source_bytes=123)
    return make_expression_intent(candidate=rows[0]['feed']['formed_candidates'][0],
                                  preparation_record=preparation, terms_observation=terms,
                                  decision_at=decision)


def _publish_expression(s, root, row, intents=None):
    return publish_pair(client=s, bucket='b', feed=copy.deepcopy(row['feed']),
                        payload=row['payload'], lock_path=root / 'lock',
                        now=_clock(), expression_intents=intents)


def _read_expression(s, root):
    return publisher.read_expression_pair(s, 'b', lock_path=root / 'lock')


def test_expression_commitment_has_real_availability_and_legacy_wire_compatibility(tmp_path, monkeypatch):
    from engine import options_alpha_expression_publication as expressions
    from engine.options_alpha_candidate_feed import validate_publication_receipt_binding
    rows = _feeds(tmp_path / 'source', monkeypatch)
    intent = _expression_intent(rows, tmp_path / 'source')
    s = MetadataS3()
    assert _publish_expression(s, tmp_path, rows[0], [intent]) == 'published'
    legacy = read_pair(s, 'b')
    assert legacy.feed == rows[0]['feed'] and legacy.payload == rows[0]['payload']
    assert legacy.feed['schema'] == 'options.alpha_candidate_feed/v2'
    assert legacy.receipt['schema'] == 'options.alpha_candidate_feed_publication_receipt/v1'
    validate_publication_receipt_binding(feed=legacy.feed, payload=legacy.payload,
                                       receipt=legacy.receipt,
                                       receipt_published_at=legacy.receipt_last_modified)
    assert legacy.expression_manifest is None  # v2 readers need not load private terms
    missing = expressions.resolve_intent_availability(legacy, intent['expression_id'])
    assert missing['available_at'] is None and not missing['capture_eligible']
    assert missing['intent'] is None and missing['public_consumer_available'] is False
    assert missing['first_receipt_id'] is None
    pair = _read_expression(s, tmp_path)
    available = expressions.resolve_intent_availability(pair, intent['expression_id'])
    assert available['status'] == 'available'
    assert available['available_at'] == pair.receipt_last_modified
    assert available['commitment_published_at'] == pair.receipt_last_modified
    assert available['intent'] == intent
    assert available['intent_bytes_sha256'] == expressions.digest(intent)
    assert available['consumer_expression_bytes_resolved'] is True
    assert available['public_consumer_available'] is False
    attached_only = read_pair(s, 'b', expression_manifest=pair.expression_manifest)
    unresolved = expressions.resolve_intent_availability(attached_only, intent['expression_id'])
    assert unresolved['reason'] == 'ORIGINAL_CONSUMER_EXPRESSION_BYTES_UNRESOLVED'
    assert unresolved['available_at'] is None and unresolved['intent'] is None
    assert unresolved['public_consumer_available'] is False
    assert unresolved['first_receipt_id'] == pair.receipt['receipt_id']
    absent = expressions.resolve_intent_availability(pair, 'unpublished-expression')
    assert absent['reason'] == 'EXPRESSION_NOT_PUBLISHED'
    assert absent['first_receipt_id'] is None
    assert available['available_at'] != pair.receipt['payload_r2_confirmed_at']
    assert all(value is False for value in available['authority'].values())
    assert not available['capture_eligible'] and not available['training_eligible']
    assert set(s.o) == {PAYLOAD_KEY, RECEIPT_KEY}
    assert s.metadata[PAYLOAD_KEY][expressions.METADATA_KEY] == pair.expression_manifest_sha256
    assert s.metadata[RECEIPT_KEY][expressions.METADATA_KEY] == pair.expression_manifest_sha256


def test_late_expression_has_own_first_publication_and_successors_preserve_it(tmp_path, monkeypatch):
    from engine import options_alpha_expression_publication as expressions
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    _publish_expression(s, tmp_path, rows[0])
    candidate_time = read_pair(s, 'b').receipt_last_modified
    intent = _expression_intent(rows, tmp_path / 'source', decision='2026-08-14T00:00:03Z')
    _publish_expression(s, tmp_path, rows[1], [intent])
    first = _read_expression(s, tmp_path)
    actual = expressions.resolve_intent_availability(first, intent['expression_id'])
    assert actual['available_at'] != candidate_time
    assert actual['available_at'] == first.receipt_last_modified
    for row in rows[2:]:
        assert _publish_expression(s, tmp_path, row) == 'published'
        later = _read_expression(s, tmp_path)
        carried = expressions.resolve_intent_availability(later, intent['expression_id'])
        assert carried['available_at'] == actual['available_at']
        assert carried['first_receipt_id'] == first.receipt['receipt_id']
        cid = intent['candidate_id']
        assert later.receipt['candidates'][cid]['first_consumer_published_at'] == candidate_time


def test_new_expression_cannot_reuse_same_feed_generation_or_refresh_noop_time(tmp_path, monkeypatch):
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    _publish_expression(s, tmp_path, rows[0])
    intent = _expression_intent(rows, tmp_path / 'source')
    before = copy.deepcopy((s.o, s.metadata, s.puts))
    with pytest.raises(PublicationError, match='new canonical feed generation'):
        _publish_expression(s, tmp_path, rows[0], [intent])
    assert (s.o, s.metadata, s.puts) == before
    _publish_expression(s, tmp_path, rows[1], [intent])
    before = copy.deepcopy((s.o, s.metadata, s.puts))
    assert _publish_expression(s, tmp_path, rows[1], [intent]) == 'noop'
    assert (s.o, s.metadata, s.puts) == before


@pytest.mark.parametrize('key', [PAYLOAD_KEY, RECEIPT_KEY])
@pytest.mark.parametrize('when', ['before', 'after'])
def test_expression_transaction_recovers_original_manifest_without_new_intent(tmp_path, monkeypatch, key, when):
    from engine import options_alpha_expression_publication as expressions
    rows = _feeds(tmp_path / 'source', monkeypatch)
    intent = _expression_intent(rows, tmp_path / 'source')
    s = MetadataS3()
    _publish_expression(s, tmp_path, rows[0])
    setattr(s, 'fail_before' if when == 'before' else 'fail', key)
    with pytest.raises(PublicationError):
        _publish_expression(s, tmp_path, rows[1], [intent])
    journal_path = tmp_path / 'lock.transaction.json'
    journal = publisher._load(journal_path)
    assert journal['schema'] == publisher.EXPRESSION_JOURNAL_SCHEMA
    assert journal['expression_manifest']['expressions'][intent['expression_id']]['intent'] == intent
    assert recover_pending_pair(client=s, bucket='b', lock_path=tmp_path / 'lock', now=lambda: '2026-08-14T01:00:00Z') in {'published', 'noop'}
    assert not journal_path.exists()
    pair = _read_expression(s, tmp_path)
    assert expressions.resolve_intent_availability(pair, intent['expression_id'])['status'] == 'available'
    assert len(s.puts) == 4  # two original plus two successor effects, no duplicate writes


def test_expression_publication_requires_original_retained_manifest_on_new_host(tmp_path, monkeypatch):
    rows = _feeds(tmp_path / 'source', monkeypatch)
    intent = _expression_intent(rows, tmp_path / 'source')
    s = MetadataS3()
    _publish_expression(s, tmp_path, rows[0], [intent])
    (tmp_path / 'lock.sealed.json').unlink()
    puts = len(s.puts)
    with pytest.raises(PublicationError, match='original retained expression manifest'):
        _read_expression(s, tmp_path)
    with pytest.raises(PublicationError, match='original retained expression manifest'):
        _publish_expression(s, tmp_path, rows[1], [intent])
    assert len(s.puts) == puts


@pytest.mark.parametrize('where', [PAYLOAD_KEY, RECEIPT_KEY])
def test_expression_metadata_mismatch_refuses_read_and_publication(tmp_path, monkeypatch, where):
    from engine import options_alpha_expression_publication as expressions
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    intent = _expression_intent(rows, tmp_path / 'source')
    _publish_expression(s, tmp_path, rows[0], [intent])
    s.metadata[where][expressions.METADATA_KEY] = 'f' * 64
    before = len(s.puts)
    with pytest.raises(PublicationError, match='partial/unsealed'):
        read_pair(s, 'b')
    with pytest.raises(PublicationError):
        _publish_expression(s, tmp_path, rows[1])
    assert len(s.puts) == before


def test_expression_clock_uncertainty_never_borrows_or_clamps_candidate_clock(tmp_path, monkeypatch):
    from engine import options_alpha_expression_publication as expressions
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    intent = _expression_intent(rows, tmp_path / 'source', decision='2026-08-14T00:00:02.500000Z')
    _publish_expression(s, tmp_path, rows[0], [intent])
    pair = _read_expression(s, tmp_path)
    observed = expressions.resolve_intent_availability(pair, intent['expression_id'])
    assert observed['status'] == 'unavailable' and observed['available_at'] is None
    assert observed['reason'] == 'EXTERNAL_PUBLICATION_CLOCK_PRECEDES_INTENT'
    assert pair.receipt_last_modified == '2026-08-14T00:00:02Z'


def test_expression_manifest_tampering_or_downgrade_never_replays(tmp_path, monkeypatch):
    import json
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    intent = _expression_intent(rows, tmp_path / 'source')
    _publish_expression(s, tmp_path, rows[0], [intent])
    cache_path = tmp_path / 'lock.sealed.json'
    cache = json.loads(cache_path.read_bytes())
    cache['schema'] = publisher.JOURNAL_SCHEMA
    cache_path.write_bytes(publisher.canonical_bytes(cache))
    puts = len(s.puts)
    with pytest.raises(PublicationError, match='versioned local state'):
        _publish_expression(s, tmp_path, rows[1])
    assert len(s.puts) == puts


def test_expression_get_head_metadata_race_is_unsealed(tmp_path, monkeypatch):
    from engine import options_alpha_expression_publication as expressions
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    intent = _expression_intent(rows, tmp_path / 'source')
    _publish_expression(s, tmp_path, rows[0], [intent])
    original = s.head_object

    def racing_head(**args):
        result = original(**args)
        if args['Key'] == PAYLOAD_KEY:
            result['Metadata'][expressions.METADATA_KEY] = 'f' * 64
        return result

    monkeypatch.setattr(s, 'head_object', racing_head)
    with pytest.raises(PublicationError, match='readback raced'):
        _read_expression(s, tmp_path)


def test_coherent_foreign_commitment_or_lost_commitment_cannot_replace_retained_history(tmp_path, monkeypatch):
    from engine import options_alpha_expression_publication as expressions
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    intent = _expression_intent(rows, tmp_path / 'source')
    _publish_expression(s, tmp_path, rows[0], [intent])
    puts = len(s.puts)
    for key in (PAYLOAD_KEY, RECEIPT_KEY):
        s.metadata[key][expressions.METADATA_KEY] = 'f' * 64
    with pytest.raises(PublicationError, match='original retained'):
        _publish_expression(s, tmp_path, rows[1])
    for key in (PAYLOAD_KEY, RECEIPT_KEY):
        del s.metadata[key][expressions.METADATA_KEY]
    with pytest.raises(PublicationError, match='lost expression history'):
        _publish_expression(s, tmp_path, rows[1])
    assert len(s.puts) == puts


class CoherentLossS3(MetadataS3):
    """A provider moment that drops both commitments together, not partially.

    The stored bodies stay byte-identical and legacy-valid, so every read sees
    one perfectly sealed manifest-less pair, exactly as a legacy peer leaves it.
    """

    def __init__(self):
        super().__init__()
        self.drop_commitments_on_put = None
        self.legacy_peer_pair = None

    def put_object(self, **args):
        key = args['Key']
        raced = self.race == key
        try:
            return super().put_object(**args)
        finally:
            if raced and key == PAYLOAD_KEY and self.legacy_peer_pair is not None:
                # A manifest-less peer stored the identical payload and completed
                # the pair before our conditional payload write landed.
                builder = self.legacy_peer_pair
                self.legacy_peer_pair = None
                body, etag, _ = self.o[key]
                self.n += 1
                self.o[RECEIPT_KEY] = (builder(body, etag), f'"peer{self.n}"', self._time())
                self.metadata.pop(PAYLOAD_KEY, None)
                self.metadata.pop(RECEIPT_KEY, None)
            if key == self.drop_commitments_on_put:
                self.drop_commitments_on_put = None
                self.metadata.pop(PAYLOAD_KEY, None)
                self.metadata.pop(RECEIPT_KEY, None)


def _legacy_peer_receipt_bytes(feed, payload_body, etag):
    """The exact manifest-less receipt a legacy peer would seal for this payload."""
    composition = datetime.fromisoformat(feed['generated_at'].replace('Z', '+00:00'))
    return publisher.canonical_bytes(publisher._make_receipt(
        feed, payload_body, None, etag,
        (composition + timedelta(seconds=1)).isoformat().replace('+00:00', 'Z'),
        (composition + timedelta(seconds=2)).isoformat().replace('+00:00', 'Z')))


def _assert_first_expression_journal_retained(root, intent):
    journal = publisher._load(root / 'lock.transaction.json')
    assert journal['schema'] == publisher.EXPRESSION_JOURNAL_SCHEMA
    assert (journal['expression_manifest']['expressions']
            [intent['expression_id']]['intent']) == intent
    assert not (root / 'lock.sealed.json').exists()


@pytest.mark.parametrize('lost_at', ['payload_412', 'receipt_412', 'final_readback'])
def test_coherent_legacy_pair_cannot_retire_first_expression_journal(tmp_path, monkeypatch, lost_at):
    # The first expression-bearing transaction races a coherent manifest-less
    # pair at each seal site. Sealing there would retire the journal and drop
    # the only retained manifest, so the seal must refuse and keep the
    # original durable transaction without replaying any provider effect.
    rows = _feeds(tmp_path / 'source', monkeypatch)
    intent = _expression_intent(rows, tmp_path / 'source')
    s = CoherentLossS3()
    if lost_at == 'payload_412':
        s.race = PAYLOAD_KEY
        s.legacy_peer_pair = lambda body, etag: _legacy_peer_receipt_bytes(
            rows[0]['feed'], body, etag)
    else:
        s.drop_commitments_on_put = RECEIPT_KEY
        if lost_at == 'receipt_412':
            s.race = RECEIPT_KEY
    with pytest.raises(PublicationError, match='durable transaction obligation'):
        _publish_expression(s, tmp_path, rows[0], [intent])
    _assert_first_expression_journal_retained(tmp_path, intent)
    puts = len(s.puts)
    with pytest.raises(PublicationError):
        _publish_expression(s, tmp_path, rows[0], [intent])
    assert len(s.puts) == puts  # the refusal and retry replay no provider effect


def test_inherited_expression_coherent_loss_keeps_original_journal(tmp_path, monkeypatch):
    rows = _feeds(tmp_path / 'source', monkeypatch)
    intent = _expression_intent(rows, tmp_path / 'source')
    s = CoherentLossS3()
    assert _publish_expression(s, tmp_path, rows[0], [intent]) == 'published'
    s.drop_commitments_on_put = RECEIPT_KEY
    puts = len(s.puts)
    with pytest.raises(PublicationError, match='lost expression history'):
        _publish_expression(s, tmp_path, rows[1], [intent])
    journal = publisher._load(tmp_path / 'lock.transaction.json')
    assert (journal['expression_manifest']['expressions']
            [intent['expression_id']]['intent']) == intent
    assert len(s.puts) == puts + 2  # generation effects landed; the seal still refused


def test_pending_manifest_cannot_be_substituted_after_provider_effect(tmp_path, monkeypatch):
    import json
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    intent = _expression_intent(rows, tmp_path / 'source')
    _publish_expression(s, tmp_path, rows[0])
    s.fail = RECEIPT_KEY
    with pytest.raises(PublicationError):
        _publish_expression(s, tmp_path, rows[1], [intent])
    journal_path = tmp_path / 'lock.transaction.json'
    original = journal_path.read_bytes()
    altered = json.loads(original)
    altered['expression_manifest']['expressions'][intent['expression_id']]['first_consumer_published_at'] = '2026-08-13T14:30:00Z'
    journal_path.write_bytes(publisher.canonical_bytes(altered))
    puts = len(s.puts)
    with pytest.raises(PublicationError):
        recover_pending_pair(client=s, bucket='b', lock_path=tmp_path / 'lock', now=lambda: '2026-08-14T01:00:00Z')
    assert len(s.puts) == puts and journal_path.exists()
    journal_path.write_bytes(original)  # restore the actual retained original, no new operation
    assert recover_pending_pair(client=s, bucket='b', lock_path=tmp_path / 'lock', now=lambda: '2026-08-14T01:00:00Z') == 'noop'


def test_terms_and_future_decision_errors_are_rejected_before_publication(tmp_path, monkeypatch):
    from engine import options_alpha_expression_publication as expressions
    rows = _feeds(tmp_path / 'source', monkeypatch)
    intent = _expression_intent(rows, tmp_path / 'source')
    s = MetadataS3()
    bad = copy.deepcopy(intent)
    bad['terms_observation']['multiplier'] = True
    bad['expression_id'] = 'oaexprintent_' + expressions.digest({k: v for k, v in bad.items() if k != 'expression_id'})
    with pytest.raises(PublicationError, match='intent input invalid'):
        _publish_expression(s, tmp_path, rows[0], [bad])
    future = _expression_intent(rows, tmp_path / 'source', decision='2026-08-15T14:32:01Z')
    with pytest.raises(PublicationError, match='not yet observable'):
        _publish_expression(s, tmp_path, rows[0], [future])
    assert not s.puts and not (tmp_path / 'lock.transaction.json').exists()


def test_same_body_receipt_rewrite_cannot_refresh_first_expression_publication(tmp_path, monkeypatch):
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    intent = _expression_intent(rows, tmp_path / 'source')
    _publish_expression(s, tmp_path, rows[0], [intent])
    body, etag, original_time = s.o[RECEIPT_KEY]
    # S3 ETags cover the body; a metadata/same-body overwrite can retain it.
    s.o[RECEIPT_KEY] = (body, etag, original_time + timedelta(minutes=1))
    puts = len(s.puts)
    with pytest.raises(PublicationError, match='sealed generation changed'):
        _read_expression(s, tmp_path)
    with pytest.raises(PublicationError, match='sealed generation changed'):
        _publish_expression(s, tmp_path, rows[0], [intent])
    assert len(s.puts) == puts


def test_expression_reader_does_not_reconcile_a_pending_provider_effect(tmp_path, monkeypatch):
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    intent = _expression_intent(rows, tmp_path / 'source')
    s.fail = RECEIPT_KEY
    with pytest.raises(PublicationError):
        _publish_expression(s, tmp_path, rows[0], [intent])
    puts = len(s.puts)
    with pytest.raises(PublicationError, match='original recovery'):
        _read_expression(s, tmp_path)
    assert (tmp_path / 'lock.transaction.json').exists() and len(s.puts) == puts


@pytest.mark.parametrize('state_file', ['lock.sealed.json', 'lock.transaction.json'])
def test_versioned_expression_state_cannot_silently_lose_its_manifest(tmp_path, monkeypatch, state_file):
    import json
    rows = _feeds(tmp_path / 'source', monkeypatch)
    s = MetadataS3()
    intent = _expression_intent(rows, tmp_path / 'source')
    if state_file.endswith('transaction.json'):
        s.fail = RECEIPT_KEY
        with pytest.raises(PublicationError):
            _publish_expression(s, tmp_path, rows[0], [intent])
    else:
        _publish_expression(s, tmp_path, rows[0], [intent])
    path = tmp_path / state_file
    state = json.loads(path.read_bytes())
    body = state.get('sealed', state)
    del body['expression_manifest']
    # Removing commitment metadata too must not downgrade a v2 local state.
    body.pop('expression_manifest_sha256', None)
    path.write_bytes(publisher.canonical_bytes(state))
    puts = len(s.puts)
    with pytest.raises(PublicationError, match='requires original manifest'):
        _read_expression(s, tmp_path)
    with pytest.raises(PublicationError, match='requires original manifest'):
        _publish_expression(s, tmp_path, rows[0], [intent])
    assert len(s.puts) == puts
