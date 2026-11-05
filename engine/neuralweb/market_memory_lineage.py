"""Same-owner certified lineage; v1 full-ancestry readers remain unchanged.

Offline qualification validates every original append-one link. Online reads
validate published certificates and exact requested original bytes. These are
different assurance contracts. This module implements no production publisher,
signature, scheduler, source capture, fitting or catalog activation.
"""
from __future__ import annotations

import copy
import re
import os
import stat
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from engine.neuralweb import market_memory_pit as pit
from engine.neuralweb import market_memory_trusted as trusted

CERTIFICATE_SCHEMA = "market_memory.lineage_certificate.v1"
HEAD_SCHEMA = "market_memory.lineage_head.v1"
ASSURANCE = "certified_publication_lineage_v1"
_TOKEN = object()
_DIGEST = re.compile(r"[a-f0-9]{64}\Z")
_CERTIFICATE = re.compile(r"mmcert_[a-f0-9]{64}\Z")
_AUTHORITY = {"external_origin_authenticated": False, "external_clock_authenticated": False,
              "ancestor_live_reread": False, "may_train": False, "may_trade": False}
_IMPORTED_PRODUCER_CODE_SHA256 = sha256(
    b"".join(Path(module.__file__).read_bytes() for module in (pit, trusted))
    + Path(__file__).read_bytes()
).hexdigest()


class LineageBudgetError(pit.MarketMemoryStoreError):
    pass


class LineageRightsError(pit.MarketMemoryStoreError):
    pass


class LineageProofUnavailableError(pit.MarketMemoryStoreError):
    """No exact authoritative publication ref is available; never substitute."""


class LineageProofPendingError(pit.MarketMemoryStoreError):
    """The requested current generation has no completed published proof."""


@dataclass(frozen=True)
class OfflineQualificationBudget:
    """Explicit offline ceiling; constructing it grants no production effect."""
    total_bytes: int = 512 * 1024 * 1024
    batch_bytes: int = 64 * 1024 * 1024
    cpu_seconds: float = 30
    wall_seconds: float = 60

    def __post_init__(self):
        for value, ceiling in ((self.total_bytes, 512 * 1024 * 1024),
                               (self.batch_bytes, 64 * 1024 * 1024)):
            if type(value) is not int or not 1 <= value <= ceiling:
                raise LineageBudgetError("invalid explicit offline byte budget")
        for value, ceiling in ((self.cpu_seconds, 30), (self.wall_seconds, 60)):
            if type(value) not in (int, float) or not 0 < value <= ceiling:
                raise LineageBudgetError("invalid explicit offline time budget")
        if self.batch_bytes > self.total_bytes:
            raise LineageBudgetError("batch budget exceeds total budget")


class _ReadBudget:
    def __init__(self, *, total_bytes=64 * 1024 * 1024, offline=None):
        self.offline = offline
        self.limit = offline.total_bytes if offline else total_bytes
        self.batch_limit = offline.batch_bytes if offline else self.limit
        self.bytes = 0
        self.batches = []
        self.batch = None
        self.cpu_started = time.process_time()
        self.wall_started = time.monotonic()
        self.last_generation_id = None

    def check(self):
        if self.offline and (time.process_time() - self.cpu_started > self.offline.cpu_seconds
                             or time.monotonic() - self.wall_started > self.offline.wall_seconds):
            raise LineageBudgetError("offline qualification time budget exhausted")

    def read(self, path, *, limit, label, generation_id=None):
        self.check()
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise pit.MarketMemoryStoreError(f"{label} is unavailable") from exc
        if size > limit or size > self.batch_limit or self.bytes + size > self.limit:
            raise LineageBudgetError("lineage input byte budget exhausted")
        if self.batch is None or self.batch["input_bytes"] + size > self.batch_limit:
            if self.batch is not None:
                self.batch["completed_at"] = _instant()
            self.batch = {"input_object_count": 0, "input_bytes": 0,
                          "first_source_generation_id": None, "last_source_generation_id": None,
                          "boundary_newer_generation_id": self.last_generation_id,
                          "boundary_older_generation_id": generation_id,
                          "started_at": _instant(), "completed_at": _instant()}
            self.batches.append(self.batch)
        payload, body = pit._read_canonical_object(path, limit=min(limit, self.limit - self.bytes), label=label)
        # Check actual bytes as well as pre-read size; mutation never increases a grant.
        if len(body) > size or self.batch["input_bytes"] + len(body) > self.batch_limit:
            raise LineageBudgetError("lineage input changed during bounded read")
        self.bytes += len(body)
        self.batch["input_bytes"] += len(body)
        self.batch["input_object_count"] += 1
        if generation_id:
            if self.batch["first_source_generation_id"] is None:
                self.batch["first_source_generation_id"] = generation_id
            self.batch["last_source_generation_id"] = generation_id
            self.last_generation_id = generation_id
        self.batch["completed_at"] = _instant()
        self.check()
        return payload, body


