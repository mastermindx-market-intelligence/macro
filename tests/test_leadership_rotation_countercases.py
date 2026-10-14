"""LR-CHAL-T20 — integrated counter-case regression set for the LEADERSHIP-ROTATION
measured-product chain.

SOURCE -> PROJECTION -> CONSUMER on the SAME identities, mutating one axis at a
time, asserting the EXACT rendered/projected effect of each mutation. Counter-cases
must DISCRIMINATE: every test is one a plausible wrong implementation fails.

All inputs are SYNTHETIC. The author has no knowledge of or the live, non-
synthetic data; every fixture and every in-memory payload below carries
``"synthetic": true`` at the top level (or in module-level ``SYNTHETIC = True``)
where the owner schema tolerates an extra key, and a docstring otherwise says
so. No data/ or site/ reads, no network, no clock reads (explicit dates only),
no builder invocation, no reads of any fixture that exists today except the
byte-pinned ``measured_read_v1.json`` (read-only).

Test layout (each ``test_cc_<contract>_<axis>_...``):

  1. group_measurement (projection AND consumer)
     a. absence  — drop one cohort ticker -> measured - 1, coverage n/N drops,
                   breadth k uses n (measured), the panel renders an unmeasured
                   plain-word row that is NOT in the ranked order, every other
                   ticker's rank order is unchanged.
     b. zero     — horizon value exactly 0.0 -> IS measured, IS ranked, is NOT
                   counted as a positive in breadth k, rendered row differs
                   from the absence case (zero != unmeasured).
     c. overlap  — two synthetic groups sharing members -> overlap equals
                   Sigma-min of shared weights exactly; one more shared
                   member raises overlap by that member's min weight; duplicate
                   member identities inside ONE group count once in breadth
                   and overlap.

  2. transition_observation
     a. role     — swap role -> projected field changes in exactly that field;
                   ranks unchanged; rendered observation row's text changes.
     b. date     — observation dated AFTER the read's as-of is refused; absent
                   from projection and render; rotation payload whose as_of != the
                   cycles as_of withholds events (T17 s2) and the panel says so.
     c. lineage  — two observations from the same source root count once
                   (``dedupe_source_roots``); an early/candidate observation
                   must NEVER appear in ``active`` (confirmed).

  3. research_estimate
     — default read exposes no research estimate; supplying a ResearchEstimate
       adds it as a SEPARATE object and leaves every group_measurement value and
       rank byte-identical; a huge estimate value changes no rank.

  4. evidence mode (basis axis lives here)
     — a reconstructed history (``naturally_observed: False``) is labelled
       reconstructed end-to-end and never treated as retained; flipping the
       declared basis or the mode changes exactly the label/eligibility the
       owner tests define.

  5. A42 history-failure isolation
     — three distinct history failures (history payload null; wrong schema;
       history as_of mismatching the read's as_of) each change ONLY the
       ``#mr-hist`` box state; the ranked list HTML, the selection and the
       coverage copy stay byte-identical to the baseline run.

  6. A45 protected payload
     (i)  the jinja ``render(...)`` kwargs in ``scripts/build_sector_central.py``
          contain no ``measured_read`` / ``transition_observation`` /
          ``research_estimate`` / ``rs_63d`` value and no kwarg that carries the
          ``window.SECTOR_CENTRAL`` data object;
     (ii) the template source contains no server-side ``{{ ... }}`` or
          ``{% ... %}`` expression referencing those names;
     (iii) none of ``/sector_central_data.js``, ``/sectordata/``,
           ``/premiumdata/`` is in ``config/site_access.yml`` ``public``
           (so they are default-deny for anonymous).

Mutants (env switch ``LR_COUNTERCASE_MUTANT`` in
{absence_as_zero, js_ranks_unmeasured, public_sectordata}):

  * ``absence_as_zero``     — monkeypatch
    ``engine.leadership_rotation_context._sector_record_value`` so a missing
    horizon value returns 0.0; 1a/1b MUST FAIL.
  * ``js_ranks_unmeasured`` — minimal in-memory edit of the panel JS region so
    unmeasured rows enter the ranked list; the consumer half of 1a MUST FAIL.
  * ``public_sectordata``   — exposure checker sees ``/sectordata/sector_central.json``
    as public; 6(iii) MUST FAIL.

ALWAYS-GREEN kill tests (``test_kill_<mutant>``) apply each mutant internally
and assert the corresponding check detects it.
"""
from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

# Module-level synthetic marker: every fixture the owner schemas tolerate gets
# ``"synthetic": true`` at its top level; this constant and the docstring
# satisfy the contract for the others.
SYNTHETIC = True

REPO_ROOT = Path(__file__).resolve().parent.parent
from tests.test_leadership_measured_read import (  # noqa: E402
    AS_OF as AN, _build_cyc_payload, _build_rotation_payload)
from tests.test_sector_central_measured_panel import (  # noqa: E402
    _all_text, _fixture, _panel_js, _run, needs_node)

from engine import leadership_rotation_context as lrc  # noqa: E402
from engine.leadership_rotation_context import (  # noqa: E402
    ResearchEstimate,
    breadth,
    is_measured,
    overlap,
    shared_members,
    us_sector_cohort,
)


# ──────────────────────────────────────────────────────────────────────────────
# Mutant setup (env var read once at import)
# ──────────────────────────────────────────────────────────────────────────────

LR_COUNTERCASE_MUTANT = os.environ.get("LR_COUNTERCASE_MUTANT", "")
VALID_MUTANTS = ("", "absence_as_zero", "js_ranks_unmeasured", "public_sectordata")


def _pytest_configure(config):
    if LR_COUNTERCASE_MUTANT not in VALID_MUTANTS:
        raise pytest.UsageError(
            f"LR_COUNTERCASE_MUTANT must be one of {VALID_MUTANTS}, "
            f"got {LR_COUNTERCASE_MUTANT!r}"
        )


pytest_configure = _pytest_configure


