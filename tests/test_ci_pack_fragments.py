"""Byte-exact split/join of .github/ci/legacy-jobs.yml at job boundaries."""

from __future__ import annotations

import hashlib
import inspect
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

from scripts.ci_pack_fragments import (
    PREAMBLE_KEY,
    TRAILER_KEY,
    Fragment,
    MergeResult,
    check_manifest,
    join,
    job_paths,
    main,
    merge3,
    owner_for_paths,
    split,
)
from scripts.run_ci_pack import load_legacy_jobs


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / ".github" / "ci" / "legacy-jobs.yml"


def _text() -> str:
    return MANIFEST.read_text(encoding="utf-8")


def _changed_keys(base: list[Fragment], edited: list[Fragment]) -> set[str]:
    before = {fragment.key: fragment.text for fragment in base}
    after = {fragment.key: fragment.text for fragment in edited}
    assert set(before) == set(after)
    return {key for key in before if before[key] != after[key]}


def test_real_manifest_round_trips_byte_for_byte() -> None:
    raw = MANIFEST.read_bytes()
    text = raw.decode("utf-8")
    assert join(split(text)).encode("utf-8") == raw


def test_split_is_deterministic() -> None:
    text = _text()
    first = split(text)
    second = split(text)
    assert first == second
    assert split(join(first)) == first


def test_job_count_matches_run_ci_pack_parse() -> None:
    fragments = [fragment for fragment in split(_text()) if fragment.kind == "job"]
    jobs = load_legacy_jobs(MANIFEST)
    assert len(fragments) == len(jobs)
    assert [fragment.key for fragment in fragments] == [job.job_id for job in jobs]


def test_job_paths_match_the_manifest_document() -> None:
    text = _text()
    document = yaml.safe_load(text)
    for fragment in split(text):
        if fragment.kind != "job":
            continue
        declared = document["jobs"][fragment.key].get("paths") or []
        assert job_paths(fragment.text) == list(declared)


def test_preamble_and_trailer_bookend_the_jobs() -> None:
    fragments = split(_text())
    assert fragments[0].key == PREAMBLE_KEY
    assert fragments[0].kind == "preamble"
    assert fragments[0].owner == "shared"
    assert fragments[-1].key == TRAILER_KEY
    assert fragments[-1].kind == "trailer"
    assert fragments[-1].owner == "shared"
    assert all(fragment.kind == "job" for fragment in fragments[1:-1])
    assert fragments[0].text.startswith("# Legacy CI job manifest")
    assert "\njobs:\n" in fragments[0].text


def test_owner_is_the_single_vertical_directory_or_shared() -> None:
    assert (
        owner_for_paths(
            ["engine/alpha_vertical/**", "tests/test_frag_owner_alpha.py"]
        )
        == "alpha_vertical"
    )
    assert (
        owner_for_paths(["engine/alpha_vertical/**", "engine/beta_vertical/**"])
        == "shared"
    )
    assert owner_for_paths(["tests/test_frag_owner_alpha.py"]) == "shared"
    assert owner_for_paths([]) == "shared"
    assert (
        owner_for_paths(
            ["engine/alpha_vertical/**", "lib/frag_owner_not_a_module.py"]
        )
        == "shared"
    )


def test_two_vertical_prs_do_not_touch_the_same_fragment() -> None:
    """Two edits of different owners change disjoint fragments.

    The synthetic manifest has one job confined to ``alpha_vertical``, one
    confined to ``beta_vertical``, and one unscoped job that stays ``shared``.
    Each PR replaces only its own job's run scalar.
    """
    original = (
        "# synthetic legacy manifest\n"
        "jobs:\n"
        "  alpha-desk:\n"
        "    paths:\n"
        '      - "engine/alpha_vertical/**"\n'
        '      - "tests/test_frag_owner_alpha.py"\n'
        "    steps:\n"
        "      - name: alpha\n"
        "        run: echo alpha-marker\n"
        "\n"
        "  # beta owns the next block\n"
        "  beta-desk:\n"
        "    paths:\n"
        '      - "engine/beta_vertical/**"\n'
        "    steps:\n"
        "      - name: beta\n"
        "        run: echo beta-marker\n"
        "\n"
        "  platform-fence:\n"
        "    steps:\n"
        "      - name: shared\n"
        "        run: echo shared-marker\n"
        "# trailer note\n"
    )
    alpha_edit = original.replace("echo alpha-marker", "echo alpha-marker-v2", 1)
    beta_edit = original.replace("echo beta-marker", "echo beta-marker-v2", 1)
    assert join(split(original)) == original
    assert join(split(alpha_edit)) == alpha_edit
    assert join(split(beta_edit)) == beta_edit

    base = split(original)
    owners = {fragment.key: fragment.owner for fragment in base}
    assert owners["alpha-desk"] == "alpha_vertical"
    assert owners["beta-desk"] == "beta_vertical"
    assert owners["platform-fence"] == "shared"
    assert owners["alpha-desk"] != owners["beta-desk"]

    changed_alpha = _changed_keys(base, split(alpha_edit))
    changed_beta = _changed_keys(base, split(beta_edit))
    assert changed_alpha == {"alpha-desk"}
    assert changed_beta == {"beta-desk"}
    assert changed_alpha.isdisjoint(changed_beta)


def test_control_plane_job_names_this_suite() -> None:
    fragments = {fragment.key: fragment for fragment in split(_text())}
    job = fragments["ci-control-plane-contracts"]
    run_lines = [
        line.split("run:", 1)[1]
        for line in job.text.splitlines()
        if line.strip().startswith("run:")
    ]
    assert any("tests/test_ci_pack_fragments.py" in line for line in run_lines)


def test_check_cli_reports_a_byte_identical_manifest() -> None:
    assert main(["--check"]) == 0
    report = check_manifest(MANIFEST)
    assert report.startswith("jobs=")
    assert " fragments=" in report
    assert " owners={" in report
    jobs = int(report.split(" ", 1)[0].split("=", 1)[1])
    fragments = split(_text())
    assert jobs == sum(1 for fragment in fragments if fragment.kind == "job")
    assert f"fragments={len(fragments)}" in report


def _job(job_id: str, run: str) -> str:
    return (
        f"  {job_id}:\n"
        "    if: ${{ false }}\n"
        "    runs-on: ubuntu-latest\n"
        "    steps:\n"
        f"      - name: {job_id}\n"
        f"        run: {run}\n"
    )


def _doc(
    jobs: list[tuple[str, str]],
    *,
    preamble: str = "# synthetic legacy manifest\njobs:\n",
    trailer: str = "",
) -> str:
    parts = [preamble]
    for index, (job_id, run) in enumerate(jobs):
        if index:
            parts.append("\n")
        parts.append(_job(job_id, run))
    parts.append(trailer)
    return "".join(parts)


def _insert_after(text: str, anchor: str, job_id: str, run: str) -> str:
    """Insert one real-shaped job immediately after ``anchor``'s fragment."""
    addition = "\n" + _job(job_id, run)
    pieces: list[str] = []
    found = False
    for fragment in split(text):
        pieces.append(fragment.text)
        if fragment.key == anchor:
            pieces.append(addition)
            found = True
    assert found, anchor
    return "".join(pieces)


def _append(text: str, job_id: str, run: str) -> str:
    frags = split(text)
    anchor = next(
        (fragment.key for fragment in reversed(frags) if fragment.kind == "job"),
        PREAMBLE_KEY,
    )
    return _insert_after(text, anchor, job_id, run)


def _drop(text: str, key: str) -> str:
    return "".join(fragment.text for fragment in split(text) if fragment.key != key)


def _fragment(text: str, key: str) -> str:
    return next(fragment.text for fragment in split(text) if fragment.key == key)


