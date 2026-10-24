# tests/defense_o2_source_contracts/test_public_agreement_payload.py
"""Tests for the public_agreement documentary contract helper."""

from __future__ import annotations

import copy
import json
import math

import pytest

from engine.government_revenue.public_agreement import (
    AGREEMENT_KEYS,
    agreement_assertion_id,
    agreement_payload_errors,
)


# ---------------------------------------------------------------------------
# Fixtures: byte-identical evidence stubs and matching rows.
# ---------------------------------------------------------------------------


SDA_SOURCE = "https://www.sda.mil/news/tranche2-prototype-agreement"
SDA_RETRIEVED_AT = "2024-10-18T12:00:00Z"
SDA_EVIDENCE_KNOWN_AT = "2024-10-18T13:00:00Z"
SDA_ROW_KNOWN_AT = "2024-10-18T18:00:00Z"
SDA_GRAPH_KNOWN_AT = "2024-12-31T23:59:59Z"

SDA_SHA = "0" * 64
SDA_EVIDENCE_ID = "ev:" + SDA_SHA[:12]

ISSUER_SOURCE = "https://www.l3harris.com/investors/press-release/tranche2"
ISSUER_RETRIEVED_AT = "2024-10-17T12:00:00Z"
ISSUER_EVIDENCE_KNOWN_AT = "2024-10-17T13:00:00Z"
ISSUER_ROW_KNOWN_AT = "2024-10-17T18:00:00Z"

ISSUER_SHA = "1" * 64
ISSUER_EVIDENCE_ID = "ev:" + ISSUER_SHA[:12]


def _evidence(sha, source_url, retrieved_at, known_at, *, evidence_class, **extra):
    record = {
        "evidence_id": "ev:" + sha[:12],
        "sha256": sha,
        "evidence_class": evidence_class,
        "source_url": source_url,
        "retrieved_from_url": source_url,
        "retrieved_at": retrieved_at,
        "known_at": known_at,
        "claim_scopes": ["public_agreement"],
    }
    if evidence_class == "issuer_disclosure":
        record.setdefault("pinned_issuer_host", "www.l3harris.com")
        record.setdefault(
            "pinned_issuer_host_basis",
            "source URL host matches pinned issuer domain",
        )
    record.update(extra)
    return record


def _sda_row():
    row = {
        "id": "prog-agreement:placeholder",
        "revision": 1,
        "source_url": SDA_SOURCE,
        "program_label": "Tranche 2 Tracking Layer",
        "umbrella_label": None,
        "agreement_form": "firm_fixed_price_ota_prototype",
        "parties": [
            {
                "name_literal": "L3Harris Technologies",
                "entity_id": None,
                "potential_value": {
                    "value": 955,
                    "unit": "USD_million",
                    "approximate": True,
                },
                "announced_vehicles": 18,
            },
            {
                "name_literal": "Northrop Grumman",
                "entity_id": None,
                "potential_value": {
                    "value": 798,
                    "unit": "USD_million",
                    "approximate": False,
                },
                "announced_vehicles": 18,
            },
        ],
        "collective_value": {
            "value": 1.75,
            "unit": "USD_billion",
            "approximate": True,
            "overlaps_named_party_values": True,
        },
        "expected_launch_year": 2028,
        "published_on": "2024-07-13",
        "known_at": SDA_ROW_KNOWN_AT,
        "verification_state": "reviewed",
        "evidence_refs": [SDA_EVIDENCE_ID],
        "predecessor_id": None,
        "succession_reason": None,
    }
    row["id"] = agreement_assertion_id(row)
    return row


def _sda_evidence_index():
    return {
        SDA_EVIDENCE_ID: _evidence(
            SDA_SHA,
            SDA_SOURCE,
            SDA_RETRIEVED_AT,
            SDA_EVIDENCE_KNOWN_AT,
            evidence_class="official_contract_announcement",
        )
    }


def _issuer_row():
    row = {
        "id": "prog-agreement:placeholder",
        "revision": 1,
        "source_url": ISSUER_SOURCE,
        "program_label": "Tranche 2 Tracking Layer",
        "umbrella_label": "Proliferated Warfighter Space Architecture",
        "agreement_form": "firm_fixed_price_ota_prototype",
        "parties": [
            {
                "name_literal": "L3Harris Technologies",
                "entity_id": None,
                "potential_value": {
                    "value": 955,
                    "unit": "USD_million",
                    "approximate": True,
                },
                "announced_vehicles": 18,
            }
        ],
        "collective_value": None,
        "expected_launch_year": 2028,
        "published_on": "2024-07-13",
        "known_at": ISSUER_ROW_KNOWN_AT,
        "verification_state": "reviewed",
        "evidence_refs": [ISSUER_EVIDENCE_ID],
        "predecessor_id": None,
        "succession_reason": None,
    }
    row["id"] = agreement_assertion_id(row)
    return row


