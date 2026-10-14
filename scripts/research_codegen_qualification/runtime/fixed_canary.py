"""One commissioned trusted probe, not candidate activation or a scheduler.

No command-line execution entry point. The hash-verified bootstrap is the only
production caller. Every physical dependency remains the fixed reviewed source.
"""
import hashlib
import json
import os
from pathlib import Path
import time

from phase_budget import QualificationBudget, PHASE_ORDER, BudgetRefused

ROOT = '01a1333c-a475-7052-95a8-72a88eb8c17b'
OPERATION = 'rf-fixed-smoke-runsc-01a1333c-v4'
BASE = Path('/var/lib/mastermind/rf-canary-01a1333c-v4')
FINAL_HEADROOM = 2048


class CanaryRefused(ValueError):
    pass


def raw(doc):
    return json.dumps(doc, sort_keys=True, separators=(',', ':'),
                      allow_nan=False, ensure_ascii=True).encode('ascii')


def digest(doc):
    return hashlib.sha256(raw(doc)).hexdigest()


def retain_after_attempt(action, retain, report):
    """Preserve the original attempt failure if partial accounting also fails."""
    try:
        value = action()
    except BaseException as original:
        try:
            retain()
        except Exception as accounting:
            report.doc['capture_retention_failure_type'] = type(accounting).__name__
            report.doc['original_attempt_failure_type'] = type(original).__name__
        raise
    retain()
    return value


class Report:
    """Retain partial observations before budget/refusal exceptions propagate."""
    def __init__(self, budget, commission):
        self.budget = budget
        self.raw_bytes = 0
        self.accounted_metadata = 0
        self.doc = {'schema': 'rf.fixed_canary.v1', 'root': ROOT,
                    'operation': OPERATION, 'commission_sha256': commission,
                    'status': 'INCOMPLETE', 'completed_phases': [],
                    'observations': {}, 'candidate_admission': False,
                    'containment_qualified': False}

    def sync(self):
        size = len(raw(self.doc))
        if size + self.raw_bytes + FINAL_HEADROOM > 65536:
            raise CanaryRefused('return_envelope_headroom')
        delta = max(0, size - self.accounted_metadata)
        self.budget.charge_metadata(delta)
        self.accounted_metadata += delta

    def observe(self, key, doc, captured=0):
        if key in self.doc['observations']:
            raise CanaryRefused('duplicate_observation')
        if type(captured) is not int or captured < 0:
            raise CanaryRefused('invalid_capture_count')
        # Save the actual capture even if its late arrival freezes the budget.
        self.doc['observations'][key] = doc
        self.raw_bytes += captured
        self.budget.charge_raw(captured)
        self.sync()

    def seal(self, failure=None):
        if failure is not None:
            self.doc.update(status='STOPPED_NO_RETRY', failure_type=type(failure).__name__)
        else:
            self.doc['status'] = 'FIXED_SMOKE_PASSED'
        self.doc['captured_raw_bytes'] = self.raw_bytes
        self.doc['budget'] = self.budget.snapshot()._asdict()
        body = raw(self.doc)
        if len(body) + self.raw_bytes > 65536:
            # No success with a missing evidence return, and no new filesystem
            # write after refusal. Preserve identity and hashes on stdout only.
            self.doc = {'schema': 'rf.fixed_canary.v1', 'root': ROOT,
                        'operation': OPERATION, 'status': 'EVIDENCE_RETURN_OVERFLOW',
                        'full_report_sha256': hashlib.sha256(body).hexdigest(),
                        'captured_raw_bytes': self.raw_bytes,
                        'completed_phases': self.doc['completed_phases'],
                        'candidate_admission': False, 'containment_qualified': False}
        return self.doc


