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


@dataclass(frozen=True)
class SourceAdmission(Admission):
    """Original source-head proof for an allowlisted native target, not entry."""
    target_ref: str = "main"


@dataclass(frozen=True)
class NativeAdmission(Admission):
    """One reserved native queue original; never a dispatch or a PR refresh.

    merge_sha remains the exact two-parent potential PR merge observed before
    enqueue. The native squash commit is separately bound, never relabeled.
    A missing queue/group/run binding retains its one reservation floor.
    """
    target_ref: str = "codex/merge-queue-pilot"
    tree_sha: str = ""
    queue_entry_id: str | None = None
    group_head_sha: str | None = None


def admission_role(admission):
    return "merge_group" if isinstance(admission, NativeAdmission) else "pr_head"


def bind_native_entry(admission, entry_id):
    if (not isinstance(admission, NativeAdmission) or not _admission_valid(admission)
            or not isinstance(entry_id, str) or not 0 < len(entry_id) <= 256
            or not all(32 < ord(c) < 127 for c in entry_id)
            or admission.queue_entry_id not in {None, entry_id}):
        raise ValueError("native original queue entry cannot be replaced")
    return replace(admission, queue_entry_id=entry_id)


def bind_native_execution(admission, group, run_id, run_attempt):
    """Caller authenticates complete native membership + exact server run.

    Does not discover a run by timestamp/name. Rebuilt/retried groups require a
    separately admitted original; this generation can bind exactly once.
    """
    if (not isinstance(admission, NativeAdmission) or not _admission_valid(admission)
            or not isinstance(group, dict) or set(group) != {
                "target_ref", "queue_entry_id", "pr_number", "source_head_sha",
                "group_head_sha", "base_sha", "tree_sha"}
            or not _hex(group.get("group_head_sha"), 40)
            or (group["target_ref"], group["queue_entry_id"], group["pr_number"],
                group["source_head_sha"], group["base_sha"], group["tree_sha"]) != (
                admission.target_ref, admission.queue_entry_id, admission.pr_number,
                admission.head_sha, admission.base_sha, admission.tree_sha)
            or admission.queue_entry_id is None
            or admission.group_head_sha not in {None, group["group_head_sha"]}):
        raise ValueError("native execution differs from original queue admission")
    candidate = replace(admission, group_head_sha=group["group_head_sha"])
    return bind_run(candidate, run_id, run_attempt)


def native_execution_identity(admission):
    if (not isinstance(admission, NativeAdmission) or not _admission_valid(admission)
            or admission.run_id is None):
        raise ValueError("native original execution is not bound")
    return dict(target_ref=admission.target_ref, queue_entry_id=admission.queue_entry_id,
                pr_number=admission.pr_number, source_head_sha=admission.head_sha,
                group_head_sha=admission.group_head_sha, base_sha=admission.base_sha,
                tree_sha=admission.tree_sha)


def _positive(value):
    return type(value) is int and value > 0


def _hex(value, size):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{%d}" % size, value) is not None


def _admission_valid(a):
    if isinstance(a,SourceAdmission) and a.target_ref not in {"main","codex/merge-queue-pilot"}:return False
    if isinstance(a, NativeAdmission):
        if (a.target_ref not in {"main", "codex/merge-queue-pilot"} or not _hex(a.tree_sha, 40)
                or (a.queue_entry_id is not None and (not isinstance(a.queue_entry_id, str)
                    or not 0 < len(a.queue_entry_id) <= 256
                    or not all(32 < ord(c) < 127 for c in a.queue_entry_id)))
                or (a.group_head_sha is not None and (not _hex(a.group_head_sha, 40) or a.queue_entry_id is None))
                or (a.run_id is not None and a.group_head_sha is None)):
            return False
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