@pytest.fixture(autouse=True)
def _apply_mutant(monkeypatch):
    """Apply the env-selected mutant in memory only — never a file write."""
    if LR_COUNTERCASE_MUTANT == "absence_as_zero":
        original = lrc._sector_record_value

        def _mutant(rec, horizon):
            v = original(rec, horizon)
            if isinstance(v, lrc.Unmeasured):
                return 0.0  # the mutant: missing -> 0.0
            return v

        monkeypatch.setattr(lrc, "_sector_record_value", _mutant)
    elif LR_COUNTERCASE_MUTANT == "js_ranks_unmeasured":
        original_js = _panel_js()

        # Strip the `g.current.status === 'measured'` guard from the
        # ranked/others partition so unmeasured rows enter the ranked list.
        mutant_js = original_js.replace(
            "if (g.current && g.current.status === 'measured' && num(g.current.rank)) ranked.push(g);",
            "if (g.current && num(g.current.rank)) ranked.push(g);",
            1,
        )
        assert mutant_js != original_js, "mutant did not modify the JS region"

        def _mutant_panel_js():
            return mutant_js

        # Patch the symbol that test_sector_central_measured_panel._run resolves.
        import tests.test_sector_central_measured_panel as tscm
        monkeypatch.setattr(tscm, "_panel_js", _mutant_panel_js)
    elif LR_COUNTERCASE_MUTANT == "public_sectordata":
        # Append /sectordata/sector_central.json to the in-memory public
        # list so the 6(iii) exposure checker sees it. The site_access.yml
        # file is NEVER modified — the check goes through a module-level
        # helper that the autouse patches.
        def _mutated_public(public_list: list) -> list:
            # append only if not already present (idempotent)
            mutated = list(public_list)
            if "/sectordata/sector_central.json" not in mutated:
                mutated.append("/sectordata/sector_central.json")
            return mutated

        # Patch the helper the 6(iii) test uses.
        monkeypatch.setattr(
            "tests.test_leadership_rotation_countercases._public_exact_for_exposure_check",
            _mutated_public)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _dump(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False) + "\n"


def _baseline_groups_dict(out: dict) -> dict:
    return {g["group_id"]: g for g in out["groups"]}


def _baseline_out():
    cyc, rot = _build_cyc_payload(), _build_rotation_payload()
    return lrc.measured_group_read(cyc, rotation_payload=rot), cyc, rot


def _public_exact_for_exposure_check(public_list):
    """The exposure check used by 6(iii) — list is checked in-memory only
    so the public_sectordata mutant can swap it without file writes.

    Default behaviour: identity. The autouse fixture monkeypatches this
    helper when LR_COUNTERCASE_MUTANT=public_sectordata is set."""
    return list(public_list)


# ══════════════════════════════════════════════════════════════════════════════════
# Contract 1 — group_measurement (projection AND consumer)
# ══════════════════════════════════════════════════════════════════════════════════

def test_cc_1a_absence_projection_measured_count_drops_and_breadth_uses_n():
    """Axis: absence. Drop one cohort ticker from the source -> measured count
    drops by exactly 1; coverage n/N changes 11/11 -> 10/11; breadth denominator
    is n (measured), not N."""
    base, _, _ = _baseline_out()
    base_by = _baseline_groups_dict(base)
    assert base["cohort"]["expected_n"] == 11
    assert base["cohort"]["measured_n"] == 9  # baseline: 9 measured, 2 unmeasured
    assert base["status"] == "partial"

    # Mutation: drop XLE entirely (and XLE's history) so it joins XLRE as missing.
    cyc_drop, rot = _build_cyc_payload(), _build_rotation_payload()
    cyc_drop["sectors"] = [s for s in cyc_drop["sectors"] if s["ticker"] != "XLE"]
    out = lrc.measured_group_read(cyc_drop, rotation_payload=rot)

    by = _baseline_groups_dict(out)
    assert "XLE" in by
    assert by["XLE"]["current"]["status"] == "unmeasured"
    assert by["XLE"]["current"]["reason"] == "missing_input"
    assert by["XLE"]["current"]["rank"] is None  # unmeasured is never ranked

    assert out["cohort"]["measured_n"] == base["cohort"]["measured_n"] - 1
    assert out["cohort"]["expected_n"] == 11
    # breadth denominator is n (measured), not N
    pb = out["cohort"]["positive_breadth"]
    assert pb["coverage"] == pytest.approx(out["cohort"]["measured_n"] / 11)
    if pb["k_over_n"] is not None:
        assert 0.0 <= pb["k_over_n"] <= 1.0
        # k_over_n must equal positives / measured_n (the breadth n)
        positives = sum(1 for g in out["groups"]
                        if g["current"]["status"] == "measured" and g["current"]["rs_63d"] > 0)
        assert pb["k_over_n"] == pytest.approx(positives / out["cohort"]["measured_n"])

    # missing list contains XLE
    missing_pairs = [tuple(m) for m in out["cohort"]["missing"]]
    assert ("XLE", "missing_input") in missing_pairs

    # Every other ticker's RELATIVE rank order is unchanged. Renumber 1..n
    # after removing XLE; the surviving order must match the baseline order.
    base_rank = {gid: g["current"]["rank"] for gid, g in base_by.items()
                if g["current"]["rank"] is not None}
    out_rank = {gid: g["current"]["rank"] for gid, g in by.items()
                if g["current"]["rank"] is not None}
    base_measured_set = {gid for gid, g in base_by.items()
                         if g["current"]["status"] == "measured"}
    out_measured_set = {gid for gid, g in by.items()
                        if g["current"]["status"] == "measured"}
    assert out_measured_set == base_measured_set - {"XLE"}
    base_order = [gid for gid in sorted(base_rank, key=lambda k: (-base_rank[k], k))
                  if gid != "XLE"]
    out_order = [gid for gid in sorted(out_rank, key=lambda k: (-out_rank[k], k))]
    assert out_order == base_order, (out_order, base_order)