def sequence(actions, budget, commission):
    """Fixed five phases; injected actions exist only for hermetic join tests."""
    if set(actions) != set(PHASE_ORDER):
        raise CanaryRefused('phase_set')
    report = Report(budget, commission)
    try:
        report.sync()
        for name in PHASE_ORDER:
            grant = budget.begin(name)
            report.sync()
            # Existing audited helpers own fixed 16KiB envelopes. Do not shrink
            # cleanup reserves or grant an extra pool when the total is smaller.
            if name != 'archive' and grant.raw_allowance < 16384:
                raise CanaryRefused('remaining_phase_envelope')
            if actions[name](grant, report) is not True:
                raise CanaryRefused('phase_not_confirmed')
            budget.finish(name, True)
            report.doc['completed_phases'].append(name)
            report.sync()
        return report.seal()
    except Exception as exc:
        try:
            active = budget.snapshot().activephase
            if active is not None:
                budget.finish(active, False)
        except BudgetRefused:
            pass
        return report.seal(exc)


def execute(source_dir, work_dir, budget, commission, *, clock=time.monotonic):
    """Production path; no host, image, runtime, command or path override."""
    if (Path(source_dir) != BASE / 'source' or Path(work_dir) != BASE / 'work'
            or os.geteuid() != 0 or type(commission) is not str
            or len(commission) != 64 or any(c not in '0123456789abcdef' for c in commission)):
        raise CanaryRefused('bootstrap_identity')
    import runsc_install as install
    import cli29_anonymous_config as cli
    import pinned_archive_phase as archive
    import fixed_image_phase as image
    import qualification_manifest as projection
    import qualification_smoke as smoke
    import qualification_runsc_smoke as runsc

    source, work = Path(source_dir), Path(work_dir)
    state = {}

    def checkpoint(grant):
        if clock() >= grant.deadline or budget.snapshot().frozen:
            raise CanaryRefused('phase_deadline')

    def private_doc(name, doc, grant):
        checkpoint(grant)
        data = raw(doc)
        path = work / name
        install.write_private_file(str(path), data, 0o600, (0, 0), os.chown,
                                   checkpoint=lambda: checkpoint(grant))
        checkpoint(grant)
        if install.read_regular_bounded(str(path), len(data)) != data:
            raise CanaryRefused('private_receipt_readback')
        return str(path), hashlib.sha256(data).hexdigest()

    def cli_phase(grant, report):
        checkpoint(grant)
        doc = cli.execute(str(work), absolute_deadline=grant.deadline, raw_cap=grant.raw_allowance)
        report.observe('cli', doc, doc['raw_output_bytes'])
        return doc['status'] == 'PASS'

    def archive_phase(grant, report):
        state['archive'] = archive.acquire(str(work), grant.deadline)
        report.observe('archive', state['archive'])
        return True

    def install_phase(grant, report):
        doc = {'schema': install.BINDING_SCHEMA, 'root_id': ROOT,
               'operation_id': OPERATION, 'effect_commission_token': commission,
               'archive_path': state['archive']['archive_path'],
               'member_sha256': state['archive']['member_sha256'],
               'operation_scratch_dir': str(work), 'binary_version_path': runsc.CONSUMER_PATH}
        path, sha = private_doc('installer-binding.json', doc, grant)
        remaining = grant.deadline - clock()
        if remaining <= 60:
            raise CanaryRefused('installer_rollback_reserve')
        pool = install.Budget(total_seconds=remaining, combined_output_bytes=grant.raw_allowance)
        runner = install.BoundedRunner(pool)
        engine = install.InstallEngine(install.Layout.production(), runner, budget=pool)
        state['installer'] = engine
        code, receipt = engine.execute(path, sha)
        report.observe('installer', receipt, pool.spent_output_bytes + pool.rollback_spent_output_bytes)
        if code != 0 or engine.frozen:
            return False
        data = raw(receipt)
        manifest = projection.project_installer_result(data,
            expected_sha256=hashlib.sha256(data).hexdigest(), expected_operation=OPERATION,
            expected_hostname=engine.host_id, expected_daemon_id=engine.daemon_id)
        state['manifest'] = manifest
        report.observe('installed_manifest', manifest)
        return True

    def image_phase(grant, report):
        t = smoke.load_transport_module(str(source / 'transport.py'))
        state['transport'] = t
        sequence_number = 0
        def observe(doc):
            nonlocal sequence_number
            sequence_number += 1
            report.observe('image_capture_%d' % sequence_number, doc, doc['raw_bytes'])
        def before_pull(doc):
            report.observe('image_pull_intent', doc)
            return private_doc('image-pull-intent.json', doc, grant)[1]
        prepared = image.prepare(state['installer'], t, deadline=grant.deadline,
            raw_cap=grant.raw_allowance, before_pull=before_pull, observe=observe)
        # Raw records are already retained once above, including failed calls.
        prepared = {k: v for k, v in prepared.items() if k != 'observations'}
        state['image'] = prepared
        report.observe('image', prepared)
        return prepared['status'] == 'PRESENT'

    def smoke_phase(grant, report):
        engine = state['installer']
        prepared = state['image']
        adjudication = {'schema': 'rf.fixed_image_gate_application.v1',
            'commission_sha256': commission, 'image_receipt_sha256': digest(prepared),
            'exact_fixed_gate_passed': True, 'candidate_admission': False,
            'interpretation': 'Commissioned deterministic gate; not independent OCI blob proof'}
        report.observe('image_gate_application', adjudication)
        binding_doc = {'binding_schema': smoke.BINDING_SCHEMA,
            'expected_hostname': prepared['host']['Name'], 'expected_uid': 65534, 'expected_gid': 65534,
            'expected_kernel': prepared['host']['KernelVersion'],
            'expected_host_os': prepared['host']['OperatingSystem'],
            'daemon_arch': 'x86_64', 'ostype': 'linux',
            'docker_endpoint': smoke.DOCKER_ENDPOINT, 'docker_server_version': '29.1.3',
            'image_receipt_sha256': digest(prepared),
            'image_adjudication_sha256': digest(adjudication),
            'client_config_dir': engine.docker_config_path,
            'client_config_sha256': smoke.ANONYMOUS_CLIENT_CONFIG_SHA256}
        binding_path, binding_sha = private_doc('smoke-binding.json', binding_doc, grant)
        binding = smoke.load_binding_file(binding_path, binding_sha)
        manifest = state['manifest']
        if runsc._manifest_problem(manifest, binding) is not None:
            raise CanaryRefused('manifest_binding')
        runsc.verify_installed_bundle(manifest)
        checkpoint(grant)
        comp = runsc.build_runsc_composition(str(source / 'transport.py'),
                                             str(source / 'fixed_smoke_probe.py'))
        actual = smoke._real_executor(comp.t)
        def bounded(argv, *, deadline_seconds, output_cap_bytes):
            checkpoint(grant)
            engine._verify_client_config()
            if engine.socket_inspector(engine.layout.docker_socket, 0) != engine.socket_facts:
                raise CanaryRefused('socket_changed')
            return actual(argv, deadline_seconds=min(deadline_seconds, grant.deadline-clock()),
                          output_cap_bytes=output_cap_bytes)
        bounded.combined_capture = True
        physical = runsc.RunscQualificationEngine(comp.t, comp.plan, executor=bounded, binding=binding)
        # Include verification and receipt setup in the original 130s phase.
        physical._t0 = grant.deadline - 130
        def attempt_and_verify():
            attempt = smoke.execute_attempt(comp, physical, str(work / 'smoke-receipt.jsonl'))
            return smoke.validate_verdict(comp.t, attempt)
        def retain():
            captured = sum(len(x['stdout']) + len(x['stderr']) for x in physical.ledger)
            report.observe('smoke_execution', {'ledger': physical.evidence_ledger(),
                'known_container_id': physical.settled_cid,
                'self_cleanup_confirmed': physical.self_cleanup_confirmed,
                'frozen': physical.frozen}, captured)
        verdict = retain_after_attempt(attempt_and_verify, retain, report)
        report.observe('smoke_verdict', verdict)
        return True

    return sequence(dict(cli=cli_phase, archive=archive_phase, install=install_phase,
                         image=image_phase, smoke=smoke_phase), budget, commission)
