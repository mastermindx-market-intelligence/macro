"""Explicit incumbent invocation of one retained initial conversion.

This is neither admission nor discovery. The assigning owner supplies the result
and digest. A live host gate must implement assert_valid/begin_install/
confirm_install/hold; no production issuer or serialized boolean is supplied here.
"""
from __future__ import annotations

from hashlib import sha256
from contextvars import ContextVar
import json
import os
import sys
from pathlib import Path

# Ordinary file-path imports pin this source tree. In a qualified bootstrap,
# __file__ belongs to the verified outside-checkout bundle; the finite finder
# still refuses every unqualified first-party import.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine import qledger_original_result as storage
from engine.qledger_original_conversion import (
    ConversionOwnerTarget, OriginalConversionIntent, OriginalConversionOwner,
)
from engine.qledger_store import ClaimsBindingScope, ClaimsReadScope
from engine.qledger_store_protocol import ProtocolLimits, SnapshotIntegrityError
from engine.qledger_store_sources import (
    LOCK_RELATIVE_PATH, LockedLocalSource, _absolute, claims_lock, verify_source_snapshot,
)
from scripts.ci import qledger_conversion_candidate as candidate
from scripts.ci import qledger_publication as publication


def _fail(message, code="OWNER_INVOCATION_UNPROVEN"):
    raise SnapshotIntegrityError(code, message)


_LIVE_PRODUCER = ContextVar("qledger_live_producer_invocation", default=None)


class _LiveProducerInvocation:
    """Live callback boundary only; never serializable admission or transfer."""
    def __init__(self, invocation, binding, gate, installed, budget, retention):
        self.invocation, self.binding, self.gate = invocation, binding, gate
        self.installed, self.budget, self.retention = installed, budget, retention
        self.pid, self.active = os.getpid(), True

    def check(self, phase):
        if (not self.active or _LIVE_PRODUCER.get() is not self
                or os.getpid() != self.pid or self.pid != self.binding.original_process_id):
            _fail("same-process live producer invocation is absent")
        return self.invocation._gate(self.gate, phase, self.installed,
            producer_binding=self.binding, budget_id=self.budget, retention_id=self.retention)

    def __reduce__(self):
        raise TypeError("live producer invocation cannot transfer")


def require_live_producer(binding):
    """Inspect the existing caller's active scope; this function cannot enter it."""
    live = _LIVE_PRODUCER.get()
    if type(live) is not _LiveProducerInvocation or live.binding is not binding:
        _fail("same-process live producer invocation is absent")
    live.check("engine-owner-entry")
    return live


def load_conversion(repo, *, result_path, manifest_digest):
    """Fresh restart readback from the explicit same path; never re-prepare."""
    repo, path = _absolute(repo), _absolute(result_path)
    publication._repo(repo)
    if type(manifest_digest) is not str or not storage._HASH.fullmatch(manifest_digest):
        _fail("explicit original manifest digest required")
    root_fd = result_fd = None
    try:
        root_fd = storage._owner(path.parent, path, path.name, repo / "data/qledger/claims.jsonl")
        result_fd = storage._open_child(root_fd, path.name)
        raw = storage._read(result_fd, "manifest.json", storage._manifest_bound(ProtocolLimits()), [])
        if sha256(raw).hexdigest() != manifest_digest:
            _fail("retained original manifest differs")
        doc = json.loads(raw)
        if storage._json(doc) != raw:
            _fail("original manifest must be canonical and unambiguous")
        target = dict(doc["target"])
        target["commit_metadata"] = candidate.CandidateCommitMetadata(**target["commit_metadata"])
        for name in ("owner_root", "result_path"):
            target[name] = Path(target[name])
        target = ConversionOwnerTarget(**target)
        if target.owner_root != path.parent or target.result_path != path or target.result_id != path.name:
            _fail("original result location differs from explicit invocation")
        owner = OriginalConversionOwner(repo, intent=OriginalConversionIntent(**doc["intent"]),
                                        target=target, limits=ProtocolLimits(**doc["limits"]))
        owner.readback(manifest_digest)
        return ConversionInvocation(owner, manifest_digest)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SnapshotIntegrityError("OWNER_INVOCATION_UNPROVEN", "original invocation readback failed") from exc
    finally:
        for fd in (result_fd, root_fd):
            if fd is not None:
                os.close(fd)


