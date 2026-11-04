"""Tests for scripts/project_knowledge_recipes.py.

These are pure fixture tests: every preimage is a synthetic record string and
nothing is published.  When the real Macro validator (``scripts/agentos.py``)
is present as a sibling of this file's parent ``scripts/`` directory, the
generated decision postimages are additionally exercised through the actual
``parse_record``/``check_decision`` path; otherwise those checks are reported
as skipped, and the parent owns the real-repo validator run.
"""

import hashlib
import importlib.util
import inspect
import os
import sys
import tempfile
import unittest
import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import project_knowledge_recipes as pkr  # noqa: E402

AGENTOS_PATH = os.path.join(SCRIPTS, "agentos.py")
HAS_AGENTOS = os.path.isfile(AGENTOS_PATH)


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def hex_(n, seed="a"):
    return (seed * n)[:n]


def canonical_sha256(value):
    return hashlib.sha256(pkr.canonical(value).encode("utf-8")).hexdigest()


WS_BODY = "\nKeep this body exactly as written.\nSecond body line.\n"

WS_TEXT = (
    "---\n"
    "schema: agentos.workstream.v1\n"
    "key: SPEC-EDITING\n"
    "title: Spec editing pipeline\n"
    "objective: Ship observable spec editing behaviour.\n"
    "status: active\n"
    "program: mmos-core\n"
    "repos:\n"
    "- macro\n"
    "- terminal\n"
    "owner: chairman\n"
    "class: build\n"
    "blast_radius: reversible\n"
    "ambiguity: specified\n"
    "waves:\n"
    "- label: wave-1\n"
    "next_action: Land the editor codec.\n"
    "decisions:\n"
    "- DEC:EARLIER-CALL\n"
    "artifacts:\n"
    "- research/notes.md\n"
    "---\n" + WS_BODY
)

WS_NO_DECISIONS = WS_TEXT.replace(
    "decisions:\n- DEC:EARLIER-CALL\n", "decisions: []\n"
)

ACTOR = "workspace:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
ACTOR_B = "workspace:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
DIGEST = hex_(64, "c")
COMMIT = hex_(40, "b")

FILE_ADD_SCHEMA = pkr.SCHEMA_FILE_ADD_REQUEST
PREF_SCHEMA = pkr.SCHEMA_PREFERENCE_SET_REQUEST
DEC_POINTER = "DEC:" + pkr.PREFERENCE_DECISION_KEY_PREFIX + "SPEC-EDITING"


def file_request(workstream_text, *, request_id=None, work_ref="WS:SPEC-EDITING",
                 display_name="notes.md", media_type="text/markdown",
                 content="# notes\n中文 body line.\n"):
    if request_id is None:
        request_id = "mmos-project-file-add-" + hex_(40, "a")
    return {
        "schema": FILE_ADD_SCHEMA,
        "request_id": request_id,
        "work_ref": work_ref,
        "source_commit": COMMIT,
        "base_revision": sha256_text(workstream_text),
        "file": {
            "display_name": display_name,
            "media_type": media_type,
            "content_utf8": content,
        },
    }


def pref_request(workstream_text, *, request_id=None, work_ref="WS:SPEC-EDITING",
                 expected=None, value="以后请用中文写周报。"):
    if request_id is None:
        request_id = "mmos-project-preference-set-" + hex_(40, "d")
    return {
        "schema": PREF_SCHEMA,
        "request_id": request_id,
        "work_ref": work_ref,
        "source_commit": COMMIT,
        "base_revision": sha256_text(workstream_text),
        "expected_preference_revision": expected,
        "value": value,
    }


def build_file_add(request, *, actor=ACTOR, workstream_text=WS_TEXT,
                   existing_file_text=None):
    return pkr.build_project_file_add(
        request,
        actor_ref=actor,
        permission_binding_digest=DIGEST,
        captured_commit=COMMIT,
        workstream_text=workstream_text,
        existing_file_text=existing_file_text,
    )


def build_pref(request, *, actor=ACTOR, workstream_text=WS_NO_DECISIONS,
               decision_text=None, decision_date="2026-11-04"):
    return pkr.build_project_preference_set(
        request,
        actor_ref=actor,
        permission_binding_digest=DIGEST,
        captured_commit=COMMIT,
        workstream_text=workstream_text,
        decision_text=decision_text,
        decision_date=decision_date,
    )


