"""Tests for the "publish required fence contexts" step of .github/workflows/fences.yml.

The step is an actions/github-script v7 call, so these tests parse the ACTUAL
JavaScript out of the workflow YAML and execute it under Node with an in-process
mock of the github-script environment (``github``, ``core``, ``context``,
``require``, ``process.env``) — the same shape the action injects. No network:
every GitHub call is a local mock that models what the Checks API would retain.

Contract under test (response-loss recovery, per invocation):

* at most ONE ``checks.create`` per context, always with an explicit
  ``request: { retries: 0 }``;
* a thrown create OR a malformed success receipt is ambiguous and triggers
  exactly ONE bounded read-only ``checks.listForRef`` page
  (exact head + check_name, filter: all, per_page: 100, page: 1) — never a
  retry, an update, a second page or a poll;
* the receipt — direct or recovered — must be complete and match the exact
  binding: GitHub Actions app (15368), repo, head, run, attempt, check name,
  terminal status/conclusion, output title+summary and details_url. An omitted
  field is a mismatch (fail closed); absence of the exact binding is UNKNOWN,
  never proof of no-write;
* any unresolvable outcome raises a fixed EFFECT_UNKNOWN error and stops every
  later create in the invocation.

Additional fail-closed contract (independent review B1/B2 plus root-required
pagination and error sanitization):

* the recovery page must be provably the LAST page: a non-empty ``Link``
  response header (checked case-insensitively) fails closed BEFORE
  ``total_count`` is even considered;
* EVERY row of that page must be a real check-run object — a null, string,
  number or array row rejects the whole page instead of being silently
  skipped;
* the exact binding is found by CENSUS on ``external_id`` alone and must
  appear EXACTLY once before any other field is validated; sibling records
  with a different external_id are normal and do not block recovery;
* ``RUN_ID`` and ``RUN_ATTEMPT`` must be canonical positive integers
  (``/^[1-9][0-9]*$/``) before any create, and the step's action-level
  ``retries`` input is pinned to 0;
* thrown call details are never interpolated into logs or errors: failure
  reasons are fixed internal classification tokens only.

These bounds hold per invocation only — the tests deliberately do NOT assert
global exactly-once across invocations.
"""

import copy
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "fences.yml"

HEAD = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
RUN_ID = "991100"
ATTEMPT = "3"
OWNER = "octo"
REPO = "hut"
DETAILS_URL = f"https://github.com/{OWNER}/{REPO}/actions/runs/{RUN_ID}"
CONTEXT = {"serverUrl": "https://github.com", "apiUrl": "https://api.github.com", "repo": {"owner": OWNER, "repo": REPO}}
CONTEXT_NAMES = ["self-mod-fence", "capability-broker", "grader-manifest"]

