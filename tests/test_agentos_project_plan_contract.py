"""Focused tests for the pure Agent OS project_plan_adoption content contract.

Negative tests assert actual raised behavior (closed value-free codes), not
skips or shims.  The validator module itself is pure stdlib with no I/O;
these tests only import it and call its functions.
"""

import copy
import hashlib
import importlib.util
import os
import types

import pytest

_MODULE_CANDIDATES = (
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "scripts",
        "agentos_project_plan_contract.py",
    ),
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "agentos_project_plan_contract.py",
    ),
)


def _load_contract():
    for candidate in _MODULE_CANDIDATES:
        if os.path.isfile(candidate):
            spec = importlib.util.spec_from_file_location(
                "agentos_project_plan_contract", candidate
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
    raise ImportError("agentos_project_plan_contract module not found")


contract = _load_contract()

MACRO = contract.MACRO_REPOSITORY
MASTERMIND = contract.MASTERMIND_REPOSITORY
WORK_REF = "WS:PLAN-ALPHA"
WS_RECORD_PATH = "agentos/workstreams/WS-PLAN-ALPHA.md"

COMMIT_A = "a" * 40
COMMIT_B = "b" * 40
COMMIT_C = "c" * 40

PLAN_LF = b"# Project plan alpha\n\nAdopted body.\n"
PLAN_CRLF = PLAN_LF.replace(b"\n", b"\r\n")
PLAN_BOM = b"\xef\xbb\xbf" + PLAN_LF
PLAN_UNICODE = "# Project plan alpha\n\nCafé ☕ body.\n".encode("utf-8")
PLAN_LATIN1 = "# Project plan alpha\n\nCafé body.\n".encode("latin-1")
BIG_CANDIDATE = b"x" * contract.MAX_CANDIDATE_BYTES
HUGE_SOURCE = b"a" * contract.MAX_SOURCE_BYTES

WS_BYTES_A = b"plan-alpha workstream record a\n"
WS_BYTES_B = b"plan-alpha workstream record b\n"
WS_BYTES_C = b"plan-alpha workstream record c\n"

REF_A = {
    "repository": MACRO,
    "path": WS_RECORD_PATH,
    "commit": COMMIT_A,
    "content_sha256": hashlib.sha256(WS_BYTES_A).hexdigest(),
}
REF_B = {
    "repository": MACRO,
    "path": WS_RECORD_PATH,
    "commit": COMMIT_B,
    "content_sha256": hashlib.sha256(WS_BYTES_B).hexdigest(),
}
REF_C = {
    "repository": MACRO,
    "path": WS_RECORD_PATH,
    "commit": COMMIT_C,
    "content_sha256": hashlib.sha256(WS_BYTES_C).hexdigest(),
}
EDITORIAL_REF = {
    "repository": MASTERMIND,
    "path": "docs/plans/alpha-plan.md",
    "commit": COMMIT_A,
    "content_sha256": hashlib.sha256(PLAN_LF).hexdigest(),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ref(
    path="docs/plans/alpha.md",
    repository=MACRO,
    commit=COMMIT_A,
    content=PLAN_LF,
    content_sha256=None,
):
    return {
        "repository": repository,
        "path": path,
        "commit": commit,
        "content_sha256": sha(content) if content_sha256 is None else content_sha256,
    }


def adoption(**overrides):
    value = {
        "schema": contract.ADOPTION_SCHEMA,
        "work_ref": WORK_REF,
        "adopted_source": dict(REF_A),
        "predecessor": None,
        "proposal_source": None,
        "display_revision": "r19",
    }
    value.update(overrides)
    return value


def proposal(**overrides):
    value = {
        "schema": contract.PROPOSAL_SCHEMA,
        "proposal_id": "PLAN-ALPHA-R20",
        "work_ref": WORK_REF,
        "base_adoption": None,
        "base_source": dict(REF_A),
        "candidate_sha256": sha(PLAN_LF),
        "rationale": "Refresh the project plan for the next wave.",
        "evidence": [],
    }
    value.update(overrides)
    return value


def dec(
    key,
    meta=None,
    supersedes=None,
    superseded_by=None,
    affects=(WORK_REF,),
    decided_at="2020-01-01T00:00:00Z",
    with_meta=True,
):
    record = {
        "key": key,
        "question": "Adopt the project plan for " + key + "?",
        "answer": "Adopt.",
        "rationale": "Wave alignment.",
        "alternatives": [],
        "evidence": [],
        "affects": list(affects),
        "confidence": "high",
        "reversibility": "low",
        "decided_by": "owner",
        "decided_at": decided_at,
    }
    if supersedes is not None:
        record["supersedes"] = list(supersedes)
    if superseded_by is not None:
        record["superseded_by"] = superseded_by
    if with_meta:
        record["project_plan_adoption"] = meta if meta is not None else adoption()
    return record


def genesis(key="GEN", **overrides):
    return dec(
        key,
        meta=adoption(adopted_source=dict(REF_A)),
        supersedes=[],
        **overrides,
    )


def chain_records():
    return [
        dec(
            "GEN",
            meta=adoption(adopted_source=dict(REF_A)),
            supersedes=[],
            superseded_by="DEC:R2",
            decided_at="2999-12-31T23:59:59Z",
        ),
        dec(
            "R2",
            meta=adoption(adopted_source=dict(REF_B), predecessor="DEC:GEN"),
            supersedes=["DEC:GEN"],
            superseded_by="DEC:R3",
            decided_at="2000-01-01T00:00:00Z",
        ),
        dec(
            "R3",
            meta=adoption(adopted_source=dict(REF_C), predecessor="DEC:R2"),
            supersedes=["DEC:R2"],
            decided_at="1999-01-01T00:00:00Z",
        ),
    ]


def cycle_pair():
    return [
        dec(
            "CYCLE-X",
            meta=adoption(adopted_source=dict(REF_B), predecessor="DEC:CYCLE-Y"),
            supersedes=["DEC:CYCLE-Y"],
            superseded_by="DEC:CYCLE-Y",
        ),
        dec(
            "CYCLE-Y",
            meta=adoption(adopted_source=dict(REF_C), predecessor="DEC:CYCLE-X"),
            supersedes=["DEC:CYCLE-X"],
            superseded_by="DEC:CYCLE-X",
        ),
    ]


def expect(code, func, *args, **kwargs):
    with pytest.raises(contract.PlanContentError) as excinfo:
        func(*args, **kwargs)
    assert excinfo.value.code == code
    assert str(excinfo.value) == code
    assert excinfo.value.code in contract.CONTENT_ERROR_CODES
    return excinfo.value


# ---------------------------------------------------------------------------
# module purity


def test_module_is_pure_stdlib_without_io_surfaces():
    imported = {
        name
        for name, value in vars(contract).items()
        if isinstance(value, types.ModuleType) and not name.startswith("__")
    }
    assert imported == {"hashlib"}
    for forbidden in (
        "os",
        "io",
        "json",
        "yaml",
        "re",
        "subprocess",
        "socket",
        "pathlib",
        "datetime",
        "time",
        "random",
        "open",
        "Path",
    ):
        assert forbidden not in vars(contract)
    assert not hasattr(contract, "dataclasses")


def test_error_type_is_valueerror_with_closed_codes():
    assert issubclass(contract.PlanContentError, ValueError)
    for code in contract.CONTENT_ERROR_CODES:
        error = contract.PlanContentError(code)
        assert error.code == code
        assert str(error) == code
    with pytest.raises(ValueError):
        contract.PlanContentError("NOT_A_CLOSED_CODE")


def test_closed_code_set_matches_contract():
    assert contract.CONTENT_ERROR_CODES == frozenset(
        {
            "INVALID_SOURCE_REF",
            "SOURCE_BYTES_MISMATCH",
            "INVALID_ADOPTION",
            "INVALID_PROPOSAL",
            "WORK_REF_MISMATCH",
            "LINEAGE_CONFLICT",
            "LINEAGE_INCOMPLETE",
            "STALE_PREDECESSOR",
            "CONTENT_OVER_BUDGET",
        }
    )


# ---------------------------------------------------------------------------
# source references


class TestValidateSourceRef:
    def test_valid_ref_round_trip_detached(self):
        value = ref()
        result = contract.validate_source_ref(value)
        assert result == value
        assert set(result) == {"repository", "path", "commit", "content_sha256"}
        assert result is not value
        result["path"] = "tampered.md"
        assert value["path"] == "docs/plans/alpha.md"

    def test_accepts_both_repositories(self):
        assert contract.validate_source_ref(ref(repository=MACRO))["repository"] == MACRO
        assert (
            contract.validate_source_ref(ref(repository=MASTERMIND))["repository"]
            == MASTERMIND
        )

    @pytest.mark.parametrize("value", [None, True, False, 5, "ref", b"{}", [], (), {}])
    def test_rejects_unsafe_types(self, value):
        expect("INVALID_SOURCE_REF", contract.validate_source_ref, value)

    def test_rejects_extra_and_missing_keys(self):
        extra = ref()
        extra["status"] = "accepted"
        expect("INVALID_SOURCE_REF", contract.validate_source_ref, extra)
        short = {"repository": MACRO, "path": "docs/x.md", "commit": COMMIT_A}
        expect("INVALID_SOURCE_REF", contract.validate_source_ref, short)

    @pytest.mark.parametrize(
        "repository", ["macro", "mastermindx-market-intelligence/other", True, None, 7]
    )
    def test_rejects_wrong_repository(self, repository):
        expect(
            "INVALID_SOURCE_REF",
            contract.validate_source_ref,
            ref(repository=repository),
        )

    @pytest.mark.parametrize(
        "path",
        [
            "",
            "/docs/plans/x.md",
            "docs\\plans\\x.md",
            "docs/plans/x.md\n",
            "docs/plans/x.md\r",
            "docs/plans/x.md\x00",
            "docs/plans/x.txt",
            "docs//x.md",
            "docs/./x.md",
            "../x.md",
            "docs/../x.md",
            "./x.md",
            "docs/plans/x.md/",
        ],
    )
    def test_rejects_unsafe_paths(self, path):
        expect(
            "INVALID_SOURCE_REF", contract.validate_source_ref, ref(path=path)
        )

    def test_path_length_bound(self):
        ok = "docs/" + "a" * 504 + ".md"
        assert len(ok) == 512
        contract.validate_source_ref(ref(path=ok))
        long_path = ok + "a"
        expect(
            "INVALID_SOURCE_REF", contract.validate_source_ref, ref(path=long_path)
        )

    @pytest.mark.parametrize(
        "commit",
        ["", "a" * 39, "a" * 41, "A" * 40, "g" * 40, True, None, 40, "a" * 40 + "\n"],
    )
    def test_rejects_bad_commit(self, commit):
        expect(
            "INVALID_SOURCE_REF", contract.validate_source_ref, ref(commit=commit)
        )

    @pytest.mark.parametrize(
        "digest",
        [
            "",
            "a" * 63,
            "a" * 65,
            "A" * 64,
            "g" * 64,
            True,
            None,
            64,
            "a" * 64 + "\n",
            "\n" + "a" * 64,
        ],
    )
    def test_rejects_bad_digest(self, digest):
        value = {
            "repository": MACRO,
            "path": "docs/plans/alpha.md",
            "commit": COMMIT_A,
            "content_sha256": digest,
        }
        expect("INVALID_SOURCE_REF", contract.validate_source_ref, value)

    def test_ref_is_fact_not_authority(self):
        result = contract.validate_source_ref(ref())
        assert set(result) == {"repository", "path", "commit", "content_sha256"}
        assert "adoption" not in result
        assert "display_revision" not in result
        assert "status" not in result


# ---------------------------------------------------------------------------
# raw byte binding


class TestBindSourceRef:
    def test_exact_lf_bytes_bind(self):
        value = ref(content=PLAN_LF)
        result = contract.bind_source_ref(value, PLAN_LF)
        assert result == contract.validate_source_ref(value)

    def test_crlf_bytes_rejected_against_lf_digest(self):
        expect(
            "SOURCE_BYTES_MISMATCH",
            contract.bind_source_ref,
            ref(content=PLAN_LF),
            PLAN_CRLF,
        )

    def test_crlf_source_binds_when_digest_is_exact(self):
        value = ref(content=PLAN_CRLF)
        result = contract.bind_source_ref(value, PLAN_CRLF)
        assert result["content_sha256"] == sha(PLAN_CRLF)
        assert result["content_sha256"] != sha(PLAN_LF)

    def test_bom_bytes_rejected_against_plain_digest(self):
        expect(
            "SOURCE_BYTES_MISMATCH",
            contract.bind_source_ref,
            ref(content=PLAN_LF),
            PLAN_BOM,
        )

    def test_bom_source_binds_exactly_without_normalization(self):
        value = ref(content=PLAN_BOM)
        result = contract.bind_source_ref(value, PLAN_BOM)
        assert result["content_sha256"] == sha(PLAN_BOM)
        assert result["content_sha256"] != sha(PLAN_LF)

    def test_unicode_utf8_binds_and_latin1_rejected(self):
        value = ref(content=PLAN_UNICODE)
        assert contract.bind_source_ref(value, PLAN_UNICODE)["content_sha256"] == sha(
            PLAN_UNICODE
        )
        expect(
            "SOURCE_BYTES_MISMATCH",
            contract.bind_source_ref,
            ref(content=PLAN_LATIN1),
            PLAN_LATIN1,
        )

    def test_empty_bytes_rejected(self):
        expect(
            "SOURCE_BYTES_MISMATCH", contract.bind_source_ref, ref(content=PLAN_LF), b""
        )

    def test_source_byte_budget(self):
        value = {"repository": MACRO, "path": "docs/x.md", "commit": COMMIT_A,
                 "content_sha256": sha(HUGE_SOURCE)}
        assert contract.bind_source_ref(value, HUGE_SOURCE)["path"] == "docs/x.md"
        expect(
            "SOURCE_BYTES_MISMATCH",
            contract.bind_source_ref,
            value,
            HUGE_SOURCE + b"a",
        )

    @pytest.mark.parametrize(
        "raw", [None, "text", bytearray(PLAN_LF), memoryview(PLAN_LF), True, 7]
    )
    def test_rejects_non_bytes(self, raw):
        expect(
            "SOURCE_BYTES_MISMATCH",
            contract.bind_source_ref,
            ref(content=PLAN_LF),
            raw,
        )

    def test_invalid_ref_checked_before_bytes(self):
        expect(
            "INVALID_SOURCE_REF",
            contract.bind_source_ref,
            ref(path="/etc/passwd.md"),
            PLAN_LF,
        )

    def test_binding_is_not_availability_or_authority(self):
        result = contract.bind_source_ref(ref(content=PLAN_LF), PLAN_LF)
        assert set(result) == {"repository", "path", "commit", "content_sha256"}


# ---------------------------------------------------------------------------
# adoption metadata


class TestValidateAdoption:
    def test_valid_genesis_metadata_detached(self):
        value = adoption()
        result = contract.validate_adoption(value, work_ref=WORK_REF)
        assert set(result) == {
            "schema",
            "work_ref",
            "adopted_source",
            "predecessor",
            "proposal_source",
            "display_revision",
        }
        assert result["adopted_source"] == REF_A
        assert result["adopted_source"] is not value["adopted_source"]
        assert result["display_revision"] == "r19"

    @pytest.mark.parametrize(
        "schema",
        [
            "agentos.execution_plan.v1",
            "agentos.project_plan_adoption.v2",
            "agentos.project_plan_proposal.v1",
            "",
            None,
            7,
            True,
        ],
    )
    def test_rejects_foreign_or_malformed_schema(self, schema):
        expect(
            "INVALID_ADOPTION",
            contract.validate_adoption,
            adoption(schema=schema),
            work_ref=WORK_REF,
        )

    @pytest.mark.parametrize(
        "extra",
        [
            {"accepted": True},
            {"status": "adopted"},
            {"granted": True},
            {"job_id": "J-1"},
            {"admission": "admitted"},
            {"current": True},
            {"latest": True},
        ],
    )
    def test_rejects_authority_and_status_extras(self, extra):
        value = adoption()
        value.update(extra)
        expect("INVALID_ADOPTION", contract.validate_adoption, value, work_ref=WORK_REF)

    def test_rejects_non_dict_and_wrong_keys(self):
        expect("INVALID_ADOPTION", contract.validate_adoption, None, work_ref=WORK_REF)
        expect("INVALID_ADOPTION", contract.validate_adoption, True, work_ref=WORK_REF)
        expect(
            "INVALID_ADOPTION",
            contract.validate_adoption,
            list(adoption().items()),
            work_ref=WORK_REF,
        )
        short = adoption()
        del short["display_revision"]
        expect(
            "INVALID_ADOPTION", contract.validate_adoption, short, work_ref=WORK_REF
        )

    @pytest.mark.parametrize(
        "target",
        [None, "", "junk", "PLAN-ALPHA", "ws:plan-alpha", "WS:", "WS:plan-alpha",
         "WS:PLAN-ALPHA-", "WS:PLAN--ALPHA", "WS:" + "A" * 65, "WS:A", "WS:PLAN ALPHA"],
    )
    def test_rejects_invalid_target_work_ref(self, target):
        expect(
            "WORK_REF_MISMATCH", contract.validate_adoption, adoption(), work_ref=target
        )

    def test_work_ref_bound_is_max_64(self):
        edge = "WS:" + "A" * 64
        assert len(edge[3:]) == 64
        canonical = "agentos/workstreams/WS-" + "A" * 64 + ".md"
        value = adoption(work_ref=edge, adopted_source=ref(path=canonical))
        contract.validate_adoption(value, work_ref=edge)

    @pytest.mark.parametrize(
        "bad_ref_value",
        ["WS:", "ws:plan-alpha", "WS:plan", "WS:PLAN-ALPHA-", "PLAN-ALPHA", None, 7],
    )
    def test_rejects_malformed_metadata_work_ref(self, bad_ref_value):
        expect(
            "INVALID_ADOPTION",
            contract.validate_adoption,
            adoption(work_ref=bad_ref_value),
            work_ref=WORK_REF,
        )

    def test_metadata_work_ref_mismatch_with_target(self):
        expect(
            "WORK_REF_MISMATCH",
            contract.validate_adoption,
            adoption(work_ref="WS:PLAN-BETA"),
            work_ref=WORK_REF,
        )

    @pytest.mark.parametrize(
        "path",
        [
            "agentos/workstreams/plan-beta.md",
            "agentos/workstreams/PLAN-ALPHA.md",
            "agentos/workstreams/Plan-Alpha.md",
            "agentos/workstreams/sub/plan-alpha.md",
        ],
    )
    def test_rejects_cross_workstream_source_substitution(self, path):
        value = adoption(adopted_source=ref(path=path, content=WS_BYTES_A))
        expect(
            "INVALID_ADOPTION", contract.validate_adoption, value, work_ref=WORK_REF
        )

    def test_exact_workstream_record_path_accepted(self):
        value = adoption(adopted_source=dict(REF_A))
        result = contract.validate_adoption(value, work_ref=WORK_REF)
        assert result["adopted_source"]["path"] == WS_RECORD_PATH

    def test_mastermind_editorial_source_is_parent_qualified_not_invented(self):
        value = adoption(adopted_source=dict(EDITORIAL_REF))
        result = contract.validate_adoption(value, work_ref=WORK_REF)
        assert result["adopted_source"]["repository"] == MASTERMIND

    def test_malformed_adopted_source(self):
        expect(
            "INVALID_SOURCE_REF",
            contract.validate_adoption,
            adoption(adopted_source=ref(path="/abs.md")),
            work_ref=WORK_REF,
        )

    @pytest.mark.parametrize(
        "predecessor",
        [None, "DEC:KEY-1", "DEC:GENESIS-2"],
    )
    def test_predecessor_accepts_null_or_dec_ref(self, predecessor):
        result = contract.validate_adoption(
            adoption(predecessor=predecessor), work_ref=WORK_REF
        )
        assert result["predecessor"] == predecessor

    @pytest.mark.parametrize(
        "predecessor",
        ["KEY-1", "DEC:", "DEC:A", "DEC:key-1", "DEC:KEY--1", "DEC:KEY-",
         "DEC:" + "K" * 129, "", True, 7, "GEN"],
    )
    def test_rejects_malformed_predecessor(self, predecessor):
        expect(
            "INVALID_ADOPTION",
            contract.validate_adoption,
            adoption(predecessor=predecessor),
            work_ref=WORK_REF,
        )

    def test_dec_key_bound_is_2_to_128(self):
        edge = "DEC:" + "K" * 128
        contract.validate_adoption(adoption(predecessor=edge), work_ref=WORK_REF)

    def test_proposal_source_optional_but_valid(self):
        proposal_ref = ref(path="docs/proposals/alpha.md")
        result = contract.validate_adoption(
            adoption(proposal_source=proposal_ref), work_ref=WORK_REF
        )
        assert result["proposal_source"] == proposal_ref
        expect(
            "INVALID_SOURCE_REF",
            contract.validate_adoption,
            adoption(proposal_source=ref(path="/abs.md")),
            work_ref=WORK_REF,
        )
        expect(
            "INVALID_ADOPTION",
            contract.validate_adoption,
            adoption(proposal_source=ref(path="agentos/workstreams/plan-beta.md")),
            work_ref=WORK_REF,
        )

    @pytest.mark.parametrize(
        "display", [None, "r19", "v19", "revision 19 (explicit)", "x" * 128]
    )
    def test_display_revision_explicit_only(self, display):
        result = contract.validate_adoption(
            adoption(display_revision=display), work_ref=WORK_REF
        )
        assert result["display_revision"] == display

    @pytest.mark.parametrize(
        "display", ["", "   ", "\t", "r19\n", "r1\r9", "r19\x00", "x" * 129, 19, True, []]
    )
    def test_rejects_malformed_display_revision(self, display):
        expect(
            "INVALID_ADOPTION",
            contract.validate_adoption,
            adoption(display_revision=display),
            work_ref=WORK_REF,
        )

    def test_display_revision_is_never_inferred(self):
        value = adoption()
        del value["display_revision"]
        expect("INVALID_ADOPTION", contract.validate_adoption, value, work_ref=WORK_REF)

    def test_output_detachment_both_directions(self):
        value = adoption()
        result = contract.validate_adoption(value, work_ref=WORK_REF)
        value["adopted_source"]["path"] = "agentos/workstreams/plan-beta.md"
        value["display_revision"] = "tampered"
        assert result["adopted_source"]["path"] == WS_RECORD_PATH
        assert result["display_revision"] == "r19"
        result["display_revision"] = "mutated"
        assert value["display_revision"] == "tampered"
        again = contract.validate_adoption(adoption(), work_ref=WORK_REF)
        assert again == contract.validate_adoption(adoption(), work_ref=WORK_REF)
        assert again is not result


# ---------------------------------------------------------------------------
# proposal headers


class TestValidateProposal:
    def test_valid_header_detached(self):
        value = proposal()
        result = contract.validate_proposal(
            value, work_ref=WORK_REF, candidate_bytes=PLAN_LF
        )
        assert set(result) == {
            "schema",
            "proposal_id",
            "work_ref",
            "base_adoption",
            "base_source",
            "candidate_sha256",
            "rationale",
            "evidence",
        }
        assert result["base_source"] is not value["base_source"]
        assert result["evidence"] == []
        result["rationale"] = "tampered"
        assert value["rationale"] == "Refresh the project plan for the next wave."

    def test_exact_bytes_are_the_contract_not_serializer_output(self):
        raw = b"# Plan\r\n\r\nbody\twith\ttabs.\n"
        value = proposal(candidate_sha256=sha(raw))
        result = contract.validate_proposal(
            value, work_ref=WORK_REF, candidate_bytes=raw
        )
        assert result["candidate_sha256"] == sha(raw)
        normalized = raw.replace(b"\r\n", b"\n")
        expect(
            "SOURCE_BYTES_MISMATCH",
            contract.validate_proposal,
            proposal(candidate_sha256=sha(normalized)),
            work_ref=WORK_REF,
            candidate_bytes=raw,
        )

    def test_candidate_byte_swap_rejected(self):
        expect(
            "SOURCE_BYTES_MISMATCH",
            contract.validate_proposal,
            proposal(candidate_sha256=sha(PLAN_LF)),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF.replace(b"alpha", b"ALPHA"),
        )

    def test_candidate_must_be_utf8_bytes(self):
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            proposal(candidate_sha256=sha(PLAN_LATIN1)),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LATIN1,
        )
        expect(
            "SOURCE_BYTES_MISMATCH",
            contract.validate_proposal,
            proposal(),
            work_ref=WORK_REF,
            candidate_bytes="text",
        )

    def test_candidate_budget(self):
        value = proposal(candidate_sha256=sha(BIG_CANDIDATE))
        contract.validate_proposal(value, work_ref=WORK_REF, candidate_bytes=BIG_CANDIDATE)
        expect(
            "CONTENT_OVER_BUDGET",
            contract.validate_proposal,
            proposal(candidate_sha256=sha(BIG_CANDIDATE + b"x")),
            work_ref=WORK_REF,
            candidate_bytes=BIG_CANDIDATE + b"x",
        )

    def test_candidate_must_be_nonempty(self):
        expect(
            "CONTENT_OVER_BUDGET",
            contract.validate_proposal,
            proposal(candidate_sha256=sha(b"")),
            work_ref=WORK_REF,
            candidate_bytes=b"",
        )

    def test_schema_mismatch_rejected(self):
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            proposal(schema=contract.ADOPTION_SCHEMA),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )

    @pytest.mark.parametrize(
        "extra",
        [{"granted": True}, {"status": "proposed"}, {"job_id": "J-9"}, {"lease": "L"}],
    )
    def test_authority_extras_rejected(self, extra):
        value = proposal()
        value.update(extra)
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            value,
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )

    @pytest.mark.parametrize(
        "pid", ["A1", "PLAN-ALPHA-R20", "X" * 128]
    )
    def test_proposal_id_accepts_upper_kebab(self, pid):
        result = contract.validate_proposal(
            proposal(proposal_id=pid), work_ref=WORK_REF, candidate_bytes=PLAN_LF
        )
        assert result["proposal_id"] == pid

    @pytest.mark.parametrize(
        "pid", ["", "A", "a1", "PLAN--X", "-LEAD", "TRAIL-", "X" * 129, None, 7]
    )
    def test_proposal_id_rejects_malformed(self, pid):
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            proposal(proposal_id=pid),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )

    def test_work_ref_mismatch(self):
        expect(
            "WORK_REF_MISMATCH",
            contract.validate_proposal,
            proposal(work_ref="WS:PLAN-BETA"),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )
        expect(
            "WORK_REF_MISMATCH",
            contract.validate_proposal,
            proposal(),
            work_ref="nonsense",
            candidate_bytes=PLAN_LF,
        )

    def test_base_adoption_null_with_exact_base_source_is_structural_only(self):
        value = proposal(base_adoption=None, base_source=dict(REF_A))
        result = contract.validate_proposal(
            value, work_ref=WORK_REF, candidate_bytes=PLAN_LF
        )
        assert result["base_adoption"] is None
        assert result["base_source"] == REF_A
        assert "accepted" not in result
        assert "status" not in result

    def test_base_adoption_form(self):
        contract.validate_proposal(
            proposal(base_adoption="DEC:GEN"), work_ref=WORK_REF, candidate_bytes=PLAN_LF
        )
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            proposal(base_adoption="GEN"),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )

    def test_base_source_required_and_rule_bound(self):
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            proposal(base_source=None),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )
        expect(
            "INVALID_SOURCE_REF",
            contract.validate_proposal,
            proposal(base_source=ref(path="/abs.md")),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            proposal(base_source=ref(path="agentos/workstreams/plan-beta.md")),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )

    @pytest.mark.parametrize(
        "rationale", ["", "   ", "x" * 4097, None, 7]
    )
    def test_rationale_bounds(self, rationale):
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            proposal(rationale=rationale),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )

    def test_rationale_upper_bound_ok(self):
        long_rationale = "Refresh because. " * 240
        assert len(long_rationale) <= 4096
        contract.validate_proposal(
            proposal(rationale=long_rationale), work_ref=WORK_REF, candidate_bytes=PLAN_LF
        )

    def test_evidence_bounds(self):
        many = [
            ref(path="docs/evidence/e%02d.md" % index) for index in range(32)
        ]
        result = contract.validate_proposal(
            proposal(evidence=many), work_ref=WORK_REF, candidate_bytes=PLAN_LF
        )
        assert result["evidence"] == many
        assert result["evidence"] is not many
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            proposal(evidence=many + [ref(path="docs/evidence/e32.md")]),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            proposal(evidence="docs/evidence.md"),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )
        expect(
            "INVALID_SOURCE_REF",
            contract.validate_proposal,
            proposal(evidence=[ref(path="/abs.md")]),
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )

    def test_candidate_digest_field_form(self):
        for bad in ["", "a" * 63, "A" * 64, "g" * 64, None, True, "a" * 64 + "\n"]:
            expect(
                "INVALID_PROPOSAL",
                contract.validate_proposal,
                proposal(candidate_sha256=bad),
                work_ref=WORK_REF,
                candidate_bytes=PLAN_LF,
            )

    def test_non_dict_header_rejected(self):
        expect(
            "INVALID_PROPOSAL",
            contract.validate_proposal,
            "header",
            work_ref=WORK_REF,
            candidate_bytes=PLAN_LF,
        )