def assert_raises(testcase, code, fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except pkr.KnowledgeRecipeError as exc:
        testcase.assertEqual(exc.code, code, "wrong code: %r" % (exc.code,))
        return exc
    testcase.fail("expected KnowledgeRecipeError(%s)" % (code,))


class TestConstants(unittest.TestCase):

    def test_bounded_limits_are_fixed(self):
        self.assertEqual(pkr.MAX_FILE_BYTES, 32768)
        self.assertEqual(pkr.MAX_PREFERENCE_BYTES, 2000)
        self.assertEqual(pkr.MAX_PROJECT_FILES, 32)

    def test_module_has_no_effect_surface(self):
        source = inspect.getsource(pkr)
        for forbidden in ("import subprocess", "import socket", "import urllib",
                          "import requests", "import os", "from pathlib",
                          "subprocess.", "socket.", "urllib.request",
                          "os.system", "os.open", "Path(", "open(",
                          "__import__"):
            self.assertNotIn(forbidden, source)
        imports = sorted(
            name for name in ("copy", "datetime", "hashlib", "json", "re",
                              "yaml")
            if "import %s" % name in source or "from typing" in source)
        self.assertTrue({"copy", "hashlib", "json", "re", "yaml"}
                        <= set(imports))


class TestCanonical(unittest.TestCase):

    def test_canonical_form(self):
        self.assertEqual(
            pkr.canonical({"b": 1, "a": "中文"}),
            '{"a":"中文","b":1}',
        )

    def test_canonical_is_deterministic_and_compact(self):
        a = pkr.canonical({"k": ["x", {"z": 1, "y": 2}], "n": None})
        b = pkr.canonical({"n": None, "k": ["x", {"z": 1, "y": 2}]})
        self.assertEqual(a, b)
        self.assertNotIn(" ", a)

    def test_canonical_rejects_nan(self):
        with self.assertRaises(pkr.KnowledgeRecipeError):
            pkr.canonical({"k": float("nan")})


class TestFileAddHappyPath(unittest.TestCase):

    def test_full_recipe_shape_and_paths(self):
        request = file_request(WS_TEXT)
        recipe = build_file_add(request)
        self.assertEqual(recipe["schema"], pkr.SCHEMA_RECIPE)
        self.assertEqual(recipe["state"], "DRAFT_ONLY")
        self.assertEqual(recipe["action"], "project_file_add")
        self.assertEqual(recipe["work_ref"], "WS:SPEC-EDITING")
        self.assertEqual(recipe["request_id"], request["request_id"])
        self.assertEqual(recipe["captured_commit"], COMMIT)
        self.assertEqual(recipe["permission_binding_digest"], DIGEST)
        expected_id = canonical_sha256({
            "principal_scope": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "request_id": request["request_id"],
            "work_ref": "WS:SPEC-EDITING",
        })
        file_image, ws_image = recipe["postimages"]
        self.assertEqual(len(recipe["postimages"]), 2)
        self.assertEqual(
            file_image["path"],
            "agentos/project-files/WS-SPEC-EDITING/%s.md" % expected_id,
        )
        self.assertEqual(file_image["expected_preimage_sha256"], None)
        self.assertEqual(ws_image["path"], "agentos/workstreams/WS-SPEC-EDITING.md")
        self.assertEqual(ws_image["expected_preimage_sha256"], sha256_text(WS_TEXT))

    def test_exact_file_bytes_preserved(self):
        content = "# 标题\n\nline one\nline two\r\nwith tab\there\n"
        request = file_request(
            WS_TEXT, display_name="性能说明.md", media_type="text/markdown",
            content=content)
        recipe = build_file_add(request)
        file_image = recipe["postimages"][0]
        self.assertEqual(file_image["content_utf8"], content)
        self.assertEqual(file_image["content_sha256"], sha256_text(content))

    def test_txt_extension_and_media_type(self):
        request = file_request(
            WS_TEXT, display_name="NOTES.TXT", media_type="text/plain",
            content="plain text\n")
        recipe = build_file_add(request)
        path = recipe["postimages"][0]["path"]
        self.assertTrue(path.endswith(".txt"), path)
        self.assertEqual(recipe["postimages"][0]["content_utf8"], "plain text\n")

    def test_ws_postimage_preserves_unrelated_fields_and_body(self):
        recipe = build_file_add(file_request(WS_TEXT))
        ws_text = recipe["postimages"][1]["content_utf8"]
        data, body = pkr._load_record(ws_text, "INVALID_WORKSTREAM_RECORD")
        self.assertEqual(body, WS_BODY)
        self.assertEqual(data["schema"], "agentos.workstream.v1")
        self.assertEqual(data["key"], "SPEC-EDITING")
        self.assertEqual(data["objective"], "Ship observable spec editing behaviour.")
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["program"], "mmos-core")
        self.assertEqual(data["repos"], ["macro", "terminal"])
        self.assertEqual(data["owner"], "chairman")
        self.assertEqual(data["waves"], [{"label": "wave-1"}])
        self.assertEqual(data["decisions"], ["DEC:EARLIER-CALL"])
        entry = data["project_files"][0]
        self.assertEqual(data["artifacts"],
                         ["research/notes.md", entry["artifact_ref"]])
        self.assertEqual(entry["display_name"], "notes.md")
        self.assertEqual(entry["media_type"], "text/markdown")
        self.assertEqual(entry["origin"]["kind"], "PRINCIPAL_UPLOAD")
        self.assertEqual(entry["origin"]["actor_ref"], ACTOR)
        self.assertEqual(entry["origin"]["request_sha256"],
                         recipe["request_fingerprint"])
        self.assertEqual(entry["content_sha256"],
                         recipe["postimages"][0]["content_sha256"])

    def test_deterministic_id_fingerprint_and_repeat(self):
        request = file_request(WS_TEXT)
        first = build_file_add(request)
        second = build_file_add(file_request(WS_TEXT))
        self.assertEqual(first, second)
        expected_fingerprint = canonical_sha256({
            "schema": pkr.SCHEMA_REQUEST_FINGERPRINT,
            "request": request,
            "actor_ref": ACTOR,
            "permission_binding_digest": DIGEST,
            "captured_commit": COMMIT,
            "preimages": {"workstream": sha256_text(WS_TEXT), "file": None},
        })
        self.assertEqual(first["request_fingerprint"], expected_fingerprint)

    def test_identity_changes_with_scope_and_request(self):
        base = file_request(WS_TEXT)
        other_scope = build_file_add(base, actor=ACTOR_B)
        other_request = file_request(
            WS_TEXT, request_id="mmos-project-file-add-" + hex_(40, "f"))
        self.assertNotEqual(
            other_scope["postimages"][0]["path"],
            build_file_add(base)["postimages"][0]["path"])
        self.assertNotEqual(
            other_request["request_id"], base["request_id"])
        self.assertNotEqual(
            build_file_add(other_request)["postimages"][0]["path"],
            build_file_add(base)["postimages"][0]["path"])

    def test_postimage_entries_are_closed(self):
        recipe = build_file_add(file_request(WS_TEXT))
        self.assertEqual(
            set(recipe.keys()),
            {"schema", "state", "action", "work_ref", "request_id",
             "request_fingerprint", "captured_commit",
             "permission_binding_digest", "postimages"})
        for image in recipe["postimages"]:
            self.assertEqual(
                set(image.keys()),
                {"path", "content_utf8", "content_sha256",
                 "expected_preimage_sha256"})