def _single_runs_on_job(text: str) -> tuple[str, str, str]:
    """First job fragment with exactly one ``    runs-on:`` line.

    Selection by property rather than a live-manifest index: the merged-edit
    case used to pin ``manifest_keys[2]`` plus a literal
    ``runs-on: ubuntu-latest`` line, so a reordering or runner migration on
    main would break it. Returns ``(key, fragment text, the runs-on line)``.
    """
    for fragment in split(text):
        if fragment.kind != "job":
            continue
        lines = [
            line
            for line in fragment.text.splitlines(keepends=True)
            if line.startswith("    runs-on:")
        ]
        if len(lines) == 1:
            return fragment.key, fragment.text, lines[0]
    raise AssertionError("no job fragment has exactly one runs-on line")


def _conflict_block(ours_text: str, theirs_text: str) -> str:
    """The marker bytes ``merge3`` must emit around one fragment."""

    def _body(text: str) -> str:
        if text == "" or text.endswith("\n"):
            return text
        return text + "\n"

    opener = "<" * 7
    closer = ">" * 7
    return (
        f"{opener} ours\n{_body(ours_text)}{'=' * 7}\n"
        f"{_body(theirs_text)}{closer} theirs\n"
    )


def _job_keys(text: str) -> list[str]:
    return [fragment.key for fragment in split(text) if fragment.kind == "job"]


def _assert_loadable(result: MergeResult) -> None:
    """Clean merge text round-trips and is a manifest the pack loader accepts."""
    assert result.conflicts == ()
    assert join(split(result.text)) == result.text
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "legacy-jobs.yml"
        path.write_text(result.text, encoding="utf-8")
        loaded = load_legacy_jobs(path)
    assert [job.job_id for job in loaded] == _job_keys(result.text)


def test_merge3_keeps_a_job_added_on_only_one_side() -> None:
    base = _doc([("alpha", "echo alpha"), ("beta", "echo beta")])
    ours = _append(base, "ours-job", "echo ours")
    theirs = _insert_after(base, "alpha", "theirs-job", "echo theirs")
    leading = _insert_after(base, PREAMBLE_KEY, "lead-job", "echo lead")

    added_by_ours = merge3(base, ours, base)
    added_by_theirs = merge3(base, base, theirs)
    added_at_front = merge3(base, base, leading)

    assert added_by_ours.conflicts == ()
    assert added_by_ours.text == ours
    assert added_by_theirs.text == theirs
    assert added_at_front.text == leading
    assert _job_keys(added_by_ours.text) == ["alpha", "beta", "ours-job"]
    assert _job_keys(added_by_theirs.text) == ["alpha", "theirs-job", "beta"]
    assert _job_keys(added_at_front.text) == ["lead-job", "alpha", "beta"]
    _assert_loadable(added_by_ours)
    _assert_loadable(added_by_theirs)
    _assert_loadable(added_at_front)


def test_merge3_keeps_jobs_added_on_both_sides_ours_then_theirs() -> None:
    """Shared anchors take ours' new jobs first, then theirs', each in side order.

    A key both sides add with the same text is kept once. Differing text for
    that same key is a conflict, not a second YAML key.
    """
    base = _doc([("alpha", "echo alpha"), ("beta", "echo beta")])
    ours = _append(_append(base, "ours-a", "echo ours-a"), "ours-b", "echo ours-b")
    theirs = _append(
        _insert_after(base, "alpha", "theirs-mid", "echo theirs-mid"),
        "theirs-end",
        "echo theirs-end",
    )
    result = merge3(base, ours, theirs)
    assert result == merge3(base, ours, theirs)
    assert result.conflicts == ()
    assert _job_keys(result.text) == [
        "alpha",
        "theirs-mid",
        "beta",
        "ours-a",
        "ours-b",
        "theirs-end",
    ]
    _assert_loadable(result)

    extra = _append(base, "extra", "echo extra")
    identical = merge3(base, extra, extra)
    assert identical.conflicts == ()
    assert identical.text == extra
    assert _job_keys(identical.text).count("extra") == 1
    _assert_loadable(identical)

    differing = merge3(
        base,
        _append(base, "extra", "echo from-ours"),
        _append(base, "extra", "echo from-theirs"),
    )
    assert differing.conflicts == ("extra",)
    assert differing.text.count("<" * 7 + " ours") == 1
    assert join(split(differing.text)) == differing.text
    assert _conflict_block(
        _fragment(_append(base, "extra", "echo from-ours"), "extra"),
        _fragment(_append(base, "extra", "echo from-theirs"), "extra"),
    ) in differing.text


def test_merge3_takes_a_job_edited_on_one_side_only() -> None:
    base = _doc([("alpha", "echo alpha"), ("beta", "echo beta")])
    edited = base.replace("run: echo alpha\n", "run: echo alpha-v2\n", 1)
    from_ours = merge3(base, edited, base)
    from_theirs = merge3(base, base, edited)
    assert from_ours.conflicts == ()
    assert from_theirs.conflicts == ()
    assert from_ours.text == edited
    assert from_theirs.text == edited
    assert _fragment(from_ours.text, "beta") == _fragment(base, "beta")
    _assert_loadable(from_ours)
    _assert_loadable(from_theirs)


def test_merge3_takes_an_identical_edit_once() -> None:
    base = _doc([("alpha", "echo alpha"), ("beta", "echo beta")])
    edited = base.replace("run: echo beta\n", "run: echo beta-v2\n", 1)
    result = merge3(base, edited, edited)
    assert result.conflicts == ()
    assert result.text == edited
    assert _job_keys(result.text) == ["alpha", "beta"]
    _assert_loadable(result)


def test_merge3_conflicts_when_a_job_is_edited_differently() -> None:
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    ours = base.replace("run: echo alpha\n", "run: echo alpha-ours\n", 1)
    ours = ours.replace("run: echo gamma\n", "run: echo gamma-ours\n", 1)
    theirs = base.replace("run: echo alpha\n", "run: echo alpha-theirs\n", 1)
    theirs = theirs.replace("run: echo gamma\n", "run: echo gamma-theirs\n", 1)
    result = merge3(base, ours, theirs)
    assert result.conflicts == ("alpha", "gamma")
    assert join(split(result.text)) == result.text
    assert result.text == (
        _fragment(base, PREAMBLE_KEY)
        + _conflict_block(_fragment(ours, "alpha"), _fragment(theirs, "alpha"))
        + _fragment(base, "beta")
        + _conflict_block(_fragment(ours, "gamma"), _fragment(theirs, "gamma"))
        + _fragment(base, TRAILER_KEY)
    )
    assert "echo beta\n" in result.text
    assert result.text.count("<" * 7 + " ours") == 2


def test_merge3_deletes_a_job_removed_on_one_unchanged_side() -> None:
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    without_beta = _drop(base, "beta")
    from_ours = merge3(base, without_beta, base)
    from_theirs = merge3(base, base, without_beta)
    both = merge3(base, without_beta, without_beta)
    assert from_ours.conflicts == ()
    assert from_theirs.conflicts == ()
    assert both.conflicts == ()
    assert from_ours.text == without_beta
    assert from_theirs.text == without_beta
    assert both.text == without_beta
    assert "beta" not in _job_keys(from_ours.text)
    _assert_loadable(from_ours)
    _assert_loadable(both)


def test_merge3_conflicts_on_delete_versus_edit() -> None:
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    deleted = _drop(base, "beta")
    edited = base.replace("run: echo beta\n", "run: echo beta-v2\n", 1)
    ours_deleted = merge3(base, deleted, edited)
    theirs_deleted = merge3(base, edited, deleted)
    assert ours_deleted.conflicts == ("beta",)
    assert theirs_deleted.conflicts == ("beta",)
    assert join(split(ours_deleted.text)) == ours_deleted.text
    assert join(split(theirs_deleted.text)) == theirs_deleted.text
    assert ours_deleted.text == (
        _fragment(base, PREAMBLE_KEY)
        + _fragment(base, "alpha")
        + _conflict_block("", _fragment(edited, "beta"))
        + _fragment(base, "gamma")
        + _fragment(base, TRAILER_KEY)
    )
    assert theirs_deleted.text == (
        _fragment(base, PREAMBLE_KEY)
        + _fragment(base, "alpha")
        + _conflict_block(_fragment(edited, "beta"), "")
        + _fragment(base, "gamma")
        + _fragment(base, TRAILER_KEY)
    )
    assert "echo beta-v2\n" in ours_deleted.text


