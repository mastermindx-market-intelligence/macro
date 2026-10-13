"""Byte-exact split/join of .github/ci/legacy-jobs.yml at job boundaries."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

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


def test_merge3_replay_of_appended_jobs_is_clean_where_merge_file_conflicts(
    tmp_path: Path,
) -> None:
    """Replay d6d1342b53, where both parents appended jobs onto legacy-jobs.yml.

    Parent 203e0f19 added ``market-ontology-f09-usgs-mcs``. Parent e692d9dc
    added ``recurring-briefs`` at the same end plus two mid-file jobs. The
    recorded resolution kept every added job. A line-level ``git merge-file``
    still conflicts on that shared append.
    """
    ours_rev = "203e0f1992bf20b885cd3333d9a074be4cd172b0"
    theirs_rev = "e692d9dc4bdc812c0b51e45fc95764c1874ff0b2"
    merged_rev = "d6d1342b535beb784b149c123c7055fdbde206cb"

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


def test_merge3_positional_swap_of_leading_real_jobs_returns_that_side() -> None:
    """Positional swap of the first two real jobs must not invent a third text.

    ``company-intelligence-private-runtime`` and
    ``microstructure-pressure-response-r0`` trade places. The separator newline
    stays in the gap, so the fragment texts differ from base by that glue
    alone. One side is order-only and the other side is the base, so the merge
    is that side's original bytes.
    """
    base = _text()
    keys = _job_keys(base)
    assert keys[0] == "company-intelligence-private-runtime"
    assert keys[1] == "microstructure-pressure-response-r0"
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
    """Any incumbent reorder that is not exactly one order-only side conflicts.

    The record is a single ``__order__`` marker pair around the original
    texts. A matching reorder on both sides, a reorder beside an edit, a
    reorder beside an append, and a reorder beside a deletion all take that
    path.
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

    same = merge3(base, ours, ours)
    assert same.conflicts == ("__order__",)
    assert same.text == _conflict_block(ours, ours)

    edited = base.replace("run: echo alpha\n", "run: echo alpha-v2\n", 1)
    mixed = merge3(base, ours, edited)
    assert mixed.conflicts == ("__order__",)
    assert mixed.text == _conflict_block(ours, edited)

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
