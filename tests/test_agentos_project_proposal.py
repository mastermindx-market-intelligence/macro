"""tests/test_agentos_project_proposal.py — the DRAFT_ONLY compiler's contract.

Two halves, in this order of importance:

1. THE CANONICAL JOIN.  Every accepted draft must survive the REAL
   ``scripts.agentos`` round trip — ``FRONTMATTER_RE`` -> ``yaml.safe_load``
   -> ``check_workstream`` — with zero hard problems, and must parse back to
   exactly the authored record.  Nothing here stubs, mirrors or re-implements
   that parser; the checker's own enum sets are the only membership law, and
   this file asserts the compiler carries no parallel copy of them.

2. THE COMPILER'S OWN LAW.  Envelope shape, exact-key closure, the
   proposal-only state rule, byte budgets, character hygiene, determinism,
   detachment and purity.  Refused inputs raise ``ProposalError`` (a
   ``ValueError``); accepted inputs compile byte-identically every time.  One
   test compiles a full proposal under an I/O ban — ``Path.open`` /
   ``Path.write_text`` / ``subprocess`` / ``socket`` all patched to raise —
   which is the machine-checked form of: this compiler never proves a Git
   write, a store write, or a conversation.

Import bootstrap: in the integrated tree this file lives in ``tests/`` next to
``scripts/``, so one repo-root entry serves both imports.  In flat artifact
staging (module beside this file, no ``scripts/`` package) the canonical
checkout reaches us through the ambient ``PYTHONPATH`` — the same join the
parent integration runs.
"""

from __future__ import annotations

import copy
import hashlib
import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent

if (_HERE.parent / "scripts" / "agentos.py").is_file():  # integrated tree
    if str(_HERE.parent) not in sys.path:
        sys.path.insert(0, str(_HERE.parent))
    from scripts import agentos
    from scripts import agentos_project_proposal as proposal
else:  # flat artifact staging
    if str(_HERE) not in sys.path:
        sys.path.insert(0, str(_HERE))
    import agentos_project_proposal as proposal
    from scripts import agentos

compile_proposal = proposal.compile_proposal
ProposalError = proposal.ProposalError

# Explicit test data only — no defaults, no inference, no fixture files.
PROGRAMS = frozenset({"ledger-integrity", "terminal-onboarding"})
KEY = "AGENTOS-PROPOSAL-COMPILER"
COMMIT = "0123456789abcdef0123456789abcdef01234567"
REQUEST_ID = "req-2026-11-03.agentos.compiler.001"

OBJECTIVE = (
    "为 AgentOS 增加一个纯编译边界：把已授权的项目提案编译为 DRAFT_ONLY 的 WS 记录草稿。\n"
    "形如 key: value、&anch、*ref、{a: 1}、[x] 的 YAML-looking 文本必须原样保留，含\t制表符。\n"
    "A fenced line inside the value is content, not structure:\n"
    "---\n"
    "not-a-fence: true"
)
NEXT_ACTION = "Compile the positive fixture and join it through\nscripts.agentos.check_workstream\t(tab legal)."

OUTPUT_KEYS = {
    "schema",
    "state",
    "request_id",
    "request_sha256",
    "expected_commit",
    "work_ref",
    "path",
    "content_utf8",
    "content_sha256",
}


def make_request() -> dict:
    """One fully-authored proposal request — every field written out."""
    return {
        "schema": proposal.REQUEST_SCHEMA,
        "request_id": REQUEST_ID,
        "expected_commit": COMMIT,
        "record": {
            "key": KEY,
            "title": "Compile project proposals into DRAFT_ONLY workstream records",
            "objective": OBJECTIVE,
            "status": "proposed",
            "program": "ledger-integrity",
            "repos": ["macro"],
            "owner": "sol",
            "class": "build",
            "blast_radius": "reversible",
            "ambiguity": "specified",
            "waves": [
                {"id": "W1", "title": "Author the request envelope and exact-key law", "status": "todo"},
                {
                    "id": "W2",
                    "title": "Join the canonical checker and refuse hard problems",
                    "status": "todo",
                    "depends_on": ["W1"],
                },
            ],
            "next_action": NEXT_ACTION,
        },
    }


