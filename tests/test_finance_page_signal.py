"""Page signal: admission writes each falsifier onto the slice with that slice_id.

The two rows live in tests/fixtures/finance_case_signal/synthesis_v0.json.
Nothing here reads research/finance. compose_finance_projection stays empty.
"""

from __future__ import annotations

import ast
import copy
import json
from collections.abc import Iterator, Mapping, MutableMapping
from pathlib import Path
from typing import Any

import jsonschema
import pytest

import engine.sector_intelligence.finance_case_signal as finance_case_signal
import engine.sector_intelligence.finance_page_signal as finance_page_signal
from engine.sector_intelligence.finance_page_signal import (
    SynthesisAdmissionRefusal,
    apply_page_signal,
)
from engine.sector_intelligence.finance_projection import compose_finance_projection
from tests.test_finance_intelligence_projection import (
    _default_8slice_inputs,
    _knowledge_cutoff,
    _today,
)


_FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "finance_case_signal"
    / "synthesis_v0.json"
)
_SCHEMA = (
    Path(__file__).resolve().parents[1]
    / "contracts"
    / "sector_intelligence"
    / "finance_intelligence_read_model.v1.schema.json"
)
def _document() -> dict:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def _row(canonical_case_id: str) -> dict:
    return next(
        row for row in _document()["cases"] if row["canonical_case_id"] == canonical_case_id
    )


