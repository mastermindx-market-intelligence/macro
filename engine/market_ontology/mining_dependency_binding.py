"""Mining M1 consumption-side dependency binding (T01').

This module is the Mining vertical's *consumer* seam onto the GMI shared theme-research
foundation.  It deliberately owns nothing of that foundation: no kernel, no response schema,
no route, no publisher, no client framework (mandatory plan addendum §2, rulings R-MIN-00/06/21).
It provides three things the Mining suites need before the shared owner delivers the exact
profile interface:

* locally defined ``MiningResearchQuery`` / ``MiningOwnerBundle`` dataclasses that mirror the
  shared candidate's field names without importing from it (R-MIN-24);
* ``validate_delivery_inputs`` — a pure, closed delivery-input validator that always refuses
  *live* admission (real bytes, rights, private objects are incumbent-owner acts, G2–G6) while
  saying whether a synthetic case is research-usable, cross-checks the case's ``expected``
  oracle against its omission set, and owns the Mining query refusals: ``unknown_slice`` and
  ``slice_theme_mismatch`` are Mining-invented, while ``limit_out_of_range``,
  ``offset_negative``, ``expected_generation_required``, ``replay_cutoffs_required`` and
  ``generation_changed`` MIRROR the shared candidate's predicates (limit 1..100, generation
  only for a paged read, cutoffs only under ``system_replay``) so the wrapper can later
  delegate to the kernel without a behaviour change (R-MIN-06, R-MIN-24);
* ``publication_harness`` — a test-only harness whose ``client()`` returns a typed
  ``route_unbound`` refusal with zero reads for entitled and unentitled callers alike, because
  the shared POST route family exists on neither ``main`` nor the shared candidate (R-MIN-06),
  and whose ``shared_contract()`` probes the shared assertion contract lazily and degrades to a
  typed ``shared_contract_unavailable`` refusal.

Nothing here performs I/O, network access, identity minting, numerical finance or clock reads.
Every authority flag stays literal ``False`` at every layer that echoes it.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

__all__ = [
    "RESULT_KEYS",
    "SLICE_ANCHORS",
    "SHARED_ROUTE_PATHS",
    "OMISSION_REASONS",
    "OMISSION_TO_LIMITATION",
    "AUTHORITY",
    "MiningResearchRefusal",
    "MiningResearchQuery",
    "MiningOwnerBundle",
    "RouteUnbound",
    "Harness",
    "validate_query",
    "validate_delivery_inputs",
    "publication_harness",
]

# Closed result contract of ``validate_delivery_inputs`` (order is part of the contract).
RESULT_KEYS: tuple[str, ...] = ("live_admission", "research_usable", "reasons", "bindings")

# The two closed Mining definitions and the kernel-side canonical theme ids they anchor to
# (the ``theme:`` form; never the mount grammar — R-MIN-27).
SLICE_ANCHORS: dict[str, str] = {
    "mining_copper_economics": "theme:copper_steel_electrify",
    "mining_rare_earth_economics": "theme:rare_earth_critical_min",
}

# Declared by the shared owner's mount template only; absent from ``app/`` on main.
EXPECTED_KEYS = frozenset({"signed_native_blocks", "reported_only_economics"})
SHARED_ROUTE_PATHS: tuple[str, str] = (
    "/api/themes/v1/research/query",
    "/api/themes/v1/research/evidence",
)

# Closed omission vocabulary carried by the synthetic casebook fixtures -> plain-word reason.
OMISSION_REASONS: dict[str, str] = {
    "reporting_basis": "The reporting basis of the source figure is absent.",
    "issuer": "No native issuer identity is bound to the source.",
    "economics": "The source carries no economic packet; it is source-only.",
    "stream_threshold": "The contractual stream threshold balance is unknown.",
    "source_revision": "The consumed source revision changed after the derivation was bound.",
    "next_period_outlook": "The revision is a same-horizon revision, not a next-period outlook.",
    "source_rights": "The source rights disposition denies display.",
    "page_generation": "The page generation changed between request and delivery.",
}

# Frozen omission word -> T04 composition limitation code (seat ruling R-MIN-30). The two
# vocabularies are disjoint by construction; T04 consumes this table instead of inventing one.
# A signed loss is NOT an omission: the sign travels inside the retained native block (IR-02).
OMISSION_TO_LIMITATION: dict[str, str] = {
    "reporting_basis": "missing_basis",
    "issuer": "missing_issuer",
    "economics": "source_only",
    "stream_threshold": "stream_threshold_unknown",
    "source_revision": "changed_source",
    "next_period_outlook": "missing_derivation",
    "source_rights": "denied_source",
    "page_generation": "page_generation_change",
}

AUTHORITY: dict[str, bool] = {
    "can_rank": False,
    "can_gate": False,
    "can_size": False,
    "can_originate": False,
    "can_open_entry": False,
}

_LIVE_ADMISSION_REASON = (
    "Live admission is refused on main: native source bytes, source rights, private "
    "objects and the shared route are incumbent-owner acts that no synthetic case can grant."
)
_LIMIT_MIN, _LIMIT_MAX = 1, 100  # mirrors the shared candidate's _MIN_LIMIT, _MAX_LIMIT (R-MIN-24)
_SHARED_CONTRACT_MODULE = "engine.theme_graph.curation_assertion"


class MiningResearchRefusal(Exception):
    """A typed, Mining-owned refusal. ``code`` is one of the closed codes below."""

    CODES: tuple[str, ...] = (
        "unknown_slice",
        "slice_theme_mismatch",
        "limit_out_of_range",
        "offset_negative",
        "expected_generation_required",
        "replay_cutoffs_required",
        "generation_changed",
        "shared_contract_unavailable",
    )

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in self.CODES:
            raise ValueError(f"unknown refusal code {code!r}")
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class MiningResearchQuery:
    """Mirror of the shared candidate's query shape, defined locally (R-MIN-24)."""

    anchor_theme_id: str
    slice_key: str
    view: str
    time_mode: str
    source_cutoff: str | None
    recorded_cutoff: str | None
    offset: int = 0
    limit: int = 50
    expected_generation: str | None = None