def test_merge3_preamble_and_trailer_follow_the_job_rules() -> None:
    base = _doc([("alpha", "echo alpha")], trailer="# trailer\n")
    preamble_edit = base.replace(
        "# synthetic legacy manifest\n", "# ours header\n", 1
    )
    assert merge3(base, preamble_edit, base).text == preamble_edit
    assert merge3(base, base, preamble_edit).text == preamble_edit
    assert merge3(base, preamble_edit, preamble_edit).text == preamble_edit
    _assert_loadable(merge3(base, preamble_edit, preamble_edit))

    other_header = base.replace(
        "# synthetic legacy manifest\n", "# theirs header\n", 1
    )
    conflicted = merge3(base, preamble_edit, other_header)
    assert conflicted.conflicts == (PREAMBLE_KEY,)
    assert join(split(conflicted.text)) == conflicted.text
    assert conflicted.text == _conflict_block(
        _fragment(preamble_edit, PREAMBLE_KEY),
        _fragment(other_header, PREAMBLE_KEY),
    ) + "".join(
        fragment.text
        for fragment in split(base)
        if fragment.kind != "preamble"
    )

    removed = base.replace("# trailer\n", "", 1)
    assert merge3(base, removed, base).text == removed
    assert merge3(base, base, removed).text == removed
    assert _fragment(merge3(base, removed, base).text, TRAILER_KEY) == ""
    _assert_loadable(merge3(base, removed, base))

    trailer_edit = base.replace("# trailer\n", "# trailer v2\n", 1)
    delete_vs_edit = merge3(base, removed, trailer_edit)
    assert delete_vs_edit.conflicts == (TRAILER_KEY,)
    assert join(split(delete_vs_edit.text)) == delete_vs_edit.text
    assert delete_vs_edit.text.endswith(
        _conflict_block("", _fragment(trailer_edit, TRAILER_KEY))
    )


def test_module_docstring_documents_the_opt_in_merge_driver() -> None:
    import scripts.ci_pack_fragments as module

    doc = module.__doc__ or ""
    assert ".github/ci/legacy-jobs.yml merge=cipack" in doc
    assert (
        'git config merge.cipack.driver '
        '"python3 scripts/ci_pack_fragments.py merge3 %O %A %B"'
    ) in doc


def test_edit_side_permuted_is_a_required_keyword_only_flag() -> None:
    """The moved-separator guard flag cannot be omitted: it is required.

    ``_apply_order_and_edits`` runs the ``_moved_separators_agree`` guard
    exactly when ``edit_side_permuted`` is True, so the flag decides whether a
    permutation that moved a separator is checked on the edit side. The
    behaviour lives in the signature: keyword-only with no default, so a caller
    that omits it raises ``TypeError`` at the call site. This pins that shape,
    because re-adding ``= False`` keeps every behavioural test here green while
    restoring the silent no-guard merge for a permuted-edit-side caller.
    """
    import scripts.ci_pack_fragments as module

    param = inspect.signature(module._apply_order_and_edits).parameters[
        "edit_side_permuted"
    ]
    assert param.kind is inspect.Parameter.KEYWORD_ONLY, (
        "edit_side_permuted must stay keyword-only: a positional caller could "
        "pass the flag by accident, or a refactor could drop it from the call "
        "entirely, and the moved-separator guard would silently stop running"
    )
    assert param.default is inspect.Parameter.empty, (
        "HAZARD: re-adding a default (edit_side_permuted: bool = False) lets a "
        "permuted-edit-side caller omit the flag and merge without the "
        "moved-separator guard; it must stay required so omission raises "
        "TypeError at the call site instead of silently merging"
    )


def test_merge3_cli_writes_ours_and_exits_like_a_merge_driver(tmp_path: Path) -> None:
    base = _doc([("alpha", "echo alpha")])
    ours = _append(base, "ours-job", "echo ours")
    theirs = _append(base, "theirs-job", "echo theirs")
    base_path = tmp_path / "base.yml"
    ours_path = tmp_path / "ours.yml"
    theirs_path = tmp_path / "theirs.yml"
    base_path.write_text(base, encoding="utf-8")
    ours_path.write_text(ours, encoding="utf-8")
    theirs_path.write_text(theirs, encoding="utf-8")

    assert main(["merge3", str(base_path), str(ours_path), str(theirs_path)]) == 0
    assert base_path.read_text(encoding="utf-8") == base
    assert theirs_path.read_text(encoding="utf-8") == theirs
    written = ours_path.read_text(encoding="utf-8")
    assert written == merge3(base, ours, theirs).text
    _assert_loadable(merge3(base, ours, theirs))

    conflict_ours = base.replace("run: echo alpha\n", "run: echo ours\n", 1)
    conflict_theirs = base.replace("run: echo alpha\n", "run: echo theirs\n", 1)
    ours_path.write_text(conflict_ours, encoding="utf-8")
    theirs_path.write_text(conflict_theirs, encoding="utf-8")
    assert main(["merge3", str(base_path), str(ours_path), str(theirs_path)]) == 1
    conflicted = ours_path.read_text(encoding="utf-8")
    assert conflicted == merge3(base, conflict_ours, conflict_theirs).text
    assert ("<" * 7 + " ours") in conflicted
    assert join(split(conflicted)) == conflicted


