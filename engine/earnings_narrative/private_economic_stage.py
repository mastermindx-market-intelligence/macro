"""Stage private PG economic evidence into the existing off-repo wire tree.

The public Earnings Wire builder owns public bytes. This module only adds
role-bounded native members under an already-staged private directory, after
legacy records and context exist and before ``prepare_private_publication``.
It does not write the object store and it does not own the current pointer.

Contracts consumed from the private publication owner (not redefined here):
``earnings.tier_payload/v2`` and ``earnings.private_manifest/v2``. The verified
prior is ``load_economic_closure``. Authority stays at the research-display
ceiling: the six interpretation flags are literal false.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path
import re
import stat
from typing import Any

from engine.company_intelligence import pg_profile
from engine.company_intelligence.pg_profile import PgPreparationRefused, prepare_pg_workspace
from engine.earnings_narrative import economic_interpretation
from engine.earnings_narrative.context_packets import canonical_json_bytes
from engine.earnings_narrative.private_publication import (
    DOSSIER_PAGE,
    MANIFEST_SCHEMA_V2,
    MAX_NATIVE_CHAIN,
    NATIVE_STAGE_SCHEMA,
    RECORD_SCHEMA_V2,
    EarningsPrivatePublicationError,
    load_economic_closure,
    load_private_manifest,
    load_private_predecessor,
    validate_slug,
)


AUTHORITY_CEILING = "research_display_only"
DOSSIER_SLUG = "pg-economic-dossier"
_REPO = Path(__file__).resolve().parents[2]
_CLOCK_RE = re.compile(r"\A[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\Z")
_GENERATION_ID_RE = re.compile(r"\A[a-f0-9]{24}\Z")
_PRIVATE_METRICS = frozenset(pg_profile.PG_METRIC_KEYS)


class PrivateEconomicStageError(ValueError):
    """The private economic stage refused to write."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


class PriorClosureUnavailable(PrivateEconomicStageError):
    """An installed private generation could not be verified. Do not mint a root."""

    def __init__(self) -> None:
        super().__init__("prior_unverified")


@dataclass(frozen=True)
class VerifiedPrior:
    """One verified installed generation. ``closure`` is None for a v1 pointer."""

    closure: Mapping[str, Any] | None
    previous_manifest: Mapping[str, Any] | None
    native_source_cutoff: str | None
    schema: str


def load_verified_prior(store: Any) -> VerifiedPrior | None:
    """Read the installed generation through the private publication owner.

    ``None`` means the pointer is absent (a first launch). A pointer that cannot
    be verified raises :class:`PriorClosureUnavailable` and writes nothing.
    """
    try:
        manifest = load_private_manifest(store)
    except EarningsPrivatePublicationError as exc:
        if "pointer is unavailable" in str(exc):
            return None
        raise PriorClosureUnavailable() from exc
    try:
        predecessor = load_private_predecessor(store)
    except EarningsPrivatePublicationError as exc:
        raise PriorClosureUnavailable() from exc
    schema = manifest.get("schema")
    if schema != MANIFEST_SCHEMA_V2:
        return VerifiedPrior(
            closure=None,
            previous_manifest=predecessor,
            native_source_cutoff=None,
            schema=schema if type(schema) is str else "",
        )
    native = manifest.get("native")
    slots = native.get("economic_slots") if type(native) is dict else None
    if type(slots) is not dict:
        raise PriorClosureUnavailable()
    company_id = pg_profile.pg_issuer().company_id
    slot = slots.get(company_id)
    if slot is None:
        return VerifiedPrior(None, predecessor, manifest.get("native_source_cutoff"), MANIFEST_SCHEMA_V2)
    slug = slot.get("slug") if type(slot) is dict else None
    if type(slug) is not str:
        raise PriorClosureUnavailable()
    try:
        closure = load_economic_closure(store, manifest=manifest, slug=slug)
    except EarningsPrivatePublicationError as exc:
        raise PriorClosureUnavailable() from exc
    cutoff = manifest.get("native_source_cutoff")
    return VerifiedPrior(
        closure=closure,
        previous_manifest=predecessor,
        native_source_cutoff=cutoff if type(cutoff) is str else None,
        schema=MANIFEST_SCHEMA_V2,
    )