# ---------------------------------------------------------------------------
# current-adoption selection


class TestSelectCurrentAdoption:
    def test_no_records_returns_none(self):
        assert contract.select_current_adoption([], work_ref=WORK_REF) is None

    def test_legacy_records_without_metadata_are_ignored_and_unaffected(self):
        legacy = dec("LEGACY-1", with_meta=False)
        snapshot = copy.deepcopy(legacy)
        assert (
            contract.select_current_adoption([legacy], work_ref=WORK_REF) is None
        )
        assert legacy == snapshot

    def test_unrelated_adoption_ignored_even_with_other_workstream_paths(self):
        beta = dec(
            "BETA-1",
            meta=adoption(
                work_ref="WS:PLAN-BETA",
                adopted_source=ref(
                    path="agentos/workstreams/plan-beta.md", content=b"beta record\n"
                ),
            ),
            affects=("WS:PLAN-BETA",),
        )
        assert contract.select_current_adoption([beta], work_ref=WORK_REF) is None

    def test_single_genesis_selected(self):
        records = [genesis()]
        result = contract.select_current_adoption(records, work_ref=WORK_REF)
        assert result["decision_ref"] == "DEC:GEN"
        assert result["adoption"]["work_ref"] == WORK_REF
        assert result["adoption"]["predecessor"] is None

    def test_valid_three_decision_reciprocal_chain(self):
        result = contract.select_current_adoption(chain_records(), work_ref=WORK_REF)
        assert result["decision_ref"] == "DEC:R3"
        assert result["adoption"]["adopted_source"] == REF_C
        assert result["adoption"]["predecessor"] == "DEC:R2"

    def test_canonical_scoped_key_accepted(self):
        records = [genesis()]
        result = contract.select_current_adoption(records, work_ref=WORK_REF)
        assert result["decision_ref"] == "DEC:GEN"

    def test_no_timestamp_election(self):
        base = chain_records()
        first = contract.select_current_adoption(base, work_ref=WORK_REF)
        flipped = chain_records()
        flipped[0]["decided_at"] = "1999-01-01T00:00:00Z"
        flipped[2]["decided_at"] = "2999-12-31T23:59:59Z"
        second = contract.select_current_adoption(flipped, work_ref=WORK_REF)
        assert first["decision_ref"] == "DEC:R3"
        assert second["decision_ref"] == "DEC:R3"

    def test_missing_predecessor_is_incomplete(self):
        records = [
            genesis(),
            dec(
                "R2",
                meta=adoption(adopted_source=dict(REF_B), predecessor="DEC:GHOST"),
                supersedes=["DEC:GHOST"],
            ),
        ]
        expect(
            "LINEAGE_INCOMPLETE",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_missing_successor_is_incomplete_even_with_valid_head(self):
        records = [
            dec("GEN", meta=adoption(), supersedes=[], superseded_by="DEC:GHOST"),
        ]
        expect(
            "LINEAGE_INCOMPLETE",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_broken_reciprocal_link_rejected(self):
        records = chain_records()
        records[0]["superseded_by"] = "DEC:R3"
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_predecessor_must_occur_in_supersedes(self):
        records = [
            genesis(),
            dec(
                "R2",
                meta=adoption(adopted_source=dict(REF_B), predecessor="DEC:GEN"),
                supersedes=[],
            ),
        ]
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_extra_scoped_supersession_rejected(self):
        records = chain_records()
        records[2]["supersedes"] = ["DEC:R2", "DEC:GEN"]
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_duplicate_scoped_key_rejected(self):
        records = [genesis(), genesis()]
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )
        prefixed_and_bare = [genesis(), genesis()]
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            prefixed_and_bare,
            work_ref=WORK_REF,
        )

    def test_fork_branch_rejected(self):
        records = [
            genesis(superseded_by="DEC:R2"),
            dec(
                "R2",
                meta=adoption(adopted_source=dict(REF_B), predecessor="DEC:GEN"),
                supersedes=["DEC:GEN"],
            ),
            dec(
                "R3",
                meta=adoption(adopted_source=dict(REF_C), predecessor="DEC:GEN"),
                supersedes=["DEC:GEN"],
            ),
        ]
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_self_supersession_rejected(self):
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            [dec("GEN", meta=adoption(), supersedes=[], superseded_by="DEC:GEN")],
            work_ref=WORK_REF,
        )

    def test_cycle_rejected(self):
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            cycle_pair(),
            work_ref=WORK_REF,
        )

    def test_cycle_alongside_apparently_valid_head_rejected(self):
        records = chain_records() + cycle_pair()
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_competing_heads_rejected_without_timestamp_election(self):
        records = chain_records() + [
            dec("GEN2", meta=adoption(adopted_source=dict(REF_B)), supersedes=[],
                decided_at="2999-12-31T23:59:59Z"),
        ]
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_three_heads_rejected(self):
        records = [genesis(), genesis("GEN2"), genesis("GEN3")]
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_genesis_must_not_secretly_supersede_scoped_adoption(self):
        records = [
            genesis(),
            dec(
                "GEN2",
                meta=adoption(adopted_source=dict(REF_B)),
                supersedes=["DEC:GEN"],
            ),
        ]
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_genesis_superseding_unscoped_legacy_decision_is_allowed(self):
        records = [
            dec(
                "GEN",
                meta=adoption(adopted_source=dict(REF_A)),
                supersedes=["DEC:LEGACY-1"],
            ),
        ]
        result = contract.select_current_adoption(records, work_ref=WORK_REF)
        assert result["decision_ref"] == "DEC:GEN"

    def test_claimed_target_with_excluding_affects_refuses(self):
        records = [genesis(affects=("WS:OTHER",))]
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_unclaimed_target_with_including_affects_refuses(self):
        records = [
            dec(
                "BETA-1",
                meta=adoption(work_ref="WS:PLAN-BETA"),
                affects=(WORK_REF,),
            ),
        ]
        expect(
            "LINEAGE_CONFLICT",
            contract.select_current_adoption,
            records,
            work_ref=WORK_REF,
        )

    def test_scoped_key_form_enforced(self):
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            [dec("key-lower", meta=adoption())],
            work_ref=WORK_REF,
        )
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            [dec("A", meta=adoption())],
            work_ref=WORK_REF,
        )
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            [dec("K" * 129, meta=adoption())],
            work_ref=WORK_REF,
        )
        missing_key = genesis()
        del missing_key["key"]
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            [missing_key],
            work_ref=WORK_REF,
        )

    def test_relevant_record_metadata_fully_validated(self):
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            [dec("GEN", meta=adoption(schema="agentos.execution_plan.v1"))],
            work_ref=WORK_REF,
        )
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            [
                dec(
                    "GEN",
                    meta=adoption(
                        adopted_source=ref(
                            path="agentos/workstreams/plan-beta.md",
                            content=WS_BYTES_A,
                        )
                    ),
                )
            ],
            work_ref=WORK_REF,
        )

    def test_affects_must_be_a_string_list_on_adoption_records(self):
        missing = genesis()
        del missing["affects"]
        expect(
            "INVALID_ADOPTION", contract.select_current_adoption, [missing],
            work_ref=WORK_REF,
        )
        string_affects = genesis()
        string_affects["affects"] = "WS:PLAN-ALPHA"
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            [string_affects],
            work_ref=WORK_REF,
        )
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            [genesis(affects=(WORK_REF, 7))],
            work_ref=WORK_REF,
        )

    def test_malformed_metadata_or_record_container(self):
        expect(
            "WORK_REF_MISMATCH",
            contract.select_current_adoption,
            [genesis()],
            work_ref="junk",
        )
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            "records",
            work_ref=WORK_REF,
        )
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            ("records",),
            work_ref=WORK_REF,
        )
        bad_meta = genesis()
        bad_meta["project_plan_adoption"] = "metadata"
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            [bad_meta],
            work_ref=WORK_REF,
        )
        malformed_ref_meta = genesis()
        malformed_ref_meta["project_plan_adoption"] = {"work_ref": "WS:"}
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            [malformed_ref_meta],
            work_ref=WORK_REF,
        )
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            ["record"],
            work_ref=WORK_REF,
        )

    def test_record_count_bound(self):
        filler = [
            dec("LEGACY-%d" % index, with_meta=False) for index in range(127)
        ]
        assert len(filler + [genesis()]) == 128
        result = contract.select_current_adoption(
            filler + [genesis()], work_ref=WORK_REF
        )
        assert result["decision_ref"] == "DEC:GEN"
        expect(
            "INVALID_ADOPTION",
            contract.select_current_adoption,
            filler + [genesis(), genesis("GEN2")],
            work_ref=WORK_REF,
        )

    def test_records_never_mutated_and_outputs_detached(self):
        records = chain_records()
        snapshot = copy.deepcopy(records)
        first = contract.select_current_adoption(records, work_ref=WORK_REF)
        second = contract.select_current_adoption(records, work_ref=WORK_REF)
        assert records == snapshot
        assert first == second
        assert first is not second
        assert first["adoption"] is not second["adoption"]
        head = records[2]
        assert first["adoption"] is not head["project_plan_adoption"]
        first["adoption"]["display_revision"] = "mutated"
        assert head["project_plan_adoption"]["display_revision"] == "r19"
        assert records == snapshot


