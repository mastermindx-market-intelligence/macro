"""Regression proof for the execution continuation law (DEC:EXECUTION-CONTINUATION-INVARIANTS).

Ten cases, one per observed failure. Each names its ENFORCEMENT LEVEL explicitly,
because the two levels are not interchangeable and pretending otherwise is how a
"covered" failure ships uncovered:

* HOOK — asserted against `.claude/hooks/ship_loop_guard.py` behaviour. The guard may
  only use facts it already holds (its own block ledger, the final message the harness
  hands it). Anything requiring it to infer lanes, custody, delegation scope or carrier
  state would make it a control plane, which repository law forbids.
* LAW — asserted as two-sided cross-surface parity: the rule is present, in the same
  words, on every surface that governs a session, and the negation that would reopen the
  failure is absent. This is the mechanism `tests/test_ship_loop_hold_wrapper.py` already
  uses for `DEC:HOLD-PARKS-SHIP-NOT-DIALOGUE`, and it exists because the last time only
  five of six law surfaces were corrected, the sixth silently kept the obsolete rule.

A LAW case is a real regression guard, not a spelling check: it fails the moment an edit
drops a clause, weakens a precondition, or adds an escape state to the closed set.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = ROOT / ".claude" / "hooks" / "ship_loop_guard.py"
SPEC = importlib.util.spec_from_file_location("execution_continuation_guard", HOOK_PATH)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


# Every surface a session of any client actually reads. CLAUDE.md is Claude-only;
# AGENTS.md is what Codex reads; the Cursor rule is a separate always-apply surface that
# no amount of editing the other two ever reaches; the decision record is the company
# memory of why. A rule on three of four is a rule one fleet does not have.
LAW_SURFACES = (
    "CLAUDE.md",
    "AGENTS.md",
    ".cursor/rules/execution-continuation.mdc",
    "agentos/decisions/DEC-EXECUTION-CONTINUATION-INVARIANTS.md",
)


# Markdown emphasis, heading and quote punctuation only. `_` is deliberately NOT
# stripped: it is load-bearing inside every state name this file checks for.
_MARKUP = re.compile(r"[*`#>]")


def _law_text(relative: str) -> str:
    """Return one law surface normalized for a claim about MEANING, not layout.

    Three normalizations, each answering a way a real clause has hidden from a real
    parity check: whitespace collapses (so a clause straddling a Markdown line wrap is
    still present, and — far worse — a banned phrase cannot evade its own check by
    being re-wrapped); emphasis punctuation is stripped (`**never**` and `never` are
    the same rule, and a surface should not go dark because one file bolds a word);
    and case is folded (a sentence opening a bullet is capitalized and the same
    sentence mid-paragraph is not).
    """
    path = ROOT / relative
    if path.exists():
        raw = path.read_text(encoding="utf-8")
    else:
        proc = subprocess.run(
            ("git", "show", f"HEAD:{relative}"),
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        assert proc.returncode == 0, f"{relative} unreadable: {proc.stderr}"
        raw = proc.stdout
    return " ".join(_MARKUP.sub("", raw).split()).lower()


def _clause(text: str) -> str:
    """Normalize an expected clause the same way, so the two sides are comparable."""
    return " ".join(_MARKUP.sub("", text).split()).lower()


def _on_every_surface(*clauses: str) -> None:
    for relative in LAW_SURFACES:
        text = _law_text(relative)
        for clause in clauses:
            assert _clause(clause) in text, (
                f"{relative} is missing the binding clause {clause!r}"
            )


def _state(tmp_path: Path, **overrides) -> Path:
    tmp_path.mkdir(parents=True, exist_ok=True)
    path = tmp_path / "continuation-state.json"
    state = {
        "root": str(tmp_path),
        "start_head": "0" * 40,
        "baseline": {},
        "last_blocker": "",
        "blocker_count": 0,
        "total_blocks": 0,
        "external_blocks": 0,
    }
    state.update(overrides)
    GUARD._save(path, state)
    return path


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ("git", *args), cwd=repo, text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=True,
    ).stdout.strip()


def _commitless_session(tmp_path: Path) -> tuple[Path, Path]:
    """A real repository where the session has produced nothing yet.

    This is the shape the whole ship chain skips (`_stop` returns as soon as HEAD still
    equals `start_head`), and therefore the shape every failure in this family escaped
    through: a delegation that returned nothing, a checkpoint, a status note, a context
    rotation. The fixture has to be a real repo rather than a stub, because "clean stop"
    is only meaningful if the ordinary gates genuinely had their chance to fire.
    """
    # A fresh directory per call: case 10 runs the whole terminal vocabulary through
    # this fixture inside one tmp_path.
    repo = Path(tempfile.mkdtemp(dir=tmp_path, prefix="repo-"))
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    (repo / "kept.txt").write_text("baseline\n", encoding="utf-8")
    _git(repo, "add", "kept.txt")
    _git(repo, "commit", "-m", "initial")
    path = repo.parent / f"{repo.name}-state.json"
    GUARD._save(
        path,
        {
            "root": str(repo),
            "start_head": _git(repo, "rev-parse", "HEAD"),
            "baseline": GUARD._fingerprint(repo),
            "last_blocker": "",
            "blocker_count": 0,
            "total_blocks": 0,
            "external_blocks": 0,
        },
    )
    return repo, path


def _stop_emission(monkeypatch, capsys, tmp_path, final: str):
    """Run `_stop` on a commitless session and return what it emitted, or None."""
    repo, path = _commitless_session(tmp_path)
    for name in ("_github_slug", "_fast_forwarded_onto_main"):
        monkeypatch.setattr(
            GUARD,
            name,
            lambda *_a, _name=name, **_k: pytest.fail(f"{_name} ran on a commitless session"),
        )
    GUARD._stop(repo, path, {"hook_event_name": "Stop", "last_assistant_message": final})
    out = capsys.readouterr().out.strip()
    return json.loads(out) if out else None


def _stop_emission_before_any_probe(monkeypatch, capsys, tmp_path, final: str):
    """Same, with the tree snapshot itself wired to fail.

    The `more_work_exists` gate sits ahead of the dirty snapshot on purpose, so a
    self-declared unfinished session is judged without a single git call. Making the
    probe explode proves the ORDER, rather than merely asserting the verdict a cheaper
    path happens to produce.
    """
    repo, path = _commitless_session(tmp_path)
    monkeypatch.setattr(
        GUARD, "_fingerprint", lambda *_a, **_k: pytest.fail("the tree was probed before the gate")
    )
    monkeypatch.setattr(
        GUARD, "_run", lambda *_a, **_k: pytest.fail("git ran before the gate")
    )
    GUARD._stop(repo, path, {"hook_event_name": "Stop", "last_assistant_message": final})
    out = capsys.readouterr().out.strip()
    return json.loads(out) if out else None


def _block_reason(tmp_path, capsys, code: str, *, repeats: int = 1, final: str = "working") -> str:
    """Return the block text a session actually receives for `code`.

    Deliberately routed through `_block` rather than through `continuation_directive`.
    A composer that is never called is the exact defect this repository has shipped
    five times (the `::warning` lines emitted through a prefixing logger, dead in CI
    and green in review), so every behavioural claim below is asserted against the
    emitted block.
    """
    path = _state(tmp_path / f"blk-{code}-{repeats}")
    payload = {"stop_hook_active": True, "last_assistant_message": final}
    reason = ""
    for _ in range(repeats):
        GUARD._block(path, GUARD._load(path), payload, code, "detail")
        reason = json.loads(capsys.readouterr().out.strip())["reason"]
    return reason

# --------------------------------------------------------------------------------------
# Case 1 — one review/tool lane blocked while product work remains.
# --------------------------------------------------------------------------------------


def test_case_1_a_blocked_lane_never_reads_as_a_finished_mission(tmp_path, capsys):
    """HOOK + LAW.

    The observed failure: one review lane, provider, or tool goes down and the session
    reports the whole mission as over. Before this change every block closed with the
    same sentence — "Continue the task and complete commit -> ... -> live verification"
    — which says nothing about the other lanes, so a session with four healthy lanes and
    one dead one read the block as terminal for all five.
    """
    for code in ("unmerged", "ci_failed", "render_pending", "uncommitted", "live_stale"):
        reason = _block_reason(tmp_path, capsys, code)
        assert "Freeze the blocked lane only" in reason, code
        assert "Independent authorized lanes continue" in reason, code
        assert "never a finished mission" in reason, code

    _on_every_surface(
        "BLOCKER -> freeze the affected lane -> check independent useful lanes -> continue",
        "ALL_SCOPED_LANES_BLOCKED",
        "must name the lanes it checked",
    )


# --------------------------------------------------------------------------------------
# Case 2 — CI queue blocked with a durable watcher already armed.
# --------------------------------------------------------------------------------------


def test_case_2_a_wait_owned_outside_the_session_is_never_answered_by_polling(tmp_path, capsys):
    """HOOK + LAW.

    `gh_quota_guard.py` shape 7 measured ~25 consecutive Stop cycles of single
    `gh pr checks` polls by a session that already had a watcher armed at 150s, and its
    docstring names the mechanism: the Stop block reads as a demand to demonstrate a
    fresh attempt. The fix is in the block text itself, so the demand is no longer made.
    """
    for code in sorted(GUARD.WAITING_BLOCKERS):
        reason = _block_reason(tmp_path, capsys, code)
        assert "WAIT owned outside this session" in reason, code
        assert "does not answer this block" in reason, code
        assert "one-line hold note" in reason, code
        assert "never on the queue" in reason, code

    # A block the session itself must act on is NOT a wait: telling it to go do
    # something else would be the opposite error.
    for code in ("uncommitted", "unpushed", "unsafe_branch", "render_failed"):
        assert "WAIT owned outside" not in _block_reason(tmp_path, capsys, code), code

    _on_every_surface(
        "WAITING EXTERNAL -> durable watcher/owner; do useful parallel principal work; "
        "do not burn principal capacity polling",
        "satisfied by a one-line hold note, never by a fresh poll",
    )


# --------------------------------------------------------------------------------------
# Case 3 — delegated Fable program CEO vs ordinary Claude worker.
# --------------------------------------------------------------------------------------


def test_case_3_chairman_delegation_outranks_the_default_role_inside_its_scope():
    """LAW (two-sided).

    A hook cannot see delegation scope and must not guess it, so this is law — but it is
    law with both halves pinned, because each half alone produces a different failure. A
    seat that forgets the override re-asks Sol for decisions it already owns (the Agent
    Fabric stall). A seat that forgets the leak rule takes one program's delegation as
    general authority, which is the same error `DEC:SOL-HOLD-IS-A-MERGE-BARRIER` already
    names for per-PR merge grants.
    """
    _on_every_surface(
        # the defaults survive
        "Sol is the default AI CEO / system owner",
        "bounded workers",
        "Fable is scarce principal capacity by default",
        # the override
        "an explicit Chairman delegation overrides those defaults inside its stated "
        "scope, and a default role assumption never overrides it back",
        # the leak rule
        "never leaks outside its stated scope",
        # and no second authority plane is created here
        "authority map",
        "promotes no worker to principal",
    )


# --------------------------------------------------------------------------------------
# Case 4 — delegation surface unavailable, lawful direct execution still available.
# --------------------------------------------------------------------------------------


def test_case_4_an_unavailable_delegation_surface_does_not_end_execution():
    """LAW (two-sided, all four preconditions pinned).

    The observed failure: the Fabric, a pool, or a spawn is unavailable, and the session
    treats that as proof that the work cannot proceed — while it still holds the tools
    and the custody to do the bounded work itself. Each precondition is pinned
    separately: dropping any one of them turns a guarded permission into a blanket one.
    """
    _on_every_surface(
        "NO WORKER STARTED + lawful principal tools/custody + no conflict/EFFECT_UNKNOWN "
        "-> direct bounded execution may continue",
        "is not evidence that execution is impossible",
        "no worker actually started",
        "lawful tools and custody",
        "no other owner is working the same artifact",
    )


# --------------------------------------------------------------------------------------
# Case 5 — delegation surface unavailable AND direct execution is not lawful.
# --------------------------------------------------------------------------------------


def test_case_5_when_direct_execution_is_unlawful_the_stop_is_named_not_silent():
    """LAW (the negative case, which is the half that usually goes missing).

    Case 4's permission is worthless — and dangerous — without its complement. When a
    precondition fails, the session owes a NAMED state and the exact missing thing, not
    a quiet exit and not a second worker racing the first on a contested artifact.
    """
    _on_every_surface(
        "ALL_SCOPED_LANES_BLOCKED",
        "EXACT_HUMAN_GATE",
        "never a silent stop",
        "second worker on a contested artifact",
    )
    _on_every_surface("naming the exact missing thing")


# --------------------------------------------------------------------------------------
# Case 6 — effect-unknown timeout.
# --------------------------------------------------------------------------------------


def test_case_6_effect_unknown_reconciles_on_the_same_carrier():
    """LAW, plus one HOOK-side property.

    A timed-out post or an ambiguous dispatch is the classic double-act generator: the
    session cannot see whether the act landed, retries blind, and the irreversible thing
    happens twice. The law names same-carrier reconciliation. The hook-side property is
    that `EFFECT_UNKNOWN` is a LAWFUL end state — a session in that condition must be
    able to classify honestly rather than be pushed into claiming an outcome.
    """
    assert "EFFECT_UNKNOWN" in GUARD.SESSION_END_STATES
    assert "EFFECT_UNKNOWN" not in GUARD.NON_TERMINAL_SESSION_END_STATES
    assert GUARD.declared_session_end_state("SESSION END: EFFECT_UNKNOWN") == "EFFECT_UNKNOWN"

    _on_every_surface(
        "EFFECT_UNKNOWN -> same-carrier reconciliation; never blind retry/failover",
        "same carrier that performed it",
    )


# --------------------------------------------------------------------------------------
# Case 7 — a checkpoint or status note produced while the parent outcome is unfinished.
# --------------------------------------------------------------------------------------


def test_case_7_a_record_of_work_is_never_the_outcome_it_describes(monkeypatch, tmp_path, capsys):
    """HOOK + LAW.

    Two mechanisms, because the failure has two shapes. A session that wrote a
    checkpoint and stopped with work outstanding is refused by the `more_work_exists`
    gate — and refused on the COMMITLESS path, which is the one the whole ship chain
    used to skip. A session that overclaims in its final message gets the gap named
    against the rung its own block proves.
    """
    emitted = _stop_emission_before_any_probe(
        monkeypatch, capsys, tmp_path, "Checkpoint written.\nSESSION END: MORE_WORK_EXISTS"
    )
    assert emitted is not None, "a self-declared unfinished session must not stop clean"
    assert emitted["decision"] == "block"
    assert "SHIP LOOP more_work_exists" in emitted["reason"]
    assert "not a stopping state" in emitted["reason"]

    conflation = GUARD.delivery_claim_conflation("unmerged", "PRODUCTION_PROOF")
    assert "PRODUCTION_PROOF" in conflation and "CI" in conflation
    assert "none implies the next" in conflation
    # And the same gap is named in the block the session receives, from the final
    # message the guard has already read - no extra probe, no extra request.
    overclaim = _block_reason(
        tmp_path, capsys, "unmerged", final="Wave is SHIPPED and ACCEPTED."
    )
    assert "claims `ACCEPTANCE`" in overclaim
    assert "reaches only `CI`" in overclaim

    _on_every_surface("never the outcome it describes")


# --------------------------------------------------------------------------------------
# Case 8 — ACK/QUEUED mistaken for START/RUNNING (and every other rung confusion).
# --------------------------------------------------------------------------------------


def test_case_8_the_delivery_rungs_are_distinct_and_none_implies_the_next():
    """HOOK + LAW."""
    assert GUARD.DELIVERY_LADDER == (
        "ACK",
        "QUEUED",
        "START",
        "RUNNING",
        "DELIVERED",
        "CI",
        "MERGED",
        "PRODUCTION_PROOF",
        "ACCEPTANCE",
    )
    assert len(set(GUARD.DELIVERY_LADDER)) == len(GUARD.DELIVERY_LADDER)

    # An acknowledgement or a queue entry never reaches a started worker.
    assert GUARD.DELIVERY_LADDER.index("ACK") < GUARD.DELIVERY_LADDER.index("QUEUED")
    assert GUARD.DELIVERY_LADDER.index("QUEUED") < GUARD.DELIVERY_LADDER.index("START")
    assert GUARD.DELIVERY_LADDER.index("START") < GUARD.DELIVERY_LADDER.index("RUNNING")

    # Claim detection reads the shop vocabulary, never ordinary prose.
    assert GUARD.strongest_delivery_claim("the PR is MERGED and the wave was ACCEPTED") == "ACCEPTANCE"
    assert GUARD.strongest_delivery_claim("the worker is QUEUED") == "QUEUED"
    assert GUARD.strongest_delivery_claim("ci is red and nothing merged or accepted yet") == ""

    # An overclaim against what the block proves is named; an honest claim is silent.
    assert GUARD.delivery_claim_conflation("unmerged", "MERGED")
    assert GUARD.delivery_claim_conflation("ci_failed", "ACCEPTANCE")
    assert GUARD.delivery_claim_conflation("unmerged", "DELIVERED") == ""
    assert GUARD.delivery_claim_conflation("ci_failed", "MERGED") == ""
    # A code that proves nothing about delivery makes no claim about a claim.
    assert GUARD.delivery_claim_conflation("github_unreachable", "ACCEPTANCE") == ""

    # "CI" and "ACK" stay OUT of the claim vocabulary on purpose: both are ordinary
    # English in these reports, and a false advisory line is cheap but not free.
    assert "CI" not in GUARD._DELIVERY_CLAIM_TOKENS
    assert "ACK" not in GUARD._DELIVERY_CLAIM_TOKENS

    _on_every_surface(
        "ACK -> QUEUED -> START -> RUNNING -> DELIVERED -> CI -> MERGED -> "
        "PRODUCTION_PROOF -> ACCEPTANCE",
        "none implies the next",
    )


# --------------------------------------------------------------------------------------
# Case 9 — context rotation mistaken for completion.
# --------------------------------------------------------------------------------------


def test_case_9_context_rotation_is_a_harness_event_not_an_outcome(tmp_path, capsys):
    """HOOK + LAW.

    A compaction or resume must not hand a session a clean slate: if the block ledger
    reset, a session could rotate context and stop free on the next Stop, and the escape
    ladders — which count blocks precisely so an unsatisfiable gate cannot trap anyone —
    would become unreachable in the other direction too.
    """
    path = _state(tmp_path, last_blocker="unmerged", blocker_count=4, total_blocks=9,
                  external_blocks=2, start_head="a" * 40)

    for source in ("resume", "compact"):
        GUARD._session_start(tmp_path, path, {"source": source})
        capsys.readouterr()
        state = GUARD._load(path)
        assert state["total_blocks"] == 9, source
        assert state["blocker_count"] == 4, source
        assert state["external_blocks"] == 2, source
        assert state["start_head"] == "a" * 40, source

    _on_every_surface("is a harness event", "not an outcome")


# --------------------------------------------------------------------------------------
# Case 10 — a short, expensive session: early is fine, padding is not.
# --------------------------------------------------------------------------------------


def test_case_10_reaching_the_outcome_early_stops_clean_and_only_that_does(
    monkeypatch, tmp_path, capsys
):
    """HOOK + LAW, both directions.

    The gate must refuse exactly one state and no others. Refusing more would punish a
    session that genuinely reached its outcome or its human gate in ten minutes — and
    the incentive that creates is padding, which costs real money in a shop whose burn
    is context times turns.
    """
    for state in GUARD.SESSION_END_STATES:
        if state in GUARD.NON_TERMINAL_SESSION_END_STATES:
            continue
        emitted = _stop_emission(monkeypatch, capsys, tmp_path, f"Done.\nSESSION END: {state}")
        assert emitted is None, f"{state} is a lawful terminal classification and must stop clean"

    # No declaration at all also stops clean here: the guard never invents a verdict
    # from silence, and the ordinary ship chain below still judges a session that
    # actually produced a commit.
    assert _stop_emission(monkeypatch, capsys, tmp_path, "all done") is None

    _on_every_surface(
        "never pad a session to look substantial, and never stop while authorized work remains",
    )


# --------------------------------------------------------------------------------------
# Cross-cutting: the closed vocabulary, and the ladder that keeps the refusal escapable.
# --------------------------------------------------------------------------------------


def test_the_session_start_injection_actually_carries_the_law(tmp_path, capsys):
    """HOOK, and the surface with the most leverage and the least visible failure.

    `_session_start`'s `additionalContext` is the ONE place this law reaches a session
    that never opens a repository file — Claude, Codex, Cursor and every other client
    get it the same way. It is also the easiest thing in the guard to break silently:
    hook stdout must be a SINGLE JSON value, and a second emitted object makes the whole
    output unparseable, at which point the harness drops the injection and nothing says
    so. The guard's own `_stop` carries that warning in a comment; nothing asserted it.

    That is the `::warning`-through-a-logger defect in another costume: a call that
    reviews as correct, runs clean, and produces nothing. So this parses the emitted
    bytes rather than reading the source string.
    """
    repo, path = _commitless_session(tmp_path)
    path.unlink()  # force the startup branch to mint fresh state
    GUARD._session_start(repo, path, {"source": "startup"})

    emitted = capsys.readouterr().out
    payload = json.loads(emitted)  # fails loudly if a second value was ever printed
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    context = payload["hookSpecificOutput"]["additionalContext"]

    # The ship chain the law must never be read as releasing.
    assert "MANDATORY SHIP LOOP" in context
    # Each invariant, in the compressed form a bootstrap line can carry.
    for clause in (
        "EXECUTION CONTINUATION LAW",
        "freeze",
        "independent authorized lanes",
        "bounded direct execution may continue",
        "never spend principal capacity polling",
        "no-delta cycles",
        "DO_NOT_REDO unless materially invalidated",
        "reconciled on the same carrier",
        "SESSION END:",
        "MORE_WORK_EXISTS is never a valid stopping state",
    ):
        assert clause in context, f"the bootstrap injection dropped {clause!r}"
    # The full closed vocabulary, so a session is told the whole set, not a subset.
    for state in GUARD.SESSION_END_STATES:
        assert state in context, f"the bootstrap injection omits {state}"
    # And the whole delivery ladder, since conflating two rungs needs both named.
    for rung in GUARD.DELIVERY_LADDER:
        assert rung in context, f"the bootstrap injection omits the rung {rung}"


def test_the_session_end_vocabulary_is_closed_and_identical_in_code_and_law():
    """A code-to-law binding, the strongest form available for a rule a hook enforces.

    Drift in either direction is a real defect: a state named in law but unknown to the
    guard is unenforced, and a state known to the guard but absent from law is a rule no
    session was told about.
    """
    assert set(GUARD.SESSION_END_STATES) == {
        "PROVEN_OUTCOME",
        "EXACT_HUMAN_GATE",
        "EFFECT_UNKNOWN",
        "ALL_SCOPED_LANES_BLOCKED",
        "DURABLE_EXECUTION_RUNNING",
        "MORE_WORK_EXISTS",
    }
    assert GUARD.NON_TERMINAL_SESSION_END_STATES == frozenset({"MORE_WORK_EXISTS"})

    decoys = (
        "CHECKPOINT_WRITTEN",
        "CONTEXT_ROTATED",
        "STATUS_POSTED",
        "WORK_CONTINUES",
        "PARTIAL_PROGRESS",
    )
    for relative in LAW_SURFACES:
        text = _law_text(relative)
        for state in GUARD.SESSION_END_STATES:
            assert state.lower() in text, f"{relative} does not name the end state {state}"
        for decoy in decoys:
            assert decoy.lower() not in text, f"{relative} added an escape state: {decoy}"
        assert _clause("MORE_WORK_EXISTS is never a valid stopping state") in text, relative
        assert _clause("MORE_WORK_EXISTS is a valid") not in text, relative


def test_a_declaration_is_required_and_a_quotation_is_not_one():
    """The refusal reads a marked declaration, never a mention.

    Without the marker a session quoting its own law — "MORE_WORK_EXISTS is never a
    valid stopping state" — would block itself, which is exactly the class of
    self-inflicted unsatisfiable gate this repository has been bitten by before.
    """
    assert GUARD.declared_session_end_state("SESSION END: MORE_WORK_EXISTS") == "MORE_WORK_EXISTS"
    assert GUARD.declared_session_end_state("**SESSION END STATE:** PROVEN_OUTCOME") == "PROVEN_OUTCOME"
    assert GUARD.declared_session_end_state("- session_end: EXACT_HUMAN_GATE") == "EXACT_HUMAN_GATE"
    assert GUARD.declared_session_end_state("MORE_WORK_EXISTS is never a valid stopping state") == ""
    assert GUARD.declared_session_end_state("I will not declare a session end state") == ""
    assert GUARD.declared_session_end_state("") == ""
    assert GUARD.declared_session_end_state("SESSION END: SOMETHING_ELSE") == ""
    # A confused message resolves fail-closed toward continuing the work.
    assert (
        GUARD.declared_session_end_state("SESSION END: PROVEN_OUTCOME\nSESSION END: MORE_WORK_EXISTS")
        == "MORE_WORK_EXISTS"
    )


def test_the_refusal_is_escapable_through_the_ordinary_any_code_ladder(tmp_path, capsys):
    """A gate with no reachable exit is how the remedy becomes the incident.

    `more_work_exists` is deliberately INTERNAL — the session can always satisfy it by
    finishing the work or reclassifying honestly — so it carries the high 10-consecutive
    ceiling rather than the low external one, and it is not in `EXTERNAL_BLOCKERS`.
    """
    assert GUARD.MORE_WORK_EXISTS not in GUARD.EXTERNAL_BLOCKERS

    path = _state(tmp_path)
    payload = {"stop_hook_active": True, "last_assistant_message": "SHIP LOOP BLOCKED: evidence"}
    for _ in range(9):
        GUARD._block(path, GUARD._load(path), payload, GUARD.MORE_WORK_EXISTS, "still open")
        assert json.loads(capsys.readouterr().out.strip())["decision"] == "block"
    GUARD._block(path, GUARD._load(path), payload, GUARD.MORE_WORK_EXISTS, "still open")
    assert capsys.readouterr().out.strip() == "", "the any-code ladder must release at 10"


def test_a_repeat_block_reads_as_a_no_delta_cycle(tmp_path, capsys):
    """HOOK.

    The old body was byte-identical on block 1 and block 25, which is what an unchanging
    instruction buys: an unchanging response. Two equivalent cycles now say so, and name
    the three exits.
    """
    assert "No-delta cycle" not in _block_reason(tmp_path, capsys, "unmerged", repeats=1)
    second = _block_reason(tmp_path, capsys, "unmerged", repeats=2)
    assert "No-delta cycle 2 on `unmerged`" in second
    assert "a third identical attempt is banned" in second
    assert "Change tactic, change lane, or change owner" in second

    _on_every_surface("2 equivalent no-delta cycles -> change tactic/lane/owner")


def test_accepted_work_is_not_redone_without_a_material_invalidator():
    """LAW (two-sided).

    The failure is a fresh session re-deriving, re-proposing, or re-building work that
    was already accepted, because its own context does not contain the acceptance. So
    the law names what does NOT count as an invalidator, not only what does.
    """
    _on_every_surface(
        "accepted work -> DO_NOT_REDO unless materially invalidated",
        "material invalidator",
        "DO_NOT_REBUILD.md",
    )
    _on_every_surface("lost transcript", "absent memory")


def test_the_continuation_law_never_reads_as_a_release_from_the_ship_chain():
    """LAW (two-sided), and the likeliest way a future edit breaks this.

    "A blocked lane is not a finished mission" is one paraphrase away from "a blocked
    lane lets me stop", which would hand every session a release from the unmerged
    contract the project owner restored by hand on 2026-08-12. The two laws compose;
    neither releases the other, and every surface has to say so.
    """
    _on_every_surface(
        "This law does not weaken the ordinary ship chain: both bind, and neither "
        "releases the other.",
        "never a reason to leave an unmerged pull request",
    )


def test_the_law_creates_no_second_control_plane():
    """The non-goal, pinned. Every surface must say what it does not create.

    `DEC:AGENTOS-HOME-IS-MACRO` and the Executive OS prohibition on
    `duplicate_control_planes` are both load-bearing here: a continuation law is exactly
    the kind of rule that grows a scheduler if nobody writes down that it must not.
    """
    decision = _law_text("agentos/decisions/DEC-EXECUTION-CONTINUATION-INVARIANTS.md")
    for forbidden in ("control plane", "lifecycle store", "queue", "watcher", "memory system"):
        assert forbidden in decision, f"the record must disclaim creating a {forbidden}"
    assert "creates no strategic state" in decision
    assert "widens no credential" in decision