def _falsifier_validator() -> jsonschema.Draft202012Validator:
    schema = json.loads(_SCHEMA.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(schema["$defs"]["falsifier"])


def _slice(slice_id: str, falsifier_id: str | None) -> dict:
    falsifiers = []
    ids: list[str] = []
    if falsifier_id is not None:
        falsifiers.append(
            {
                "falsifier_id": falsifier_id,
                "statement": "Previous statement.",
                "window": "2020-01-01",
                "state": "WATCHING",
            }
        )
        ids.append(falsifier_id)
    return {
        "slice_id": slice_id,
        "falsifiers": falsifiers,
        "rerating": {"falsifier_ids": ids},
    }


def _page() -> dict:
    return {
        "slices": [
            _slice("card_networks", "sentinel-card"),
            _slice("exchanges_trading_venues", None),
            _slice("custody_asset_servicing", "kept-id"),
        ]
    }


def _ids(page: dict) -> dict[str, list[str]]:
    return {
        sl["slice_id"]: [item["falsifier_id"] for item in sl["falsifiers"]]
        for sl in page["slices"]
    }


def test_admitted_row_lands_on_named_slice() -> None:
    case = _document()
    alpha = _row("syn-fin-case-alpha")
    beta = _row("syn-fin-case-beta")
    page = _page()
    apply_page_signal(case, page)
    by_id = {sl["slice_id"]: sl for sl in page["slices"]}
    card = by_id["card_networks"]
    placed = card["falsifiers"]
    assert len(placed) == 1
    falsifier = placed[0]
    assert falsifier["state"] == "NOT_YET_EVALUABLE"
    assert falsifier["falsifier_id"] == alpha["canonical_case_id"]
    assert falsifier["statement"] == alpha["primary_limit"]
    assert falsifier["window"] == alpha["anchor_date"]
    assert card["rerating"]["falsifier_ids"] == [falsifier["falsifier_id"]]
    _falsifier_validator().validate(falsifier)
    venue = by_id["exchanges_trading_venues"]
    assert venue["falsifiers"][0]["falsifier_id"] == beta["canonical_case_id"]
    assert venue["rerating"]["falsifier_ids"] == [beta["canonical_case_id"]]
    assert venue["falsifiers"][0]["state"] == "NOT_YET_EVALUABLE"
    kept = by_id["custody_asset_servicing"]
    assert [item["falsifier_id"] for item in kept["falsifiers"]] == ["kept-id"]
    assert kept["rerating"]["falsifier_ids"] == ["kept-id"]
    assert "WATCHING" not in {item["state"] for item in placed}


def test_measured_count_blocks_admission() -> None:
    case = _document()
    case["formal_causal_outcomes_measured"] = 1
    page = _page()
    before = _ids(page)
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        apply_page_signal(case, page)
    assert str(caught.value) == "formal_causal_outcomes_measured"
    assert _ids(page) == before
    flat = [item for ids in _ids(page).values() for item in ids]
    assert "syn-fin-case-alpha" not in flat
    assert "syn-fin-case-beta" not in flat


def test_prospective_validation_blocks_admission() -> None:
    case = _document()
    case["prospective_validation_started"] = True
    page = _page()
    before = _ids(page)
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        apply_page_signal(case, page)
    assert str(caught.value) == "prospective_validation_started"
    assert _ids(page) == before


def test_row_with_measured_outcome_blocks_admission() -> None:
    case = _document()
    assert case["formal_causal_outcomes_measured"] == 0
    case["cases"][0]["formal_causal_outcome"] = "MEASURED"
    page = _page()
    before = _ids(page)
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        apply_page_signal(case, page)
    assert str(caught.value) == "row_outcome_not_unmeasured"
    assert _ids(page) == before


def test_page_without_slices_is_refused() -> None:
    page: dict = {}
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        apply_page_signal(_document(), page)
    assert str(caught.value) == "no_slices"
    assert page == {}


def test_row_naming_an_absent_slice_writes_nothing() -> None:
    beta = _row("syn-fin-case-beta")
    assert beta["slice_id"] == "exchanges_trading_venues"
    page = {"slices": [_slice("card_networks", "sentinel-card")]}
    before = _ids(page)
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        apply_page_signal(_document(), page)
    assert str(caught.value) == "slice_absent"
    assert _ids(page) == before
    assert page["slices"][0]["rerating"]["falsifier_ids"] == ["sentinel-card"]


def test_descriptive_measured_stays_not_yet_evaluable() -> None:
    alpha = _row("syn-fin-case-alpha")
    assert alpha["descriptive_evidence_state"] == "MARKET_AND_VALUATION_MEASURED"
    assert "MEASURED" in alpha["descriptive_evidence_state"]
    page = _page()
    apply_page_signal(_document(), page)
    card = next(sl for sl in page["slices"] if sl["slice_id"] == "card_networks")
    assert card["falsifiers"][0]["state"] == "NOT_YET_EVALUABLE"
    assert card["falsifiers"][0]["falsifier_id"] == alpha["canonical_case_id"]


def test_compose_keeps_empty_falsifiers() -> None:
    document = compose_finance_projection(
        _default_8slice_inputs(),
        generated_at=_today(),
        knowledge_cutoff=_knowledge_cutoff(),
    )
    assert document["slices"]
    for sl in document["slices"]:
        assert sl["falsifiers"] == []
        assert sl["rerating"]["falsifier_ids"] == []


def _falsifier_writer_names(module: object) -> list[str]:
    """Public functions of ``module`` that write falsifiers.

    A function counts if it names ``falsifiers``, holds the string
    ``"falsifiers"``, or names the placement helper ``_attach_falsifiers``.
    """
    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    return [
        node.name
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and not node.name.startswith("_")
        and any(
            (
                isinstance(child, ast.Name)
                and child.id in ("falsifiers", "_attach_falsifiers")
            )
            or (isinstance(child, ast.Constant) and child.value == "falsifiers")
            for child in ast.walk(node)
        )
    ]


def test_attach_falsifiers_is_not_a_public_placement_path() -> None:
    """Falsifiers reach a page only through apply_page_signal.

    The placement helper is module-private in finance_case_signal and is not
    re-exported by finance_page_signal. Across both modules,
    ``apply_page_signal`` is the only public function that writes the
    ``falsifiers`` key or calls the helper; ``project_falsifier`` projects
    one row and places nothing.
    """
    assert not hasattr(finance_case_signal, "attach_falsifiers")
    assert hasattr(finance_case_signal, "_attach_falsifiers")
    assert not hasattr(finance_page_signal, "attach_falsifiers")
    assert _falsifier_writer_names(finance_page_signal) == ["apply_page_signal"]
    assert _falsifier_writer_names(finance_case_signal) == []


@pytest.mark.parametrize(
    "slices",
    [{"card_networks": {"falsifiers": []}}, "card_networks"],
    ids=["dict", "string"],
)
def test_wrong_typed_slices_is_refused_with_no_slices(slices) -> None:
    """A non-list page["slices"], not only a missing key, is refused as "no_slices".

    The page object is left untouched: refusal happens before any placement.
    """
    page = {"slices": slices}
    before = copy.deepcopy(page)
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        apply_page_signal(_document(), page)
    assert str(caught.value) == "no_slices"
    assert page == before


@pytest.mark.parametrize(
    "shape",
    ["missing", "empty_list", "string"],
    ids=["missing", "empty_list", "string"],
)
def test_bad_cases_value_is_refused_with_no_rows(shape) -> None:
    """admit_synthesis alone refuses a missing, empty or non-list "cases" with "no_rows".

    apply_page_signal delegates to admit_synthesis, so a missing, empty or
    non-list ``cases`` is still refused with the exact code, page untouched.
    """
    case = _document()
    if shape == "missing":
        del case["cases"]
    elif shape == "empty_list":
        case["cases"] = []
    else:
        case["cases"] = "x"
    page = _page()
    before = _ids(page)
    with pytest.raises(SynthesisAdmissionRefusal) as caught:
        apply_page_signal(case, page)
    assert str(caught.value) == "no_rows"
    assert _ids(page) == before


class _TwoReadDocument(Mapping[str, Any]):
    """Case document whose ``"cases"`` answer changes on a second read.

    The first read returns the admitted rows; every later read returns a
    different list. Any routing that re-reads the raw document after
    admission would place the second list's rows against the first list's
    falsifiers.
    """

    def __init__(self, first: list[dict[str, Any]], later: list[dict[str, Any]]) -> None:
        self._lists = [list(first), list(later)]
        self.cases_reads = 0
        self._top: dict[str, Any] = {
            "formal_causal_outcomes_measured": 0,
            "prospective_validation_started": False,
            "cases": self._lists[0],
        }

    def __getitem__(self, key: str) -> Any:
        if key == "cases":
            index = min(self.cases_reads, len(self._lists) - 1)
            self.cases_reads += 1
            return self._lists[index]
        return self._top[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._top)

    def __len__(self) -> int:
        return len(self._top)


def test_routing_reads_only_the_admitted_rows() -> None:
    """apply_page_signal routes the rows admission captured, never a re-read.

    Admission reads ``document["cases"]`` once. This document hands a
    different list to any later read: the second list swaps the beta row
    for a gamma row on ``custody_asset_servicing``. Routing that re-reads
    the document would attach beta's falsifier to gamma's slice and
    clobber the kept falsifier there. The admitted-pairs path places the
    falsifiers of the admitted rows only, so beta lands on
    ``exchanges_trading_venues`` and custody is left as it was.
    """
    first = copy.deepcopy(_document()["cases"])
    gamma = copy.deepcopy(first[1])
    gamma["canonical_case_id"] = "syn-fin-case-gamma"
    gamma["slice_id"] = "custody_asset_servicing"
    document = _TwoReadDocument(first, [first[0], gamma])
    page = _page()
    apply_page_signal(document, page)
    assert document.cases_reads == 1, document.cases_reads
    by_id = {sl["slice_id"]: sl for sl in page["slices"]}
    venue = by_id["exchanges_trading_venues"]
    assert [item["falsifier_id"] for item in venue["falsifiers"]] == ["syn-fin-case-beta"]
    assert venue["rerating"]["falsifier_ids"] == ["syn-fin-case-beta"]
    kept = by_id["custody_asset_servicing"]
    assert [item["falsifier_id"] for item in kept["falsifiers"]] == ["kept-id"]
    assert kept["rerating"]["falsifier_ids"] == ["kept-id"]


def test_placement_is_all_or_nothing_across_slices(monkeypatch) -> None:
    """A WATCHING refusal on the LAST grouped slice leaves every slice untouched.

    The refusal comes from the real path, not a patched-out helper: the row
    routed to the last slice in grouping order projects a falsifier whose
    state is not ``NOT_YET_EVALUABLE``, so the real :func:`_attach_falsifiers`
    refuses it with ``watching_not_emitted``. The dry pass must cover every
    grouped slice, not only the first, or an earlier slice is rewritten
    before the refusal lands. ``project_falsifier`` is patched on
    ``finance_page_signal``, the name the module calls from ``_admit_pairs``.
    """
    document = _document()
    order: list[str] = []
    for row in document["cases"]:
        if row["slice_id"] not in order:
            order.append(row["slice_id"])
    last_slice = order[-1]
    real_project = finance_case_signal.project_falsifier

    def watching_on_last_row(row):
        falsifier = real_project(row)
        if row.get("slice_id") == last_slice:
            falsifier = {**falsifier, "state": "WATCHING"}
        return falsifier

    monkeypatch.setattr(finance_page_signal, "project_falsifier", watching_on_last_row)
    page = _page()
    before = _ids(page)
    before_full = copy.deepcopy(page)
    with pytest.raises(
        finance_case_signal.FinanceCaseSignalRefusal, match="watching_not_emitted"
    ):
        apply_page_signal(document, page)
    assert _ids(page) == before
    assert page == before_full


class _RaisingReratingLookup(MutableMapping[str, Any]):
    """Slice mapping whose ``get("rerating")`` raises ``exc``.

    Every other key behaves like the underlying plain dict, so building
    the id-to-slice index succeeds; only the ``rerating`` lookup raises.
    The override is required for the KeyError param: an inherited
    ``Mapping.get`` would swallow a KeyError from ``__getitem__`` and
    return its default instead of letting it propagate.
    """

    def __init__(self, store: dict[str, Any], exc: BaseException) -> None:
        self._store = store
        self._exc = exc

    def get(self, key: str, default: Any = None) -> Any:
        if key == "rerating":
            raise self._exc
        return self._store.get(key, default)

    def __getitem__(self, key: str) -> Any:
        return self._store[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._store[key] = value

    def __delitem__(self, key: str) -> None:
        del self._store[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)


@pytest.mark.parametrize(
    "exc",
    [
        pytest.param(
            RuntimeError("rerating lookup exploded"), id="runtime_error"
        ),
        pytest.param(
            KeyError("rerating"), id="key_error_from_overridden_get"
        ),
    ],
)
def test_raising_rerating_lookup_leaves_both_slices_untouched(exc) -> None:
    """A caller-supplied lookup that raises leaves the page as it was.

    The document routes one falsifier to each of the two slices. The
    second slice's ``get("rerating")`` raises, so the first slice's
    falsifiers and the second slice's own placement must both stay
    unwritten: every lookup on a caller-supplied slice happens before
    the first caller-visible write. The raised exception propagates.
    """
    first = _slice("card_networks", "sentinel-card")
    second: dict[str, Any] = {
        "slice_id": "exchanges_trading_venues",
        "falsifiers": [],
        "rerating": {"falsifier_ids": []},
    }
    page = {"slices": [first, _RaisingReratingLookup(second, exc)]}
    before_first = copy.deepcopy(first)
    before_second = copy.deepcopy(second)
    with pytest.raises(type(exc)) as caught:
        apply_page_signal(_document(), page)
    assert caught.value is exc
    assert first == before_first
    assert second == before_second


class _RaisingClassRerating(MutableMapping):
    """A MutableMapping whose ``__class__`` raises RuntimeError on access.

    typing.MutableMapping's instance check is a ``_SpecialGenericAlias``
    that consults ``type(obj)`` and bypasses the Python ``__class__``
    attribute, so ``isinstance`` returns True here without raising.
    A plain ``isinstance`` against a type it is not (``dict``, ``int``) reads
    ``obj.__class__`` with no abc frame; a ``collections.abc`` ``ABCMeta`` check also
    raises under it. Implemented as a MutableMapping subclass so the
    rerating write at the end of ``_attach_falsifiers`` runs at HEAD
    when ``isinstance`` passes: the all-or-nothing assertion can then
    require the rerating falsifier ids to actually be written.
    ``==`` returns a bool against a plain dict and raises only against a
    hostile ``other``; a deepcopy snapshot is one, so tests read ``_store``.
    """

    def __init__(self) -> None:
        self._store: dict[str, Any] = {}

    @property
    def __class__(self):
        raise RuntimeError("hostile __class__")

    def __getitem__(self, key: str) -> Any:
        return self._store[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._store[key] = value

    def __delitem__(self, key: str) -> None:
        del self._store[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._store)

    def __len__(self) -> int:
        return len(self._store)


def test_raising_class_lookup_leaves_both_slices_consistent() -> None:
    """A rerating whose ``__class__`` raises RuntimeError keeps slices consistent.

    The second slice's ``rerating`` is a MutableMapping subclass whose
    ``__class__`` access raises. The all-or-nothing law: after the
    call, either it raised and BOTH slices equal their pre-call deep
    copies, or it returned and BOTH slices carry their falsifier
    writes: ``falsifiers`` ids and ``rerating["falsifier_ids"]`` exactly equal
    that row's canonical id, on the caller's own rerating. A partial state — slice 1
    written, slice 2 not — fails with a message naming the partial
    write. The subclass decision is measured: without subclassing
    ``MutableMapping`` the HEAD branch skips the rerating write and
    slice 2 silently loses its ``falsifier_ids``, so the assertion
    could not distinguish "returned with both writes" from "returned
    with one write"; subclassing lets the all-or-nothing law name the
    missing rerating write explicitly. The raised branch checks the
    hostile rerating by identity and backing store, because comparing
    it with ``==`` raises the same RuntimeError.
    """
    first = _slice("card_networks", "sentinel-card")
    hostile = _RaisingClassRerating()
    hostile["falsifier_ids"] = []
    second: dict[str, Any] = {
        "slice_id": "exchanges_trading_venues",
        "falsifiers": [],
        "rerating": hostile,
    }
    page = {"slices": [first, second]}
    before_first = copy.deepcopy(first)
    before_second_rest = copy.deepcopy(
        {key: value for key, value in second.items() if key != "rerating"}
    )
    before_store = copy.deepcopy(hostile._store)

    raised: BaseException | None = None
    try:
        apply_page_signal(_document(), page)
    except BaseException as exc:
        raised = exc

    if raised is not None:
        assert first == before_first, (
            f"first slice was written after raise: {first!r} != {before_first!r}"
        )
        rest = {key: value for key, value in second.items() if key != "rerating"}
        assert rest == before_second_rest, (
            f"second slice was written after raise: {rest!r} != {before_second_rest!r}"
        )
        if not (
            second.get("rerating") is hostile and hostile._store == before_store
        ):
            pytest.fail(
                f"second slice rerating was written after raise: {hostile._store!r}"
            )
        return

    alpha_ids = [_row("syn-fin-case-alpha")["canonical_case_id"]]
    beta_ids = [_row("syn-fin-case-beta")["canonical_case_id"]]
    assert [item["falsifier_id"] for item in first["falsifiers"]] == alpha_ids
    assert first["rerating"]["falsifier_ids"] == alpha_ids
    assert [item["falsifier_id"] for item in second["falsifiers"]] == beta_ids
    if not (second["rerating"] is hostile and hostile["falsifier_ids"] == beta_ids):
        pytest.fail(
            "partial write: second slice rerating is not the caller's hostile "
            f"object carrying {beta_ids!r}; its store is {hostile._store!r}"
        )


def test_neither_signal_module_reads_research_or_uses_io_primitives() -> None:
    """Neither signal module reads research/ or touches files or the network.

    Neither finance_case_signal nor finance_page_signal may import anything
    under research/, nor import builtins/io/os/pathlib/requests/socket/
    urllib, nor call open() as a name or an attribute (``builtins.open``),
    nor hold a ``research/`` path in a string other than a docstring.
    Docstrings are exempt because both module docstrings name
    research/finance to promise they never read it.
    """
    forbidden_roots = {
        "builtins",
        "io",
        "os",
        "pathlib",
        "requests",
        "socket",
        "urllib",
    }
    for module in (finance_case_signal, finance_page_signal):
        tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        offenders = {
            name for name in imported
            if name.split(".")[0] in forbidden_roots or "research" in name.split(".")
        }
        assert not offenders, (module.__name__, sorted(offenders))
        assert not [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "open"
        ], module.__name__
        assert not [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "open"
        ], (module.__name__, "attribute .open() call")
        docstrings = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(
                node,
                ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
            )
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        }
        path_constants = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and "research/" in node.value
            and id(node) not in docstrings
        ]
        assert not path_constants, (module.__name__, path_constants)
