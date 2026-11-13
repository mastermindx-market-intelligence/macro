"""Resolver security boundary: real receipt ZIPs, stubbed GETs, no hosted effects."""
from dataclasses import asdict, replace
import hashlib
import io
import json
import zipfile

import pytest

from scripts import ci_proof_admission as admission
from scripts import resolve_ci_pr_admission as resolver


class Harness:
    def __init__(self, monkeypatch):
        self.now = 0
        self.sleeps = []
        self.calls = []
        self.readbacks = 0
        self.wait_reads = 0
        self.failure = None
        self.ancestry = "ahead"
        self.prepared = admission.Admission("a" * 12, 123, "1" * 40, "2" * 40, "3" * 40, "4" * 40)
        self.bound = replace(self.prepared, run_id=90)
        self.controller = {"id": 70, "run_attempt": 1, "repository": {"id": 17},
            "path": ".github/workflows/merge-on-green.yml", "head_branch": "main",
            "head_sha": "c" * 40, "event": "schedule"}
        self.run = {"id": 90, "run_attempt": 1, "repository": {"id": 17},
            "path": ".github/workflows/ci.yml", "head_branch": "main",
            "head_sha": "4" * 40, "event": "workflow_dispatch", "status": "in_progress"}
        self.pull = {"number": 123, "state": "open",
            "head": {"sha": "1" * 40, "repo": {"id": 17, "full_name": resolver.REPOSITORY}},
            # Main has moved. Only the immutable admitted merge is tested.
            "base": {"sha": "9" * 40, "ref": "main", "repo": {"id": 17, "full_name": resolver.REPOSITORY}}}
        self.commit = {"sha": "3" * 40, "parents": [{"sha": "2" * 40}, {"sha": "1" * 40}]}
        self.artifacts = {}
        self.archives = {}
        self.refs = {}
        self.install(80, self.prepared)
        self.install(81, self.bound)
        monkeypatch.setattr(resolver.mog, "_request", self.request)
        monkeypatch.setattr(resolver.mog, "_download_semantic_artifact", self.download)

    def install(self, artifact_id, record):
        body = json.dumps({"schema": "mastermind.ci-proof-admission.v1", "repository_id": 17,
            "controller_run_id": 70, "controller_run_attempt": 1, "admission": asdict(record)}, sort_keys=True).encode()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("ci-proof-admission.json", body)
        raw = buffer.getvalue()
        phase = "prepared" if record.run_id is None else "bound"
        self.artifacts[artifact_id] = {"id": artifact_id,
            "name": f"ci-proof-admission-70-1-{record.generation}-{phase}", "expired": False,
            "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "workflow_run": {"id": 70, "repository_id": 17, "head_sha": "c" * 40}}
        self.archives[artifact_id] = raw
        self.refs[artifact_id] = {"artifact_id": artifact_id, "controller_run_id": 70,
            "controller_attempt": 1, "controller_sha": "c" * 40,
            "payload_sha256": hashlib.sha256(body).hexdigest()}

    def request(self, method, url, token):
        assert method == "GET"
        assert token == "test-token"
        prefix = f"{resolver.mog.GITHUB_API}/repos/{resolver.REPOSITORY}"
        assert url.startswith(prefix + "/")
        path = url[len(prefix):]
        self.calls.append(path)
        if self.failure and self.failure in path:
            return 403, {"message": "do not disclose test-token"}
        if path == "/actions/runs/90":
            return 200, self.run
        if path == "/actions/runs/70/attempts/1":
            return 200, self.controller
        if path.startswith("/actions/artifacts/"):
            return 200, self.artifacts[int(path.rsplit("/", 1)[1])]
        if path.startswith("/compare/"):
            return 200, {"status": self.ancestry, "base_commit": {"sha": "c" * 40},
                         "merge_base_commit": {"sha": "c" * 40}}
        if path == "/issues/123/comments?per_page=100&page=1":
            self.readbacks += 1
            ids = [80] if self.readbacks <= self.wait_reads else [80, 81]
            return 200, [{"user":{"id":41898282,"login":"github-actions[bot]","type":"Bot"},"body": resolver.mog.ADMISSION_COMMENT_PREFIX + json.dumps(self.refs[i])} for i in ids]
        if path == "/pulls/123":
            return 200, self.pull
        if path == "/git/commits/" + "3" * 40:
            return 200, self.commit
        raise AssertionError("unexpected API path " + path)

    def download(self, url, token):
        assert url.startswith(f"{resolver.mog.GITHUB_API}/repos/{resolver.REPOSITORY}/actions/artifacts/")
        assert url.endswith("/zip") and token == "test-token"
        return self.archives[int(url.split("/")[-2])]

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds

    def args(self):
        return {"inputs": {"proof_role": "pr_head", "admission_generation": "a" * 12,
            "admission_artifact_id": "80", "admission_payload_sha256": self.refs[80]["payload_sha256"],
            "pr_number": "123", "subject_head_sha": "1" * 40, "tested_base_sha": "2" * 40,
            "tested_merge_sha": "3" * 40, "expected_workflow_definition_sha": "4" * 40},
            "repository": resolver.REPOSITORY, "repository_id": 17, "run_id": 90,
            "run_attempt": 1, "workflow_sha": "4" * 40, "event_sha": "4" * 40,
            "event_name": "workflow_dispatch", "ref": "refs/heads/main", "token": "test-token",
            "clock": lambda: self.now, "sleep": self.sleep}


@pytest.fixture
def h(monkeypatch):
    return Harness(monkeypatch)


def test_bound_original_receipt_yields_exact_source_even_after_main_moves(h):
    result = resolver.resolve(**h.args())
    assert result == {"tested_commit": "3" * 40, "subject_head": "1" * 40, "base": "2" * 40,
        "pr_number": "123", "head_repository_id": "17", "same_repository": "true",
        "admission_generation": "a" * 12, "semantic_role": "pr_head"}
    assert not h.sleeps


def test_prepared_alone_waits_only_within_one_original_attempt(h):
    h.wait_reads = 2
    assert resolver.resolve(**h.args())["semantic_role"] == "pr_head"
    assert h.readbacks == 3 and h.sleeps == [5, 5]
    assert sum(path == "/actions/runs/90" for path in h.calls) == 5


def test_prepared_without_bound_receipt_expires_without_outputs_or_effect(h):
    h.wait_reads = 100
    with pytest.raises(resolver.ResolutionError, match="incomplete"):
        resolver.resolve(**h.args())
    assert h.readbacks == resolver.MAX_READBACKS
    assert sum(h.sleeps) < resolver.DEADLINE_SECONDS


def test_attempt_change_while_waiting_never_adopts_the_rerun(h):
    h.wait_reads = 1
    args = h.args()
    def change_attempt(seconds):
        h.sleep(seconds)
        h.run["run_attempt"] = 2
    args["sleep"] = change_attempt
    with pytest.raises(resolver.ResolutionError, match="original active"):
        resolver.resolve(**args)
    assert h.readbacks == 1 and h.sleeps == [5]


def test_bound_reference_cannot_transfer_generation_to_another_controller_attempt(h):
    h.refs[81]["controller_attempt"] = 2
    with pytest.raises(resolver.ResolutionError, match="original controller attempt"):
        resolver.resolve(**h.args())
    assert not h.sleeps


def test_original_deadline_includes_http_time(h):
    def advancing_clock():
        h.now += 6
        return h.now
    args = h.args()
    args["clock"] = advancing_clock
    with pytest.raises(resolver.ResolutionError, match="deadline"):
        resolver.resolve(**args)
    assert not h.sleeps


@pytest.mark.parametrize("change", [{"run_id": 91}, {"run_attempt": 2}, {"settled": True},
                                    {"merge_sha": "5" * 40}, {"pr_number": 124}])
def test_bound_wrong_replayed_or_conflicting_identity_refused(h, change):
    h.install(81, replace(h.bound, **change))
    with pytest.raises(resolver.ResolutionError):
        resolver.resolve(**h.args())
    assert not h.sleeps


@pytest.mark.parametrize("field,value", [("status", "completed"), ("run_attempt", 2),
    ("run_attempt", True), ("event", "pull_request"), ("head_sha", "5" * 40),
    ("path", ".github/workflows/evil.yml"), ("head_branch", "candidate")])
def test_current_run_must_be_original_active_protected_dispatch(h, field, value):
    h.run[field] = value
    with pytest.raises(resolver.ResolutionError):
        resolver.resolve(**h.args())
    assert not h.sleeps


@pytest.mark.parametrize("parents", [["1" * 40, "2" * 40], ["2" * 40], ["2" * 40, "1" * 40, "5" * 40]])
def test_merge_parent_order_and_arity_are_exact(h, parents):
    h.commit["parents"] = [{"sha": sha} for sha in parents]
    with pytest.raises(resolver.ResolutionError):
        resolver.resolve(**h.args())


def test_superseded_head_does_not_fall_back_to_current_merge(h):
    h.pull["head"]["sha"] = "5" * 40
    with pytest.raises(resolver.ResolutionError, match="subject"):
        resolver.resolve(**h.args())


def test_fork_is_explicit_and_never_classified_as_same_repository(h):
    h.pull["head"]["repo"] = {"id": 18, "full_name": "contributor/macro"}
    result = resolver.resolve(**h.args())
    assert result["same_repository"] == "false" and result["head_repository_id"] == "18"


@pytest.mark.parametrize("repo", [None, {"id": True, "full_name": resolver.REPOSITORY},
    {"id": 17, "full_name": "attacker/macro"}, {"id": 18, "full_name": resolver.REPOSITORY}])
def test_missing_or_conflicting_subject_repository_fails(h, repo):
    h.pull["head"]["repo"] = repo
    with pytest.raises(resolver.ResolutionError):
        resolver.resolve(**h.args())


def test_controller_ancestry_is_verified(h):
    h.ancestry = "diverged"
    with pytest.raises(resolver.ResolutionError, match="ancestry"):
        resolver.resolve(**h.args())


def test_unreadable_record_is_unknown_not_a_wait_retry(h):
    h.failure = "/issues/123/comments"
    with pytest.raises(resolver.ResolutionError, match="UNKNOWN") as error:
        resolver.resolve(**h.args())
    assert "test-token" not in str(error.value) and not h.sleeps


def test_archive_corruption_cannot_be_replaced_by_comment_claim(h):
    h.archives[81] += b"changed"
    with pytest.raises(resolver.ResolutionError):
        resolver.resolve(**h.args())
    assert not h.sleeps


@pytest.mark.parametrize("field,value", [("pr_number", "123/../../secrets"),
    ("admission_artifact_id", "https://attacker"), ("subject_head_sha", "$(cat secret)"),
    ("proof_role", "main"), ("expected_workflow_definition_sha", "5" * 40)])
def test_untrusted_inputs_never_become_paths_or_shell(h, field, value):
    args = h.args()
    args["inputs"][field] = value
    with pytest.raises(resolver.ResolutionError):
        resolver.resolve(**args)
    assert not h.calls


def test_get_only_deadline_wrapper_restores_incumbent_interfaces(h):
    old_request = resolver.mog._request
    old_timeout = resolver.mog.REQUEST_TIMEOUT_SECONDS
    with pytest.raises(resolver.ResolutionError):
        with resolver._bounded_reads(resolver.REPOSITORY, "test-token", lambda: 0, 120):
            resolver.mog._request("POST", "https://api.github.com/repos/" + resolver.REPOSITORY + "/actions", "test-token")
    assert resolver.mog._request == old_request
    assert resolver.mog.REQUEST_TIMEOUT_SECONDS == old_timeout


def test_outsider_malformed_index_cannot_consume_admitted_original(h,monkeypatch):
    original=resolver.mog.fetch_issue_comments
    def comments(*a,**kw):
        rows=original(*a,**kw)
        return [{'id':9,'user':{'id':42,'login':'outsider','type':'User'},
                 'body':resolver.mog.ADMISSION_COMMENT_PREFIX+'{'}]+rows
    monkeypatch.setattr(resolver.mog,'fetch_issue_comments',comments)
    assert resolver.resolve(**h.args())['semantic_role']=='pr_head'
    assert not h.sleeps