class TestFileAddRejections(unittest.TestCase):

    def test_wrong_schema_and_extra_keys(self):
        bad = file_request(WS_TEXT)
        bad["schema"] = "mastermind.project_file_add_request.v2"
        assert_raises(self, "MALFORMED_REQUEST_SCHEMA", build_file_add, bad)
        extra = file_request(WS_TEXT)
        extra["grant"] = "do-it"
        assert_raises(self, "MALFORMED_REQUEST_SCHEMA", build_file_add, extra)
        missing = file_request(WS_TEXT)
        del missing["base_revision"]
        assert_raises(self, "MALFORMED_REQUEST_SCHEMA", build_file_add, missing)

    def test_no_boolean_authorizes_anything(self):
        bools = file_request(WS_TEXT)
        bools["base_revision"] = True
        assert_raises(self, "MALFORMED_REQUEST_SCHEMA", build_file_add, bools)
        bool_file = file_request(WS_TEXT)
        bool_file["file"] = True
        assert_raises(self, "MALFORMED_REQUEST_SCHEMA", build_file_add, bool_file)
        assert_raises(self, "INVALID_ACTOR_REF", build_file_add,
                      file_request(WS_TEXT), actor=True)
        assert_raises(self, "INVALID_PERMISSION_BINDING_DIGEST",
                      pkr.build_project_file_add, file_request(WS_TEXT),
                      actor_ref=ACTOR, permission_binding_digest=True,
                      captured_commit=COMMIT, workstream_text=WS_TEXT)

    def test_request_id_prefix_and_stamp(self):
        short = file_request(WS_TEXT, request_id="mmos-project-file-add-" + hex_(39))
        assert_raises(self, "INVALID_REQUEST_ID", build_file_add, short)
        upper = file_request(WS_TEXT, request_id="mmos-project-file-add-" + "A" * 40)
        assert_raises(self, "INVALID_REQUEST_ID", build_file_add, upper)
        wrong_prefix = pref_request(WS_NO_DECISIONS)["request_id"]
        swapped = file_request(WS_TEXT, request_id=wrong_prefix)
        assert_raises(self, "INVALID_REQUEST_ID", build_file_add, swapped)

    def test_source_commit_must_equal_captured_commit(self):
        request = file_request(WS_TEXT)
        request["source_commit"] = hex_(40, "9")
        assert_raises(self, "SOURCE_COMMIT_MISMATCH", build_file_add, request)

    def test_stale_base_revision_rejected(self):
        request = file_request(WS_TEXT)
        request["base_revision"] = sha256_text(WS_TEXT + "tampered\n")
        assert_raises(self, "BASE_REVISION_MISMATCH", build_file_add, request)

    def test_cross_work_scope_rejected(self):
        request = file_request(WS_TEXT, work_ref="WS:OTHER-KEY")
        assert_raises(self, "WORK_SCOPE_MISMATCH", build_file_add, request)

    def test_bad_work_ref_shapes(self):
        for bad in ("WS:A", "WS:spec-editing", "WS:SPEC-EDITING-",
                    "WS:SPEC--EDITING", "spec-editing", "WS:SPEC EDITING"):
            request = file_request(WS_TEXT, work_ref=bad)
            assert_raises(self, "INVALID_WORK_REF", build_file_add, request)

    def test_actor_ref_bounded_trusted_scope(self):
        for bad in ("workspace:principal-label", "workspace:" + "G" * 64, "workspace:" + "a" * 63, "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", "workspace:", "workspace:  ",
                    "workspace:scope with space", "workspace:" + "x" * 300):
            assert_raises(self, "INVALID_ACTOR_REF", build_file_add,
                          file_request(WS_TEXT), actor=bad)

    def test_digest_and_commit_shapes(self):
        assert_raises(
            self, "INVALID_PERMISSION_BINDING_DIGEST",
            pkr.build_project_file_add, file_request(WS_TEXT),
            actor_ref=ACTOR, permission_binding_digest=hex_(63),
            captured_commit=COMMIT, workstream_text=WS_TEXT)
        assert_raises(
            self, "INVALID_CAPTURED_COMMIT",
            pkr.build_project_file_add, file_request(WS_TEXT),
            actor_ref=ACTOR, permission_binding_digest=DIGEST,
            captured_commit=hex_(40).upper(), workstream_text=WS_TEXT)

    def test_workstream_text_limit_and_workspace_validation(self):
        huge = WS_TEXT + ("# pad\n" * 30000)
        self.assertGreater(len(huge.encode("utf-8")), pkr.MAX_WORKSTREAM_BYTES)
        assert_raises(self, "LIMIT_EXCEEDED", build_file_add,
                      file_request(huge), workstream_text=huge)
        assert_raises(self, "INVALID_WORKSTREAM_TEXT", build_file_add,
                      file_request(WS_TEXT), workstream_text=WS_TEXT.encode("utf-8"))
        no_fence = WS_TEXT.replace("---\n", "", 1)
        assert_raises(self, "INVALID_WORKSTREAM_RECORD", build_file_add,
                      file_request(no_fence), workstream_text=no_fence)

    def test_workstream_structural_fields(self):
        cases = [
            (WS_TEXT.replace("repos:\n- macro\n- terminal\n", "repos:\n- terminal\n"),
             "WS:SPEC-EDITING", "REPOSITORY_SCOPE_MISMATCH"),
            (WS_TEXT.replace("status: active\n", "status: done-forever\n"),
             "WS:SPEC-EDITING", "INVALID_WORKSTREAM_FIELD"),
            (WS_TEXT.replace("key: SPEC-EDITING\n", "key: OTHER-KEY\n"),
             "WS:SPEC-EDITING", "WORK_SCOPE_MISMATCH"),
            (WS_TEXT.replace("waves:\n- label: wave-1\n", "waves: []\n"),
             "WS:SPEC-EDITING", "INVALID_WORKSTREAM_FIELD"),
        ]
        for text, work_ref, code in cases:
            request = file_request(text, work_ref=work_ref)
            assert_raises(self, code, build_file_add, request,
                          workstream_text=text)

    def test_display_name_rules(self):
        bad_names = [
            "", "noext", ".md", "with/slash.md", "with\\back.md", "a" * 129 + ".md",
            "doc.rst", "doc.pdf", "nul\x00.md", "ctl\x01.md", "del\x7f.md",
        ]
        for name in bad_names:
            request = file_request(WS_TEXT, display_name=name)
            assert_raises(self, "INVALID_PROJECT_FILE", build_file_add, request)

    def test_media_type_rules(self):
        request = file_request(WS_TEXT, display_name="notes.md",
                               media_type="text/plain")
        assert_raises(self, "INVALID_PROJECT_FILE", build_file_add, request)
        request = file_request(WS_TEXT, display_name="notes.txt",
                               media_type="text/markdown")
        assert_raises(self, "INVALID_PROJECT_FILE", build_file_add, request)
        request = file_request(WS_TEXT, display_name="notes.md",
                               media_type="text/HTML")
        assert_raises(self, "INVALID_PROJECT_FILE", build_file_add, request)

    def test_content_rules(self):
        assert_raises(self, "INVALID_PROJECT_FILE", build_file_add,
                      file_request(WS_TEXT, content=""))
        assert_raises(self, "INVALID_PROJECT_FILE", build_file_add,
                      file_request(WS_TEXT, content="bad\x00nul\n"))
        assert_raises(self, "INVALID_PROJECT_FILE", build_file_add,
                      file_request(WS_TEXT, content="bad\x01ctl\n"))
        assert_raises(self, "INVALID_PROJECT_FILE", build_file_add,
                      file_request(WS_TEXT, content="del\x7f\n"))
        assert_raises(self, "INVALID_PROJECT_FILE", build_file_add,
                      file_request(WS_TEXT, content="c1\x85\n"))
        assert_raises(self, "INVALID_PROJECT_FILE", build_file_add,
                      file_request(WS_TEXT, content="lone\ud800surrogate"))
        big = "x" * (pkr.MAX_FILE_BYTES + 1) + "\n"
        assert_raises(self, "LIMIT_EXCEEDED", build_file_add,
                      file_request(WS_TEXT, content=big))
        ok = "y" * (pkr.MAX_FILE_BYTES - 1) + "\n"
        build_file_add(file_request(WS_TEXT, content=ok))

    def test_error_message_leaks_nothing(self):
        marker = "confidential-secret-marker"
        request = file_request(WS_TEXT, content="ctl\x01" + marker + "\n")
        exc = assert_raises(self, "INVALID_PROJECT_FILE", build_file_add, request)
        self.assertNotIn(marker, str(exc))
        self.assertNotIn(marker, exc.code)