def canonical_bytes(value):
    return pit._canonical_bytes(value)


def _instant():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _digest(value, field):
    if type(value) is not str or not _DIGEST.fullmatch(value):
        raise pit.MarketMemoryStoreError(f"invalid lineage {field}")


def _policy(policy, action, resource):
    if (type(getattr(policy, "policy_id", None)) is not str or not 1 <= len(policy.policy_id) <= 256
            or not callable(getattr(policy, "check", None))):
        raise LineageRightsError("authenticated application policy required")
    try:
        decision = policy.check(action, copy.deepcopy(resource))
    except Exception as exc:
        raise LineageRightsError("current lineage rights denied") from exc
    if decision is not None:
        raise LineageRightsError("authorization boolean is not authenticated policy")


def _profile(reader):
    if type(reader) is pit.FileAsKnownAtReader:
        return pit.STORE_PROFILE
    if type(reader) is trusted.TrustedFileAsKnownAtReader:
        return trusted.TRUSTED_STORE_PROFILE
    raise pit.MarketMemoryStoreError("concrete PIT/trusted owner reader required")


def _resource(reader, generation_id=None, query_id=None):
    return {"store_profile": _profile(reader), "owner_root_ref": sha256(str(reader.root).encode()).hexdigest(),
            "generation_id": generation_id, "query_id": query_id}


def _owner_state(reader, budget):
    profile = _profile(reader)
    pit._validate_store_directory_tree(reader.root)
    manifest, manifest_body = budget.read(pit._store_manifest_path(reader.root),
        limit=pit._MAX_STORE_MANIFEST_BYTES, label="certified owner manifest")
    if profile == pit.STORE_PROFILE:
        clean_manifest = pit._validate_store_manifest(manifest)
    else:
        clean_manifest = trusted._validate_manifest(manifest)
    head, head_body = budget.read(pit._head_path(reader.root), limit=pit._MAX_HEAD_BYTES, label="certified owner HEAD")
    clean_head = pit._validate_head(head, store_id=clean_manifest["store_id"])
    return clean_manifest, sha256(manifest_body).hexdigest(), clean_head, sha256(head_body).hexdigest()


@dataclass(frozen=True, init=False)
class VerifiedOwnerLineage:
    """In-process qualification result; not external origin authentication."""
    _body: bytes
    _seal: object

    def __init__(self, body, *, _key=None):
        if _key is not _TOKEN:
            raise pit.MarketMemoryStoreError("owner-qualified lineage required")
        object.__setattr__(self, "_body", body)
        object.__setattr__(self, "_seal", _TOKEN)