def _issuer_evidence_index():
    return {
        ISSUER_EVIDENCE_ID: _evidence(
            ISSUER_SHA,
            ISSUER_SOURCE,
            ISSUER_RETRIEVED_AT,
            ISSUER_EVIDENCE_KNOWN_AT,
            evidence_class="issuer_disclosure",
        )
    }


def _canonical(row):
    """Re-encode the same canonical form used by agreement_assertion_id."""
    canonical = {}
    for key in AGREEMENT_KEYS:
        if key == "id":
            continue
        value = row[key]
        if key == "evidence_refs":
            canonical[key] = sorted(value)
        elif key == "parties":
            canonical[key] = list(value)
        else:
            canonical[key] = value
    return json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


# ---------------------------------------------------------------------------
# Positive: identity + payload
# ---------------------------------------------------------------------------


def test_agreement_keys_is_closed_frozenset():
    assert isinstance(AGREEMENT_KEYS, frozenset)
    assert len(AGREEMENT_KEYS) == 15


def test_valid_sda_row_has_no_payload_errors():
    row = _sda_row()
    index = _sda_evidence_index()
    errors = agreement_payload_errors(row, index, graph_known_at=SDA_GRAPH_KNOWN_AT)
    assert errors == [], errors


def test_valid_issuer_row_has_no_payload_errors():
    row = _issuer_row()
    index = _issuer_evidence_index()
    errors = agreement_payload_errors(
        row, index, graph_known_at="2024-12-31T23:59:59Z"
    )
    assert errors == [], errors


def test_assertion_id_is_stable_across_equivalent_parties_reordering_when_separate_rows():
    base = _sda_row()
    index = _sda_evidence_index()
    swapped = copy.deepcopy(base)
    swapped["parties"] = list(reversed(base["parties"]))
    swapped["id"] = agreement_assertion_id(swapped)
    assert base["id"] != swapped["id"]
    assert (
        agreement_payload_errors(base, index, graph_known_at=SDA_GRAPH_KNOWN_AT) == []
    )
    assert (
        agreement_payload_errors(swapped, index, graph_known_at=SDA_GRAPH_KNOWN_AT)
        == []
    )


def test_evidence_refs_sorting_does_not_change_identity():
    row = _sda_row()
    digest_input = list(reversed(row["evidence_refs"]))
    rebuilt = copy.deepcopy(row)
    rebuilt["evidence_refs"] = digest_input
    rebuilt["id"] = agreement_assertion_id(rebuilt)
    assert rebuilt["id"] == row["id"]


def test_revision_two_with_unchanged_evidence_keeps_evidence_id_but_changes_row_id():
    base = _sda_row()
    index = _sda_evidence_index()
    revised = copy.deepcopy(base)
    revised["revision"] = 2
    revised["predecessor_id"] = base["id"]
    revised["succession_reason"] = "corrected"
    revised["known_at"] = "2024-10-19T18:00:00Z"
    revised["evidence_refs"] = list(base["evidence_refs"])
    revised["id"] = agreement_assertion_id(revised)

    assert revised["id"] != base["id"]
    assert revised["evidence_refs"] == [SDA_EVIDENCE_ID]
    errors = agreement_payload_errors(
        revised, index, graph_known_at=SDA_GRAPH_KNOWN_AT
    )
    assert errors == [], errors


def test_changing_known_clock_changes_identity():
    base = _sda_row()
    shifted = copy.deepcopy(base)
    shifted["known_at"] = "2024-10-19T00:00:00Z"
    shifted["id"] = agreement_assertion_id(shifted)
    assert shifted["id"] != base["id"]


def test_changing_literal_changes_identity():
    base = _sda_row()
    shifted = copy.deepcopy(base)
    shifted["program_label"] = "Tranche 2 Transport Layer"
    shifted["id"] = agreement_assertion_id(shifted)
    assert shifted["id"] != base["id"]


