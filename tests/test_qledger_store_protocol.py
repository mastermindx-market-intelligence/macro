"""Synthetic acceptance for the inactive protocol, without native data or writers."""

from dataclasses import replace
from hashlib import sha256
import io
import itertools
import json

import pytest

from engine import qledger_store_protocol as p


def digest(value):
    return sha256(value).hexdigest()


def encoded(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")


@pytest.fixture
def limits():
    return p.ProtocolLimits(
        base_bytes=16384, part_bytes=128, page_bytes=2048, root_bytes=4096,
        descriptor_bytes=1024, leaf_entries=2, fanout=2, index_levels=3,
        history_operations=32, reference_visits=4096, snapshot_members=1024,
        snapshot_bytes=524288, logical_bytes=16384, input_rows=1024,
        publication_objects=1024, git_blob_bytes=16384,
    )


def initial(raw, limits):
    ref = p.MemberRef(p.BASE_PATH, digest(raw), len(raw))
    root = p.RootRecord(ref, None, 0, len(raw), digest(raw), limits.fingerprint)
    source = p.InMemorySource({p.BASE_PATH: raw}, snapshot_id="fixture:base")
    return source, p.verify_snapshot(source, root, limits=limits)


def source_mapping(source):
    return {r.path: source.read_member(r.path) for r in source.iter_members()}


def materialized_fixture(source, plan, name="fixture:candidate"):
    # A fake owner materializes only an in-memory mapping, never a real path.
    values = source_mapping(source)
    values.update(plan.members)
    values[p.ROOT_PATH] = plan.root_bytes
    return p.InMemorySource(values, snapshot_id=name)


def append(source, snapshot, txid, rows, limits):
    plan = p.plan_append(snapshot, transaction_id=txid, serialized_rows=rows, limits=limits)
    candidate = materialized_fixture(source, plan, "fixture:" + txid)
    root = p.decode_root(plan.root_bytes, limits=limits)
    verified = p.verify_snapshot(candidate, root, limits=limits)
    return candidate, verified, plan


def raw(snapshot):
    with p.open_logical_bytes(snapshot) as stream:
        return stream.read()


def error(call, code=None):
    with pytest.raises(p.SnapshotIntegrityError) as caught:
        call()
    if code is not None:
        assert caught.value.code == code
    return caught.value


def replace_catalog_page(source, snapshot, change):
    ref = snapshot.root.catalog
    assert ref is not None
    value = json.loads(source.read_member(ref.member.path))
    change(value)
    data = encoded(value)
    member = p.MemberRef(p.PAGE_PREFIX + digest(data) + ".json", digest(data), len(data))
    tree = replace(ref, member=member)
    root = replace(snapshot.root, catalog=tree)
    values = source_mapping(source)
    values[member.path] = data
    return p.InMemorySource(values, snapshot_id="fixture:changed-page"), root


@pytest.mark.parametrize("raw_bytes", [
    b"", b'{"id":1}\n', b'{"id":1}', b"\nmalformed\nnull\n[1,2]\nfalse\n",
    '{"label":"inside\u2028separator"}\n{"label":"next"}\r\n'.encode(),
    b'{"id":1}\r{"id":2}\r\n{"id":3}\n',
    b"\xff\xfe\n", b'\xef\xbb\xbf{"id":1}\n',
])
def test_verified_base_is_exact_bytes_and_closes(raw_bytes, limits):
    _, snapshot = initial(raw_bytes, limits)
    stream = p.open_logical_bytes(snapshot)
    with stream:
        pieces = []
        while True:
            piece = stream.read(3)
            if not piece:
                break
            pieces.append(piece)
    assert b"".join(pieces) == raw_bytes
    assert stream.closed
    assert snapshot.receipt.complete
    assert snapshot.receipt.logical_digest == digest(raw_bytes)


def test_append_keeps_unterminated_base_concatenation(limits):
    source, snapshot = initial(b'{"claim_id":"before"}', limits)
    row = b'{"claim_id":"after"}\n'
    _, after, _ = append(source, snapshot, "tail", [row], limits)
    expected = b'{"claim_id":"before"}' + row
    assert raw(after) == expected
    with pytest.raises(json.JSONDecodeError):
        json.loads(raw(after))
    assert b"}\n{" not in raw(after)


def test_business_duplicates_and_retry_identity_are_separate(limits):
    source, base = initial(b"", limits)
    row = b'{"claim_id":"same","value":1}\n'
    source, once, one = append(source, base, "one", [row, row], limits)
    retry = p.plan_append(once, transaction_id="one", serialized_rows=[row, row], limits=limits)
    assert retry.is_noop and retry.reason == "already_applied"
    assert dict(retry.members) == {}
    assert retry.snapshot is once
    source, twice, two = append(source, once, "two", [row], limits)
    assert raw(twice) == row * 3
    assert twice.root.operation_count == 2
    assert one.transaction.transaction_id != two.transaction.transaction_id
    error(lambda: p.plan_append(
        twice, transaction_id="one", serialized_rows=[row], limits=limits
    ), "CONFLICT")


def test_empty_append_has_no_transaction_or_root_change(limits):
    _, snapshot = initial(b"original", limits)
    plan = p.plan_append(snapshot, transaction_id="empty", serialized_rows=[], limits=limits)
    assert plan.is_noop
    assert plan.reason == "empty_append"
    assert plan.root_bytes == snapshot.root_bytes
    assert not plan.members
    assert plan.snapshot is snapshot


def test_base_mapping_and_successful_view_are_immutable_copies(limits):
    base = b"old\n"
    mapping = {p.BASE_PATH: base}
    source = p.InMemorySource(mapping, snapshot_id="fixture:immutable")
    root = p.RootRecord(p.MemberRef(p.BASE_PATH, digest(base), len(base)), None, 0, len(base),
                        digest(base), limits.fingerprint)
    mapping[p.BASE_PATH] = b"changed\n"
    verified = p.verify_snapshot(source, root, limits=limits)
    assert raw(verified) == base
    with pytest.raises(TypeError):
        source._members[p.BASE_PATH] = b"mutation"
    with pytest.raises(TypeError):
        verified._members[p.BASE_PATH] = b"mutation"
    error(lambda: p.open_logical_bytes(None), "INCOMPLETE")
    error(lambda: p.open_logical_bytes(replace(verified, _seal=None)), "INCOMPLETE")


def test_verified_bytes_are_not_reread_from_external_source(limits):
    immutable, base = initial(b"original\n", limits)

    class ExternalSource:
        snapshot_id = "fixture:external-contract"
        reads = 0

        def read_member(self, path):
            self.reads += 1
            if self.reads > 1:
                raise OSError("later external failure")
            return immutable.read_member(path)

        def iter_members(self):
            return immutable.iter_members()

    source = ExternalSource()
    verified = p.verify_snapshot(source, base.root, limits=limits)
    assert raw(verified) == b"original\n"
    assert source.reads == 1  # retained-byte proof, not a real Git coherence proof


def test_changing_source_identity_is_an_explicit_failure(limits):
    immutable, base = initial(b"original\n", limits)

    class MovingSource:
        snapshot_id = "fixture:before"

        def read_member(self, path):
            self.snapshot_id = "fixture:after"
            return immutable.read_member(path)

    error(lambda: p.verify_snapshot(MovingSource(), base.root, limits=limits), "SOURCE_CHANGED")


@pytest.mark.parametrize("response", [bytearray(b"x\n"), None, "x\n"])
def test_mutable_or_nonbyte_member_is_rejected(response, limits):
    _, base = initial(b"x\n", limits)

    class WrongSource:
        snapshot_id = "fixture:wrong"
        def read_member(self, path):
            return response

    error(lambda: p.verify_snapshot(WrongSource(), base.root, limits=limits), "MALFORMED")


def test_missing_source_and_unknown_reader_error_are_typed(limits):
    _, base = initial(b"base\n", limits)
    missing = p.InMemorySource({}, snapshot_id="fixture:missing")
    error(lambda: p.verify_snapshot(missing, base.root, limits=limits), "MISSING")

    class FailedSource:
        snapshot_id = "fixture:failed"
        def read_member(self, path):
            raise ValueError("source adapter failure")

    error(lambda: p.verify_snapshot(FailedSource(), base.root, limits=limits), "MISSING")


@pytest.mark.parametrize("case", [
    "unknown", "boolean_count", "negative_count", "float", "nan", "duplicate",
    "format", "path_escape", "profile", "count_without_catalog", "invalid_utf8",
    "not_object", "noncanonical", "nonbytes", "extra_depth",
])
def test_strict_root_codec_refuses_bad_metadata(case, limits):
    _, snapshot = initial(b"base\n", limits)
    obj = json.loads(snapshot.root_bytes)
    if case == "unknown":
        obj["unknown"] = 1
    elif case == "boolean_count":
        obj["operation_count"] = False
    elif case == "negative_count":
        obj["operation_count"] = -1
    elif case == "format":
        obj["format"] = "future"
    elif case == "path_escape":
        obj["base"]["path"] = "data/qledger/../claims.jsonl"
    elif case == "profile":
        obj["limits_digest"] = "0" * 64
    elif case == "count_without_catalog":
        obj["operation_count"] = 1
    elif case == "extra_depth":
        obj["base"]["nested"] = {"nested": [1]}
    payload = encoded(obj)
    if case == "float":
        payload = snapshot.root_bytes.replace(b'"operation_count":0', b'"operation_count":0.0')
    elif case == "nan":
        payload = snapshot.root_bytes.replace(b'"operation_count":0', b'"operation_count":NaN')
    elif case == "duplicate":
        payload = snapshot.root_bytes[:-1] + b',"operation_count":0}'
    elif case == "invalid_utf8":
        payload = b"\xff"
    elif case == "not_object":
        payload = b"[]"
    elif case == "noncanonical":
        payload += b"\n"
    elif case == "nonbytes":
        payload = snapshot.root_bytes.decode()
    error(lambda: p.decode_root(payload, limits=limits))


@pytest.mark.parametrize("kwargs", [
    {"part_bytes": 0}, {"part_bytes": True}, {"fanout": 1}, {"index_levels": 4},
    {"history_operations": 65537}, {"base_bytes": 96 * 1024 * 1024 + 1},
    {"root_bytes": "4096"}, {"snapshot_bytes": -1},
])
def test_profile_cannot_expand_supported_hard_bounds(kwargs):
    error(lambda: p.ProtocolLimits(**kwargs), "LIMIT")


def test_root_size_budget_is_explicit(limits):
    error(lambda: initial(b"", replace(limits, root_bytes=128)), "LIMIT")


@pytest.mark.parametrize("rows", [[b"not-terminated"], [b"a\nb\n"], ["text\n"], [None]])
def test_unknown_serialized_row_input_is_typed_without_plan(rows, limits):
    _, snapshot = initial(b"base\n", limits)
    before = snapshot.root_bytes
    error(lambda: p.plan_append(
        snapshot, transaction_id="bad-rows", serialized_rows=rows, limits=limits
    ), "MALFORMED")
    assert snapshot.root_bytes == before
    assert raw(snapshot) == b"base\n"


def test_row_and_input_iteration_budgets_fail_without_effect(limits):
    _, snapshot = initial(b"", limits)
    error(lambda: p.plan_append(
        snapshot, transaction_id="oversize", serialized_rows=[b"x" * 128 + b"\n"], limits=limits
    ), "CAPACITY")
    bounded = replace(limits, input_rows=3)
    _, other = initial(b"", bounded)
    error(lambda: p.plan_append(
        other, transaction_id="infinite", serialized_rows=itertools.repeat(b"x\n"), limits=bounded
    ), "LIMIT")

    def failing():
        yield b"ok\n"
        raise OSError("input failure")

    error(lambda: p.plan_append(
        snapshot, transaction_id="failed-input", serialized_rows=failing(), limits=limits
    ), "MALFORMED")
    assert snapshot.root.operation_count == 0


def test_catalog_rollovers_are_bounded_and_reuse_immutable_prefix_pages(limits):
    source, snapshot = initial(b"", limits)
    previous = []
    first_full_leaf = None
    for number in range(12):
        prior_bytes = source_mapping(source)
        before = snapshot
        source, snapshot, plan = append(source, snapshot, f"batch-{number}", [f"{number}\n".encode()], limits)
        previous.append(f"{number}\n".encode())
        assert raw(snapshot) == b"".join(previous)
        assert set(json.loads(plan.root_bytes)) == set(json.loads(before.root_bytes))
        assert len(plan.root_bytes) <= limits.root_bytes
        assert all(source.read_member(path) == data for path, data in prior_bytes.items() if path != p.ROOT_PATH)
        assert all(len(data) <= (limits.part_bytes if path.startswith(p.PART_PREFIX) else limits.page_bytes)
                   for path, data in plan.members.items())
        if number == 2:
            catalog = json.loads(source.read_member(snapshot.root.catalog.member.path))
            first_full_leaf = catalog["entries"][0]["member"]["path"]
        if number == 3:
            assert first_full_leaf in snapshot._members
            assert first_full_leaf not in plan.members
    assert snapshot.root.catalog.height == 3
    assert snapshot.root.operation_count == 12


def test_extent_rollovers_large_transaction_and_repeated_payloads(limits):
    tiny = replace(limits, part_bytes=4)
    source, snapshot = initial(b"", tiny)
    rows = [f"{n}\n".encode() for n in range(10)]
    source, after, plan = append(source, snapshot, "many-parts", rows, tiny)
    assert raw(after) == b"".join(rows)
    assert plan.transaction.extents.height == 2
    assert plan.transaction.extents.count == 5
    assert len(encoded(p._transaction_obj(plan.transaction))) <= tiny.descriptor_bytes

    duplicate_limits = replace(limits, part_bytes=5)
    source, base = initial(b"", duplicate_limits)
    source, duplicated, plan = append(source, base, "duplicate-parts", [b"same\n"] * 12, duplicate_limits)
    assert raw(duplicated) == b"same\n" * 12
    assert plan.transaction.extents.count == 12
    assert len([path for path in plan.members if path.startswith(p.PART_PREFIX)]) == 1


def test_capacity_exhaustion_has_no_unbounded_fallback(limits):
    bounded = replace(limits, index_levels=1, history_operations=32)
    source, snapshot = initial(b"", bounded)
    for index in range(4):
        source, snapshot, _ = append(source, snapshot, f"t-{index}", [b"x\n"], bounded)
    prior = source_mapping(source)
    error(lambda: p.plan_append(
        snapshot, transaction_id="too-deep", serialized_rows=[b"x\n"], limits=bounded
    ), "CAPACITY")
    assert source_mapping(source) == prior
    assert snapshot.root.catalog.height == 1
    tiny = replace(limits, part_bytes=2, index_levels=1)
    _, base = initial(b"", tiny)
    error(lambda: p.plan_append(
        base, transaction_id="huge-batch", serialized_rows=[b"x\n"] * 5, limits=tiny
    ), "CAPACITY")


def test_history_byte_member_and_reference_budgets(limits):
    bounded = replace(limits, history_operations=1)
    source, base = initial(b"", bounded)
    _, one, _ = append(source, base, "one", [b"x\n"], bounded)
    error(lambda: p.plan_append(one, transaction_id="two", serialized_rows=[b"x\n"], limits=bounded), "CAPACITY")
    for change in [
        {"snapshot_bytes": 10}, {"snapshot_members": 1}, {"reference_visits": 1},
    ]:
        narrower = replace(limits, **change)
        if "snapshot_bytes" in change:
            error(lambda: initial(b"base\n", narrower), "LIMIT")
        else:
            _, base = initial(b"", narrower)
            error(lambda: p.plan_append(
                base, transaction_id="budget", serialized_rows=[b"x\n"], limits=narrower
            ), "LIMIT")


@pytest.mark.parametrize("member_class", ["base", "part", "page"])
@pytest.mark.parametrize("failure", ["missing", "changed"])
def test_every_referenced_member_is_verified_before_success(member_class, failure, limits):
    source, base = initial(b"base\n", limits)
    source, after, _ = append(source, base, "one", [b"new\n"], limits)
    values = source_mapping(source)
    if member_class == "base":
        path = p.BASE_PATH
    elif member_class == "part":
        path = next(x for x in values if x.startswith(p.PART_PREFIX))
    else:
        path = after.root.catalog.member.path
    if failure == "missing":
        values.pop(path)
    else:
        values[path] += b"changed"
    corrupt = p.InMemorySource(values, snapshot_id="fixture:corrupt")
    error(lambda: p.verify_snapshot(corrupt, after.root, limits=limits),
          "MISSING" if failure == "missing" else "HASH_MISMATCH")


@pytest.mark.parametrize("case", ["unknown", "boolean_height", "ordinal", "txid_conflict", "descriptor_unknown"])
def test_validly_hashed_bad_catalog_metadata_is_rejected(case, limits):
    source, base = initial(b"", limits)
    source, one, _ = append(source, base, "one", [b"1\n"], limits)
    source, two, _ = append(source, one, "two", [b"2\n"], limits)

    def change(page):
        if case == "unknown":
            page["unknown"] = True
        elif case == "boolean_height":
            page["height"] = False
        elif case == "ordinal":
            page["entries"].reverse()
        elif case == "txid_conflict":
            page["entries"][1]["value"]["transaction_id"] = "one"
        else:
            page["entries"][0]["value"]["unknown"] = 1

    changed, root = replace_catalog_page(source, two, change)
    error(lambda: p.verify_snapshot(changed, root, limits=limits))


def test_index_order_range_height_and_cycle_claims_fail(limits):
    source, snapshot = initial(b"", limits)
    for index in range(5):
        source, snapshot, _ = append(source, snapshot, f"t-{index}", [f"{index}\n".encode()], limits)

    for case in ["reverse", "gap", "height", "cycle"]:
        def change(page):
            if case == "reverse":
                page["entries"].reverse()
            elif case == "gap":
                page["entries"][0]["start"] = 1
            elif case == "height":
                page["entries"][0]["height"] = 3
            else:
                # A claimed cycle cannot pass hash/range verification either.
                page["entries"][0]["member"] = {
                    "path": snapshot.root.catalog.member.path,
                    "digest": snapshot.root.catalog.member.digest,
                    "size": snapshot.root.catalog.member.size,
                }
        changed, root = replace_catalog_page(source, snapshot, change)
        error(lambda: p.verify_snapshot(changed, root, limits=limits))


def test_mixed_snapshots_never_return_a_partial_history(limits):
    base_source, base = initial(b"base\n", limits)
    source_a, after_a, _ = append(base_source, base, "a", [b"a\n"], limits)
    source_b, _, _ = append(base_source, base, "b", [b"b\n"], limits)
    mixed = source_mapping(source_a)
    for path in list(mixed):
        if path.startswith(p.PART_PREFIX):
            mixed.pop(path)
    mixed.update({k: v for k, v in source_mapping(source_b).items() if k.startswith(p.PART_PREFIX)})
    error(lambda: p.verify_snapshot(
        p.InMemorySource(mixed, snapshot_id="fixture:mixed"), after_a.root, limits=limits
    ), "MISSING")


def test_replacement_retains_all_prior_raw_history(limits):
    source, base = initial(b"\nmalformed\n {\"old\":1} \n", limits)
    source, appended, _ = append(source, base, "before-rewrite", [b'{"old":2}\n'], limits)
    plan = p.plan_replace_view(
        appended, transaction_id="rewrite", expected_view_digest=appended.root.logical_digest,
        replacement_rows=[b'{"new":3}\n'], limits=limits,
    )
    source_after = materialized_fixture(source, plan)
    rewritten = p.verify_snapshot(source_after, plan.snapshot.root, limits=limits)
    assert raw(rewritten) == b'{"new":3}\n'
    assert rewritten._members[p.BASE_PATH] == b"\nmalformed\n {\"old\":1} \n"
    assert set(appended._members) - {
        path for path in appended._members if path.startswith(p.PAGE_PREFIX)
    } <= set(rewritten._members)
    # Missing inactive history is still incomplete even when the active view is intact.
    values = source_mapping(source_after)
    old_part = next(path for path in values if path.startswith(p.PART_PREFIX) and values[path] == b'{"old":2}\n')
    values.pop(old_part)
    error(lambda: p.verify_snapshot(
        p.InMemorySource(values, snapshot_id="fixture:missing-history"), rewritten.root, limits=limits
    ), "MISSING")


def legacy_rows(raw_bytes):
    result = []
    for line in raw_bytes.decode("utf-8").splitlines():
        if not line.strip():
            continue
        try:
            result.append(json.loads(line.strip()))
        except Exception:
            continue
    return result


def native_backfill_specimen(raw_bytes, stamps):
    """Frozen behavior from the exact source excerpt; not a production invocation."""
    rows = legacy_rows(raw_bytes)
    backfilled = 0
    for row in rows:
        if row.get("vector_asof") is None:
            key = str((row.get("scope") or {}).get("key") or "")
            if key.endswith((".SS", ".SZ", ".HK")):
                continue
            stamp = stamps.get(str(row.get("asof") or ""), {})
            if stamp.get("vector_asof") is not None:
                for key, value in stamp.items():
                    if row.get(key) is None:
                        row[key] = value
                row["regime_stamp_basis"] = "recomputed_history"
                backfilled += 1
    if not backfilled:
        return None, rows
    return [(json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8") for row in rows], rows


def test_replacement_matches_backfill_serializer_and_basis_exception(limits):
    wider = replace(limits, part_bytes=2048)
    rows = [
        {"claim_id": "same", "timestamp": "2026-09-01T10:00:00Z", "check_by": "2026-10-01",
         "horizon_d": 20, "asof": "2026-09-01", "scope": {"key": "WMT"},
         "vector_asof": None, "regime_stamp_basis": "pit_live", "regime": "keep-non-null"},
        {"claim_id": "same", "timestamp": "original-duplicate", "asof": "2026-09-01",
         "scope": {"key": "COST"}, "vector_asof": "already-stamped", "regime_stamp_basis": "pit_live"},
        {"claim_id": "hk", "asof": "2026-09-01", "scope": {"key": "0700.HK"}, "vector_asof": None},
        {"claim_id": "uncovered", "asof": "1999-01-01", "scope": {"key": "WMT"}, "vector_asof": None},
    ]
    original = b"\nmalformed\n" + b"".join(
        ("  " + json.dumps(row, ensure_ascii=False) + "  \n").encode() for row in rows
    )
    stamps = {"2026-09-01": {"vector_asof": "2026-09-01", "regime": "Mixed", "regime_stamp_basis": "pit_live"}}
    serialized, expected_rows = native_backfill_specimen(original, stamps)
    source, snapshot = initial(original, wider)
    plan = p.plan_replace_view(
        snapshot, transaction_id="backfill", expected_view_digest=snapshot.root.logical_digest,
        replacement_rows=serialized, limits=wider,
    )
    after = p.verify_snapshot(materialized_fixture(source, plan), plan.snapshot.root, limits=wider)
    assert raw(after) == b"".join(serialized)
    assert b"malformed" not in raw(after)
    assert after._members[p.BASE_PATH] == original
    actual = legacy_rows(raw(after))
    assert actual == expected_rows
    assert [r["claim_id"] for r in actual] == ["same", "same", "hk", "uncovered"]
    assert actual[0]["regime_stamp_basis"] == "recomputed_history"
    assert actual[0]["regime"] == "keep-non-null"
    assert actual[1]["regime_stamp_basis"] == "pit_live"
    assert actual[2]["vector_asof"] is None
    assert actual[3]["vector_asof"] is None
    for key in ("claim_id", "timestamp", "check_by", "horizon_d"):
        assert actual[0][key] == rows[0][key]
    no_replacement, _ = native_backfill_specimen(original, {})
    assert no_replacement is None  # native owner does not invoke a replacement
    with pytest.raises(AttributeError):
        native_backfill_specimen(b"null\n", stamps)


def test_replacement_can_be_empty_without_destroying_history(limits):
    source, snapshot = initial(b"original\n", limits)
    plan = p.plan_replace_view(
        snapshot, transaction_id="empty-view", expected_view_digest=snapshot.root.logical_digest,
        replacement_rows=[], limits=limits,
    )
    after = p.verify_snapshot(materialized_fixture(source, plan), plan.snapshot.root, limits=limits)
    assert raw(after) == b""
    assert after._members[p.BASE_PATH] == b"original\n"
    assert after.root.operation_count == 1  # storage capability is not domain permission


def test_stale_replace_fails_and_exact_retry_after_append_is_idempotent(limits):
    source, base = initial(b"base\n", limits)
    replacement = p.plan_replace_view(
        base, transaction_id="replace", expected_view_digest=base.root.logical_digest,
        replacement_rows=[b"replacement\n"], limits=limits,
    )
    source = materialized_fixture(source, replacement)
    changed = p.verify_snapshot(source, replacement.snapshot.root, limits=limits)
    source, later, _ = append(source, changed, "later", [b"suffix\n"], limits)
    retry = p.plan_replace_view(
        later, transaction_id="replace", expected_view_digest=base.root.logical_digest,
        replacement_rows=[b"replacement\n"], limits=limits,
    )
    assert retry.is_noop and retry.reason == "already_applied"
    assert raw(retry.snapshot) == b"replacement\nsuffix\n"
    error(lambda: p.plan_replace_view(
        later, transaction_id="different", expected_view_digest=base.root.logical_digest,
        replacement_rows=[b"bad\n"], limits=limits
    ), "CONFLICT")


def test_two_clone_rebase_preserves_remote_prefix_local_order_and_duplicates(limits):
    base_source, base = initial(b"base\n", limits)
    source_a, a, plan_a = append(base_source, base, "local-a", [b"same\n"], limits)
    _, ab, plan_b = append(source_a, a, "local-b", [b"same\n"], limits)
    remote_source, remote, _ = append(base_source, base, "remote", [b"remote\n"], limits)
    rebased = p.rebase_pending(remote, [plan_a, plan_b], limits=limits)
    assert raw(rebased.snapshot) == b"base\nremote\nsame\nsame\n"
    assert rebased.applied == ("local-a", "local-b")
    assert rebased.already_applied == ()
    assert rebased.snapshot._transactions[:len(remote._transactions)] == remote._transactions
    assert raw(ab) == b"base\nsame\nsame\n"
    assert raw(remote) == b"base\nremote\n"
    assert source_mapping(remote_source)[p.BASE_PATH] == b"base\n"


def test_rebase_retries_are_an_ordered_prefix_and_conflicting_reuse_fails(limits):
    base_source, base = initial(b"", limits)
    source_a, a, plan_a = append(base_source, base, "a", [b"a\n"], limits)
    _, ab, plan_b = append(source_a, a, "b", [b"b\n"], limits)
    retry = p.rebase_pending(ab, [plan_a, plan_b], limits=limits)
    assert retry.already_applied == ("a", "b") and not retry.applied
    assert raw(retry.snapshot) == b"a\nb\n"
    _, only_b, _ = append(base_source, base, "b", [b"b\n"], limits)
    error(lambda: p.rebase_pending(only_b, [plan_a, plan_b], limits=limits), "CONFLICT")
    _, conflicting, _ = append(base_source, base, "a", [b"different\n"], limits)
    error(lambda: p.rebase_pending(conflicting, [plan_a], limits=limits), "CONFLICT")


def test_rebase_rejects_stale_rewrite_other_base_and_unordered_chain(limits):
    base_source, base = initial(b"base\n", limits)
    rewrite = p.plan_replace_view(
        base, transaction_id="rewrite", expected_view_digest=base.root.logical_digest,
        replacement_rows=[b"replaced\n"], limits=limits,
    )
    _, remote, _ = append(base_source, base, "remote", [b"remote\n"], limits)
    error(lambda: p.rebase_pending(remote, [rewrite], limits=limits), "CONFLICT")
    other_source, other = initial(b"different-base\n", limits)
    _, _, other_plan = append(other_source, other, "other", [b"other\n"], limits)
    error(lambda: p.rebase_pending(remote, [other_plan], limits=limits), "CONFLICT")
    _, _, a = append(base_source, base, "a", [b"a\n"], limits)
    _, _, b = append(base_source, base, "b", [b"b\n"], limits)
    error(lambda: p.rebase_pending(remote, [a, b], limits=limits), "CONFLICT")


def test_interrupted_fake_publication_keeps_old_snapshot_and_rejects_new_root(limits):
    source, base = initial(b"base\n", limits)
    plan = p.plan_append(base, transaction_id="new", serialized_rows=[b"new\n"], limits=limits)
    assert raw(p.verify_snapshot(source, base.root, limits=limits)) == b"base\n"
    ordered = list(plan.members)
    for omitted in ordered:
        values = source_mapping(source)
        values.update({k: v for k, v in plan.members.items() if k != omitted})
        values[p.ROOT_PATH] = plan.root_bytes
        interrupted = p.InMemorySource(values, snapshot_id="fixture:interrupted")
        error(lambda: p.verify_snapshot(interrupted, plan.snapshot.root, limits=limits))
        assert raw(p.verify_snapshot(interrupted, base.root, limits=limits)) == b"base\n"
    complete = materialized_fixture(source, plan)
    assert raw(p.verify_snapshot(complete, plan.snapshot.root, limits=limits)) == b"base\nnew\n"


def test_publication_validates_candidate_root_and_explicit_object_inventory(limits):
    source, base = initial(b"base\n", limits)
    source, after, _ = append(source, base, "one", [b"new\n"], limits)
    before = source_mapping(source)
    receipt = p.validate_publication(
        source, after.root, [p.BlobInfo("1" * 40, 100)], limits=limits
    )
    assert receipt.accepted and not receipt.retryable
    assert receipt.source_id == source.snapshot_id
    assert "provided-" in receipt.scope
    assert source_mapping(source) == before
    error(lambda: p.validate_publication(
        source, after.root, [p.BlobInfo("2" * 40, limits.git_blob_bytes + 1)], limits=limits
    ), "NONRETRYABLE_OVERSIZE")
    assert source_mapping(source) == before  # an absent final-tree ancestor still blocks


def test_publication_catches_oversize_unreferenced_member(limits):
    source, base = initial(b"base\n", limits)
    source, after, _ = append(source, base, "one", [b"new\n"], limits)
    values = source_mapping(source)
    orphan = b"x" * (limits.part_bytes + 1)
    values[p.PART_PREFIX + digest(orphan) + ".jsonl"] = orphan
    orphan_source = p.InMemorySource(values, snapshot_id="fixture:orphan")
    assert raw(p.verify_snapshot(orphan_source, after.root, limits=limits)) == b"base\nnew\n"
    error(lambda: p.validate_publication(orphan_source, after.root, [], limits=limits), "NONRETRYABLE_OVERSIZE")


@pytest.mark.parametrize("case", ["missing_root", "wrong_root", "nonprotocol", "bad_path"])
def test_publication_rejects_incomplete_or_wrong_candidate_inventory(case, limits):
    source, base = initial(b"base\n", limits)
    source, after, _ = append(source, base, "one", [b"new\n"], limits)
    values = source_mapping(source)
    if case == "missing_root":
        values.pop(p.ROOT_PATH)
    elif case == "wrong_root":
        values[p.ROOT_PATH] = b"wrong"
    elif case == "nonprotocol":
        values["outside/data.json"] = b"unexpected"
    else:
        values[p.PART_PREFIX + "../escape.jsonl"] = b"x\n"
    bad = p.InMemorySource(values, snapshot_id="fixture:bad-candidate")
    error(lambda: p.validate_publication(bad, after.root, [], limits=limits))


def test_inventory_cannot_hide_a_referenced_member_or_lie_about_root_bytes(limits):
    source, base = initial(b"base\n", limits)
    source, after, _ = append(source, base, "one", [b"new\n"], limits)

    class IncompleteInventory:
        snapshot_id = source.snapshot_id
        def read_member(self, path):
            return source.read_member(path)
        def iter_members(self):
            return [ref for ref in source.iter_members() if ref.path != p.BASE_PATH]

    error(lambda: p.validate_publication(IncompleteInventory(), after.root, [], limits=limits), "INCOMPLETE")

    class LyingRoot:
        snapshot_id = source.snapshot_id
        def read_member(self, path):
            return b"wrong" if path == p.ROOT_PATH else source.read_member(path)
        def iter_members(self):
            return source.iter_members()

    error(lambda: p.validate_publication(LyingRoot(), after.root, [], limits=limits), "HASH_MISMATCH")


@pytest.mark.parametrize("blobs", [
    [p.BlobInfo("short", 1)],
    [p.BlobInfo("a" * 40, True)],
    [p.BlobInfo("a" * 40, -1)],
    [p.BlobInfo("a" * 40, 1), p.BlobInfo("a" * 40, 1)],
    [None],
])
def test_bad_introduced_object_metadata_is_typed(blobs, limits):
    source, base = initial(b"", limits)
    values = source_mapping(source)
    values[p.ROOT_PATH] = base.root_bytes
    source = p.InMemorySource(values, snapshot_id="fixture:root")
    error(lambda: p.validate_publication(source, base.root, blobs, limits=limits))


def test_failure_is_explicit_to_a_fixture_consumer_with_a_legacy_broad_catch(limits):
    _, base = initial(b"base\n", limits)
    missing = p.InMemorySource({}, snapshot_id="fixture:missing")

    def fixture_consumer():
        try:
            snapshot = p.verify_snapshot(missing, base.root, limits=limits)
            return {"state": "ready", "rows": legacy_rows(raw(snapshot))}
        except p.SnapshotIntegrityError:
            raise
        except Exception:
            return {"state": "ready", "rows": []}

    error(fixture_consumer, "MISSING")
    # Actual production consumer catch propagation is not integrated by this test.


def test_text_parsers_retain_their_own_unicode_and_newline_semantics(limits):
    data = '{"label":"inside\u2028separator"}\r\n{"id":2}\r{"id":3}\n'.encode()
    _, snapshot = initial(data, limits)
    split_policy = legacy_rows(data)
    with p.open_logical_bytes(snapshot) as binary:
        with io.TextIOWrapper(binary, encoding="utf-8", newline=None) as stream:
            physical_policy = [json.loads(line) for line in stream if line.strip()]
    assert physical_policy[0] == {"label": "inside\u2028separator"}
    assert split_policy != physical_policy
    assert raw(snapshot) == data


def test_verified_results_cannot_inherit_a_seal_after_dataclass_replacement(limits):
    _, snapshot = initial(b"base\n", limits)
    error(lambda: p.VerifiedSnapshot(), "INCOMPLETE")
    error(lambda: replace(snapshot, _active=()), "INCOMPLETE")
    plan = p.plan_append(snapshot, transaction_id="one", serialized_rows=[b"new\n"], limits=limits)
    error(lambda: p.PublicationPlan(), "MALFORMED")
    error(lambda: replace(plan, transaction=None), "MALFORMED")


def test_replacement_history_budget_fails_without_discarding_prior_bytes(limits):
    roomy = replace(limits, part_bytes=2048)
    base_raw = b"malformed legacy anchor\n"
    first_row = b"a" * 1500 + b"\n"
    second_row = b"b" * 1500 + b"\n"
    source, base = initial(base_raw, roomy)
    sample = p.plan_replace_view(
        base, transaction_id="first", expected_view_digest=base.root.logical_digest,
        replacement_rows=[first_row], limits=roomy,
    )
    # Allow the first generation, but not another distinct payload plus its
    # retained predecessor. Root profile digests have fixed encoded length.
    cap = sample.snapshot.receipt.retained_bytes + len(second_row) - 1
    bounded = replace(roomy, snapshot_bytes=cap)
    source, base = initial(base_raw, bounded)
    first = p.plan_replace_view(
        base, transaction_id="first", expected_view_digest=base.root.logical_digest,
        replacement_rows=[first_row], limits=bounded,
    )
    source = materialized_fixture(source, first)
    before = source_mapping(source)
    current = p.verify_snapshot(source, first.snapshot.root, limits=bounded)
    error(lambda: p.plan_replace_view(
        current, transaction_id="second", expected_view_digest=current.root.logical_digest,
        replacement_rows=[second_row], limits=bounded,
    ), "LIMIT")
    assert source_mapping(source) == before
    assert current._members[p.BASE_PATH] == base_raw
    assert raw(current) == first_row
    assert first.snapshot.root.operation_count == 1


def root_validation_candidate(limits, *, ref_change=lambda ref: ref, payload_change=lambda data: data):
    source, base = initial(b"base\n", limits)
    values = source_mapping(source)
    values[p.ROOT_PATH] = base.root_bytes
    real = p.InMemorySource(values, snapshot_id="fixture:root-validation")

    class Source:
        snapshot_id = real.snapshot_id

        def read_member(self, path):
            value = real.read_member(path)
            return payload_change(value) if path == p.ROOT_PATH else value

        def iter_members(self):
            for ref in real.iter_members():
                yield ref_change(ref) if ref.path == p.ROOT_PATH else ref

    return Source(), base.root


def test_publication_root_inventory_rejects_float_size(limits):
    source, root = root_validation_candidate(
        limits, ref_change=lambda ref: p.MemberRef(ref.path, ref.digest, float(ref.size))
    )
    error(lambda: p.validate_publication(source, root, [], limits=limits), "LIMIT")


@pytest.mark.parametrize("payload_change", [bytearray, memoryview])
def test_publication_root_payload_requires_exact_bytes(payload_change, limits):
    source, root = root_validation_candidate(limits, payload_change=payload_change)
    error(lambda: p.validate_publication(source, root, [], limits=limits), "MALFORMED")


@pytest.mark.parametrize("field", ["path", "digest"])
def test_publication_root_fields_reject_equal_string_subclasses(field, limits):
    class EqualString(str):
        pass

    def changed(ref):
        if field == "path":
            return p.MemberRef(EqualString(ref.path), ref.digest, ref.size)
        return p.MemberRef(ref.path, EqualString(ref.digest), ref.size)

    source, root = root_validation_candidate(limits, ref_change=changed)
    error(lambda: p.validate_publication(source, root, [], limits=limits), "MALFORMED")


def test_publication_root_size_limit_is_validated_before_identity_equality(limits):
    source, root = root_validation_candidate(
        limits, ref_change=lambda ref: p.MemberRef(ref.path, ref.digest, limits.root_bytes + 1)
    )
    error(lambda: p.validate_publication(source, root, [], limits=limits), "LIMIT")


def restart(remote, base, candidate, ids, limits):
    return p.rebase_verified_pending(
        remote, original_base_snapshot=base, original_candidate_snapshot=candidate,
        authorized_transaction_ids=ids, limits=limits,
    )


def two_pending(limits):
    source, base = initial(b"unterminated-base", limits)
    first_source, first, one = append(source, base, "storage-one", [b"same\n", b"same\n"], limits)
    candidate_source, candidate, two = append(first_source, first, "storage-two", [b"tail\n"], limits)
    return source, base, candidate_source, candidate, (one, two)


def assert_same_rebase(actual, expected):
    assert actual.expected_remote_root_digest == expected.expected_remote_root_digest
    assert actual.snapshot.root_bytes == expected.snapshot.root_bytes
    assert actual.members == expected.members
    assert actual.applied == expected.applied
    assert actual.already_applied == expected.already_applied


def test_restart_matches_live_rebase_without_changing_occurrences_or_separator(limits):
    source, base, _, candidate, plans = two_pending(limits)
    _, remote, _ = append(source, base, "remote", [b"remote\n"], limits)
    result = restart(remote, base, candidate, iter(["storage-one", "storage-two"]), limits)
    expected = p.rebase_pending(remote, plans, limits=limits)
    assert_same_rebase(result, expected)
    assert raw(result.snapshot) == b"unterminated-baseremote\nsame\nsame\ntail\n"
    assert result.snapshot.root.base == base.root.base
    assert result.applied == ("storage-one", "storage-two")


def test_restart_partial_retry_then_complete_retry_preserve_remote_occurrences(limits):
    source, base, _, candidate, plans = two_pending(limits)
    first_source = materialized_fixture(source, plans[0])
    _, remote, _ = append(first_source, plans[0].snapshot, "remote", [b"remote\n"], limits)
    result = restart(remote, base, candidate, ["storage-one", "storage-two"], limits)
    assert result.already_applied == ("storage-one",)
    assert result.applied == ("storage-two",)
    assert raw(result.snapshot) == b"unterminated-basesame\nsame\nremote\ntail\n"
    retry = restart(result.snapshot, base, candidate, ["storage-one", "storage-two"], limits)
    assert retry.snapshot is result.snapshot
    assert retry.applied == () and retry.already_applied == ("storage-one", "storage-two")
    assert not retry.members


def test_restart_mixed_append_replace_append_retains_hidden_raw_history(limits):
    source, base = initial(b"base\n", limits)
    one_source, one, append_plan = append(source, base, "append", [b"hidden\n"], limits)
    replace_plan = p.plan_replace_view(
        one, transaction_id="replace", expected_view_digest=one.root.logical_digest,
        replacement_rows=[b"same\n", b"same\n"], limits=limits,
    )
    replaced_source = materialized_fixture(one_source, replace_plan)
    _, candidate, tail = append(replaced_source, replace_plan.snapshot, "tail", [b"end\n"], limits)
    result = restart(base, base, candidate, ["append", "replace", "tail"], limits)
    assert_same_rebase(result, p.rebase_pending(base, (append_plan, replace_plan, tail), limits=limits))
    assert result.snapshot.root_bytes == candidate.root_bytes
    assert raw(result.snapshot) == b"same\nsame\nend\n"
    assert b"hidden\n" in result.members.values()
    assert result.snapshot.root.base == base.root.base
    assert result.snapshot.root.operation_count == 3


def test_restart_empty_replace_and_exact_retry_after_later_append(limits):
    source, base = initial(b"hidden\n", limits)
    plan = p.plan_replace_view(
        base, transaction_id="empty-view", expected_view_digest=base.root.logical_digest,
        replacement_rows=[], limits=limits,
    )
    result = restart(base, base, plan.snapshot, ["empty-view"], limits)
    assert raw(result.snapshot) == b"" and result.snapshot.root.base == base.root.base
    materialized = materialized_fixture(source, plan)
    _, remote, _ = append(materialized, plan.snapshot, "later", [b"later\n"], limits)
    retried = restart(remote, base, plan.snapshot, ["empty-view"], limits)
    assert retried.snapshot is remote and not retried.members
    assert retried.already_applied == ("empty-view",)
    assert raw(retried.snapshot) == b"later\n"


def test_restart_zero_pending_validates_prefix_but_preserves_remote_identity(limits, monkeypatch):
    source, base = initial(b"base", limits)
    noop = p.plan_append(base, transaction_id="never-stored", serialized_rows=[], limits=limits)
    _, remote, _ = append(source, base, "remote", [b"x\n"], limits)
    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("zero pending created a plan"))
    result = restart(remote, base, noop.snapshot, (), limits)
    assert result.snapshot is remote
    assert result.expected_remote_root_digest == remote.receipt.root_digest
    assert not result.members and not result.applied and not result.already_applied
    error(lambda: restart(remote, base, noop.snapshot, ["never-stored"], limits), "CONFLICT")


@pytest.mark.parametrize("ids", [
    [], ["storage-one"], ["storage-two", "storage-one"],
    ["storage-one", "storage-one"], ["storage-one", "storage-two", "extra"],
    ["same", "storage-two"],
])
def test_restart_authorization_is_the_complete_ordered_storage_suffix(ids, limits, monkeypatch):
    _, base, _, candidate, _ = two_pending(limits)
    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("unauthorized plan created"))
    error(lambda: restart(base, base, candidate, ids, limits), "CONFLICT")


@pytest.mark.parametrize("ids", [
    None, 7, "storage-one", b"storage-one", bytearray(b"storage-one"),
    {"storage-one": True}, {"storage-one"}, frozenset({"storage-one"}),
    [True], [1.0], [b"storage-one"], ["bad id"], ["x" * 129],
])
def test_restart_rejects_malformed_or_unordered_authorization(ids, limits, monkeypatch):
    _, base, _, candidate, _ = two_pending(limits)
    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("malformed authorization planned"))
    error(lambda: restart(base, base, candidate, ids, limits), "MALFORMED")