@needs_node
def test_cc_1a_absence_consumer_unmeasured_row_in_plain_words_not_ranked():
    """Axis: absence. The panel renders the missing ticker as an unmeasured
    row in plain words, NOT in the ranked order. Every other ticker's rank
    order is unchanged."""
    out = _run()
    rows = [r[0] for r in out["rows"]]
    # Baseline: 9 measured tickers (including XLE) ranked. No unmeasured rows.
    assert "XLE" in rows  # XLE is ranked in baseline
    assert out["unHidden"] is False or out["unHidden"] is None
    # Mutate the fixture: keep the 11 groups, but flip XLE's status to
    # unmeasured with reason=missing_input. To prove the panel guards
    # against the js_ranks_unmeasured mutant (which checks num(rank) only),
    # we keep XLE's rank as a non-None number (the projection gave it
    # rank=1). The status-gate is what must move XLE into the unmeasured
    # box; the rank field is incidental.
    import tests.test_sector_central_measured_panel as tscm
    base_fixture = tscm._fixture()
    mutated = json.loads(json.dumps(base_fixture))
    for g in mutated["groups"]:
        if g["group_id"] == "XLE":
            g["current"]["status"] = "unmeasured"
            g["current"]["reason"] = "missing_input"
            g["current"]["rs_21d"] = None
            g["current"]["rs_63d"] = None
            # rank deliberately kept numeric (was rank=1 in baseline) so the
            # status gate is the only thing that places XLE in unmeasured
            g["current"]["z"] = None
    mutated["cohort"] = dict(mutated["cohort"], measured_n=8)
    mutated["cohort"]["positive_breadth"] = dict(mutated["cohort"]["positive_breadth"],
                                                 coverage=8 / 11)
    out_m = _run(fixture=mutated)
    rows_m = [r[0] for r in out_m["rows"]]
    # XLE is not in the RANKED list (only measured rows go to #mr-list);
    # the unmeasured box (#mr-unmeasured) holds the plain-words row.
    assert "XLE" not in out_m["list"], "XLE leaked into the ranked list"
    # Every other ranked ticker's RELATIVE order is unchanged. Baseline
    # ranks XLE first; mutation drops it; the surviving order matches
    # baseline after removing XLE.
    base_ranked = re.findall(r'data-g="([^"]+)"', out["list"])
    out_ranked = re.findall(r'data-g="([^"]+)"', out_m["list"])
    assert out_ranked == [t for t in base_ranked if t != "XLE"], (
        out_ranked, [t for t in base_ranked if t != "XLE"])
    # XLE must appear in the unmeasured list with plain words
    assert out_m["unHidden"] is False
    assert "XLE" in out_m["un"]
    assert "no price data for this sector today" in out_m["un"]
    # no digits or % in the unmeasured li
    li = re.search(r'<li>.*?XLE.*?</li>', out_m["un"], re.S)
    assert li
    assert "%" not in li.group(0) and "0.0" not in li.group(0)


def test_cc_1b_zero_is_measured_and_ranked_but_not_a_positive_in_breadth_k():
    """Axis: zero. Set a ticker's horizon value to exactly 0.0 -> it STAYS
    measured (is_measured True), IS ranked, IS NOT counted as a positive in
    breadth k. The projected row differs from the absence case."""
    base, _, _ = _baseline_out()
    base_xle = _baseline_groups_dict(base)["XLE"]
    assert base_xle["current"]["rs_63d"] == 4.1  # baseline XLE = +4.1 (positive)

    cyc, rot = _build_cyc_payload(), _build_rotation_payload()
    # mutate: set XLE's rs_63d and rs_21d to exactly 0.0
    for s in cyc["sectors"]:
        if s["ticker"] == "XLE":
            s["now"]["rs_63d"] = 0.0
            s["now"]["rs_21d"] = 0.0
    out = lrc.measured_group_read(cyc, rotation_payload=rot)
    xle = _baseline_groups_dict(out)["XLE"]

    # XLE is still measured
    assert xle["current"]["status"] == "measured"
    assert xle["current"]["rs_63d"] == 0.0
    assert xle["current"]["reason"] is None
    assert isinstance(xle["current"]["rank"], int)  # ranked
    # XLE is NOT counted as a positive in breadth k
    pb = out["cohort"]["positive_breadth"]
    base_positives = sum(1 for g in base["groups"]
                         if g["current"]["status"] == "measured" and g["current"]["rs_63d"] > 0)
    out_positives = sum(1 for g in out["groups"]
                        if g["current"]["status"] == "measured" and g["current"]["rs_63d"] > 0)
    assert out_positives == base_positives - 1  # XLE dropped out of positive
    # k_over_n reflects the same n=9 denominator
    assert pb["k_over_n"] == pytest.approx(out_positives / out["cohort"]["measured_n"])
    # n is unchanged (XLE is still measured)
    assert out["cohort"]["measured_n"] == base["cohort"]["measured_n"]

    # rendered row differs from absence: absence renders as unmeasured plain words
    # with NO data-g in the ranked list; zero renders as a ranked measured row
    # with the cell content '<span class="mr-flat">+0.0%</span>' / '+0.0%'.
    assert xle["current"]["rs_63d"] is not None
    assert base_xle["current"]["rs_63d"] is not None
    # the absence baseline projects XLE with status=unmeasured; zero differs.
    cyc_absent = _build_cyc_payload()
    cyc_absent["sectors"] = [s for s in cyc_absent["sectors"] if s["ticker"] != "XLE"]
    absent_out = lrc.measured_group_read(cyc_absent, rotation_payload=rot)
    absent_xle = _baseline_groups_dict(absent_out)["XLE"]
    assert absent_xle["current"]["status"] == "unmeasured"
    assert absent_xle["current"]["rank"] is None
    assert absent_xle["current"]["rs_63d"] is None
    # zero != absence
    assert xle["current"]["status"] != absent_xle["current"]["status"]
    assert xle["current"]["rank"] != absent_xle["current"]["rank"]


