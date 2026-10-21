"""Company-slot registration adapter for the communications research composer.

The adapter reports whether that composer can register on the shared research
shell. It does not move measure algebra into the shell, does not change
``binding_state``, and does not register a mount. Shell modules are imported
lazily, by string literal, and are absent on this base. This module is not a
registry, store, route, publisher, or rights plane.
"""
from __future__ import annotations

import importlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, NoReturn

SHARED_CONTRACT_MODULE = "engine.theme_graph.curation_assertion"
SHARED_SHELL_MODULE = "engine.market_ontology.theme_research_binding"
SHARED_REGISTRY_MODULE = "engine.market_ontology.theme_research_registry"

SCHEMA_ID = "communications_business_research.v1"
# Shell field only. No evidence contract is shipped and no file is read.
EVIDENCE_SCHEMA_ID = "communications_business_research.evidence.unregistered"
DEFINITION_VERSION = "unbound"
VIEW_KEYS = ("four_company_claims",)
COMPANY_SLOTS = ("meta", "alphabet", "trade_desk", "magnite")
ENTRY_KIND = "company_profile"
VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE = "vertical_registration_held:company_profile"

# VerticalRegistration fields on #7870 eee23a0e, theme_research_registry.py:118-131.
# Lines 118-127 are the names Technology's tuple omits in part; titles follow
# through line 131 and are required constructor arguments.
_VERTICAL_REGISTRATION_FIELDS: tuple[str, ...] = (
    "anchor_theme_id",
    "slice_keys",
    "view_keys",
    "schema_id",
    "evidence_schema_id",
    "definition_version",
    "compose",
    "select_evidence",
    "load_bundle",
    "build_query",
    "title_en",
    "title_zh",
    "note_en",
    "note_zh",
)


class CommunicationsRegistrationRefusal(ValueError):
    """Adapter refusal. ``str(exc)`` is exactly ``code``."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _refuse(code: str) -> NoReturn:
    raise CommunicationsRegistrationRefusal(code)


def _load_shared_contract():
    """Presence probe. Does not call validate_assertion or curation_revision."""
    try:
        module = importlib.import_module("engine.theme_graph.curation_assertion")
    except ModuleNotFoundError as exc:
        if exc.name == SHARED_CONTRACT_MODULE:
            return None
        raise
    if not callable(getattr(module, "validate_assertion", None)):
        return None
    if not callable(getattr(module, "curation_revision", None)):
        return None
    return module


def _load_binding():
    """Presence probe for the three shell names this vertical consumes."""
    try:
        module = importlib.import_module("engine.market_ontology.theme_research_binding")
    except ModuleNotFoundError as exc:
        if exc.name == SHARED_SHELL_MODULE:
            return None
        raise
    if not isinstance(getattr(module, "ResearchRefusal", None), type):
        return None
    if not isinstance(getattr(module, "BundleUnavailable", None), type):
        return None
    if not callable(getattr(module, "generation_fingerprint", None)):
        return None
    return module


def _load_registry():
    try:
        module = importlib.import_module("engine.market_ontology.theme_research_registry")
    except ModuleNotFoundError as exc:
        if exc.name == SHARED_REGISTRY_MODULE:
            return None
        raise
    if not isinstance(getattr(module, "VerticalRegistration", None), type):
        return None
    return module


def shared_contract():
    """Return the curation module, or refuse when the probe is unavailable."""
    module = _load_shared_contract()
    if module is None:
        _refuse("shared_contract_unavailable")
    return module


def _raise_research_refusal(code: str) -> NoReturn:
    binding = _load_binding()
    if binding is None:
        _refuse(code)
    raise binding.ResearchRefusal(code)


@dataclass(frozen=True, slots=True)
class CommunicationsResearchQuery:
    """Closed query. Cutoff and theme fields are not accepted."""


def build_query(**fields) -> CommunicationsResearchQuery:
    """Return this vertical's query. An unknown field is a research refusal."""
    if fields:
        _raise_research_refusal("query_field_rejected")
    return CommunicationsResearchQuery()


def compose(query: Any, bundle: Any) -> Mapping[str, Any]:
    """Not a registered composer. The company-slot hold fires first."""
    del query, bundle
    _refuse(VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE)


