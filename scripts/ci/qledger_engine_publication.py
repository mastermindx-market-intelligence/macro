"""Inactive complete engine-tree composition for explicitly ordered settled native originals.

Only a process-local original binding/write and its existing retained result are
accepted. Preparation writes unreferenced Git objects; it neither runs a producer
nor changes refs, index, checkout, budgets, selection or publication admission.
"""
from dataclasses import dataclass
import os
import sys
from pathlib import Path

# Ordinary file-path imports pin this source tree. In a qualified bootstrap,
# __file__ belongs to the verified outside-checkout bundle; the finite finder
# still refuses every unqualified first-party import.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from engine.qledger_original_result import OriginalResultClaimsBinding
from engine.qledger_store_protocol import SnapshotIntegrityError
from scripts.ci import qledger_conversion_candidate as candidate


def _require(value, message):
    if not value:
        raise SnapshotIntegrityError('ENGINE_PUBLICATION_UNPROVEN', message)


@dataclass(frozen=True)
class CompleteEnginePublication:
    source_candidate_oid: str
    tree_oid: str
    candidate_oid: str
    accepted_tip_oid: str
    accepted_ref: str
    original_manifest_digest: str
    _owner: object
    effect: str = 'unreferenced_git_objects_only'
    eligible_for_cutover: bool = False


class EnginePublicationInvocation:
    """Join actual full engine output to the existing native continuity API.

    An initial-conversion result, serialized admission or another process's
    binding is not this interface. The assigning bootstrap/controller must still
    qualify the process, original resources and ordinary same-origin push.
    """
    def __init__(self, binding, write, *, retained_original=None, original_writes=None):
        _require(type(binding) is OriginalResultClaimsBinding,
                 'exact process-local retained-original producer binding required')
        self.binding, self.write, self.retained = binding, write, retained_original
        self.writes = (write,) if original_writes is None else original_writes
        _require(type(self.writes) is tuple and self.writes and self.writes[-1] is write,
                 "explicit ordered chain must end with this original write")
        self.pid = binding.original_process_id
        checked = self._original()
        self.manifest_digest = checked.manifest_digest

    def _original(self):
        b = self.binding
        _require(os.getpid() == self.pid == b.original_process_id,
                 'original producer process differs; inherited evidence cannot transfer')
        _require(b.pre_attempt_failure is None, 'native producer has an unresolved pre-attempt failure')
        checked = b.read_original_write_chain(self.writes, retained_original=self.retained)
        _require(not hasattr(self, 'manifest_digest') or checked.manifest_digest == self.manifest_digest,
                 'original native retained result changed')
        return checked

    def _source(self, source, tree, tip, ref):
        p = candidate.publication
        for value in (source, tree, tip):
            p._oid(value)
        candidate._ref_matches(self.binding.repo_root, ref, tip)
        _require(p._commit_tree(self.binding.repo_root, source, limits=self.binding.limits) == tree,
                 'actual complete frozen engine tree differs')
        p._git(self.binding.repo_root, ['merge-base', '--is-ancestor', tip, source], output_limit=128)

    def prepare(self, *, source_candidate_oid, expected_tree_oid, accepted_tip_oid, accepted_ref):
        checked = self._original()
        self._source(source_candidate_oid, expected_tree_oid, accepted_tip_oid, accepted_ref)
        # Preserve EVERY entry in the incumbent's final tree, including its
        # render-sync output. This is a new private publication object, not a
        # rewrite of the source candidate or a claims-only substitute.
        payload = candidate._native_commit_bytes(expected_tree_oid, accepted_tip_oid,
            self.binding.operation_id, self.binding.lane_id, checked.commit_metadata)
        oid = candidate._write_git_object(self.binding.repo_root,
            ['hash-object', '-t', 'commit', '-w', '--stdin'], payload)
        _require(oid == candidate._commit_identity(payload, accepted_tip_oid), 'engine commit identity differs')
        prepared = CompleteEnginePublication(source_candidate_oid, expected_tree_oid, oid,
            accepted_tip_oid, accepted_ref, checked.manifest_digest, self)
        self.check(prepared)
        return prepared

    def check(self, prepared, *, push_args=None):
        _require(type(prepared) is CompleteEnginePublication and prepared._owner is self
                 and prepared.original_manifest_digest == self.manifest_digest,
                 'exact same-process complete engine preparation required')
        checked = self._original()
        self._source(prepared.source_candidate_oid, prepared.tree_oid,
                     prepared.accepted_tip_oid, prepared.accepted_ref)
        if push_args is not None:
            _require(tuple(push_args) == ('origin', prepared.candidate_oid + ':refs/heads/main'),
                     'engine push must name the immutable complete publication candidate')
        payload = candidate._native_commit_bytes(prepared.tree_oid, prepared.accepted_tip_oid,
            self.binding.operation_id, self.binding.lane_id, checked.commit_metadata)
        actual, _ = candidate.publication._git(self.binding.repo_root,
            ['cat-file', 'commit', prepared.candidate_oid], output_limit=4096)
        _require(actual == payload, 'engine publication metadata or full tree changed')
        binding, witness = self.binding.check_publication_candidate(self.write,
            candidate_oid=prepared.candidate_oid, expected_tree_oid=prepared.tree_oid,
            accepted_tip_oid=prepared.accepted_tip_oid, accepted_ref=prepared.accepted_ref,
            retained_original=self.retained)
        self._original()
        candidate._ref_matches(self.binding.repo_root, prepared.accepted_ref, prepared.accepted_tip_oid)
        return binding, witness