def test_parties_must_preserve_source_order_in_canonical_json():
    base = _sda_row()
    encoded_a = _canonical(base)
    swapped = copy.deepcopy(base)
    swapped["parties"] = list(reversed(base["parties"]))
    encoded_b = _canonical(swapped)
    assert encoded_a != encoded_b


# ---------------------------------------------------------------------------
# Negative parametrizations
# ---------------------------------------------------------------------------


MALFORMED_CASES = [
    pytest.param(
        lambda row, index: row.__setitem__("extra_key", "x"),
        lambda row, index: None,
        "public_agreement_unknown_key:extra_key",
        id="unknown-row-key",
    ),
    pytest.param(
        lambda row, index: row.__delitem__("umbrella_label"),
        lambda row, index: None,
        "public_agreement_missing_key:umbrella_label",
        id="missing-required-key",
    ),
    pytest.param(
        lambda row, index: row["parties"][0]["potential_value"].__setitem__(
            "value", True
        ),
        lambda row, index: None,
        "public_agreement_party_0:potential_value:invalid_value",
        id="bool-money-value",
    ),
    pytest.param(
        lambda row, index: row["parties"][0]["potential_value"].__setitem__(
            "value", math.nan
        ),
        lambda row, index: None,
        "public_agreement_party_0:potential_value:invalid_value",
        id="nan-money-value",
    ),
    pytest.param(
        lambda row, index: row["parties"][0]["potential_value"].__setitem__(
            "value", math.inf
        ),
        lambda row, index: None,
        "public_agreement_party_0:potential_value:invalid_value",
        id="inf-money-value",
    ),
    pytest.param(
        lambda row, index: row["parties"][0]["potential_value"].__setitem__(
            "value", -1
        ),
        lambda row, index: None,
        "public_agreement_party_0:potential_value:invalid_value",
        id="negative-money-value",
    ),
    pytest.param(
        lambda row, index: row["parties"][0]["potential_value"].__setitem__(
            "unit", "EUR"
        ),
        lambda row, index: None,
        "public_agreement_party_0:potential_value:invalid_unit",
        id="wrong-money-unit",
    ),
    pytest.param(
        lambda row, index: row["parties"][0]["potential_value"].__setitem__(
            "approximate", "true"
        ),
        lambda row, index: None,
        "public_agreement_party_0:potential_value:invalid_approximate",
        id="approximate-not-bool",
    ),
    pytest.param(
        lambda row, index: row["collective_value"].__setitem__(
            "overlaps_named_party_values", False
        ),
        lambda row, index: None,
        "public_agreement_collective_value:overlaps_must_be_true",
        id="aggregate-overlaps-false",
    ),
    pytest.param(
        lambda row, index: row["parties"][1].__setitem__(
            "name_literal", row["parties"][0]["name_literal"]
        ),
        lambda row, index: None,
        "public_agreement_party_1:duplicate_name_literal",
        id="duplicate-party-literal",
    ),
    pytest.param(
        lambda row, index: row["parties"][0].__setitem__(
            "entity_id", "entity/abc"
        ),
        lambda row, index: None,
        "public_agreement_party_0:entity_id_must_be_null",
        id="fake-entity-id",
    ),
    pytest.param(
        lambda row, index: row.__setitem__(
            "source_url", row["source_url"].replace("https://", "http://")
        ),
        lambda row, index: None,
        "public_agreement_invalid_source_url",
        id="http-source-url",
    ),
    pytest.param(
        lambda row, index: row.__setitem__(
            "source_url", "https://www.sda.mil:443/news"
        ),
        lambda row, index: None,
        "public_agreement_invalid_source_url",
        id="source-url-with-port",
    ),
    pytest.param(
        lambda row, index: row.__setitem__(
            "source_url", row["source_url"].replace("://", "://user:pass@")
        ),
        lambda row, index: None,
        "public_agreement_invalid_source_url",
        id="source-url-userinfo",
    ),
    pytest.param(
        lambda row, index: row.__setitem__(
            "source_url", "https://www.sda-mil.com/news"
        ),
        lambda row, index: None,
        "public_agreement_invalid_official_source_host",
        id="lookalike-source-host",
    ),
    pytest.param(
        lambda row, index: row["parties"][0].__setitem__("announced_vehicles", -1),
        lambda row, index: None,
        "public_agreement_party_0:invalid_announced_vehicles",
        id="negative-announced-vehicles",
    ),
    pytest.param(
        lambda row, index: row["parties"][0].__setitem__("announced_vehicles", True),
        lambda row, index: None,
        "public_agreement_party_0:invalid_announced_vehicles",
        id="bool-announced-vehicles",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("agreement_form", "cost_plus"),
        lambda row, index: None,
        "public_agreement_invalid_agreement_form",
        id="wrong-agreement-form",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("verification_state", "draft"),
        lambda row, index: None,
        "public_agreement_invalid_verification_state",
        id="wrong-verification-state",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("revision", True),
        lambda row, index: None,
        "public_agreement_invalid_revision",
        id="bool-revision",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("revision", 0),
        lambda row, index: None,
        "public_agreement_invalid_revision",
        id="zero-revision",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("revision", 2)
        or row.__setitem__("predecessor_id", "prog-agreement:NOT-HEX")
        or row.__setitem__("succession_reason", "corrected"),
        lambda row, index: None,
        "public_agreement_invalid_predecessor_id",
        id="bad-predecessor-format",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("revision", 2)
        or row.__setitem__("predecessor_id", "prog-agreement:" + "0" * 24)
        or row.__setitem__("succession_reason", "amended"),
        lambda row, index: None,
        "public_agreement_invalid_succession_reason",
        id="wrong-succession-reason",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("published_on", "2024-13-40"),
        lambda row, index: None,
        "public_agreement_invalid_published_on",
        id="invalid-published-on",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("published_on", "2024-7-13"),
        lambda row, index: None,
        "public_agreement_invalid_published_on",
        id="non-zero-padded-published-on",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("expected_launch_year", 1800),
        lambda row, index: None,
        "public_agreement_invalid_expected_launch_year",
        id="expected-launch-year-out-of-range",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("expected_launch_year", True),
        lambda row, index: None,
        "public_agreement_invalid_expected_launch_year",
        id="bool-expected-launch-year",
    ),
    pytest.param(
        lambda row, index: None,
        lambda row, index: index[row["evidence_refs"][0]].__setitem__(
            "evidence_class", "news_article"
        ),
        "public_agreement_invalid_evidence_class",
        id="wrong-evidence-class",
    ),
    pytest.param(
        lambda row, index: None,
        lambda row, index: index[row["evidence_refs"][0]].__setitem__(
            "claim_scopes", ["other_contract"]
        ),
        "public_agreement_evidence_missing_scope",
        id="evidence-missing-scope",
    ),
    pytest.param(
        lambda row, index: None,
        lambda row, index: index[row["evidence_refs"][0]].__setitem__(
            "sha256", "z" * 64
        ),
        "public_agreement_invalid_evidence_sha256",
        id="bad-evidence-sha256",
    ),
    pytest.param(
        lambda row, index: None,
        lambda row, index: index[row["evidence_refs"][0]].__setitem__(
            "sha256", "abcdef" + "0" * 58
        ),
        "public_agreement_evidence_id_field_mismatch",
        id="evidence-id-vs-sha-mismatch",
    ),
    pytest.param(
        lambda row, index: None,
        lambda row, index: index[row["evidence_refs"][0]].__setitem__(
            "retrieved_from_url", "https://www.sda.mil/other"
        ),
        "public_agreement_evidence_retrieved_url_mismatch",
        id="evidence-retrieved-url-mismatch",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("evidence_refs", ["ev:" + "f" * 12]),
        lambda row, index: None,
        "public_agreement_missing_evidence_ref",
        id="dangling-evidence-ref",
    ),
    pytest.param(
        lambda row, index: None,
        lambda row, index: index[row["evidence_refs"][0]].__setitem__(
            "known_at", "2024-10-17T23:00:00Z"
        ),
        "public_agreement_evidence_known_before_retrieved",
        id="evidence-known-before-retrieved",
    ),
    pytest.param(
        lambda row, index: None,
        lambda row, index: index[row["evidence_refs"][0]].__setitem__(
            "known_at", "2024-10-20T00:00:00Z"
        ),
        "public_agreement_known_at_before_evidence_known_at",
        id="row-known-before-evidence",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("known_at", "2024-10-18T18:00:00"),
        lambda row, index: None,
        "public_agreement_invalid_known_at",
        id="naive-known-at",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("known_at", "2024-10-18T18:00:00+05:00"),
        lambda row, index: None,
        "public_agreement_invalid_known_at",
        id="non-utc-known-at",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("known_at", "2024-10-18"),
        lambda row, index: None,
        "public_agreement_invalid_known_at",
        id="date-only-known-at",
    ),
    pytest.param(
        lambda row, index: row.__setitem__("known_at", "2025-01-01T00:00:00Z"),
        lambda row, index: None,
        "public_agreement_known_at_after_graph",
        id="known-at-after-graph",
    ),
    pytest.param(
        lambda row, index: index[row["evidence_refs"][0]].__setitem__(
            "retrieved_at", "2024-10-19T00:00:00Z"
        ),
        lambda row, index: None,
        "public_agreement_evidence_known_before_retrieved",
        id="retrieved-after-known",
    ),
]