def capacity(runs, admissions, *, census_complete, records_complete, legacy_reservations=0,
             decision=None):
    """Conservative free slots, never a permission to dispatch without custody.

    Inputs must be authenticated by the caller. Completeness includes all active
    statuses/carriers and all outstanding PR records, including closed PRs. The
    retained record floor survives missing index results and unknown effects. A
    settled flag means exact terminal original-run/attempt evidence was validated;
    elapsed time or a closed/superseded PR is never settlement.
    """
    # Optional observation only: never recompute or grant capacity from this data.
    # Production callers already bound the inventory; do not truncate identities.
    if decision is not None:
        decision.clear()
        decision.update(evaluated=True, cap=CAP, census_complete=census_complete is True,
                        records_complete=records_complete is True, validated=False,
                        free_slots=0)
    if (census_complete is not True or records_complete is not True
            or type(legacy_reservations) is not int or legacy_reservations < 0):
        return 0
    identities = {}
    active_ids = set()
    for r in runs:
        if (not isinstance(r, Run) or not _positive(r.run_id) or not _positive(r.attempt)
                or r.status not in ACTIVE_STATUSES | {"completed"}
                or r.role not in {"pr_head", "main", "merge_group"}):
            return 0
        identity = (r.attempt, r.role)
        if r.run_id in identities and identities[r.run_id] != identity:
            return 0
        identities[r.run_id] = identity
        if r.role in {"pr_head", "merge_group"} and r.status in ACTIVE_STATUSES:
            active_ids.add(r.run_id)
    indexed_active_ids = set(active_ids) if decision is not None else None
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
            if a.run_id in identities and identities[a.run_id] != (a.run_attempt, admission_role(a)):
                return 0
        if not a.settled:
            if a.run_id is None:
                unindexed.add(a.generation)
            else:
                active_ids.add(a.run_id)
    free_slots = max(0, CAP - len(active_ids) - len(unindexed) - legacy_reservations)
    if decision is not None:
        decision.update(validated=True, free_slots=free_slots,
                        counted_run_ids=sorted(active_ids),
                        indexed_active_run_ids=sorted(indexed_active_ids),
                        bound_floor_run_ids=sorted(active_ids - indexed_active_ids),
                        unindexed_generations=sorted(unindexed),
                        counted_run_count=len(active_ids),
                        unindexed_count=len(unindexed), legacy_reservations=legacy_reservations,
                        used_slots=len(active_ids) + len(unindexed) + legacy_reservations)
    return free_slots


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
            or run.role != admission_role(admission) or run.run_id != admission.run_id
            or run.attempt != admission.run_attempt):
        raise ValueError('no exact terminal original run')
    return replace(admission, settled=True)


