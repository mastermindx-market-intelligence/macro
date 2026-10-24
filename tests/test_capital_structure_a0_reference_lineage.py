"""A0-1 lineage harness (SPEC_A0 §3): source → state → calculation → API.

For every dossier expectation the chain is walked in-process against the REAL
``data/capital_structure/`` bundles.  A sparse tree skips the whole lineage
suite with the exact reason ``a0: real bundles absent on this tree``; the
registered legacy job runs it on a full tree.  An expectation the A0-0 checker
reports UNTRACEABLE skips with ``a0: untraceable expectation <TICKER>
<path_id>``; it is never asserted.  Every failure quotes the dossier value and
the served value together: a mismatch is a FINDING, never something to patch.

Merged-name mapping (SPEC_A0 §3 named the pre-merge surface; these are the
merged names this harness asserts against):
- ``_current_user``                -> ``app.capital_structure.require_site_full_user``
- ``CalculationReceipt.operands``  -> the merged receipt carries digests only;
  operand names resolve through the path record's predicates/path_evidence and
  the row's own qualified rule example (``rule_examples[].inputs``/``expected``)
- ``funding_gap_coverage``         -> the scenario-only ``cash_reconciliation``
  and ``funding_schedule`` records, asserted absent from the served state record
- ``INPUTS_PATH``                  -> derived as ``STATE_PATH.parent /
  capacity_inputs.json`` (``CAPACITY_INPUTS_FILENAME``)

Exact arithmetic only (``Decimal``); no score, rank, sizing, probability or
recommendation anywhere; a binary ``float`` never carries a unit here.
"""
from __future__ import annotations

from decimal import Decimal  # exact base-10 arithmetic only; never an approximation
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any

import pytest

pytest.importorskip("fastapi", reason="capital structure lineage API rungs need fastapi")
pytest.importorskip("httpx", reason="FastAPI TestClient needs httpx")

from fastapi.testclient import TestClient  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "check_capital_structure_reference_dossiers.py"

_SPEC = importlib.util.spec_from_file_location(
    "check_capital_structure_reference_dossiers", SCRIPT_PATH,
)
checker = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(checker)

from app import capital_structure as api  # noqa: E402
from tests.test_capital_structure_api import _headers  # noqa: E402
from tests.test_capital_structure_state_api import (  # noqa: E402
    _bare_client,
    _deny_site_full,
    _scenario_body,
)

# Engine modules through the checker's own loader (the real package only).
_rq = checker._engine_module("reference_qualification")
_contracts = checker._engine_module("issuer_state_contracts")
_scenario_inputs_module = checker._engine_module("scenario_inputs")
_compose_module = checker._engine_module("scenario_composition")
_state_bundle_module = checker._engine_module("state_bundle")

PREFIX = "/api/capital-structure/v1"
SCENARIO_TICKERS = ("CLNN", "EDBL")

#: The suite's one sparse-tree exit, byte-for-byte the checker's own message.
BUNDLE_ABSENT = "a0: real bundles absent on this tree"

_TYPED_TUPLES = {
    "SUPPORT_STATES": _contracts.SUPPORT_STATES,
    "QUANTITY_STATUSES": _contracts.QUANTITY_STATUSES,
    "ROUTE_STATUSES": _contracts.ROUTE_STATUSES,
    "CONSTRAINT_STATUSES": _contracts.CONSTRAINT_STATUSES,
    "FLOW_CERTAINTIES": _contracts.FLOW_CERTAINTIES,
}

_EVIDENCE_REF_KEYS = ("manifest_id", "span_id", "text_sha256")
_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")


# ---------------------------------------------------------------------------
# The module-level skip helper (the sparse-tree proof pins its exact reason)
# ---------------------------------------------------------------------------


def _state_bundle_path() -> Path:
    return ROOT / checker.BUNDLE_RELPATH


def _capacity_inputs_path() -> Path:
    return ROOT / "data" / "capital_structure" / _scenario_inputs_module.CAPACITY_INPUTS_FILENAME


def _skip_unless_real_bundles() -> None:
    """Skip with the exact reason unless BOTH real bundles are present."""
    if not _state_bundle_path().is_file() or not _capacity_inputs_path().is_file():
        pytest.skip(BUNDLE_ABSENT)


# ---------------------------------------------------------------------------
# Collection-time parametrization (dossier rows only; bundle-independent)
# ---------------------------------------------------------------------------


def _expectation_params() -> list[Any]:
    params = []
    for _ticker, spec in sorted(checker.load_dossiers(ROOT).items()):
        for row in spec.get("expectations") or []:
            path_id = str(row.get("path_id") or "")
            params.append(pytest.param((str(spec["ticker"]), row), id=f"{spec['ticker']}:{path_id}"))
    return params


def _negative_params() -> list[Any]:
    params = []
    for _ticker, spec in sorted(checker.load_dossiers(ROOT).items()):
        for index, row in enumerate(spec.get("negatives") or (), start=1):
            params.append(pytest.param((str(spec["ticker"]), row), id=f"{spec['ticker']}:neg{index}"))
    return params


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    if "expectation" in metafunc.fixturenames:
        metafunc.parametrize("expectation", _expectation_params())
    if "negative" in metafunc.fixturenames:
        metafunc.parametrize("negative", _negative_params())


# ---------------------------------------------------------------------------
# The one module-scoped fixture: dossiers, pack, REAL bundles, traceability
# ---------------------------------------------------------------------------


