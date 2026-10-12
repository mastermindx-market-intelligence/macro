"""A01-A06 acceptance for the SNI identity relationship DRAFT contract.

Fixtures are synthetic. Counters follow the shape of the Alibaba/Tencent
coverage profiles (venue, local_code, currency) and carry no canonical ids.
"""
import hashlib
import sys
from fractions import Fraction
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research/single_name_intelligence/identity"))

from sni_identity_relations import (  # noqa: E402
    AUTHORITY_FLAGS,
    CounterRef,
    Receipt,
    Relation,
    RelationKind,
    RelationRefused,
    RelationRegistry,
    from_jsonl,
    record_id,
    refuse_authority,
    require_issuer_id,
    to_jsonl,
    validate,
)

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "research/single_name_intelligence/identity/sni_identity_relations.py"
)

AS_OF = "2026-10-11T00:00:00Z"
ISSUED = "2026-01-01T00:00:00Z"
VALID_FROM = "2026-01-02T00:00:00Z"


def _digest(tag: str) -> str:
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()


def _receipt(tag: str, *, owner: str = "stock_identity", expires: str | None = None) -> Receipt:
    return Receipt(
        receipt_id="rcpt-" + tag,
        source_owner=owner,
        issued_at_utc=ISSUED,
        expires_at_utc=expires,
        digest=_digest(tag),
    )


def _counter(venue: str, code: str, currency: str, *, owner: str = "stock_identity") -> CounterRef:
    return CounterRef(
        venue_mic=venue,
        local_code=code,
        currency=currency,
        security_id=None,
        security_id_owner=owner,
    )


def _rel(kind: RelationKind, a: CounterRef, b: CounterRef, receipt: Receipt, *,
         ratio: Fraction | None = None, valid_to: str | None = None) -> Relation:
    return Relation(
        kind=kind,
        a=a,
        b=b,
        ratio=ratio,
        receipt=receipt,
        valid_from_utc=VALID_FROM,
        valid_to_utc=valid_to,
    )


def ads_pair():
    ads = _counter("XNYS", "BABA", "USD")
    ordinary = _counter("XHKG", "09988", "HKD")
    return ads, ordinary


def alibaba_dual():
    hkd = _counter("XHKG", "09988", "HKD")
    rmb = _counter("XHKG", "89988", "CNH")
    return hkd, rmb


def tencent_dual():
    hkd = _counter("XHKG", "00700", "HKD")
    rmb = _counter("XHKG", "80700", "CNH")
    return hkd, rmb


def test_a01_counterref_ads_not_equal_ordinary():
    ads, ordinary = ads_pair()
    assert ads != ordinary
    assert ads.key() != ordinary.key()
    assert ads.local_code == "BABA"
    assert ordinary.local_code == "09988"


def test_a01_ads_of_records_distinct_endpoints():
    ads, ordinary = ads_pair()
    rel = _rel(RelationKind.ADS_OF, ads, ordinary, _receipt("ads-1-8"), ratio=Fraction(1, 8))
    validate(rel)
    assert rel.a != rel.b
    rec = record_id(rel)
    swapped = _rel(RelationKind.ADS_OF, ordinary, ads, _receipt("ads-1-8"), ratio=Fraction(1, 8))
    assert record_id(swapped) != rec
    registry = RelationRegistry()
    registry.add(rel)
    stored = registry.rows()[0].relation
    assert stored.a.local_code == "BABA"
    assert stored.b.local_code == "09988"
    assert stored.a != stored.b


def test_a02_dual_counters_null_security_id():
    a_hkd, a_rmb = alibaba_dual()
    t_hkd, t_rmb = tencent_dual()
    assert a_hkd.security_id is None and a_rmb.security_id is None
    assert t_hkd.security_id is None and t_rmb.security_id is None
    r1 = _rel(RelationKind.DUAL_COUNTER_OF, a_hkd, a_rmb, _receipt("ali-dual"))
    r2 = _rel(RelationKind.DUAL_COUNTER_OF, t_hkd, t_rmb, _receipt("ten-dual"))
    registry = RelationRegistry()
    registry.add(r1)
    registry.add(r2)
    blob = to_jsonl(registry)
    assert "ISS:" not in blob
    for row in registry.rows():
        assert row.relation.a.security_id is None
        assert row.relation.b.security_id is None
        dumped = to_jsonl(RelationRegistry())  # sanity: empty has no prefix
        assert "ISS:" not in dumped


def test_a02_jsonl_has_no_constructed_id_prefix():
    a_hkd, a_rmb = alibaba_dual()
    t_hkd, t_rmb = tencent_dual()
    registry = RelationRegistry()
    registry.add(_rel(RelationKind.DUAL_COUNTER_OF, a_hkd, a_rmb, _receipt("ali-dual-b")))
    registry.add(_rel(RelationKind.DUAL_COUNTER_OF, t_hkd, t_rmb, _receipt("ten-dual-b")))
    blob = to_jsonl(registry)
    assert "ISS:" not in blob
    assert "SEC:" not in blob
    restored = from_jsonl(blob)
    assert to_jsonl(restored) == blob
    for row in restored.rows():
        assert row.relation.a.security_id is None
        assert row.relation.b.security_id is None