def validate_execution(admission, *, subject_head, base, merge, parents, workflow):
    """Validate observed Git objects after authenticated admission lookup.

    The trusted resolver observes these values; workflow inputs and PR body text
    alone cannot establish them. There is no mutable-ref or one-parent fallback.
    """
    if (isinstance(admission, NativeAdmission) or not _admission_valid(admission)
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


def _bounded_receipt_payload(archive, payload_sha256, *, member_limit=32768):
    """The incumbent one-member/one-MiB envelope, with no filesystem extraction."""
    import hashlib,io,json,zipfile
    if not isinstance(archive,bytes) or len(archive)>1048576:
        raise ValueError('oversized receipt archive')
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
    if payload_sha256 is not None and hashlib.sha256(payload).hexdigest() != payload_sha256:
        raise ValueError('admission receipt bytes differ from retained digest')
    try:
        data = json.loads(payload, object_pairs_hook=_unique_object)
    except (ValueError, UnicodeError) as exc:
        raise ValueError('unreadable admission receipt') from exc
    return data


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
    data = _bounded_receipt_payload(archive,payload_sha256,member_limit=member_limit)
    if (not isinstance(data, dict)
            or type(data.get('repository_id')) is not int or data['repository_id'] != repository_id
            or type(data.get('controller_run_id')) is not int or data['controller_run_id'] != controller_run_id
            or type(data.get('controller_run_attempt')) is not int
            or data['controller_run_attempt'] != controller_attempt):
        raise ValueError('admission receipt repository/controller identity mismatch')
    return data


def authenticate_receipt(**context):
    """Same immutable envelope; native v2 cannot be relabeled as PR v1."""
    from dataclasses import fields
    data = _controller_receipt_data(**context)
    expected = {'schema', 'repository_id', 'controller_run_id',
                'controller_run_attempt', 'admission'}
    classes = {'mastermind.ci-proof-admission.v1': Admission,
               'mastermind.ci-proof-native-admission.v1': NativeAdmission,
               'mastermind.ci-proof-source-admission.v1': SourceAdmission}
    cls = classes.get(data.get('schema'))
    if (set(data) != expected or cls is None
            or not isinstance(data['admission'], dict)
            or set(data['admission']) != {f.name for f in fields(cls)}):
        raise ValueError('admission receipt schema mismatch')
    result = cls(**data['admission'])
    if not _admission_valid(result):
        raise ValueError('malformed admitted proof identity')
    stage = 'prepared' if result.run_id is None else 'bound'
    if isinstance(result, NativeAdmission):
        stage = 'native-' + ('bound' if result.run_id is not None else
                            'queued' if result.queue_entry_id is not None else 'prepared')
    if isinstance(result,SourceAdmission):stage='source-'+stage
    expected_name = (f"ci-proof-admission-{context['controller_run_id']}-"
                     f"{context['controller_attempt']}-{result.generation}-{stage}")
    if context['artifact'].get('name') != expected_name:
        raise ValueError('admission artifact generation/stage mismatch')
    return result


@dataclass(frozen=True)
class LegacyMigration:
    """A controller migration fact, never an Admission or an age witness."""
    pr_number: int
    generation: str
    pre_head_sha: str
    head_sha: str
    acquired_at: str
    proof_run_id: int
    proof_run_attempt: int
    phase: str
    residuals: tuple = ()
    intent_artifact_id: int | None = None
    acknowledged: bool = False
    observed_register: str | None = None


def migration_pointer(record, artifact_id):
    if not _positive(record.pr_number) or not _positive(artifact_id):
        raise ValueError('invalid migration pointer identity')
    value = f'a2 p={record.pr_number} i={artifact_id} s=migrating r={artifact_id}'
    if len(value)>100:raise ValueError('migration pointer exceeds existing description bound')
    return value


def authenticate_migration(**context):
    """Same original-controller archive binding/limits; strictly separate type."""
    from dataclasses import fields
    data = _controller_receipt_data(**context)
    if (set(data) != {'schema', 'repository_id', 'controller_run_id',
                     'controller_run_attempt', 'migration'}
            or data['schema'] != 'mastermind.ci-proof-migration.v1'
            or not isinstance(data['migration'], dict)
            or set(data['migration']) != {f.name for f in fields(LegacyMigration)}):
        raise ValueError('migration receipt schema mismatch')
    raw=data['migration'].copy()
    if not isinstance(raw['residuals'],list) or len(raw['residuals'])>1000:
        raise ValueError('migration residual inventory malformed')
    raw['residuals']=tuple(raw['residuals'])
    result = LegacyMigration(**raw)
    numbers=set()
    for row in result.residuals:
        if (not isinstance(row,dict) or set(row)!={'pr_number','head_sha','state'}
                or not _positive(row['pr_number']) or row['pr_number']==result.pr_number
                or row['pr_number'] in numbers or not _hex(row['head_sha'],40) or row['state']!='closed'):
            raise ValueError('migration residual identity invalid')
        numbers.add(row['pr_number'])
    try:
        when = datetime.fromisoformat(result.acquired_at.replace('Z', '+00:00'))
    except (AttributeError, TypeError, ValueError):
        raise ValueError('migration acquisition clock invalid')
    if (not _positive(result.pr_number) or not _hex(result.generation, 12)
            or not _hex(result.pre_head_sha, 40) or not _hex(result.head_sha, 40)
            or result.pre_head_sha == result.head_sha or when.tzinfo is None
            or not _positive(result.proof_run_id) or type(result.proof_run_attempt) is not int
            or result.proof_run_attempt != 1 or type(result.acknowledged) is not bool
            or context['controller_attempt'] != 1):
        raise ValueError('migration original generation invalid')
    if result.phase == 'intent':
        valid = (result.intent_artifact_id is None and not result.acknowledged
                 and result.observed_register is None)
    elif result.phase == 'outcome':
        valid = (_positive(result.intent_artifact_id) and result.acknowledged
                 and result.observed_register == migration_pointer(result, result.intent_artifact_id))
    else:
        valid = False
    expected = (f"ci-proof-migration-{context['controller_run_id']}-"
                f"{context['controller_attempt']}-{result.generation}-{result.phase}")
    if not valid or context['artifact'].get('name') != expected:
        raise ValueError('migration phase/acknowledgement mismatch')
    return result

@dataclass(frozen=True)
class AgeSnapshot:
    demands: tuple[Demand, ...]
    # Exact per-PR comment coverage, not a global time or a transitive ref list.
    covered_comments: tuple[tuple[int, int], ...] = ()
    version: int = 1


def authenticate_age_snapshot(**context):
    from dataclasses import fields
    data = _controller_receipt_data(**context, member_limit=262144)
    version={'mastermind.ci-proof-demands.v1':1,'mastermind.ci-proof-demands.v2':2}.get(data.get('schema'))
    expected={'schema','repository_id','controller_run_id','controller_run_attempt','demands'}
    if version==2:expected.add('covered_comments')
    if (version is None or set(data)!=expected or not isinstance(data['demands'],list)
            or len(data['demands'])>1000 or context['artifact'].get('name') !=
            f"ci-proof-demands-{context['controller_run_id']}-{context['controller_attempt']}"):
        raise ValueError('demand receipt schema/identity mismatch')
    result=[]
    for row in data['demands']:
        if not isinstance(row,dict) or set(row)!={f.name for f in fields(Demand)}:
            raise ValueError('malformed demand record')
        result.append(Demand(**row))
    ordered=ordered_demands(result)
    if len(ordered)!=len(result):raise ValueError('duplicate demand record')
    coverage=[]
    if version==2:
        if len({d.pr_number for d in ordered})!=len(ordered):raise ValueError('multiple snapshot ages for one PR')
        rows=data['covered_comments']
        if not isinstance(rows,list) or len(rows)>1000:raise ValueError('age coverage exceeds existing bound')
        for row in rows:
            if (not isinstance(row,dict) or set(row)!={'pr_number','through_comment_id'}
                    or not _positive(row['pr_number']) or not _positive(row['through_comment_id'])):
                raise ValueError('invalid age coverage')
            coverage.append((row['pr_number'],row['through_comment_id']))
        if len(dict(coverage))!=len(coverage):raise ValueError('duplicate age coverage scope')
    return AgeSnapshot(tuple(ordered),tuple(sorted(coverage)),version)


def authenticate_demands(**context):
    """v1 changed rows retain their meaning; v2 adds explicit age-only coverage."""
    return list(authenticate_age_snapshot(**context).demands)


def fold_age_snapshots(entries, load):
    """Authenticate coverage before skipping originals; no newest-wins rule.

    Each entry is a server PR/comment identity and an untrusted locator. Numeric
    cutoff law is the incumbent per-PR checkpoint convention. Requiring EVERY
    covered cutoff below this snapshot's original index rejects self/future and
    cyclic coverage conservatively, even across differently ordered PR pages.
    """
    seen=set();coverage={};demands=[];selected=None
    for number,comment_id,reference in sorted(entries,key=lambda e:e[1],reverse=True):
        if not _positive(number) or not _positive(comment_id) or comment_id in seen:
            raise ValueError('invalid original age index identity')
        seen.add(comment_id)
        if comment_id<=coverage.get(number,0):continue
        snapshot=load(reference)
        if not isinstance(snapshot,AgeSnapshot):raise ValueError('unauthenticated age snapshot')
        if snapshot.version==2:
            if selected is not None:raise ValueError('conflicting uncovered age successors')
            if any(cutoff>=comment_id for _,cutoff in snapshot.covered_comments):
                raise ValueError('age snapshot covers itself or a future index')
            selected=comment_id
            coverage.update(snapshot.covered_comments)
        demands.extend(snapshot.demands)
    # Every unserved generation must keep its original PR/age/purpose. Head
    # versions may differ; pending_demand_for_pr binds the observed current head.
    generations={}
    for d in demands:
        _demand_time(d)
        identity=(d.pr_number,d.requested_at,d.purpose)
        if d.demand_id in generations and generations[d.demand_id]!=identity:
            raise ValueError('age generation identity changed')
        generations[d.demand_id]=identity
    return AgeSnapshot(tuple(demands),tuple(sorted(coverage.items())),2 if selected else 1)


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
        if type(old) is not type(record):
            raise ValueError('admission carrier changed within generation')
        bindings = {'run_id': None, 'settled': False}
        if isinstance(old, NativeAdmission):
            bindings.update(queue_entry_id=None, group_head_sha=None)
            for key in ('queue_entry_id', 'group_head_sha'):
                left, right = getattr(old, key), getattr(record, key)
                if left is not None and right is not None and left != right:
                    raise ValueError('conflicting native original binding')
        if replace(old, **bindings) != replace(record, **bindings):
            raise ValueError('conflicting admission generation identity')
        if old.run_id is not None and record.run_id is not None and old.run_id != record.run_id:
            raise ValueError('conflicting original dispatch run')
        merged = dict(run_id=old.run_id or record.run_id, settled=old.settled or record.settled)
        if isinstance(old, NativeAdmission):
            merged.update(queue_entry_id=old.queue_entry_id or record.queue_entry_id,
                          group_head_sha=old.group_head_sha or record.group_head_sha)
        result[record.generation] = replace(old, **merged)
    return list(result.values())


def reserved_dispatch_allowed(runs, records, reserved, *, census_complete, records_complete,
                              decision=None):
    """Revalidate capacity immediately before spending an existing reservation.

    The caller supplies the authenticated complete inventory, including this exact
    reservation. Remove only that one unstarted slot, then require a real free
    slot. This catches legacy/out-of-band arrivals since preparation without
    dropping another generation or relaunching an already bound original.
    """
    if decision is not None:
        decision.clear()
        decision.update(evaluated=True, allowed=False, reservation_validated=False,
                        capacity={"evaluated": False})
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
    if decision is not None:
        decision.update(reservation_validated=True, reserved_generation=reserved.generation,
                        capacity_excludes_reserved_generation=True)
    allowed = capacity(runs, other, census_complete=census_complete,
                       records_complete=records_complete,
                       decision=decision["capacity"] if decision is not None else None) > 0
    if decision is not None:
        decision["allowed"] = allowed
    return allowed


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
                       and r.role == admission_role(a)]
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
        converted = []
        for row in value[field]:
            cls = record_type
            if record_type is Admission and isinstance(row, dict) and set(row) == {f.name for f in fields(NativeAdmission)}:
                cls = NativeAdmission
            elif record_type is Admission and isinstance(row,dict) and set(row)=={f.name for f in fields(SourceAdmission)}:
                cls=SourceAdmission
            if not isinstance(row, dict) or set(row) != {f.name for f in fields(cls)}:
                raise ValueError('checkpoint record schema mismatch')
            converted.append(cls(**row))
        value[field] = tuple(converted)
    checkpoint = Checkpoint(**value)
    if (not _checkpoint_valid(checkpoint) or context['artifact'].get('name') != (
            f"ci-proof-checkpoint-{context['controller_run_id']}-{context['controller_attempt']}-{checkpoint.pr_number}")):
        raise ValueError('checkpoint identity or artifact name mismatch')
    return checkpoint