class ReferenceChain:
    """Everything the §3 walk needs, loaded once from the real served tree."""

    def __init__(self) -> None:
        self.dossiers = checker.load_dossiers(ROOT)
        self.pack = _rq.load_reference_pack(ROOT / checker.REFERENCE_PACK_RELPATH)
        self.bundle = json.loads(_state_bundle_path().read_text(encoding="utf-8"))
        self.inputs_record = json.loads(_capacity_inputs_path().read_text(encoding="utf-8"))
        rule_ids, pinned_spans = checker._load_rule_pack_ids(ROOT)
        self.results = checker.evaluate_expectations(
            self.dossiers, self.pack, self.bundle,
            rule_ids=rule_ids, pinned_spans=pinned_spans,
        )
        self._by_key = {
            (str(row["ticker"]), str(row["path_id"])): row for row in self.results
        }

    def classification(self, ticker: str, path_id: str) -> tuple[str, str]:
        row = self._by_key.get((ticker, path_id))
        if row is None:
            return "untraceable", "the checker produced no result row for this path_id"
        return str(row["kind"]), str(row["detail"])

    def example(self, example_id: Any) -> Any:
        for candidate in self.pack.rule_examples:
            if candidate.example_id == example_id:
                return candidate
        return None


@pytest.fixture(scope="module")
def chain() -> ReferenceChain:
    _skip_unless_real_bundles()
    return ReferenceChain()


def _admitted(chain: ReferenceChain, expectation: tuple[str, dict[str, Any]]):
    """Run only checker-traceable rows; skip UNTRACEABLE and gap rows by name."""
    ticker, row = expectation
    path_id = str(row.get("path_id"))
    kind, _detail = chain.classification(ticker, path_id)
    if kind == "untraceable":
        pytest.skip(f"a0: untraceable expectation {ticker} {path_id}")
    if kind == "gap":
        pytest.skip(f"a0: gap expectation {ticker} {path_id} (dossier fixes no expected value)")
    return ticker, row


# ---------------------------------------------------------------------------
# The ONE shared response check every response passes through (§3 last para)
# ---------------------------------------------------------------------------


def _assert_no_unit_floats(value: Any, in_unit_record: bool = False) -> None:
    """No binary float may carry a unit: unit-bearing numbers are exact ints/strings."""
    if isinstance(value, dict):
        unit_record = in_unit_record or "unit" in value
        for item in value.values():
            _assert_no_unit_floats(item, unit_record)
        return
    if isinstance(value, list):
        for item in value:
            _assert_no_unit_floats(item, in_unit_record)
        return
    if isinstance(value, bool) or isinstance(value, str) or value is None:
        return
    assert not (in_unit_record and isinstance(value, float)), (
        f"a unit-bearing JSON number arrived as a binary float: {value!r}"
    )


def _assert_evidence_keys_present(value: Any) -> None:
    """Wherever a body carries an ``evidence`` key it carries exact refs."""
    if isinstance(value, dict):
        if "evidence" in value:
            evidence = value["evidence"]
            assert evidence is not None, "an evidence key arrived null"
            rows = evidence if isinstance(evidence, list) else [evidence]
            for row in rows:
                assert isinstance(row, dict), f"evidence ref is not an object: {row!r}"
                for key in _EVIDENCE_REF_KEYS:
                    assert str(row.get(key) or "").strip(), (
                        f"evidence ref missing {key}: {row!r}"
                    )
        for item in value.values():
            _assert_evidence_keys_present(item)
        return
    if isinstance(value, list):
        for item in value:
            _assert_evidence_keys_present(item)


def _check_response(response: Any, *, status: int | None = None) -> dict[str, Any]:
    """Private no-store body, no validators, no recommendation vocabulary,
    no unit-bearing float, every evidence key present."""
    if status is not None:
        assert response.status_code == status, (
            status, response.status_code, response.text[:400]
        )
    _headers(response)
    assert response.headers.get("etag") is None
    assert response.headers.get("last-modified") is None
    body = response.json()
    serialized = json.dumps(body, sort_keys=True).lower()
    for word in api._RECOMMENDATION_WORDS:
        assert word not in serialized, word
    _assert_no_unit_floats(body)
    _assert_evidence_keys_present(body)
    return body


# ---------------------------------------------------------------------------
# Served-record readers (bundle shapes, never fixtures)
# ---------------------------------------------------------------------------


def _served_issuer(bundle: dict[str, Any], issuer_id: str) -> dict[str, Any] | None:
    for row in bundle.get("issuers") or []:
        if str((row.get("request") or {}).get("issuer_id")) == issuer_id:
            return row
    return None


def _family_record_named(issuer_record: dict[str, Any], family: str) -> dict[str, Any] | None:
    for row in issuer_record.get("families") or []:
        if str(row.get("family")) == family:
            return row
    return None


def _path_evidence_keys(bundle: dict[str, Any], issuer_id: str, path_id: str) -> list[str]:
    index = (bundle.get("issuer_index") or {}).get(issuer_id) or {}
    return [str(key) for key in (index.get("path_evidence") or {}).get(path_id) or ()]


def _evidence_refs_for(bundle: dict[str, Any], keys: list[str]) -> list[dict[str, str]]:
    refs = []
    for key in keys:
        entry = bundle["evidence_index"][key]
        refs.append({name: str(entry[name]) for name in _EVIDENCE_REF_KEYS})
    return refs