def _qualify_owner(reader, *, operation_ref, policy, budget, expected_head_body_sha256=None):
    resource = _resource(reader)
    _policy(policy, "qualify_market_memory_lineage", resource)
    if type(operation_ref) is not str or not 1 <= len(operation_ref) <= 256:
        raise pit.MarketMemoryStoreError("bounded qualification operation ref required")
    if type(budget) is not OfflineQualificationBudget:
        raise LineageBudgetError("explicit offline budget required")
    account = _ReadBudget(offline=budget)
    started = _instant()
    manifest, manifest_digest, head, head_digest = _owner_state(reader, account)
    head_observed_at = _instant()
    if expected_head_body_sha256 is not None:
        _digest(expected_head_body_sha256, "expected HEAD digest")
        if expected_head_body_sha256 != head_digest:
            raise pit.MarketMemoryStoreError("source HEAD differs from qualification grant")
    generation_id = head["generation_id"]
    links, seen, newer = [], set(), None
    while generation_id is not None:
        account.check()
        if generation_id in seen or len(seen) >= pit._MAX_GENERATION_CAPTURES + 1:
            raise pit.MarketMemoryStoreError("lineage cycle/depth bound exceeded")
        seen.add(generation_id)
        generation, body = account.read(pit._generation_path(reader.root, generation_id),
            limit=pit._MAX_GENERATION_BYTES, label="offline exact owner generation", generation_id=generation_id)
        clean = pit._validate_generation(generation, store_id=manifest["store_id"])
        if clean["generation_id"] != generation_id:
            raise pit.MarketMemoryStoreError("source generation filename/identity mismatch")
        digest = sha256(body).hexdigest()
        if newer is None:
            if digest != head["generation_sha256"]:
                raise pit.MarketMemoryStoreError("source HEAD generation digest mismatch")
        else:
            pit._validate_generation_link(newer=newer, older=clean)
        links.append({"generation_id": generation_id, "generation_sha256": digest,
                      "previous_generation_id": clean["previous_generation_id"], "capture_count": len(clean["captures"])})
        newer = clean
        generation_id = clean["previous_generation_id"]
    if newer is None or newer["captures"] or links[-1]["capture_count"] != 0:
        raise pit.MarketMemoryStoreError("lineage did not reach actual empty genesis")
    if len(links) != links[0]["capture_count"] + 1:
        raise pit.MarketMemoryStoreError("lineage count/depth mismatch")
    account.check()
    _policy(policy, "qualify_market_memory_lineage", resource)
    value = {"schema": CERTIFICATE_SCHEMA, "certificate_id": "", "store_profile": _profile(reader),
             "store_id": manifest["store_id"], "store_manifest_sha256": manifest_digest,
             "qualified_source_head": {"head_body_sha256": head_digest, "generation_id": head["generation_id"],
                 "generation_sha256": head["generation_sha256"], "capture_count": links[0]["capture_count"], "observed_at": head_observed_at},
             "chain_links": links,
             "verification": {"qualification_operation_ref": operation_ref, "producer_code_sha256": _IMPORTED_PRODUCER_CODE_SHA256,
                 "producer_config_sha256": sha256(canonical_bytes({"profile": _profile(reader), "budget": budget.__dict__})).hexdigest(),
                 "started_at": started, "completed_at": _instant(), "per_batch_byte_limit": budget.batch_bytes,
                 "total_byte_limit": budget.total_bytes, "total_input_bytes": account.bytes,
                 "cpu_seconds_limit": budget.cpu_seconds, "wall_seconds_limit": budget.wall_seconds,
                 "batches": account.batches, "genesis_verified": True, "all_append_one_links_verified": True,
                 "cycle_depth_count_verified": True, "complete": True},
             "assurance": ASSURANCE, "authority": dict(_AUTHORITY)}
    account.check()
    return VerifiedOwnerLineage(canonical_bytes(value), _key=_TOKEN)


def _content_id(value):
    core = copy.deepcopy(value)
    core.pop("certificate_id")
    return "mmcert_" + sha256(canonical_bytes(core)).hexdigest()