def test_merge3_cli_help_escapes_the_percent_placeholders(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``merge3 --help`` renders the git ``%O %A %B`` placeholders verbatim.

    argparse %-formats positional help strings at display time, so an
    unescaped ``%O`` raises ``ValueError: unsupported format character 'O'``
    inside ``--help``. The escape added by acb75c49 had no test. The
    ``pytest.raises(SystemExit)`` wrapper doubles as the "no ValueError
    escapes" bar: a ``ValueError`` propagating out of ``main`` fails this
    test instead of exiting. Pinned RED on the pre-fix blob
    ``d581f0cc8fe2741b8fec9760a2562ecd0231cacf:scripts/ci_pack_fragments.py``
    imported from a copy under the lane tmp directory; GREEN at HEAD.
    """
    with pytest.raises(SystemExit):
        main(["merge3", "--help"])
    captured = capsys.readouterr()
    assert "ancestor file (%O)" in captured.out
    assert "current file (%A), overwritten" in captured.out
    assert "other file (%B)" in captured.out
    assert "%%" not in captured.out


def _commit_resolves(rev: str) -> bool:
    """True when ``git cat-file -e <rev>^{commit}`` exits 0 in this checkout."""
    proc = subprocess.run(
        ["git", "cat-file", "-e", f"{rev}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
    )
    return proc.returncode == 0


def test_merge3_replay_of_appended_jobs_is_clean_where_merge_file_conflicts(
    tmp_path: Path,
) -> None:
    """Two-sided end append, reconstructed without repository history.

    This is the d6d1342b53 shape as fixture text: a short base manifest, ours
    appends ``market-ontology-f09-usgs-mcs``, and theirs appends
    ``recurring-briefs`` after the same last job. ``merge3`` is clean and
    emits ours' job then theirs'. ``git merge-file`` still conflicts. The
    recorded replay is ``test_merge3_d6d1342b53_replay_when_commits_resolve``.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    ours = _append(base, "market-ontology-f09-usgs-mcs", "echo usgs-mcs")
    theirs = _append(base, "recurring-briefs", "echo recurring-briefs")
    result = merge3(base, ours, theirs)

    assert result.conflicts == ()
    assert ("<" * 7) not in result.text
    keys = _job_keys(result.text)
    assert keys == [
        "alpha",
        "beta",
        "gamma",
        "market-ontology-f09-usgs-mcs",
        "recurring-briefs",
    ]
    assert keys.index("market-ontology-f09-usgs-mcs") + 1 == keys.index(
        "recurring-briefs"
    )
    _assert_loadable(result)

    base_path = tmp_path / "base.yml"
    ours_path = tmp_path / "ours.yml"
    theirs_path = tmp_path / "theirs.yml"
    base_path.write_text(base, encoding="utf-8")
    ours_path.write_text(ours, encoding="utf-8")
    theirs_path.write_text(theirs, encoding="utf-8")
    proc = subprocess.run(
        [
            "git",
            "merge-file",
            "-p",
            "-q",
            str(ours_path),
            str(base_path),
            str(theirs_path),
        ],
        cwd=tmp_path,
        capture_output=True,
    )
    assert 0 < proc.returncode < 128
    assert ("<" * 7).encode() in proc.stdout
    assert ours_path.read_text(encoding="utf-8") == ours
    assert base_path.read_text(encoding="utf-8") == base
    assert theirs_path.read_text(encoding="utf-8") == theirs


def test_merge3_mid_file_insert_and_end_appends_where_merge_file_conflicts(
    tmp_path: Path,
) -> None:
    """Mid-file insert beside the shared end-append fixture.

    Ours inserts ``research-vault-source-lineage`` after the middle anchor
    ``beta`` and appends ``market-ontology-f09-usgs-mcs``. Theirs appends
    ``recurring-briefs`` at that same end. ``merge3`` keeps the insert after
    its anchor and the two end jobs ours-then-theirs. ``git merge-file`` in
    ``tmp_path`` still conflicts. The inputs are fixture text, so this case
    does not read a commit or repository history.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    ours = _append(
        _insert_after(
            base, "beta", "research-vault-source-lineage", "echo lineage"
        ),
        "market-ontology-f09-usgs-mcs",
        "echo usgs-mcs",
    )
    theirs = _append(base, "recurring-briefs", "echo recurring-briefs")
    assert _job_keys(ours) == [
        "alpha",
        "beta",
        "research-vault-source-lineage",
        "gamma",
        "market-ontology-f09-usgs-mcs",
    ]
    assert _job_keys(theirs) == [
        "alpha",
        "beta",
        "gamma",
        "recurring-briefs",
    ]
    result = merge3(base, ours, theirs)

    assert result.conflicts == ()
    assert ("<" * 7) not in result.text
    keys = _job_keys(result.text)
    assert keys == [
        "alpha",
        "beta",
        "research-vault-source-lineage",
        "gamma",
        "market-ontology-f09-usgs-mcs",
        "recurring-briefs",
    ]
    assert keys.index("beta") + 1 == keys.index("research-vault-source-lineage")
    assert keys.index("market-ontology-f09-usgs-mcs") + 1 == keys.index(
        "recurring-briefs"
    )
    _assert_loadable(result)

    base_path = tmp_path / "base.yml"
    ours_path = tmp_path / "ours.yml"
    theirs_path = tmp_path / "theirs.yml"
    base_path.write_text(base, encoding="utf-8")
    ours_path.write_text(ours, encoding="utf-8")
    theirs_path.write_text(theirs, encoding="utf-8")
    proc = subprocess.run(
        [
            "git",
            "merge-file",
            "-p",
            "-q",
            str(ours_path),
            str(base_path),
            str(theirs_path),
        ],
        cwd=tmp_path,
        capture_output=True,
    )
    assert 0 < proc.returncode < 128
    assert ("<" * 7).encode() in proc.stdout
    assert ours_path.read_text(encoding="utf-8") == ours
    assert base_path.read_text(encoding="utf-8") == base
    assert theirs_path.read_text(encoding="utf-8") == theirs


def test_merge3_stock_dashboard_first_frame_mid_file_insert_is_hermetic(
    tmp_path: Path,
) -> None:
    """The d6d1342b53 mid-file job as fixture text, with no repository history.

    ``test_merge3_d6d1342b53_replay_when_commits_resolve`` needs ``git
    cat-file`` history and skips in a depth-1 clone. This fixture rebuilds
    that replay's mid-file job shape: theirs inserts
    ``stock-dashboard-first-frame`` after the middle anchor ``beta`` and
    appends ``recurring-briefs``, while ours appends
    ``market-ontology-f09-usgs-mcs``. ``merge3`` keeps the insert after its
    anchor and orders the two end jobs ours-then-theirs, the same shape the
    full-history replay pins; the replay's digest
    ``e9dfd7ca0d26c702ca5daaacb0710b1bf7bae2b8a1e2b8ce0a6b5ebf48f128aa``
    is untouched. ``git merge-file`` still conflicts. The inputs are
    fixture text: no commit reads, no merge-base, no ``git cat-file``.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    ours = _append(base, "market-ontology-f09-usgs-mcs", "echo usgs-mcs")
    theirs = _append(
        _insert_after(
            base, "beta", "stock-dashboard-first-frame", "echo first-frame"
        ),
        "recurring-briefs",
        "echo recurring-briefs",
    )
    assert _job_keys(ours) == [
        "alpha",
        "beta",
        "gamma",
        "market-ontology-f09-usgs-mcs",
    ]
    assert _job_keys(theirs) == [
        "alpha",
        "beta",
        "stock-dashboard-first-frame",
        "gamma",
        "recurring-briefs",
    ]
    result = merge3(base, ours, theirs)

    assert result.conflicts == ()
    assert ("<" * 7) not in result.text
    keys = _job_keys(result.text)
    assert keys == [
        "alpha",
        "beta",
        "stock-dashboard-first-frame",
        "gamma",
        "market-ontology-f09-usgs-mcs",
        "recurring-briefs",
    ]
    assert keys.index("beta") + 1 == keys.index("stock-dashboard-first-frame")
    assert keys.index("market-ontology-f09-usgs-mcs") + 1 == keys.index(
        "recurring-briefs"
    )
    _assert_loadable(result)

    base_path = tmp_path / "base.yml"
    ours_path = tmp_path / "ours.yml"
    theirs_path = tmp_path / "theirs.yml"
    base_path.write_text(base, encoding="utf-8")
    ours_path.write_text(ours, encoding="utf-8")
    theirs_path.write_text(theirs, encoding="utf-8")
    proc = subprocess.run(
        [
            "git",
            "merge-file",
            "-p",
            "-q",
            str(ours_path),
            str(base_path),
            str(theirs_path),
        ],
        cwd=tmp_path,
        capture_output=True,
    )
    assert 0 < proc.returncode < 128
    assert ("<" * 7).encode() in proc.stdout
    assert ours_path.read_text(encoding="utf-8") == ours
    assert base_path.read_text(encoding="utf-8") == base
    assert theirs_path.read_text(encoding="utf-8") == theirs


def test_merge3_d6d1342b53_replay_when_commits_resolve(tmp_path: Path) -> None:
    """Replay d6d1342b53 when both parent commits are in this checkout.

    Parent 203e0f19 added ``market-ontology-f09-usgs-mcs``. Parent e692d9dc
    added ``recurring-briefs`` at the same end plus two mid-file jobs. The
    recorded resolution kept every added job. A shallow checkout does not
    contain those commits; this replay skips instead of calling merge-base.
    """
    ours_rev = "203e0f1992bf20b885cd3333d9a074be4cd172b0"
    theirs_rev = "e692d9dc4bdc812c0b51e45fc95764c1874ff0b2"
    merged_rev = "d6d1342b535beb784b149c123c7055fdbde206cb"
    missing = [
        rev
        for rev in (ours_rev, theirs_rev, merged_rev)
        if not _commit_resolves(rev)
    ]
    if missing:
        pytest.skip(
            "shallow checkout does not contain "
            + ", ".join(missing)
            + " (git cat-file -e <sha>^{commit} rc != 0)"
        )

    def blob(rev: str) -> str:
        return subprocess.check_output(
            ["git", "show", f"{rev}:.github/ci/legacy-jobs.yml"],
            cwd=ROOT,
        ).decode("utf-8")

    base_rev = (
        subprocess.check_output(
            ["git", "merge-base", ours_rev, theirs_rev],
            cwd=ROOT,
        )
        .decode("utf-8")
        .strip()
    )
    base = blob(base_rev)
    ours = blob(ours_rev)
    theirs = blob(theirs_rev)
    result = merge3(base, ours, theirs)

    assert result.conflicts == ()
    assert ("<" * 7) not in result.text
    keys = _job_keys(result.text)
    assert keys.index("market-ontology-f09-usgs-mcs") + 1 == keys.index(
        "recurring-briefs"
    )
    for added in (
        "market-ontology-f09-usgs-mcs",
        "recurring-briefs",
        "research-vault-source-lineage",
        "stock-dashboard-first-frame",
    ):
        assert added in keys
    assert result.text == blob(merged_rev)
    digest = hashlib.sha256(result.text.encode("utf-8")).hexdigest()
    assert digest == (
        "e9dfd7ca0d26c702ca5daaacb0710b1bf7bae2b8a1e2b8ce0a6b5ebf48f128aa"
    )
    assert join(split(result.text)) == result.text

    base_path = tmp_path / "base.yml"
    ours_path = tmp_path / "ours.yml"
    theirs_path = tmp_path / "theirs.yml"
    base_path.write_text(base, encoding="utf-8")
    ours_path.write_text(ours, encoding="utf-8")
    theirs_path.write_text(theirs, encoding="utf-8")
    proc = subprocess.run(
        [
            "git",
            "merge-file",
            "-p",
            "-q",
            str(ours_path),
            str(base_path),
            str(theirs_path),
        ],
        cwd=ROOT,
        capture_output=True,
    )
    assert 0 < proc.returncode < 128
    assert ("<" * 7).encode() in proc.stdout
    assert ours_path.read_text(encoding="utf-8") == ours

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "legacy-jobs.yml"
        path.write_text(result.text, encoding="utf-8")
        loaded = load_legacy_jobs(path)
    assert [job.job_id for job in loaded] == keys


def _lead_and_body(fragment: Fragment) -> tuple[str, str]:
    """Split a fragment into the leading separator and the bytes at its key."""
    lines = fragment.text.split("\n")
    marker = f"  {fragment.key}:"
    for index, line in enumerate(lines):
        if line.rstrip("\r") == marker:
            if index == 0:
                return "", "\n".join(lines)
            return "\n".join(lines[:index]) + "\n", "\n".join(lines[index:])
    raise AssertionError(fragment.key)


def _positional_swap(text: str, key_a: str, key_b: str) -> str:
    """Swap two jobs' bodies and leave each position's leading separator."""
    parts = split(text)
    by_key = {fragment.key: fragment for fragment in parts}
    lead_a, body_a = _lead_and_body(by_key[key_a])
    lead_b, body_b = _lead_and_body(by_key[key_b])
    assert lead_a + body_a == by_key[key_a].text
    assert lead_b + body_b == by_key[key_b].text
    replaced = {key_a: lead_a + body_b, key_b: lead_b + body_a}
    return "".join(replaced.get(fragment.key, fragment.text) for fragment in parts)


def _swap_fragments(text: str, key_a: str, key_b: str) -> str:
    """Exchange two whole fragments, separator included."""
    parts = split(text)
    index = {fragment.key: position for position, fragment in enumerate(parts)}
    left, right = index[key_a], index[key_b]
    parts[left], parts[right] = parts[right], parts[left]
    return join(parts)


def test_merge3_real_manifest_with_itself_is_byte_identical() -> None:
    text = _text()
    result = merge3(text, text, text)
    assert result.conflicts == ()
    assert result.text == text
    assert join(split(result.text)) == text


def test_merge3_one_sided_order_only_change_returns_that_sides_bytes() -> None:
    """A pure incumbent reorder is kept by returning that side's original bytes.

    The other side's fragment texts equal the base. Both directions are
    order-only. A whole-fragment swap is the same kind of change: the per-key
    bodies match and only the key order differs.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    reordered = _doc(
        [
            ("beta", "echo beta"),
            ("alpha", "echo alpha"),
            ("gamma", "echo gamma"),
        ]
    )
    assert reordered != base
    assert _job_keys(reordered) == ["beta", "alpha", "gamma"]

    from_ours = merge3(base, reordered, base)
    from_theirs = merge3(base, base, reordered)
    assert from_ours.conflicts == ()
    assert from_theirs.conflicts == ()
    assert from_ours.text == reordered
    assert from_theirs.text == reordered
    assert from_ours.text != base

    swapped = _swap_fragments(base, "alpha", "beta")
    assert _job_keys(swapped)[:2] == ["beta", "alpha"]
    assert merge3(base, swapped, base).text == swapped
    assert merge3(base, swapped, base).conflicts == ()
    _assert_loadable(merge3(base, reordered, base))


def test_merge3_identical_order_only_permutation_is_taken_once() -> None:
    """The same order-only permutation on both sides is taken once.

    ``merge3(base, swapped, swapped)`` is that permutation and has no
    conflict. Two different permutations stay a single ``__order__`` conflict.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    swapped = _doc(
        [
            ("beta", "echo beta"),
            ("alpha", "echo alpha"),
            ("gamma", "echo gamma"),
        ]
    )
    other = _doc(
        [
            ("gamma", "echo gamma"),
            ("beta", "echo beta"),
            ("alpha", "echo alpha"),
        ]
    )
    assert swapped != base
    assert _job_keys(swapped) == ["beta", "alpha", "gamma"]

    same = merge3(base, swapped, swapped)
    assert same.conflicts == ()
    assert same.text == swapped

    positional = _positional_swap(base, "alpha", "beta")
    assert positional != base
    assert merge3(base, positional, positional).conflicts == ()
    assert merge3(base, positional, positional).text == positional

    different = merge3(base, swapped, other)
    assert different.conflicts == ("__order__",)
    assert different.text == _conflict_block(swapped, other)


def test_merge3_same_key_order_different_glue_is_order_conflict() -> None:
    """Same job-key order is taken only when the two texts are equal.

    A positional swap and a whole-fragment swap of the same pair are both
    order-only and share a key order. The separator stays in the slot or
    moves with the job, so the texts differ and the merge stays ``__order__``.
    ``merge3(base, swapped, swapped).text == swapped`` still holds.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    positional = _positional_swap(base, "alpha", "beta")
    whole = _swap_fragments(base, "alpha", "beta")
    assert _job_keys(positional) == _job_keys(whole) == ["beta", "alpha", "gamma"]
    assert positional != whole

    from_ours = merge3(base, positional, whole)
    from_theirs = merge3(base, whole, positional)
    assert from_ours.conflicts == ("__order__",)
    assert from_theirs.conflicts == ("__order__",)
    assert from_ours.text == _conflict_block(positional, whole)
    assert from_theirs.text == _conflict_block(whole, positional)

    swapped = positional
    same = merge3(base, swapped, swapped)
    assert same.conflicts == ()
    assert same.text == swapped


def test_merge3_agreed_order_with_one_sided_body_edit_is_clean() -> None:
    """Agreed permutation, one order-only side, one body edit: clean merge.

    Base is alpha, beta, gamma, delta. Ours swaps beta and alpha positionally
    and edits nothing else (order-only). Theirs carries the same key order
    built the same way plus gamma's run changed to ``echo gamma-v2``. The
    order is agreed and only one side edited a body, so the merge is theirs'
    bytes with no conflict.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
            ("delta", "echo delta"),
        ]
    )
    ours = _positional_swap(base, "alpha", "beta")
    theirs = ours.replace("run: echo gamma\n", "run: echo gamma-v2\n", 1)
    assert _job_keys(base) == ["alpha", "beta", "gamma", "delta"]
    assert _job_keys(ours) == _job_keys(theirs)
    assert _job_keys(theirs) == ["beta", "alpha", "gamma", "delta"]

    result = merge3(base, ours, theirs)
    assert result.conflicts == ()
    assert _job_keys(result.text) == ["beta", "alpha", "gamma", "delta"]
    assert result.text.count("echo gamma-v2") == 1
    assert result.text == theirs
    _assert_loadable(result)