def _cited_rule_ids(path_record: dict[str, Any]) -> set[str]:
    cited: set[str] = set()
    for predicate in (path_record.get("predicates") or {}).values():
        if isinstance(predicate, dict):
            cited.update(str(rule) for rule in predicate.get("rule_ids") or ())
    return cited


def _first_known_quantity(value: Any, needle: str | None = None, context: str = "") -> str | None:
    """The first known Quantity-shaped record, optionally under a named context."""
    if isinstance(value, dict):
        local = " ".join(
            [str(key) for key in value]
            + [str(item) for item in value.values() if isinstance(item, str)]
        )
        context = f"{context} {local}".strip()
        if (
            value.get("status") == "known"
            and all(name in value for name in ("unit", "status"))
            and (needle is None or needle in context.lower())
        ):
            return context
        for key, item in value.items():
            found = _first_known_quantity(
                item, needle,
                f"{context} {key}".strip() if isinstance(key, str) else context,
            )
            if found is not None:
                return found
        return None
    if isinstance(value, list):
        for item in value:
            found = _first_known_quantity(item, needle, context)
            if found is not None:
                return found
    return None


# ---------------------------------------------------------------------------
# §3 step 1 — source rung
# ---------------------------------------------------------------------------


def test_a0_source_rung_gold_and_span_bound(
    chain: ReferenceChain, expectation: tuple[str, dict[str, Any]]
) -> None:
    ticker, row = _admitted(chain, expectation)
    spec = chain.dossiers[ticker]
    identity = _rq.identity_for(chain.pack, ticker)
    assert spec["issuer_id"] == identity.issuer_id, (
        f"{ticker}: dossier issuer_id {spec['issuer_id']!r} vs pack identity {identity.issuer_id!r}"
    )

    problems = _rq.verify_gold_fixtures(chain.pack, ROOT)
    assert not problems, f"{ticker}: gold fixtures failed the pack: {problems}"

    bundle_index = chain.bundle.get("evidence_index") or {}
    pack_spans = checker._pack_span_index(chain.pack)
    for operand in row.get("operands") or ():
        name = str(operand.get("name"))
        ref = operand.get("ref")
        if ref is not None:
            entry = bundle_index.get(str(ref))
            assert entry is not None, (
                f"{ticker}/{row['path_id']}: operand {name!r} ref {ref} is not in the "
                f"served evidence_index (the index holds {len(bundle_index)} entries)"
            )
            assert str(entry.get("issuer_id")) == spec["issuer_id"], (
                f"{ticker}/{row['path_id']}: operand {name!r} evidence is served for "
                f"{entry.get('issuer_id')!r}, not {spec['issuer_id']!r}"
            )
            claimed = operand.get("text_sha256")
            if claimed is not None:
                served = str(entry.get("text_sha256") or entry.get("ledger_text_sha256"))
                assert served == str(claimed), (
                    f"{ticker}/{row['path_id']}: operand {name!r} dossier digest "
                    f"{claimed!r} vs served entry digest {served!r}"
                )
        else:
            label = str(operand.get("pack_span"))
            digest = pack_spans.get(label)
            assert digest is not None, (
                f"{ticker}/{row['path_id']}: operand {name!r} pack span {label!r} is "
                f"absent from the qualified pack sources"
            )
            claimed = operand.get("text_sha256")
            if claimed is not None:
                assert digest == str(claimed), (
                    f"{ticker}/{row['path_id']}: operand {name!r} dossier digest "
                    f"{claimed!r} vs pack span digest {digest!r}"
                )


# ---------------------------------------------------------------------------
# §3 step 2 — state rung
# ---------------------------------------------------------------------------


def _example_numeric_pool(example: Any) -> dict[str, str]:
    """The example's numeric operand values, keyed by its own names."""
    pool: dict[str, str] = {}
    if example is None:
        return pool
    for source in (example.inputs, example.expected):
        for key, value in source.items():
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                continue
            try:
                Decimal(str(value))
            except Exception:  # noqa: BLE001 — a non-numeric example value is no operand value
                continue
            pool.setdefault(str(key), str(value))
    return pool


def _resolve_operand_key(pool: dict[str, str], name: str) -> str | None:
    """Exact name first; else one unique token-subset match in the same pool."""
    if name in pool:
        return name
    wanted = _tokens_of(name)
    if not wanted:
        return None
    candidates = [key for key in pool if wanted <= _tokens_of(key)]
    if len(candidates) == 1:
        return candidates[0]
    return None


def _tokens_of(name: str) -> frozenset[str]:
    return frozenset(part for part in _TOKEN_SPLIT.split(name.lower()) if part)