def recorded_entry(request, actor=ACTOR):
    recipe = build_file_add(request, actor=actor)
    ws_text = recipe["postimages"][1]["content_utf8"]
    data, _ = pkr._load_record(ws_text, "INVALID_WORKSTREAM_RECORD")
    return data["project_files"][0], ws_text


def ws_with_project_files(entries, *, artifacts=None):
    lines = WS_TEXT.splitlines(keepends=True)
    block = "".join(lines)
    extra = ("project_files:\n" + "".join(_dump_entry(entry) for entry in entries)) if entries else "project_files: []\n"
    if artifacts is None and entries:
        artifacts = list(dict.fromkeys(entry["artifact_ref"] for entry in entries))
    if artifacts is not None:
        block = block.replace(
            "artifacts:\n- research/notes.md\n",
            "artifacts:\n- research/notes.md\n" +
            "".join("- %s\n" % a for a in artifacts))
    return block.replace("---\n" + WS_BODY, extra + "---\n" + WS_BODY)


def _dump_entry(entry):
    text = pkr._dump_yaml({"__e__": entry})
    body = text.split("__e__:\n", 1)[1]
    lines = body.splitlines(keepends=True)
    return "".join(
        ("- " + line[2:]) if index == 0 else ("  " + line[2:])
        for index, line in enumerate(lines))


class TestFileAddConflictsAndLimits(unittest.TestCase):

    def test_same_identity_same_metadata_is_already_recorded(self):
        request = file_request(WS_TEXT)
        first = build_file_add(request)
        ws_text = first["postimages"][1]["content_utf8"]
        replay = file_request(ws_text, request_id=request["request_id"])
        assert_raises(self, "ALREADY_RECORDED", build_file_add, replay,
                      workstream_text=ws_text)

    def test_captured_existing_file_text_is_already_recorded(self):
        request = file_request(WS_TEXT)
        assert_raises(self, "ALREADY_RECORDED", build_file_add, request,
                      existing_file_text="# previous upload\n")

    def test_same_id_different_metadata_is_conflict(self):
        request = file_request(WS_TEXT)
        other = file_request(WS_TEXT)
        other["file"]["content_utf8"] = "different content\n"
        entry, _ = recorded_entry(other)
        text = ws_with_project_files([entry])
        request["base_revision"] = sha256_text(text)
        assert_raises(self, "CONFLICT", build_file_add, request,
                      workstream_text=text)

    def test_duplicate_id_or_path_in_existing_entries_is_conflict(self):
        request = file_request(WS_TEXT)
        entry, _ = recorded_entry(request)
        clone = dict(entry)
        clone["display_name"] = "notes.txt"
        clone["media_type"] = "text/plain"
        clone["artifact_ref"] = entry["artifact_ref"][:-3] + ".txt"
        text = ws_with_project_files([entry, clone])
        request["base_revision"] = sha256_text(text)
        assert_raises(self, "CONFLICT", build_file_add, request,
                      workstream_text=text)
        text2 = ws_with_project_files([entry, dict(entry)])
        request2 = file_request(
            WS_TEXT,
            request_id="mmos-project-file-add-" + hex_(40, "e"))
        request2["base_revision"] = sha256_text(text2)
        assert_raises(self, "CONFLICT", build_file_add, request2,
                      workstream_text=text2)

    def test_existing_entry_with_extra_metadata_is_rejected(self):
        entry, _ = recorded_entry(file_request(WS_TEXT))
        entry["note"] = "extra"
        text = ws_with_project_files([entry])
        request = file_request(WS_TEXT)
        request["base_revision"] = sha256_text(text)
        assert_raises(self, "INVALID_EXISTING_PROJECT_FILE", build_file_add,
                      request, workstream_text=text)

    def test_existing_entry_cross_scope_path_is_rejected(self):
        entry, _ = recorded_entry(file_request(WS_TEXT))
        entry["artifact_ref"] = entry["artifact_ref"].replace(
            "WS-SPEC-EDITING", "WS-OTHER-KEY")
        text = ws_with_project_files([entry])
        request = file_request(WS_TEXT)
        request["base_revision"] = sha256_text(text)
        assert_raises(self, "INVALID_EXISTING_PROJECT_FILE", build_file_add,
                      request, workstream_text=text)

    def test_project_files_cap_32(self):
        entries = []
        for i in range(32):
            req = file_request(
                WS_TEXT, request_id="mmos-project-file-add-" + hex_(38, "1") +
                "%02d" % i)
            req_entry, _ = recorded_entry(req)
            entries.append(req_entry)
        text = ws_with_project_files(entries)
        request = file_request(WS_TEXT)
        request["base_revision"] = sha256_text(text)
        assert_raises(self, "LIMIT_EXCEEDED", build_file_add, request,
                      workstream_text=text)
        text31 = ws_with_project_files(entries[:31])
        request31 = file_request(WS_TEXT)
        request31["base_revision"] = sha256_text(text31)
        recipe = build_file_add(request31, workstream_text=text31)
        data, _ = pkr._load_record(
            recipe["postimages"][1]["content_utf8"], "INVALID_WORKSTREAM_RECORD")
        self.assertEqual(len(data["project_files"]), 32)

    def test_artifacts_cap_256_no_truncation(self):
        entry, _ = recorded_entry(file_request(WS_TEXT))
        legacy = ["docs/legacy-%03d.md" % i for i in range(256)]
        text = ws_with_project_files([], artifacts=legacy)
        request = file_request(WS_TEXT)
        request["base_revision"] = sha256_text(text)
        assert_raises(self, "LIMIT_EXCEEDED", build_file_add, request,
                      workstream_text=text)
        legacy255 = legacy[:254]
        text255 = ws_with_project_files([], artifacts=legacy255)
        request255 = file_request(WS_TEXT)
        request255["base_revision"] = sha256_text(text255)
        recipe = build_file_add(request255, workstream_text=text255)
        data, _ = pkr._load_record(
            recipe["postimages"][1]["content_utf8"], "INVALID_WORKSTREAM_RECORD")
        self.assertEqual(len(data["artifacts"]), 256)
        self.assertEqual(data["artifacts"][:-1], ["research/notes.md"] + legacy255)
        self.assertEqual(data["artifacts"][255],
                         recipe["postimages"][0]["path"])

    def test_legacy_artifacts_entries_untouched(self):
        entry, _ = recorded_entry(file_request(WS_TEXT))
        legacy = ["docs/with space.md", "docs/中文-档案.md"]
        text = ws_with_project_files([], artifacts=legacy)
        request = file_request(WS_TEXT)
        request["base_revision"] = sha256_text(text)
        recipe = build_file_add(request, workstream_text=text)
        data, _ = pkr._load_record(
            recipe["postimages"][1]["content_utf8"], "INVALID_WORKSTREAM_RECORD")
        self.assertEqual(data["artifacts"][0], "research/notes.md")
        self.assertEqual(data["artifacts"][1:3], legacy)

    def test_malformed_decisions_list_rejected(self):
        text = WS_TEXT.replace("decisions:\n- DEC:EARLIER-CALL\n",
                               "decisions:\n- EARLIER-CALL\n")
        request = file_request(text)
        assert_raises(self, "INVALID_WORKSTREAM_FIELD", build_file_add,
                      request, workstream_text=text)
        text2 = WS_TEXT.replace("artifacts:\n- research/notes.md\n",
                                "artifacts: not-a-list\n")
        request2 = file_request(text2)
        assert_raises(self, "INVALID_WORKSTREAM_FIELD", build_file_add,
                      request2, workstream_text=text2)

    def test_missing_lists_default_to_empty(self):
        text = WS_TEXT.replace("decisions:\n- DEC:EARLIER-CALL\n", "") \
                      .replace("artifacts:\n- research/notes.md\n", "")
        request = file_request(text)
        recipe = build_file_add(request, workstream_text=text)
        data, _ = pkr._load_record(
            recipe["postimages"][1]["content_utf8"], "INVALID_WORKSTREAM_RECORD")
        self.assertEqual(data.get("decisions", []), [])
        self.assertEqual(data["artifacts"], [recipe["postimages"][0]["path"]])