NODE_RUNNER = r"""'use strict';
const fs = require('fs');
const vm = require('vm');

const APP_ID = 15368;
const caseSpec = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const script = fs.readFileSync(process.argv[3], 'utf8');

const sentCreates = [];
const sentLists = [];
const coreCalls = [];
const coreLog = [];
const badRetries = [];
let retained = null;   // the write GitHub kept (create resolved server-side)
let lastSent = null;   // params of the most recent create attempt, even if thrown

function snap(v) { return JSON.parse(JSON.stringify(v)); }

// What the Checks API returns for a check run created from these params.
function recordFrom(p) {
  return {
    id: 424242,
    node_id: 'CR_kwDOFence',
    name: p.name,
    head_sha: p.head_sha,
    status: p.status,
    conclusion: p.conclusion,
    details_url: p.details_url,
    external_id: p.external_id,
    html_url: p.details_url,
    url: 'https://api.github.com/repos/' + p.owner + '/' + p.repo + '/check-runs/424242',
    check_suite: { id: 31337 },
    app: { id: APP_ID, slug: 'github-actions', node_id: 'MDM6QXBwMTUzNjg=' },
    pull_requests: [],
    started_at: '2026-10-23T07:00:00Z',
    completed_at: '2026-10-23T07:00:05Z',
    output: { title: p.output.title, summary: p.output.summary, text: null },
  };
}

function setPath(obj, path, value) {
  const parts = path.split('.');
  let cur = obj;
  for (let i = 0; i < parts.length - 1; i += 1) {
    if (!cur[parts[i]] || typeof cur[parts[i]] !== 'object') cur[parts[i]] = {};
    cur = cur[parts[i]];
  }
  cur[parts[parts.length - 1]] = value;
}

// {"output.title": "x"} mutates a nested field; {"details_url": "__omit__"}
// models an API response that omitted the field entirely.
function applyMutations(record, mutations) {
  for (const path of Object.keys(mutations || {})) {
    if (mutations[path] === '__omit__') delete record[path];
    else setPath(record, path, mutations[path]);
  }
}

async function create(p) {
  sentCreates.push(snap(p));
  lastSent = p;
  if (!p.request || p.request.retries !== 0) badRetries.push('create#' + sentCreates.length);
  retained = caseSpec.liveRecord && sentCreates.length === 1 ? snap(caseSpec.liveRecord) : null;
  if (caseSpec.create === 'throw') throw new Error(caseSpec.throwMessage || 'Original 500 from checks.create');
  if (!retained) retained = recordFrom(p);
  if (caseSpec.create === 'malformed') {
    const partial = snap(retained);
    delete partial.output;
    delete partial.details_url;
    return { data: partial };
  }
  return { data: snap(retained) };
}

// Attach the case's header map (if any) to the response exactly like the
// Checks API client does: headers live next to data on the response object.
function respond(payload) {
  if (caseSpec.headers) return { data: payload, headers: caseSpec.headers };
  return { data: payload };
}

async function listForRef(p) {
  sentLists.push(snap(p));
  if (!p.request || p.request.retries !== 0) badRetries.push('list#' + sentLists.length);
  const mode = caseSpec.list || 'match';
  if (mode === 'throw') throw new Error(caseSpec.listThrowMessage || 'Original 500 from checks.listForRef');
  if (mode === 'none') return respond({ total_count: 0, check_runs: [] });
  const source = retained || (lastSent ? recordFrom(lastSent) : null);
  if (!source) return respond({ total_count: 0, check_runs: [] });
  let records;
  if (mode === 'dup') {
    records = [snap(source), snap(source)];
  } else {
    const single = snap(source);
    applyMutations(single, caseSpec.mutate);
    records = [single];
  }
  for (const extra of caseSpec.extraRecords || []) {
    const sibling = snap(source);
    applyMutations(sibling, extra.mutate || {});
    records.push(sibling);
  }
  for (const raw of caseSpec.rawRows || []) {
    records.push(raw);
  }
  const shape = caseSpec.listShape || 'wellformed';
  if (shape === 'no-total') return respond({ check_runs: records });
  if (shape === 'count-mismatch') return respond({ total_count: records.length + 1, check_runs: records });
  if (shape === 'not-array') return respond({ total_count: 1, check_runs: { 0: records[0] } });
  if (shape === 'over-100') {
    const many = [];
    for (let i = 0; i < 101; i += 1) many.push(snap(records[0]));
    return respond({ total_count: many.length, check_runs: many });
  }
  return respond({ total_count: records.length, check_runs: records });
}

const core = {};
for (const name of ['error', 'warning', 'notice', 'info', 'debug', 'setFailed',
                    'setOutput', 'exportVariable', 'saveState', 'startGroup', 'endGroup']) {
  core[name] = function () {
    coreCalls.push(name);
    try {
      coreLog.push(name + ': ' + JSON.stringify([].slice.call(arguments)));
    } catch (err) {
      coreLog.push(name + ': <unserializable arguments>');
    }
  };
}
core.getState = function () { return ''; };
core.isDebug = function () { return false; };

function finish(result) {
  const report = Object.assign({}, result, {
    createCalls: sentCreates.length,
    listCalls: sentLists.length,
    badRetries: badRetries,
    coreCalls: coreCalls,
    coreLog: coreLog,
    createParams: sentCreates,
    listParams: sentLists,
  });
  process.stdout.write(JSON.stringify(report) + '\n');
}

const context = Object.assign(
  { serverUrl: 'https://github.com', repo: { owner: 'octo', repo: 'hut' } },
  caseSpec.context || {}
);

const sandbox = {
  github: { rest: { checks: { create: create, listForRef: listForRef } } },
  core: core,
  context: context,
  require: function (name) {
    if (name === 'crypto' || name === 'node:crypto') return require('crypto');
    throw new Error('require("' + String(name) + '") is not permitted in the fence publish sandbox');
  },
  process: { env: Object.assign({}, caseSpec.env || {}) },
  console: { log: function () {}, error: function () {} },
};
vm.createContext(sandbox);

let pending;
try {
  pending = vm.runInContext('(async () => {\n' + script + '\n})()', sandbox, { timeout: 30000 });
} catch (err) {
  finish({ ok: false, message: String((err && err.message) || err) });
  process.exit(0);
}
pending.then(
  function () { finish({ ok: true, message: '' }); },
  function (err) { finish({ ok: false, message: String((err && err.message) || err) }); }
);
"""