def test_a0_state_rung_path_supported_with_named_operands(
    chain: ReferenceChain, expectation: tuple[str, dict[str, Any]]
) -> None:
    ticker, row = _admitted(chain, expectation)
    spec = chain.dossiers[ticker]
    path_id = str(row["path_id"])
    family_name = str(row["family"])

    issuer_record = _served_issuer(chain.bundle, spec["issuer_id"])
    assert issuer_record is not None, (
        f"{ticker}/{path_id}: the served bundle carries no issuer record for "
        f"{spec['issuer_id']!r} (served: "
        f"{[str((r.get('request') or {}).get('issuer_id')) for r in chain.bundle.get('issuers') or []]})"
    )
    family = _family_record_named(issuer_record, family_name)
    assert family is not None, (
        f"{ticker}/{path_id}: the served families "
        f"{[str(r.get('family')) for r in issuer_record.get('families') or []]!r} "
        f"carry no {family_name!r} family record"
    )
    support = str((family.get("provenance") or {}).get("support"))
    assert support in ("supported", "partial"), (
        f"{ticker}/{path_id}: family {family_name!r} provenance support {support!r} "
        f"is neither supported nor partial"
    )

    served_paths = {
        str(item.get("path_id")): item for item in family.get("records") or []
    }
    assert path_id in served_paths, (
        f"{ticker}/{path_id}: FINDING — the served {family_name!r} family publishes "
        f"path ids {sorted(served_paths)!r}, not the dossier path_id"
    )

    receipt = issuer_record.get("receipt") or {}
    for name in ("input_digest", "rule_digest", "implementation_digest"):
        assert re.match(r"^[0-9a-f]{64}$", str(receipt.get(name) or "")), (
            f"{ticker}/{path_id}: the served state receipt {name} is "
            f"{receipt.get(name)!r}, not a sha256 hex digest"
        )

    pool = _example_numeric_pool(chain.example(row.get("rule_example_id")))
    serialized_path = json.dumps(served_paths.get(path_id) or {}, sort_keys=True)
    for operand in row.get("operands") or ():
        name = str(operand.get("name"))
        resolved = _resolve_operand_key(pool, name)
        named = resolved is not None or f'"{name}"' in serialized_path
        assert named, (
            f"{ticker}/{path_id}: dossier operand {name!r} is named neither by its "
            f"rule example {row.get('rule_example_id')!r} (keys {sorted(pool)!r}) "
            f"nor by the served path record"
        )


# ---------------------------------------------------------------------------
# §3 step 3 — calculation rung (exact Decimal recompute)
# ---------------------------------------------------------------------------

_ARITH_TOKEN = re.compile(r"\s*(min|max|\(|\)|[+\-*/]|[A-Za-z_][A-Za-z0-9_]*|[0-9]+)")


def _tokenize_arithmetic(expression: str) -> list[str]:
    tokens: list[str] = []
    position = 0
    while position < len(expression):
        matched = _ARITH_TOKEN.match(expression, position)
        if matched is None:
            if not expression[position:].strip():
                break
            raise ValueError(f"unparsable arithmetic at {expression[position:]!r}")
        tokens.append(matched.group(1))
        position = matched.end()
    return tokens


class _Arithmetic:
    """Recursive-descent exact evaluator over Decimal: + - * / ( ) min max."""

    def __init__(self, tokens: list[str], resolve: Any) -> None:
        self.tokens = tokens
        self.position = 0
        self.resolve = resolve

    def evaluate(self) -> Decimal:
        value = self._expr()
        assert self.position == len(self.tokens), (
            f"trailing arithmetic tokens {self.tokens[self.position:]!r}"
        )
        return value

    def _peek(self) -> str | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def _take(self, expected: str | None = None) -> str:
        token = self._peek()
        assert token is not None, "arithmetic ended early"
        if expected is not None:
            assert token == expected, f"expected {expected!r} in arithmetic, found {token!r}"
        self.position += 1
        return token

    def _expr(self) -> Decimal:
        value = self._term()
        while self._peek() in ("+", "-"):
            if self._take() == "+":
                value = value + self._term()
            else:
                value = value - self._term()
        return value

    def _term(self) -> Decimal:
        value = self._factor()
        while self._peek() in ("*", "/"):
            if self._take() == "*":
                value = value * self._factor()
            else:
                divisor = self._factor()
                quotient = value / divisor
                assert quotient * divisor == value, (
                    f"division {value} / {divisor} is not exact"
                )
                value = quotient
        return value

    def _factor(self) -> Decimal:
        token = self._peek()
        assert token is not None, "arithmetic ended early"
        if token == "(":
            self._take("(")
            value = self._expr()
            self._take(")")
            return value
        if token in ("min", "max"):
            self._take()
            self._take("(")
            first = self._expr()
            self._take(",")
            second = self._expr()
            self._take(")")
            return min(first, second) if token == "min" else max(first, second)
        self._take()
        if token.isdigit():
            return Decimal(int(token))
        return self.resolve(token)


def _operand_resolver(chain: ReferenceChain, row: dict[str, Any]):
    """Resolve operand VALUES from the row's own qualified rule example only.

    Exact key match first; otherwise a unique token-subset match within the
    same example — the pack's own extraction of the very span the operand
    locator names.  Anything else raises, and the test reports it as a finding.
    """
    pool = _example_numeric_pool(chain.example(row.get("rule_example_id")))

    def resolve(name: str) -> Decimal:
        key = _resolve_operand_key(pool, name)
        if key is not None:
            return Decimal(pool[key])
        raise KeyError(
            f"operand {name!r} resolves to no exact rule-example value "
            f"(pool: {sorted(pool)!r})"
        )

    return resolve