# ---------------------------------------------------------------------------
# stale-base guards


class TestRequireExpectedPredecessor:
    def test_initial_baseline(self):
        assert (
            contract.require_expected_predecessor(adoption(), None) is None
        )
        expect(
            "STALE_PREDECESSOR",
            contract.require_expected_predecessor,
            adoption(predecessor="DEC:GEN"),
            None,
        )

    def test_matching_predecessor_passes(self):
        current = contract.select_current_adoption(
            [genesis()], work_ref=WORK_REF
        )
        candidate = adoption(adopted_source=dict(REF_B), predecessor="DEC:GEN")
        assert contract.require_expected_predecessor(candidate, current) is None

    def test_stale_predecessor_rejected(self):
        current = contract.select_current_adoption(
            [genesis()], work_ref=WORK_REF
        )
        expect(
            "STALE_PREDECESSOR",
            contract.require_expected_predecessor,
            adoption(),
            current,
        )
        future = contract.select_current_adoption(
            chain_records(), work_ref=WORK_REF
        )
        expect(
            "STALE_PREDECESSOR",
            contract.require_expected_predecessor,
            adoption(adopted_source=dict(REF_B), predecessor="DEC:GEN"),
            future,
        )

    def test_candidate_metadata_validated_first(self):
        expect(
            "INVALID_ADOPTION",
            contract.require_expected_predecessor,
            adoption(schema="agentos.execution_plan.v1"),
            None,
        )
        expect(
            "INVALID_ADOPTION",
            contract.require_expected_predecessor,
            adoption(
                adopted_source=ref(path="agentos/workstreams/plan-beta.md"),
            ),
            None,
        )

    def test_current_shape_validated(self):
        expect(
            "INVALID_ADOPTION",
            contract.require_expected_predecessor,
            adoption(),
            {"decision_ref": "DEC:GEN"},
        )
        expect(
            "INVALID_ADOPTION",
            contract.require_expected_predecessor,
            adoption(),
            {"decision_ref": "GEN", "adoption": {}},
        )
        expect(
            "INVALID_ADOPTION",
            contract.require_expected_predecessor,
            adoption(),
            "current",
        )
        hollow = {
            "decision_ref": "DEC:GEN",
            "adoption": {
                "schema": contract.ADOPTION_SCHEMA,
                "work_ref": WORK_REF,
                "predecessor": None,
                "proposal_source": None,
                "display_revision": "r19",
            },
        }
        expect(
            "INVALID_ADOPTION",
            contract.require_expected_predecessor,
            adoption(predecessor="DEC:GEN"),
            hollow,
        )
        bad_source_current = {
            "decision_ref": "DEC:GEN",
            "adoption": adoption(adopted_source=ref(path="/abs.md")),
        }
        expect(
            "INVALID_SOURCE_REF",
            contract.require_expected_predecessor,
            adoption(predecessor="DEC:GEN"),
            bad_source_current,
        )

    def test_creates_no_write_and_returns_none(self):
        current = contract.select_current_adoption(
            [genesis()], work_ref=WORK_REF
        )
        candidate = adoption(adopted_source=dict(REF_B), predecessor="DEC:GEN")
        assert contract.require_expected_predecessor(candidate, current) is None


