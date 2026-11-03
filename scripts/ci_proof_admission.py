"""Pure contracts used by merge-on-green's shared PR-proof admission.

No persistence, network, dispatch, expiry or independent scheduler lives here.
The serialized incumbent controller owns records and authenticates their source.
"""
from dataclasses import dataclass, replace
from datetime import datetime
import re


CAP = 8
ACTIVE_STATUSES = frozenset({"queued", "in_progress", "pending", "requested", "waiting"})


@dataclass(frozen=True)
class Demand:
    pr_number: int
    head_sha: str
    purpose: str
    requested_at: str
    demand_id: str


@dataclass(frozen=True)
class Run:
    run_id: int
    attempt: int
    status: str
    role: str


@dataclass(frozen=True)
class Admission:
    generation: str
    pr_number: int
    head_sha: str
    base_sha: str
    merge_sha: str
    workflow_sha: str
    run_id: int | None = None
    run_attempt: int = 1
    settled: bool = False


def _positive(value):
    return type(value) is int and value > 0


def _hex(value, size):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % size, value) is not None


def _admission_valid(a):
    return (
        isinstance(a, Admission)
        and _hex(a.generation, 12)
        and _positive(a.pr_number)
        and all(_hex(s, 40) for s in (a.head_sha, a.base_sha, a.merge_sha, a.workflow_sha))
        and (a.run_id is None or _positive(a.run_id))
        and _positive(a.run_attempt)
        and type(a.settled) is bool
        and (not a.settled or a.run_id is not None)
    )


def capacity(runs, admissions, *, census_complete, records_complete, legacy_reservations=0):
    """Conservative free slots, never a permission to dispatch without custody.

    Inputs must be authenticated by the caller. Completeness includes all active
    statuses/carriers and all outstanding PR records, including closed PRs. The
    retained record floor survives missing index results and unknown effects. A
    settled flag means exact terminal original-run/attempt evidence was validated;
    elapsed time or a closed/superseded PR is never settlement.
    """
    if (census_complete is not True or records_complete is not True
            or type(legacy_reservations) is not int or legacy_reservations < 0):
        return 0
    identities = {}
    active_ids = set()
    for r in runs:
        if (not isinstance(r, Run) or not _positive(r.run_id) or not _positive(r.attempt)
                or r.status not in ACTIVE_STATUSES | {"completed"}
                or r.role not in {"pr_head", "main"}):
            return 0
        identity = (r.attempt, r.role)
        if r.run_id in identities and identities[r.run_id] != identity:
            return 0
        identities[r.run_id] = identity
        if r.role == "pr_head" and r.status in ACTIVE_STATUSES:
            active_ids.add(r.run_id)
    generations = {}
    bound_ids = {}
    unindexed = set()
    for a in admissions:
        if not _admission_valid(a):
            return 0
        if a.generation in generations and generations[a.generation] != a:
            return 0
        generations[a.generation] = a
        if a.run_id is not None:
            if a.run_id in bound_ids and bound_ids[a.run_id] != a.generation:
                return 0
            bound_ids[a.run_id] = a.generation
            if a.run_id in identities and identities[a.run_id] != (a.run_attempt, "pr_head"):
                return 0
        if not a.settled:
            if a.run_id is None:
                unindexed.add(a.generation)
            else:
                active_ids.add(a.run_id)
    return max(0, CAP - len(active_ids) - len(unindexed) - legacy_reservations)


