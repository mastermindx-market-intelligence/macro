"""Incumbent ThemeState generation mechanics, never a producer or rights owner.

Public SUCCESSOR authority is deliberately unwired. ControlledOwnerVerifier is
an explicitly synthetic test interface restricted to temporary roots; it cannot
authorize runtime publication. Legacy API initialization retains old semantics
without claiming natural first-family proof. Direct-file reader cutover is held.
"""
from __future__ import annotations
import base64
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from dataclasses import dataclass
import jsonschema

PRIMARY = "data/neuralweb/theme_state.json"
MIRROR = "site/neuralwebdata/theme_state.json"
HISTORY = "data/neuralweb/theme_phase_history.jsonl"
CURRENT = "data/neuralweb/theme_state_current.json"
GENERATIONS = "data/neuralweb/theme_state_generations"
PENDING = "data/neuralweb/.theme_state_pending.json"
LOCK = "data/neuralweb/.theme_state_publish.lock"
SCHEMA = "neuralweb.theme_state_generation.v1"
ID_RE = re.compile(r"^tsg-[0-9a-f]{64}$")
_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "contracts/theme_graph/theme_state_generation.v1.schema.json"

class GenerationUnavailable(ValueError):
    """Typed unavailable/refused boundary, never an empty history."""
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)

def fail(reason):
    raise GenerationUnavailable(reason)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,allow_nan=False,separators=(",",":")).encode()

def parse(raw):
    try:
        return json.loads(raw.decode("utf-8"),parse_constant=lambda x: fail("NONFINITE_JSON"))
    except (UnicodeError,json.JSONDecodeError):
        fail("MALFORMED_JSON")

def b64(raw):
    return None if raw is None else base64.b64encode(raw).decode()

def unb64(value):
    try:
        return None if value is None else base64.b64decode(value,validate=True)
    except (ValueError,TypeError):
        fail("MALFORMED_BYTES")

def instant(value):
    try:
        if not isinstance(value,str):
            raise ValueError
        t=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
        if t.tzinfo is None or t.utcoffset() is None:
            raise ValueError
        return t.astimezone(dt.timezone.utc)
    except ValueError:
        fail("INVALID_PRECISE_CLOCK")

@dataclass(frozen=True)
class History:
    raw: bytes
    rows_json: str
    @property
    def rows(self):
        return json.loads(self.rows_json)

def preflight_phase_history(raw):
    """Scan exact prefix under incumbent latest-as_of predecessor semantics."""
    from . import thematic_state as legacy
    rows=[]
    latest={}
    seen=set()
    for line in raw.splitlines():
        if not line.strip():
            continue
        row=parse(line)
        if not isinstance(row,dict) or row.get("schema")!=legacy.HISTORY_SCHEMA:
            fail("HISTORY_FOREIGN_SCHEMA")
        tid=row.get("theme_id"); date=row.get("as_of")
        if not isinstance(tid,str) or not tid or not isinstance(date,str):
            fail("HISTORY_INVALID_KEY")
        try:
            if dt.date.fromisoformat(date).isoformat()!=date:
                raise ValueError
        except ValueError:
            fail("HISTORY_INVALID_DATE")
        instant(row.get("ts"))
        key=(tid,date)
        if key in seen:
            fail("HISTORY_DUPLICATE_DAILY_KEY")
        seen.add(key)
        for name in ("foresight_stage","scoring_lifecycle","radar_lifecycle","divergence_quadrant"):
            if name not in row or (row[name] is not None and not isinstance(row[name],str)):
                fail("HISTORY_INVALID_TRACKED_TYPE")
        evidence=row.get("evidence_z")
        if not isinstance(evidence,dict):
            fail("HISTORY_INVALID_EVIDENCE")
        for value in evidence.values():
            if value is not None and (type(value) not in (int,float)):
                fail("HISTORY_INVALID_EVIDENCE")
        canonical(row)  # rejects nonfinite optional fields without stripping them
        previous=latest.get(tid)
        expected=legacy._row_hash(previous) if previous is not None else None
        if "prev_hash" not in row or row["prev_hash"]!=expected:
            fail("HISTORY_CHAIN_MISMATCH")
        if previous is None or date>previous["as_of"]:
            latest[tid]=row
        rows.append(row)
    return History(raw,canonical(rows).decode())