def test_restart_authorization_iteration_is_bounded_and_iteration_errors_are_typed(limits, monkeypatch):
    _, base, _, candidate, _ = two_pending(limits)
    consumed = []

    def endless():
        for value in itertools.chain(["storage-one", "storage-two"], itertools.repeat("extra")):
            consumed.append(value)
            yield value

    def broken():
        yield "storage-one"
        raise RuntimeError("synthetic authorization failure")

    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("invalid iterable planned"))
    error(lambda: restart(base, base, candidate, endless(), limits), "CONFLICT")
    assert consumed == ["storage-one", "storage-two", "extra"]
    error(lambda: restart(base, base, candidate, broken(), limits), "MALFORMED")


@pytest.mark.parametrize("case", ["candidate-anchor", "candidate-prefix", "candidate-short", "remote-prefix", "remote-anchor"])
def test_restart_rejects_changed_or_missing_original_anchor_and_history(case, limits, monkeypatch):
    source, anchor = initial(b"base\n", limits)
    base_source, base, _ = append(source, anchor, "prefix", [b"kept\n"], limits)
    _, candidate, _ = append(base_source, base, "pending", [b"tail\n"], limits)
    remote = base
    if case == "candidate-anchor":
        other_source, other = initial(b"other\n", limits)
        other_source, other, _ = append(other_source, other, "prefix", [b"kept\n"], limits)
        _, candidate, _ = append(other_source, other, "pending", [b"tail\n"], limits)
    elif case == "candidate-prefix":
        changed_source, changed, _ = append(source, anchor, "prefix", [b"changed\n"], limits)
        _, candidate, _ = append(changed_source, changed, "pending", [b"tail\n"], limits)
    elif case == "candidate-short":
        candidate = anchor
    elif case == "remote-prefix":
        remote = anchor
    else:
        _, remote = initial(b"other\n", limits)
    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("changed prefix planned"))
    error(lambda: restart(remote, base, candidate, ["pending"], limits), "CONFLICT")