DEC_PATH = "agentos/decisions/DEC-" + pkr.PREFERENCE_DECISION_KEY_PREFIX + "SPEC-EDITING.md"


class TestPreferenceNew(unittest.TestCase):

    def test_new_record_is_closed_and_exact(self):
        request = pref_request(WS_NO_DECISIONS, value="以后请用中文写周报。")
        recipe = build_pref(request)
        self.assertEqual(recipe["state"], "DRAFT_ONLY")
        self.assertEqual(recipe["action"], "project_preference_set")
        self.assertEqual(recipe["work_ref"], "WS:SPEC-EDITING")
        self.assertEqual(len(recipe["postimages"]), 2)
        dec_image, ws_image = recipe["postimages"]
        self.assertEqual(dec_image["path"], DEC_PATH)
        self.assertEqual(dec_image["expected_preimage_sha256"], None)
        self.assertEqual(ws_image["path"], "agentos/workstreams/WS-SPEC-EDITING.md")
        self.assertEqual(ws_image["expected_preimage_sha256"],
                         sha256_text(WS_NO_DECISIONS))
        data, body = pkr._load_record(dec_image["content_utf8"],
                                      "INVALID_EXISTING_DECISION")
        self.assertEqual(body, "")
        self.assertEqual(data["key"], pkr.PREFERENCE_DECISION_KEY_PREFIX + "SPEC-EDITING")
        self.assertEqual(
            data["question"], pkr.PREFERENCE_QUESTION)
        self.assertEqual(data["answer"], "以后请用中文写周报。")
        self.assertEqual(data["rationale"], pkr.PREFERENCE_RATIONALE)
        self.assertEqual(data["alternatives"], [{
            "option": pkr.PREFERENCE_ALTERNATIVE_OPTION,
            "why_not": pkr.PREFERENCE_ALTERNATIVE_WHY_NOT}])
        self.assertEqual(data["evidence"],
                         ["project-authoring-request:" + recipe["request_fingerprint"]])
        self.assertEqual(data["affects"], ["WS:SPEC-EDITING"])
        self.assertEqual(data["confidence"], "high")
        self.assertEqual(data["reversibility"], "easy")
        self.assertEqual(data["decided_by"], ACTOR)
        self.assertEqual(data["decided_at"], "2026-11-04")
        self.assertNotIn("created", data)
        self.assertNotIn("updated", data)
        preference = data["project_preference"]
        self.assertEqual(preference["schema"], "agentos.project_preference.v1")
        self.assertEqual(preference["work_ref"], "WS:SPEC-EDITING")
        self.assertEqual(preference["kind"], "COMMUNICATION")
        self.assertEqual(preference["value"], "以后请用中文写周报。")
        self.assertEqual(preference["origin"], {
            "kind": "USER_EDIT", "actor_ref": ACTOR,
            "source_ref": None, "source_revision": None})
        self.assertEqual(preference["last_edit"], {
            "actor_ref": ACTOR,
            "request_sha256": recipe["request_fingerprint"]})

    def test_new_fingerprint_and_ws_pointer(self):
        request = pref_request(WS_NO_DECISIONS)
        recipe = build_pref(request)
        expected = canonical_sha256({
            "schema": pkr.SCHEMA_REQUEST_FINGERPRINT,
            "request": request,
            "actor_ref": ACTOR,
            "permission_binding_digest": DIGEST,
            "captured_commit": COMMIT,
            "preimages": {"workstream": sha256_text(WS_NO_DECISIONS),
                          "decision": None},
        })
        self.assertEqual(recipe["request_fingerprint"], expected)
        ws_data, _ = pkr._load_record(
            recipe["postimages"][1]["content_utf8"], "INVALID_WORKSTREAM_RECORD")
        self.assertEqual(ws_data["decisions"], [DEC_POINTER])
        self.assertEqual(ws_data["artifacts"], ["research/notes.md"])
        self.assertNotIn("project_files", ws_data)
        self.assertEqual(recipe["postimages"][0]["content_utf8"],
                         build_pref(pref_request(WS_NO_DECISIONS))
                         ["postimages"][0]["content_utf8"])

    def test_multiline_and_zh_literal_preserved(self):
        value = "周报用中文。\n每天站会用英文，保持简短。\t谢谢。\n"
        request = pref_request(WS_NO_DECISIONS, value=value)
        recipe = build_pref(request)
        dec_text = recipe["postimages"][0]["content_utf8"]
        data, _ = pkr._load_record(dec_text, "INVALID_EXISTING_DECISION")
        self.assertEqual(data["project_preference"]["value"], value)
        self.assertEqual(recipe["postimages"][0]["content_sha256"],
                         sha256_text(dec_text))

    def test_value_limits(self):
        exact = "v" * pkr.MAX_PREFERENCE_BYTES
        build_pref(pref_request(WS_NO_DECISIONS, value=exact))
        over = "v" * (pkr.MAX_PREFERENCE_BYTES + 1)
        assert_raises(self, "LIMIT_EXCEEDED", build_pref,
                      pref_request(WS_NO_DECISIONS, value=over))
        assert_raises(self, "INVALID_PREFERENCE_VALUE", build_pref,
                      pref_request(WS_NO_DECISIONS, value="   "))
        assert_raises(self, "INVALID_PREFERENCE_VALUE", build_pref,
                      pref_request(WS_NO_DECISIONS, value="bad\x00"))
        assert_raises(self, "INVALID_PREFERENCE_VALUE", build_pref,
                      pref_request(WS_NO_DECISIONS, value="lone\ud800"))

    def test_no_inference_from_titles_or_model_text(self):
        request = pref_request(WS_NO_DECISIONS, value="ship it")
        recipe = build_pref(request)
        dec_text = recipe["postimages"][0]["content_utf8"]
        self.assertNotIn("Spec editing pipeline", dec_text)

    def test_new_requires_null_expected_revision_and_no_pointer(self):
        request = pref_request(WS_NO_DECISIONS,
                               expected=sha256_text("whatever"))
        assert_raises(self, "SOURCE_MISMATCH", build_pref, request)
        dec, ws_after, _ = new_preference_pair()
        request2 = pref_request(ws_after)
        assert_raises(self, "SOURCE_MISMATCH", build_pref, request2,
                      workstream_text=ws_after)

    def test_decision_date_is_real_calendar_date(self):
        build_pref(pref_request(WS_NO_DECISIONS), decision_date="2024-02-29")
        for bad in ("2026-02-30", "2026-13-01", "2026-00-10", "20261104",
                    "2026-11-4", "not-a-date", 20261104):
            assert_raises(self, "INVALID_DECISION_DATE", build_pref,
                          pref_request(WS_NO_DECISIONS), decision_date=bad)