def validate_certificate(value):
    expected = {"schema", "certificate_id", "store_profile", "store_id", "store_manifest_sha256",
                "qualified_source_head", "chain_links", "verification", "assurance", "authority"}
    if type(value) is not dict or set(value) != expected:
        raise pit.MarketMemoryStoreError("lineage certificate fields differ from declared schema")
    clean = copy.deepcopy(value)
    if (clean["schema"] != CERTIFICATE_SCHEMA or clean["assurance"] != ASSURANCE
            or type(clean["authority"]) is not dict or set(clean["authority"]) != set(_AUTHORITY)
            or any(value is not False for value in clean["authority"].values())):
        raise pit.MarketMemoryStoreError("lineage assurance/authority mismatch")
    if clean["store_profile"] not in (pit.STORE_PROFILE, trusted.TRUSTED_STORE_PROFILE):
        raise pit.MarketMemoryStoreError("unknown concrete lineage store profile")
    if type(clean["store_id"]) is not str or not pit._STORE_ID.fullmatch(clean["store_id"]):
        raise pit.MarketMemoryStoreError("invalid lineage store id")
    _digest(clean["store_manifest_sha256"], "store manifest digest")
    head = clean["qualified_source_head"]
    if type(head) is not dict or set(head) != {"head_body_sha256", "generation_id", "generation_sha256", "capture_count", "observed_at"}:
        raise pit.MarketMemoryStoreError("lineage qualified HEAD fields mismatch")
    _digest(head["head_body_sha256"], "source HEAD digest")
    if type(head["capture_count"]) is not int:
        raise pit.MarketMemoryStoreError("qualified HEAD capture count is not an integer")
    pit._parse_exact_utc(head["observed_at"], field="lineage observed_at")
    links = clean["chain_links"]
    if type(links) is not list or not 1 <= len(links) <= 4097:
        raise pit.MarketMemoryStoreError("invalid lineage link bound")
    seen = set()
    for i, link in enumerate(links):
        if type(link) is not dict or set(link) != {"generation_id", "generation_sha256", "previous_generation_id", "capture_count"}:
            raise pit.MarketMemoryStoreError("invalid lineage link fields")
        gid = link["generation_id"]
        if type(gid) is not str or not pit._GENERATION_ID.fullmatch(gid) or gid in seen:
            raise pit.MarketMemoryStoreError("invalid/duplicate lineage generation id")
        seen.add(gid)
        _digest(link["generation_sha256"], "generation digest")
        if type(link["capture_count"]) is not int or link["capture_count"] != len(links) - i - 1:
            raise pit.MarketMemoryStoreError("lineage is not complete append-one through genesis")
        previous = links[i + 1]["generation_id"] if i + 1 < len(links) else None
        if link["previous_generation_id"] != previous:
            raise pit.MarketMemoryStoreError("lineage predecessor binding mismatch")
    if any(head[k] != links[0][k] for k in ("generation_id", "generation_sha256", "capture_count")):
        raise pit.MarketMemoryStoreError("lineage source HEAD/link mismatch")
    verification = clean["verification"]
    fields = {"qualification_operation_ref", "producer_code_sha256", "producer_config_sha256", "started_at", "completed_at",
              "per_batch_byte_limit", "total_byte_limit", "total_input_bytes", "cpu_seconds_limit", "wall_seconds_limit",
              "batches", "genesis_verified", "all_append_one_links_verified", "cycle_depth_count_verified", "complete"}
    if type(verification) is not dict or set(verification) != fields:
        raise pit.MarketMemoryStoreError("lineage qualification verification fields mismatch")
    for flag in ("genesis_verified", "all_append_one_links_verified", "cycle_depth_count_verified", "complete"):
        if verification[flag] is not True:
            raise pit.MarketMemoryStoreError("lineage qualification is incomplete")
    for field in ("producer_code_sha256", "producer_config_sha256"):
        _digest(verification[field], field)
    if type(verification["qualification_operation_ref"]) is not str or not 1 <= len(verification["qualification_operation_ref"]) <= 256:
        raise pit.MarketMemoryStoreError("lineage operation ref missing")
    start, _ = pit._parse_exact_utc(verification["started_at"], field="qualification started_at")
    end, _ = pit._parse_exact_utc(verification["completed_at"], field="qualification completed_at")
    if end < start:
        raise pit.MarketMemoryStoreError("qualification interval reversed")
    observed_at, _ = pit._parse_exact_utc(head["observed_at"], field="lineage observed_at")
    if not start <= observed_at <= end:
        raise pit.MarketMemoryStoreError("source HEAD observation lies outside qualification")
    OfflineQualificationBudget(total_bytes=verification["total_byte_limit"], batch_bytes=verification["per_batch_byte_limit"],
        cpu_seconds=verification["cpu_seconds_limit"], wall_seconds=verification["wall_seconds_limit"])
    batches = verification["batches"]
    if type(batches) is not list or not batches or len(batches) > 8194:
        raise pit.MarketMemoryStoreError("qualification batch evidence missing")
    total = 0
    positions = {link["generation_id"]: i for i, link in enumerate(links)}
    generation_cursor, metadata_remaining = 0, 2  # manifest, then source HEAD
    previous_batch_end = start
    for batch in batches:
        if type(batch) is not dict or set(batch) != {"input_object_count", "input_bytes", "first_source_generation_id", "last_source_generation_id", "boundary_newer_generation_id", "boundary_older_generation_id", "started_at", "completed_at"}:
            raise pit.MarketMemoryStoreError("qualification batch fields mismatch")
        if (type(batch["input_object_count"]) is not int or batch["input_object_count"] < 1
                or type(batch["input_bytes"]) is not int or not 1 <= batch["input_bytes"] <= verification["per_batch_byte_limit"]):
            raise pit.MarketMemoryStoreError("qualification batch accounting invalid")
        total += batch["input_bytes"]
        batch_start, _ = pit._parse_exact_utc(batch["started_at"], field="batch started_at")
        batch_end, _ = pit._parse_exact_utc(batch["completed_at"], field="batch completed_at")
        if not start <= batch_start <= batch_end <= end:
            raise pit.MarketMemoryStoreError("qualification batch interval mismatch")
        if batch_start < previous_batch_end:
            raise pit.MarketMemoryStoreError("qualification batch order mismatch")
        previous_batch_end = batch_end
        for field in ("first_source_generation_id", "last_source_generation_id", "boundary_newer_generation_id", "boundary_older_generation_id"):
            if batch[field] is not None and batch[field] not in seen:
                raise pit.MarketMemoryStoreError("qualification batch witness is not a chain member")
        if batch["boundary_newer_generation_id"] is not None and batch["boundary_older_generation_id"] is not None:
            newer = next(link for link in links if link["generation_id"] == batch["boundary_newer_generation_id"])
            if newer["previous_generation_id"] != batch["boundary_older_generation_id"]:
                raise pit.MarketMemoryStoreError("qualification batch append-link witness mismatch")
        first, last = batch["first_source_generation_id"], batch["last_source_generation_id"]
        if first is None:
            if (last is not None or generation_cursor or batch["input_object_count"] > metadata_remaining
                    or batch["boundary_newer_generation_id"] is not None
                    or batch["boundary_older_generation_id"] is not None):
                raise pit.MarketMemoryStoreError("qualification metadata batch coverage mismatch")
            metadata_remaining -= batch["input_object_count"]
        else:
            if last is None or positions[first] != generation_cursor or positions[last] < generation_cursor:
                raise pit.MarketMemoryStoreError("qualification generation batch coverage mismatch")
            generation_count = positions[last] - generation_cursor + 1
            expected_newer = links[generation_cursor - 1]["generation_id"] if generation_cursor else None
            expected_older = None if metadata_remaining else first
            if (batch["input_object_count"] != generation_count + metadata_remaining
                    or batch["boundary_newer_generation_id"] != expected_newer
                    or batch["boundary_older_generation_id"] != expected_older):
                raise pit.MarketMemoryStoreError("qualification batch object/boundary accounting mismatch")
            generation_cursor += generation_count
            metadata_remaining = 0
    if generation_cursor != len(links) or metadata_remaining:
        raise pit.MarketMemoryStoreError("qualification batches do not cover every original object")
    if type(verification["total_input_bytes"]) is not int or total != verification["total_input_bytes"] or total > verification["total_byte_limit"]:
        raise pit.MarketMemoryStoreError("qualification total byte accounting mismatch")
    if clean["certificate_id"] != _content_id(clean):
        raise pit.MarketMemoryStoreError("lineage certificate identity mismatch")
    if len(canonical_bytes(clean)) > 2 * 1024 * 1024:
        raise pit.MarketMemoryStoreError("lineage certificate object exceeds bound")
    return clean