@pytest.mark.parametrize("case", ["different-content", "accepted-later-before-new", "reordered"])
def test_restart_rejects_conflicting_or_reordered_remote_retry_before_planning(case, limits, monkeypatch):
    source, base, _, candidate, plans = two_pending(limits)
    if case == "different-content":
        _, remote, _ = append(source, base, "storage-one", [b"changed\n"], limits)
    else:
        remote_source, remote, _ = append(source, base, "storage-two", [b"tail\n"], limits)
        if case == "reordered":
            _, remote, _ = append(remote_source, remote, "storage-one", [b"same\n", b"same\n"], limits)
    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("conflicting retry planned"))
    error(lambda: restart(remote, base, candidate, ["storage-one", "storage-two"], limits), "CONFLICT")


@pytest.mark.parametrize("same_view", [False, True])
def test_restart_stale_replace_requires_original_root_not_only_same_logical_view(same_view, limits):
    source, base = initial(b"original\n", limits)
    candidate = p.plan_replace_view(
        base, transaction_id="local-rewrite", expected_view_digest=base.root.logical_digest,
        replacement_rows=[b"new\n"], limits=limits,
    ).snapshot
    remote_source, remote, _ = append(source, base, "remote", [b"extra\n"], limits)
    if same_view:
        remote = p.plan_replace_view(
            remote, transaction_id="remote-restore", expected_view_digest=remote.root.logical_digest,
            replacement_rows=[b"original\n"], limits=limits,
        ).snapshot
        assert remote.root.logical_digest == base.root.logical_digest
    error(lambda: restart(remote, base, candidate, ["local-rewrite"], limits), "CONFLICT")
    assert raw(candidate) == b"new\n"