def test_merge3_agreed_order_mirrored_is_clean() -> None:
    """The mirror of the test above: the edit side is ours, the order side theirs.

    The same base, permutation, and gamma edit, with the two roles swapped,
    merge to the same keys and the same single ``gamma-v2`` with no conflict.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
            ("delta", "echo delta"),
        ]
    )
    order = _positional_swap(base, "alpha", "beta")
    edited = order.replace("run: echo gamma\n", "run: echo gamma-v2\n", 1)

    result = merge3(base, edited, order)
    assert result.conflicts == ()
    assert _job_keys(result.text) == ["beta", "alpha", "gamma", "delta"]
    assert result.text.count("echo gamma-v2") == 1
    assert result.text == edited
    _assert_loadable(result)


def test_merge3_agreed_keys_different_glue_stays_order_conflict() -> None:
    """Negative control: same key order, mixed glue, plus an edit.

    Ours is the positional swap (order-only); theirs is the whole-fragment
    swap of the same pair plus the gamma body edit. The two sides chose
    different separator glue for the same permutation, and the edit side's
    base-shape glue is not an edit ``_apply_order_and_edits`` can see past,
    so the merge still records ``__order__`` in both directions.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
            ("delta", "echo delta"),
        ]
    )
    ours = _positional_swap(base, "alpha", "beta")
    theirs = _swap_fragments(base, "alpha", "beta").replace(
        "run: echo gamma\n", "run: echo gamma-v2\n", 1
    )
    assert _job_keys(ours) == _job_keys(theirs) == ["beta", "alpha", "gamma", "delta"]
    assert ours != theirs

    forward = merge3(base, ours, theirs)
    assert forward.conflicts == ("__order__",)
    assert forward.text == _conflict_block(ours, theirs)
    reverse = merge3(base, theirs, ours)
    assert reverse.conflicts == ("__order__",)
    assert reverse.text == _conflict_block(theirs, ours)