def new_preference_pair(*, value="以后请用中文写周报。", actor=ACTOR,
                        request_id="mmos-project-preference-set-" + hex_(40, "d")):
    request = pref_request(WS_NO_DECISIONS, request_id=request_id, value=value)
    recipe = build_pref(request, actor=actor)
    return (
        recipe["postimages"][0]["content_utf8"],
        recipe["postimages"][1]["content_utf8"],
        recipe,
    )


class TestPreferenceEdit(unittest.TestCase):

    def test_edit_updates_provenance_and_preserves_fields(self):
        old_dec, ws_after, first = new_preference_pair()
        request = pref_request(
            ws_after, request_id="mmos-project-preference-set-" + hex_(40, "2"),
            expected=sha256_text(old_dec), value="改用英文，每周五发。")
        recipe = build_pref(request, actor=ACTOR_B, workstream_text=ws_after,
                            decision_text=old_dec, decision_date="2026-11-05")
        dec_image, ws_image = recipe["postimages"]
        self.assertEqual(dec_image["expected_preimage_sha256"],
                         sha256_text(old_dec))
        self.assertEqual(ws_image["expected_preimage_sha256"],
                         sha256_text(ws_after))
        data, _ = pkr._load_record(dec_image["content_utf8"],
                                   "INVALID_EXISTING_DECISION")
        self.assertEqual(data["answer"], "改用英文，每周五发。")
        self.assertEqual(data["project_preference"]["value"], "改用英文，每周五发。")
        self.assertEqual(data["decided_by"], ACTOR_B)
        self.assertEqual(data["decided_at"], "2026-11-05")
        self.assertEqual(data["project_preference"]["last_edit"], {
            "actor_ref": ACTOR_B,
            "request_sha256": recipe["request_fingerprint"]})
        self.assertEqual(data["project_preference"]["origin"], {
            "kind": "USER_EDIT", "actor_ref": ACTOR,
            "source_ref": None, "source_revision": None})
        self.assertEqual(
            data["evidence"],
            ["project-authoring-request:" + first["request_fingerprint"],
             "project-authoring-request:" + recipe["request_fingerprint"]])
        self.assertEqual(data["question"], pkr.PREFERENCE_QUESTION)
        self.assertEqual(data["rationale"], pkr.PREFERENCE_RATIONALE)
        self.assertEqual(data["affects"], ["WS:SPEC-EDITING"])
        ws_data, _ = pkr._load_record(ws_image["content_utf8"],
                                      "INVALID_WORKSTREAM_RECORD")
        self.assertEqual(ws_data["decisions"], [DEC_POINTER])
        self.assertNotIn("project_files", ws_data)
        self.assertEqual(ws_data["artifacts"], ["research/notes.md"])

    def test_conversation_origin_preserved_on_edit(self):
        old_dec, ws_after, _ = new_preference_pair()
        source_ref = "session-reply-" + hex_(64, "e")
        source_revision = hex_(64, "f")
        qualified = old_dec.replace(
            "origin:\n    kind: USER_EDIT\n    actor_ref: workspace:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n"
            "    source_ref: null\n    source_revision: null\n",
            "origin:\n    kind: CONVERSATION\n"
            "    actor_ref: workspace:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc\n"
            "    source_ref: %s\n    source_revision: %s\n"
            % (source_ref, source_revision))
        self.assertIn("kind: CONVERSATION", qualified)
        request = pref_request(
            ws_after, request_id="mmos-project-preference-set-" + hex_(40, "3"),
            expected=sha256_text(qualified), value="改用英文，每周五发。")
        recipe = build_pref(request, actor=ACTOR_B, workstream_text=ws_after,
                            decision_text=qualified, decision_date="2026-11-06")
        data, _ = pkr._load_record(
            recipe["postimages"][0]["content_utf8"], "INVALID_EXISTING_DECISION")
        self.assertEqual(data["project_preference"]["origin"], {
            "kind": "CONVERSATION",
            "actor_ref": "workspace:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
            "source_ref": source_ref,
            "source_revision": source_revision})

    def test_stale_expected_revision_is_source_mismatch(self):
        old_dec, ws_after, _ = new_preference_pair()
        request = pref_request(
            ws_after, request_id="mmos-project-preference-set-" + hex_(40, "4"),
            expected=hex_(64, "0"), value="改用英文。")
        assert_raises(self, "SOURCE_MISMATCH", build_pref, request,
                      actor=ACTOR_B, workstream_text=ws_after,
                      decision_text=old_dec, decision_date="2026-11-05")

    def test_edit_without_ws_pointer_is_source_mismatch(self):
        old_dec, _, _ = new_preference_pair()
        request = pref_request(
            WS_NO_DECISIONS,
            request_id="mmos-project-preference-set-" + hex_(40, "5"),
            expected=sha256_text(old_dec))
        assert_raises(self, "SOURCE_MISMATCH", build_pref, request,
                      decision_text=old_dec)

    def test_tampered_existing_record_variants(self):
        old_dec, ws_after, _ = new_preference_pair()

        def variant(**replacements):
            data, _ = pkr._load_record(old_dec, "INVALID_EXISTING_DECISION")
            data.update(replacements)
            return pkr._serialize_record(data, "")

        def expect_reject(text, code="INVALID_EXISTING_DECISION"):
            request = pref_request(
                ws_after,
                request_id="mmos-project-preference-set-" + hex_(40, "6"),
                expected=sha256_text(text))
            assert_raises(self, code, build_pref, request, actor=ACTOR_B,
                          workstream_text=ws_after, decision_text=text,
                          decision_date="2026-11-05")

        expect_reject(variant(key="OTHER-KEY"))
        expect_reject(variant(question="A different question?"))
        expect_reject(variant(affects=["WS:OTHER-KEY"]))
        expect_reject(variant(confidence="low"))
        expect_reject(variant(superseded_by="DEC:OTHER-KEY"))
        expect_reject(variant(created="2026-01-01", updated="2026-01-02"))
        expect_reject(variant(unexpected_field="x"))
        expect_reject(
            variant(**{"project_preference": {
                "schema": "agentos.project_preference.v1",
                "work_ref": "WS:SPEC-EDITING", "kind": "COMMUNICATION",
                "value": "以后请用中文写周报。",
                "origin": {"kind": "USER_EDIT", "actor_ref": ACTOR,
                           "source_ref": "session-reply-" + hex_(64, "e"),
                           "source_revision": None},
                "last_edit": {"actor_ref": ACTOR,
                              "request_sha256": hex_(64, "1")}}}))
        mismatched = old_dec.replace(
            "answer: 以后请用中文写周报。", "answer: 别的回答")
        expect_reject(mismatched)
        oversized = old_dec + ("# pad\n" * 3000)
        self.assertGreater(len(oversized.encode("utf-8")), pkr.MAX_DECISION_BYTES)
        request = pref_request(
            ws_after, request_id="mmos-project-preference-set-" + hex_(40, "7"),
            expected=sha256_text(oversized))
        assert_raises(self, "LIMIT_EXCEEDED", build_pref, request,
                      actor=ACTOR_B, workstream_text=ws_after,
                      decision_text=oversized, decision_date="2026-11-05")

    def test_evidence_cap_64(self):
        old_dec, ws_after, _ = new_preference_pair()
        data, _ = pkr._load_record(old_dec, "INVALID_EXISTING_DECISION")
        data["evidence"] = ["project-authoring-request:" + hex_(64, str(i % 10))
                            for i in range(64)]
        full = pkr._serialize_record(data, "")
        request = pref_request(
            ws_after, request_id="mmos-project-preference-set-" + hex_(40, "8"),
            expected=sha256_text(full), value="改用英文。")
        assert_raises(self, "LIMIT_EXCEEDED", build_pref, request,
                      actor=ACTOR_B, workstream_text=ws_after,
                      decision_text=full, decision_date="2026-11-05")
        data["evidence"] = data["evidence"][:63]
        almost = pkr._serialize_record(data, "")
        request2 = pref_request(
            ws_after, request_id="mmos-project-preference-set-" + hex_(40, "9"),
            expected=sha256_text(almost), value="改用英文。")
        recipe = build_pref(request2, actor=ACTOR_B, workstream_text=ws_after,
                            decision_text=almost, decision_date="2026-11-05")
        edited, _ = pkr._load_record(
            recipe["postimages"][0]["content_utf8"], "INVALID_EXISTING_DECISION")
        self.assertEqual(len(edited["evidence"]), 64)

    def test_preference_request_shape(self):
        bad = pref_request(WS_NO_DECISIONS)
        bad["schema"] = "mastermind.project_preference_set_request.v2"
        assert_raises(self, "MALFORMED_REQUEST_SCHEMA", build_pref, bad)
        extra = pref_request(WS_NO_DECISIONS)
        extra["origin"] = {"kind": "CONVERSATION"}
        assert_raises(self, "MALFORMED_REQUEST_SCHEMA", build_pref, extra)
        missing = pref_request(WS_NO_DECISIONS)
        del missing["value"]
        assert_raises(self, "MALFORMED_REQUEST_SCHEMA", build_pref, missing)
        boolrev = pref_request(WS_NO_DECISIONS, expected=True)
        assert_raises(self, "MALFORMED_REQUEST_SCHEMA", build_pref, boolrev)
        wrongprefix = pref_request(
            WS_NO_DECISIONS,
            request_id="mmos-project-file-add-" + hex_(40))
        assert_raises(self, "INVALID_REQUEST_ID", build_pref, wrongprefix)
        sourcemismatch = pref_request(WS_NO_DECISIONS)
        sourcemismatch["source_commit"] = hex_(40, "7")
        assert_raises(self, "SOURCE_COMMIT_MISMATCH", build_pref, sourcemismatch)

