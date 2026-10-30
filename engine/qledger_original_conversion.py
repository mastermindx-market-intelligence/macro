"""Inactive initial-conversion owner using the existing original-result store.

This retains a genuine legacy conversion, never a fictitious native write.
No installer, ref update, producer, clock, discovery or production selection is
provided. Labels bind caller-supplied budget/retention context; they do not prove
admission, retention policy, legacy-writer exclusion or atomic installation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
from types import MappingProxyType

from engine import qledger_original_result as storage
from engine.qledger_store import NativeGitClaimsBinding
from engine.qledger_store_protocol import (
    ROOT_PATH, InMemorySource, ProtocolLimits, SnapshotIntegrityError, decode_root,
    open_logical_bytes, validate_publication, verify_snapshot,
)
from engine.qledger_store_sources import (
    GitTreeSource, _absolute, _check_git_hash, _file_identity, _member_limit,
    read_legacy_claims_blob, verify_source_snapshot,
)
from scripts.ci import qledger_conversion_candidate as candidate

_SCHEMA = "qledger-original-conversion/v1"
_TAG = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")
_SEAL = object()


def _fail(message):
    raise SnapshotIntegrityError("ORIGINAL_CONVERSION_UNPROVEN", message)


@dataclass(frozen=True)
class OriginalConversionIntent:
    operation_id: str
    lane_id: str
    transaction_id: str

    def __post_init__(self):
        for value in (self.operation_id, self.lane_id, self.transaction_id):
            if type(value) is not str or not _TAG.fullmatch(value):
                _fail("explicit stable conversion identity required")


@dataclass(frozen=True)
class ConversionOwnerTarget:
    owner_root: Path
    result_path: Path
    result_id: str
    accepted_tip_oid: str
    accepted_ref: str
    legacy_blob_oid: str
    commit_metadata: candidate.CandidateCommitMetadata
    budget_id: str
    retention_id: str
    target_ref: str = "refs/heads/main"


@dataclass(frozen=True)
class PreparedOriginalConversion:
    manifest_bytes: bytes
    manifest_digest: str
    objects: object
    candidate: candidate.PreparedConversionCandidate
    _seal: object


@dataclass(frozen=True)
class RetainedOriginalConversion:
    manifest_digest: str
    intent: OriginalConversionIntent
    target: ConversionOwnerTarget
    limits: ProtocolLimits
    source_bytes: bytes
    snapshot: object
    candidate_oid: str
    tree_oid: str
    eligible_for_cutover: bool = False
    source_scope: str = "ACCEPTED_PREFIX_ONLY"

    def require_complete_current_generation(self):
        """Restart readback is exact prefix evidence, never a live source cut."""
        candidate.require_complete_authority_generation(candidate.AcceptedPrefixQualification(
            accepted_tip_oid=self.target.accepted_tip_oid,
            accepted_ref=self.target.accepted_ref,
            source_blob_oid=self.target.legacy_blob_oid,
            source_logical_sha256=sha256(self.source_bytes).hexdigest(),
            source_byte_count=len(self.source_bytes),
        ))


class OriginalConversionOwner:
    """One explicit conversion/result location; no apply or enrollment API."""

    def __init__(self, repo, *, intent, target, limits):
        repo = _absolute(repo)
        candidate.publication._repo(repo)
        candidate.publication._profile(limits)
        if type(intent) is not OriginalConversionIntent or type(target) is not ConversionOwnerTarget:
            _fail("exact conversion intent and owner target required")
        intent.__post_init__()
        for value in (target.budget_id, target.retention_id):
            if type(value) is not str or not _TAG.fullmatch(value):
                _fail("explicit original budget and retention binding required")
        owner_root, result_path = _absolute(target.owner_root), _absolute(target.result_path)
        if (result_path.parent != owner_root or result_path.name != target.result_id
                or type(target.result_id) is not str or not storage._RESULT_ID.fullmatch(target.result_id)
                or owner_root.is_relative_to(repo)
                or type(target.accepted_ref) is not str or not target.accepted_ref.startswith("refs/")
                or target.target_ref != "refs/heads/main"
                or type(target.commit_metadata) is not candidate.CandidateCommitMetadata):
            _fail("invalid explicit conversion source, location or metadata")
        target.commit_metadata.git_identity()
        candidate.publication._oid(target.legacy_blob_oid)
        candidate.publication._native_binding(candidate.publication.NativePublicationBinding(
            intent.operation_id, intent.lane_id, target.target_ref, target.accepted_tip_oid, "0" * 64))
        self.repo, self.intent, self.target, self.limits = repo, intent, target, limits

    @property
    def claims_path(self):
        return self.repo / "data/qledger/claims.jsonl"

    def _context(self):
        target = asdict(self.target)
        for key in ("owner_root", "result_path"):
            target[key] = str(target[key])
        return {"schema": _SCHEMA, "claims_path": str(self.claims_path),
                "intent": asdict(self.intent), "target": target, "limits": asdict(self.limits)}

    def _commit_bytes(self, tree):
        identity = self.target.commit_metadata.git_identity()
        return (f"tree {tree}\nparent {self.target.accepted_tip_oid}\n"
                f"author {identity}\ncommitter {identity}\n\nQLedger conversion candidate "
                f"{self.intent.operation_id} {self.intent.transaction_id}\n").encode("ascii")

    def prepare(self):
        """Prepare immutable Git objects and original inputs; never install them."""
        t, i, limits = self.target, self.intent, self.limits
        prepared = candidate.prepare_legacy_conversion_candidate(self.repo,
            accepted_tip_oid=t.accepted_tip_oid, accepted_ref=t.accepted_ref,
            expected_legacy_blob_oid=t.legacy_blob_oid, transaction_id=i.transaction_id,
            operation_id=i.operation_id, lane_id=i.lane_id, commit_metadata=t.commit_metadata,
            limits=limits)
        source_tree = candidate.publication._commit_tree(self.repo, t.accepted_tip_oid, limits=limits)
        original = read_legacy_claims_blob(self.repo, tree_oid=source_tree,
                                          expected_blob_oid=t.legacy_blob_oid, limits=limits)
        snapshot = verify_source_snapshot(GitTreeSource(self.repo, tree_oid=prepared.tree_oid,
                                                        limits=limits), limits=limits)
        commit, _ = candidate.publication._git(self.repo, ["cat-file", "commit", prepared.candidate_oid],
                                               output_limit=4096)
        objects = {}

        def store(payload):
            digest = sha256(payload).hexdigest()
            if digest in objects and objects[digest] != payload:
                _fail("conversion object digest collision")
            objects[digest] = payload
            return digest

        manifest = {**self._context(),
            "source": {"object": store(original.raw_bytes), "bytes": original.byte_count},
            "snapshot": {"root": store(snapshot.root_bytes),
                         "members": {path: store(payload) for path, payload in snapshot._members.items()}},
            "git": {"candidate_oid": prepared.candidate_oid, "tree_oid": prepared.tree_oid,
                    "commit": store(commit)}}
        raw = storage._json(manifest)
        if (len(raw) > storage._manifest_bound(limits) or len(objects) > limits.snapshot_members
                or len(raw) + sum(map(len, objects.values())) > limits.snapshot_bytes):
            _fail("conversion inputs and manifest exceed the existing retention budget")
        digest = sha256(raw).hexdigest()
        self._verify(raw, objects, digest)
        candidate._ref_matches(self.repo, t.accepted_ref, t.accepted_tip_oid)
        return PreparedOriginalConversion(raw, digest, MappingProxyType(objects), prepared, _SEAL)

    def _manifest(self, raw, expected_digest):
        if (type(expected_digest) is not str or not storage._HASH.fullmatch(expected_digest)
                or sha256(raw).hexdigest() != expected_digest):
            _fail("conversion manifest differs from explicit immutable identity")
        manifest = json.loads(raw)
        context = self._context()
        if (type(manifest) is not dict or storage._json(manifest) != raw
                or set(manifest) != set(context) | {"source", "snapshot", "git"}
                or any(manifest[k] != v for k, v in context.items())):
            _fail("foreign or noncanonical conversion manifest")
        return manifest

    def _references(self, manifest):
        source, snapshot, git = (manifest[k] for k in ("source", "snapshot", "git"))
        if (type(source) is not dict or set(source) != {"object", "bytes"}
                or type(source["bytes"]) is not int or not 0 < source["bytes"] <= self.limits.logical_bytes
                or type(snapshot) is not dict or set(snapshot) != {"root", "members"}
                or type(snapshot["members"]) is not dict
                or len(snapshot["members"]) > self.limits.snapshot_members
                or type(git) is not dict or set(git) != {"candidate_oid", "tree_oid", "commit"}):
            _fail("malformed conversion object descriptors")
        refs = {}

        def reference(digest, maximum):
            if type(digest) is not str or not storage._HASH.fullmatch(digest):
                _fail("malformed conversion object digest")
            refs[digest] = min(refs.get(digest, maximum), maximum)

        reference(source["object"], min(source["bytes"], self.limits.snapshot_bytes))
        reference(snapshot["root"], self.limits.root_bytes)
        for path, digest in snapshot["members"].items():
            reference(digest, _member_limit(path, self.limits))
        reference(git["commit"], 4096)
        return refs

    def _verify(self, raw, objects, digest):
        manifest = self._manifest(raw, digest)
        refs = self._references(manifest)
        if (set(objects) != set(refs) or len(objects) > self.limits.snapshot_members
                or any(type(v) is not bytes for v in objects.values())
                or len(raw) + sum(map(len, objects.values())) > self.limits.snapshot_bytes
                or any(len(v) > refs[k] or sha256(v).hexdigest() != k
                       for k, v in objects.items())):
            _fail("incomplete, oversized or changed conversion objects")
        original = objects[manifest["source"]["object"]]
        if len(original) != manifest["source"]["bytes"] or not original.endswith(b"\n"):
            _fail("conversion source length or final LF changed")
        _check_git_hash("blob", original, self.target.legacy_blob_oid)
        desc = manifest["snapshot"]
        members = {path: objects[value] for path, value in desc["members"].items()}
        source = InMemorySource({**members, ROOT_PATH: objects[desc["root"]]},
                                snapshot_id="original-conversion:" + digest)
        snapshot = verify_snapshot(source, decode_root(objects[desc["root"]], limits=self.limits),
                                   limits=self.limits)
        if set(snapshot._members) != set(members):
            _fail("conversion contains unreferenced native members")
        validate_publication(source, snapshot.root, (), limits=self.limits)
        transactions = snapshot._transactions
        if (snapshot.root.base.size != 0 or len(transactions) != 1
                or transactions[0].kind != "append"
                or transactions[0].transaction_id != self.intent.transaction_id
                or snapshot.root.logical_size != len(original)
                or snapshot.root.logical_digest != sha256(original).hexdigest()):
            _fail("conversion is not the complete original source and one declared append")
        offset, view = 0, memoryview(original)
        with open_logical_bytes(snapshot) as stream:
            while chunk := stream.read(65536):
                if chunk != view[offset:offset + len(chunk)]:
                    _fail("conversion changed ordered original bytes")
                offset += len(chunk)
        if offset != len(original):
            _fail("conversion omitted original bytes")
        git = manifest["git"]
        candidate.publication._oid(git["tree_oid"])
        commit = self._commit_bytes(git["tree_oid"])
        if (objects[git["commit"]] != commit
                or candidate._commit_identity(commit, self.target.accepted_tip_oid) != git["candidate_oid"]):
            _fail("conversion Git identity differs from its fixed original metadata")
        return RetainedOriginalConversion(digest, self.intent, self.target, self.limits,
                                           original, snapshot, git["candidate_oid"], git["tree_oid"])

    def retain(self, prepared):
        """Install once through the existing store; same-path readback only."""
        if type(prepared) is not PreparedOriginalConversion or prepared._seal is not _SEAL:
            _fail("explicit prepared original conversion required")
        self._verify(prepared.manifest_bytes, prepared.objects, prepared.manifest_digest)
        t = self.target
        root_fd = result_fd = members_fd = None
        try:
            root_fd = storage._owner(t.owner_root, t.result_path, t.result_id, self.claims_path)
            os.mkdir(t.result_path.name, 0o700, dir_fd=root_fd)
            result_fd = storage._open_child(root_fd, t.result_path.name)
            storage._sync_dir(root_fd)
            os.mkdir("members", 0o700, dir_fd=result_fd)
            members_fd = storage._open_child(result_fd, "members")
            for digest, payload in prepared.objects.items():
                storage._write(members_fd, digest, payload)
            storage._sync_dir(members_fd)
            storage._write(result_fd, "manifest.json", prepared.manifest_bytes)
            storage._sync_dir(result_fd)
            storage._same(root_fd, t.result_path.name, result_fd)
            storage._stable_owner(t.owner_root, root_fd)
            storage._sync_dir(root_fd)
        except (OSError, ValueError, TypeError) as exc:
            raise SnapshotIntegrityError("ORIGINAL_CONVERSION_UNPROVEN",
                                         "conversion retention unproven; preserve the exact path") from exc
        finally:
            for fd in (members_fd, result_fd, root_fd):
                if fd is not None:
                    os.close(fd)
        return self.readback(prepared.manifest_digest)

    def readback(self, expected_manifest_digest):
        """Bounded restart readback, without Git or a replacement operation."""
        t, limits = self.target, self.limits
        root_fd = result_fd = members_fd = None
        identities = []
        try:
            root_fd = storage._owner(t.owner_root, t.result_path, t.result_id, self.claims_path)
            result_fd = storage._open_child(root_fd, t.result_path.name)
            if storage._entries(result_fd, 2) != {"members", "manifest.json"}:
                _fail("incomplete conversion result")
            raw = storage._read(result_fd, "manifest.json", storage._manifest_bound(limits), identities)
            refs = self._references(self._manifest(raw, expected_manifest_digest))
            members_fd = storage._open_child(result_fd, "members")
            if storage._entries(members_fd, limits.snapshot_members) != set(refs):
                _fail("incomplete or unexpected conversion object inventory")
            remaining, objects = limits.snapshot_bytes - len(raw), {}
            for digest, maximum in refs.items():
                payload = storage._read(members_fd, digest, min(maximum, remaining), identities)
                remaining -= len(payload)
                objects[digest] = payload
            retained = self._verify(raw, objects, expected_manifest_digest)
            for fd in (members_fd, result_fd, root_fd):
                storage._sync_dir(fd)
            for parent, name, identity in identities:
                if _file_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != identity:
                    _fail("conversion result changed after verification")
            if storage._entries(members_fd, limits.snapshot_members) != set(refs):
                _fail("conversion inventory changed after verification")
            storage._same(result_fd, "members", members_fd)
            storage._same(root_fd, t.result_path.name, result_fd)
            storage._stable_owner(t.owner_root, root_fd)
            return retained
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            raise SnapshotIntegrityError("ORIGINAL_CONVERSION_UNPROVEN",
                                         "conversion readback unproven; no cutover admitted") from exc
        finally:
            for fd in (members_fd, result_fd, root_fd):
                if fd is not None:
                    os.close(fd)

    def check_publication_candidate(self, *, expected_manifest_digest, candidate_oid,
                                    expected_tree_oid, accepted_tip_oid, accepted_ref):
        """Check the incumbent's complete frozen output; never substitute a tree."""
        retained = self.readback(expected_manifest_digest)
        if accepted_ref != self.target.accepted_ref:
            _fail("publication changed the original named accepted reference")
        candidate._ref_matches(self.repo, accepted_ref, accepted_tip_oid)
        if candidate.publication._commit_tree(self.repo, candidate_oid, limits=self.limits) != expected_tree_oid:
            _fail("actual publication differs from the incumbent's complete frozen tree")
        binding = candidate.publication.NativePublicationBinding(self.intent.operation_id,
            self.intent.lane_id, self.target.target_ref, accepted_tip_oid, retained.snapshot.receipt.root_digest)
        witness = candidate.publication.check_legacy_conversion_candidate(self.repo,
            candidate_oid=candidate_oid, accepted_baseline_oids=(accepted_tip_oid,),
            target_ref=self.target.target_ref, binding=binding,
            expected_legacy_blob_oid=self.target.legacy_blob_oid,
            conversion_transaction_id=self.intent.transaction_id, limits=self.limits)
        candidate._ref_matches(self.repo, accepted_ref, accepted_tip_oid)
        return binding, witness

    def read_binding(self, *, expected_manifest_digest, commit_oid, require_complete_current=False):
        """Historical immutable binding. Current complete authority remains unproven."""
        if type(require_complete_current) is not bool:
            raise SnapshotIntegrityError("PUBLICATION_INPUT", "current-generation request must be a boolean")
        retained = self.readback(expected_manifest_digest)
        if require_complete_current:
            retained.require_complete_current_generation()
        return NativeGitClaimsBinding(self.repo, commit_oid=commit_oid,
            expected_root_digest=retained.snapshot.receipt.root_digest, limits=self.limits)