def test_merge3_agreed_permutation_with_two_sided_body_edits_conflicts() -> None:
    """Negative control: both sides edit gamma differently.

    The permutation is agreed, but neither side is order-only and the two
    bodies differ from each other and from base. The merge must report a
    conflict (never a silent pick); it records one ``__order__`` conflict
    holding both whole texts.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
            ("delta", "echo delta"),
        ]
    )
    perm = _positional_swap(base, "alpha", "beta")
    ours = perm.replace("run: echo gamma\n", "run: echo gamma-v2\n", 1)
    theirs = perm.replace("run: echo gamma\n", "run: echo gamma-v3\n", 1)

    result = merge3(base, ours, theirs)
    assert result.conflicts == ("__order__",)
    assert result.text == _conflict_block(ours, theirs)


def test_merge3_agreed_three_job_rotation_with_one_sided_body_edit_is_clean() -> None:
    """A three-job rotation agreed on both sides merges beside a one-sided edit.

    Base is alpha, beta, gamma. Ours re-emits the same three jobs in the
    rotated order beta, gamma, alpha and edits nothing, so it is order-only.
    Theirs carries that same rotation with gamma's run changed to
    ``echo gamma-v2``. The rotation moves beta's leading separator into the
    first slot and both sides chose that glue, so the agreed order applies and
    the edited body wins: the merge is theirs' bytes with no conflict. The
    mixed-glue shape stays an ``__order__`` conflict in both directions: a
    rotation built by moving whole fragments keeps each job's own separator,
    so the edit side did not move every separator the permutation moved and
    the positional glue must not silently outrank it.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    rotation = _doc(
        [
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
            ("alpha", "echo alpha"),
        ]
    )
    edited_rotation = _doc(
        [
            ("beta", "echo beta"),
            ("gamma", "echo gamma-v2"),
            ("alpha", "echo alpha"),
        ]
    )
    assert _job_keys(base) == ["alpha", "beta", "gamma"]
    assert _job_keys(rotation) == ["beta", "gamma", "alpha"]
    assert rotation != base
    # Ours is order-only: every job's bytes from its key line onward are the
    # base bytes; only the leading separators moved with the slots.
    assert {
        fragment.key: _lead_and_body(fragment)[1]
        for fragment in split(rotation)
        if fragment.kind == "job"
    } == {
        fragment.key: _lead_and_body(fragment)[1]
        for fragment in split(base)
        if fragment.kind == "job"
    }

    agree = merge3(base, rotation, edited_rotation)
    assert agree.conflicts == ()
    assert agree.text == edited_rotation
    assert "run: echo gamma-v2\n" in _fragment(agree.text, "gamma")
    _assert_loadable(agree)

    mirrored = merge3(base, edited_rotation, rotation)
    assert mirrored.conflicts == ()
    assert mirrored.text == edited_rotation

    whole = _swap_fragments(_swap_fragments(base, "alpha", "beta"), "alpha", "gamma")
    mixed = whole.replace("run: echo gamma\n", "run: echo gamma-v2\n", 1)
    assert _job_keys(mixed) == ["beta", "gamma", "alpha"]
    assert mixed != edited_rotation

    forward = merge3(base, rotation, mixed)
    assert forward.conflicts == ("__order__",)
    assert forward.text == _conflict_block(rotation, mixed)
    reverse = merge3(base, mixed, rotation)
    assert reverse.conflicts == ("__order__",)
    assert reverse.text == _conflict_block(mixed, rotation)