@pytest.mark.parametrize("row_mutator,index_mutator,expected_substring", MALFORMED_CASES)
def test_malformed_row_reports_expected_error(
    row_mutator, index_mutator, expected_substring
):
    row = copy.deepcopy(_sda_row())
    index = copy.deepcopy(_sda_evidence_index())
    if row_mutator is not None:
        row_mutator(row, index)
    if index_mutator is not None:
        index_mutator(row, index)
    errors = agreement_payload_errors(row, index, graph_known_at=SDA_GRAPH_KNOWN_AT)
    assert any(expected_substring in err for err in errors), (
        "expected substring %r in %r" % (expected_substring, errors)
    )


# ---------------------------------------------------------------------------
# Issuer-row specific evidence checks
# ---------------------------------------------------------------------------


def _build_issuer_index_mutator(key, value):
    def _mut(row, index):
        index[row["evidence_refs"][0]][key] = value
    return _mut


@pytest.mark.parametrize(
    "mutator,expected_substring",
    [
        (
            _build_issuer_index_mutator("pinned_issuer_host", "www.example.com"),
            "public_agreement_invalid_issuer_pin_host",
        ),
        (
            _build_issuer_index_mutator("pinned_issuer_host_basis", ""),
            "public_agreement_invalid_issuer_pin_basis",
        ),
        (
            _build_issuer_index_mutator("pinned_issuer_host_basis", None),
            "public_agreement_invalid_issuer_pin_basis",
        ),
    ],
)
def test_issuer_pin_violations(mutator, expected_substring):
    row = copy.deepcopy(_issuer_row())
    index = copy.deepcopy(_issuer_evidence_index())
    mutator(row, index)
    errors = agreement_payload_errors(row, index, graph_known_at="2024-12-31T23:59:59Z")
    assert any(expected_substring in err for err in errors), errors