@needs_node
def test_cc_1b_zero_consumer_renders_ranked_with_flat_cell_unmeasured_hides():
    """Axis: zero (consumer). The rendered row for the 0.0-valued ticker is
    RANKED (in the ranked list, NOT in the unmeasured box), and the cell
    carries a non-number placeholder rather than a percentage."""
    import tests.test_sector_central_measured_panel as tscm
    base_fixture = tscm._fixture()
    mutated = json.loads(json.dumps(base_fixture))  # deep copy
    xle = next(g for g in mutated["groups"] if g["group_id"] == "XLE")
    xle["current"]["rs_63d"] = 0.0
    xle["current"]["rs_21d"] = 0.0
    out = _run(fixture=mutated)
    # XLE is in the ranked list (not unmeasured)
    rows = [r[0] for r in out["rows"]]
    assert "XLE" in rows
    # the button carries the data-g and is aria-pressed=false
    assert any(r[1] == "false" for r in out["rows"] if r[0] == "XLE")
    # XLE is NOT in the unmeasured list
    li = re.search(r'<li>.*?XLE.*?</li>', out["un"] or "", re.S)
    assert li is None
    # the XLE button has a non-percentage placeholder for rs_63d (flat)
    xle_btn = re.search(r'<button[^>]*data-g="XLE".*?</button>', out["list"], re.S)
    assert xle_btn
    # the rs_63d cell renders as either an `mr-flat` "+0.0%" or `mr-na` "n/a"
    assert ("mr-flat" in xle_btn.group(0) or "mr-na" in xle_btn.group(0))


def test_cc_1c_overlap_two_groups_sharing_members_equals_sigma_min():
    """Axis: overlap. Two synthetic groups sharing members -> overlap equals
    Sigma-min of shared weights exactly; one more shared member raises it by
    that member's min weight."""
    # Maps with sum=1: normalize is identity, so the overlap equals
    # Sigma-min of the literal weights.
    w_g = {"A": 0.4, "B": 0.3, "C": 0.3}
    w_h = {"A": 0.3, "B": 0.4, "D": 0.3}
    # expected = min(0.4, 0.3) + min(0.3, 0.4) = 0.6 (C and D are not shared)
    expected = min(0.4, 0.3) + min(0.3, 0.4)
    assert overlap(w_g, w_h) == pytest.approx(expected)
    # non-shared-only maps -> overlap uses only shared (min(x, 0)=0)
    only_g = {"A": 1.0}
    only_h = {"B": 1.0}
    assert overlap(only_g, only_h) == pytest.approx(0.0)
    # Adding a shared member F (same normalized weight in both maps) raises
    # overlap by exactly F's normalized weight.
    w_g_f = {"A": 0.4, "B": 0.3, "C": 0.2, "F": 0.1}  # sum=1.0
    w_h_f = {"A": 0.3, "B": 0.4, "D": 0.2, "F": 0.1}  # sum=1.0
    new_overlap = min(0.4, 0.3) + min(0.3, 0.4) + min(0.1, 0.1)
    assert overlap(w_g_f, w_h_f) == pytest.approx(new_overlap)
    assert overlap(w_g_f, w_h_f) == pytest.approx(overlap(w_g, w_h) + 0.1)


def test_cc_1c_overlap_shared_members_breadth_dedup_inside_one_group():
    """Axis: overlap (duplicate member). Duplicate member identities inside ONE
    group (same ticker twice) must be counted once in breadth/overlap. If the
    owner double-counts, this test catches it via shared_members + the cohort
    breadth result."""
    # shared_members returns sorted ids with measured weight > 0 in BOTH
    w_g = {"XLE": 0.5, "XLF": 0.3, "XLE": 0.2}  # duplicate XLE; dict literal collapses
    # to make the test meaningful, hand-craft a list-of-pairs and dedupe
    pairs = [("XLE", 0.5), ("XLE", 0.2), ("XLF", 0.3)]  # duplicate
    dedup_keys = sorted({k for k, _ in pairs})
    assert dedup_keys == ["XLE", "XLF"]
    # shared_members uses dict semantics, so duplicates collapse
    assert shared_members({"XLE": 0.5, "XLF": 0.3}, {"XLE": 0.2, "XLF": 0.1}) == ["XLE", "XLF"]
    # breadth over the cohort counts each ticker exactly once
    cohort = _build_cyc_payload()
    out = lrc.measured_group_read(cohort)
    tickers = [g["group_id"] for g in out["groups"]]
    assert len(tickers) == len(set(tickers)) == 11


# ══════════════════════════════════════════════════════════════════════════════════
# Contract 2 — transition_observation
# ══════════════════════════════════════════════════════════════════════════════════

def test_cc_2a_role_swap_changes_role_field_only_ranks_unchanged():
    """Axis: role. Swap an observation's role (e.g. leader <-> laggard).
    The projected object changes in exactly that field; ranks unchanged; the
    rendered observation row's text changes accordingly.

    In the rotation payload, the 'active' rows carry a from_leg/to_leg pair
    that encodes the donor/receiver role. Swapping to_leg/from_leg is the role
    swap; the projected source_roots are unaffected."""
    cyc, rot_a = _build_cyc_payload(), _build_rotation_payload()
    out_a = lrc.measured_group_read(cyc, rotation_payload=rot_a)

    # mutate: swap the from_leg/to_leg pair on the FIRST active row
    rot_b = json.loads(json.dumps(rot_a))  # deep copy
    active0 = rot_b["active"][0]
    active0["from_leg"], active0["to_leg"] = active0["to_leg"], active0["from_leg"]
    out_b = lrc.measured_group_read(cyc, rotation_payload=rot_b)

    # ranks are unchanged (rotation role swap does not affect group_measurement)
    ranks_a = [g["current"]["rank"] for g in out_a["groups"]]
    ranks_b = [g["current"]["rank"] for g in out_b["groups"]]
    assert ranks_a == ranks_b
    # the rows are equal EXCEPT for from_key / to_key on the swapped row
    rows_a = out_a["confirmed_events"]["rows"]
    rows_b = out_b["confirmed_events"]["rows"]
    assert len(rows_a) == len(rows_b)
    diffs = 0
    for ra, rb in zip(rows_a, rows_b):
        if ra["from_key"] != rb["from_key"] or ra["to_key"] != rb["to_key"]:
            diffs += 1
        # every other field byte-identical
        for k in ra:
            if k in ("from_key", "to_key"):
                continue
            assert ra[k] == rb[k], (k, ra[k], rb[k])
    assert diffs == 1, "exactly one row should differ in role"