def build_lineage_certificate(qualification):
    if type(qualification) is not VerifiedOwnerLineage or qualification._seal is not _TOKEN:
        raise pit.MarketMemoryStoreError("genuine owner qualification required")
    import json
    value = json.loads(qualification._body)
    value["certificate_id"] = _content_id(value)
    return validate_certificate(value)


def build_lineage_head_pointer(certificate, *, publisher_revision):
    clean = validate_certificate(certificate)
    if type(publisher_revision) is not str or not 1 <= len(publisher_revision) <= 256:
        raise pit.MarketMemoryStoreError("publisher revision required")
    return {"schema": HEAD_SCHEMA, "store_id": clean["store_id"], "certificate_id": clean["certificate_id"],
            "certificate_sha256": sha256(canonical_bytes(clean)).hexdigest(),
            "qualified_source_generation_id": clean["qualified_source_head"]["generation_id"],
            "qualified_source_generation_sha256": clean["qualified_source_head"]["generation_sha256"],
            "publisher_revision": publisher_revision}


def lineage_head_path(owner_root):
    return pit._safe_store_path(Path(owner_root), "lineage", "LINEAGE_HEAD.json")


def certificate_path(owner_root, certificate_id):
    if type(certificate_id) is not str or not _CERTIFICATE.fullmatch(certificate_id):
        raise pit.MarketMemoryStoreError("invalid certificate reference")
    return pit._safe_store_path(Path(owner_root), "lineage", "certificates", certificate_id[7:9], certificate_id + ".json")