def plan_phase_history(artifact,history,*,recorded_at):
    from . import thematic_state as legacy
    instant(recorded_at)
    if artifact.get("schema")!="neuralweb.theme_state.v1":
        fail("HISTORY_INCOMING_SCHEMA")
    date=artifact.get("as_of")
    try:
        if dt.date.fromisoformat(date).isoformat()!=date:
            raise ValueError
    except (ValueError,TypeError):
        fail("HISTORY_INCOMING_DATE")
    blocks=artifact.get("themes")
    if not isinstance(blocks,list):
        fail("HISTORY_INCOMING_POPULATION")
    ids=[b.get("theme_id") if isinstance(b,dict) else None for b in blocks]
    if any(not isinstance(i,str) or not i for i in ids) or len(ids)!=len(set(ids)):
        fail("HISTORY_INCOMING_DUPLICATE_OR_INVALID_ID")
    seen={(r["theme_id"],r["as_of"]) for r in history.rows}
    latest={}
    for r in history.rows:
        if r["theme_id"] not in latest or r["as_of"]>latest[r["theme_id"]]["as_of"]:
            latest[r["theme_id"]]=r
    result=[]
    for block in blocks:
        tid=block["theme_id"]
        if (tid,date) in seen:
            continue
        state=legacy._extract_tracked_state(block)
        previous=latest.get(tid)
        transition=previous is None or state!={k:previous[k] for k in state}
        heartbeat=previous is not None and (dt.date.fromisoformat(date)-dt.date.fromisoformat(previous["as_of"])).days>=legacy._HEARTBEAT_DAYS
        if not transition and not heartbeat:
            continue
        baskets=block.get("basket_intel") or []
        first=baskets[0] if baskets else {}
        div=block.get("divergence_board") or {}
        row={"schema":legacy.HISTORY_SCHEMA,"as_of":date,"ts":recorded_at,"theme_id":tid,
             **state,"evidence_z":{"crowding":first.get("crowding"),"divergence_score":div.get("divergence")},
             "prev_hash":legacy._row_hash(previous) if previous is not None else None}
        result.append(row)
        seen.add((tid,date))
    tail=b"\n".join(canonical(r) for r in result)
    if tail:
        tail=(b"" if not history.raw or history.raw.endswith((b"\n",b"\r")) else b"\n")+tail+b"\n"
    preflight_phase_history(history.raw+tail)
    return tail,len(result)

def confined(root,relative):
    root=Path(root)
    if root.is_symlink():
        fail("FAMILY_SYMLINK")
    root=root.resolve()
    path=root/relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        fail("FAMILY_PATH_ESCAPE")
    for p in [path,*path.parents]:
        if p==root.parent:
            break
        if p.is_symlink():
            fail("FAMILY_SYMLINK")
    return path

def read(root,relative):
    p=confined(root,relative)
    try:
        return p.read_bytes()
    except FileNotFoundError:
        return None
    except OSError:
        fail("FAMILY_UNREADABLE")

def entry_preflight(root,*,legacy_api=False,allow_pending=False):
    if Path(root).is_symlink():
        fail("FAMILY_SYMLINK")
    root=Path(root).resolve()
    for rel in (PRIMARY,MIRROR,HISTORY,CURRENT,GENERATIONS,PENDING,LOCK):
        confined(root,rel)
    raw=read(root,HISTORY)
    current=read(root,CURRENT)
    aliases={p:read(root,p) for p in (PRIMARY,MIRROR)}
    if raw is None and (current is not None or any(v is not None for v in aliases.values())):
        fail("HISTORY_MISSING_PRIOR_FAMILY")
    if raw is None and not legacy_api:
        fail("FIRST_FAMILY_AUTHORITY_UNAVAILABLE")
    history=preflight_phase_history(raw or b"")
    if read(root,PENDING) is not None and not allow_pending:
        fail("PENDING_GENERATION_OWNS_PREFIX")
    if current is not None:
        ref=parse(current)
        accepted = _validate_ref(root,ref)
        if any(raw != unb64(accepted["compatibility_b64"]) for raw in aliases.values()):
            fail("ACCEPTED_ALIAS_FRONTIER_MISMATCH")
        # Current tape can include only the accepted publication frontier here.
        if sha(history.raw)!=ref["history_sha256"] or len(history.raw)!=ref["history_length"]:
            fail("ACCEPTED_HISTORY_FRONTIER_MISMATCH")
    _check_generation_population(root,current)
    return {"root":str(root),"history":history,"history_exists":raw is not None,
            "current":current,"aliases":aliases}

def _accepted_ancestry(root,current):
    accepted = {}
    while current is not None:
        ref = parse(current)
        gid = ref.get("generation_id") if isinstance(ref,dict) else None
        if gid in accepted:
            fail("GENERATION_LINEAGE_CYCLE")
        plan = _validate_ref(root,ref)
        accepted[gid] = plan
        current = unb64(plan["prior_reference_b64"])
    return accepted