class ConversionInvocation:
    def __init__(self, owner, manifest_digest):
        if type(owner) is not OriginalConversionOwner:
            _fail("exact original conversion owner required")
        self.owner, self.manifest_digest = owner, manifest_digest

    def _git_oid(self, name):
        if name not in ("HEAD", "main", "refs/heads/main"):
            publication._oid(name)
        raw, _ = publication._git(self.owner.repo, ["rev-parse", "--verify", name + "^{commit}"],
                                  output_limit=128)
        oid = raw.strip().decode("ascii")
        publication._oid(oid)
        return oid

    def preflight(self, *, boundary, accepted_tip_oid, tree_oid=None, parent_oid=None,
                  candidate_oid=None, target_ref="refs/heads/main", push_args=()):
        owner = self.owner
        retained = owner.readback(self.manifest_digest)
        if target_ref != owner.target.target_ref:
            _fail("publication target differs from original binding")
        candidate._ref_matches(owner.repo, owner.target.accepted_ref, accepted_tip_oid)
        if boundary == "frozen-tree":
            if tree_oid is None or parent_oid is None:
                _fail("actual frozen tree and parent required")
            if parent_oid != accepted_tip_oid:
                _fail("initial conversion frozen parent differs from accepted tip")
            source_tree = publication._commit_tree(owner.repo, accepted_tip_oid, limits=owner.limits)
            publication.read_legacy_claims_blob(owner.repo, tree_oid=source_tree,
                expected_blob_oid=owner.target.legacy_blob_oid, limits=owner.limits)
            binding = publication.NativePublicationBinding(owner.intent.operation_id,
                owner.intent.lane_id, target_ref, accepted_tip_oid, retained.snapshot.receipt.root_digest)
            result = publication.check_frozen_tree(owner.repo, tree_oid=tree_oid,
                parent_commit_oid=parent_oid, accepted_baseline_oids=(accepted_tip_oid,),
                binding=binding, limits=owner.limits)
        elif boundary in ("pre-rebase", "publish-candidate"):
            if candidate_oid is None or tree_oid is None:
                _fail("incumbent's exact complete candidate and frozen tree required")
            publication._oid(candidate_oid)
            publication._oid(tree_oid)
            expected_tree = tree_oid
            if boundary == "publish-candidate":
                # No implicit upstream, force, deletion, options or multiple refspecs.
                if len(push_args) != 2 or push_args[0] != "origin":
                    _fail("native push requires the incumbent's one explicit origin/main refspec")
                spec = push_args[1]
                if spec == "main":
                    source, destination = "main", "refs/heads/main"
                elif type(spec) is str and spec.count(":") == 1:
                    source, destination = spec.split(":")
                else:
                    _fail("ambiguous native push refspec")
                if destination not in ("main", "refs/heads/main"):
                    _fail("native push targets a different ref")
                actual = self._git_oid(source)
                if candidate_oid is not None and candidate_oid != actual:
                    _fail("explicit candidate differs from actual push source")
                candidate_oid = actual
            tree_oid = publication._commit_tree(owner.repo, candidate_oid, limits=owner.limits)
            if tree_oid != expected_tree:
                _fail("actual candidate differs from incumbent's complete frozen tree")
            _, witness = owner.check_publication_candidate(expected_manifest_digest=self.manifest_digest,
                candidate_oid=candidate_oid, expected_tree_oid=tree_oid,
                accepted_tip_oid=accepted_tip_oid, accepted_ref=owner.target.accepted_ref)
            result = witness.publication
        else:
            _fail("unknown incumbent publication boundary")
        candidate._ref_matches(owner.repo, owner.target.accepted_ref, accepted_tip_oid)
        return result

    def invoke_reader(self, commit_oid, consumer, *args, **kwargs):
        binding = self.owner.read_binding(expected_manifest_digest=self.manifest_digest,
                                           commit_oid=commit_oid)
        with ClaimsBindingScope(binding), ClaimsReadScope(self.owner.repo):
            return consumer(*args, **kwargs)

    def _gate(self, gate, phase, commit_oid, *, producer_binding=None, budget_id=None, retention_id=None):
        if gate is None or type(gate) is bool:
            _fail("actual live exclusion/installation gate is absent", "ADMISSION_UNPROVEN")
        for name in ("assert_valid", "begin_install", "confirm_install", "hold"):
            if not callable(getattr(gate, name, None)):
                _fail("live owner gate is incomplete", "ADMISSION_UNPROVEN")
        context = dict(repo=self.owner.repo, operation_id=self.owner.intent.operation_id,
            budget_id=self.owner.target.budget_id, retention_id=self.owner.target.retention_id,
            commit_oid=commit_oid, phase=phase)
        if producer_binding is not None:
            for value in (budget_id, retention_id):
                if type(value) is not str or not publication._TAG.fullmatch(value):
                    _fail("explicit original producer budget and retention binding required")
            context.update(operation_id=producer_binding.operation_id,
                lane_id=producer_binding.lane_id, budget_id=budget_id, retention_id=retention_id)
        if gate.assert_valid(**context) is not None:
            _fail("an assertion, not a boolean admission claim, is required", "ADMISSION_UNPROVEN")
        return context

    def initial_checkout(self, *, gate, checkout, candidate_oid, expected_tree_oid, accepted_tip_oid):
        """Gate the existing checkout callback; never bootstrap BASE/ROOT directly.

        begin_install must durably hold the existing launcher before checkout.
        confirm_install must keep processes gated until explicit bindings are
        installed. No exception clears that hold or authorizes retry/rollback.
        """
        context = self._gate(gate, "initial-checkout", candidate_oid)
        retained = self.owner.readback(self.manifest_digest)
        self.preflight(boundary="pre-rebase", candidate_oid=candidate_oid,
                       tree_oid=expected_tree_oid, accepted_tip_oid=accepted_tip_oid)
        # Never overwrite a different accepted checkout, native generation,
        # dirty original tails or another incumbent's work.
        if self._git_oid("HEAD") != accepted_tip_oid:
            _fail("initial checkout differs from admitted accepted tip")
        from engine.qledger_store import _require_legacy_namespace
        _require_legacy_namespace(self.owner.claims_path)
        publication._git(self.owner.repo, ["diff", "--quiet", "--exit-code"], output_limit=4096)
        publication._git(self.owner.repo, ["diff", "--cached", "--quiet", "--exit-code"], output_limit=4096)
        try:
            gate.begin_install(**context)
            self._gate(gate, "initial-checkout", candidate_oid)
            checkout(candidate_oid)  # The incumbent supplies its existing checkout operation.
            self._gate(gate, "verify-installation", candidate_oid)
            if self._git_oid("HEAD") != candidate_oid:
                _fail("checkout did not install the exact candidate")
            publication._git(self.owner.repo, ["diff", "--quiet", "--exit-code", candidate_oid], output_limit=4096)
            with claims_lock(self.owner.repo / LOCK_RELATIVE_PATH, mode="exclusive", timeout=0) as lease:
                source = LockedLocalSource(self.owner.repo, lease=lease,
                    expected_root_digest=retained.snapshot.receipt.root_digest, limits=self.owner.limits)
                verify_source_snapshot(source, limits=self.owner.limits)
            self.owner.read_binding(expected_manifest_digest=self.manifest_digest, commit_oid=candidate_oid)
            self._gate(gate, "before-process-release", candidate_oid)
            gate.confirm_install(**context)
        except BaseException as exc:
            gate.hold(**context, cause=exc)
            raise  # No automatic restore, re-checkout or original-operation replay.
        return retained.snapshot.receipt.root_digest

    def invoke_producer(self, binding, *, gate, installed_commit_oid, budget_id, retention_id,
                        producer, args=(), kwargs=None):
        from engine.qledger_original_result import OriginalResultClaimsBinding
        if (type(binding) is not OriginalResultClaimsBinding or binding.repo_root != self.owner.repo
                or binding.limits != self.owner.limits):
            _fail("explicit retained-original producer binding required")
        context = self._gate(gate, "producer", installed_commit_oid, producer_binding=binding,
                             budget_id=budget_id, retention_id=retention_id)
        if self._git_oid("HEAD") != installed_commit_oid:
            _fail("producer version differs from admitted installation")
        try:
            failure_before = binding.pre_attempt_failure
            live = _LiveProducerInvocation(self, binding, gate, installed_commit_oid, budget_id, retention_id)
            token = _LIVE_PRODUCER.set(live)
            try:
                with ClaimsBindingScope(binding):
                    result = producer(*args, **(kwargs or {}))
            finally:
                live.active = False
                _LIVE_PRODUCER.reset(token)
            # Opening/admission/preparation can refuse before _begin creates an
            # attempt. A caught refusal must not look like legitimate no-write.
            if binding.pre_attempt_failure is not failure_before:
                _fail("producer returned after a native pre-attempt failure")
            # A producer must not swallow an unretained/failed storage attempt.
            latest = {}
            for attempt in binding.attempts:
                intent = attempt.write.intent
                if intent in latest and not binding._same_original_write(latest[intent].write, attempt.write):
                    _fail("producer replaced an original write during reconciliation")
                latest[intent] = attempt
            for attempt in latest.values():
                outcome = attempt.outcome
                if (outcome is None or outcome.status not in ("materialized", "noop", "already_applied")
                        or outcome.clock_status == "uncertain"):
                    _fail("producer returned with an unresolved original storage attempt")
            self._gate(gate, "producer-complete", installed_commit_oid, producer_binding=binding,
                       budget_id=budget_id, retention_id=retention_id)
            return result
        except BaseException as exc:
            gate.hold(**context, cause=exc)
            raise