def assert_public_workspace_admission(workspace: Mapping[str, Any]) -> None:
    """Refuse a private PG economic workspace at a public publication boundary.

    The decision is the workspace's metric ids and rights profile. A caller
    flag cannot admit it. A public Apple or homebuilder workspace, and a
    public-rights PG teaser that does not carry the private metric profile,
    pass.
    """
    if type(workspace) is not dict and not isinstance(workspace, Mapping):
        raise PrivateEconomicStageError("malformed_workspace")
    if _carries_private_profile(workspace, 0):
        raise PrivateEconomicStageError("private_workspace_refused")


def augment_private_stage(
    stage_dir: str | Path,
    *,
    acquisition: Mapping[str, Any] | None,
    prior_closure: VerifiedPrior | Mapping[str, Any] | None,
    observed_at: str | None,
    previous_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Derive or reuse the PG native record inside an existing off-repo stage.

    Writes only ``native/`` members and one dossier record. Performs no object
    store write and does not move the current pointer.
    """
    root = _stage_root(stage_dir)
    closure = _closure_of(prior_closure)
    predecessor = _predecessor_of(prior_closure, previous_manifest)
    floor = prior_closure.native_source_cutoff if isinstance(prior_closure, VerifiedPrior) else None

    if _withdrawn(acquisition):
        if closure is None:
            raise PrivateEconomicStageError("withdrawal_without_prior")
        return _write_stage(
            root,
            chain=_chain_items(closure),
            currentness=_stored_currentness(closure),
            facts=_stored_facts(closure),
            fiscal_scope=_stored_scope(closure),
            slug=_stored_slug(closure),
            predecessor=predecessor,
            floor=floor,
            observed_at=observed_at,
        )
    if _malformed_marker(acquisition):
        if closure is None:
            raise PrivateEconomicStageError("preparation_refused")
        return _write_stage(
            root,
            chain=_chain_items(closure),
            currentness={"state": "newer_source_pending", "source_clock": _require_clock(observed_at)},
            facts=_stored_facts(closure),
            fiscal_scope=_stored_scope(closure),
            slug=_stored_slug(closure),
            predecessor=predecessor,
            floor=floor,
            observed_at=observed_at,
        )
    if acquisition is None:
        if closure is None:
            return {"wrote": False, "schema": RECORD_SCHEMA_V2}
        return _write_stage(
            root,
            chain=_chain_items(closure),
            currentness=_stored_currentness(closure),
            facts=_stored_facts(closure),
            fiscal_scope=_stored_scope(closure),
            slug=_stored_slug(closure),
            predecessor=predecessor,
            floor=floor,
            observed_at=observed_at,
        )

    try:
        prepared = prepare_pg_workspace(
            acquisition,
            prior=_prepare_prior(closure),
            observed_at=_require_clock(observed_at),
        )
    except PgPreparationRefused as exc:
        if closure is None:
            raise PrivateEconomicStageError("preparation_refused") from exc
        return _write_stage(
            root,
            chain=_chain_items(closure),
            currentness={"state": "newer_source_pending", "source_clock": _require_clock(observed_at)},
            facts=_stored_facts(closure),
            fiscal_scope=_stored_scope(closure),
            slug=_stored_slug(closure),
            predecessor=predecessor,
            floor=floor,
            observed_at=observed_at,
        )

    prepared_document = prepared["document_metadata"]
    stored_document_id = (
        closure["chain"][-1]["document"]["document_id"] if closure is not None else None
    )
    same_document = (
        closure is not None
        and isinstance(stored_document_id, str)
        and isinstance(prepared_document["document_id"], str)
        and _plain_str(stored_document_id) == _plain_str(prepared_document["document_id"])
    )
    if same_document:
        chain = _chain_items(closure)
        facts = _stored_facts(closure)
        slug = _stored_slug(closure)
    elif closure is not None:
        chain = _chain_items(closure)
        chain.append(_prepared_item(prepared))
        facts = None
        slug = _stored_slug(closure)
    else:
        chain = [_prepared_item(prepared)]
        facts = None
        slug = DOSSIER_SLUG
    if len(chain) > MAX_NATIVE_CHAIN:
        raise PrivateEconomicStageError("over_limit")
    scope = prepared["currentness_context"]["fiscal_scope"]
    return _write_stage(
        root,
        chain=chain,
        currentness=prepared["currentness_context"]["currentness"],
        facts=facts,
        fiscal_scope=tuple(scope),
        slug=slug,
        predecessor=predecessor,
        floor=floor,
        observed_at=observed_at,
    )


def _plain_str(value: str) -> str:
    """An exact ``str`` copy, so a hostile ``str`` subclass cannot fake equality.

    ``str.__str__`` is the base implementation reached without the MRO: a
    subclass overriding ``__eq__``/``__hash__``/``__str__`` still yields a plain
    ``str`` whose identity, hash and equality are the genuine ones. Behaviour for
    a plain ``str`` is unchanged (``str.__str__`` returns the same object).
    """
    copy = str.__str__(value)
    if type(copy) is not str:  # defensive: never trust an overridden copy path
        copy = "".join(copy)
    return copy


def _carries_private_profile(value: Any, depth: int) -> bool:
    """True when private PG metric ids or the private rights profile are present."""
    if depth > 32:
        raise PrivateEconomicStageError("over_limit")
    if isinstance(value, Mapping):
        metric = value.get("metric")
        if isinstance(metric, str) and _plain_str(metric) in _PRIVATE_METRICS:
            return True
        rights_profile = value.get("rights_profile")
        if isinstance(rights_profile, str) and (
            _plain_str(rights_profile) == pg_profile.PG_PRIVATE_RIGHTS_PROFILE
        ):
            return True
        return any(_carries_private_profile(item, depth + 1) for item in value.values())
    if isinstance(value, (str, bytes, bytearray)):
        return False
    if isinstance(value, Sequence):
        return any(_carries_private_profile(item, depth + 1) for item in value)
    return False


def _closure_of(prior: VerifiedPrior | Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if prior is None:
        return None
    if isinstance(prior, VerifiedPrior):
        return prior.closure
    if type(prior) is dict and "chain" in prior and "record" in prior:
        return prior
    raise PrivateEconomicStageError("malformed_prior")


def _predecessor_of(
    prior: VerifiedPrior | Mapping[str, Any] | None,
    explicit: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if explicit is not None:
        if type(explicit) is not dict:
            raise PrivateEconomicStageError("malformed_prior")
        return dict(explicit)
    if isinstance(prior, VerifiedPrior) and prior.previous_manifest is not None:
        return dict(prior.previous_manifest)
    return None


def _withdrawn(acquisition: Mapping[str, Any] | None) -> bool:
    return type(acquisition) is dict and acquisition.get("withdrawn") is True


def _malformed_marker(acquisition: Mapping[str, Any] | None) -> bool:
    if type(acquisition) is not dict:
        return False
    outcome = acquisition.get("outcome")
    return type(outcome) is str and _plain_str(outcome) == "malformed"


def _require_clock(value: str | None) -> str:
    if type(value) is not str or _CLOCK_RE.fullmatch(value) is None:
        raise PrivateEconomicStageError("malformed_observation_clock")
    return value


def _prepare_prior(closure: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if closure is None:
        return None
    newest = closure["chain"][-1]
    return {"workspace": newest["workspace"], "document_metadata": newest["document"]}


def _chain_items(closure: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {"workspace": item["workspace"], "document": item["document"], "text": item["text"]}
        for item in closure["chain"]
    ]


def _prepared_item(prepared: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "workspace": prepared["workspace"],
        "document": prepared["document_metadata"],
        "text": prepared["decoded_source"],
    }


def _stored_currentness(closure: Mapping[str, Any]) -> dict[str, Any] | None:
    return closure["selection"]["selection"]["currentness"]


def _stored_facts(closure: Mapping[str, Any]) -> Any:
    return closure["selection"]["selection"]["facts"]


def _stored_scope(closure: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(closure["selection"]["fiscal_scope"])


def _stored_slug(closure: Mapping[str, Any]) -> str:
    slug = closure["record"]["slug"]
    if type(slug) is not str:
        raise PrivateEconomicStageError("malformed_prior")
    return slug


def _stage_root(stage_dir: str | Path) -> Path:
    raw = Path(stage_dir)
    if raw.is_symlink():
        raise PrivateEconomicStageError("unsafe_path")
    root = raw.expanduser().resolve()
    if root == _REPO or _REPO in root.parents:
        raise PrivateEconomicStageError("stage_inside_repository")
    if not (root / "records").is_dir() or not (root / "context" / "latest.json").is_file():
        raise PrivateEconomicStageError("stage_incomplete")
    return root


def _admit_generation_id(generation_id: object) -> str:
    """24 lowercase hex, and the publisher slug grammar, before the id is a filename."""
    if type(generation_id) is not str or _GENERATION_ID_RE.fullmatch(generation_id) is None:
        raise PrivateEconomicStageError("unsafe_path")
    try:
        validate_slug(generation_id)
    except EarningsPrivatePublicationError as exc:
        raise PrivateEconomicStageError("unsafe_path") from exc
    return generation_id


def _admit_slug(slug: object) -> str:
    if type(slug) is not str:
        raise PrivateEconomicStageError("unsafe_path")
    try:
        validate_slug(slug)
    except EarningsPrivatePublicationError as exc:
        raise PrivateEconomicStageError("unsafe_path") from exc
    return slug


def _write_stage_file(path: Path, body: bytes) -> None:
    """Publish stage bytes by inode swap, never by truncating an existing inode.

    ``Path.write_bytes`` opens the target with ``O_TRUNC`` and reuses its inode,
    so a hardlink planted at a stage path lets this writer rewrite the victim
    under its other name. A stage file must be owned by one name: refuse a
    symlink or any target whose ``st_nlink`` is above 1, then write an exclusive
    private temp file beside the target and ``os.replace`` it onto the path.
    Callers keep their own ``_confined_file`` confinement; this only owns the
    write mechanism.
    """
    try:
        status = os.lstat(path)
    except FileNotFoundError:
        status = None
    if status is not None and (
        stat.S_ISLNK(status.st_mode) or status.st_nlink > 1
    ):
        raise PrivateEconomicStageError("hardlinked_stage_file")
    temp = path.parent / f".{path.name}.tmp-{os.getpid()}-{os.urandom(4).hex()}"
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _confined_file(stage_root: Path, directory: Path, name: str) -> Path:
    """One child of directory whose resolved path stays under the stage root."""
    if type(name) is not str or not name or name != Path(name).name:
        raise PrivateEconomicStageError("unsafe_path")
    path = (directory / name).resolve()
    root = stage_root.resolve()
    if path.parent != directory.resolve() or root not in path.parents:
        raise PrivateEconomicStageError("unsafe_path")
    return path


def _admit_chain_paths(root: Path, chain: list[dict[str, Any]], slug: str) -> None:
    _confined_file(root, root / "records", f"{_admit_slug(slug)}.json")
    for item in chain:
        generation_id = _admit_generation_id(item["workspace"]["generation_id"])
        _confined_file(root, root / "native" / "workspaces", f"{generation_id}.json")


def _write_stage(
    root: Path,
    *,
    chain: list[dict[str, Any]],
    currentness: dict[str, Any] | None,
    facts: Any,
    fiscal_scope: tuple[str, ...] | list[str],
    slug: str,
    predecessor: dict[str, Any] | None,
    floor: str | None,
    observed_at: str | None,
) -> dict[str, Any]:
    if not chain:
        raise PrivateEconomicStageError("preparation_refused")
    if len(chain) > MAX_NATIVE_CHAIN:
        raise PrivateEconomicStageError("over_limit")
    newest = chain[-1]
    workspace = newest["workspace"]
    document = newest["document"]
    text = newest["text"]
    if type(text) is not str:
        raise PrivateEconomicStageError("mismatched_source")
    company_id = workspace.get("issuer", {}).get("company_id") if type(workspace.get("issuer")) is dict else None
    if not isinstance(company_id, str) or _plain_str(company_id) != pg_profile.pg_issuer().company_id:
        raise PrivateEconomicStageError("cross_issuer")
    event_id = workspace.get("event_id")
    if type(event_id) is not str:
        raise PrivateEconomicStageError("malformed_prior")
    selection = {"facts": facts, "currentness": currentness}
    interpretation = economic_interpretation.build_economic_interpretation(
        workspace,
        source_texts={document["document_id"]: text},
        fiscal_scope=tuple(fiscal_scope),
        selection=selection,
        semantic_revision=economic_interpretation.SEMANTIC_REVISION,
        code_revision=economic_interpretation.CODE_REVISION,
    )
    _assert_authority(interpretation)
    observations = interpretation["observations"]
    if type(observations) is not list or not 1 <= len(observations) <= 24:
        raise PrivateEconomicStageError("over_limit")
    dossier = {
        "schema": RECORD_SCHEMA_V2,
        "page": DOSSIER_PAGE,
        "slug": slug,
        "required_tier": "essential",
        "public_facts": 0,
        "locked_facts": len(observations),
        "facts_html": "",
        "receipt_rows_html": "",
        "economic_interpretation": interpretation,
    }
    links: list[dict[str, str]] = []
    received: dict[str, dict[str, Any]] = {}
    _admit_chain_paths(root, chain, slug)
    native = _reset_native(root)
    workspaces = native / "workspaces"
    documents = native / "documents"
    bodies = native / "source_bodies"
    for item in chain:
        workspace_body = canonical_json_bytes(item["workspace"])
        generation_id = _admit_generation_id(item["workspace"]["generation_id"])
        _write_stage_file(_confined_file(root, workspaces, f"{generation_id}.json"), workspace_body)
        document_body = canonical_json_bytes(item["document"])
        document_digest = sha256(document_body).hexdigest()
        _write_stage_file(documents / f"{document_digest}.json", document_body)
        item_text = item["text"]
        if type(item_text) is not str:
            raise PrivateEconomicStageError("mismatched_source")
        text_body = item_text.encode("utf-8")
        content_digest = sha256(text_body).hexdigest()
        declared = item["document"].get("content_sha256")
        if type(declared) is not str or content_digest != declared:
            raise PrivateEconomicStageError("mismatched_source")
        body_path = bodies / f"{content_digest}.txt"
        try:
            body_status = os.lstat(body_path)
        except FileNotFoundError:
            body_status = None
        except OSError as exc:
            raise PrivateEconomicStageError("unreadable_stage_file") from exc
        if body_status is not None:
            if stat.S_ISLNK(body_status.st_mode) or body_status.st_nlink > 1:
                raise PrivateEconomicStageError("hardlinked_stage_file")
            try:
                existing_body = body_path.read_bytes()
            except OSError as exc:
                raise PrivateEconomicStageError("unreadable_stage_file") from exc
            if existing_body != text_body:
                raise PrivateEconomicStageError("mismatched_source")
        _write_stage_file(body_path, text_body)
        received[content_digest] = {
            "sha256": content_digest,
            "length": len(text_body),
            "declared_encoding": "utf-8",
        }
        links.append({"workspace": generation_id, "document": document_digest})
    clocks = _clocks(chain, currentness, observed_at)
    if type(floor) is str and _CLOCK_RE.fullmatch(floor):
        clocks.append(floor)
    cutoff = max(clocks)
    stage_manifest = {
        "schema": NATIVE_STAGE_SCHEMA,
        "native_source_cutoff": cutoff,
        "previous_manifest": predecessor,
        "selections": {
            slug: {
                "company_id": company_id,
                "event_id": event_id,
                "profile_version": pg_profile.PG_PROFILE_VERSION,
                "fiscal_scope": list(fiscal_scope),
                "chain": links,
                "selection": selection,
                "interpretation_id": interpretation["interpretation_id"],
            },
        },
        "economic_slots": {company_id: {"slug": slug, "event_id": event_id}},
        "received": received,
    }
    _write_stage_file(native / "latest.json", canonical_json_bytes(stage_manifest))
    _write_stage_file(
        _confined_file(root, root / "records", f"{_admit_slug(slug)}.json"),
        canonical_json_bytes(dossier),
    )
    return {
        "wrote": True,
        "schema": RECORD_SCHEMA_V2,
        "slug": slug,
        "source_sha256": document["content_sha256"],
        "first_observed_at": workspace["lifecycle"]["observed_at"],
        "interpretation_id": interpretation["interpretation_id"],
        "currentness": currentness["state"] if type(currentness) is dict else None,
        "authority_ceiling": AUTHORITY_CEILING,
    }


def _assert_authority(interpretation: Mapping[str, Any]) -> None:
    if AUTHORITY_CEILING != "research_display_only":
        raise PrivateEconomicStageError("authority_ceiling")
    authority = interpretation.get("authority")
    if authority != economic_interpretation.AUTHORITY or any(authority.values()):
        raise PrivateEconomicStageError("authority_ceiling")


def _clocks(
    chain: list[dict[str, Any]],
    currentness: dict[str, Any] | None,
    observed_at: str | None,
) -> list[str]:
    found: list[str] = []
    if type(observed_at) is str and _CLOCK_RE.fullmatch(observed_at):
        found.append(observed_at)
    if type(currentness) is dict and type(currentness.get("source_clock")) is str:
        clock = currentness["source_clock"]
        if _CLOCK_RE.fullmatch(clock):
            found.append(clock)
    for item in chain:
        lifecycle = item["workspace"].get("lifecycle") if type(item["workspace"]) is dict else None
        if type(lifecycle) is dict:
            for key in ("observed_at", "source_available_at"):
                clock = lifecycle.get(key)
                if type(clock) is str and _CLOCK_RE.fullmatch(clock):
                    found.append(clock)
        generated = item["workspace"].get("generated_at") if type(item["workspace"]) is dict else None
        if type(generated) is str and _CLOCK_RE.fullmatch(generated):
            found.append(generated)
        document = item["document"]
        if type(document) is dict:
            for key in ("available_at", "fetched_at", "published_at"):
                clock = document.get(key)
                if type(clock) is str and _CLOCK_RE.fullmatch(clock):
                    found.append(clock)
    if not found:
        raise PrivateEconomicStageError("malformed_source_clock")
    return found


def _reset_native(root: Path) -> Path:
    native = root / "native"
    if native.is_symlink():
        raise PrivateEconomicStageError("unsafe_path")
    if native.exists():
        if not native.is_dir():
            raise PrivateEconomicStageError("unsafe_path")
        for path in sorted(native.rglob("*"), reverse=True):
            if path.is_symlink():
                raise PrivateEconomicStageError("unsafe_path")
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    for name in ("workspaces", "documents", "source_bodies"):
        (native / name).mkdir(parents=True, exist_ok=True)
    return native
