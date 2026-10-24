"""Partial production evidence for the existing retained-conversion HostGate.

The original publisher supplies its pre-push origin identity; this module reads
that same normal Git remote and validates the complete immutable candidate. It
never pushes, fetches, creates a reservation, infers retention or releases entry.
Unsupported host/resource assertions name the missing authority and refuse.
"""
from __future__ import annotations

from hashlib import sha256
import os
import sys
from pathlib import Path
import selectors
import subprocess
import tempfile
from urllib.parse import urlsplit
import time

# Ordinary file-path imports pin this source tree. In a qualified bootstrap,
# __file__ belongs to the verified outside-checkout bundle; the finite finder
# still refuses every unqualified first-party import.
_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT))

from scripts.ci.qledger_host_gate import GateRefusal
from scripts.ci.qledger_owner_invocation import load_conversion
from scripts.ci import qledger_publication as publication


class EvidenceUnavailable(GateRefusal):
    pass


def _require(value, message):
    if not value:
        raise EvidenceUnavailable(message)


class OrdinaryPublicationEvidence:
    """Real same-origin ref readback; no production admission is supplied.

    origin_binding_sha256 uses the incumbent normal-push identity convention:
    SHA256 of the single identical, Git-expanded fetch/push destination bytes.
    The assigning original owner must supply its existing pre-push binding.
    Capturing today's URL here would not prove that original identity.
    """
    def __init__(self, context, *, origin_binding_sha256):
        _require(type(origin_binding_sha256) is str and len(origin_binding_sha256) == 64
                 and all(x in '0123456789abcdef' for x in origin_binding_sha256),
                 'original normal-push origin binding required')
        self.context, self.origin_digest = context, origin_binding_sha256
        self._pid, self._last, self._failed = os.getpid(), time.monotonic_ns(), False
        _require(type(context.original_deadline_monotonic_ns) is int,
                 'original absolute monotonic endpoint required; wall-clock PUSH_DEADLINE is not that endpoint')
        self._check()
        self.invocation = load_conversion(context.repo, result_path=context.result_path,
                                          manifest_digest=context.manifest_digest)
        owner = self.invocation.owner
        _require((owner.target.owner_root, owner.intent.operation_id, owner.target.budget_id,
                  owner.target.retention_id) == (context.owner_root, context.operation_id,
                  context.budget_id, context.retention_id), 'retained original owner binding differs')
        self._check()

    def _check(self):
        now = time.monotonic_ns()
        self._failed = self._failed or now < self._last or now >= self.context.original_deadline_monotonic_ns
        self._last = max(now, self._last)
        _require(os.getpid() == self._pid and not self._failed,
                 'readback process changed or original endpoint is unavailable/expired')
        return (self.context.original_deadline_monotonic_ns - now) / 1_000_000_000

    def _bound(self, context):
        self._check()
        gate = context.get('gate')
        _require(gate is not None and gate.repo == self.context.repo
                 and gate.invocation.manifest_digest == self.context.manifest_digest
                 and gate.owner.target.result_path == self.context.result_path
                 and gate.candidate_oid == self.context.candidate_oid
                 and context.get('repo') == self.context.repo
                 and context.get('commit_oid') == self.context.candidate_oid
                 and context.get('operation_id') == self.context.operation_id
                 and context.get('budget_id') == self.context.budget_id
                 and context.get('retention_id') == self.context.retention_id
                 and context.get('lane_id') is None
                 and context.get('bootstrap_pid') == self._pid
                 and context.get('original_deadline_monotonic_ns') == self.context.original_deadline_monotonic_ns
                 and context.get('conversion_result_path') == self.context.result_path
                 and context.get('conversion_manifest_digest') == self.context.manifest_digest,
                 'original publication invocation binding differs')
        return gate

    def _git(self, args, maximum=4096, *, private_cwd=None):
        """One bounded read on the incumbent Git carrier; no raw output escapes."""
        self._check()
        env = dict(os.environ)
        # Inherited config parameters can redirect even a literal URL. Local
        # identity observations and the remote read share no injected Git state.
        env = {key: value for key, value in env.items() if not key.startswith('GIT_')}
        env.update(GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1', GIT_NO_REPLACE_OBJECTS='1',
                   GIT_TERMINAL_PROMPT='0', GIT_GRAFT_FILE=os.devnull)
        options = []
        directory = self.context.repo
        if private_cwd is not None:
            directory = private_cwd
            # No checkout discovery, system/global config, netrc, mutable URL
            # rewriting, credential helper, proxy or HTTP redirect may change
            # the destination actually read. Unsupported authentication refuses;
            # it is never recovered from mutable checkout credentials/config.
            env.update(HOME=str(directory), XDG_CONFIG_HOME=str(directory),
                       GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_SYSTEM=os.devnull,
                       GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_COUNT='0',
                       GIT_CEILING_DIRECTORIES=str(directory))
            for setting in ('protocol.allow=never', 'protocol.file.allow=always',
                            'protocol.https.allow=always', 'http.followRedirects=false',
                            'http.sslVerify=true', 'http.proxy=', 'credential.helper='):
                options += ['-c', setting]
        command = ['git', '--no-replace-objects', *options, '-C', str(directory), *args]
        try:
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, env=env)
        except OSError as exc:
            raise EvidenceUnavailable('normal publication readback could not start') from exc
        data = bytearray()
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(proc.stdout, selectors.EVENT_READ)
                while selector.get_map():
                    remaining = self._check()
                    ready = selector.select(min(remaining, 0.25))
                    self._check()
                    # A short select interval keeps the original sticky clock
                    # check live even when the remote sends no bytes.
                    for key, _ in ready:
                        chunk = os.read(key.fd, min(65536, maximum + 1 - len(data)))
                        if not chunk:
                            selector.unregister(key.fileobj)
                        else:
                            data.extend(chunk)
                            _require(len(data) <= maximum, 'normal publication output exceeded bound')
            try:
                code = proc.wait(timeout=self._check())
            except subprocess.TimeoutExpired as exc:
                raise EvidenceUnavailable('original publication readback budget expired') from exc
            _require(code == 0, 'normal publication ref readback is unavailable')
            self._check()
            return bytes(data)
        finally:
            if proc.poll() is None:
                proc.kill()  # Only this adapter's read-only Git child, never a writer/service.
                proc.wait()
            if proc.stdout is not None:
                proc.stdout.close()

    def _origin(self):
        fetch = self._git(['remote', 'get-url', '--all', 'origin']).splitlines()
        push = self._git(['remote', 'get-url', '--push', '--all', 'origin']).splitlines()
        _require(len(fetch) == 1 and fetch == push and fetch[0]
                 and sha256(fetch[0]).hexdigest() == self.origin_digest,
                 'original normal-push origin changed or is ambiguous')
        return fetch[0]

    def assert_publication_readback(self, **context):
        gate = self._bound(context)
        owner = self.invocation.owner
        _require(gate.accepted_tip_oid == owner.target.accepted_tip_oid,
                 'original accepted publication baseline differs')
        retained = owner.readback(self.context.manifest_digest)
        binding = publication.NativePublicationBinding(owner.intent.operation_id, owner.intent.lane_id,
            owner.target.target_ref, owner.target.accepted_tip_oid, retained.snapshot.receipt.root_digest)
        witness = publication.check_legacy_conversion_candidate(owner.repo,
            candidate_oid=gate.candidate_oid, accepted_baseline_oids=(owner.target.accepted_tip_oid,),
            target_ref=owner.target.target_ref, binding=binding,
            expected_legacy_blob_oid=owner.target.legacy_blob_oid,
            conversion_transaction_id=owner.intent.transaction_id, limits=owner.limits)
        _require(witness.publication.tree_oid == gate.tree_oid, 'complete publication tree differs')
        self._check()
        destination = self._origin().decode('utf-8', errors='strict')
        parsed = urlsplit(destination)
        _require((destination.startswith('/') and not parsed.scheme)
                 or (parsed.scheme == 'https' and parsed.hostname and not parsed.username
                     and not parsed.password and not parsed.query and not parsed.fragment),
                 'qualified publication transport requires absolute local path or credential-free HTTPS; bound authentication unavailable')
        # The literal expanded destination is checked above and read without
        # consulting the mutable checkout again. The second observation below
        # detects persistent carrier drift; it is not the query's identity proof.
        with tempfile.TemporaryDirectory(prefix='.qledger-ref-read-', dir=self.context.owner_root) as scratch:
            raw = self._git(['ls-remote', '--refs', '--exit-code', '--', destination,
                             owner.target.target_ref], private_cwd=scratch)
        self._origin()
        expected = (gate.candidate_oid + '\t' + owner.target.target_ref + '\n').encode('ascii')
        _require(raw == expected, 'exact full candidate is not confirmed at original publication ref')
        self._bound(context)

    def assert_resources(self, **context):
        self._check()
        raise EvidenceUnavailable('original ordinary push budget/process anchor and actual root retention/capacity policy unavailable; manifest labels and protocol limits are not those authorities')

    def assert_launcher_coverage(self, **context):
        self._check()
        raise EvidenceUnavailable('held complete new-entry/launcher exclusion authority unavailable')

    def assert_bootstrap_exclusion(self, **context):
        self._check()
        raise EvidenceUnavailable('original writer incarnations and pre-open claims FD settlement unavailable')

    def assert_descendants_settled(self, **context):
        self._check()
        raise EvidenceUnavailable('original known descendant/process-death settlement authority unavailable')

    def assert_process_version(self, **context):
        self._check()
        raise EvidenceUnavailable('actual loaded owner/runtime bundle and native process binding authority unavailable')


def build_evidence(context, *, origin_binding_sha256):
    """Owner-entry factory; the original origin pin identifies, never admits."""
    return OrdinaryPublicationEvidence(context, origin_binding_sha256=origin_binding_sha256)