def test_a0_calculation_rung_exact_decimal_recompute(
    chain: ReferenceChain, expectation: tuple[str, dict[str, Any]]
) -> None:
    ticker, row = _admitted(chain, expectation)
    expected_text = str(row["expected"])
    dossier_value = Decimal(expected_text)
    try:
        computed = _Arithmetic(
            _tokenize_arithmetic(str(row["arithmetic"])),
            _operand_resolver(chain, row),
        ).evaluate()
    except KeyError as error:
        raise AssertionError(
            f"{ticker}/{row['path_id']}: FINDING — the stated arithmetic cannot be "
            f"recomputed from permitted in-harness operands: {error.args[0]}"
        ) from error
    computed_text = format(computed, "f")
    assert computed_text == format(dossier_value, "f"), (
        f"{ticker}/{row['path_id']}: FINDING — dossier expected {expected_text!r} vs "
        f"recomputed {computed_text!r} from arithmetic {row['arithmetic']!r}"
    )


# ---------------------------------------------------------------------------
# §3 steps 4–5 — API rung and scenario rung
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def a0_client(chain: ReferenceChain):
    """The entitled browser-equivalent client: app.main's app, entitlement granted."""
    from app.main import app as main_app

    main_app.dependency_overrides[api.require_site_full_user] = lambda: {
        "id": "a0-lineage-entitled-user"
    }
    api._reset_cache()
    api._reset_state_cache()
    api._reset_inputs_cache()
    yield TestClient(main_app)
    main_app.dependency_overrides.pop(api.require_site_full_user, None)
    api._reset_cache()
    api._reset_state_cache()
    api._reset_inputs_cache()


def test_a0_api_rung_state_registration_and_evidence_agree(
    chain: ReferenceChain,
    a0_client: TestClient,
    expectation: tuple[str, dict[str, Any]],
) -> None:
    ticker, row = _admitted(chain, expectation)
    spec = chain.dossiers[ticker]
    path_id = str(row["path_id"])
    issuer_id = spec["issuer_id"]
    bundle = chain.bundle

    state_body = _check_response(
        a0_client.get(f"{PREFIX}/issuers/{issuer_id}/state"), status=200
    )
    issuer_record = _served_issuer(bundle, issuer_id)
    assert issuer_record is not None, (
        f"{ticker}/{path_id}: no served issuer record for {issuer_id!r}"
    )
    assert state_body["view"] == {
        "mode": "current",
        "as_of": bundle["as_of"],
        "clock": "system",
        "state_id": str(issuer_record["state_id"]),
        "generation_id": bundle["generation_id"],
        "scenario_id": None,
    }, f"{ticker}/{path_id}: the /state view echo drifted: {state_body['view']!r}"

    family_name = str(row["family"])
    state_family = (state_body.get("families") or {}).get(family_name)
    assert state_family is not None, (
        f"{ticker}/{path_id}: the /state families "
        f"{sorted(state_body.get('families') or {})!r} omit {family_name!r}"
    )
    state_paths = {
        str(item.get("path_id")): item for item in state_family.get("records") or []
    }
    assert path_id in state_paths, (
        f"{ticker}/{path_id}: FINDING — the /state {family_name!r} family publishes "
        f"{sorted(state_paths)!r}, not the dossier path_id"
    )

    registration_body = _check_response(
        a0_client.get(f"{PREFIX}/issuers/{issuer_id}/state/registration"), status=200
    )
    registration_paths = {
        str(item.get("path_id")): item for item in registration_body.get("paths") or []
    }
    assert path_id in registration_paths, (
        f"{ticker}/{path_id}: FINDING — /state/registration publishes "
        f"{sorted(registration_paths)!r}, not the dossier path_id"
    )
    refs = _evidence_refs_for(bundle, _path_evidence_keys(bundle, issuer_id, path_id))
    assert registration_paths[path_id]["evidence"] == refs, (
        f"{ticker}/{path_id}: /state/registration evidence "
        f"{registration_paths[path_id]['evidence']!r} vs bundle-derived {refs!r}"
    )
    cited = _cited_rule_ids(state_paths[path_id])
    assert set(registration_paths[path_id].get("rule_status") or {}) == cited, (
        f"{ticker}/{path_id}: rule_status "
        f"{sorted(registration_paths[path_id].get('rule_status') or {})!r} vs the state "
        f"record's cited rules {sorted(cited)!r}"
    )
    if row.get("rule_id") is not None:
        assert str(row["rule_id"]) in cited, (
            f"{ticker}/{path_id}: FINDING — dossier rule {row['rule_id']!r} is not "
            f"among the served cited rules {sorted(cited)!r}"
        )

    for ref in refs:
        evidence_body = _check_response(
            a0_client.get(
                f"{PREFIX}/issuers/{issuer_id}/evidence/"
                f"{ref['manifest_id']}/{ref['span_id']}"
            ),
            status=200,
        )
        entry = bundle["evidence_index"][f"{ref['manifest_id']}/{ref['span_id']}"]
        assert evidence_body["text_sha256"] == entry["text_sha256"], (
            f"{ticker}/{path_id}: the evidence route serves digest "
            f"{evidence_body['text_sha256']!r} vs bundle {entry['text_sha256']!r}"
        )
        for operand in evidence_body.get("operands") or []:
            assert operand["path_id"] == path_id, (
                f"{ticker}/{path_id}: evidence operand names path {operand['path_id']!r}"
            )
            predicate = (state_paths[path_id].get("predicates") or {}).get(
                str(operand["name"])
            )
            assert predicate is not None, (
                f"{ticker}/{path_id}: evidence operand {operand['name']!r} names no "
                f"predicate of the served path record"
            )
            assert operand["value"] == predicate.get("status"), (
                f"{ticker}/{path_id}: evidence operand {operand['name']!r} value "
                f"{operand['value']!r} vs state predicate {predicate.get('status')!r}"
            )