@pytest.mark.parametrize("slot", ["remote", "base", "candidate"])
@pytest.mark.parametrize("bad", [None, {}, "unverified"])
def test_restart_requires_verified_snapshots_in_every_position(slot, bad, limits, monkeypatch):
    _, base, _, candidate, _ = two_pending(limits)
    values = {"remote": base, "base": base, "candidate": candidate}
    values[slot] = bad
    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("unverified object planned"))
    error(lambda: restart(values["remote"], values["base"], values["candidate"], ["storage-one", "storage-two"], limits), "INCOMPLETE")


def test_restart_uninitialized_snapshot_cannot_inherit_verification(limits, monkeypatch):
    _, base, _, candidate, _ = two_pending(limits)
    forged = object.__new__(p.VerifiedSnapshot)
    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("unsealed object planned"))
    error(lambda: restart(base, base, forged, ["storage-one", "storage-two"], limits))
    with pytest.raises(p.SnapshotIntegrityError):
        replace(candidate, root=base.root)


def test_restart_profile_mismatch_and_invalid_profile_fail_before_plans(limits, monkeypatch):
    _, base, _, candidate, _ = two_pending(limits)
    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("profile mismatch planned"))
    error(lambda: restart(base, base, candidate, ["storage-one", "storage-two"], replace(limits, part_bytes=127)), "LIMIT")
    error(lambda: restart(base, base, candidate, ["storage-one", "storage-two"], None), "MALFORMED")