def _check_generation_population(root,current,pending_id=None):
    accepted = _accepted_ancestry(root,current)
    directory = confined(root,GENERATIONS)
    if directory.exists():
        if not directory.is_dir():
            fail("GENERATION_DIRECTORY_INVALID")
        for child in directory.iterdir():
            if child.is_symlink() or not child.is_dir() or not ID_RE.fullmatch(child.name):
                fail("GENERATION_POPULATION_INVALID")
            if child.name not in accepted and child.name != pending_id:
                fail("ORPHAN_GENERATION_UNAVAILABLE")
    return accepted

def cas_entry(root,entry):
    if read(root,PENDING) is not None:
        fail("PENDING_GENERATION_OWNS_PREFIX")
    _check_generation_population(root,read(root,CURRENT))
    if str(Path(root).resolve())!=entry["root"]:
        fail("FAMILY_ROOT_MISMATCH")
    if read(root,HISTORY)!=(entry["history"].raw if entry["history_exists"] else None):
        fail("HISTORY_CAS_MISMATCH")
    if read(root,CURRENT)!=entry["current"]:
        fail("REFERENCE_CAS_MISMATCH")
    if any(read(root,p)!=v for p,v in entry["aliases"].items()):
        fail("ALIAS_CAS_MISMATCH")

@contextlib.contextmanager
def family_lock(root):
    p=confined(root,LOCK)
    p.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(p,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd);fail("OWNER_BUSY")
    try:
        yield
    finally:
        fcntl.flock(fd,fcntl.LOCK_UN)
        os.close(fd)