def test_a03_require_issuer_id_refuses_none():
    with pytest.raises(RelationRefused) as caught:
        require_issuer_id(None, op="group_issuers")
    assert caught.value.code == "ISSUER_ID_REQUIRED"
    assert "group_issuers" in caught.value.message
    assert require_issuer_id("caller-supplied-opaque", op="group_issuers") == "caller-supplied-opaque"


def test_a04_padding_mismatch_refused_without_stock_identity_receipt():
    padded = _counter("XHKG", "0700", "HKD")
    unpadded = _counter("XHKG", "700", "HKD")
    rel = _rel(
        RelationKind.ALIAS_OF,
        padded,
        unpadded,
        _receipt("pad-research", owner="sni_draft"),
    )
    with pytest.raises(RelationRefused) as caught:
        validate(rel)
    assert caught.value.code == "PADDING_MISMATCH"


def test_a04_alias_currency_mismatch_refused():
    a = _counter("XHKG", "09988", "HKD")
    b = _counter("XHKG", "09988", "USD")
    rel = _rel(RelationKind.ALIAS_OF, a, b, _receipt("alias-ccy"))
    with pytest.raises(RelationRefused) as caught:
        validate(rel)
    assert caught.value.code == "CROSS_BIND_CURRENCY"


def test_a04_alias_venue_mismatch_refused():
    a = _counter("XHKG", "BABA", "USD")
    b = _counter("XNYS", "BABA", "USD")
    rel = _rel(RelationKind.ALIAS_OF, a, b, _receipt("alias-venue"))
    with pytest.raises(RelationRefused) as caught:
        validate(rel)
    assert caught.value.code == "CROSS_BIND_VENUE"


def test_a05_conflicting_ratio_refused():
    ads, ordinary = ads_pair()
    first = _rel(RelationKind.ADS_OF, ads, ordinary, _receipt("ratio-8"), ratio=Fraction(1, 8))
    second = _rel(RelationKind.ADS_OF, ads, ordinary, _receipt("ratio-4"), ratio=Fraction(1, 4))
    registry = RelationRegistry()
    registry.add(first)
    with pytest.raises(RelationRefused) as caught:
        registry.add(second)
    assert caught.value.code == "CONFLICT"


def test_a05_expired_receipt_refused():
    ads, ordinary = ads_pair()
    rel = _rel(
        RelationKind.ADS_OF,
        ads,
        ordinary,
        _receipt("expired", expires="2020-01-01T00:00:00Z"),
        ratio=Fraction(1, 8),
    )
    with pytest.raises(RelationRefused) as caught:
        validate(rel)
    assert caught.value.code == "RECEIPT_EXPIRED"


def test_a05_supersede_keeps_old_row():
    ads, ordinary = ads_pair()
    old = _rel(RelationKind.ADS_OF, ads, ordinary, _receipt("ratio-8b"), ratio=Fraction(1, 8))
    new = _rel(RelationKind.ADS_OF, ads, ordinary, _receipt("ratio-4b"), ratio=Fraction(1, 4))
    registry = RelationRegistry()
    old_id = registry.add(old)
    new_id = registry.supersede(old_id, new, reason="ratio correction")
    stored_old = registry.row(old_id)
    assert stored_old.superseded_by == new_id
    assert stored_old.supersede_reason == "ratio correction"
    assert stored_old.relation.ratio == Fraction(1, 8)
    assert stored_old.relation.receipt.digest == _digest("ratio-8b")
    active = registry.active(AS_OF)
    assert len(active) == 1
    assert active[0].ratio == Fraction(1, 4)
    assert record_id(active[0]) == new_id
    hist = registry.history(ads.key())
    assert len(hist) == 2


def test_a06_symmetric_record_id_both_ways():
    a_hkd, a_rmb = alibaba_dual()
    t_hkd, t_rmb = tencent_dual()
    receipt = _receipt("sym-ali")
    ab = _rel(RelationKind.DUAL_COUNTER_OF, a_hkd, a_rmb, receipt)
    ba = _rel(RelationKind.DUAL_COUNTER_OF, a_rmb, a_hkd, receipt)
    assert record_id(ab) == record_id(ba)
    ten_receipt = _receipt("sym-ten")
    t_ab = _rel(RelationKind.DUAL_COUNTER_OF, t_hkd, t_rmb, ten_receipt)
    t_ba = _rel(RelationKind.DUAL_COUNTER_OF, t_rmb, t_hkd, ten_receipt)
    assert record_id(t_ab) == record_id(t_ba)
    group_ab = _rel(
        RelationKind.SAME_ISSUER_GROUP,
        a_hkd,
        _counter("XNYS", "BABA", "USD"),
        _receipt("group"),
    )
    group_ba = _rel(
        RelationKind.SAME_ISSUER_GROUP,
        _counter("XNYS", "BABA", "USD"),
        a_hkd,
        _receipt("group"),
    )
    assert record_id(group_ab) == record_id(group_ba)