def test_official_host_required_for_official_class():
    row = copy.deepcopy(_sda_row())
    index = copy.deepcopy(_sda_evidence_index())
    row["source_url"] = "https://www.l3harris.com/news"
    errors = agreement_payload_errors(row, index, graph_known_at=SDA_GRAPH_KNOWN_AT)
    assert "public_agreement_invalid_official_source_host" in errors


def test_issuer_host_required_for_issuer_class():
    row = copy.deepcopy(_issuer_row())
    index = copy.deepcopy(_issuer_evidence_index())
    row["source_url"] = "https://www.sda.mil/news"
    errors = agreement_payload_errors(row, index, graph_known_at="2024-12-31T23:59:59Z")
    assert "public_agreement_invalid_issuer_source_host" in errors


# ---------------------------------------------------------------------------
# Identity strictness
# ---------------------------------------------------------------------------


def test_assertion_id_raises_keyerror_on_missing_key():
    row = _sda_row()
    row.pop("umbrella_label")
    with pytest.raises(KeyError):
        agreement_assertion_id(row)


def test_assertion_id_raises_keyerror_on_extra_key():
    row = _sda_row()
    row["junk"] = 1
    with pytest.raises(KeyError):
        agreement_assertion_id(row)


def test_assertion_id_raises_valueerror_on_non_mapping():
    with pytest.raises(ValueError):
        agreement_assertion_id("not a mapping")


def test_assertion_id_raises_valueerror_on_nan_value():
    row = _sda_row()
    row["parties"][0]["potential_value"]["value"] = math.nan
    with pytest.raises(ValueError):
        agreement_assertion_id(row)


def test_identity_mismatch_reported_when_id_lies():
    row = _sda_row()
    index = _sda_evidence_index()
    row["id"] = "prog-agreement:" + "0" * 24
    errors = agreement_payload_errors(row, index, graph_known_at=SDA_GRAPH_KNOWN_AT)
    assert "public_agreement_identity_mismatch" in errors