def write_atomic(root,relative,raw):
    p=confined(root,relative)
    p.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix=".theme-state-",dir=p.parent)
    try:
        with os.fdopen(fd,"wb") as f:
            f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(name,p)
        dfd=os.open(p.parent,os.O_RDONLY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        if os.path.exists(name): os.unlink(name)

def append_legacy(root,artifact):
    from . import thematic_state as legacy
    entry=entry_preflight(root,legacy_api=True)
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    tail,n=plan_phase_history(artifact,entry["history"],recorded_at=now)
    if not legacy._ledger_advance_enabled() or not tail:
        return 0
    with family_lock(root):
        cas_entry(root,entry)
        # Do not append after an accepted generation behind its sealed frontier.
        if entry["current"] is not None:
            fail("ACCEPTED_GENERATION_REQUIRES_BUILDER")
        write_atomic(root,HISTORY,entry["history"].raw+tail)
    return n

def producer_bindings():
    """Exact executing owner closure; hashes identify code, never grant rights."""
    from . import thematic_state, envelope, theme_state_adapter
    from engine.theme_graph import theme_state_production
    from scripts import build_thematic_state
    files = {
        "engine/neuralweb/theme_state_generation.py": Path(__file__),
        "engine/neuralweb/thematic_state.py": Path(thematic_state.__file__),
        "engine/neuralweb/envelope.py": Path(envelope.__file__),
        "scripts/build_thematic_state.py": Path(build_thematic_state.__file__),
        "contracts/theme_graph/theme_state_generation.v1.schema.json": _SCHEMA_PATH,
        "engine/neuralweb/theme_state_adapter.py": Path(theme_state_adapter.__file__),
        "engine/theme_graph/theme_state_production.py": Path(theme_state_production.__file__),
        "contracts/theme_graph/theme_state.v2.schema.json": Path(theme_state_production.__file__).resolve().parents[2] / "contracts/theme_graph/theme_state.v2.schema.json",
    }
    try:
        return {name: sha(path.read_bytes()) for name,path in files.items()}
    except OSError:
        fail("GENERATION_PRODUCER_UNAVAILABLE")


def captured_frontier(bundle):
    snapshot=bundle.snapshot()
    result={}
    for name,path in (("legacy_predecessor",PRIMARY),("legacy_phase_history",HISTORY)):
        source=snapshot["sources"][name]
        if source["path"]!=path:
            fail("CAPTURED_LEGACY_FRONTIER_SCOPE_MISMATCH")
        raw=unb64(source["bytes_b64"])
        if raw is None:
            if (source["availability"]!="UNAVAILABLE" or source["null_reason"]!="SOURCE_MISSING"
                    or source["sha256"] is not None):
                fail("CAPTURED_LEGACY_FRONTIER_UNAVAILABLE")
        elif source["availability"]!="AVAILABLE" or source["null_reason"] is not None or source["sha256"]!=sha(raw):
            fail("CAPTURED_LEGACY_FRONTIER_INVALID")
        if raw is not None and name=="legacy_phase_history":
            preflight_phase_history(raw)
        if raw is not None and name=="legacy_predecessor":
            value=parse(raw)
            if type(value) is not dict or value.get("schema")!="neuralweb.theme_state.v1" or type(value.get("themes")) is not list:
                fail("CAPTURED_LEGACY_PREDECESSOR_INVALID")
        result[name]={key:source[key] for key in ("path","availability","null_reason","sha256","bytes_b64")}
    return result


def _match_captured_entry(frontier,primary,history,history_exists):
    if (unb64(frontier["legacy_predecessor"]["bytes_b64"])!=primary
            or unb64(frontier["legacy_phase_history"]["bytes_b64"])!=(history if history_exists else None)):
        fail("CAPTURED_LEGACY_FRONTIER_MISMATCH")


def _validate_owner_witness(plan,state):
    from . import theme_state_adapter as adapter
    try:
        raw=unb64(plan["owner_bundle_b64"])
        bundle=adapter.OwnerBundle(raw.decode("utf-8"),plan["source_bundle_sha256"])
        snapshot=bundle.snapshot()
        frontier=captured_frontier(bundle)
        if canonical(frontier)!=canonical(plan["captured_frontier"]):
            fail("CAPTURED_LEGACY_FRONTIER_MISMATCH")
        if plan["rollback_of"] is None:
            _match_captured_entry(frontier,unb64(plan["prior_primary_b64"]),unb64(plan["history_b64"]),plan["history_exists"])
        if snapshot["query"]!=plan["query"]:
            fail("GENERATION_SOURCE_QUERY_MISMATCH")
        expected=adapter.compare_production_shadow(state,bundle)
        if canonical(expected)!=canonical(plan["shadow"]):
            fail("GENERATION_SHADOW_BINDING_MISMATCH")
    except GenerationUnavailable:
        raise
    except (ValueError,TypeError,KeyError,AttributeError,UnicodeError):
        fail("GENERATION_OWNER_WITNESS_INVALID")


def _plan_digest(plan):
    return sha(canonical({k:v for k,v in plan.items() if k!="generation_id"}))

def _validate_reference_shape(ref):
    if type(ref) is not dict or set(ref)!={"schema","generation_id","plan_sha256","history_sha256","history_length","activation_at"} or ref["schema"]!="neuralweb.theme_state_current.v1":
        fail("INVALID_ACCEPTED_REFERENCE")
    if type(ref["history_length"]) is not int or ref["history_length"] < 0:
        fail("INVALID_ACCEPTED_REFERENCE")
    for field in ("plan_sha256","history_sha256"):
        if type(ref[field]) is not str or re.fullmatch(r"[0-9a-f]{64}",ref[field]) is None:
            fail("INVALID_ACCEPTED_REFERENCE")
    if type(ref["generation_id"]) is not str or not ID_RE.fullmatch(ref["generation_id"]):
        fail("INVALID_GENERATION_ID")
    instant(ref["activation_at"])

def _validate_ref(root,ref):
    _validate_reference_shape(ref)
    gid=ref["generation_id"]
    if not isinstance(gid,str) or not ID_RE.fullmatch(gid):
        fail("INVALID_GENERATION_ID")
    raw=read(root,GENERATIONS+"/"+gid+"/plan.json")
    if raw is None or sha(raw)!=ref["plan_sha256"]:
        fail("ACCEPTED_PLAN_UNAVAILABLE")
    plan=parse(raw);validate_generation(plan)
    if plan["generation_id"]!=gid or plan["root"]!=str(Path(root).resolve()):
        fail("ACCEPTED_PLAN_SCOPE_MISMATCH")
    if ref["activation_at"]!=plan["activation_at"]:
        fail("ACCEPTED_ACTIVATION_MISMATCH")
    for name,key in (("state.json","state_b64"),("legacy.json","compatibility_b64")):
        if read(root,GENERATIONS+"/"+gid+"/"+name)!=unb64(plan[key]):
            fail("IMMUTABLE_GENERATION_BYTES_MISMATCH")
    post=unb64(plan["history_b64"])+unb64(plan["tail_b64"])
    if ref["history_sha256"]!=sha(post) or ref["history_length"]!=len(post):
        fail("ACCEPTED_HISTORY_REF_MISMATCH")
    return plan

def validate_generation(plan):
    if type(plan) is not dict or plan.get("producer_bindings")!=producer_bindings():
        fail("GENERATION_PRODUCER_VERSION_MISMATCH")
    schema=json.loads(_SCHEMA_PATH.read_text())
    errors=list(jsonschema.Draft202012Validator(schema).iter_errors(plan))
    if errors: fail("GENERATION_CLOSED_CONTRACT")
    if plan["generation_id"]!="tsg-"+_plan_digest(plan):
        fail("GENERATION_DIGEST_MISMATCH")
    instant(plan["activation_at"])
    from engine.theme_graph import theme_state_production as production
    state=parse(unb64(plan["state_b64"]));production.validate_state(state)
    _validate_owner_witness(plan,state)
    compat=parse(unb64(plan["compatibility_b64"]))
    if (sha(unb64(plan["state_b64"]))!=plan["digests"]["state_raw"]
        or state["state_sha256"]!=plan["digests"]["state_semantic"]
        or sha(canonical(state["compatibility"]["projection"]))!=plan["digests"]["projection_unstamped"]
        or sha(canonical(compat))!=plan["digests"]["projection_stamped"]
        or sha(unb64(plan["compatibility_b64"]))!=plan["digests"]["compatibility_raw"]):
        fail("GENERATION_OBJECT_DIGEST_MISMATCH")
    # The incumbent envelope explicitly owns these five refreshed fields.
    # Pre-stamp full projection has a distinct digest; source fields remain exact.
    from . import envelope
    projection=state["compatibility"]["projection"]
    if canonical(envelope.strip_envelope(compat)) != canonical(envelope.strip_envelope(projection)):
        fail("GENERATION_PROJECTION_MISMATCH")
    if set(compat) != set(envelope.strip_envelope(projection)) | set(envelope.ENVELOPE_KEYS):
        fail("GENERATION_ENVELOPE_KEYS_MISMATCH")
    if compat["inputs_hash"] != envelope._compute_inputs_hash(envelope.strip_envelope(projection)):
        fail("GENERATION_ENVELOPE_INPUT_HASH_MISMATCH")
    envelope_clock = instant(compat["produced_at"])
    activation = instant(plan["activation_at"])
    if ((plan["rollback_of"] is None and envelope_clock != activation)
            or envelope_clock > activation or envelope_clock < instant(state["generated_at"])):
        fail("GENERATION_ENVELOPE_CLOCK_MISMATCH")
    history=preflight_phase_history(unb64(plan["history_b64"]))
    tail=unb64(plan["tail_b64"])
    preflight_phase_history(history.raw+tail)
    if plan["digests"]["history_prefix"]!=sha(history.raw) or plan["digests"]["history_tail"]!=sha(tail):
        fail("GENERATION_HISTORY_DIGEST_MISMATCH")
    for k in ("prior_primary_b64","prior_mirror_b64","prior_reference_b64"):
        unb64(plan[k])
    if not plan["history_exists"] and history.raw:
        fail("GENERATION_HISTORY_EXISTENCE_MISMATCH")
    added = len(preflight_phase_history(history.raw+tail).rows) - len(history.rows)
    if added != plan["history_rows_added"]:
        fail("GENERATION_HISTORY_COUNT_MISMATCH")
    selection = plan["rollback_selection"]
    if (plan["rollback_of"] is None) != (selection is None):
        fail("ROLLBACK_SELECTION_MISMATCH")
    if selection is not None:
        if selection["generation_id"] != plan["rollback_of"] or selection["state_generated_at"] != state["generated_at"] or tail:
            fail("ROLLBACK_SELECTION_MISMATCH")
        if selection["state_raw_sha256"] != plan["digests"]["state_raw"]:
            fail("ROLLBACK_STATE_BYTES_MISMATCH")
    previous=unb64(plan["prior_reference_b64"])
    if previous is not None:
        ref=parse(previous)
        _validate_reference_shape(ref)
        if instant(ref["activation_at"])>instant(plan["activation_at"]):
            fail("ACTIVATION_REGRESSION")
    if instant(state["generated_at"])>instant(plan["activation_at"]):
        fail("ACTIVATION_PRECEDES_STATE")
    if plan["source_bundle_sha256"]!=state["bundle_ref"]["sha256"] or plan["query"]!={"effective_at":state["effective_at"],"known_at":state["known_at"]}:
        fail("GENERATION_SOURCE_QUERY_MISMATCH")
    if selection is None:
        expected_tail, expected_count = plan_phase_history(compat,history,recorded_at=plan["activation_at"])
        if tail != expected_tail or plan["history_rows_added"] != expected_count:
            fail("GENERATION_TAIL_DIFFERS_FROM_NATIVE_PLAN")
    return state

def prepare_generation(bundle,*,root,generated_at,activation_at,entry,previous=None,correction_reason=None):
    from . import theme_state_adapter as adapter
    from .envelope import stamp
    if str(Path(root).resolve())!=entry["root"]: fail("FAMILY_ROOT_MISMATCH")
    if entry["current"] is None and entry["history"].raw:
        # No authenticated legacy-frontier bridge is currently wired.
        fail("LEGACY_FRONTIER_AUTHORITY_UNAVAILABLE")
    frontier=captured_frontier(bundle)
    _match_captured_entry(frontier,entry["aliases"][PRIMARY],entry["history"].raw,entry["history_exists"])
    bindings=producer_bindings()
    if entry["current"] is not None:
        prior_plan = _validate_ref(root,parse(entry["current"]))
        actual_prior = validate_generation(prior_plan)
        if previous is not None and canonical(previous) != canonical(actual_prior):
            fail("CORRECTION_PRIOR_NOT_ACCEPTED")
        if correction_reason is not None:
            previous = actual_prior
    elif previous is not None:
        fail("CORRECTION_PRIOR_NOT_ACCEPTED")
    result=adapter.compose_production_from_owner_bundle(bundle,generated_at=generated_at,
                                                      previous=previous,correction_reason=correction_reason)
    compat=stamp(result["legacy_candidate"],artifact_id="theme-state",
                 now=instant(activation_at))  # exactly once; actual transaction clock
    tail,n=plan_phase_history(compat,entry["history"],recorded_at=activation_at)
    state=result["state"]
    plan={"schema":SCHEMA,"generation_id":"","root":entry["root"],"activation_at":activation_at,
          "state_b64":b64(canonical(state)),"compatibility_b64":b64(canonical(compat)),
          "history_b64":b64(entry["history"].raw),"history_exists":entry["history_exists"],"tail_b64":b64(tail),
          "prior_primary_b64":b64(entry["aliases"][PRIMARY]),"prior_mirror_b64":b64(entry["aliases"][MIRROR]),
          "prior_reference_b64":b64(entry["current"]),"history_rows_added":n,
          "source_bundle_sha256":bundle.bundle_sha256,"query":{"effective_at":state["effective_at"],"known_at":state["known_at"]},
          "shadow":result["shadow"],"rollback_of":None,"rollback_selection":None,
          "producer_bindings":bindings,"owner_bundle_b64":b64(bundle.payload_json.encode()),
          "captured_frontier":frontier,
          "publication_status":"UNAVAILABLE","authority_reason":"ACTUAL_OWNER_PUBLICATION_RESOLVER_NOT_WIRED",
          "digests":{"state_raw":sha(canonical(state)),"state_semantic":state["state_sha256"],
                     "projection_unstamped":sha(canonical(state["compatibility"]["projection"])),
                     "projection_stamped":sha(canonical(compat)),"compatibility_raw":sha(canonical(compat)),
                     "history_prefix":sha(entry["history"].raw),"history_tail":sha(tail)}}
    plan["generation_id"]="tsg-"+_plan_digest(plan)
    validate_generation(plan)
    return plan

@dataclass(frozen=True)
class ControlledDecision:
    root: str
    generation_id: str
    action: str
    checked_at: str
    status: str
    owner_event: str
    purpose: str = "CONTROLLED_TEST_ONLY"

class ControlledOwnerVerifier:
    """Injected trusted fixture interface; NOT an authentication implementation."""
    def current_action_at(self,plan,*,action):
        """Real check instant by default; controlled fixtures may supply their clock."""
        return dt.datetime.now(dt.timezone.utc).isoformat()

    def resolve(self,plan,*,action):
        raise NotImplementedError

def _controlled_authority(root,plan,verifier,action,action_at):
    if not isinstance(verifier,ControlledOwnerVerifier):
        fail("OWNER_PUBLICATION_AUTHORITY_UNAVAILABLE")
    # No CLI/public build can inject this interface. Bound temporary fixture only.
    resolved_root=Path(root).resolve()
    temp=Path(tempfile.gettempdir()).resolve()
    if not resolved_root.is_relative_to(temp) or resolved_root==temp:
        fail("CONTROLLED_TEST_ROOT_REQUIRED")
    receipt=verifier.resolve(plan,action=action)
    if type(receipt) is not ControlledDecision or receipt.purpose!="CONTROLLED_TEST_ONLY":
        fail("OWNER_PUBLICATION_AUTHORITY_UNAVAILABLE")
    if receipt.status!="ACCEPTED": fail("OWNER_PUBLICATION_REJECTED")
    if receipt.root!=str(resolved_root) or receipt.generation_id!=plan["generation_id"] or receipt.action!=action or type(receipt.owner_event) is not str or not receipt.owner_event.strip():
        fail("OWNER_PUBLICATION_SCOPE_MISMATCH")
    if instant(action_at)<instant(plan["activation_at"]) or instant(receipt.checked_at)!=instant(action_at):
        fail("OWNER_PUBLICATION_CHECK_NOT_EXACT")
    return receipt

def _preimage(plan):
    return {HISTORY:unb64(plan["history_b64"]) if plan["history_exists"] else None,
            PRIMARY:unb64(plan["prior_primary_b64"]),MIRROR:unb64(plan["prior_mirror_b64"]),
            CURRENT:unb64(plan["prior_reference_b64"])}

def _reference(plan):
    post=unb64(plan["history_b64"])+unb64(plan["tail_b64"])
    return canonical({"schema":"neuralweb.theme_state_current.v1","generation_id":plan["generation_id"],
        "plan_sha256":sha(canonical(plan)),"history_sha256":sha(post),"history_length":len(post),
        "activation_at":plan["activation_at"]})

def publish_generation(root,plan,*,controlled_verifier=None,fault=None,resume=False):
    """Only controlled mechanics can execute; ordinary production use refuses."""
    validate_generation(plan)
    if str(Path(root).resolve())!=plan["root"]:fail("FAMILY_ROOT_MISMATCH")
    action="ROLLBACK" if plan["rollback_of"] else "PUBLISH"
    if not isinstance(controlled_verifier,ControlledOwnerVerifier):
        fail("OWNER_PUBLICATION_AUTHORITY_UNAVAILABLE")
    action_at=controlled_verifier.current_action_at(plan,action=action)
    instant(action_at)
    _controlled_authority(root,plan,controlled_verifier,action,action_at)
    validate_generation(plan)  # current owner check cannot substitute a changed producer/witness
    for rel in (PRIMARY,MIRROR,HISTORY,CURRENT,GENERATIONS,PENDING,LOCK):
        confined(root,rel)
    expected=_preimage(plan)
    if plan["prior_reference_b64"] is not None:
        previous_plan = _validate_ref(root,parse(unb64(plan["prior_reference_b64"])))
        state = validate_generation(plan)
        if state["correction"] is not None and plan["rollback_of"] is None:
            actual_prior = validate_generation(previous_plan)
            prior = state["correction"]["previous"]
            if any(prior[k] != actual_prior[k] for k in ("generation_id","state_sha256","generated_at")):
                fail("CORRECTION_PRIOR_NOT_ACCEPTED")
    if plan["rollback_selection"] is not None:
        selection = plan["rollback_selection"]
        historical_raw = read(root,GENERATIONS+"/"+selection["generation_id"]+"/plan.json")
        if historical_raw is None or sha(historical_raw) != selection["plan_sha256"]:
            fail("ROLLBACK_SELECTION_UNAVAILABLE")
        historical = parse(historical_raw)
        validate_generation(historical)
        historical_post = unb64(historical["history_b64"])+unb64(historical["tail_b64"])
        if (selection["generation_id"] not in _accepted_ancestry(root,unb64(plan["prior_reference_b64"]))
                or sha(historical_post) != selection["history_sha256"]
                or len(historical_post) != selection["history_length"]
                or plan["state_b64"] != historical["state_b64"]
                or plan["compatibility_b64"] != historical["compatibility_b64"]):
            fail("ROLLBACK_SELECTION_MISMATCH")
    history_now=read(root,HISTORY)
    post=unb64(plan["history_b64"])+unb64(plan["tail_b64"])
    from . import thematic_state as legacy
    if unb64(plan["tail_b64"]) and not legacy._ledger_advance_enabled():
        fail("HISTORY_NIGHTLY_OWNER_REQUIRED")
    if history_now is not None: preflight_phase_history(history_now)
    pending=read(root,PENDING)
    gid=plan["generation_id"];base=GENERATIONS+"/"+gid
    sealed=read(root,base+"/plan.json")
    _check_generation_population(root,read(root,CURRENT),gid if resume else None)
    ref=_reference(plan)
    if read(root,CURRENT)==ref and pending is None:
        _validate_ref(root,parse(ref))
        if history_now!=post or any(read(root,p)!=unb64(plan["compatibility_b64"]) for p in (PRIMARY,MIRROR)):
            fail("ACCEPTED_FAMILY_BYTES_MISMATCH")
        return {"status":"ALREADY_ACCEPTED","generation_id":gid}
    if resume:
        if pending!=canonical(plan) or sealed!=canonical(plan):
            fail("ORIGINAL_SEALED_PLAN_UNAVAILABLE")
        for p,old in expected.items():
            new=post if p==HISTORY else ref if p==CURRENT else unb64(plan["compatibility_b64"])
            if read(root,p) not in (old,new):
                fail("RESUME_COLLATERAL_BYTES")
    else:
        if pending is not None or sealed is not None:
            fail("PENDING_OR_ORPHAN_GENERATION")
        for p,raw in expected.items():
            if read(root,p)!=raw: fail("ENTRY_CAS_MISMATCH")
    def hit(stage):
        if fault is not None: fault(stage)
    with family_lock(root):
        # Repeat exact authority/CAS inside process-shared lock.
        _controlled_authority(root,plan,controlled_verifier,action,action_at)
        validate_generation(plan)  # recheck immediately before stage/alias/history effects
        if resume:
            if read(root,PENDING)!=canonical(plan) or read(root,base+"/plan.json")!=canonical(plan):
                fail("ORIGINAL_SEALED_PLAN_UNAVAILABLE")
            for p,old in expected.items():
                new=post if p==HISTORY else ref if p==CURRENT else unb64(plan["compatibility_b64"])
                if read(root,p) not in (old,new): fail("RESUME_COLLATERAL_BYTES")
            for name,key in (("state.json","state_b64"),("legacy.json","compatibility_b64")):
                if read(root,base+"/"+name)!=unb64(plan[key]):fail("IMMUTABLE_GENERATION_BYTES_MISMATCH")
        else:
            if read(root,PENDING) is not None:fail("PENDING_GENERATION_OWNS_PREFIX")
            for p,raw in expected.items():
                if read(root,p)!=raw:fail("ENTRY_CAS_MISMATCH")
            write_atomic(root,PENDING,canonical(plan));hit("stage")
            write_atomic(root,base+"/state.json",unb64(plan["state_b64"]))
            write_atomic(root,base+"/legacy.json",unb64(plan["compatibility_b64"]))
            write_atomic(root,base+"/plan.json",canonical(plan));hit("seal")
        for rel,stage in ((PRIMARY,"primary"),(MIRROR,"mirror")):
            if read(root,rel)!=unb64(plan["compatibility_b64"]):
                write_atomic(root,rel,unb64(plan["compatibility_b64"]))
            hit(stage)
        if read(root,HISTORY)!=post:
            write_atomic(root,HISTORY,post)
        hit("tail")
        if any(read(root,p)!=unb64(plan["compatibility_b64"]) for p in (PRIMARY,MIRROR)) or read(root,HISTORY)!=post:
            fail("FAMILY_POSTIMAGE_MISMATCH")
        _controlled_authority(root,plan,controlled_verifier,action,action_at)
        validate_generation(plan)  # accepted reference never seals a drifted producer/witness
        write_atomic(root,CURRENT,ref);hit("ref")
        confined(root,PENDING).unlink()
    return {"status":"CONTROLLED_ACCEPTED","generation_id":gid}

def resume_generation(root,plan,**kwargs):
    return publish_generation(root,plan,resume=True,**kwargs)

def rollback_generation(root,previous_id,*,activation_at,controlled_verifier=None,fault=None):
    if not isinstance(previous_id,str) or not ID_RE.fullmatch(previous_id):
        fail("INVALID_GENERATION_ID")
    entry=entry_preflight(root)
    raw=read(root,GENERATIONS+"/"+previous_id+"/plan.json")
    if raw is None:fail("ROLLBACK_GENERATION_UNAVAILABLE")
    old=parse(raw);validate_generation(old)
    ancestry = _accepted_ancestry(root,entry["current"])
    if previous_id not in ancestry:
        fail("ROLLBACK_NOT_ACCEPTED_ANCESTOR")
    _validate_ref(root,parse(_reference(old)))
    plan=dict(old)
    plan.update(activation_at=activation_at,history_b64=b64(entry["history"].raw),history_exists=True,
                tail_b64=b64(b""),history_rows_added=0,prior_primary_b64=b64(entry["aliases"][PRIMARY]),
                prior_mirror_b64=b64(entry["aliases"][MIRROR]),prior_reference_b64=b64(entry["current"]),
                rollback_of=previous_id,
                rollback_selection={"generation_id":previous_id,"plan_sha256":sha(raw),
                    "history_sha256":sha(unb64(old["history_b64"])+unb64(old["tail_b64"])),
                    "history_length":len(unb64(old["history_b64"])+unb64(old["tail_b64"])),
                    "state_generated_at":validate_generation(old)["generated_at"],
                    "state_raw_sha256":old["digests"]["state_raw"]})
    plan["digests"]=dict(old["digests"],history_prefix=sha(entry["history"].raw),history_tail=sha(b""))
    plan["generation_id"]="tsg-"+_plan_digest(plan)
    validate_generation(plan)
    return publish_generation(root,plan,controlled_verifier=controlled_verifier,fault=fault)