@pytest.mark.parametrize("budget, message", [
    ({"snapshot_bytes": 6000}, "byte-work"),
    ({"reference_visits": 15}, "reference-work"),
])
def test_restart_aggregate_work_is_bounded_before_any_reconstruction(budget, message, limits, monkeypatch):
    limited = replace(limits, **budget)
    _, base, _, candidate, _ = two_pending(limited)
    assert candidate.receipt.retained_bytes <= limited.snapshot_bytes
    assert candidate.receipt.reference_visits <= limited.reference_visits
    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("budget failure constructed a plan"))
    caught = error(lambda: restart(base, base, candidate, ["storage-one", "storage-two"], limited), "LIMIT")
    assert message in str(caught)


def test_restart_combined_history_capacity_fails_before_plans(limits, monkeypatch):
    limited = replace(limits, history_operations=2)
    source, base, _, candidate, _ = two_pending(limited)
    _, remote, _ = append(source, base, "remote", [b"other\n"], limited)
    monkeypatch.setattr(p, "_finish", lambda *a, **k: pytest.fail("capacity failure constructed a plan"))
    error(lambda: restart(remote, base, candidate, ["storage-one", "storage-two"], limited), "CAPACITY")
    assert candidate.root.operation_count == 2 and remote.root.operation_count == 1