class TestRequireProposalBase:
    def test_no_current_requires_null_base(self):
        value = proposal(base_adoption=None, base_source=dict(REF_A))
        assert contract.require_proposal_base(value, None) is None
        expect(
            "STALE_PREDECESSOR",
            contract.require_proposal_base,
            proposal(base_adoption="DEC:GEN", base_source=dict(REF_A)),
            None,
        )

    def test_matching_base_passes(self):
        current = contract.select_current_adoption([genesis()], work_ref=WORK_REF)
        value = proposal(
            base_adoption="DEC:GEN",
            base_source=dict(REF_A),
            candidate_sha256=sha(PLAN_LF),
        )
        assert contract.require_proposal_base(value, current) is None

    def test_reference_equality_is_not_byte_evidence(self):
        current = contract.select_current_adoption([genesis()], work_ref=WORK_REF)
        value = proposal(base_adoption="DEC:GEN", base_source=dict(REF_A))
        assert contract.require_proposal_base(value, current) is None
        expect(
            "SOURCE_BYTES_MISMATCH",
            contract.bind_source_ref,
            dict(REF_A),
            b"different bytes on disk\n",
        )

    def test_stale_base_source_rejected(self):
        current = contract.select_current_adoption([genesis()], work_ref=WORK_REF)
        expect(
            "STALE_PREDECESSOR",
            contract.require_proposal_base,
            proposal(
                base_adoption="DEC:GEN",
                base_source=ref(path=WS_RECORD_PATH, commit=COMMIT_B, content=WS_BYTES_A),
            ),
            current,
        )
        expect(
            "STALE_PREDECESSOR",
            contract.require_proposal_base,
            proposal(
                base_adoption="DEC:GEN",
                base_source={
                    "repository": MACRO,
                    "path": WS_RECORD_PATH,
                    "commit": COMMIT_A,
                    "content_sha256": sha(b"tampered record\n"),
                },
            ),
            current,
        )

    def test_stale_base_decision_rejected(self):
        current = contract.select_current_adoption([genesis()], work_ref=WORK_REF)
        expect(
            "STALE_PREDECESSOR",
            contract.require_proposal_base,
            proposal(base_adoption="DEC:R2", base_source=dict(REF_A)),
            current,
        )

    def test_editorial_mastermind_baseline_allowed(self):
        current = {
            "decision_ref": "DEC:GEN",
            "adoption": contract.validate_adoption(
                adoption(adopted_source=dict(EDITORIAL_REF)), work_ref=WORK_REF
            ),
        }
        value = proposal(
            base_adoption="DEC:GEN",
            base_source=dict(EDITORIAL_REF),
            candidate_sha256=sha(PLAN_LF),
        )
        assert contract.require_proposal_base(value, current) is None
        drifted = dict(EDITORIAL_REF)
        drifted["commit"] = COMMIT_B
        expect(
            "STALE_PREDECESSOR",
            contract.require_proposal_base,
            proposal(base_adoption="DEC:GEN", base_source=drifted),
            current,
        )

    def test_header_validated_first(self):
        expect(
            "INVALID_PROPOSAL",
            contract.require_proposal_base,
            proposal(schema=contract.ADOPTION_SCHEMA),
            None,
        )
        expect(
            "INVALID_PROPOSAL",
            contract.require_proposal_base,
            proposal(base_source=ref(path="agentos/workstreams/plan-beta.md")),
            None,
        )
        expect(
            "INVALID_ADOPTION",
            contract.require_proposal_base,
            proposal(),
            {"decision_ref": "DEC:GEN"},
        )
        hollow = {
            "decision_ref": "DEC:GEN",
            "adoption": {
                "schema": contract.ADOPTION_SCHEMA,
                "work_ref": WORK_REF,
                "predecessor": None,
                "proposal_source": None,
                "display_revision": "r19",
            },
        }
        expect(
            "INVALID_ADOPTION",
            contract.require_proposal_base,
            proposal(base_adoption="DEC:GEN"),
            hollow,
        )