@dataclass(frozen=True, init=False)
class _Membership:
    root: Path
    profile: str
    store_id: str
    manifest_digest: str
    link: dict
    certificate: dict
    publication_resource: dict
    _seal: object

    def __init__(self, reader, manifest, manifest_digest, link, certificate, publication_resource, *, _key=None):
        if _key is not _TOKEN:
            raise pit.MarketMemoryStoreError("published owner membership required")
        for k, v in {"root": reader.root, "profile": _profile(reader), "store_id": manifest["store_id"],
                     "manifest_digest": manifest_digest, "link": copy.deepcopy(link),
                     "certificate": copy.deepcopy(certificate),
                     "publication_resource": copy.deepcopy(publication_resource), "_seal": _TOKEN}.items():
            object.__setattr__(self, k, v)


def _membership(reader, generation_id, expected_certificate_ref, budget, *, policy):
    if type(generation_id) is not str or not pit._GENERATION_ID.fullmatch(generation_id):
        raise pit.MarketMemoryStoreError("exact requested generation id required")
    manifest, manifest_digest, head, head_digest = _owner_state(reader, budget)
    pit._validate_store_directory(reader.root / "lineage", label="owner lineage directory")
    pointer, _ = budget.read(lineage_head_path(reader.root), limit=65536, label="owner lineage HEAD")
    if type(pointer) is not dict or set(pointer) != {"schema", "store_id", "certificate_id", "certificate_sha256",
            "qualified_source_generation_id", "qualified_source_generation_sha256", "publisher_revision"}:
        raise pit.MarketMemoryStoreError("lineage pointer fields mismatch")
    if (pointer["schema"] != HEAD_SCHEMA or pointer["store_id"] != manifest["store_id"]
            or type(pointer["publisher_revision"]) is not str or not 1 <= len(pointer["publisher_revision"]) <= 256):
        raise pit.MarketMemoryStoreError("lineage pointer owner/publication mismatch")
    _digest(pointer["certificate_sha256"], "pointer certificate digest")
    if expected_certificate_ref is not None and expected_certificate_ref != pointer["certificate_id"]:
        raise LineageProofUnavailableError("historical expected publication ref unavailable; no latest fallback")
    proof_path = certificate_path(reader.root, pointer["certificate_id"])
    for directory in (proof_path.parent.parent, proof_path.parent):
        pit._validate_store_directory(directory, label="owner lineage certificate directory")
    for path in (lineage_head_path(reader.root), proof_path):
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise pit.MarketMemoryStoreError("owner lineage publication is unavailable") from exc
        if metadata.st_uid != os.getuid() or stat.S_IMODE(metadata.st_mode) != 0o600:
            raise pit.MarketMemoryStoreError("owner lineage proof must be an owned 0600 file")
    certificate, body = budget.read(proof_path, limit=2 * 1024 * 1024,
        label="owner published lineage certificate")
    clean = validate_certificate(certificate)
    if (sha256(body).hexdigest() != pointer["certificate_sha256"] or clean["certificate_id"] != pointer["certificate_id"]
            or clean["store_profile"] != _profile(reader) or clean["store_id"] != manifest["store_id"]
            or clean["store_manifest_sha256"] != manifest_digest
            or pointer["qualified_source_generation_id"] != clean["qualified_source_head"]["generation_id"]
            or pointer["qualified_source_generation_sha256"] != clean["qualified_source_head"]["generation_sha256"]):
        raise pit.MarketMemoryStoreError("published certificate/store/pointer mismatch")
    # File custody and a self-consistent hash are not qualification admission.
    # The authenticated application must admit this exact publication before
    # the successor may use it to avoid an online full-ancestry walk.
    publication_resource = {
        **_resource(reader, generation_id), "store_id": manifest["store_id"],
        "certificate_id": clean["certificate_id"], "certificate_sha256": sha256(body).hexdigest(),
        "publisher_revision": pointer["publisher_revision"],
        "qualification_operation_ref": clean["verification"]["qualification_operation_ref"],
        "producer_code_sha256": clean["verification"]["producer_code_sha256"],
        "producer_config_sha256": clean["verification"]["producer_config_sha256"],
        "qualified_source_head": copy.deepcopy(clean["qualified_source_head"]),
    }
    _policy(policy, "use_qualified_market_memory_lineage_certificate", publication_resource)
    links = [link for link in clean["chain_links"] if link["generation_id"] == generation_id]
    if len(links) != 1:
        if generation_id == head["generation_id"]:
            raise LineageProofPendingError("requested current generation is not certified; proof pending")
        raise pit.MarketMemoryStoreError("requested generation is not certified")
    membership = _Membership(reader, manifest, manifest_digest, links[0], clean, publication_resource, _key=_TOKEN)
    observed = {"head_body_sha256": head_digest, "generation_id": head["generation_id"], "generation_sha256": head["generation_sha256"]}
    pending = any(observed[k] != clean["qualified_source_head"][k] for k in observed)
    return membership, observed, pending