def stored_catalog_fixture(limits):
    """A valid public-wire specimen with intentionally separate small extents."""
    source, base = initial(b"no-separator", limits)
    values = source_mapping(source)
    chunks = [b"same\r\v\n", b"same\r\v\n", b"\xff\n"]

    def member(payload, prefix, suffix):
        path = prefix + digest(payload) + suffix
        values[path] = payload
        return {"path": path, "digest": digest(payload), "size": len(payload)}

    # Three occurrences use two immutable parts; repeated occurrences stay in
    # the ordered extent list and are never inferred from physical member count.
    parts = [member(chunk, p.PART_PREFIX, ".jsonl") for chunk in chunks]
    extent_leaves = []
    for offset in (0, 2):
        entries = [{"ordinal": i, "value": parts[i]} for i in range(offset, min(offset + 2, 3))]
        page = encoded({"format": p.PAGE_FORMAT, "kind": "extents", "height": 0, "entries": entries})
        extent_leaves.append({
            "member": member(page, p.PAGE_PREFIX, ".json"), "kind": "extents", "height": 0,
            "start": offset, "count": len(entries),
        })
    extent_page = encoded({"format": p.PAGE_FORMAT, "kind": "extents", "height": 1, "entries": extent_leaves})
    extents = {
        "member": member(extent_page, p.PAGE_PREFIX, ".json"),
        "kind": "extents", "height": 1, "start": 0, "count": 3,
    }
    payload = b"".join(chunks)
    transaction = {
        "transaction_id": "stored-parts", "kind": "append", "extents": extents,
        "payload_size": len(payload), "payload_digest": digest(payload), "expected_view_digest": None,
    }
    catalog_page = encoded({
        "format": p.PAGE_FORMAT, "kind": "catalog", "height": 0,
        "entries": [{"ordinal": 0, "value": transaction}],
    })
    ref = member(catalog_page, p.PAGE_PREFIX, ".json")
    catalog = p.TreeRef(p.MemberRef(**ref), "catalog", 0, 0, 1)
    logical = b"no-separator" + payload
    root = p.RootRecord(base.root.base, catalog, 1, len(logical), digest(logical), limits.fingerprint)
    retained_source = p.InMemorySource(values, snapshot_id="fixture:stored-extent-shape")
    candidate = p.verify_snapshot(retained_source, root, limits=limits)
    return base, retained_source, candidate, payload


