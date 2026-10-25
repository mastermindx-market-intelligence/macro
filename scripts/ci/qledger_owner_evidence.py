"""Partial production evidence for the existing retained-conversion HostGate.

The original publisher supplies its pre-push origin identity; this module reads
that same normal Git remote and validates the complete immutable candidate. It
never pushes, fetches, creates a reservation, infers retention or releases entry.
Unsupported host/resource assertions name the missing authority and refuse.
"""
from __future__ import annotations

from hashlib import sha256
from functools import wraps
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
from scripts.ci.qledger_owner_invocation import load_conversion, record_publication_assertion_refusal
from scripts.ci import qledger_publication as publication


class EvidenceUnavailable(GateRefusal):
    pass


def _require(value, message):
    if not value:
        raise EvidenceUnavailable(message)


def _record_original_refusal(method):
    @wraps(method)
    def guarded(self, **context):
        try:
            return method(self, **context)
        except BaseException as exc:
            # Includes missing/malformed context, early _check and even a wrong
            # dispatch branch; provider-local binding may not exist yet.
            record_publication_assertion_refusal(exc)
            raise
    return guarded


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
        self._native_readback_attempt = None  # One live original; never a restart/admission receipt.
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

    def _native_bound(self, context):
        _require(all(context.get(name) is not None for name in
                     ('native_checked', 'native_prepared', 'native_attempt')),
                 'actual typed live native invocation/preparation/original attempt required')
        # Native-only qualified dependencies; legacy conversion bundles keep
        # their original finite inventory. Static closure still follows these.
        from scripts.ci import qledger_engine_publication as native_engine
        from scripts.ci import qledger_engine_publisher as native_publisher
        self._check()
        checked, prepared, attempt = (context.get(name) for name in
            ('native_checked', 'native_prepared', 'native_attempt'))
        _require(type(checked) is native_engine._LiveFinalCandidate
                 and type(prepared) is native_engine.CompleteEnginePublication
                 and type(attempt) in (native_publisher._OriginalPublicationAttempt,
                                       native_publisher._HTTPSPublicationAttempt),
                 'actual typed live native invocation/preparation/original attempt required')
        _require(self._native_readback_attempt is None,
                 'original native readback already entered; uncertain response cannot be retried')
        self._native_readback_attempt = attempt
        gate, live, invocation = context.get('gate'), checked.live, checked.invocation
        _require(type(invocation) is native_engine.EnginePublicationInvocation
                 and gate is live.gate and live.invocation is gate.invocation
                 and gate.invocation.manifest_digest == self.context.manifest_digest
                 and gate.owner.target == self.invocation.owner.target
                 and gate.owner.intent == self.invocation.owner.intent
                 and gate.repo == self.context.repo == context.get('repo')
                 and gate.candidate_oid == self.context.candidate_oid == live.installed == context.get('commit_oid')
                 and checked.prepared is prepared and prepared._owner is invocation
                 and checked.publication_attempt is attempt and attempt.checked is checked
                 and attempt.prepared is prepared,
                 'native original differs from the live installed owner/candidate')
        _require(context.get('phase') in ('native-publication-readback', 'native-https-readback')
                 and context.get('bootstrap_pid') == os.getpid() == self._pid == invocation.pid == attempt.pid
                 and context.get('original_deadline_monotonic_ns') == self.context.original_deadline_monotonic_ns
                 and context.get('conversion_result_path') == self.context.result_path
                 and context.get('conversion_manifest_digest') == self.context.manifest_digest,
                 'native readback creator or original bootstrap endpoint differs')
        binding = invocation.binding
        _require((context.get('operation_id'), context.get('lane_id')) == (binding.operation_id, binding.lane_id)
                 and (context.get('budget_id'), context.get('retention_id')) == (live.budget, live.retention)
                 and gate.producers.get((binding.operation_id, binding.lane_id)) == (live.budget, live.retention)
                 and context.get('publication_candidate_oid') == prepared.candidate_oid
                 and context.get('publication_tree_oid') == prepared.tree_oid
                 and context.get('original_manifest_digest') == prepared.original_manifest_digest == invocation.manifest_digest
                 and context.get('origin_binding_sha256') == self.origin_digest == attempt.origin_digest
                 and (context.get('original_attempt'), context.get('original_max_attempts'), context.get('original_alarm_seconds'))
                     == (attempt.ordinal, attempt.maximum, attempt.alarm),
                 'native original resources, chain, full tree or original transport differs')
        checked._check()
        native_binding, witness = invocation.check(prepared)
        _require(witness.publication.candidate_oid == prepared.candidate_oid
                 and witness.publication.tree_oid == prepared.tree_oid
                 and native_binding.expected_root_digest == invocation.write.plan.snapshot.receipt.root_digest
                 and native_binding.accepted_tip_oid == prepared.accepted_tip_oid
                 and native_binding.target_ref == witness.publication.target_ref
                     == self.invocation.owner.target.target_ref == 'refs/heads/main',
                 'complete immutable native publication differs')
        return checked, prepared, attempt

    def _assert_native_publication_readback(self, context):
        checked, prepared, attempt = self._native_bound(context)
        from scripts.ci import qledger_engine_publisher as native_publisher
        response = attempt.push_response
        _require(attempt.effect_started and attempt.push_process is not None
                 and attempt.push_process.returncode == 0
                 and type(response) is tuple and len(response) == 3 and response[2] == 0,
                 'actual original successful Git response unavailable; matching ref cannot settle it')
        if type(attempt) is native_publisher._HTTPSPublicationAttempt:
            native_publisher._require_https_update_ack(response[0], destination=attempt.carrier.destination,
                candidate_oid=prepared.candidate_oid, accepted_tip_oid=prepared.accepted_tip_oid)
            expected = (prepared.candidate_oid + '\trefs/heads/main\n').encode()
        else:
            _require(attempt.origin_ref_installed and response[0] == b'objects-ready\n',
                     'original local object ingestion and ref CAS unproven')
            expected = (prepared.candidate_oid + '\n').encode()
        _require(attempt.last_response == (expected, b'', 0),
                 'known original candidate readback unavailable; no lost-response substitution')
        # Full immutable candidate/chain proof was checked above. Recheck
        # the live transport/root without repeating that same whole proof.
        attempt.check()
        attempt.readback(prepared.candidate_oid)
        checked._check()
        for write in checked.invocation.writes:
            checked.invocation.binding._settled(write)
        self._check()

    def _assert_native_reader(self, context):
        from scripts.ci.qledger_owner_invocation import NativeReaderInvocation
        call = context.get('native_reader')
        _require(type(call) is NativeReaderInvocation, 'actual fresh native reader invocation required')
        self._check();call.check()
        gate=call.gate
        _require(context.get('gate') is gate and gate.repo == self.context.repo
                 and gate.invocation.manifest_digest == self.context.manifest_digest
                 and gate.candidate_oid == self.context.candidate_oid
                 and call.pid == self._pid == os.getpid()
                 and call.deadline == self.context.original_deadline_monotonic_ns
                 and all(context.get(k) == v for k,v in call.context.items()),
                 'original native reader process/resources/code binding differs')
        _require(gate._native_expected == call.record and call.binding.commit_oid == call.record['candidate']
                 and call.binding.tree_oid == call.record['tree']
                 and call.binding.read_snapshot().receipt.root_digest == call.record['root'],
                 'actual immutable native reader generation differs')
        self._native_origin_readback(call.record,call.check)

    def _native_origin_readback(self,record,check):
        self._check();check()
        _require(record['publication']['origin'] == self.origin_digest, 'reader original publication origin differs')
        destination=self._origin().decode('utf-8',errors='strict')
        parsed=urlsplit(destination)
        expected=(record['candidate']+'\n').encode()
        if destination.startswith('/') and not parsed.scheme:
            from scripts.ci.qledger_host_gate import _directory
            import stat
            root=refs=heads=fd=None
            try:
                root=_directory(Path(destination))
                refs=os.open('refs',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=root)
                heads=os.open('heads',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=refs)
                _require(record['publication']['transport'] == 'local_objects_and_loose_ref_cas'
                         and [[os.fstat(h).st_dev,os.fstat(h).st_ino] for h in (root,refs,heads)]
                             == record['publication']['layout'], 'reader original ref namespace differs')
                fd=os.open('main',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=heads)
                before=os.fstat(fd)
                _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size == 41,
                         'reader original direct loose ref required')
                raw=os.read(fd,42)
                after=os.fstat(fd)
                _require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)
                         == (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
                         and raw == expected
                         and (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)
                             == (lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns))(
                                 os.stat('main',dir_fd=heads,follow_symlinks=False)),
                         'native reader original ref differs')
                _require((os.fstat(refs).st_dev,os.fstat(refs).st_ino)
                         == (os.stat('refs',dir_fd=root,follow_symlinks=False).st_dev,os.stat('refs',dir_fd=root,follow_symlinks=False).st_ino)
                         and (os.fstat(heads).st_dev,os.fstat(heads).st_ino)
                         == (os.stat('heads',dir_fd=refs,follow_symlinks=False).st_dev,os.stat('heads',dir_fd=refs,follow_symlinks=False).st_ino),
                         'reader ref namespace changed')
                _require((os.fstat(root).st_dev,os.fstat(root).st_ino)
                         == (os.stat(destination,follow_symlinks=False).st_dev,os.stat(destination,follow_symlinks=False).st_ino),
                         'reader original endpoint changed')
            finally:
                for handle in (fd,heads,refs,root):
                    if handle is not None:os.close(handle)
        else:
            raise EvidenceUnavailable('fresh native HTTPS/SSH reader carrier is not qualified; original writer auth cannot transfer')
        self._origin();check();self._check()

    def _assert_native_anchor(self,context):
        from scripts.ci.qledger_owner_invocation import _LiveProducerInvocation,require_live_producer
        from scripts.ci.qledger_host_gate import HostGate
        live=context.get('native_anchor')
        _require(type(live) is _LiveProducerInvocation and require_live_producer(live.binding) is live,
                 'actual new original data-anchor invocation required')
        self._check();gate=live.gate
        _require(type(gate) is HostGate and gate._native_anchor_live is live
                 and gate._native_owner_binding is live.binding and gate._mode=='install'
                 and gate.repo==self.context.repo and gate.candidate_oid==self.context.candidate_oid
                 and gate.invocation.manifest_digest==self.context.manifest_digest
                 and live.pid==self._pid==os.getpid()
                 and live.data_anchor_deadline==self.context.original_deadline_monotonic_ns
                 and all(context.get(k)==v for k,v in gate._anchor_context(live).items()),
                 'original data-anchor process/resources/code binding differs')
        record=gate._native_start_generation
        _require(record is not None and gate._native_expected==record,'current verified data generation absent')
        self._native_origin_readback(record,lambda:gate._anchor_check(live))

    @_record_original_refusal
    def assert_publication_readback(self, **context):
        if context.get('phase')=='native-anchor-readback' or 'native_anchor' in context:
            return self._assert_native_anchor(context)
        if context.get('phase') == 'native-reader' or 'native_reader' in context:
            return self._assert_native_reader(context)
        if context.get('phase') in ('native-publication-readback', 'native-https-readback') or any(
                name in context for name in ('native_checked', 'native_prepared', 'native_attempt')):
            try:
                return self._assert_native_publication_readback(context)
            except BaseException as exc:
                attempt = self._native_readback_attempt
                checked = context.get('native_checked')
                if (attempt is not None and attempt is context.get('native_attempt')
                        and attempt.checked is checked and checked.active and not attempt.confirmed):
                    checked.failure = checked.failure or exc
                    attempt.uncertain = True
                raise
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