def _demand_time(demand):
    if (not isinstance(demand, Demand) or not _positive(demand.pr_number)
            or not _hex(demand.head_sha, 40) or not _hex(demand.demand_id, 12)
            or demand.purpose not in {"authored", "refresh"}
            or not isinstance(demand.requested_at, str)):
        raise ValueError("invalid proof demand identity")
    try:
        when = datetime.fromisoformat(demand.requested_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid proof demand clock") from exc
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError("proof demand clock requires timezone")
    return when


def ordered_demands(demands):
    """Order already eligible demands by stable first-unserved age.

    Eligibility/source/authority checks belong to the incumbent controller. A
    blocked demand does not get a reserved slot. Later authored demand has no
    priority over an older eligible refresh. A pending head change keeps its age.
    """
    by_pr = {}
    by_id = {}
    clocks = {}
    for demand in demands:
        clocks[demand.pr_number] = _demand_time(demand)
        if demand.pr_number in by_pr and by_pr[demand.pr_number] != demand:
            raise ValueError("conflicting outstanding demands for PR")
        if demand.demand_id in by_id and by_id[demand.demand_id] != demand:
            raise ValueError("conflicting demand generation")
        by_pr[demand.pr_number] = demand
        by_id[demand.demand_id] = demand
    return sorted(by_pr.values(), key=lambda d: (clocks[d.pr_number], d.demand_id, d.pr_number))


def replace_pending_head(demand, head_sha):
    """Only for a never-admitted demand; immutable admissions are not updated."""
    _demand_time(demand)
    if not _hex(head_sha, 40):
        raise ValueError("invalid replacement head")
    return replace(demand, head_sha=head_sha)


def bind_run(admission, run_id, run_attempt):
    """Bind the original dispatch response once; never adopt a replacement run."""
    if not _admission_valid(admission) or not _positive(run_id) or not _positive(run_attempt):
        raise ValueError('invalid original run binding')
    if admission.run_attempt != run_attempt:
        raise ValueError('changed original run attempt')
    if admission.run_id is not None and admission.run_id != run_id:
        raise ValueError('admission already bound to another original run')
    return replace(admission, run_id=run_id)


def settle_run(admission, run):
    """Settlement is exact terminal workload evidence, not a successful proof.

    The caller must authenticate the run and validate its admission provenance.
    Failure/cancellation can settle hosted capacity without granting any green
    check, refresh permission, release or product acceptance.
    """
    if (not _admission_valid(admission) or admission.run_id is None
            or not isinstance(run, Run) or not _positive(run.run_id) or not _positive(run.attempt)
            or run.status != 'completed'
            or run.role != 'pr_head' or run.run_id != admission.run_id
            or run.attempt != admission.run_attempt):
        raise ValueError('no exact terminal original run')
    return replace(admission, settled=True)


def validate_execution(admission, *, subject_head, base, merge, parents, workflow):
    """Validate observed Git objects after authenticated admission lookup.

    The trusted resolver observes these values; workflow inputs and PR body text
    alone cannot establish them. There is no mutable-ref or one-parent fallback.
    """
    if (not _admission_valid(admission)
            or (subject_head, base, merge, workflow) != (
                admission.head_sha, admission.base_sha, admission.merge_sha, admission.workflow_sha)
            or parents != [admission.base_sha, admission.head_sha]):
        raise ValueError('admitted source/definition does not match exact tested merge')


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate admission receipt field')
        result[key] = value
    return result


def _controller_receipt_data(*, archive, payload_sha256, repository_id,
                         artifact_id, controller_run_id, controller_attempt,
                         controller_sha, artifact, controller, member_limit=32768):
    """Bind immutable receipt bytes to the protected controller's Actions run.

    ``artifact`` and ``controller`` must come from authenticated GitHub endpoints,
    not a PR comment. The caller independently pins the protected control SHA,
    supplies the downloaded archive bytes. This function hashes and extracts the
    bounded canonical member from those SAME bytes without writing any path. A comment is only a lookup/index. Bot identity and comment URLs
    grant no authority. Missing/expired evidence preserves the outstanding slot.
    """
    import hashlib
    import json
    import io
    import zipfile

    if (not isinstance(archive, bytes) or len(archive) > 1048576
            or not all(_positive(i) for i in (
                repository_id, artifact_id, controller_run_id, controller_attempt))
            or not _hex(controller_sha, 40) or not _hex(payload_sha256, 64)
            or not isinstance(artifact, dict) or not isinstance(controller, dict)):
        raise ValueError('malformed admission provenance')
    archive_sha256 = hashlib.sha256(archive).hexdigest()
    run_binding = artifact.get('workflow_run')
    repo_binding = controller.get('repository')
    if (not isinstance(run_binding, dict) or not isinstance(repo_binding, dict)
            or not all(_positive(v) for v in (artifact.get('id'),
                run_binding.get('id'), run_binding.get('repository_id'),
                controller.get('id'), controller.get('run_attempt'), repo_binding.get('id')))
            or artifact.get('id') != artifact_id
            or artifact.get('expired') is not False
            or artifact.get('digest') != 'sha256:' + archive_sha256
            or run_binding.get('id') != controller_run_id
            or run_binding.get('repository_id') != repository_id
            or run_binding.get('head_sha') != controller_sha
            or controller.get('id') != controller_run_id
            or controller.get('run_attempt') != controller_attempt
            or repo_binding.get('id') != repository_id
            or controller.get('path') not in {'.github/workflows/merge-on-green.yml',
                '.github/workflows/merge-on-green.yml@main',
                '.github/workflows/merge-on-green.yml@refs/heads/main',
                '.github/workflows/merge-on-green.yml@'+controller_sha}
            or controller.get('head_branch') != 'main'
            or controller.get('head_sha') != controller_sha
            or controller.get('event') not in {
                'workflow_run', 'schedule', 'workflow_dispatch', 'pull_request_target'}):
        raise ValueError('receipt was not produced by the exact protected controller')
    try:
        with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
            entries = bundle.infolist()
            if (len(entries) != 1 or entries[0].filename != 'ci-proof-admission.json'
                    or entries[0].is_dir() or entries[0].file_size > member_limit):
                raise ValueError('ambiguous or oversized admission receipt member')
            with bundle.open(entries[0]) as member:
                payload = member.read(member_limit + 1)
            if len(payload) > member_limit:
                raise ValueError('oversized admission receipt bytes')
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ValueError('unreadable admission archive') from exc
    if hashlib.sha256(payload).hexdigest() != payload_sha256:
        raise ValueError('admission receipt bytes differ from retained digest')
    try:
        data = json.loads(payload, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError) as exc:
        raise ValueError('unreadable admission receipt') from exc
    if (not isinstance(data, dict)
            or type(data.get('repository_id')) is not int or data['repository_id'] != repository_id
            or type(data.get('controller_run_id')) is not int or data['controller_run_id'] != controller_run_id
            or type(data.get('controller_run_attempt')) is not int
            or data['controller_run_attempt'] != controller_attempt):
        raise ValueError('admission receipt repository/controller identity mismatch')
    return data


def authenticate_receipt(**context):
    """Authenticate one generation-specific prepared or bound proof receipt."""
    from dataclasses import fields
    data = _controller_receipt_data(**context)
    expected = {'schema', 'repository_id', 'controller_run_id',
                'controller_run_attempt', 'admission'}
    if (set(data) != expected or data['schema'] != 'mastermind.ci-proof-admission.v1'
            or not isinstance(data['admission'], dict)
            or set(data['admission']) != {f.name for f in fields(Admission)}):
        raise ValueError('admission receipt schema mismatch')
    result = Admission(**data['admission'])
    if not _admission_valid(result):
        raise ValueError('malformed admitted proof identity')
    stage = 'prepared' if result.run_id is None else 'bound'
    expected_name = (f"ci-proof-admission-{context['controller_run_id']}-"
                     f"{context['controller_attempt']}-{result.generation}-{stage}")
    if context['artifact'].get('name') != expected_name:
        raise ValueError('admission artifact generation/stage mismatch')
    return result


def authenticate_demands(**context):
    """Authenticate bounded changed-demand records from the same controller.

    This artifact authenticates records indexed on existing PRs; it is not a
    launch reservation or a queue. The complete PR discovery remains authoritative.
    """
    from dataclasses import fields
    data = _controller_receipt_data(**context, member_limit=262144)
    if (set(data) != {'schema', 'repository_id', 'controller_run_id', 'controller_run_attempt', 'demands'}
            or data['schema'] != 'mastermind.ci-proof-demands.v1'
            or not isinstance(data['demands'], list) or len(data['demands']) > 1000
            or context['artifact'].get('name') != (
                f"ci-proof-demands-{context['controller_run_id']}-{context['controller_attempt']}")):
        raise ValueError('demand receipt schema/identity mismatch')
    result = []
    for row in data['demands']:
        if not isinstance(row, dict) or set(row) != {f.name for f in fields(Demand)}:
            raise ValueError('malformed demand record')
        result.append(Demand(**row))
    ordered = ordered_demands(result)
    if len(ordered) != len(result):
        raise ValueError('duplicate demand record')
    return ordered


def merge_records(records):
    """Fold authenticated immutable receipts without rewinding original effects.

    A bound receipt may follow a prepared receipt for the same generation. An old
    comment cannot rewind that binding or its terminal settlement. Conflicting
    source, run or attempt identities are an unresolved record, not latest-wins.
    """
    result = {}
    for record in records:
        if not _admission_valid(record):
            raise ValueError('malformed admission receipt state')
        old = result.get(record.generation)
        if old is None:
            result[record.generation] = record
            continue
        if replace(old, run_id=None, settled=False) != replace(record, run_id=None, settled=False):
            raise ValueError('conflicting admission generation identity')
        if old.run_id is not None and record.run_id is not None and old.run_id != record.run_id:
            raise ValueError('conflicting original dispatch run')
        result[record.generation] = replace(old, run_id=old.run_id or record.run_id,
                                             settled=old.settled or record.settled)
    return list(result.values())


def reserved_dispatch_allowed(runs, records, reserved, *, census_complete, records_complete):
    """Revalidate capacity immediately before spending an existing reservation.

    The caller supplies the authenticated complete inventory, including this exact
    reservation. Remove only that one unstarted slot, then require a real free
    slot. This catches legacy/out-of-band arrivals since preparation without
    dropping another generation or relaunching an already bound original.
    """
    if (not _admission_valid(reserved) or reserved.run_id is not None
            or reserved.run_attempt != 1 or reserved.settled):
        return False
    try:
        merged = merge_records(records)
    except ValueError:
        return False
    if reserved not in merged:
        return False
    other = [a for a in merged if a.generation != reserved.generation]
    return capacity(runs, other, census_complete=census_complete,
                    records_complete=records_complete) > 0


def pending_demand_for_pr(records, admissions, pr_number, current_head):
    """Recover first-unserved age from authenticated PR demand records.

    The caller has separately established current eligibility and complete record
    custody. A reserved generation is not offered again even if its dispatch is
    unknown. Source changes may update a never-admitted demand without resetting
    age. New cycles are minted by the controller only after this returns None and
    the existing effects/eligibility gates permit them.
    """
    if not _positive(pr_number) or not _hex(current_head, 40):
        raise ValueError('invalid live PR identity')
    admitted = {a.generation: a for a in merge_records(admissions)}
    pending = {}
    for d in records:
        _demand_time(d)
        if d.pr_number != pr_number:
            continue
        if d.demand_id in admitted:
            if admitted[d.demand_id].pr_number != d.pr_number:
                raise ValueError('demand/admission PR mismatch')
            continue
        old = pending.get(d.demand_id)
        if old and replace(old, head_sha=d.head_sha) != d:
            raise ValueError('pending demand age or purpose changed')
        pending[d.demand_id] = d
    if len(pending) > 1:
        raise ValueError('multiple unserved demands for the same PR')
    if not pending:
        return None
    return replace_pending_head(next(iter(pending.values())), current_head)


@dataclass(frozen=True)
class Checkpoint:
    """Authenticated compaction of ONE existing PR's admission comments.

    This is bounded evidence coverage, not a new queue. The controller may create
    it only after a complete original PR comment read and run reconciliation.
    Outstanding UNKNOWN is carried forward. A covered record is retired only by
    exact terminal disposition, never by age, closure or an expired artifact.
    """
    pr_number: int
    covered_through_comment_id: int
    admissions: tuple[Admission, ...]
    demands: tuple[Demand, ...]
    settled: tuple[Admission, ...]


def compact_pr_records(pr_number, covered_through_comment_id, records, demands,
                       observed_runs, *, records_complete):
    if (records_complete is not True or not _positive(pr_number)
            or not _positive(covered_through_comment_id)):
        raise ValueError('incomplete PR record custody for compaction')
    current = merge_records(records)
    if any(a.pr_number != pr_number for a in current):
        raise ValueError('cross-PR admission compaction')
    outstanding, settled = [], []
    for a in current:
        if a.run_id is not None:
            matches = [r for r in observed_runs if isinstance(r, Run)
                       and _positive(r.run_id) and _positive(r.attempt)
                       and r.run_id == a.run_id and r.attempt == a.run_attempt
                       and r.role == 'pr_head']
            # An active observation always beats a terminal one during a
            # non-atomic read. Do not compact away an observed active execution.
            if any(r.status in ACTIVE_STATUSES for r in matches):
                a = replace(a, settled=False)
            elif matches and all(r.status == 'completed' for r in matches):
                a = settle_run(a, matches[0])
        (settled if a.settled else outstanding).append(a)
    admitted_ids = {a.generation for a in current}
    # Input versions are in authenticated original comment order. A head change
    # does not create a second demand or reset its first-unserved clock.
    pending_by_id = {}
    for d in demands:
        _demand_time(d)
        if d.pr_number != pr_number:
            raise ValueError('cross-PR demand compaction')
        if d.demand_id not in admitted_ids:
            previous = pending_by_id.get(d.demand_id)
            if previous and replace(previous, head_sha=d.head_sha) != d:
                raise ValueError('pending demand age or purpose changed')
            pending_by_id[d.demand_id] = d
    pending = ordered_demands(pending_by_id.values())
    if len(outstanding) > CAP or len(settled) > 100 or len(pending) > 1:
        raise ValueError('PR checkpoint exceeds bounded lifecycle')
    return Checkpoint(pr_number, covered_through_comment_id, tuple(outstanding), tuple(pending), tuple(settled))


def _checkpoint_valid(checkpoint):
    if (not isinstance(checkpoint, Checkpoint) or not _positive(checkpoint.pr_number)
            or not _positive(checkpoint.covered_through_comment_id)
            or not all(isinstance(values, tuple) for values in (
                checkpoint.admissions, checkpoint.demands, checkpoint.settled))):
        return False
    try:
        recomputed = compact_pr_records(checkpoint.pr_number, checkpoint.covered_through_comment_id,
            [*checkpoint.admissions, *checkpoint.settled], list(checkpoint.demands), [], records_complete=True)
        return recomputed == checkpoint
    except (ValueError, TypeError):
        return False


def validate_checkpoint_transition(previous, current):
    """Check complete-state conservation before a producer publishes coverage."""
    if (not _checkpoint_valid(previous) or not _checkpoint_valid(current)
            or previous.pr_number != current.pr_number
            or current.covered_through_comment_id < previous.covered_through_comment_id):
        raise ValueError('invalid checkpoint transition')
    resolved = {a.generation: a for a in (*current.admissions, *current.settled)}
    for a in previous.admissions:
        if a.generation not in resolved:
            raise ValueError('outstanding admission omitted from subsequent coverage')
        if merge_records([a, resolved[a.generation]]) != [resolved[a.generation]]:
            raise ValueError('checkpoint rewinds original bound state')
    pending = {d.demand_id: d for d in current.demands}
    for demand in previous.demands:
        if demand.demand_id in resolved:
            continue
        successor = pending.get(demand.demand_id)
        if successor is None or replace(demand, head_sha=successor.head_sha) != successor:
            raise ValueError('checkpoint drops or changes an unserved demand')


def select_checkpoint(checkpoints, pr_number):
    """Choose authenticated coverage, never a comment's mutable 'latest' claim."""
    if not _positive(pr_number):
        raise ValueError('invalid checkpoint PR')
    by_coverage = {}
    for checkpoint in checkpoints:
        if not _checkpoint_valid(checkpoint) or checkpoint.pr_number != pr_number:
            raise ValueError('invalid authenticated checkpoint')
        coverage = checkpoint.covered_through_comment_id
        if coverage in by_coverage and by_coverage[coverage] != checkpoint:
            raise ValueError('conflicting authenticated coverage')
        by_coverage[coverage] = checkpoint
    ordered = [by_coverage[n] for n in sorted(by_coverage)]
    for previous, current in zip(ordered, ordered[1:]):
        validate_checkpoint_transition(previous, current)
    return ordered[-1] if ordered else None


def references_after_checkpoint(references, checkpoint):
    """Retain every original index newer than authenticated complete coverage.

    Input comment IDs must come from a complete server read. Duplicate/conflicting
    IDs and malformed coverage fail closed. This function authenticates nothing.
    """
    if checkpoint is not None and not _checkpoint_valid(checkpoint):
        raise ValueError('invalid record coverage')
    seen = set()
    result = []
    boundary = checkpoint.covered_through_comment_id if checkpoint else 0
    for comment_id, reference in references:
        if not _positive(comment_id) or comment_id in seen:
            raise ValueError('invalid or duplicated original comment ID')
        seen.add(comment_id)
        if comment_id > boundary:
            result.append((comment_id, reference))
    return result


def authenticate_checkpoint(**context):
    """Authenticate a bounded PR checkpoint through original Actions evidence."""
    from dataclasses import fields
    data = _controller_receipt_data(**context)
    if (set(data) != {'schema','repository_id','controller_run_id','controller_run_attempt','checkpoint'}
            or data['schema'] != 'mastermind.ci-proof-checkpoint.v1'
            or not isinstance(data['checkpoint'], dict)
            or set(data['checkpoint']) != {f.name for f in fields(Checkpoint)}):
        raise ValueError('checkpoint schema mismatch')
    value = dict(data['checkpoint'])
    for field, record_type, limit in (('admissions',Admission,CAP),('settled',Admission,100),('demands',Demand,1)):
        if not isinstance(value[field], list) or len(value[field]) > limit:
            raise ValueError('checkpoint lifecycle bound exceeded')
        expected_keys = {f.name for f in fields(record_type)}
        if any(not isinstance(row, dict) or set(row) != expected_keys for row in value[field]):
            raise ValueError('checkpoint record schema mismatch')
        value[field] = tuple(record_type(**row) for row in value[field])
    checkpoint = Checkpoint(**value)
    if (not _checkpoint_valid(checkpoint) or context['artifact'].get('name') != (
            f"ci-proof-checkpoint-{context['controller_run_id']}-{context['controller_attempt']}-{checkpoint.pr_number}")):
        raise ValueError('checkpoint identity or artifact name mismatch')
    return checkpoint