def compile_fixture() -> dict:
    return compile_proposal(make_request(), programs=set(PROGRAMS))


def canonical_request_bytes(request: dict) -> bytes:
    """The documented canonical form, computed independently of the compiler."""
    return json.dumps(
        request,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def deep(depth: int):
    """Build pathological nesting iteratively — no recursion in the fixture."""
    value: object = []
    for _ in range(depth):
        value = [value]
    return value


# ------------------------------------------------------------- canonical join


def test_draft_roundtrips_through_the_real_checker_with_no_hard_problems():
    result = compile_fixture()
    assert result["schema"] == "agentos.project_proposal.v1"
    assert result["state"] == "DRAFT_ONLY"
    match = agentos.FRONTMATTER_RE.match(result["content_utf8"])
    assert match, "compiled draft must open with a well-formed frontmatter fence"
    record = agentos.yaml.safe_load(match.group(1))
    assert isinstance(record, dict)
    assert set(record) == set(proposal.RECORD_KEYS), "frontmatter has no schema key and no runtime fields"
    problems = agentos.check_workstream(record, Path(result["path"]), set(PROGRAMS))
    assert [problem.rule for problem in problems if problem.hard] == []


def test_parsed_record_equals_the_authored_input_byte_for_byte():
    result = compile_fixture()
    match = agentos.FRONTMATTER_RE.match(result["content_utf8"])
    record = agentos.yaml.safe_load(match.group(1))
    # Dict equality: the compiler's fixed key order is presentation, values
    # must be the authored ones exactly — including ZH and YAML-looking text.
    assert record == make_request()["record"]
    assert record["objective"] == OBJECTIVE
    assert record["next_action"] == NEXT_ACTION


def test_body_carries_static_explanation_and_provenance_only():
    result = compile_fixture()
    match = agentos.FRONTMATTER_RE.match(result["content_utf8"])
    body = match.group(2)
    assert (
        "<!--\n"
        "agentos-project-proposal provenance (DRAFT_ONLY):\n"
        f"request_id: {result['request_id']}\n"
        f"request_sha256: {result['request_sha256']}\n"
        f"expected_commit: {result['expected_commit']}\n"
        "-->\n"
    ) in result["content_utf8"]
    # Caller goal/title never land in the body as unescaped markup.
    assert make_request()["record"]["title"] not in body
    assert "为 AgentOS" not in body
    assert "DRAFT_ONLY" in body


def test_enum_and_join_law_is_canonical_not_parallel():
    """The compiler must import the checker's sets, never re-declare them."""
    for name in ("CLASSES", "BLAST", "AMBIGUITY", "REPOS", "WORKSTREAM_STATUS", "WAVE_STATUS", "KEY_RE"):
        assert not hasattr(proposal, name), f"parallel enum copy: {name}"
    assert proposal.agentos is agentos, "the compiler must join the actual canonical module"


def test_membership_and_dependency_rules_come_from_the_checker():
    request = make_request()
    request["record"]["class"] = "mechanical"
    request["record"]["repos"] = ["macro", "terminal", "mastermind"]
    result = compile_proposal(request, programs=set(PROGRAMS))
    match = agentos.FRONTMATTER_RE.match(result["content_utf8"])
    record = agentos.yaml.safe_load(match.group(1))
    assert record["class"] in agentos.CLASSES
    assert set(record["repos"]) <= agentos.REPOS
    assert agentos.check_workstream(record, Path(result["path"]), set(PROGRAMS)) == []


# ------------------------------------------------------------- determinism


def test_compile_is_deterministic_and_hashes_are_independently_reproducible():
    first = compile_fixture()
    second = compile_fixture()
    assert first == second
    request = make_request()
    assert first["request_sha256"] == hashlib.sha256(canonical_request_bytes(request)).hexdigest()
    assert first["content_sha256"] == hashlib.sha256(first["content_utf8"].encode("utf-8")).hexdigest()
    # No self-referential hash: request digest covers the input, content
    # digest covers the output, and they are different quantities.
    assert first["request_sha256"] != first["content_sha256"]
    assert len(first["content_utf8"].encode("utf-8")) <= proposal.MAX_CONTENT_BYTES


def test_request_digest_is_over_the_input_not_the_rendered_output():
    result = compile_fixture()
    content_sha = hashlib.sha256(result["content_utf8"].encode("utf-8")).hexdigest()
    assert result["content_sha256"] == content_sha
    assert result["request_sha256"] != content_sha
    assert result["request_sha256"] == hashlib.sha256(canonical_request_bytes(make_request())).hexdigest()


def test_output_carries_exactly_the_contract_keys_and_references():
    result = compile_fixture()
    assert set(result) == OUTPUT_KEYS
    assert result["work_ref"] == "WS:" + KEY
    assert result["path"] == "agentos/workstreams/WS-" + KEY + ".md"
    assert issubclass(ProposalError, ValueError)


def test_program_from_the_alternate_supplied_catalog_compiles():
    request = make_request()
    request["record"]["program"] = "terminal-onboarding"
    request["record"]["repos"] = ["terminal"]
    result = compile_proposal(request, programs=set(PROGRAMS))
    match = agentos.FRONTMATTER_RE.match(result["content_utf8"])
    record = agentos.yaml.safe_load(match.group(1))
    assert agentos.check_workstream(record, Path(result["path"]), set(PROGRAMS)) == []


# ------------------------------------------------------------- detachment


def test_compile_does_not_mutate_the_frozen_request():
    request = make_request()
    before = copy.deepcopy(request)
    compile_proposal(request, programs=set(PROGRAMS))
    assert request == before


def test_earlier_output_is_immune_to_later_caller_mutation():
    request = make_request()
    first = compile_proposal(request, programs=set(PROGRAMS))
    request["record"]["title"] = "MUTATED AFTER THE FACT"
    request["record"]["repos"].append("terminal")
    request["record"]["waves"][0]["title"] = "MUTATED WAVE TITLE"
    assert "MUTATED AFTER THE FACT" not in first["content_utf8"]
    assert "MUTATED WAVE TITLE" not in first["content_utf8"]
    assert "Compile project proposals into DRAFT_ONLY workstream records" in first["content_utf8"]
    assert first == compile_fixture()
    # A later compile of the same (mutated) object reflects the new input; the
    # earlier result is untouched by either the mutation or the recompile.
    mutated = compile_proposal(request, programs=set(PROGRAMS))
    assert mutated["content_utf8"] != first["content_utf8"]
    assert mutated != first
    assert first == compile_fixture()


# ------------------------------------------------------------- purity


def test_compile_is_pure_no_files_subprocess_or_sockets(monkeypatch):
    """The compiler must work with every effect surface patched to raise."""
    def denial(surface):
        def _deny(*args, **kwargs):
            raise AssertionError("compiler attempted " + surface)
        return _deny

    for method in ("open", "read_text", "write_text", "read_bytes", "write_bytes",
                   "mkdir", "touch", "unlink", "rename", "replace", "chmod"):
        monkeypatch.setattr(Path, method, denial("Path." + method), raising=False)
    for name in ("run", "Popen", "check_output", "check_call", "call"):
        monkeypatch.setattr(subprocess, name, denial("subprocess." + name), raising=False)
    for name in ("socket", "create_connection", "getaddrinfo"):
        monkeypatch.setattr(socket, name, denial("socket." + name), raising=False)

    result = compile_fixture()
    assert result["state"] == "DRAFT_ONLY"
    match = agentos.FRONTMATTER_RE.match(result["content_utf8"])
    assert match and agentos.yaml.safe_load(match.group(1))["key"] == KEY


# ------------------------------------------------------------- refusals


def _set_record(**changes):
    def mutate(request):
        request["record"].update(changes)
    return mutate


def _drop_record(field):
    def mutate(request):
        del request["record"][field]
    return mutate


def _set_wave(index, **changes):
    def mutate(request):
        request["record"]["waves"][index].update(changes)
    return mutate


def _set_request(**changes):
    def mutate(request):
        request.update(changes)
    return mutate


def _drop_request(field):
    def mutate(request):
        del request[field]
    return mutate


def _wave_dep(index, deps):
    def mutate(request):
        request["record"]["waves"][index]["depends_on"] = deps
    return mutate


HEAVY = "\U00020000"  # one valid, control-free, four-byte UTF-8 character

REFUSALS = [
    # traversal — the key builds a path, so separators and dots are dead on arrival
    ("key-traversal-parent", _set_record(key="../EVIL")),
    ("key-traversal-slash", _set_record(key="A/B")),
    ("key-traversal-backslash", _set_record(key="A\\B")),
    ("key-dotdot-segment", _set_record(key="A-..-B")),
    # newline keys — '$' would admit these; fullmatch must not
    ("key-trailing-newline", _set_record(key=KEY + "\n")),
    ("key-embedded-newline", _set_record(key="AGENTOS\nCOMPILER")),
    ("key-lowercase", _set_record(key="agentos-compiler")),
    ("key-padded", _set_record(key=" " + KEY)),
    ("key-too-long", _set_record(key="A" * 65)),
    # commit shape
    ("commit-uppercase", _set_request(expected_commit=COMMIT.upper())),
    ("commit-short", _set_request(expected_commit=COMMIT[:39])),
    ("commit-long", _set_request(expected_commit=COMMIT + "aa")),
    ("commit-nonhex", _set_request(expected_commit="z" * 40)),
    ("commit-wrong-type", _set_request(expected_commit=40 * 0)),
    # request id shape
    ("request-id-empty", _set_request(request_id="")),
    ("request-id-leading-dash", _set_request(request_id="-abc")),
    ("request-id-too-long", _set_request(request_id="a" * 129)),
    ("request-id-space", _set_request(request_id="abc def")),
    ("request-id-newline", _set_request(request_id="abc\ndef")),
    ("request-id-nonascii", _set_request(request_id="réq-1")),
    ("request-id-wrong-type", _set_request(request_id=["req"])),
    # envelope closure
    ("request-extra-runtime", _set_request(runtime={"mode": "write-store"})),
    ("request-extra-store", _set_request(store="agentos")),
    ("request-missing-schema", _drop_request("schema")),
    ("request-missing-record", _drop_request("record")),
    ("request-wrong-schema", _set_request(schema="agentos.project_proposal.v1")),
    ("request-record-null", _set_request(record=None)),
    # record closure — runtime, derived, claim and ownership fields are refused
    ("record-extra-created", _set_record(created="2026-11-03")),
    ("record-extra-created-timestamp", _set_record(created="2026-11-03T00:00:00Z")),
    ("record-extra-updated", _set_record(updated="2026-11-02")),
    ("record-extra-claim", _set_record(claim={"by": "sol", "at": "2026-11-03", "expires": "2026-11-04"})),
    ("record-extra-runtime-ref", _set_record(runtime_ref={"service": "x", "deployed_sha": "y", "freshness_artifact": "z"})),
    ("record-extra-owns-paths", _set_record(owns_paths=["scripts/*"])),
    ("record-extra-wait", _set_record(wait={"kind": "external_action", "review_after": "2026-12-01", "condition": "x"})),
    ("record-extra-p0", _set_record(p0="P0.SOME")),
    # proposal-only state
    ("status-active", _set_record(status="active")),
    ("status-padded", _set_record(status="proposed ")),
    ("status-wrong-type", _set_record(status=["proposed"])),
    # owner law
    ("owner-missing", _drop_record("owner")),
    ("owner-empty", _set_record(owner="")),
    ("owner-blank", _set_record(owner="   ")),
    ("owner-padded", _set_record(owner=" sol ")),
    ("owner-too-long", _set_record(owner="o" * 201)),
    ("owner-control", _set_record(owner="sol\x00")),
    ("owner-wrong-type", _set_record(owner={"seat": "sol"})),
    # program law — membership in the supplied catalog only
    ("program-unknown", _set_record(program="no-such-program")),
    ("program-padded", _set_record(program=" ledger-integrity ")),
    ("program-empty", _set_record(program="")),
    ("program-too-long", _set_record(program="p" * 129)),
    ("program-wrong-type", _set_record(program={"key": "ledger-integrity"})),
    # repos law
    ("repo-duplicate", _set_record(repos=["macro", "macro"])),
    ("repo-unknown", _set_record(repos=["macro", "phoenix"])),
    ("repo-not-list", _set_record(repos="macro")),
    ("repo-empty-list", _set_record(repos=[])),
    ("repo-too-many", _set_record(repos=["macro", "terminal", "mastermind", "macro"])),
    ("repo-non-string", _set_record(repos=[1])),
    ("repo-wrong-case", _set_record(repos=["MACRO"])),
    # canonical enum fields
    ("class-invalid", _set_record(**{"class": "researchy"})),
    ("class-wrong-case", _set_record(**{"class": "Build"})),
    ("blast-invalid", _set_record(blast_radius="user-facing")),
    ("blast-padded", _set_record(blast_radius="reversible ")),
    ("ambiguity-invalid", _set_record(ambiguity="open-ended")),
    # text hygiene and limits
    ("title-empty", _set_record(title="")),
    ("title-too-long", _set_record(title="t" * 201)),
    ("title-wrong-type", _set_record(title=42)),
    ("title-control-char", _set_record(title="ok\x1b[0m")),
    ("objective-empty", _set_record(objective=" ")),
    ("objective-too-long", _set_record(objective="o" * 4001)),
    ("objective-carriage-return", _set_record(objective="a\rb")),
    ("objective-nul", _set_record(objective="a\x00b")),
    ("objective-wrong-type", _set_record(objective=["a"])),
    ("next-action-empty", _set_record(next_action="")),
    ("next-action-too-long", _set_record(next_action="n" * 1001)),
    ("next-action-bell", _set_record(next_action="x\x07")),
    # wave law
    ("wave-extra-pr", _set_wave(0, pr=1)),
    ("wave-extra-adoption", _set_wave(0, adoption="auto")),
    ("wave-extra-wait", _set_wave(0, wait={"kind": "external_action", "review_after": "2026-12-01", "condition": "x"})),
    ("wave-status-done", _set_wave(0, status="done")),
    ("wave-status-in-progress", _set_wave(1, status="in_progress")),
    ("wave-missing-id", lambda r: r["record"]["waves"][0].pop("id")),
    ("wave-missing-title", lambda r: r["record"]["waves"][0].pop("title")),
    ("wave-missing-status", lambda r: r["record"]["waves"][0].pop("status")),
    ("wave-id-padded", _set_wave(0, id=" W1")),
    ("wave-id-empty", _set_wave(0, id="")),
    ("wave-id-too-long", _set_wave(0, id="W" * 65)),
    ("wave-id-wrong-type", _set_wave(0, id=1)),
    ("wave-title-empty", _set_wave(0, title="")),
    ("wave-title-too-long", _set_wave(0, title="w" * 201)),
    ("wave-title-wrong-type", _set_wave(0, title=["t"])),
    ("wave-duplicate-id", _set_wave(1, id="W1")),
    ("waves-empty", _set_record(waves=[])),
    ("waves-not-list", _set_record(waves={"W1": {"id": "W1", "title": "t", "status": "todo"}})),
    ("waves-of-strings", _set_record(waves=["W1", "W2"])),
    ("waves-too-many", _set_record(waves=[{"id": f"W{i}", "title": "t", "status": "todo"} for i in range(1, 18)])),
    # wave dependencies
    ("wave-cycle-pair", _wave_dep(0, ["W2"])),
    ("wave-self-cycle", _wave_dep(0, ["W1"])),
    ("wave-dep-dangling", _wave_dep(1, ["W9"])),
    ("wave-dep-non-string-dropped-by-checker", _wave_dep(1, [3])),  # the checker would silently drop this edge
    ("wave-dep-not-a-list", _wave_dep(0, "W2")),
    ("wave-dep-null", _wave_dep(1, None)),
    # structural junk
    ("title-deep-junk", lambda r: r["record"].update(title=deep(5000))),
    ("waves-deep-junk", lambda r: r["record"].update(waves=deep(500))),
    ("objective-deep-junk", lambda r: r["record"].update(objective=deep(5000))),
    # over the canonical JSON budget (fields individually within their limits)
    ("request-over-canonical-budget", lambda r: (
        r["record"].update(
            objective=HEAVY * 4000,
            title=HEAVY * 200,
            next_action=HEAVY * 1000,
            waves=[
                {"id": "W1", "title": HEAVY * 200, "status": "todo"},
                {"id": "W2", "title": HEAVY * 200, "status": "todo", "depends_on": ["W1"]},
            ],
        )
    )),
    ("record-is-list", lambda r: r.update(record=["not", "a", "mapping"])),
]


@pytest.mark.parametrize("label,mutate", REFUSALS, ids=[label for label, _ in REFUSALS])
def test_refuses(label, mutate):
    request = make_request()
    mutate(request)
    with pytest.raises(ProposalError):
        compile_proposal(request, programs=set(PROGRAMS))


def test_refusal_messages_name_the_offending_field():
    request = make_request()
    request["record"]["key"] = "../EVIL"
    with pytest.raises(ProposalError, match="record.key"):
        compile_proposal(request, programs=set(PROGRAMS))
    request = make_request()
    request["record"]["objective"] = HEAVY * 4000 + "x"  # field limit, not the JSON budget
    with pytest.raises(ProposalError, match="record.objective"):
        compile_proposal(request, programs=set(PROGRAMS))
    request = make_request()
    request["record"]["status"] = "active"
    with pytest.raises(ProposalError, match="proposed"):
        compile_proposal(request, programs=set(PROGRAMS))


def test_over_budget_request_is_rejected_by_the_canonical_json_budget_alone():
    request = make_request()
    request["record"].update(
        objective=HEAVY * 4000,
        title=HEAVY * 200,
        next_action=HEAVY * 1000,
        waves=[
            {"id": "W1", "title": HEAVY * 200, "status": "todo"},
            {"id": "W2", "title": HEAVY * 200, "status": "todo", "depends_on": ["W1"]},
        ],
    )
    # The fixture must be over budget while every field is inside its own
    # limit — otherwise a field rule, not the budget, would be what fires.
    assert len(canonical_request_bytes(request)) > proposal.MAX_REQUEST_BYTES
    assert len(request["record"]["objective"]) <= proposal.MAX_OBJECTIVE_CHARS
    with pytest.raises(ProposalError, match="budget"):
        compile_proposal(request, programs=set(PROGRAMS))


def test_request_itself_is_not_a_mapping():
    for junk in ([], "request", None, 42, ()):
        with pytest.raises(ProposalError):
            compile_proposal(junk, programs=set(PROGRAMS))


@pytest.mark.parametrize(
    "catalog",
    [
        None,
        set(),
        ["ledger-integrity"],
        ("ledger-integrity",),
        {"ledger-integrity", 7},
        {" ledger-integrity "},
        {"", "ledger-integrity"},
        {"ledger-integrity", b"macro"},
    ],
    ids=[
        "none", "empty-set", "list", "tuple", "non-string-member",
        "padded-member", "empty-member", "bytes-member",
    ],
)
def test_refuses_invalid_program_catalog(catalog):
    with pytest.raises(ProposalError):
        compile_proposal(make_request(), programs=catalog)


def test_programs_omitted_fails_closed_at_the_call_site():
    with pytest.raises(TypeError):
        compile_proposal(make_request())  # keyword is required; absence never defaults


def test_deep_request_envelope_is_refused_without_recursing():
    request = make_request()
    request["request_id"] = {"a": deep(5000)}
    with pytest.raises(ProposalError):
        compile_proposal(request, programs=set(PROGRAMS))