def _read_owner_generation(reader, membership, *, budget, policy):
    if (type(budget) is not _ReadBudget or type(membership) is not _Membership or membership._seal is not _TOKEN
            or membership.root != reader.root or membership.profile != _profile(reader)):
        raise pit.MarketMemoryStoreError("concrete owner certified membership required")
    link = membership.link
    _policy(policy, "read_market_memory_lineage", _resource(reader, link["generation_id"]))
    generation, body = budget.read(pit._generation_path(reader.root, link["generation_id"]),
        limit=pit._MAX_GENERATION_BYTES, label="certified exact original generation")
    clean = pit._validate_generation(generation, store_id=membership.store_id)
    if (sha256(body).hexdigest() != link["generation_sha256"] or clean["generation_id"] != link["generation_id"]
            or clean["previous_generation_id"] != link["previous_generation_id"] or len(clean["captures"]) != link["capture_count"]):
        raise pit.MarketMemoryStoreError("certified original generation differs from published qualification")
    return clean


def _read_owner_capture(reader, membership, *, query_id, budget, policy):
    # Keep the exact requested query in every disclosure policy resource.
    resource = _resource(reader, membership.link["generation_id"], query_id)
    _policy(policy, "read_market_memory_lineage", resource)
    generation = _read_owner_generation(reader, membership, budget=budget, policy=policy)
    if type(query_id) is not str or not pit._QUERY_ID.fullmatch(query_id):
        raise pit.MarketMemoryStoreError("exact requested query id required")
    entries = [row for row in generation["captures"] if row["query_id"] == query_id]
    if len(entries) != 1:
        raise pit.MarketMemoryStoreError("query is absent/ambiguous in certified original generation")
    receipt_limit = pit._MAX_RECEIPT_BYTES if _profile(reader) == pit.STORE_PROFILE else trusted._MAX_RECEIPT_BYTES
    _policy(policy, "read_market_memory_capture_metadata", {
        **resource, "store_id": membership.store_id,
        "context_id": entries[0]["context_id"], "capture_id": entries[0]["capture_id"],
    })
    receipt, body = budget.read(pit._query_path(reader.root, query_id),
        limit=receipt_limit, label="certified original query receipt")
    validator = pit._validate_capture_receipt if _profile(reader) == pit.STORE_PROFILE else trusted._validate_receipt
    clean = validator(receipt)
    if clean["store_id"] != membership.store_id or pit._capture_entry(clean) != entries[0]:
        raise pit.MarketMemoryStoreError("certified receipt/index mismatch")
    _policy(policy, "read_market_memory_capture", _capture_resource(resource, clean))
    alias, alias_body = budget.read(pit._context_path(reader.root, clean["context_id"]),
        limit=receipt_limit, label="certified original context alias")
    if body != alias_body or alias != receipt:
        raise pit.MarketMemoryStoreError("certified query/context alias mismatch")
    _policy(policy, "read_market_memory_lineage", _capture_resource(resource, clean))
    if _profile(reader) == pit.STORE_PROFILE:
        stored = pit._load_stored_from_receipt(reader.root, clean, store_id=membership.store_id, read_budget=budget)
        return stored, None
    return trusted._load_stored_with_feature(reader.root, clean, store_id=membership.store_id, read_budget=budget)