# ---------------------------------------------------------------------------
# value-free error surface


class TestValueFreeErrors:
    @pytest.mark.parametrize(
        "call",
        [
            lambda: contract.validate_source_ref(
                ref(path="/SECRET-MARKER-7f3a.md")
            ),
            lambda: contract.validate_source_ref(ref(commit="SECRET-MARKER-7f3a")),
            lambda: contract.bind_source_ref(ref(), b"SECRET-MARKER-7f3a\n"),
            lambda: contract.validate_adoption(
                adoption(display_revision="SECRET-MARKER-7f3a\n"), work_ref=WORK_REF
            ),
            lambda: contract.validate_adoption(
                adoption(work_ref="WS:SECRET-MARKER"), work_ref=WORK_REF
            ),
            lambda: contract.validate_proposal(
                proposal(rationale="SECRET-MARKER-7f3a" + "x" * 4097),
                work_ref=WORK_REF,
                candidate_bytes=PLAN_LF,
            ),
            lambda: contract.validate_proposal(
                proposal(),
                work_ref=WORK_REF,
                candidate_bytes=b"SECRET-MARKER-7f3a\n",
            ),
            lambda: contract.select_current_adoption(
                [genesis(affects=("WS:SECRET-MARKER",))], work_ref=WORK_REF
            ),
            lambda: contract.select_current_adoption(
                [genesis(), genesis()], work_ref=WORK_REF
            ),
            lambda: contract.require_expected_predecessor(
                adoption(predecessor="DEC:GEN"), None
            ),
            lambda: contract.require_proposal_base(
                proposal(base_adoption="DEC:GEN"), None
            ),
        ],
    )
    def test_messages_stay_value_free(self, call):
        with pytest.raises(contract.PlanContentError) as excinfo:
            call()
        message = str(excinfo.value)
        assert message == excinfo.value.code
        assert "SECRET-MARKER-7f3a" not in message
        assert "SECRET" not in message
        assert message in contract.CONTENT_ERROR_CODES

    def test_error_never_echoes_question_or_body(self):
        records = [genesis(), genesis("GEN2")]
        with pytest.raises(contract.PlanContentError) as excinfo:
            contract.select_current_adoption(records, work_ref=WORK_REF)
        message = str(excinfo.value)
        for fragment in ("Adopt the project plan", "Adopt.", "GEN2", "r19"):
            assert fragment not in message