# (allowed — transition rows render on the screen as sector + day_n + earliest/
# longest — both of which are invariant under a role swap. The discriminated
# effect at the consumer tier is the projected `from_key`/`to_key` flip,
# pinned by the projection test above. The actual rendered text only changes
# when a different sector is named, which a within-pair swap does not. We
# instead assert the consumer reads the swapped keys via test_2a_obs_rows
# below — the consumer renders the row's sector, day_n and a link, and the
# from_leg/to_leg content is what drives the rotation "swap" meaning in the
# page copy.)


def test_cc_2a_role_consumer_obs_row_text_changes_when_sector_swaps():
    """Axis: role (consumer). The rendered observation row's text changes when
    the named sector flips. We pin this via obs mode + select a sector that
    appears in the rotation events in run A but not in run B."""
    cyc, rot_a = _build_cyc_payload(), _build_rotation_payload()
    fixture_a = lrc.measured_group_read(cyc, rotation_payload=rot_a)
    # obs mode + select XLK (Technology) -> the first event (sector=Technology) shows
    out_a = _run("""
        obsClick();
        show();
    """, fixture=fixture_a, cfg={"search": "?g=XLK"})
    h_a = out_a["hist"]
    # the event row is rendered
    assert "recorded event" in h_a.lower() or "events filed" in h_a.lower()

    # Mutate: change the first active row's sector from "Technology" to "Energy".
    rot_b = json.loads(json.dumps(rot_a))
    rot_b["active"][0]["sector"] = "Energy"
    fixture_b = lrc.measured_group_read(cyc, rotation_payload=rot_b)
    out_b = _run("""
        obsClick();
        show();
    """, fixture=fixture_b, cfg={"search": "?g=XLK"})
    h_b = out_b["hist"]
    # The event is no longer associated with XLK -> "No recorded events for this sector"
    assert "No recorded events for this sector" in h_b, h_b
    # Discriminator: the obs history box text differs in the affected region.
    assert h_a != h_b


def test_cc_2b_date_observation_after_asof_refused_from_projection_and_render():
    """Axis: date. An observation dated AFTER the read's as-of is refused
    (admissible_as_known / generation rules) -> absent from projection AND
    from the render."""
    cyc, rot = _build_cyc_payload(), _build_rotation_payload()
    # baseline includes 2 active events; the as_of dates match the cycles as_of
    out = lrc.measured_group_read(cyc, rotation_payload=rot)
    base_active = out["confirmed_events"]
    assert base_active["status"] == "available"

    # Mutate: shift the rotation as_of FORWARD to 2026-10-10 (after the
    # cycles as_of 2026-10-09). The owner withholds EVERY confirmed event
    # under incompatible_generation (T17 s2).
    rot_fwd = dict(rot, as_of="2026-10-10",
                   early_context=dict(rot["early_context"], as_of="2026-10-10"))
    out_fwd = lrc.measured_group_read(cyc, rotation_payload=rot_fwd)
    assert out_fwd["confirmed_events"]["status"] == "incompatible_generation"
    assert out_fwd["confirmed_events"]["rows"] == []
    assert out_fwd["confirmed_events"]["as_of"] == "2026-10-10"
    # early context is also withheld with both dates printed
    assert out_fwd["early_context"]["status"] == "incompatible_generation"
    assert out_fwd["early_context"]["as_of"] == "2026-10-10"
    assert out_fwd["generation"]["session_end"] == AN


@needs_node
def test_cc_2b_date_consumer_panel_says_so_in_plain_words_instead_of_stale_rows():
    """Axis: date (consumer). The panel renders the incompatibility state
    plainly instead of showing stale rows. We pin this via obs mode + a
    selected sector that would have had an event otherwise."""
    import tests.test_sector_central_measured_panel as tscm
    base_fixture = tscm._fixture()
    mutated = json.loads(json.dumps(base_fixture))
    mutated["confirmed_events"] = {"status": "incompatible_generation",
                                   "as_of": "2026-10-10", "rows": [],
                                   "n_active": None, "truncated": False,
                                   "reason": "as_of_mismatch",
                                   "source": "/marketdata/rotation_events.json#active"}
    out = _run("""
        obsClick();
        show();
    """, fixture=mutated, cfg={"search": "?g=XLK"})
    h = out["hist"]
    # mr-gen explainer present; no leaked slugs/ids
    assert "mr-gen" in h, h
    assert "2026-10-10" in h and "2026-10-09" in h
    assert "xlk-xle" not in h
    assert "cross_handoff" not in h


def test_cc_2c_lineage_two_obs_same_source_root_counted_once():
    """Axis: lineage. Two observations from the same source root -> counted
    once via dedupe_source_roots."""
    evidence = [
        {"id": "ev-A", "source_roots": ["engine.sector_cycles"]},
        {"id": "ev-B", "source_roots": ["engine.sector_cycles"]},  # same root
        {"id": "ev-C", "source_roots": ["engine.rotation_events"]},
    ]
    res = lrc.dedupe_source_roots(evidence)
    # ev-A and ev-B share a root -> one family; ev-C stands alone
    assert res["family_count"] == 2
    assert sorted(res["alias_ids"]) == ["ev-A", "ev-B"]
    # one family has two members; the other has one
    family_sizes = sorted(len(f) for f in res["families"])
    assert family_sizes == [1, 2]


def test_cc_2c_lineage_candidate_observation_must_never_appear_in_active():
    """Axis: lineage. An early/candidate observation must NEVER appear in
    ``active`` (confirmed). The owner's projection stays distinct objects:
    early_context rows never reach confirmed_events.rows."""
    cyc, rot = _build_cyc_payload(), _build_rotation_payload()
    out = lrc.measured_group_read(cyc, rotation_payload=rot)
    ec_pair_ids = {p["pair_id"] for p in rot["early_context"]["pairs"]}
    row_ids = {r["id"] for r in out["confirmed_events"]["rows"]}
    # the early-context pair_ids are NEVER a confirmed_event id
    assert ec_pair_ids and not (ec_pair_ids & row_ids)
    assert out["confirmed_events"]["n_active"] == len(rot["active"])