def workflow_doc():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def publish_step():
    for step in workflow_doc()["jobs"]["fence-pack"]["steps"]:
        if step.get("id") == "publish":
            return step
    raise AssertionError("publish step (id: publish) not found in fences.yml")


def base_env(**overrides):
    env = {
        "HEAD_SHA": HEAD,
        "RUN_ID": RUN_ID,
        "RUN_ATTEMPT": ATTEMPT,
        "SELF_MOD_SELFTEST": "success",
        "SELF_MOD_LIVE": "success",
        "SELF_MOD_TESTS": "success",
        "AGENT_OS_RECORD_CONTRACT": "success",
        "CAPABILITY_SELFTEST": "success",
        "CAPABILITY_LIVE": "success",
        "GRADER_SELFTEST": "success",
        "GRADER_LIVE": "success",
    }
    env.update(overrides)
    return env


def base_case(**overrides):
    case = {"env": base_env(), "context": CONTEXT, "create": "ok", "list": "match"}
    case.update(overrides)
    return case


@pytest.fixture(scope="module")
def harness(tmp_path_factory):
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("node is required to execute the actual publish script")
    workdir = tmp_path_factory.mktemp("fence-pub-node")
    runner = workdir / "runner.js"
    runner.write_text(NODE_RUNNER, encoding="utf-8")
    script = workdir / "publish.js"
    text = publish_step()["with"]["script"]
    assert isinstance(text, str) and "checks.create" in text
    script.write_text(text, encoding="utf-8")
    return {"node": node, "runner": str(runner), "script": str(script)}