@dataclass(frozen=True)
class MiningOwnerBundle:
    """Mirror of the shared candidate's owner bundle, defined locally (R-MIN-24)."""

    revision_tuple: tuple[tuple[str, str], ...]
    rights_revision: str
    assertions: tuple[Mapping[str, Any], ...] = ()
    identity_results: tuple[Mapping[str, Any], ...] = ()
    event_workspaces: tuple[Mapping[str, Any], ...] = ()
    financial_packets: tuple[Mapping[str, Any], ...] = ()
    interpretation_blocks: tuple[Mapping[str, Any], ...] = ()
    native_refs: tuple[Mapping[str, Any], ...] = ()
    omissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RouteUnbound:
    """Typed refusal returned while the shared POST route family is absent on main."""

    code: str = "route_unbound"
    read_count: int = 0
    detail: str = (
        f"The shared paths {SHARED_ROUTE_PATHS[0]} and {SHARED_ROUTE_PATHS[1]} "
        "are absent on main."
    )
    authority: Mapping[str, bool] = field(default_factory=lambda: dict(AUTHORITY))


def _is_int(value: Any) -> bool:
    # ``bool`` is a subclass of ``int``; the shared candidate's own rule rejects it.
    return isinstance(value, int) and not isinstance(value, bool)


def validate_query(query: MiningResearchQuery, *, account_generation: str | None = None) -> None:
    """Raise a typed ``MiningResearchRefusal`` for every closed Mining query defect."""

    if query.slice_key not in SLICE_ANCHORS:
        raise MiningResearchRefusal("unknown_slice", f"slice {query.slice_key!r} is not a Mining definition")
    if query.anchor_theme_id != SLICE_ANCHORS[query.slice_key]:
        raise MiningResearchRefusal(
            "slice_theme_mismatch",
            f"slice {query.slice_key!r} anchors to {SLICE_ANCHORS[query.slice_key]!r}, not {query.anchor_theme_id!r}",
        )
    if not _is_int(query.limit) or query.limit < _LIMIT_MIN or query.limit > _LIMIT_MAX:
        raise MiningResearchRefusal("limit_out_of_range", f"limit must be an int in {_LIMIT_MIN}..{_LIMIT_MAX}")
    if not _is_int(query.offset) or query.offset < 0:
        raise MiningResearchRefusal("offset_negative", "offset must be a non-negative int")
    if query.offset > 0 and query.expected_generation is None:
        raise MiningResearchRefusal("expected_generation_required", "a paged read (offset > 0) needs the expected page generation")
    if query.time_mode == "system_replay" and (query.source_cutoff is None or query.recorded_cutoff is None):
        raise MiningResearchRefusal("replay_cutoffs_required", "a system_replay read needs both the source cutoff and the recorded cutoff")
    if (
        account_generation is not None
        and query.expected_generation is not None
        and query.expected_generation != account_generation
    ):
        raise MiningResearchRefusal(
            "generation_changed",
            f"expected {query.expected_generation!r} but the account generation is {account_generation!r}",
        )