def test_a06_input_order_permutation_same_jsonl():
    ads, ordinary = ads_pair()
    a_hkd, a_rmb = alibaba_dual()
    t_hkd, t_rmb = tencent_dual()
    relations = [
        _rel(RelationKind.ADS_OF, ads, ordinary, _receipt("ord-ads"), ratio=Fraction(1, 8)),
        _rel(RelationKind.DUAL_COUNTER_OF, a_hkd, a_rmb, _receipt("ord-ali")),
        _rel(RelationKind.DUAL_COUNTER_OF, t_hkd, t_rmb, _receipt("ord-ten")),
    ]
    forward = RelationRegistry()
    reverse = RelationRegistry()
    for rel in relations:
        forward.add(rel)
    for rel in reversed(relations):
        reverse.add(rel)
    ids_forward = sorted(row.record_id for row in forward.rows())
    ids_reverse = sorted(row.record_id for row in reverse.rows())
    assert ids_forward == ids_reverse
    assert to_jsonl(forward) == to_jsonl(reverse)


def test_a06_duplicate_count_once():
    a_hkd, a_rmb = alibaba_dual()
    rel = _rel(RelationKind.DUAL_COUNTER_OF, a_hkd, a_rmb, _receipt("dup"))
    registry = RelationRegistry()
    first = registry.add(rel)
    with pytest.raises(RelationRefused) as caught:
        registry.add(rel)
    assert caught.value.code == "DUPLICATE"
    assert first == record_id(rel)
    assert len(registry.rows()) == 1


def test_module_source_has_no_constructed_id_prefixes():
    text = MODULE_PATH.read_text(encoding="utf-8")
    assert "ISS:" not in text
    assert "SEC:" not in text


def test_ratio_required_and_forbidden():
    ads, ordinary = ads_pair()
    missing = _rel(RelationKind.ADS_OF, ads, ordinary, _receipt("no-ratio"), ratio=None)
    with pytest.raises(RelationRefused) as caught:
        validate(missing)
    assert caught.value.code == "RATIO_REQUIRED"
    a_hkd, a_rmb = alibaba_dual()
    forbidden = _rel(
        RelationKind.DUAL_COUNTER_OF,
        a_hkd,
        a_rmb,
        _receipt("ratio-on-dual"),
        ratio=Fraction(1, 1),
    )
    with pytest.raises(RelationRefused) as caught:
        validate(forbidden)
    assert caught.value.code == "RATIO_FORBIDDEN"


def test_self_relation_refused():
    ads, _ordinary = ads_pair()
    rel = _rel(RelationKind.ALIAS_OF, ads, ads, _receipt("self"))
    with pytest.raises(RelationRefused) as caught:
        validate(rel)
    assert caught.value.code == "SELF_RELATION"


def test_bad_digest_refused():
    ads, ordinary = ads_pair()
    bad = Receipt(
        receipt_id="rcpt-bad",
        source_owner="stock_identity",
        issued_at_utc=ISSUED,
        expires_at_utc=None,
        digest="not-hex",
    )
    rel = _rel(RelationKind.ADS_OF, ads, ordinary, bad, ratio=Fraction(1, 8))
    with pytest.raises(RelationRefused) as caught:
        validate(rel)
    assert caught.value.code == "BAD_DIGEST"


def test_padding_allowed_with_stock_identity_receipt():
    padded = _counter("XHKG", "0700", "HKD")
    unpadded = _counter("XHKG", "700", "HKD")
    rel = _rel(
        RelationKind.ALIAS_OF,
        padded,
        unpadded,
        _receipt("pad-ok", owner="stock_identity"),
    )
    validate(rel)
    assert padded != unpadded
    registry = RelationRegistry()
    registry.add(rel)
    assert registry.rows()[0].relation.a.local_code == "0700"
    assert registry.rows()[0].relation.b.local_code == "700"


def test_authority_flags_stay_false_and_refuse_true():
    for name, value in AUTHORITY_FLAGS.items():
        assert value is False
    registry = RelationRegistry()
    assert registry.rank_authority is False
    assert registry.gate_authority is False
    assert registry.size_authority is False
    assert registry.signal_authority is False
    assert registry.escalation_authority is False
    assert registry.trade_authority is False
    with pytest.raises(RelationRefused) as caught:
        refuse_authority(rank_authority=True)
    assert caught.value.code == "AUTHORITY_FORBIDDEN"
    with pytest.raises(RelationRefused) as caught:
        registry.trade_authority = True
    assert caught.value.code == "AUTHORITY_FORBIDDEN"
    ads, ordinary = ads_pair()
    rel = _rel(RelationKind.ADS_OF, ads, ordinary, _receipt("auth"), ratio=Fraction(1, 8))
    with pytest.raises(RelationRefused) as caught:
        registry.add(rel, signal_authority=True)
    assert caught.value.code == "AUTHORITY_FORBIDDEN"