def test_a0_scenario_rung_supply_and_cash_separate(
    chain: ReferenceChain,
    a0_client: TestClient,
    expectation: tuple[str, dict[str, Any]],
) -> None:
    ticker, row = _admitted(chain, expectation)
    if ticker not in SCENARIO_TICKERS:
        pytest.skip(f"a0: no scenario path for {ticker}")
    spec = chain.dossiers[ticker]
    issuer_id = spec["issuer_id"]
    bundle = chain.bundle

    action_kind = "at_the_market" if ticker == "CLNN" else "shelf_takedown"
    scenario = _contracts.FinancingScenario(
        view="counterfactual",
        as_of=str(bundle["as_of"]),
        horizon_start=str(bundle["as_of"])[:10],
        horizon_end=str(bundle["as_of"])[:10],
        price=_contracts.PriceAssumption("fixed", "USD", fixed_price="1.00"),
        actions=(
            _contracts.ActionSelection(
                route_id=_contracts.stable_id(
                    "route", {"ticker": ticker, "path_id": str(row["path_id"])}
                ),
                action=action_kind,
                settlement="cash",
            ),
        ),
        fee_rate="0.05",
        label=f"a0 reference lineage scenario {row['path_id']}",
    )
    response = a0_client.post(
        f"{PREFIX}/issuers/{issuer_id}/scenarios/evaluate",
        json=_scenario_body(scenario),
    )
    assert response.status_code == 200, (
        f"{ticker}/{row['path_id']}: FINDING — the scenario rung refused the chain: "
        f"{response.status_code} {response.text[:300]!r}"
    )
    body = _check_response(response, status=200)

    state = _state_bundle_module.state_from_record(_served_issuer(bundle, issuer_id))
    assembled = _scenario_inputs_module.assemble_scenario_inputs(
        chain.inputs_record,
        issuer_id,
        scenario.as_of,
        served_state_generation_id=str(bundle["generation_id"]),
    )
    assert not isinstance(assembled, _scenario_inputs_module.ScenarioInputsUnavailable)
    recomputed = _compose_module.compose_scenario(
        state,
        assembled.instruments,
        assembled.basis,
        assembled.financials,
        assembled.commitments,
        scenario,
        assembled.rules,
        pack=api._rule_pack(),
    ).as_record()
    assert json.dumps(body["result"], sort_keys=True) == json.dumps(
        recomputed, sort_keys=True
    ), (
        f"{ticker}/{row['path_id']}: the served scenario result is not "
        f"compose_scenario's own record for the same inputs bundle"
    )
    _contracts.validate_state_record("scenario_result", body["result"])

    supply_rows = body["result"]["issuance_rows"]
    cash_rows = body["result"]["cash_reconciliation"]
    serialized_cash = {json.dumps(row, sort_keys=True) for row in cash_rows}
    for supply in supply_rows:
        assert json.dumps(supply, sort_keys=True) not in serialized_cash, (
            f"{ticker}/{row['path_id']}: a supply row and a cash row collapsed into "
            f"one record: {supply!r}"
        )
    served_record = json.dumps(_served_issuer(bundle, issuer_id), sort_keys=True)
    for scenario_only in ("cash_reconciliation", "funding_schedule"):
        assert f'"{scenario_only}"' in json.dumps(body["result"]), (
            f"{ticker}/{row['path_id']}: the scenario result carries no "
            f"{scenario_only!r} record"
        )
        assert scenario_only not in served_record, (
            f"{ticker}/{row['path_id']}: {scenario_only!r} leaked into the served "
            f"state record; the funding half is scenario-only"
        )


# ---------------------------------------------------------------------------
# §3 step 6 — negative rung: typed states and exact refusal texts, never numbers
# ---------------------------------------------------------------------------


def _probe_date(spec: dict[str, Any]) -> str | None:
    """The archetype's own probe date from the J5 section (never the cutoff)."""
    text = (ROOT / checker.DOSSIER_DIR / f"{spec['ticker']}.md").read_text(encoding="utf-8")
    section = text.split("## J5 cutoff", 1)[-1].split("## ", 1)[0]
    others = [
        day for day in re.findall(r"\d{4}-\d{2}-\d{2}", section)
        if day != str(spec["j5_cutoff"])
    ]
    return others[-1] if others else None