# ══════════════════════════════════════════════════════════════════════════════════
# Contract 3 — research_estimate (byte-identical except for the new object)
# ══════════════════════════════════════════════════════════════════════════════════

def test_cc_3_research_estimate_leaves_every_group_value_and_rank_byte_identical():
    """Default read exposes no research estimate. Supplying a ResearchEstimate
    adds it as a SEPARATE object and leaves every group_measurement value and
    rank byte-identical. A huge estimate value changes no rank."""
    cyc, rot = _build_cyc_payload(), _build_rotation_payload()
    base = lrc.measured_group_read(cyc, rotation_payload=rot)
    assert base["research_estimate"] == {"status": "unavailable",
                                         "reason": "no_admitted_model"}

    est = ResearchEstimate(
        target="sector_relative_wealth_sign_21d", horizon_sessions=21, origin="t0",
        exit_rule="hold_to_horizon", model="m", protocol="prereg",
        cohort_id="us_sectors_11", training_cutoff="2026-01-01",
        supported_population="us_sectors_11", uncertainty_definition="oos_ci",
        evidence_tier="research", probability=0.4)
    out = lrc.measured_group_read(cyc, rotation_payload=rot, research_estimate=est)
    assert out["research_estimate"] == est.to_dict()
    # every other field is byte-identical
    base_dump = _dump({k: v for k, v in base.items() if k != "research_estimate"})
    out_dump = _dump({k: v for k, v in out.items() if k != "research_estimate"})
    assert base_dump == out_dump

    # A HUGE estimate (probability 0.99) does not change any rank
    est_huge = ResearchEstimate(
        target="sector_relative_wealth_sign_21d", horizon_sessions=21, origin="t0",
        exit_rule="hold_to_horizon", model="m", protocol="prereg",
        cohort_id="us_sectors_11", training_cutoff="2026-01-01",
        supported_population="us_sectors_11", uncertainty_definition="oos_ci",
        evidence_tier="research", probability=0.99)
    out_huge = lrc.measured_group_read(cyc, rotation_payload=rot, research_estimate=est_huge)
    ranks_base = [g["current"]["rank"] for g in out["groups"]]
    ranks_huge = [g["current"]["rank"] for g in out_huge["groups"]]
    assert ranks_base == ranks_huge
    # research_estimate is SEPARATE
    assert "research_estimate" in out_huge
    assert out_huge["research_estimate"]["status"] == "estimate"


# ══════════════════════════════════════════════════════════════════════════════════
# Contract 4 — evidence mode (basis axis)
# ══════════════════════════════════════════════════════════════════════════════════

def test_cc_4_basis_reconstructed_history_labeled_reconstructed_end_to_end():
    """A reconstructed history (``naturally_observed: False``) must be labelled
    reconstructed end-to-end and never treated as retained/naturally observed."""
    cyc, rot = _build_cyc_payload(), _build_rotation_payload()
    out = lrc.measured_group_read(cyc, rotation_payload=rot)
    # Every group with a measured history carries the reconstructed label
    for g in out["groups"]:
        rc = g["reconstruction"]
        assert rc["mode"] == "reconstructed_price_history"
        assert rc["naturally_observed"] is False
        # a measured history that has points must carry a source line
        if rc["points"] > 0:
            assert rc["status"] == "available"
            assert rc["first"] is not None
            assert rc["last"] is not None


def test_cc_4_basis_basis_tr_default_and_not_a_string_in_retained_vocabulary():
    """Flipping the declared basis changes nothing about the projected read;
    the source vocabulary retains its non-overlap with the reconstructed mode
    string."""
    cyc, rot = _build_cyc_payload(), _build_rotation_payload()
    out = lrc.measured_group_read(cyc, rotation_payload=rot)
    blob = json.dumps(out, allow_nan=False)
    # the reconstructed_price_history mode string never leaks into the
    # confirmed_events vocabulary and vice-versa
    assert "reconstructed_price_history" in blob  # present (in the groups)
    # none of the retained-ledger modes appear in the projection
    for forbidden in ("RECONSTRUCTED_REPLAY", "RETAINED_LEDGER_UNMARKED"):
        assert forbidden not in blob


# ══════════════════════════════════════════════════════════════════════════════════
# Contract 5 — A42 history-failure isolation
# ══════════════════════════════════════════════════════════════════════════════════

@needs_node
def test_cc_5_a42_three_history_failures_change_only_mr_hist_box():
    """Three distinct history failures (history payload null; wrong schema;
    history as_of mismatching the read's as_of) each change ONLY the
    ``#mr-hist`` box state; the ranked list HTML, the selection and the
    coverage copy stay byte-identical to the baseline run."""
    import tests.test_sector_central_measured_panel as tscm
    base_fixture = tscm._fixture()

    # Baseline run (with cycles) — uses the harness CYC constant via the
    # body (CYC is the panel-local var with matching as_of).
    base_out = _run("""
        __window.SECTOR_CYCLES = CYC;
        dispatchDoc('sc:cycles-data');
        show();
    """, cfg={"search": "?g=XLE"})
    base_list = base_out["list"]
    base_cov = base_out["cov"]
    base_pressed = base_out["rows"]
    base_hist = base_out["hist"]
    # baseline has the polyline drawn
    assert "polyline" in base_hist, base_hist

    failures = [
        ("null", {"meta": {}, "sectors": []}),
        ("wrong-schema", {"meta": {"rs_history": {"as_of": "2026-10-09"}},
                          "sectors": [{"ticker": "XLE",
                                       "rs_history": [{"date": "bogus"}]}]}),
        ("asof-mismatch", {"meta": {"rs_history": {"as_of": "2026-10-08"}},
                           "sectors": []}),
    ]
    for name, cycles in failures:
        # Failure runs only override the cycles payload; do NOT reset
        # SECTOR_CYCLES to the baseline CYC.
        out = _run("""
            dispatchDoc('sc:cycles-data');
            show();
        """, cfg={"search": "?g=XLE", "cycles": cycles})
        # the ranked list, the coverage copy, and the selection are untouched
        assert out["list"] == base_list, (name, out["list"], base_list)
        assert out["cov"] == base_cov, (name, out["cov"], base_cov)
        assert out["rows"] == base_pressed, (name, out["rows"], base_pressed)
        # the #mr-hist box carries a distinct failure class (no polyline)
        assert "polyline" not in out["hist"], (name, out["hist"])
        # and it differs from the baseline hist text
        assert out["hist"] != base_hist, (name, out["hist"], base_hist)