class TestDraftOnlyGuarantees(unittest.TestCase):

    def test_never_claims_receipt_publication_or_memory_state(self):
        recipes = [
            build_file_add(file_request(WS_TEXT)),
            build_pref(pref_request(WS_NO_DECISIONS)),
        ]
        blob = pkr.canonical(recipes)
        for forbidden in ("uploaded", "saved", "published", "accepted",
                          "receipt", "APPLIED", "COMMITTED", "memory_saved"):
            self.assertNotIn('"%s"' % forbidden, blob)
        for recipe in recipes:
            self.assertEqual(recipe["state"], "DRAFT_ONLY")

    def test_rejections_return_no_partial_postimages(self):
        request = file_request(WS_TEXT)
        request["base_revision"] = hex_(64, "0")
        try:
            build_file_add(request)
        except pkr.KnowledgeRecipeError:
            pass
        else:
            self.fail("expected rejection")

    def test_inputs_are_never_mutated(self):
        request = file_request(WS_TEXT)
        snapshot = pkr.canonical(request)
        build_file_add(request)
        self.assertEqual(pkr.canonical(request), snapshot)
        preq = pref_request(WS_NO_DECISIONS)
        psnap = pkr.canonical(preq)
        build_pref(preq)
        self.assertEqual(pkr.canonical(preq), psnap)
        self.assertTrue(WS_TEXT.endswith(WS_BODY))

    def test_output_within_global_byte_cap(self):
        recipe = build_pref(pref_request(WS_NO_DECISIONS))
        total = sum(len(image["content_utf8"].encode("utf-8"))
                    for image in recipe["postimages"])
        self.assertLessEqual(total, pkr.MAX_RECIPE_OUTPUT_BYTES)