def test_restart_preserves_verified_extent_shape_and_retry_digest_without_reserializing(limits):
    base, _, candidate, payload = stored_catalog_fixture(limits)
    result = restart(base, base, candidate, ["stored-parts"], limits)
    assert result.snapshot.root_bytes == candidate.root_bytes
    assert raw(result.snapshot) == b"no-separator" + payload
    retry = restart(result.snapshot, base, candidate, ["stored-parts"], limits)
    assert retry.snapshot is result.snapshot and retry.already_applied == ("stored-parts",)
    # Native row packing would give a different transaction digest. Restart
    # deliberately consumes retained extents rather than that second encoding.
    repacked = p.plan_append(base, transaction_id="stored-parts", serialized_rows=[line + b"\n" for line in payload.split(b"\n")[:-1]], limits=limits)
    assert repacked.root_bytes != candidate.root_bytes


def wrapped_catalog(source, snapshot, limits):
    ref = snapshot.root.catalog
    entries = [{
        "member": {"path": ref.member.path, "digest": ref.member.digest, "size": ref.member.size},
        "kind": ref.kind, "height": ref.height, "start": ref.start, "count": ref.count,
    }]
    page = encoded({"format": p.PAGE_FORMAT, "kind": "catalog", "height": ref.height + 1, "entries": entries})
    member = p.MemberRef(p.PAGE_PREFIX + digest(page) + ".json", digest(page), len(page))
    root = replace(snapshot.root, catalog=p.TreeRef(member, "catalog", ref.height + 1, 0, ref.count))
    values = source_mapping(source)
    values[member.path] = page
    return p.verify_snapshot(p.InMemorySource(values, snapshot_id="fixture:alternate-root"), root, limits=limits)