def run_case(harness, tmp_path, case):
    case_file = tmp_path / "case.json"
    case_file.write_text(json.dumps(case), encoding="utf-8")
    proc = subprocess.run(
        [harness["node"], harness["runner"], str(case_file), harness["script"]],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    report = json.loads(proc.stdout.strip().splitlines()[-1])
    assert report["badRetries"] == [], f"call without explicit retries:0: {report['badRetries']}"
    return report


def assert_bounded_call_shapes(report):
    """Every create is one per context with explicit retries:0; every read is
    the exact single bounded page."""
    for params in report["createParams"]:
        assert params["request"] == {"retries": 0}
        assert params["owner"] == OWNER
        assert params["repo"] == REPO
        assert params["head_sha"] == HEAD
        assert params["status"] == "completed"
        assert params["details_url"] == DETAILS_URL
    for params in report["listParams"]:
        assert params == {
            "owner": OWNER,
            "repo": REPO,
            "ref": HEAD,
            "check_name": params["check_name"],
            "filter": "all",
            "per_page": 100,
            "page": 1,
            "request": {"retries": 0},
        }


def test_workflow_contract_is_preserved():
    doc = workflow_doc()
    # permissions and triggers untouched
    assert doc["permissions"] == {"contents": "read", "checks": "write"}
    assert doc[True] == {
        "pull_request": {"branches": ["main"]},
        "push": {"branches": ["main"]},
    }
    assert set(doc["jobs"]) == {
        "fence-pack",
        "fork-self-mod-fence",
        "fork-capability-broker",
        "fork-grader-manifest",
    }
    # all original steps still present, in order
    ids = [step.get("id") for step in doc["jobs"]["fence-pack"]["steps"]]
    assert ids == [
        None,
        None,
        None,
        "self_mod_selftest",
        "self_mod_live",
        "self_mod_tests",
        "agent_os_record_contract",
        "capability_selftest",
        "capability_live",
        "grader_selftest",
        "grader_live",
        "chat_nav_selftest",
        "chat_nav_live",
        "publish",
        None,
    ]
    # the aggregation step still folds the publish outcome into the job result
    aggregation = doc["jobs"]["fence-pack"]["steps"][-1]
    assert aggregation["name"] == "fail pack when any fence failed"
    assert aggregation["env"]["PUBLISH"] == "${{ steps.publish.outcome }}"

    step = publish_step()
    assert step["if"] == "always()"
    assert step["uses"].startswith("actions/github-script@v7")
    assert step["env"]["HEAD_SHA"] == "${{ github.event.pull_request.head.sha || github.sha }}"
    assert step["env"]["RUN_ID"] == "${{ github.run_id }}"
    assert step["env"]["RUN_ATTEMPT"] == "${{ github.run_attempt }}"
    outcome_keys = {key for key in step["env"] if key.endswith(("SELFTEST", "LIVE", "TESTS", "CONTRACT"))}
    assert outcome_keys == {
        "SELF_MOD_SELFTEST",
        "SELF_MOD_LIVE",
        "SELF_MOD_TESTS",
        "AGENT_OS_RECORD_CONTRACT",
        "CAPABILITY_SELFTEST",
        "CAPABILITY_LIVE",
        "GRADER_SELFTEST",
        "GRADER_LIVE",
    }


def test_script_surface_has_no_retry_update_or_poll(harness):
    text = Path(harness["script"]).read_text(encoding="utf-8")
    assert "retries: 0" in text
    assert "checks.update" not in text
    assert "checks.patch" not in text
    assert "setTimeout" not in text
    assert "setInterval" not in text
    assert "for (" in text  # the fixed context loop still drives publication
    env_reads = set(re.findall(r"process\.env\.([A-Z_]+)", text))
    assert env_reads == {
        "HEAD_SHA",
        "RUN_ID",
        "RUN_ATTEMPT",
        "SELF_MOD_SELFTEST",
        "SELF_MOD_LIVE",
        "SELF_MOD_TESTS",
        "AGENT_OS_RECORD_CONTRACT",
        "CAPABILITY_SELFTEST",
        "CAPABILITY_LIVE",
        "GRADER_SELFTEST",
        "GRADER_LIVE",
    }


def test_all_success_direct_receipt_makes_no_read(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case())
    assert report["ok"] is True
    assert report["createCalls"] == 3
    assert report["listCalls"] == 0
    assert [p["name"] for p in report["createParams"]] == CONTEXT_NAMES
    assert_bounded_call_shapes(report)
    ids = {p["external_id"] for p in report["createParams"]}
    assert len(ids) == 3
    for params in report["createParams"]:
        assert re.fullmatch(r"[0-9a-f]{64}", params["external_id"])
        assert params["conclusion"] == "success"
        assert params["output"]["title"] == f"{params['name']}: passed"
    assert report["createParams"][0]["output"]["summary"] == "success, success, success, success"
    assert report["createParams"][1]["output"]["summary"] == "success, success"
    assert report["createParams"][2]["output"]["summary"] == "success, success"


def test_uppercase_head_sha_is_normalized_not_rejected(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case(env=base_env(HEAD_SHA=HEAD.upper())))
    assert report["ok"] is True
    assert all(p["head_sha"] == HEAD for p in report["createParams"])


def test_semantic_failure_remains_failure(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case(env=base_env(SELF_MOD_TESTS="failure")))
    assert report["ok"] is True
    assert report["createCalls"] == 3
    first = report["createParams"][0]
    assert first["conclusion"] == "failure"
    assert first["output"]["title"] == "self-mod-fence: failed"
    assert first["output"]["summary"] == "success, success, failure, success"
    for params in report["createParams"][1:]:
        assert params["conclusion"] == "success"


def test_skipped_still_maps_to_success(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case(env=base_env(CAPABILITY_LIVE="skipped")))
    assert report["ok"] is True
    assert all(p["conclusion"] == "success" for p in report["createParams"])
    assert report["createParams"][1]["output"]["summary"] == "success, skipped"


def test_thrown_create_with_retained_write_recovers_and_continues(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case(create="throw", list="match"))
    assert report["ok"] is True
    # every context: exactly one create, exactly one reconciliation read
    assert report["createCalls"] == 3
    assert report["listCalls"] == 3
    assert [p["name"] for p in report["createParams"]] == CONTEXT_NAMES
    assert [p["check_name"] for p in report["listParams"]] == CONTEXT_NAMES
    assert_bounded_call_shapes(report)


def test_malformed_success_receipt_recovers(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case(create="malformed", list="match"))
    assert report["ok"] is True
    assert report["createCalls"] == 3
    assert report["listCalls"] == 3
    assert_bounded_call_shapes(report)


def test_recovery_read_is_exact_bounded_single_page(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case(create="throw", list="match"))
    assert report["listParams"][0] == {
        "owner": OWNER,
        "repo": REPO,
        "ref": HEAD,
        "check_name": "self-mod-fence",
        "filter": "all",
        "per_page": 100,
        "page": 1,
        "request": {"retries": 0},
    }


def test_absent_binding_fails_closed_and_stops_later_creates(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case(create="throw", list="none"))
    assert report["ok"] is False
    assert "EFFECT_UNKNOWN" in report["message"]
    assert "error" in report["coreCalls"]
    # absence in the single bounded page is UNKNOWN, never proof of no-write:
    # no retry of the create, no second read, no later context
    assert report["createCalls"] == 1
    assert report["listCalls"] == 1


MISMATCH_CASES = {
    "app-id": {"app.id": 9999},
    "app-missing": {"app": "__omit__"},
    "name": {"name": "other-fence"},
    "head": {"head_sha": "b" * 40},
    "external-id": {"external_id": "f" * 64},
    # run/attempt are bound only through external_id: a record bound to a
    # different run or attempt shows up as a different external_id
    "run-attempt-binding": {"external_id": "0" * 63 + "1"},
    "external-id-missing": {"external_id": "__omit__"},
    "status": {"status": "in_progress"},
    "conclusion": {"conclusion": "neutral"},
    "output-title": {"output.title": "different title"},
    "output-summary": {"output.summary": "different summary"},
    "output-missing": {"output": "__omit__"},
    "details-url": {"details_url": "https://github.com/octo/hut/actions/runs/000001"},
    "details-url-missing": {"details_url": "__omit__"},
    "head-missing": {"head_sha": "__omit__"},
}


@pytest.mark.parametrize("label,mutate", sorted(MISMATCH_CASES.items()))
def test_mismatched_receipt_fails_closed(harness, tmp_path, label, mutate):
    report = run_case(harness, tmp_path, base_case(create="throw", list="mismatch", mutate=mutate))
    assert report["ok"] is False, f"{label} was accepted"
    assert "EFFECT_UNKNOWN" in report["message"]
    assert report["createCalls"] == 1  # no retry, no duplicate write
    assert report["listCalls"] == 1  # exactly one bounded reconciliation read


def test_duplicate_exact_binding_records_fail_closed(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case(create="throw", list="dup"))
    assert report["ok"] is False
    assert "EFFECT_UNKNOWN" in report["message"]
    assert report["createCalls"] == 1
    assert report["listCalls"] == 1


@pytest.mark.parametrize(
    "shape",
    ["no-total", "count-mismatch", "not-array", "over-100"],
)
def test_incomplete_or_malformed_list_page_fails_closed(harness, tmp_path, shape):
    report = run_case(harness, tmp_path, base_case(create="throw", list="match", listShape=shape))
    assert report["ok"] is False
    assert "EFFECT_UNKNOWN" in report["message"]
    assert report["createCalls"] == 1
    assert report["listCalls"] == 1


def test_recovery_read_failure_fails_closed(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case(create="throw", list="throw"))
    assert report["ok"] is False
    assert "EFFECT_UNKNOWN" in report["message"]
    assert report["createCalls"] == 1
    assert report["listCalls"] == 1


INVALID_INPUT_CASES = {
    "head-empty": {"env": base_env(HEAD_SHA="")},
    "head-short": {"env": base_env(HEAD_SHA="abc123")},
    "head-not-hex": {"env": base_env(HEAD_SHA="z" * 40)},
    "run-id-empty": {"env": base_env(RUN_ID="")},
    "attempt-empty": {"env": base_env(RUN_ATTEMPT="")},
    "attempt-nonnumeric": {"env": base_env(RUN_ATTEMPT="1 of 2")},
    "owner-missing": {"context": {"serverUrl": "https://github.com", "repo": {"owner": "", "repo": REPO}}},
    "server-url-missing": {"context": {"serverUrl": "", "repo": {"owner": OWNER, "repo": REPO}}},
}


@pytest.mark.parametrize("label,override", sorted(INVALID_INPUT_CASES.items()))
def test_invalid_input_fails_before_any_create(harness, tmp_path, label, override):
    report = run_case(harness, tmp_path, base_case(**override))
    assert report["ok"] is False
    assert report["message"].startswith("INVALID_INPUT"), report["message"]
    assert report["createCalls"] == 0
    assert report["listCalls"] == 0


def test_external_id_is_deterministic_and_binds_repo_head_run_attempt_check(harness, tmp_path):
    def first_external_id(**overrides):
        report = run_case(harness, tmp_path, base_case(**overrides))
        assert report["ok"] is True
        return report["createParams"][0]["external_id"]

    baseline = first_external_id()
    assert re.fullmatch(r"[0-9a-f]{64}", baseline)

    # deterministic: identical binding inputs, identical external_id
    assert first_external_id() == baseline
    # every binding dimension participates: change one, the id changes
    assert first_external_id(env=base_env(RUN_ATTEMPT=str(int(ATTEMPT) + 1))) != baseline
    assert first_external_id(env=base_env(RUN_ID=str(int(RUN_ID) + 1))) != baseline
    assert first_external_id(env=base_env(HEAD_SHA="b" * 40)) != baseline
    assert first_external_id(
        context={"serverUrl": "https://github.com", "repo": {"owner": "octo", "repo": "other-repo"}}
    ) != baseline
    # and the three contexts of one invocation never share an id
    report = run_case(harness, tmp_path, base_case())
    assert len({p["external_id"] for p in report["createParams"]}) == 3


def test_publish_step_pins_action_level_retries_to_zero():
    # actions/github-script's own retry knob must be pinned to zero so the
    # ONE-create/ONE-read contract is the only recovery path.
    assert int(publish_step()["with"]["retries"]) == 0


def test_always_on_self_mod_tests_step_includes_fence_publication_suite():
    doc = workflow_doc()
    steps = {step.get("id"): step for step in doc["jobs"]["fence-pack"]["steps"] if step.get("id")}
    run = steps["self_mod_tests"]["run"]
    assert "tests/test_fence_publication.py" in run
    assert "if" not in steps["self_mod_tests"]  # always-on: never path- or event-gated


BAD_RUN_IDS = ["0", "007", "12/34", "abc", "-1", "1.5"]


@pytest.mark.parametrize("bad", BAD_RUN_IDS)
def test_noncanonical_run_id_fails_before_any_create(harness, tmp_path, bad):
    report = run_case(harness, tmp_path, base_case(env=base_env(RUN_ID=bad)))
    assert report["ok"] is False
    assert report["message"].startswith("INVALID_INPUT"), report["message"]
    assert report["createCalls"] == 0
    assert report["listCalls"] == 0


BAD_ATTEMPTS = ["0", "007", "2/3", "-3", "1.5"]


@pytest.mark.parametrize("bad", BAD_ATTEMPTS)
def test_noncanonical_run_attempt_fails_before_any_create(harness, tmp_path, bad):
    report = run_case(harness, tmp_path, base_case(env=base_env(RUN_ATTEMPT=bad)))
    assert report["ok"] is False
    assert report["message"].startswith("INVALID_INPUT"), report["message"]
    assert report["createCalls"] == 0
    assert report["listCalls"] == 0


@pytest.mark.parametrize("raw", [None, "ghost-string", 42, [1, 2], False])
def test_non_object_rows_in_recovery_page_fail_closed(harness, tmp_path, raw):
    # After the page-shape checks, EVERY row must be a real check-run object:
    # null/string/number/array rows reject the page instead of being skipped.
    report = run_case(harness, tmp_path, base_case(create="throw", list="match", rawRows=[raw]))
    assert report["ok"] is False
    assert "EFFECT_UNKNOWN" in report["message"]
    assert report["createCalls"] == 1
    assert report["listCalls"] == 1


SAME_BINDING_CORRUPTIONS = {
    "app-id": {"app.id": 9999},
    "app-removed": {"app": "__omit__"},
    "name": {"name": "ghost-fence"},
    "head": {"head_sha": "b" * 40},
    "status": {"status": "in_progress"},
}


@pytest.mark.parametrize("label,mutate", sorted(SAME_BINDING_CORRUPTIONS.items()))
def test_same_external_id_corrupt_sibling_breaks_exactly_one_census(harness, tmp_path, label, mutate):
    # A sibling carrying the SAME external_id but a corrupted field means the
    # exact binding does not appear EXACTLY once on the page: fail closed.
    report = run_case(
        harness, tmp_path,
        base_case(create="throw", list="match", extraRecords=[{"mutate": mutate}]),
    )
    assert report["ok"] is False, f"{label} sibling with the same external_id was tolerated"
    assert "EFFECT_UNKNOWN" in report["message"]
    assert report["createCalls"] == 1
    assert report["listCalls"] == 1


def test_unrelated_external_id_sibling_does_not_block_recovery(harness, tmp_path):
    # Sibling records from older runs (different external_id) are normal; the
    # single exact-binding receipt still recovers the retained write.
    report = run_case(
        harness, tmp_path,
        base_case(
            create="throw",
            list="match",
            extraRecords=[{
                "mutate": {
                    "id": 7,
                    "external_id": "e" * 64,
                    "head_sha": "c" * 40,
                    "status": "completed",
                    "conclusion": "success",
                },
            }],
        ),
    )
    assert report["ok"] is True
    assert report["createCalls"] == 3
    assert report["listCalls"] == 3
    assert_bounded_call_shapes(report)


NEXT_LINK = '<https://api.github.com/repos/octo/hut/check-runs?page=2>; rel="next"'


@pytest.mark.parametrize("key", ["link", "Link", "LINK", "liNk"])
def test_non_empty_link_header_on_recovery_page_fails_closed(harness, tmp_path, key):
    # A Link header means the bounded page is not the last page: the read can
    # never resolve the unknown, even when total_count looks aligned.
    report = run_case(
        harness, tmp_path,
        base_case(create="throw", list="match", headers={key: NEXT_LINK}),
    )
    assert report["ok"] is False
    assert "EFFECT_UNKNOWN" in report["message"]
    assert report["createCalls"] == 1
    assert report["listCalls"] == 1


def test_empty_link_header_still_recovers(harness, tmp_path):
    report = run_case(harness, tmp_path, base_case(create="throw", list="match", headers={"link": ""}))
    assert report["ok"] is True
    assert report["createCalls"] == 3
    assert report["listCalls"] == 3


SENTINEL = "SECRET-BLOODHOUND-3311"


def assert_no_sentinel(report):
    blob = json.dumps(report)
    assert SENTINEL not in blob, "upstream error text leaked into the report"


def test_thrown_error_text_is_never_interpolated(harness, tmp_path):
    report = run_case(
        harness, tmp_path,
        base_case(
            create="throw",
            throwMessage=f"upstream 500 exploded: {SENTINEL} <html>gateway body</html>",
            list="throw",
            listThrowMessage=f"read refused: {SENTINEL} rejected",
        ),
    )
    assert report["ok"] is False
    assert "EFFECT_UNKNOWN" in report["message"]
    assert_no_sentinel(report)  # not in message, core.error args or any call params
    assert report["createCalls"] == 1
    assert report["listCalls"] == 1


def test_recovered_create_still_hides_thrown_error_text(harness, tmp_path):
    report = run_case(
        harness, tmp_path,
        base_case(create="throw", throwMessage=f"upstream 500 exploded: {SENTINEL}", list="match"),
    )
    assert report["ok"] is True
    assert report["createCalls"] == 3
    assert report["listCalls"] == 3
    assert_no_sentinel(report)


# Exact selected fields from the hosted GitHub Actions record for workflow run
# 39979973324 attempt 1, retained in pr9682-self-mod-382903e2-fields-20261023.json.
# This fixture intentionally does not derive receipt URLs from submitted params.
HOSTED_RECORD = {
    "app": {"id": 15368, "slug": "github-actions"},
    "conclusion": "success",
    "details_url": "https://github.com/mastermindx-market-intelligence/macro/runs/120505179588",
    "external_id": "fb07f1859ae24b48f2bb0017ab24de2c15d00e749c8cde4c53149af686ccd92c",
    "head_sha": "382903e20533855f89492844e6b0b66280a4560b",
    "html_url": "https://github.com/mastermindx-market-intelligence/macro/runs/120505179588",
    "id": 120505179588,
    "name": "self-mod-fence",
    "output": {"summary": "success, success, success, success", "title": "self-mod-fence: passed"},
    "status": "completed",
    "url": "https://api.github.com/repos/mastermindx-market-intelligence/macro/check-runs/120505179588",
}


def hosted_case(**overrides):
    return base_case(
        env=base_env(HEAD_SHA=HOSTED_RECORD["head_sha"], RUN_ID="39979973324", RUN_ATTEMPT="1"),
        context={"serverUrl": "https://github.com", "apiUrl": "https://api.github.com",
                 "repo": {"owner": "mastermindx-market-intelligence", "repo": "macro"}},
        liveRecord=copy.deepcopy(HOSTED_RECORD), **overrides,
    )


@pytest.mark.parametrize("create", ["ok", "throw", "malformed"])
def test_exact_hosted_normalized_receipt_is_confirmed(harness, tmp_path, create):
    report = run_case(harness, tmp_path, hosted_case(create=create))
    assert report["ok"], report
    assert len(report["createParams"]) == 3
    assert len(report["listParams"]) == (0 if create == "ok" else 3)
    assert report["createParams"][0]["external_id"] == HOSTED_RECORD["external_id"]
    assert report["createParams"][0]["details_url"] == (
        "https://github.com/mastermindx-market-intelligence/macro/actions/runs/39979973324"
    )


NORMALIZED_BAD_FIELDS = [
    ("id", 0), ("id", -1), ("id", 1.5), ("id", "120505179588"),
    ("id", 9007199254740992), ("id", None), ("id", 120505179589),
    ("details_url", "https://github.com/other/macro/runs/120505179588"),
    ("details_url", "https://github.com/mastermindx-market-intelligence/other/runs/120505179588"),
    ("details_url", "https://evil.example/mastermindx-market-intelligence/macro/runs/120505179588"),
    ("details_url", HOSTED_RECORD["details_url"] + "?q=1"),
    ("details_url", HOSTED_RECORD["details_url"] + "#fragment"),
    ("html_url", HOSTED_RECORD["html_url"] + "/"),
    ("html_url", None), ("url", None),
    ("url", "https://api.github.com/repos/other/macro/check-runs/120505179588"),
    ("url", "https://api.github.com/repos/mastermindx-market-intelligence/macro/check-runs/120505179589"),
    ("url", "https://evil.example/repos/mastermindx-market-intelligence/macro/check-runs/120505179588"),
    ("external_id", "wrong-run-binding"), ("app", {"id": 42}),
]


@pytest.mark.parametrize("field,value", NORMALIZED_BAD_FIELDS)
def test_normalized_receipt_requires_exact_self_links_and_provenance(harness, tmp_path, field, value):
    case = hosted_case()
    case["liveRecord"][field] = value
    report = run_case(harness, tmp_path, case)
    assert not report["ok"], report
    assert "EFFECT_UNKNOWN" in report["message"]
    assert len(report["createParams"]) == 1
    assert len(report["listParams"]) == 1


@pytest.mark.parametrize("field", ["id", "details_url", "html_url", "url"])
def test_normalized_receipt_missing_self_link_field_fails_closed(harness, tmp_path, field):
    case = hosted_case()
    del case["liveRecord"][field]
    report = run_case(harness, tmp_path, case)
    assert not report["ok"]
    assert "EFFECT_UNKNOWN" in report["message"]
    assert len(report["createParams"]) == len(report["listParams"]) == 1


@pytest.mark.parametrize("api_url", [None, "http://api.github.com", "https://api.example.com"])
def test_normalized_receipt_needs_trusted_api_origin(harness, tmp_path, api_url):
    case = hosted_case()
    if api_url is None:
        del case["context"]["apiUrl"]
    else:
        case["context"]["apiUrl"] = api_url
    report = run_case(harness, tmp_path, case)
    assert not report["ok"]
    assert "EFFECT_UNKNOWN" in report["message"]
    assert len(report["createParams"]) == len(report["listParams"]) == 1


@pytest.mark.parametrize("field,value", [
    ("serverUrl", "https://evil.example"),
    ("serverUrl", "http://github.com"),
    ("repo", {"owner": "other", "repo": "macro"}),
    ("repo", {"owner": "mastermindx-market-intelligence", "repo": "other"}),
])
def test_hosted_receipt_rejects_context_server_or_repo_mismatch(harness, tmp_path, field, value):
    case = hosted_case()
    case["context"][field] = value
    report = run_case(harness, tmp_path, case)
    assert not report["ok"]
    assert len(report["createParams"]) <= 1
    assert len(report["listParams"]) <= 1