def authenticate_producer_origin(*, archive, artifact, producer_run, repository_id,
                                protected_producer_sha, repository, pull, source_commit):
    """Authenticate an original producer hint, NEVER an Admission or slot.

    The caller separately qualifies this exact protected producer workflow/step
    and credential-origin source. A payload string cannot prove its token kind.
    Artifact and run metadata, PR and exact commit are authenticated API rows.
    No expired/absent artifact or bot-name heuristic supplies origin evidence.
    """
    import hashlib
    data=_bounded_receipt_payload(archive,None)
    if (not isinstance(data,dict) or set(data)!={'schema','repository_id','producer_origin'}
            or data['schema']!='mastermind.ci-proof-producer-origin.v1'
            or not _positive(repository_id) or type(data['repository_id']) is not int
            or data['repository_id']!=repository_id):raise ValueError('producer envelope invalid')
    origin=data['producer_origin']
    fields={'producer_run_id','producer_run_attempt','workflow_path','workflow_ref','workflow_sha',
        'publishing_job','publishing_step','credential_origin','pr_number','published_source_head',
        'selected_target','original_generation','candidate_tree','projection_sha256',
        'pr_creation_user_id','pr_creation_login'}
    if (not isinstance(origin,dict) or set(origin)!=fields
            or any(not _positive(origin[k]) for k in ('producer_run_id','producer_run_attempt','pr_number','pr_creation_user_id'))
            or any(not _hex(origin[k],40) for k in ('workflow_sha','published_source_head','candidate_tree'))
            or not _hex(origin['original_generation'],12) or not _hex(origin['projection_sha256'],64)
            or origin['credential_origin']!='GITHUB_TOKEN'
            or origin['selected_target'] not in {'main','codex/merge-queue-pilot'}
            or origin['workflow_path']!='.github/workflows/commodity-sentinel.yml'
            or origin['publishing_job']!='shock' or origin['publishing_step']!='native_publication_stage'
            or not isinstance(repository,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository)
            or origin['workflow_ref']!=repository+'/'+origin['workflow_path']+'@refs/heads/main'
            or origin['workflow_sha']!=protected_producer_sha):raise ValueError('producer original tuple invalid')
    name=f"ci-proof-producer-origin-{origin['producer_run_id']}-{origin['producer_run_attempt']}-{origin['publishing_job']}-{origin['publishing_step']}-{origin['original_generation']}"
    if (not isinstance(artifact,dict) or not _positive(artifact.get('id')) or artifact.get('name')!=name
            or artifact.get('expired') is not False
            or artifact.get('digest')!='sha256:'+hashlib.sha256(archive).hexdigest()
            or not isinstance(artifact.get('workflow_run'),dict)
            or any(type(artifact['workflow_run'].get(k)) is not int for k in ('id','repository_id'))
            or artifact['workflow_run']['id']!=origin['producer_run_id']
            or artifact['workflow_run']['repository_id']!=repository_id
            or artifact['workflow_run'].get('head_sha')!=protected_producer_sha):
        raise ValueError('producer original artifact unavailable or misbound')
    if (not isinstance(producer_run,dict) or not _positive(producer_run.get('id'))
            or type(producer_run.get('run_attempt')) is not int
            or producer_run['id']!=origin['producer_run_id'] or producer_run['run_attempt']!=origin['producer_run_attempt']
            or producer_run.get('path') not in {origin['workflow_path'],origin['workflow_path']+'@refs/heads/main',origin['workflow_path']+'@'+protected_producer_sha}
            or producer_run.get('head_sha')!=protected_producer_sha or producer_run.get('head_branch')!='main'
            or producer_run.get('event') not in {'schedule','push','workflow_dispatch'}
            or type((producer_run.get('repository') or {}).get('id')) is not int
            or producer_run['repository']['id']!=repository_id
            or producer_run['repository'].get('full_name')!=repository):
        raise ValueError('producer original run unavailable or misbound')
    if (not isinstance(pull,dict) or type(pull.get('number')) is not int or pull['number']!=origin['pr_number']
            or pull.get('state')!='open' or (pull.get('head') or {}).get('sha')!=origin['published_source_head']
            or (pull.get('base') or {}).get('ref')!=origin['selected_target']
            or any(type(((pull.get(k) or {}).get('repo') or {}).get('id')) is not int
                or pull[k]['repo']['id']!=repository_id or pull[k]['repo'].get('full_name')!=repository for k in ('head','base'))
            or type((pull.get('user') or {}).get('id')) is not int
            or pull['user']['id']!=origin['pr_creation_user_id']
            or pull['user'].get('login')!=origin['pr_creation_login']
            or origin['pr_creation_user_id']!=41898282 or origin['pr_creation_login']!='github-actions[bot]'):
        raise ValueError('producer original PR creation/source binding changed')
    if (not isinstance(source_commit,dict) or source_commit.get('sha')!=origin['published_source_head']
            or (source_commit.get('tree') or {}).get('sha')!=origin['candidate_tree']):
        raise ValueError('producer published source tree changed')
    return dict(origin)