def select_evidence(query: Any, bundle: Any, assertion_ref: Any) -> Mapping[str, Any]:
    """Does not pass a claim into the curation validator."""
    del query, bundle, assertion_ref
    _refuse(VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE)


def load_bundle(query: Any, *, rights_snapshot: Mapping[str, str] | None = None) -> Any:
    """No owner bundle exists. A present shell raises its BundleUnavailable."""
    del query, rights_snapshot
    binding = _load_binding()
    if binding is None:
        _refuse("shared_shell_unavailable")
    unavailable = getattr(binding, "BundleUnavailable", None)
    if not isinstance(unavailable, type) or not issubclass(unavailable, Exception):
        _refuse("shared_shell_unavailable")
    raise unavailable("communications_owner_bundle_absent")


@dataclass(frozen=True, slots=True)
class CommunicationsRegistrationFacts:
    """Company-slot facts. ``anchor_theme_id`` is None and ``slice_keys`` is empty."""

    entry_kind: str
    company_slots: tuple[str, ...]
    anchor_theme_id: str | None
    slice_keys: tuple[str, ...]
    view_keys: tuple[str, ...]
    schema_id: str
    evidence_schema_id: str
    definition_version: str
    compose: Callable[..., Any]
    select_evidence: Callable[..., Any]
    load_bundle: Callable[..., Any]
    build_query: Callable[..., Any]
    title_en: str
    title_zh: str
    note_en: str
    note_zh: str


COMMUNICATIONS_REGISTRATION_FACTS = CommunicationsRegistrationFacts(
    entry_kind=ENTRY_KIND,
    company_slots=COMPANY_SLOTS,
    anchor_theme_id=None,
    slice_keys=(),
    view_keys=VIEW_KEYS,
    schema_id=SCHEMA_ID,
    evidence_schema_id=EVIDENCE_SCHEMA_ID,
    definition_version=DEFINITION_VERSION,
    compose=compose,
    select_evidence=select_evidence,
    load_bundle=load_bundle,
    build_query=build_query,
    title_en="Communications unregistered domain-projection candidate",
    title_zh="通信未注册领域投影候选",
    note_en=(
        "Draft domain projection. Not an accepted shared query or evidence envelope. "
        "Nothing here ranks, gates, sizes or times anything."
    ),
    note_zh="领域投影草稿，不是已接受的共享查询或证据封套。此处内容不构成排序、准入、仓位或时机判断。",
)


def _theme_registrable(facts: CommunicationsRegistrationFacts) -> bool:
    return isinstance(facts.anchor_theme_id, str) and bool(facts.slice_keys)


def registration_entry_or_refusal(
    facts: CommunicationsRegistrationFacts = COMMUNICATIONS_REGISTRATION_FACTS,
) -> Any:
    """Return a shell entry, or a typed refusal before construction.

    Absent registry: ``shared_shell_unavailable``. Present registry and
    company-slot facts: ``vertical_registration_held:company_profile``, and
    the constructor is not called. Theme-registrable facts are constructed
    with the full field list. A constructor ``TypeError`` propagates.
    """
    registry = _load_registry()
    if registry is None:
        _refuse("shared_shell_unavailable")
    if not _theme_registrable(facts):
        _refuse(VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE)
    kwargs = {name: getattr(facts, name) for name in _VERTICAL_REGISTRATION_FIELDS}
    try:
        return registry.VerticalRegistration(**kwargs)
    except TypeError:
        raise
    except Exception as exc:
        _refuse("vertical_registration_refused:" + type(exc).__name__)


__all__ = (
    "SHARED_CONTRACT_MODULE",
    "SHARED_SHELL_MODULE",
    "SHARED_REGISTRY_MODULE",
    "SCHEMA_ID",
    "EVIDENCE_SCHEMA_ID",
    "DEFINITION_VERSION",
    "VIEW_KEYS",
    "COMPANY_SLOTS",
    "ENTRY_KIND",
    "VERTICAL_REGISTRATION_HELD_COMPANY_PROFILE",
    "CommunicationsRegistrationRefusal",
    "CommunicationsRegistrationFacts",
    "CommunicationsResearchQuery",
    "COMMUNICATIONS_REGISTRATION_FACTS",
    "shared_contract",
    "build_query",
    "compose",
    "select_evidence",
    "load_bundle",
    "registration_entry_or_refusal",
)