def _capture_resource(resource, receipt):
    return {**resource, "store_id": receipt["store_id"],
            "context_id": receipt["context_id"], "capture_id": receipt["capture_id"],
            "subject_id": receipt["subject"]["subject_id"],
            "source_receipt_ids": list(receipt["source_receipt_ids"]),
            "packet_sha256": receipt["packet_sha256"]}


def read_certified_generation(reader, *, generation_id, policy, expected_certificate_ref=None):
    resource = _resource(reader, generation_id)
    _policy(policy, "read_market_memory_lineage", resource)
    budget = _ReadBudget()
    membership, observed, pending = _membership(reader, generation_id, expected_certificate_ref, budget, policy=policy)
    generation = reader.read_certified_generation(membership, budget=budget, policy=policy)
    _policy(policy, "use_qualified_market_memory_lineage_certificate", membership.publication_resource)
    _policy(policy, "read_market_memory_lineage", resource)
    return {"assurance": ASSURANCE, "ancestor_live_reread": False, "state": "proof_pending" if pending else "certified",
            "certificate_id": membership.certificate["certificate_id"], "requested_generation": copy.deepcopy(membership.link),
            "generation": generation, "observed_source_head": observed, "input_bytes": budget.bytes}


def read_certified_capture(reader, *, generation_id, query_id, policy, expected_certificate_ref=None):
    resource = _resource(reader, generation_id, query_id)
    _policy(policy, "read_market_memory_lineage", resource)
    budget = _ReadBudget()
    membership, observed, pending = _membership(reader, generation_id, expected_certificate_ref, budget, policy=policy)
    _policy(policy, "read_market_memory_lineage", {**resource, "store_id": membership.store_id})
    stored, feature = reader.read_certified_capture(membership, query_id=query_id, budget=budget, policy=policy)
    actual_resource = _capture_resource(resource, stored.capture_receipt)
    _policy(policy, "use_qualified_market_memory_lineage_certificate", membership.publication_resource)
    _policy(policy, "read_market_memory_lineage", actual_resource)
    _policy(policy, "disclose_market_memory_capture", actual_resource)
    return {"assurance": ASSURANCE, "ancestor_live_reread": False, "state": "proof_pending" if pending else "certified",
            "certificate_id": membership.certificate["certificate_id"], "requested_generation": copy.deepcopy(membership.link),
            "stored": stored, "feature": feature, "observed_source_head": observed, "input_bytes": budget.bytes}