def test_merge3_agreed_permutation_with_preamble_only_edit_is_clean() -> None:
    """An agreed permutation whose edit side changed only the preamble bytes.

    Ours is the positional swap of alpha and beta (order-only). Theirs carries
    that same swap and the same separator glue, with the comment line above
    ``jobs:`` changed and every job fragment equal to ours. The permutation is
    agreed and only the preamble is a one-sided edit, so the merge is theirs'
    bytes: the edited preamble in front of the agreed order.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
            ("delta", "echo delta"),
        ]
    )
    swapped = _positional_swap(base, "alpha", "beta")
    edited = swapped.replace(
        "# synthetic legacy manifest\n", "# synthetic legacy manifest v2\n", 1
    )
    assert _job_keys(swapped) == _job_keys(edited)
    assert _job_keys(edited) == ["beta", "alpha", "gamma", "delta"]
    assert edited != swapped
    assert _changed_keys(split(swapped), split(edited)) == {PREAMBLE_KEY}

    result = merge3(base, swapped, edited)
    assert result.conflicts == ()
    assert result.text == edited
    assert _fragment(result.text, PREAMBLE_KEY) == (
        "# synthetic legacy manifest v2\njobs:\n"
    )
    _assert_loadable(result)

    mirrored = merge3(base, edited, swapped)
    assert mirrored.conflicts == ()
    assert mirrored.text == edited
    _assert_loadable(mirrored)


def test_merge3_agreed_permutation_with_trailer_only_edit_is_clean() -> None:
    """An agreed permutation whose edit side changed only the trailer bytes.

    Base carries a ``# trailing note`` trailer. Ours swaps alpha and beta
    positionally and edits nothing; theirs is that same permutation with the
    trailer alone changed to ``# trailing note v2``. The trailer comes from the
    per-key resolve exactly as the preamble does, so the merge is theirs' bytes:
    the agreed order plus the edited trailer.
    """
    jobs = [
        ("alpha", "echo alpha"),
        ("beta", "echo beta"),
        ("gamma", "echo gamma"),
        ("delta", "echo delta"),
    ]
    base = _doc(jobs, trailer="# trailing note\n")
    swapped = _positional_swap(base, "alpha", "beta")
    edited = swapped.replace("# trailing note\n", "# trailing note v2\n", 1)
    assert _job_keys(swapped) == _job_keys(edited)
    assert _job_keys(edited) == ["beta", "alpha", "gamma", "delta"]
    assert edited != swapped
    assert _changed_keys(split(swapped), split(edited)) == {TRAILER_KEY}

    result = merge3(base, swapped, edited)
    assert result.conflicts == ()
    assert result.text == edited
    assert _fragment(result.text, TRAILER_KEY) == "# trailing note v2\n"
    _assert_loadable(result)

    mirrored = merge3(base, edited, swapped)
    assert mirrored.conflicts == ()
    assert mirrored.text == edited
    _assert_loadable(mirrored)


def test_merge3_agreed_middle_job_swap_with_identical_glue_is_clean() -> None:
    """Two middle jobs trade places with identical glue, beside a body edit.

    Swapping beta and gamma is the degenerate permutation: both jobs carry the
    same leading separator, so a positional swap and a whole-fragment swap are
    byte-for-byte the same text, and no separator moves relative to the base.
    Ours is that order-only swap, theirs adds delta's run edit. The guard is
    vacuous here, the agreed order applies, and the merge is theirs' bytes in
    both directions.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
            ("delta", "echo delta"),
        ]
    )
    swapped = _positional_swap(base, "beta", "gamma")
    assert swapped == _swap_fragments(base, "beta", "gamma")
    assert _job_keys(swapped) == ["alpha", "gamma", "beta", "delta"]
    edited = swapped.replace("run: echo delta\n", "run: echo delta-v2\n", 1)
    assert _changed_keys(split(swapped), split(edited)) == {"delta"}

    result = merge3(base, swapped, edited)
    assert result.conflicts == ()
    assert result.text == edited
    assert "run: echo delta-v2\n" in _fragment(result.text, "delta")
    _assert_loadable(result)

    mirrored = merge3(base, edited, swapped)
    assert mirrored.conflicts == ()
    assert mirrored.text == edited
    _assert_loadable(mirrored)


def test_merge3_order_only_permutation_applies_with_nonoverlapping_edit(
    tmp_path: Path,
) -> None:
    """An order-only permutation and a non-overlapping scalar edit both apply.

    Ours swaps alpha and beta. Theirs only changes gamma's run scalar. Key
    order is the swap and gamma's scalar is theirs. The separator newline
    ``_leading_start`` glues on moves with the permutation: a whole-fragment
    swap keeps each job's own separator, and a positional swap keeps the
    separator in the slot. Both directions exit clean.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    swapped = _doc(
        [
            ("beta", "echo beta"),
            ("alpha", "echo alpha"),
            ("gamma", "echo gamma"),
        ]
    )
    edited = base.replace("run: echo gamma\n", "run: echo gamma-v2\n", 1)
    expected = swapped.replace("run: echo gamma\n", "run: echo gamma-v2\n", 1)
    assert expected != swapped
    assert _job_keys(expected) == ["beta", "alpha", "gamma"]

    from_ours = merge3(base, swapped, edited)
    from_theirs = merge3(base, edited, swapped)
    assert from_ours.conflicts == ()
    assert from_theirs.conflicts == ()
    assert from_ours.text == expected
    assert from_theirs.text == expected
    assert _job_keys(from_ours.text) == ["beta", "alpha", "gamma"]
    assert "run: echo gamma-v2\n" in _fragment(from_ours.text, "gamma")
    assert "run: echo beta\n" in _fragment(from_ours.text, "beta")
    assert "run: echo alpha\n" in _fragment(from_ours.text, "alpha")
    _assert_loadable(from_ours)
    _assert_loadable(from_theirs)

    whole = _swap_fragments(base, "alpha", "beta")
    whole_expected = whole.replace("run: echo gamma\n", "run: echo gamma-v2\n", 1)
    assert whole != expected
    assert merge3(base, whole, edited).conflicts == ()
    assert merge3(base, whole, edited).text == whole_expected
    assert merge3(base, edited, whole).text == whole_expected

    positional = _positional_swap(base, "alpha", "beta")
    positional_expected = positional.replace(
        "run: echo gamma\n", "run: echo gamma-v2\n", 1
    )
    placed = merge3(base, positional, edited)
    assert placed.conflicts == ()
    assert placed.text == positional_expected
    assert merge3(base, edited, positional).text == positional_expected

    alpha_edit = base.replace("run: echo alpha\n", "run: echo alpha-v2\n", 1)
    moved = merge3(base, swapped, alpha_edit)
    assert moved.conflicts == ()
    assert _job_keys(moved.text) == ["beta", "alpha", "gamma"]
    assert moved.text == swapped.replace(
        "run: echo alpha\n", "run: echo alpha-v2\n", 1
    )
    assert "run: echo alpha-v2\n" in _fragment(moved.text, "alpha")

    manifest = _text()
    manifest_keys = _job_keys(manifest)
    manifest_swap = _positional_swap(manifest, manifest_keys[0], manifest_keys[1])
    target, target_fragment, old_runs_on = _single_runs_on_job(manifest)
    # Identity, not substring: a duplicated or detached fragment passes ``in``,
    # and the positional swap legitimately moves target's leading separator
    # with the slot, so pin the bytes from the key line and the one entry that
    # ``split`` maps to target in ``manifest_swap``.
    target_body = _lead_and_body(
        next(fragment for fragment in split(manifest) if fragment.key == target)
    )[1]
    assert [
        _lead_and_body(fragment)[1]
        for fragment in split(manifest_swap)
        if fragment.key == target
    ] == [target_body]
    new_runs_on = "    runs-on: ubuntu-22.04\n"
    if old_runs_on == new_runs_on:
        new_runs_on = "    runs-on: ubuntu-24.04\n"
    assert old_runs_on != new_runs_on
    edited_fragment = target_fragment.replace(old_runs_on, new_runs_on, 1)
    assert edited_fragment != target_fragment
    manifest_edit = manifest.replace(target_fragment, edited_fragment, 1)
    manifest_expected = manifest_swap.replace(target_fragment, edited_fragment, 1)
    manifest_result = merge3(manifest, manifest_swap, manifest_edit)
    assert manifest_result.conflicts == ()
    assert manifest_result.text == manifest_expected
    assert _job_keys(manifest_result.text)[:2] == [
        manifest_keys[1],
        manifest_keys[0],
    ]
    assert new_runs_on in _fragment(manifest_result.text, target)

    base_path = tmp_path / "base.yml"
    ours_path = tmp_path / "ours.yml"
    theirs_path = tmp_path / "theirs.yml"
    base_path.write_text(base, encoding="utf-8")
    ours_path.write_text(swapped, encoding="utf-8")
    theirs_path.write_text(edited, encoding="utf-8")
    assert main(["merge3", str(base_path), str(ours_path), str(theirs_path)]) == 0
    assert ours_path.read_text(encoding="utf-8") == expected
    assert base_path.read_text(encoding="utf-8") == base
    assert theirs_path.read_text(encoding="utf-8") == edited


def test_merge3_positional_swap_beside_a_moved_separator_edit_is_order_conflict() -> None:
    """A permutation-moved separator must not silently outrank a third-shape edit.

    Ours swaps ``alpha`` and ``beta`` positionally: ``beta`` arrives in
    ``alpha``'s leading slot, so its leading separator moves (order lead
    ``""`` against the base lead ``"\n"``). Theirs inserts one
    ``  # comment between jobs`` line before the ``beta`` key -- a separator
    that differs from both the base and the moved lead.
    ``_apply_order_and_edits`` must return ``None`` so ``merge3`` records
    ``__order__`` with both full texts inside one marker pair, keeping the
    comment inside the marker instead of dropping it. This is W9-V battery
    case e1, which produced ``conflicts=()`` with ``comment_kept=False`` at
    ``03463014``.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    positional = _positional_swap(base, "alpha", "beta")
    with_comment = base.replace(
        "\n  beta:", "\n  # comment between jobs\n  beta:", 1
    )
    assert with_comment != base
    assert "  # comment between jobs\n  beta:" in with_comment

    forward = merge3(base, positional, with_comment)
    assert forward.conflicts == ("__order__",)
    assert forward.text == _conflict_block(positional, with_comment)
    middle = "=" * 7
    closer = ">" * 7
    at = forward.text.index("  # comment between jobs")
    assert forward.text.index(middle) < at < forward.text.index(closer)

    reverse = merge3(base, with_comment, positional)
    assert reverse.conflicts == ("__order__",)
    assert reverse.text == _conflict_block(with_comment, positional)

    # W9-V battery case e3: a whole-fragment swap keeps each job's own
    # separator, so order_lead == base_lead and the same comment stays
    # clean exactly as HEAD behaved before this change.
    whole = _swap_fragments(base, "alpha", "beta")
    clean = merge3(base, whole, with_comment)
    assert clean.conflicts == ()
    assert "  # comment between jobs\n  beta:" in clean.text
    _assert_loadable(clean)