class TestRealMacroValidator(unittest.TestCase):
    """Exercises the actual scripts/agentos.py validator when present.

    Skipped in a worker scratch without the Macro repo; the parent owns the
    real-repo validator run in that case.
    """

    def setUp(self):
        if not HAS_AGENTOS:
            self.skipTest("scripts/agentos.py not present in this scratch")

    def _load_agentos(self):
        spec = importlib.util.spec_from_file_location("agentos_under_test",
                                                      AGENTOS_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _check(self, agentos, record_text, stem):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, stem + ".md")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(record_text)
            rec, body = agentos.parse_record(
                __import__("pathlib").Path(path))
            problems = agentos.check_decision(rec, __import__("pathlib").Path(path))
        return problems

    def test_generated_decision_passes_real_validator(self):
        agentos = self._load_agentos()
        dec, _, _ = new_preference_pair()
        problems = self._check(
            agentos, dec,
            "DEC-" + pkr.PREFERENCE_DECISION_KEY_PREFIX + "SPEC-EDITING")
        self.assertEqual(
            [p for p in problems if getattr(p, "hard", True)], [],
            "hard validator problems: %r" % (problems,))

    def test_edited_decision_passes_real_validator(self):
        agentos = self._load_agentos()
        old_dec, ws_after, _ = new_preference_pair()
        request = pref_request(
            ws_after, request_id="mmos-project-preference-set-" + hex_(40, "e"),
            expected=sha256_text(old_dec), value="改用英文，每周五发。")
        recipe = build_pref(request, actor=ACTOR_B, workstream_text=ws_after,
                            decision_text=old_dec, decision_date="2026-11-05")
        problems = self._check(
            agentos, recipe["postimages"][0]["content_utf8"],
            "DEC-" + pkr.PREFERENCE_DECISION_KEY_PREFIX + "SPEC-EDITING")
        self.assertEqual(
            [p for p in problems if getattr(p, "hard", True)], [],
            "hard validator problems: %r" % (problems,))




class TestParentCanonicalBoundaries(unittest.TestCase):
    def test_bounded_yaml_alias_traversal(self):
        lines=["bounded_0: &bound0 [x, x]"]
        for i in range(1, 20):
            lines.append(f"bounded_{i}: &bound{i} [*bound{i-1}, *bound{i-1}]")
        ws=WS_TEXT.replace("schema: agentos.workstream.v1\n", "schema: agentos.workstream.v1\n"+"\n".join(lines)+"\n")
        with self.assertRaises(pkr.KnowledgeRecipeError): build_file_add(file_request(ws),workstream_text=ws)

    def test_orphan_project_metadata_does_not_authorize_new_postimage(self):
        first=build_file_add(file_request(WS_TEXT))
        ws=first["postimages"][1]["content_utf8"]
        path=first["postimages"][0]["path"]
        ws=ws.replace("- "+path+"\n", "")
        request=file_request(ws,request_id="mmos-project-file-add-"+hex_(40,"c"))
        with self.assertRaises(pkr.KnowledgeRecipeError) as raised:
            build_file_add(request,workstream_text=ws)
        self.assertEqual(raised.exception.code,"INVALID_EXISTING_PROJECT_FILE")

    def test_actual_canonical_workstream_record_accepts_additive_file_recipe(self):
        from pathlib import Path
        canonical_path = Path(__file__).resolve().parents[1] / "agentos/workstreams/WS-EXECUTIVE-ECOSYSTEM-COMPLETION.md"
        actual = canonical_path.read_text(encoding="utf-8")
        request = file_request(actual, work_ref="WS:EXECUTIVE-ECOSYSTEM-COMPLETION")
        recipe = build_file_add(request, workstream_text=actual)
        before, before_body = pkr._load_record(actual, "INVALID_WORKSTREAM_RECORD")
        after, after_body = pkr._load_record(recipe["postimages"][1]["content_utf8"], "INVALID_WORKSTREAM_RECORD")
        self.assertNotIn("schema", before)
        self.assertEqual(before_body, after_body)
        for key, value in before.items():
            if key not in ("artifacts", "project_files"):
                self.assertEqual(value, after[key])
        self.assertEqual(after["artifacts"][:-1], before.get("artifacts", []))

    def test_actual_legacy_workstream_without_schema_is_preserved(self):
        legacy = WS_TEXT.replace("schema: agentos.workstream.v1\n", "")
        request = file_request(legacy)
        recipe = build_file_add(request, workstream_text=legacy)
        self.assertNotIn("schema: agentos.workstream.v1", recipe["postimages"][1]["content_utf8"])
        self.assertIn("project_files:", recipe["postimages"][1]["content_utf8"])

    def test_exact_request_id_and_digest_reject_trailing_lf(self):
        for key in ["request_id", "source_commit", "base_revision"]:
            request = file_request(WS_TEXT)
            request[key] += "\n"
            with self.assertRaises(pkr.KnowledgeRecipeError): build_file_add(request)

    def test_duplicate_artifact_pointer_is_a_conflict_without_overwrite(self):
        first = build_file_add(file_request(WS_TEXT))
        new_path = first["postimages"][0]["path"]
        data, body = yaml.safe_load(WS_TEXT.split("---", 2)[1]), WS_TEXT.split("---", 2)[2]
        data["artifacts"].append(new_path)
        ws = "---\n" + yaml.safe_dump(data, sort_keys=False, allow_unicode=True) + "---" + body
        with self.assertRaises(pkr.KnowledgeRecipeError) as raised:
            build_file_add(file_request(ws), workstream_text=ws)
        self.assertEqual(raised.exception.code, "CONFLICT")

    def test_project_files_null_is_not_absence(self):
        ws = WS_TEXT.replace("artifacts:", "project_files: null\nartifacts:")
        with self.assertRaises(pkr.KnowledgeRecipeError): build_file_add(file_request(ws), workstream_text=ws)


if __name__ == "__main__":
    unittest.main()