def test_malformed_row_payload_does_not_throw():
    bad = {"junk": 1}
    errors = agreement_payload_errors(
        bad,
        {},
        graph_known_at=SDA_GRAPH_KNOWN_AT,
    )
    assert any("public_agreement_unknown_key" in e for e in errors)


def test_malformed_graph_clock_is_error_not_throw():
    row = _sda_row()
    index = _sda_evidence_index()
    errors = agreement_payload_errors(row, index, graph_known_at="not a clock")
    assert "public_agreement_graph_known_at_malformed" in errors


def test_payload_errors_does_not_mutate_inputs():
    row = copy.deepcopy(_sda_row())
    index = copy.deepcopy(_sda_evidence_index())
    snapshot_row = copy.deepcopy(row)
    snapshot_index = copy.deepcopy(index)
    agreement_payload_errors(row, index, graph_known_at=SDA_GRAPH_KNOWN_AT)
    assert row == snapshot_row
    assert index == snapshot_index

# Parent adversarial checks: malformed JSON must return errors, never crash or pass.
@pytest.mark.parametrize('bad_unit', [[], {}])
def test_parent_unhashable_money_unit_is_named_error(bad_unit):
    row = _sda_row(); row['parties'][0]['potential_value']['unit'] = bad_unit
    row['id'] = agreement_assertion_id(row)
    assert agreement_payload_errors(row, _sda_evidence_index(), graph_known_at=SDA_GRAPH_KNOWN_AT)


@pytest.mark.parametrize('bad_class', [[], {}])
def test_parent_unhashable_evidence_class_is_named_error(bad_class):
    row = _sda_row(); index = _sda_evidence_index(); index[row['evidence_refs'][0]]['evidence_class'] = bad_class
    assert agreement_payload_errors(row, index, graph_known_at=SDA_GRAPH_KNOWN_AT)


@pytest.mark.parametrize('bad_evidence', [None, [], 'not a receipt'])
def test_parent_non_object_evidence_is_refused(bad_evidence):
    row = _sda_row(); index = _sda_evidence_index(); index[row['evidence_refs'][0]] = bad_evidence
    assert agreement_payload_errors(row, index, graph_known_at=SDA_GRAPH_KNOWN_AT)


def test_parent_nonnumeric_url_port_is_named_error():
    row = _sda_row(); row['source_url'] = 'https://www.sda.mil:not-a-port/example/'
    row['id'] = agreement_assertion_id(row)
    assert agreement_payload_errors(row, _sda_evidence_index(), graph_known_at=SDA_GRAPH_KNOWN_AT)


def test_parent_large_finite_integer_is_not_float_coerced():
    row = _sda_row(); row['parties'][0]['potential_value']['value'] = 10**500
    row['id'] = agreement_assertion_id(row)
    assert not agreement_payload_errors(row, _sda_evidence_index(), graph_known_at=SDA_GRAPH_KNOWN_AT)

@pytest.mark.parametrize('label', ['Synthetic\u202eparty', 'Synthetic\x00party', 'Synthetic\u2028party'])
def test_review_invisible_label_controls_refuse(label):
    row = _sda_row(); row['parties'][0]['name_literal'] = label; row['id'] = agreement_assertion_id(row)
    assert agreement_payload_errors(row, _sda_evidence_index(), graph_known_at=SDA_GRAPH_KNOWN_AT)


@pytest.mark.parametrize('published', ['٢٠٢٦-07-13', '２０２６-07-13'])
def test_review_publication_day_uses_ascii_iso_digits(published):
    row = _sda_row(); row['published_on'] = published; row['id'] = agreement_assertion_id(row)
    assert agreement_payload_errors(row, _sda_evidence_index(), graph_known_at=SDA_GRAPH_KNOWN_AT)


def test_review_source_document_url_agrees_with_versioned_schema_path():
    row = _sda_row(); index = _sda_evidence_index(); row['source_url'] = 'https://www.sda.mil'
    index[row['evidence_refs'][0]].update(source_url=row['source_url'], retrieved_from_url=row['source_url'])
    row['id'] = agreement_assertion_id(row)
    assert agreement_payload_errors(row, index, graph_known_at=SDA_GRAPH_KNOWN_AT)


def test_review_sha256_is_exactly_64_hex_without_newline_alias():
    row = _sda_row(); index = _sda_evidence_index(); index[row['evidence_refs'][0]]['sha256'] += '\n'
    assert agreement_payload_errors(row, index, graph_known_at=SDA_GRAPH_KNOWN_AT)