def test_merge3_positional_swap_of_leading_real_jobs_returns_that_side() -> None:
    """Positional swap of the first two real jobs must not invent a third text.

    Those two jobs trade places. The separator newline stays in the gap, so
    the fragment texts differ from base by that glue alone. One side is
    order-only and the other side is the base, so the merge is that side's
    original bytes. Assertions cover that swap only, not the live job ids.
    """
    base = _text()
    keys = _job_keys(base)
    swapped = _positional_swap(base, keys[0], keys[1])
    assert join(split(swapped)) == swapped
    assert swapped != base
    assert _job_keys(swapped)[:2] == [keys[1], keys[0]]

    from_ours = merge3(base, swapped, base)
    from_theirs = merge3(base, base, swapped)
    assert from_ours.conflicts == ()
    assert from_theirs.conflicts == ()
    assert from_ours.text == swapped
    assert from_theirs.text == swapped
    assert from_ours.text != base

    whole = _swap_fragments(base, keys[0], keys[1])
    assert whole != base
    assert merge3(base, whole, base).conflicts == ()
    assert merge3(base, whole, base).text == whole


def test_merge3_incumbent_order_change_is_one_conflict(
    tmp_path: Path, capsys
) -> None:
    """An incumbent reorder that is not an order-only merge conflicts.

    The record is a single ``__order__`` marker pair around the original
    texts. Two different permutations, a reorder that also edits on the same
    side, a reorder beside an append, and a reorder beside a deletion all
    take that path. An identical permutation, and an order-only permutation
    beside a text edit, are covered by their own tests.
    """
    base = _doc(
        [
            ("alpha", "echo alpha"),
            ("beta", "echo beta"),
            ("gamma", "echo gamma"),
        ]
    )
    ours = _doc(
        [
            ("beta", "echo beta"),
            ("alpha", "echo alpha"),
            ("gamma", "echo gamma"),
        ]
    )
    theirs = _doc(
        [
            ("gamma", "echo gamma"),
            ("beta", "echo beta"),
            ("alpha", "echo alpha"),
        ]
    )

    both = merge3(base, ours, theirs)
    assert both.conflicts == ("__order__",)
    assert both.text == _conflict_block(ours, theirs)
    assert both.text.count("<" * 7 + " ours") == 1

    changed = ours.replace("run: echo gamma\n", "run: echo gamma-ours\n", 1)
    same_side = merge3(base, changed, base)
    assert same_side.conflicts == ("__order__",)
    assert same_side.text == _conflict_block(changed, base)

    other_append = _append(base, "delta", "echo delta")
    assert merge3(base, ours, other_append).conflicts == ("__order__",)
    other_delete = _drop(base, "gamma")
    assert merge3(base, ours, other_delete).conflicts == ("__order__",)

    appended = _append(ours, "delta", "echo delta")
    added = merge3(base, appended, base)
    assert added.conflicts == ("__order__",)
    assert added.text == _conflict_block(appended, base)
    assert "echo delta\n" in added.text

    deleted = _drop(
        _doc(
            [
                ("gamma", "echo gamma"),
                ("alpha", "echo alpha"),
                ("beta", "echo beta"),
            ]
        ),
        "beta",
    )
    assert _job_keys(deleted) == ["gamma", "alpha"]
    removed = merge3(base, deleted, base)
    assert removed.conflicts == ("__order__",)
    assert removed.text == _conflict_block(deleted, base)

    base_path = tmp_path / "base.yml"
    ours_path = tmp_path / "ours.yml"
    theirs_path = tmp_path / "theirs.yml"
    base_path.write_text(base, encoding="utf-8")
    ours_path.write_text(ours, encoding="utf-8")
    theirs_path.write_text(theirs, encoding="utf-8")
    assert main(["merge3", str(base_path), str(ours_path), str(theirs_path)]) == 1
    captured = capsys.readouterr()
    assert "conflict: __order__" in captured.err
    assert ours_path.read_text(encoding="utf-8") == both.text
    assert base_path.read_text(encoding="utf-8") == base
    assert theirs_path.read_text(encoding="utf-8") == theirs


def test_merge3_repeated_job_key_is_a_conflict(tmp_path: Path, capsys) -> None:
    """A second body for the same job key is a conflict, not a dropped slice.

    ``join(split)`` still round-trips both bodies. ``merge3`` of three copies
    exits through the CLI with status 1 and keeps ``echo SECOND_BODY`` inside
    the marker pair.
    """
    doc = (
        "# synthetic legacy manifest\n"
        "jobs:\n"
        + _job("alpha", "echo FIRST_BODY")
        + "\n"
        + _job("alpha", "echo SECOND_BODY")
    )
    assert join(split(doc)) == doc
    alphas = [fragment.text for fragment in split(doc) if fragment.key == "alpha"]
    assert len(alphas) == 2
    assert "echo FIRST_BODY\n" in alphas[0]
    assert "echo SECOND_BODY\n" in alphas[1]

    result = merge3(doc, doc, doc)
    assert result.conflicts == ("alpha",)
    inside_start = result.text.index("<" * 7)
    inside_end = result.text.index(">" * 7)
    inside = result.text[inside_start:inside_end]
    assert "echo FIRST_BODY" in inside
    assert "echo SECOND_BODY" in inside
    assert result.text.count("<" * 7 + " ours") == 1
    assert result.text == (
        _fragment(doc, PREAMBLE_KEY)
        + _conflict_block(alphas[0] + alphas[1], alphas[0] + alphas[1])
        + _fragment(doc, TRAILER_KEY)
    )

    base_path = tmp_path / "base.yml"
    ours_path = tmp_path / "ours.yml"
    theirs_path = tmp_path / "theirs.yml"
    for path in (base_path, ours_path, theirs_path):
        path.write_text(doc, encoding="utf-8")
    assert main(["merge3", str(base_path), str(ours_path), str(theirs_path)]) == 1
    captured = capsys.readouterr()
    assert "conflict: alpha" in captured.err
    written = ours_path.read_text(encoding="utf-8")
    assert written == result.text
    assert "echo SECOND_BODY" in written