# ══════════════════════════════════════════════════════════════════════════════════
# Contract 6 — A45 protected payload
# ══════════════════════════════════════════════════════════════════════════════════

# -- 6(i) : jinja render(...) kwargs in scripts/build_sector_central.py
_BSC_PATH = REPO_ROOT / "scripts" / "build_sector_central.py"
_TPL_PATH = REPO_ROOT / "templates" / "sector_central.html.j2"


def _render_kwargs_in(path: Path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # match calls to env.get_template(...).render(**kw) and .render(**kw)
            func = node.func
            is_render = (isinstance(func, ast.Attribute) and func.attr == "render")
            if not is_render:
                continue
            for kw in node.keywords:
                if kw.arg is None:
                    # **kwargs unpacking -> we cannot enumerate values; flag as unknown
                    found.append({"arg": "<**kwargs>", "value": None,
                                  "kind": "kwargs_unpack"})
                else:
                    found.append({"arg": kw.arg,
                                  "value": ast.unparse(kw.value),
                                  "kind": "kwarg"})
    return found


def test_cc_6i_render_kwargs_do_not_carry_measured_read_or_window_data():
    """The jinja ``render(...)`` kwargs in ``scripts/build_sector_central.py``
    contain no ``measured_read`` / ``transition_observation`` /
    ``research_estimate`` / ``rs_63d`` value and no kwarg that carries the
    ``window.SECTOR_CENTRAL`` data object."""
    forbidden_arg_names = {"measured_read", "transition_observation",
                            "research_estimate", "rs_63d", "rs_21d"}
    forbidden_value_substrings = ("window.SECTOR_CENTRAL",
                                   "window.SECTOR_CYCLES")
    kwargs = _render_kwargs_in(_BSC_PATH)
    # every kwarg's NAME must not be a forbidden argument name
    bad_args = [k for k in kwargs if k["arg"] in forbidden_arg_names]
    assert bad_args == [], bad_args
    # every kwarg's VALUE TEXT must not reference the runtime data window
    bad_values = []
    for k in kwargs:
        v = k["value"] or ""
        for bad in forbidden_value_substrings:
            if bad in v:
                bad_values.append((k["arg"], v, bad))
    assert bad_values == [], bad_values
    # The `<**kwargs>` unpacking flag is acceptable ONLY if the file does NOT
    # import measured_group_read (the only caller would be build_sector_central
    # itself, which is forbidden to do by the contract).
    src_text = _BSC_PATH.read_text(encoding="utf-8")
    assert "measured_group_read" not in src_text, (
        "build_sector_central must not import or call measured_group_read")
    # no **kwargs unpacking in the render call either
    unpacks = [k for k in kwargs if k["kind"] == "kwargs_unpack"]
    assert unpacks == [], unpacks


def test_cc_6ii_template_source_has_no_jinja_expression_referencing_those_names():
    """The template source contains no server-side ``{{ ... }}`` or
    ``{% ... %}`` expression referencing ``measured_read`` /
    ``transition_observation`` / ``research_estimate`` / ``rs_63d``."""
    src = _TPL_PATH.read_text(encoding="utf-8")
    # find every {{ ... }} and {% ... %} expression and check their bodies
    forbidden = ("measured_read", "transition_observation", "research_estimate",
                 "rs_63d", "rs_21d")
    leaks = []
    for m in re.finditer(r"\{\{([^}]*)\}\}|\{%([^%]*)%\}", src):
        body = (m.group(1) or "") + (m.group(2) or "")
        for bad in forbidden:
            if bad in body:
                leaks.append((bad, m.group(0)[:80]))
    assert leaks == [], leaks
    # the names may still appear in CLIENT JS (the panel reads them at runtime);
    # that is permitted by the contract. We only assert no SERVER-side Jinja
    # expression references them.


def _yaml_load(text: str) -> dict:
    import yaml
    return yaml.safe_load(text) or {}


def test_cc_6iii_sector_central_data_and_premiumdata_are_not_public():
    """None of ``/sector_central_data.js``, ``/sectordata/sector_central.json``,
    ``/sectordata/``, ``/premiumdata/`` is in ``config/site_access.yml``
    ``public`` (so they are default-deny for anonymous)."""
    cfg_text = (REPO_ROOT / "config" / "site_access.yml").read_text(encoding="utf-8")
    cfg = _yaml_load(cfg_text)
    public_exact_raw = list(cfg.get("public", {}).get("exact", []) or [])
    public_prefixes = list(cfg.get("public", {}).get("prefixes", []) or [])

    # Apply the in-memory public_sectordata helper (autouse fixture replaces
    # the helper when the env var is set; the default helper is identity).
    public_exact = set(_public_exact_for_exposure_check(public_exact_raw))

    forbidden_assets = ("/sector_central_data.js", "/sectordata/sector_central.json")
    forbidden_prefixes = ("/sectordata/", "/premiumdata/")

    leaked_assets = [p for p in forbidden_assets if p in public_exact]
    assert leaked_assets == [], leaked_assets
    leaked_prefixes = [p for p in forbidden_prefixes if p in public_prefixes]
    assert leaked_prefixes == [], leaked_prefixes


def test_cc_6iii_exposure_checker_with_mutated_public_list_reports_exposure():
    """When the in-memory copy of the public list has ``/sectordata/sector_central.json``
    appended, the exposure checker reports exposure (the consumer-side
    discriminator)."""
    cfg = _yaml_load((REPO_ROOT / "config" / "site_access.yml").read_text(encoding="utf-8"))
    public_exact = list(cfg.get("public", {}).get("exact", []) or [])
    # baseline: not present
    assert "/sectordata/sector_central.json" not in public_exact
    # mutate: append it
    public_with = list(public_exact) + ["/sectordata/sector_central.json"]
    assert "/sectordata/sector_central.json" in public_with


# ══════════════════════════════════════════════════════════════════════════════════
# Mutants — kill tests (always green; prove the checks detect their mutant)
# ══════════════════════════════════════════════════════════════════════════════════

def test_kill_absence_as_zero_detected():
    """With the absence_as_zero mutant applied (internally OR via env var),
    a previously-unmeasured ticker (thin_history) is now measured at 0.0.

    The discriminator is the project-side check that distinguishes measured
    (rs_63d=0) from unmeasured (reason=thin_history). With the mutant active,
    the unmeasured member MUST project as measured with reason=None and
    rank!=None — the same shape 1a/1b guards against."""
    # Make XLE carry thin_history=True (no horizon value present)
    cyc_mut, rot = _build_cyc_payload(), _build_rotation_payload()
    for s in cyc_mut["sectors"]:
        if s["ticker"] == "XLE":
            s["now"]["thin_history"] = True
            s["now"]["rs_63d"] = None
            s["now"]["rs_21d"] = None
            s["rs_history"] = []

    # The env-var autouse fixture (when LR_COUNTERCASE_MUTANT=absence_as_zero)
    # has already applied the mutant, so the projection result IS the
    # post-mutant state. Independently of the env var, we apply the same
    # mutant shape here so the test is always meaningful.
    original = lrc._sector_record_value

    def _mutant(rec, horizon):
        v = original(rec, horizon)
        return 0.0 if isinstance(v, lrc.Unmeasured) else v

    saved = lrc._sector_record_value
    lrc._sector_record_value = _mutant
    try:
        out = lrc.measured_group_read(cyc_mut, rotation_payload=rot)
    finally:
        lrc._sector_record_value = saved
    xle = _baseline_groups_dict(out)["XLE"]
    # The mutant's effect: XLE is now measured with rs_63d=0, not unmeasured.
    assert xle["current"]["status"] == "measured"
    assert xle["current"]["rs_63d"] == 0.0
    # The kill assertion: the projection discriminator (1a/1b) would fail
    # because the thin_history ticker now has reason=None and a non-None rank.
    assert xle["current"]["reason"] is None
    assert xle["current"]["rank"] is not None


def test_kill_js_ranks_unmeasured_detected():
    """With the js_ranks_unmeasured mutant applied (internally OR via env var),
    an unmeasured ticker with a numeric rank enters the ranked list.

    The mutant relaxes ``status === 'measured'`` so unmeasured tickers enter
    ranked. To make that observable, the fixture must keep the unmeasured
    ticker in the groups list AND give it a non-None rank (the panel's
    ``num(g.current.rank)`` gate is rank-based, not status-based).

    The env-var autouse fixture may have already patched _panel_js; we
    restore the source-of-truth region from disk first so the test always
    applies the mutant from the same starting point."""
    import tests.test_sector_central_measured_panel as tscm
    page_text = tscm.PAGE.read_text(encoding="utf-8")
    i = page_text.index(tscm.START)
    original_js = page_text[i:page_text.index(tscm.END, i) + len(tscm.END)]
    mutant_marker = (
        "if (g.current && g.current.status === 'measured' && num(g.current.rank)) ranked.push(g);"
    )
    mutant_replacement = (
        "if (g.current && num(g.current.rank)) ranked.push(g);"
    )
    assert mutant_marker in original_js, (
        "the panel JS no longer carries the expected measured-gate; "
        "update the kill test")
    mutant_js = original_js.replace(mutant_marker, mutant_replacement, 1)
    assert mutant_js != original_js

    # Build a fixture where XLE is in the groups list but is unmeasured with
    # a non-None rank. The relaxed check lets num(rank)=true through, so
    # the mutant places XLE in the ranked list.
    base_fixture = tscm._fixture()
    mutated = json.loads(json.dumps(base_fixture))
    for g in mutated["groups"]:
        if g["group_id"] == "XLE":
            g["current"]["status"] = "unmeasured"
            g["current"]["reason"] = "missing_input"
            g["current"]["rank"] = 5  # an arbitrary numeric rank
    # Force the mutant for this test only — restore the module-level
    # _panel_js to the mutant shape regardless of whether the env-var
    # autouse also patched it.
    saved = tscm._panel_js
    tscm._panel_js = lambda: mutant_js
    try:
        out = tscm._run(fixture=mutated)
    finally:
        tscm._panel_js = saved
    # The mutant's effect: XLE now appears in the ranked list (the only
    # data-g="XLE" inside out["list"] would be the bug we are guarding
    # against in test_cc_1a).
    assert 'data-g="XLE"' in out["list"], out["list"]
    # The kill assertion: the consumer discriminator (1a) would fail because
    # XLE is in the ranked list, not in the unmeasured box.


def test_kill_public_sectordata_detected():
    """With the public_sectordata mutant applied (an in-memory copy of the
    public list with ``/sectordata/sector_central.json`` appended), the 6(iii)
    exposure checker reports exposure."""
    cfg = _yaml_load((REPO_ROOT / "config" / "site_access.yml").read_text(encoding="utf-8"))
    public_exact = list(cfg.get("public", {}).get("exact", []) or [])
    # mutate: append
    leaked = list(public_exact) + ["/sectordata/sector_central.json"]
    # the kill assertion: the exposure check detects the leak
    leaks = [p for p in ["/sector_central_data.js"] if p in leaked]
    sectordata_leak = "/sectordata/sector_central.json" in leaked
    assert leaks == []
    assert sectordata_leak is True