def _negative_detail(
    chain: ReferenceChain,
    a0_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    ticker: str,
    row: dict[str, Any],
    text: str,
) -> None:
    spec = chain.dossiers[ticker]
    issuer_id = spec["issuer_id"]
    if text == "issuer not covered":
        stranger = "sec:cik:0000000000"
        assert stranger not in json.dumps(chain.bundle), (
            f"{ticker}: the probe issuer {stranger!r} is served; pick an absent one"
        )
        response = a0_client.get(f"{PREFIX}/issuers/{stranger}/state")
        assert response.status_code == 404, (
            f"{ticker}: FINDING — an uncovered issuer answered {response.status_code} "
            f"{response.text[:200]!r} instead of the typed refusal"
        )
        assert response.json()["detail"] == text, (
            f"{ticker}: detail {response.json()['detail']!r} vs dossier {text!r}"
        )
        _headers(response)
        return
    if text == "evidence hash mismatch":
        keys = sorted(chain.bundle.get("evidence_index") or {})
        assert keys, f"{ticker}: no served evidence span exists to probe the refusal"
        key = keys[0]
        owner = str(chain.bundle["evidence_index"][key]["issuer_id"])
        manifest_id, span_id = key.split("/", 1)
        mutated = json.loads(json.dumps(chain.bundle, sort_keys=True))
        mutated["evidence_index"][key]["ledger_text_sha256"] = _contracts.sha256_of(
            {"diverged": key}
        )
        monkeypatch.setattr(api, "_load_state", lambda: mutated)
        response = a0_client.get(
            f"{PREFIX}/issuers/{owner}/evidence/{manifest_id}/{span_id}"
        )
        assert response.status_code == 409, (
            f"{ticker}: FINDING — a diverged evidence digest answered "
            f"{response.status_code} {response.text[:200]!r} instead of the typed refusal"
        )
        assert response.json()["detail"] == text, (
            f"{ticker}: detail {response.json()['detail']!r} vs dossier {text!r}"
        )
        _headers(response)
        return
    if text == "unknown_at_date":
        cutoff = _probe_date(spec)
        assert cutoff is not None, (
            f"{ticker}: the dossier names no then-known probe date to refuse with"
        )
        response = a0_client.get(
            f"{PREFIX}/issuers/{issuer_id}/state?mode=then_known&cutoff={cutoff}"
        )
        if response.status_code == 200:
            body = _check_response(response, status=200)
            pending = body.get("not_yet_observed") or []
            statuses = {str(item.get("status")) for item in pending}
            assert statuses == {"unknown_at_date"}, (
                f"{ticker}: FINDING — then-known statuses {statuses!r} at {cutoff} "
                f"vs the dossier's {text!r}"
            )
            return
        assert response.status_code == 400, (
            f"{ticker}: FINDING — the then-known view at {cutoff} answered "
            f"{response.status_code} {response.text[:300]!r} instead of the typed "
            f"{text!r} rows or a fail-closed cutoff"
        )
        assert response.json()["detail"]["reason"] == "before_first_bound_event", (
            f"{ticker}: {response.json()['detail']!r} is not the fail-closed cutoff"
        )
        _headers(response)
        return
    # A standing phrase's rendered copy is the browser rung (§4); the API rung
    # proves its no-sum half: an unproved family that computes no number.
    served = _served_issuer(chain.bundle, issuer_id)
    assert served is not None, f"{ticker}: no served issuer record for {issuer_id!r}"
    family_name = str(
        (spec["expectations"][0] or {}).get("family") if spec.get("expectations") else "registration"
    )
    family = _family_record_named(served, family_name)
    support = str(((family or {}).get("provenance") or {}).get("support"))
    leak = _first_known_quantity(family or {})
    assert leak is None, (
        f"{ticker}: FINDING — the dossier negative {row.get('name')!r} ({text!r}) "
        f"forbids a number, the served state computed one under {leak!r}"
    )
    assert support in ("partial", "unavailable", "not_built"), (
        f"{ticker}: the standing phrase {text!r} requires an unproved family, but "
        f"the served {family_name!r} provenance support is {support!r}"
    )


def test_a0_negative_rung_typed_states_never_numbers(
    chain: ReferenceChain,
    a0_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    negative: tuple[str, dict[str, Any]],
) -> None:
    ticker, row = negative
    expect = str(row.get("expect"))
    state_name = row.get("state")
    if state_name is not None:
        members = _TYPED_TUPLES.get(str(state_name))
        assert members is not None, (
            f"{ticker}/{row.get('name')}: {state_name!r} is not a frozen contract tuple"
        )
        assert expect in members, (
            f"{ticker}/{row.get('name')}: FINDING — negative expect {expect!r} is not "
            f"a member of {state_name} {list(members)!r}; a negative is never a number"
        )
        if row.get("name") == "authorized_shares_not_established":
            assert _compose_module.AUTHORIZED_HEADROOM_UNKNOWN in str(row.get("reason") or ""), (
                f"{ticker}: the dossier must name the engine's own §7a unknown code "
                f"{_compose_module.AUTHORIZED_HEADROOM_UNKNOWN!r}"
            )
        rule_id = row.get("rule_id")
        if rule_id is not None:
            rule_ids, _pinned = checker._load_rule_pack_ids(ROOT)
            if str(rule_id) not in rule_ids:
                mentioned = set(re.findall(r"`([a-z0-9_]+)`", str(row.get("reason") or "")))
                open_gaps = {
                    str(gap.get("gap_id"))
                    for gap in chain.pack.gaps
                    if str(gap.get("status") or "inherited") == "open"
                }
                named = mentioned & open_gaps
                assert named, (
                    f"{ticker}/{row.get('name')}: rule {rule_id!r} is in no active pack "
                    f"and the negative names none of the pack's open gaps {sorted(open_gaps)!r}"
                )
        return
    assert expect.startswith("detail:"), (
        f"{ticker}/{row.get('name')}: {expect!r} is neither a typed state nor detail text"
    )
    _negative_detail(chain, a0_client, monkeypatch, ticker, row, expect[len("detail:"):])


# ---------------------------------------------------------------------------
# §3 step 7 — entitlement before any read
# ---------------------------------------------------------------------------


