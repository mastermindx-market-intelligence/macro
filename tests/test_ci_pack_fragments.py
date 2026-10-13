"""Byte-exact split/join of .github/ci/legacy-jobs.yml at job boundaries."""

from __future__ import annotations

from pathlib import Path

import yaml

from scripts.ci_pack_fragments import (
    PREAMBLE_KEY,
    TRAILER_KEY,
    Fragment,
    check_manifest,
    join,
    job_paths,
    main,
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