def validate_delivery_inputs(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Closed delivery-input validator: never admits live inputs, classifies research usability.

    ``inputs`` must carry exactly ``query``, ``bundle``, ``expected`` and ``account_generation``.
    The result is a closed dict with exactly ``RESULT_KEYS`` in that order.
    """

    expected_keys = {"query", "bundle", "expected", "account_generation"}
    actual_keys = set(inputs)
    if actual_keys != expected_keys:
        raise ValueError(
            f"unexpected delivery input keys: extra={sorted(actual_keys - expected_keys)} "
            f"missing={sorted(expected_keys - actual_keys)}"
        )
    query = inputs["query"]
    bundle = inputs["bundle"]
    account_generation = str(inputs["account_generation"])
    expected = inputs["expected"]
    if not isinstance(query, MiningResearchQuery) or not isinstance(bundle, MiningOwnerBundle):
        raise ValueError("query and bundle must be the locally defined Mining dataclasses")

    validate_query(query, account_generation=account_generation)

    reasons: list[str] = [_LIVE_ADMISSION_REASON]
    unknown = [o for o in bundle.omissions if o not in OMISSION_REASONS]
    if unknown:
        raise ValueError(f"unknown omission words {unknown!r}; closed set is {sorted(OMISSION_REASONS)}")
    reasons.extend(OMISSION_REASONS[o] for o in bundle.omissions)

    # A revision tuple that carries a different account generation is a page-generation change
    # and must be declared as one; an undeclared mismatch is a malformed case, not decoration.
    for pair in bundle.revision_tuple:
        if pair[0] == "account_generation" and str(pair[1]) != account_generation:
            if "page_generation" not in bundle.omissions:
                raise ValueError("revision tuple carries a different account generation without the page_generation omission")
    # The ``expected`` oracle is read, not carried: a retained signed native block and a
    # non-empty omission set contradict each other (a signed loss is a block, not an omission).
    if not isinstance(expected, Mapping) or set(expected) != EXPECTED_KEYS:
        raise ValueError(f"expected must carry exactly {sorted(EXPECTED_KEYS)}")
    signed_blocks = list(expected["signed_native_blocks"])
    reported_only = list(expected["reported_only_economics"])
    if bool(signed_blocks) == bool(bundle.omissions):
        raise ValueError(
            "expected contradicts omissions: a retained signed native block requires an empty "
            "omission set, and an omission requires an empty signed_native_blocks list"
        )
    if bool(reported_only) == bool(signed_blocks):
        raise ValueError("expected must carry exactly one of signed_native_blocks or reported_only_economics")

    bindings = {
        "slice_key": query.slice_key,
        "anchor_theme_id": query.anchor_theme_id,
        "account_generation": account_generation,
        "revision_tuple": [list(pair) for pair in bundle.revision_tuple],
        "rights_revision": bundle.rights_revision,
        "shared_route": "absent_on_main",
        "shared_contract": "unprobed",
        "authority": dict(AUTHORITY),
    }
    result = {
        "live_admission": "refused",
        "research_usable": len(bundle.omissions) == 0,
        "reasons": reasons,
        "bindings": bindings,
    }
    assert tuple(result) == RESULT_KEYS
    return result


class Harness:
    """Test-only publication harness. Performs no network, file or clock I/O."""

    def __init__(self) -> None:
        self.read_count = 0

    def client(self, *, entitled: bool = False) -> RouteUnbound:
        """Return the typed ``route_unbound`` refusal; identical for every caller.

        The refusal reports the harness's OWN read counter (0: the harness never reads), so a
        stub that answered a read would be caught by the counter, not masked by a constant.
        """

        del entitled  # entitlement cannot conjure a route that does not exist on main
        return RouteUnbound(read_count=self.read_count)

    def shared_contract(self) -> Callable[..., Any]:
        """Lazily probe the shared assertion contract; degrade to a typed refusal when absent."""

        # A string import, not a static ``from engine.theme_graph import ...``: the shared
        # module is absent on main until #7870 lands, and the first-party import checker
        # rightly treats a static import of an absent name as an ImportError waiting to be
        # swallowed. ``import_module`` raises ImportError for an absent module AND for a module
        # that resolves and then fails to import, so the degrade is exception-safe (R-MIN-26).
        try:
            shared = importlib.import_module(_SHARED_CONTRACT_MODULE)
        except ImportError as exc:
            raise MiningResearchRefusal(
                "shared_contract_unavailable",
                f"{_SHARED_CONTRACT_MODULE} is not importable on this checkout ({exc.__class__.__name__}); "
                "the shared owner has not delivered it to main",
            ) from None
        if not callable(getattr(shared, "validate_assertion", None)) or not callable(
            getattr(shared, "curation_revision", None)
        ):
            raise MiningResearchRefusal(
                "shared_contract_unavailable",
                f"{_SHARED_CONTRACT_MODULE} does not expose both validate_assertion and curation_revision",
            )
        return shared.validate_assertion


def publication_harness() -> Harness:
    return Harness()