def test_a0_entitlement_before_any_read(
    chain: ReferenceChain, monkeypatch: pytest.MonkeyPatch
) -> None:
    issuer_id = chain.dossiers["AIR"]["issuer_id"]
    urls = (
        ("GET", f"{PREFIX}/issuers/{issuer_id}/state", None),
        ("GET", f"{PREFIX}/issuers/{issuer_id}/state/registration", None),
        ("GET", f"{PREFIX}/issuers/{issuer_id}/evidence/manifest:probe/span:probe", None),
        ("GET", f"{PREFIX}/coverage", None),
        ("POST", f"{PREFIX}/issuers/{issuer_id}/scenarios/evaluate", {}),
    )

    def refuse(reader: str):
        def _refuse(*_args, **_kwargs):
            raise AssertionError(f"{reader} must follow entitlement")

        return _refuse

    for method, url, body in urls:
        _deny_site_full(monkeypatch)
        for reader in ("_load", "_load_state", "_load_inputs", "_load_generation"):
            monkeypatch.setattr(api, reader, refuse(reader))
        with _bare_client() as bare:
            if method == "GET":
                response = bare.get(url)
            else:
                response = bare.post(url, json=body)
        assert response.status_code == 403, (
            f"{url}: FINDING — an unentitled request answered {response.status_code} "
            f"{response.text[:200]!r} after the loaders were armed to refuse"
        )
        _headers(response)
        detail = response.json()["detail"]
        assert detail["required_feature"] == "site_full", (
            f"{url}: the denial names {detail!r}, not the site_full gate"
        )
        monkeypatch.undo()


# ---------------------------------------------------------------------------
# The withheld family — WHK proves the honest state instead of a number
# ---------------------------------------------------------------------------


def test_a0_whk_family_is_withheld_honestly(
    chain: ReferenceChain, a0_client: TestClient
) -> None:
    spec = chain.dossiers["WHK"]
    assert spec["verdict_hint"] == "withheld", (
        f"WHK: verdict hint {spec['verdict_hint']!r} is not the construction's withheld"
    )
    assert "whk_replacement_issuer" in spec["gap_ids"]
    issuer_id = spec["issuer_id"]

    served = _served_issuer(chain.bundle, issuer_id)
    assert served is not None, (
        f"WHK: no served issuer record for {issuer_id!r} — the withheld family "
        f"cannot be proven honest on an issuer the bundle does not carry"
    )
    bundle_family = _family_record_named(served, "instruments")
    assert bundle_family is None, (
        f"WHK: FINDING — the withheld instruments family is served as a record "
        f"{json.dumps(bundle_family, sort_keys=True)[:300]!r}"
    )

    body = _check_response(
        a0_client.get(f"{PREFIX}/issuers/{issuer_id}/state"), status=200
    )
    assert "instruments" not in (body.get("families") or {}), (
        f"WHK: FINDING — the API served the withheld family: "
        f"{json.dumps(body['families'].get('instruments'), sort_keys=True)[:300]!r}"
    )
    leak = _first_known_quantity(body, "instrument")
    assert leak is None, (
        f"WHK: FINDING — a number rendered for the withheld family under {leak!r}"
    )
    prior_label = str(_rq.identity_for(chain.pack, "WHK").prior_label or "")
    assert prior_label, "WHK: the pack binds no prior label for the recorded drift"
    assert prior_label not in json.dumps(body.get("identity") or {}), (
        f"WHK: FINDING — the prior label {prior_label!r} rendered as current identity"
    )

    bundle_index = chain.bundle.get("evidence_index") or {}
    witness_keys = [
        key for key, entry in sorted(bundle_index.items())
        if str(entry.get("issuer_id")) == issuer_id
    ]
    dossier_keys = [
        str(operand["ref"])
        for row in spec["expectations"]
        for operand in row.get("operands") or ()
        if operand.get("ref")
    ]
    for key in sorted(set(witness_keys + dossier_keys)):
        manifest_id, span_id = key.split("/", 1)
        witness = a0_client.get(
            f"{PREFIX}/issuers/{issuer_id}/evidence/{manifest_id}/{span_id}"
        )
        if witness.status_code == 404:
            assert witness.json()["detail"] == "evidence not found", (
                f"WHK: evidence refusal detail {witness.json()['detail']!r}"
            )
            _headers(witness)
            continue
        witness_body = _check_response(witness, status=200)
        for operand in witness_body.get("operands") or []:
            value = operand.get("value")
            assert value is None or isinstance(value, str), (
                f"WHK: FINDING — the withheld family's witness carries a numeric "
                f"operand {operand!r}"
            )


# ---------------------------------------------------------------------------
# The sparse-tree proof: the skip helper raises the exact reason
# ---------------------------------------------------------------------------


def test_a0_suite_skips_exactly_on_sparse_tree(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    missing = tmp_path / "state_bundle.json"
    assert not missing.exists()
    monkeypatch.setattr(sys.modules[__name__], "_state_bundle_path", lambda: missing)
    with pytest.raises(pytest.skip.Exception) as caught:
        _skip_unless_real_bundles()
    assert caught.value.msg == BUNDLE_ABSENT, (
        f"the sparse-tree skip reason is {caught.value.msg!r}, not {BUNDLE_ABSENT!r}"
    )
    assert caught.value.msg == checker.BUNDLE_ABSENT_MESSAGE, (
        "the harness and the A0-0 checker must name the absent bundles identically"
    )