@pytest.mark.parametrize("zero_pending", [False, True])
def test_restart_never_silently_changes_an_original_candidate_root(zero_pending, limits):
    source, base = initial(b"base\n", limits)
    candidate_source, candidate, _ = append(source, base, "one", [b"one\n"], limits)
    altered = wrapped_catalog(candidate_source, candidate, limits)
    assert raw(altered) == raw(candidate) and altered.root_bytes != candidate.root_bytes
    if zero_pending:
        error(lambda: restart(candidate, candidate, altered, [], limits), "CONFLICT")
    else:
        error(lambda: restart(base, base, altered, ["one"], limits), "CONFLICT")


def test_restart_reads_only_retained_verified_bytes_after_external_source_changes(limits):
    source, base, candidate_source, candidate, _ = two_pending(limits)

    class OneVerificationSource:
        snapshot_id = "fixture:detached"
        poisoned = False

        def read_member(self, path):
            if self.poisoned:
                pytest.fail("restart reread the external source")
            return candidate_source.read_member(path)

    external = OneVerificationSource()
    detached = p.verify_snapshot(external, candidate.root, limits=limits)
    external.poisoned = True
    result = restart(base, base, detached, ["storage-one", "storage-two"], limits)
    assert result.snapshot.root_bytes == candidate.root_bytes
    assert raw(result.snapshot) == b"unterminated-basesame\nsame\ntail\n"


@pytest.mark.parametrize("kind", ["append", "replace", "empty-append", "retry"])
def test_public_validate_plan_accepts_only_intact_planner_results(kind, limits):
    _, base = initial(b"base\n", limits)
    plan = p.plan_append(base, transaction_id="one", serialized_rows=[b"one\n"], limits=limits)
    if kind == "replace":
        plan = p.plan_replace_view(base, transaction_id="replace", expected_view_digest=base.root.logical_digest, replacement_rows=[], limits=limits)
    elif kind == "empty-append":
        plan = p.plan_append(base, transaction_id="empty", serialized_rows=[], limits=limits)
    elif kind == "retry":
        plan = p.plan_append(plan.snapshot, transaction_id="one", serialized_rows=[b"one\n"], limits=limits)
    assert p.validate_plan(plan, limits=limits) is None
    assert p.validate_plan(plan, limits=replace(limits)) is None


@pytest.mark.parametrize("bad", [None, {}, "plan"])
def test_public_validate_plan_rejects_unverified_lookalikes(bad, limits):
    error(lambda: p.validate_plan(bad, limits=limits), "MALFORMED")


def test_public_validate_plan_rejects_unsealed_objects_and_changed_profile(limits):
    _, base = initial(b"base", limits)
    plan = p.plan_append(base, transaction_id="one", serialized_rows=[b"one\n"], limits=limits)
    error(lambda: p.validate_plan(object.__new__(p.PublicationPlan), limits=limits), "MALFORMED")
    error(lambda: p.validate_plan(plan, limits=replace(limits, part_bytes=127)), "LIMIT")
    error(lambda: p.validate_plan(plan, limits=None), "MALFORMED")
    with pytest.raises(p.SnapshotIntegrityError):
        replace(plan, expected_root_digest="0" * 64)
    with pytest.raises(TypeError):
        plan.members["changed"] = b"not admitted"
    assert p.validate_plan(plan, limits=limits) is None


@pytest.mark.parametrize("field", ["expected_root_digest", "snapshot", "members", "transaction", "reason"])
def test_public_validate_plan_detects_fault_injected_public_metadata(field, limits):
    # Fault injection bypasses frozen assignment on an otherwise real synthetic
    # plan; it never constructs or copies a verification seal.
    _, base = initial(b"base\n", limits)
    plan = p.plan_append(base, transaction_id="one", serialized_rows=[b"one\n"], limits=limits)
    changes = {
        "expected_root_digest": "0" * 64,
        "snapshot": base,
        "members": type(plan.members)({}),
        "transaction": replace(plan.transaction, transaction_id="changed"),
        "reason": "already_applied",
    }
    object.__setattr__(plan, field, changes[field])
    error(lambda: p.validate_plan(plan, limits=limits))


@pytest.mark.parametrize("field", ["root-bytes", "root-counter", "receipt-counter", "mutable-member", "original-root"])
def test_public_validate_plan_rejects_changed_snapshot_metadata_and_bytes(field, limits):
    _, base = initial(b"base\n", limits)
    plan = p.plan_append(base, transaction_id="one", serialized_rows=[b"one\n"], limits=limits)
    if field == "root-bytes":
        object.__setattr__(plan.snapshot, "root_bytes", bytearray(plan.root_bytes))
    elif field == "root-counter":
        object.__setattr__(plan.snapshot, "root", replace(plan.snapshot.root, operation_count=True))
    elif field == "receipt-counter":
        object.__setattr__(plan.snapshot.receipt, "retained_bytes", float(plan.snapshot.receipt.retained_bytes))
    elif field == "mutable-member":
        members = dict(plan.members)
        key = next(iter(members))
        members[key] = bytearray(members[key])
        object.__setattr__(plan, "members", type(plan.members)(members))
    else:
        object.__setattr__(base, "root_bytes", b"changed")
    error(lambda: p.validate_plan(plan, limits=limits))


def test_public_validate_plan_rejects_noop_with_changed_result(limits):
    _, base = initial(b"base\n", limits)
    noop = p.plan_append(base, transaction_id="empty", serialized_rows=[], limits=limits)
    other = p.plan_append(base, transaction_id="one", serialized_rows=[b"one\n"], limits=limits)
    object.__setattr__(noop, "snapshot", other.snapshot)
    error(lambda: p.validate_plan(noop, limits=limits), "CONFLICT")
