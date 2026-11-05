"""The C1 fusion ranker and the retired v2 shadow — the 2026-08-15 Chairman override.

The suite is organised around the four claims the override rests on, because each one
is a place a plausible-looking implementation could be quietly wrong:

  1. THE PORT IS AN EXTRACTION.  `engine.us_prophet_fusion.aggregate` reproduces
     `scripts.prophet_fusion_race.build_c1` on the frozen research frame.  Without this
     the "deterministic C1 already specified by the workstream" is just a new model
     wearing C1's name.
  2. THE INPUTS ARE THE SAME INPUTS.  `extract_members` reads each member off a live
     board row exactly as `grade_us_board._row_features` reads it into the graded frame.
     Exact arithmetic over drifted inputs is the subtler half of the same mistake.
  3. THE FREEZE HELD.  `legacy_v2_values` reproduces scores the board actually
     PUBLISHED, byte-exact, on the committed artifact.
  4. THE SHADOW HAS NO AUTHORITY, AND A DEGRADED NIGHT SAYS SO.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine import sue as sue_engine
from engine import us_board_rank as ubr
from engine import us_prophet_fusion as fus

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "site" / "factordata" / "us_standouts.json"


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

def _row(ticker, *, alpha=1.0, off_high=-5.0, tier="T2", status="buy_now",
         sue_z=None, sue_fresh_days=None, smartmoney=False, insiders=0,
         gex="neutral", news=0, ext_z=0.5, **extra):
    row = {
        "ticker": ticker,
        "alpha": alpha,
        "off_high": off_high,
        "signal": {"tier_cascade": tier, "ticks": 1, "tier": tier},
        "entry_signal": {"status": status},
        "smartmoney_chip": smartmoney,
        "insider_buyers": insiders,
        "gex_confirm": {"verdict": gex},
        "news_burst": {"n_recent": news},
        "ext_z": ext_z,
        "label": "BUY ZONE",
    }
    if sue_z is not None:
        row["sue_z"] = sue_z
        row["sue_fresh_days"] = sue_fresh_days if sue_fresh_days is not None else 10
    row.update(extra)
    return row


@pytest.fixture(scope="module")
def committed_board():
    if not BOARD.exists():
        pytest.skip("committed board artifact not present")
    return json.loads(BOARD.read_text())


# --------------------------------------------------------------------------- #
# 1. the port is an extraction
# --------------------------------------------------------------------------- #

@pytest.mark.needs_full_checkout("data")
class TestByteParityWithTheRacedC1:
    """`aggregate` IS `build_c1`, proven on the frame the race was run on.

    THE WHOLE OVERRIDE RESTS HERE.  The commissioning says to port "the exact
    deterministic C1-as-raced family aggregation", and the only way to show a port is
    exact is to run both and compare, not to read both and agree.  The research module
    is imported by this TEST and by nothing in `engine/` — that boundary is the point of
    the extraction, and `TestProductionNeverImportsResearch` below pins it.

    The floors are evaluated over the WHOLE frame here, because that is what PR-1b's
    race did.  Production evaluates the same code over one night; see
    `TestAsOfNightFloors`.
    """

    @pytest.fixture(scope="class")
    def raced(self):
        pytest.importorskip("pandas")
        try:
            from scripts import prophet_fusion_race as race
        except Exception as exc:                          # pragma: no cover
            pytest.skip(f"race harness unavailable: {exc}")
        try:
            frame = race.build_race_frame()
        except Exception as exc:                          # pragma: no cover
            pytest.skip(f"graded board frame unavailable: {exc}")
        return race, frame, race.build_c1(frame, race.load_registry())

    @staticmethod
    def _rows(frame):
        import numpy as np

        cols = sorted(fus.REGISTERED_SIGNS)
        out = []
        for _, r in frame.features.iterrows():
            values = {}
            for c in cols:
                v = r[c] if c in frame.features.columns else None
                if v is None or (isinstance(v, float) and np.isnan(v)):
                    v = None
                values[c] = v
            out.append((str(r["date"]), values))
        return out

    def test_the_same_members_survive_the_same_floor(self, raced):
        _race, frame, c1 = raced
        admitted = fus.admit_members(self._rows(frame), apply_variance_floor=False)
        assert set(admitted.admitted) == {
            m["column"] for m in c1.membership["members_raced"]}
        assert {d["column"] for d in admitted.dropped} == {
            d["column"] for d in c1.membership["members_dropped"]}

    def test_the_same_families_vote(self, raced):
        _race, frame, c1 = raced
        rows = self._rows(frame)
        admitted = fus.admit_members(rows, apply_variance_floor=False)
        one_date = [v for d, v in rows if d == rows[0][0]]
        plane = fus.aggregate(one_date, admitted.admitted)
        assert plane.families_present == c1.membership["families_present"]

    def test_every_family_score_and_every_c1_score_matches(self, raced):
        """Per ROW, not per aggregate — an aggregate can match while rows disagree."""
        import numpy as np

        _race, frame, c1 = raced
        rows = self._rows(frame)
        admitted = fus.admit_members(rows, apply_variance_floor=False)

        by_date: dict[str, list[tuple[int, dict]]] = {}
        for i, (date, values) in enumerate(rows):
            by_date.setdefault(date, []).append((i, values))

        scores: list[float | None] = [None] * len(rows)
        fams: list[dict] = [{}] * len(rows)
        for _date, items in by_date.items():
            plane = fus.aggregate([v for _i, v in items], admitted.admitted)
            for slot, (i, _v) in enumerate(items):
                scores[i] = plane.scores[slot]
                fams[i] = plane.family_scores[slot]

        raced_scores = c1.rung.scores.reset_index(drop=True)
        raced_fams = c1.family_scores.reset_index(drop=True)
        assert len(raced_scores) == len(rows)

        worst_score, worst_family = 0.0, 0.0
        for i in range(len(rows)):
            a = raced_scores.loc[i, "score"]
            a_null = a is None or (isinstance(a, float) and np.isnan(a))
            assert a_null == (scores[i] is None), f"null disagreement at row {i}"
            if not a_null:
                # x100 is the production SCALE, not a change to the construction.
                worst_score = max(worst_score, abs(float(a) * 100.0 - scores[i]))
            for family in c1.membership["families_present"]:
                b = raced_fams.loc[i, family]
                b_null = b is None or (isinstance(b, float) and np.isnan(b))
                assert b_null == (family not in fams[i]), (family, i)
                if not b_null:
                    worst_family = max(worst_family, abs(float(b) - fams[i][family]))

        # Float ASSOCIATIVITY only: pandas sums a column, this sums a list.  Anything
        # above ~1e-9 is a construction difference, not a rounding one.
        assert worst_family < 1e-12, worst_family
        assert worst_score < 1e-10, worst_score


class TestProductionNeverImportsResearch:
    def test_the_engine_module_imports_nothing_from_scripts_or_research(self):
        """The nightly may not depend on a research harness — the reason the port
        exists at all.  Read as TEXT rather than by import so a lazily-imported name
        inside a function body cannot slip past."""
        source = (ROOT / "engine" / "us_prophet_fusion.py").read_text()
        for banned in ("from scripts", "import scripts", "from research",
                       "import research", "prophet_fusion_race", "prophet_fusion_arena"):
            for line in source.splitlines():
                stripped = line.strip()
                if stripped.startswith(("#", '"', "'")) or "``" in line:
                    continue                       # prose citing the provenance is fine
                assert banned not in stripped, f"{banned!r} in: {line}"


# --------------------------------------------------------------------------- #
# 2. the inputs are the same inputs
# --------------------------------------------------------------------------- #

class TestExtractionMirrorsTheGradedFrame:
    """`extract_members` reads what `grade_us_board._row_features` reads.

    A drift here is invisible to every parity test above — the arithmetic would stay
    exact while the numbers going into it came from somewhere else.
    """

    @pytest.fixture(scope="class")
    def graded(self):
        pytest.importorskip("pandas")
        try:
            from scripts import grade_us_board
        except Exception as exc:                          # pragma: no cover
            pytest.skip(f"grader unavailable: {exc}")
        return grade_us_board

    @pytest.mark.parametrize("row", [
        _row("A", sue_z=1.5, sue_fresh_days=10, smartmoney=True, insiders=3,
             gex="confirm", news=5),
        _row("B", alpha=None, off_high=None, tier=None, sue_z=None,
             smartmoney=False, insiders=1, gex=None, news=2),
        _row("C", sue_z=1.5, sue_fresh_days=90, insiders=2, gex="caution", news=3),
        {"ticker": "D"},                                   # a bare row: every field absent
    ])
    def test_each_member_matches_the_graders_derivation(self, graded, row):
        mine = fus.extract_members(row, (row.get("signal") or {}))
        theirs = graded._row_features(dict(row)) if hasattr(
            graded, "_row_features") else None
        if theirs is None:                                 # pragma: no cover
            pytest.skip("_row_features is not exposed")
        for column in ("alpha", "off_high", "tier_cascade", "sue_fresh",
                       "smartmoney_add", "insider_cluster", "gex_confirm_verdict",
                       "news_burst"):
            assert mine[column] == theirs.get(column), column


class TestPercentileSemantics:
    def test_average_ties_and_pct_over_the_non_null_count(self):
        # 3 present values with a tie: ranks 1, 2.5, 2.5 over n=3.
        assert fus.percentile_rank([1.0, 2.0, 2.0]) == pytest.approx(
            [1 / 3, 2.5 / 3, 2.5 / 3])

    def test_nulls_stay_null_and_do_not_enter_the_denominator(self):
        """A missing member ABSTAINS.  Handing it the mid-pool 0.5 would make a
        no-vote indistinguishable from a neutral vote, which is the exact confusion
        the abstention law exists to prevent."""
        out = fus.percentile_rank([1.0, None, 2.0])
        assert out[1] is None
        assert out == pytest.approx([0.5, None, 1.0])      # n == 2, not 3

    def test_all_null_is_all_null_not_all_zero(self):
        assert fus.percentile_rank([None, None]) == [None, None]

    @pytest.mark.needs_full_checkout("data")
    def test_it_matches_pandas_rank_pct_average(self):
        pd = pytest.importorskip("pandas")
        import numpy as np

        values = [3.0, 1.0, None, 1.0, 7.5, None, 0.0]
        expect = pd.Series([np.nan if v is None else v for v in values]).rank(
            pct=True, method="average")
        got = fus.percentile_rank(values)
        for i, v in enumerate(got):
            if v is None:
                assert bool(np.isnan(expect[i]))
            else:
                assert v == pytest.approx(float(expect[i]))


class TestOrientation:
    def test_an_unmapped_token_is_unmeasured_not_a_zero(self):
        """`gex_confirm` has no 'infirm' value.  A vocabulary miss must abstain — a
        zero would be a NEUTRAL vote cast on the strength of a producer typo."""
        sign = fus.REGISTERED_SIGNS["gex_confirm_verdict"]
        assert fus.oriented_value("infirm", sign) is None
        assert fus.oriented_value("neutral", sign) == 0.0
        assert fus.oriented_value("caution", sign) == -1.0

    def test_a_bool_on_a_continuous_member_is_not_one_point_zero(self):
        assert fus.oriented_value(True, fus.REGISTERED_SIGNS["alpha"]) is None

    def test_tier_reads_the_gates_cascade_order(self):
        sign = fus.REGISTERED_SIGNS["tier_cascade"]
        order = [fus.oriented_value(t, sign) for t in ("T2", "T1", "T3", "T4")]
        assert order == sorted(order, reverse=True), "T2 > T1 > T3 > T4"


# --------------------------------------------------------------------------- #
# the floors, evaluated AS OF NIGHT
# --------------------------------------------------------------------------- #

class TestAsOfNightFloors:
    def test_a_constant_member_is_vote_inert_even_at_full_presence(self):
        """The whole point of the variance axis: presence 100%, information 0.

        This is the shape PR-1b measured and could not act on — a column present on
        every row whose within-date percentile is a constant.  A presence floor admits
        it; the variance floor stands it down and SAYS SO.
        """
        rows = [{"flag": True}, {"flag": True}, {"flag": True}]
        sign = fus.RegisteredSign(column="flag", family="F8_ATTENTION_CROWDING",
                                  sign=+1, kind="flag", source="test")
        out = fus.admit_members([("n", r) for r in rows], signs={"flag": sign})
        assert out.admitted == ()
        (drop,) = out.dropped
        assert drop["reason"] == "vote_inert"
        assert drop["coverage"] == 1.0

    def test_a_sparse_but_variable_member_passes(self):
        """The registered acceptance test: an event flag firing on a few percent of
        rows is sparse, not inert, and must keep its vote."""
        rows = [{"flag": i == 0} for i in range(40)]
        sign = fus.RegisteredSign(column="flag", family="F8_ATTENTION_CROWDING",
                                  sign=+1, kind="flag", source="test")
        out = fus.admit_members([("n", r) for r in rows], signs={"flag": sign})
        assert out.admitted == ("flag",)

    def test_a_single_row_pool_does_not_manufacture_inertness(self):
        """A pool of one cannot carry variation for ANY member.  Counting that as a
        failed date would refuse the whole plane and stamp a legitimately tiny board
        as a degraded one — an outage invented out of a small board."""
        sign = fus.RegisteredSign(column="flag", family="F8_ATTENTION_CROWDING",
                                  sign=+1, kind="flag", source="test")
        out = fus.admit_members([("n", {"flag": True})], signs={"flag": sign})
        assert out.admitted == ("flag",)

    def test_the_presence_floor_is_measured_on_tonight_not_on_history(self):
        """`tier_cascade` sat at 0.25 coverage over the frozen 24-date frame and drops
        there; on a live buy pool every row carries a cascade verdict and it votes.
        Same code, same threshold, different frame — which is the entire prospective
        fix (#5700 left this unimplemented and PR-3 inherited it)."""
        live = [{"tier_cascade": t} for t in ("T1", "T2", "T3")] * 5
        out = fus.admit_members([("tonight", r) for r in live])
        assert "tier_cascade" in out.admitted
        thin = live + [{"tier_cascade": None}] * 60
        out2 = fus.admit_members([("tonight", r) for r in thin])
        (drop,) = [d for d in out2.dropped if d["column"] == "tier_cascade"]
        assert drop["reason"] == "below_presence_floor"


class TestNullIsNotZero:
    def test_a_row_no_family_can_speak_to_scores_null(self):
        plane = fus.aggregate([{"alpha": 1.0}, {"alpha": 2.0}, {"alpha": None}],
                              ["alpha"])
        assert plane.scores[2] is None
        assert plane.family_scores[2] == {}

    def test_an_absent_family_is_listed_with_a_reason(self):
        plane = fus.aggregate([{"alpha": 1.0}, {"alpha": 2.0}], ["alpha"])
        absent = {f["family"]: f["reason"] for f in plane.families_absent}
        assert "F6_MACRO_REGIME" in absent
        assert "STRUCTURALLY EXCLUDED" in absent["F6_MACRO_REGIME"]
        assert "F4_CATALYST_EVENT" in absent and absent["F4_CATALYST_EVENT"]

    def test_zero_families_refuses_rather_than_returning_zeros(self):
        with pytest.raises(fus.FusionUnavailable):
            fus.aggregate([{"alpha": 1.0}], [])


class TestTheFence:
    @pytest.mark.parametrize("column", sorted(fus.FORBIDDEN_INPUTS))
    def test_a_composite_or_a_count_refuses_by_name(self, column):
        sign = fus.RegisteredSign(column=column, family="F2_MOMENTUM_EXTENSION",
                                  sign=+1, kind="continuous", source="test")
        with pytest.raises(fus.ForbiddenCompositeRefusal):
            fus.aggregate([{column: 1.0}], [column], signs={column: sign})

    def test_no_registered_member_is_a_forbidden_input(self):
        assert not (set(fus.REGISTERED_SIGNS) & fus.FORBIDDEN_INPUTS)

    def test_every_registered_member_homes_in_exactly_one_family(self):
        """One column, one home — a second membership is the anti-double-count budget
        defeated by registration."""
        homes: dict[str, set[str]] = {}
        for column, sign in fus.REGISTERED_SIGNS.items():
            homes.setdefault(column, set()).add(sign.family)
        assert all(len(v) == 1 for v in homes.values())
        assert set(s.family for s in fus.REGISTERED_SIGNS.values()) <= set(
            fus.FAMILY_KEYS)

    def test_duplicate_members_collapse_inside_a_family_instead_of_double_voting(self):
        """Agreement inside a family is ONE fact, not two."""
        a = fus.RegisteredSign(column="a", family="F2_MOMENTUM_EXTENSION", sign=+1,
                               kind="continuous", source="test")
        b = fus.RegisteredSign(column="b", family="F2_MOMENTUM_EXTENSION", sign=+1,
                               kind="continuous", source="test")
        rows = [{"a": 1.0, "b": 10.0}, {"a": 2.0, "b": 20.0}]
        plane = fus.aggregate(rows, ["a", "b"], signs={"a": a, "b": b})
        assert [c["column"] for c in plane.members_collapsed] == ["b"]
        assert plane.members_collapsed[0]["duplicate_of"] == "a"
        # b contributed nothing: the family score is a's percentile alone.
        assert plane.family_scores[1]["F2_MOMENTUM_EXTENSION"] == pytest.approx(1.0)


# --------------------------------------------------------------------------- #
# 3. the freeze held
# --------------------------------------------------------------------------- #

@pytest.mark.needs_full_checkout("site")
class TestLegacyV2ByteParity:
    def test_the_frozen_scorer_reproduces_every_published_score(self, committed_board):
        """Published prophet_shadow scores on the committed v3 board, replayed.

        The board ranks by us_prophet_v3; the retired scorer lives on
        prophet_shadow as us_prophet_v2_shadow. Comparing published prophet.score
        (C1) against the frozen v2 replay is the v2-board contract and fails
        the moment the artifact flips — DAR's published prophet 63.9 vs
        replayed shadow 80.5. If the shadow drifts, the "old" column of every
        before/after comparison is a comparison against nothing — the same
        failure the race harness's own replay gate refuses to emit results
        behind.
        """
        buy = committed_board.get("buy") or []
        assert buy, "fixture must carry a buy lane"
        gate = json.loads(
            (ROOT / "site" / "factordata" / "signal_gate.json").read_text())
        verdicts = gate.get("verdicts") or {}

        rows = [dict(r) for r in buy]
        published = {str(r["ticker"]): float((r.get("prophet_shadow") or {})["score"])
                     for r in buy}
        for r in rows:
            for key in ("prophet", "prophet_shadow", "score_rank", "display_rank",
                        "featured", "featured_blocked_by", "stage"):
                r.pop(key, None)

        scored = ubr.score_rows(rows, verdict_by=verdicts,
                                board_asof=committed_board.get("as_of"),
                                bottom_watch_stage=ubr.STAGE_BASING)
        for row in scored:
            replayed = row["prophet_shadow"]["score"]
            assert replayed == pytest.approx(published[str(row["ticker"])], abs=1e-9), (
                row["ticker"])

    def test_the_comparison_script_runs_and_refuses_on_drift(self, committed_board):
        from scripts import us_prophet_fusion_compare as cmp_mod

        report = cmp_mod.compare(top=30)
        assert report["old_definition"] == ubr.SHADOW_DEFINITION == "us_prophet_v2_shadow"
        assert report["new_definition"] == ubr.BOARD_DEFINITION
        assert len(report["new_top"]) == 30
        assert report["fusion_receipt"]["families_active"]
        # Every row carries the receipt the acceptance surface promises.
        for row in report["new_top"]:
            assert row["why"]
            assert row["v2_rank"] and row["new_rank"]
            assert row["n_families"] == len(row["family_contribution"])

    def test_the_comparison_survives_the_board_it_is_run_on_becoming_v3(
            self, committed_board, tmp_path, monkeypatch):
        """The acceptance surface must still work once the board IS the new ranker.

        THE TRAP THIS PINS.  A pre-override `us_prophet_v2` board publishes the
        retired scorer as `prophet.score` and `display_rank` IS that order.  On the
        shipped fusion board neither holds: the published score is C1 and the
        retired scorer has moved to `prophet_shadow`.  Read the wrong block and the
        script fails twice — the freeze check compares a C1 score against a v2 score
        and refuses the buy lane, and `old_rank` becomes the FUSION rank, which would
        compare the new order against itself and report every delta as zero.  The
        tests above now pin the shipped v3 / shadow contract; this one still proves
        the SAME pool produces the SAME comparison when the artifact is re-derived
        as a v3 board.

        The invariant asserted here is the strong one — the SAME pool must produce the
        SAME comparison whichever generation of board it is read from.
        """
        from scripts import us_prophet_fusion_compare as cmp_mod

        gate = json.loads((BOARD.parent / "signal_gate.json").read_text())
        from_v2 = cmp_mod.compare(top=30)

        # Build the artifact the first fusion nightly actually publishes.
        rows = [dict(r) for r in committed_board["buy"]]
        for r in rows:
            for key in ("prophet", "prophet_shadow", "score_rank", "display_rank",
                        "featured", "featured_blocked_by", "stage"):
                r.pop(key, None)
        floors: dict = {}
        scored = ubr.score_rows(rows, verdict_by=gate.get("verdicts") or {},
                                board_asof=committed_board.get("as_of"),
                                bottom_watch_stage=ubr.STAGE_BASING,
                                fusion_floors=floors)
        board_v3 = dict(committed_board)
        board_v3["buy"] = scored
        board_v3["rank_by"] = board_v3["board_definition"] = ubr.published_definition(scored)
        v3_path = tmp_path / "us_standouts.json"
        v3_path.write_text(json.dumps(board_v3))
        monkeypatch.setattr(cmp_mod, "BOARD", v3_path)
        monkeypatch.setattr(cmp_mod, "_REPO", tmp_path)

        from_v3 = cmp_mod.compare(top=30)

        assert from_v3["old_definition"] == ubr.SHADOW_DEFINITION
        assert from_v3["old_rank_basis"] == "prophet_shadow.score_rank"
        assert from_v3["new_definition"] == ubr.BOARD_DEFINITION
        # Not merely "it ran": the deltas must be the real ones, not a wall of zeros.
        assert any(r["rank_change"] for r in from_v3["new_top"])
        assert ({r["ticker"]: r["rank_change"] for r in from_v3["new_top"]}
                == {r["ticker"]: r["rank_change"] for r in from_v2["new_top"]})
        assert from_v3["promoted_into_top"] == from_v2["promoted_into_top"]
        assert from_v3["demoted_out_of_top"] == from_v2["demoted_out_of_top"]
        # The shadow ranks but never features, so there is no retired featured set to
        # differ from — an empty list, never every featured name listed as a change.
        assert from_v3["featured_changed"] == []


# --------------------------------------------------------------------------- #
# 4. the shadow has no authority; a degraded night says so
# --------------------------------------------------------------------------- #

class TestTheBoardRanksByFusion:
    @staticmethod
    def _pool():
        return [
            # BROAD: every family speaks for it, but its alpha is the pool's worst.
            _row("BROAD", alpha=0.1, off_high=-3.0, tier="T2", sue_z=2.0,
                 smartmoney=True, insiders=3, gex="confirm", news=5),
            # NARROW: the retired scorer's favourite — best alpha, nothing else.
            _row("NARROW", alpha=9.0, off_high=-1.0, tier="T2", gex="neutral"),
            _row("MID", alpha=4.0, off_high=-8.0, tier="T1", sue_z=1.0,
                 smartmoney=True, insiders=0, gex="neutral", news=0),
        ]

    def test_the_canonical_score_is_the_fusion_score(self):
        scored = ubr.score_rows(self._pool(), board_asof="2026-08-15")
        for row in scored:
            block = row["prophet"]
            assert block["version"] == ubr.BOARD_DEFINITION == "us_prophet_v3"
            assert block["score_authority"].startswith("C1 evidence-family fusion")
            assert block["fusion"]["families_active"]
            assert block["score"] == pytest.approx(
                sum(block["fusion"]["family_contribution"].values())
                / len(block["fusion"]["family_contribution"]), abs=0.06)

    def test_breadth_of_evidence_can_outrank_the_retired_favourite(self):
        """The behaviour change the override is FOR, shown rather than asserted."""
        scored = ubr.score_rows(self._pool(), board_asof="2026-08-15")
        order = [r["ticker"] for r in scored]
        shadow = sorted(scored, key=lambda r: -r["prophet_shadow"]["score"])
        assert order[0] == "BROAD"
        assert shadow[0]["ticker"] == "NARROW"

    def test_the_sort_key_is_stage_then_fusion_then_ticker(self):
        scored = ubr.score_rows(self._pool(), board_asof="2026-08-15")
        keys = [(ubr.stage_rank(r["stage"]), -(r["prophet"]["score"] or 0.0),
                 r["ticker"]) for r in scored]
        assert keys == sorted(keys)

    def test_an_unscored_row_sorts_after_scored_rows_in_its_bucket(self):
        """Null-last by SAYING so, not by coercing the null to 0.0."""
        pool = self._pool()
        blind = _row("BLIND", alpha=None, off_high=None, tier=None, gex=None)
        blind.pop("news_burst"); blind.pop("smartmoney_chip"); blind.pop("insider_buyers")
        scored = ubr.score_rows(pool + [blind], board_asof="2026-08-15")
        by_stage: dict[str, list] = {}
        for row in scored:
            by_stage.setdefault(row["stage"], []).append(row)
        for bucket in by_stage.values():
            seen_null = False
            for row in bucket:
                if row["prophet"]["score"] is None:
                    seen_null = True
                else:
                    assert not seen_null, "a scored row sorted after an unscored one"

    def test_the_receipt_names_the_abstaining_families(self):
        scored = ubr.score_rows(self._pool(), board_asof="2026-08-15")
        fusion = scored[0]["prophet"]["fusion"]
        assert set(fusion["families_abstaining"]) >= {
            "F3_THEME_STRUCTURE", "F6_MACRO_REGIME", "F7_QUALITY_FUNDAMENTAL"}
        assert not set(fusion["families_abstaining"]) & set(fusion["families_active"])

    def test_the_ranking_block_publishes_the_floors_when_asked(self):
        floors: dict = {}
        scored = ubr.score_rows(self._pool(), board_asof="2026-08-15",
                                fusion_floors=floors)
        block = ubr.ranking_block(scored, fusion_floors=floors)
        assert block["fusion"]["floors"]["captured"] is True
        assert block["fusion"]["shadow_note"]
        assert block["score_kind"] == ubr.FUSION_SCORE_KIND
        json.dumps(block, allow_nan=False)

    def test_the_block_is_honest_when_the_floors_were_not_captured(self):
        scored = ubr.score_rows(self._pool(), board_asof="2026-08-15")
        block = ubr.ranking_block(scored)
        assert block["fusion"]["floors"]["captured"] is False


class TestTheShadowHasNoAuthority:
    @staticmethod
    def _pool():
        return TestTheBoardRanksByFusion._pool()

    def test_it_is_stamped_on_every_row_with_the_shadow_definition(self):
        scored = ubr.score_rows(self._pool(), board_asof="2026-08-15")
        for row in scored:
            assert row["prophet_shadow"]["version"] == ubr.SHADOW_DEFINITION
            assert row["prophet_shadow"]["version"] == "us_prophet_v2_shadow"
            assert "none" in row["prophet_shadow"]["authority"]

    def test_it_carries_its_own_rank_and_that_rank_is_not_the_board_order(self):
        scored = ubr.score_rows(self._pool(), board_asof="2026-08-15")
        board = [r["ticker"] for r in scored]
        shadow = [r["ticker"] for r in
                  sorted(scored, key=lambda r: r["prophet_shadow"]["score_rank"])]
        assert sorted(board) == sorted(shadow)
        assert board != shadow, "fixture must actually disagree or this proves nothing"

    def test_deleting_the_shadow_changes_no_order_no_score_and_no_featured_flag(self):
        """The operational meaning of ZERO AUTHORITY, tested the only way that binds:
        remove it and show nothing downstream moves."""
        with_shadow = ubr.score_rows(self._pool(), board_asof="2026-08-15")
        snapshot = [{k: v for k, v in r.items() if k != "prophet_shadow"}
                    for r in with_shadow]
        again = ubr.score_rows(self._pool(), board_asof="2026-08-15")
        for row in again:
            row.pop("prophet_shadow")
        assert again == snapshot

    def test_the_shadow_never_sets_display_rank(self):
        scored = ubr.score_rows(self._pool(), board_asof="2026-08-15")
        for row in scored:
            assert "display_rank" not in row["prophet_shadow"]


class TestDegradationIsStampedNotHidden:
    def test_a_refused_plane_publishes_the_fallback_definition_and_the_cause(self,
                                                                            monkeypatch):
        def _refuse(*_a, **_k):
            raise fus.FusionUnavailable("no family survived (synthetic)")

        monkeypatch.setattr(fus, "fuse_board", _refuse)
        scored = ubr.score_rows([_row("A"), _row("B", alpha=2.0)],
                                board_asof="2026-08-15")
        for row in scored:
            block = row["prophet"]
            assert block["version"] == ubr.FALLBACK_DEFINITION
            assert block["version"] != ubr.BOARD_DEFINITION
            assert "no family survived" in block["degradation"]["reason"]
            assert block["degradation"]["expected_definition"] == ubr.BOARD_DEFINITION
            assert "fusion" not in block
            assert "prophet_shadow" not in row

    def test_the_artifact_definition_follows_the_rows_not_the_constant(self,
                                                                      monkeypatch):
        """The trap this closes: a builder copying BOARD_DEFINITION into `rank_by`
        would publish an artifact claiming to be a fusion board over rows that say
        otherwise, and every forward ledger keyed on the artifact would pool a
        degraded night with the canonical ones."""
        def _refuse(*_a, **_k):
            raise fus.FusionUnavailable("synthetic")

        monkeypatch.setattr(fus, "fuse_board", _refuse)
        scored = ubr.score_rows([_row("A"), _row("B", alpha=2.0)],
                                board_asof="2026-08-15")
        assert ubr.published_definition(scored) == ubr.FALLBACK_DEFINITION
        assert ubr.ranking_block(scored)["definition"] == ubr.FALLBACK_DEFINITION

    def test_a_mixed_pool_refuses_rather_than_picking_one(self):
        rows = [{"prophet": {"version": "us_prophet_v3"}},
                {"prophet": {"version": "us_prophet_v2_fallback"}}]
        with pytest.raises(ValueError, match="different board definitions"):
            ubr.published_definition(rows)

    def test_the_degradation_stamp_is_still_this_market(self):
        """It must keep the US extension-outage alarm and the US entry provenance —
        a fallback night is this board having a bad night, not a sibling market."""
        assert ubr.is_us_definition(ubr.FALLBACK_DEFINITION)
        assert ubr.FALLBACK_DEFINITION in ubr.EXTENSION_PANEL_MARKETS
        assert not ubr.is_us_definition("hk_prophet_v1")


class TestSiblingBoardsAreUntouched:
    def test_a_non_us_definition_gets_the_retired_scorer_and_no_fusion_block(self):
        """`hk_prophet_v1` delegates this whole pass.  It has no registered members
        wired and must publish exactly what it published before the override."""
        rows = [_row("A", alpha=1.0), _row("B", alpha=2.0)]
        scored = ubr.score_rows(rows, board_asof="2026-08-15",
                                definition="hk_prophet_v1")
        for row in scored:
            assert row["prophet"]["version"] == "hk_prophet_v1"
            assert "fusion" not in row["prophet"]
            assert "prophet_shadow" not in row
            assert set(row["prophet"]["components"]) == set(ubr.SCORE_WEIGHTS)

    def test_the_sibling_score_equals_the_frozen_v2_arithmetic(self):
        rows = [_row("A", alpha=1.0), _row("B", alpha=2.0)]
        scored = ubr.score_rows([dict(r) for r in rows], board_asof="2026-08-15",
                                definition="hk_prophet_v1")
        us = ubr.score_rows([dict(r) for r in rows], board_asof="2026-08-15")
        # MATCHED BY TICKER: the two boards sort on different keys, so a positional
        # zip compares two different names and passes or fails by accident.
        own_by = {r["ticker"]: r for r in us}
        for sib in scored:
            assert (sib["prophet"]["score"]
                    == own_by[sib["ticker"]]["prophet_shadow"]["score"]), sib["ticker"]

    def test_a_sibling_ranking_block_keeps_its_own_definition_and_score_kind(self):
        scored = ubr.score_rows([_row("A")], board_asof="2026-08-15",
                                definition="hk_prophet_v1")
        block = ubr.ranking_block(scored, definition="hk_prophet_v1")
        assert block["definition"] == "hk_prophet_v1"
        assert block["score_kind"] == ubr.SCORE_KIND
        assert block["fusion"] is None


class TestTheEraFence:
    def test_the_displaced_stamp_was_appended_in_the_same_change(self):
        assert "us_prophet_v2" in ubr.SUPERSEDED_ERA_STAMPS
        assert ubr.BOARD_DEFINITION not in ubr.SUPERSEDED_ERA_STAMPS

    def test_the_selection_era_did_not_move(self):
        """A RANK change is not an ADMISSION change.  Bumping the era here would
        restart the H=63 episode clock and re-create the unsatisfiable-gate trap the
        era's own ruling exists to prevent."""
        assert ubr.SELECTION_ERA == "anticipation-v1-2026-08-08"

    def test_no_forecast_or_validation_language_in_the_fusion_copy(self):
        scored = ubr.score_rows(TestTheBoardRanksByFusion._pool(),
                                board_asof="2026-08-15")
        text = json.dumps(ubr.ranking_block(scored)).lower()
        text += json.dumps(scored[0]["prophet"]).lower()
        for banned in ("validated", "win rate", "win-rate", "forecast return",
                       "expected return", "backtested", "proven alpha"):
            assert banned not in text, banned

    def test_the_published_score_kind_refuses_the_alpha_claim(self):
        assert "not a calibrated return forecast" in ubr.FUSION_SCORE_KIND
        assert "not a promoted alpha model" in ubr.FUSION_SCORE_KIND



# --------------------------------------------------------------------------- #
# versioned earnings semantics: fix meaning without silently changing C1
# --------------------------------------------------------------------------- #

class TestVersionedEarningsSemantics:
    @pytest.mark.parametrize("row,expected", [
        (_row("ZERO", sue_z=2.0, sue_fresh_days=0), False),
        (_row("POS", sue_z=2.0, sue_fresh_days=1), True),
        (_row("NEG", sue_z=-2.0, sue_fresh_days=1), True),
        (_row("EDGE", sue_z=2.0, sue_fresh_days=60), True),
        (_row("STALE", sue_z=2.0, sue_fresh_days=61), False),
        ({"ticker": "MISS"}, False),
    ])
    def test_default_remains_exact_legacy_boolean(self, row, expected):
        assert fus.extract_members(row)["sue_fresh"] is expected

    @pytest.mark.parametrize("row,state,positive", [
        (_row("ZERO", sue_z=2.0, sue_fresh_days=0),
         "FRESH_REPORTED_RELATIVE_VALUE", True),
        (_row("NEG", sue_z=-2.0, sue_fresh_days=1),
         "FRESH_REPORTED_RELATIVE_VALUE", False),
        (_row("EDGE", sue_z=2.0, sue_fresh_days=60),
         "FRESH_REPORTED_RELATIVE_VALUE", True),
        (_row("STALE", sue_z=2.0, sue_fresh_days=61),
         "STALE", False),
        ({"ticker": "MISS", "sue_fresh_days": 1},
         "UNAVAILABLE", None),
        (_row("BADAGE", sue_z=2.0, sue_fresh_days=-1),
         "UNAVAILABLE", None),
    ])
    def test_v2_observation_preserves_signed_value_and_freshness(self, row, state, positive):
        out = fus.earnings_evidence_v2(row)
        assert out["schema"] == "prophet.sue_observation/v2"
        assert out["measure"] == "cross_sectional_z_of_seasonal_eps_momentum"
        assert out["analyst_consensus_beat"] is None
        assert out["rank_authority"] is False
        assert out["entry_authority"] is False
        assert out["state"] == state
        assert out["fresh_positive_relative"] is positive

    def test_v2_explicit_feature_fixes_zero_day_and_negative_sign(self):
        version = fus.EARNINGS_EVIDENCE_VERSION
        assert fus.extract_members(
            _row("ZERO", sue_z=2.0, sue_fresh_days=0),
            earnings_semantics=version,
        )["sue_fresh"] is True
        assert fus.extract_members(
            _row("NEG", sue_z=-2.0, sue_fresh_days=1),
            earnings_semantics=version,
        )["sue_fresh"] is False

    def test_v2_does_not_turn_missingness_into_a_consensus_fact(self):
        out = fus.earnings_evidence_v2({"ticker": "MISS", "sue_fresh_days": 2})
        assert out["state"] == "UNAVAILABLE"
        assert out["fresh_positive_relative"] is None
        assert out["raw_seasonal_surprise_direction"] is None
        assert out["analyst_consensus_beat"] is None

    @pytest.mark.parametrize("row", [
        {"sue_z": True, "sue_fresh_days": 1},
        {"sue_z": 1.0, "sue_fresh_days": True},
        {"sue_z": float("nan"), "sue_fresh_days": 1},
        {"sue_z": 1.0, "sue_fresh_days": float("inf")},
        {"sue_z": 1.0, "sue_fresh_days": 1.5},
    ])
    def test_v2_invalid_numeric_inputs_are_unavailable(self, row):
        out = fus.earnings_evidence_v2(row)
        assert out["state"] == "UNAVAILABLE"
        assert out["fresh_positive_relative"] is None

    def test_serving_and_grader_use_the_same_explicit_version(self):
        pytest.importorskip("pandas")
        try:
            from scripts import grade_us_board
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"grader unavailable: {exc}")
        version = fus.EARNINGS_EVIDENCE_VERSION
        rows = [
            _row("ZERO", sue_z=2.0, sue_fresh_days=0),
            _row("NEG", sue_z=-2.0, sue_fresh_days=1),
            _row("STALE", sue_z=2.0, sue_fresh_days=61),
            {"ticker": "MISS"},
        ]
        for row in rows:
            mine = fus.extract_members(row, earnings_semantics=version)["sue_fresh"]
            theirs = grade_us_board._row_features(
                dict(row), earnings_semantics=version
            )["sue_fresh"]
            assert mine == theirs
            if earnings := grade_us_board._row_features(
                dict(row), earnings_semantics=version
            ).get("earnings_evidence_v2"):
                assert earnings == fus.earnings_evidence_v2(row)

    def test_default_committed_board_preserves_legacy_sue_flag(self, committed_board):
        for row in committed_board.get("buy", []):
            expected = bool(
                row.get("sue_z")
                and (row.get("sue_fresh_days") or 999) <= 60
            )
            assert fus.extract_members(row)["sue_fresh"] is expected

    def test_explicit_version_changes_only_the_earnings_member(self, committed_board):
        version = fus.EARNINGS_EVIDENCE_VERSION
        for row in committed_board.get("buy", []):
            legacy = fus.extract_members(row)
            revised = fus.extract_members(row, earnings_semantics=version)
            assert set(legacy) == set(revised)
            for key in set(legacy) - {"sue_fresh"}:
                assert revised[key] == legacy[key], (row.get("ticker"), key)

    def test_unknown_version_refuses_in_serving_and_evaluation(self):
        with pytest.raises(ValueError, match="unknown earnings semantics"):
            fus.extract_members(_row("X"), earnings_semantics="unknown")
        pytest.importorskip("pandas")
        try:
            from scripts import grade_us_board
        except Exception as exc:  # pragma: no cover
            pytest.skip(f"grader unavailable: {exc}")
        with pytest.raises(ValueError, match="unknown earnings semantics"):
            grade_us_board._row_features(_row("X"), earnings_semantics="unknown")


# --------------------------------------------------------------------------- #
# Earnings / Expectation Revision factual evidence — non-authoritative
# --------------------------------------------------------------------------- #

class TestEarningsEvidenceEngine:
    """Factual earnings semantics for the new sleeve; no rank/entry promotion."""

    @staticmethod
    def _basis(metric="revenue", *, fiscal_period="FY2026 Q3",
               start="2026-03-29", end="2026-06-27",
               currency="USD", unit="USD_millions",
               accounting="GAAP", share_basis="NOT_APPLICABLE"):
        return sue_engine.MetricBasis(
            issuer_id="cik:0000320193",
            issuer_name="Apple Inc.",
            metric=metric,
            fiscal_period=fiscal_period,
            period_role="QUARTER",
            period_start=start,
            period_end=end,
            currency=currency,
            unit=unit,
            accounting_basis=accounting,
            share_basis=share_basis,
        )

    @classmethod
    def _actual(cls, value=109417.0, *, basis=None,
                public_at="2026-07-30T20:30:28Z",
                available_at="2026-07-30T20:30:28Z",
                event_id="evt_cik0000320193_2026q3_results",
                source_ref="sec:0000320193:0000320193-26-000018:EX-99.1"):
        return sue_engine.Actual(
            basis=basis or cls._basis(),
            value=value,
            public_at=public_at,
            available_at=available_at,
            source_ref=source_ref,
            event_id=event_id,
        )

    @classmethod
    def _expectation(cls, value=100000.0, *, basis=None,
                     kind="ANALYST_CONSENSUS",
                     forecast_at="2026-07-29T18:00:00Z",
                     available_at="2026-07-29T18:01:00Z"):
        return sue_engine.Expectation(
            basis=basis or cls._basis(),
            value=value,
            forecast_at=forecast_at,
            available_at=available_at,
            source_ref="licensed:consensus:snapshot",
            kind=kind,
        )

    @classmethod
    def _forecast(cls, contributor, value, forecast_at, revision_id, *,
                  basis=None, state="ACTIVE", valid_until=None):
        return sue_engine.Forecast(
            basis=basis or cls._basis(),
            contributor=contributor,
            value=value,
            forecast_at=forecast_at,
            available_at=forecast_at,
            revision_id=revision_id,
            source_ref=f"licensed:{revision_id}",
            state=state,
            valid_until=valid_until,
        )

    @pytest.mark.parametrize("row,state,positive", [
        ({"sue_z": 2.0, "sue_fresh_days": 0}, "FRESH_REPORTED_RELATIVE_VALUE", True),
        ({"sue_z": -2.0, "sue_fresh_days": 1}, "FRESH_REPORTED_RELATIVE_VALUE", False),
        ({"sue_z": 2.0, "sue_fresh_days": 60}, "FRESH_REPORTED_RELATIVE_VALUE", True),
        ({"sue_z": 2.0, "sue_fresh_days": 61}, "STALE", False),
        ({"sue_z": None, "sue_fresh_days": 1}, "UNAVAILABLE", None),
        ({"sue_z": 2.0, "sue_fresh_days": -1}, "UNAVAILABLE", None),
    ])
    def test_structured_sue_semantics(self, row, state, positive):
        out = sue_engine.legacy_sue_evidence(row)
        assert out["state"] == state
        assert out["fresh_positive_relative"] is positive
        assert out["analyst_consensus_beat"] is None
        assert out["raw_seasonal_surprise_direction"] is None
        assert out["rank_authority"] is False
        assert out["entry_authority"] is False

    def test_accepted_q06_revenue_change_reproduces_exact_field(self):
        current = self._actual()
        prior = self._actual(
            94036,
            basis=self._basis(
                fiscal_period="FY2025 Q3",
                start="2025-03-30",
                end="2025-06-28",
            ),
            public_at="2025-07-31T20:30:00Z",
            available_at="2025-07-31T20:30:00Z",
            event_id="evt_cik0000320193_2025q3_results",
            source_ref="sec:aapl:fy2025q3:ex99.1",
        )
        out = sue_engine.reported_change(
            current, prior, decision_at="2026-07-30T20:31:00Z")
        assert out["change_pct"] == pytest.approx(16.356501765281383)
        assert out["rank_authority"] is False
        assert out["entry_authority"] is False

    @pytest.mark.parametrize("basis", [
        _basis.__func__(currency="EUR"),
        _basis.__func__(unit="USD"),
        _basis.__func__(accounting="ADJUSTED"),
        sue_engine.MetricBasis(
            issuer_id="cik:other", issuer_name="Other", metric="revenue",
            fiscal_period="FY2025 Q3", period_role="QUARTER",
            period_start="2025-03-30", period_end="2025-06-28",
            currency="USD", unit="USD_millions", accounting_basis="GAAP"),
        sue_engine.MetricBasis(
            issuer_id="cik:0000320193", issuer_name="Apple Inc.", metric="revenue",
            fiscal_period="FY2025 9M", period_role="NINE_MONTHS",
            period_start="2024-09-29", period_end="2025-06-28",
            currency="USD", unit="USD_millions", accounting_basis="GAAP"),
    ])
    def test_reported_change_rejects_incomparable_basis(self, basis):
        prior = self._actual(
            94036, basis=basis,
            public_at="2025-07-31T20:30:00Z",
            available_at="2025-07-31T20:30:00Z", event_id="prior")
        with pytest.raises(sue_engine.EvidenceError, match="basis mismatch"):
            sue_engine.reported_change(
                self._actual(), prior, decision_at="2026-07-30T20:31:00Z")

    def test_consensus_surprise_is_distinct_from_seasonal_sue(self):
        out = sue_engine.surprise(
            self._actual(), self._expectation(),
            decision_at="2026-07-30T20:31:00Z")
        assert out["status"] == "COMPARABLE"
        assert out["signed_difference"] == 9417.0
        assert out["analyst_consensus_beat"] is True
        assert out["standardized"] is None
        assert out["rank_authority"] is False

    def test_missing_consensus_is_not_manufactured_from_prior_year(self):
        out = sue_engine.surprise(
            self._actual(), None, decision_at="2026-07-30T20:31:00Z")
        assert out["status"] == "EXPECTATION_UNAVAILABLE"
        assert out["analyst_consensus_beat"] is None
        assert out["signed_difference"] is None

    @pytest.mark.parametrize("forecast_at,available_at", [
        ("2026-07-30T20:30:28Z", "2026-07-30T20:30:28Z"),
        ("2026-07-30T20:29:00Z", "2026-07-30T20:30:28Z"),
        ("2026-07-30T20:31:00Z", "2026-07-30T20:31:00Z"),
    ])
    def test_expectation_at_or_after_release_cannot_be_backdated(
        self, forecast_at, available_at
    ):
        with pytest.raises(sue_engine.EvidenceError, match="expectation"):
            sue_engine.surprise(
                self._actual(),
                self._expectation(
                    forecast_at=forecast_at, available_at=available_at),
                decision_at="2026-07-30T21:00:00Z",
            )

    def test_scaling_is_past_only_and_method_matched(self):
        rows = [
            sue_engine.HistoricalForecastError(
                2, "2025-01-01T00:00:00Z", "e1", "s1", "rev-q",
                "ANALYST_CONSENSUS"),
            sue_engine.HistoricalForecastError(
                -1, "2025-04-01T00:00:00Z", "e2", "s2", "rev-q",
                "ANALYST_CONSENSUS"),
            sue_engine.HistoricalForecastError(
                3, "2025-07-01T00:00:00Z", "e3", "s3", "rev-q",
                "ANALYST_CONSENSUS"),
            sue_engine.HistoricalForecastError(
                0, "2025-10-01T00:00:00Z", "e4", "s4", "rev-q",
                "ANALYST_CONSENSUS"),
            sue_engine.HistoricalForecastError(
                999, "2026-08-01T00:00:00Z", "future", "sf", "rev-q",
                "ANALYST_CONSENSUS"),
            sue_engine.HistoricalForecastError(
                999, "2025-11-01T00:00:00Z", "wrong", "sw", "rev-q",
                "SEASONAL_MODEL"),
        ]
        out = sue_engine.surprise(
            self._actual(), self._expectation(),
            decision_at="2026-07-30T20:31:00Z",
            calibration=rows, calibration_key="rev-q", min_history=4)
        assert out["calibration_event_ids"] == ["e1", "e2", "e3", "e4"]
        assert out["standardized"] is not None
        assert {x["event_id"]: x["reason"]
                for x in out["excluded_calibration"]} == {
                    "future": "unavailable_before_event",
                    "wrong": "expectation_method_mismatch",
                }

    def test_matched_revisions_do_not_confuse_new_analyst_with_upgrade(self):
        rows = [
            self._forecast("A", 100, "2026-07-01T00:00:00Z", "a0"),
            self._forecast("B", 100, "2026-07-01T00:00:00Z", "b0"),
            self._forecast("A", 100, "2026-07-15T00:00:00Z", "a1"),
            self._forecast("B", 100, "2026-07-15T00:00:00Z", "b1"),
            self._forecast("C", 102, "2026-07-15T00:00:00Z", "c1"),
        ]
        out = sue_engine.matched_revisions(
            rows, basis=self._basis(),
            before="2026-07-02T00:00:00Z",
            after="2026-07-16T00:00:00Z")
        assert out["matched_count"] == 2
        assert out["matched_mean_change"] == 0
        assert out["entered"] == ["C"]
        assert out["naive_changing_roster_mean_change"] == pytest.approx(2 / 3)
        assert out["roster_difference_residual"] == pytest.approx(2 / 3)

    def test_withdrawal_does_not_fall_back_to_older_forecast(self):
        rows = [
            self._forecast("A", 100, "2026-07-01T00:00:00Z", "a0"),
            self._forecast(
                "A", None, "2026-07-10T00:00:00Z", "a1",
                state="WITHDRAWN"),
        ]
        out = sue_engine.matched_revisions(
            rows, basis=self._basis(),
            before="2026-07-02T00:00:00Z",
            after="2026-07-11T00:00:00Z")
        assert out["before_count"] == 1
        assert out["after_count"] == 0
        assert out["exited"] == ["A"]

    def test_dilution_can_reverse_income_growth_on_a_per_share_basis(self):
        out = sue_engine.per_share_bridge(
            old_income=100, new_income=120,
            old_shares=100, new_shares=150)
        assert out["income_grew"] is True
        assert out["old_eps"] == 1
        assert out["new_eps"] == pytest.approx(0.8)
        assert out["eps_grew"] is False
        assert out["share_count_effect_at_new_income"] == pytest.approx(-0.4)

    @pytest.mark.parametrize("price,probability", [(100, 0.275), (108, 0.775)])
    def test_entry_economics_change_with_price(self, price, probability):
        out = sue_engine.entry_economics(
            price=price, target=112, stop=96,
            win_cost=0.4, loss_cost=0.4, required_reward_risk=2)
        assert out["break_even_target_probability"] == pytest.approx(probability)
        assert out["estimated_win_probability"] is None
        assert out["entry_permission"] is False

    def test_two_to_one_net_price_ceiling_is_explicit(self):
        out = sue_engine.entry_economics(
            price=100, target=112, stop=96,
            win_cost=0.4, loss_cost=0.4, required_reward_risk=2)
        assert out["price_ceiling_for_required_reward_risk"] == pytest.approx(
            100.9333333333)
        assert out["within_scenario_ceiling"] is True

    def test_joint_eps_and_revenue_agreement_needs_same_event_and_method(self):
        eps_basis = self._basis(
            metric="EPS", unit="USD_per_share", share_basis="DILUTED")
        eps = sue_engine.surprise(
            self._actual(2, basis=eps_basis),
            self._expectation(1.8, basis=eps_basis),
            decision_at="2026-07-30T20:31:00Z")
        rev = sue_engine.surprise(
            self._actual(),
            self._expectation(),
            decision_at="2026-07-30T20:31:00Z")
        state = sue_engine.joint_earnings_state(eps, rev)
        assert state["state"] == "EPS_ABOVE_REVENUE_ABOVE"
        assert state["both_positive"] is True
        assert state["rank_authority"] is False

    def test_dossier_preserves_q06_source_and_all_authority_false(self):
        current = self._actual()
        prior = self._actual(
            94036,
            basis=self._basis(
                fiscal_period="FY2025 Q3",
                start="2025-03-30", end="2025-06-28"),
            public_at="2025-07-31T20:30:00Z",
            available_at="2025-07-31T20:30:00Z",
            event_id="prior")
        change = sue_engine.reported_change(
            current, prior, decision_at="2026-07-30T20:31:00Z")
        dossier = sue_engine.factual_dossier(
            event_id=current.event_id,
            issuer_id=current.basis.issuer_id,
            decision_at="2026-07-30T20:31:00Z",
            reported_changes=[change],
            source_contract_refs=[
                "macro#8069@ae9409bca5d81dbf7438ff0037a976b324853bdd:"
                "q06_source_contract_v0.2"
            ],
        )
        assert dossier["reported_changes"][0]["change_pct"] == pytest.approx(
            16.356501765281383)
        assert all(value is False for value in dossier["authority"].values())
        assert "no qualified pre-release expectation surprise" in dossier[
            "limitations"
        ]

    def test_dossier_refuses_cross_issuer_or_cross_event_evidence(self):
        basis = self._basis()
        actual = self._actual(basis=basis)
        surprise = sue_engine.surprise(
            actual, self._expectation(basis=basis),
            decision_at="2026-07-30T20:31:00Z")
        with pytest.raises(sue_engine.EvidenceError, match="surprise identity mismatch"):
            sue_engine.factual_dossier(
                event_id="other-event",
                issuer_id="cik:other",
                decision_at="2026-07-30T20:31:00Z",
                surprises=[surprise],
                source_contract_refs=["fixture"],
            )

    def test_dossier_requires_a_source_contract_reference(self):
        with pytest.raises(sue_engine.EvidenceError, match="source contract"):
            sue_engine.factual_dossier(
                event_id="fixture-event",
                issuer_id="cik:0000320193",
                decision_at="2026-07-30T20:31:00Z",
            )

    def test_dossier_refuses_authoritative_child_even_if_rehashed_elsewhere(self):
        basis = self._basis()
        surprise = sue_engine.surprise(
            self._actual(basis=basis),
            self._expectation(basis=basis),
            decision_at="2026-07-30T20:31:00Z")
        surprise = dict(surprise)
        surprise["rank_authority"] = True
        with pytest.raises(sue_engine.EvidenceError, match="authoritative child"):
            sue_engine.factual_dossier(
                event_id="evt_cik0000320193_2026q3_results",
                issuer_id="cik:0000320193",
                decision_at="2026-07-30T20:31:00Z",
                surprises=[surprise],
                source_contract_refs=["fixture"],
            )

    def test_dossier_refuses_revision_snapshot_after_its_decision(self):
        rows = [
            self._forecast("A", 100, "2026-07-01T00:00:00Z", "a0"),
            self._forecast("A", 101, "2026-07-31T00:00:00Z", "a1"),
        ]
        revision = sue_engine.matched_revisions(
            rows, basis=self._basis(),
            before="2026-07-02T00:00:00Z",
            after="2026-08-01T00:00:00Z")
        with pytest.raises(sue_engine.EvidenceError, match="revision evidence is from the future"):
            sue_engine.factual_dossier(
                event_id="fixture-event",
                issuer_id="cik:0000320193",
                decision_at="2026-07-30T20:31:00Z",
                revisions=[revision],
                source_contract_refs=["fixture"],
            )


class TestIssuerGuidanceDelivery:
    """Chronology/basis math: synthetic timestamps, not a historical ingestion replay."""
    @staticmethod
    def basis(**overrides):
        values=dict(issuer_id="cik:0000723125",issuer_name="Micron Technology, Inc.",
            metric="revenue",fiscal_period="FY2025 Q4",period_role="QUARTER",
            period_start="2025-05-30",period_end="2025-08-28",currency="USD",
            unit="USD_millions",accounting_basis="GAAP",share_basis="NOT_APPLICABLE")
        values.update(overrides);return sue_engine.MetricBasis(**values)

    @classmethod
    def actual(cls,value=11315,**kwargs):
        values=dict(basis=cls.basis(),value=value,public_at="2025-09-23T20:00:00Z",
            available_at="2025-09-23T20:01:00Z",event_id="evt_fixture_mu_q4",
            source_ref="fixture:reported-value:clocks-synthetic")
        values.update(kwargs);return sue_engine.Actual(**values)

    @classmethod
    def guide(cls,revision="initial",low=10400,high=11000,**kwargs):
        values=dict(basis=cls.basis(),low=low,high=high,public_at="2025-06-25T20:00:00Z",
            available_at="2025-06-25T20:01:00Z",revision_id=revision,
            source_ref="fixture:guidance:clocks-synthetic")
        values.update(kwargs);return sue_engine.IssuerGuidance(**values)

    @classmethod
    def updated(cls,**kwargs):
        return cls.guide("update",11100,11300,public_at="2025-08-11T12:00:00Z",
            available_at="2025-08-11T12:01:00Z",**kwargs)

    def evaluate(self,rows,**kwargs):
        return sue_engine.guidance_delivery(self.actual(),rows,
            decision_at="2025-09-23T21:00:00Z",source_history_complete=True,**kwargs)

    def test_latest_revision_separates_earlier_upgrade_from_results_news(self):
        out=self.evaluate([self.guide(),self.updated()])
        assert out["selected_revision_id"]=="update"
        assert out["latest_range"]=={"low":11100.,"midpoint":11200.,"high":11300.}
        assert out["signed_gap_to_initial_midpoint"]==615
        assert out["initial_to_latest_midpoint_change"]==500
        assert out["signed_gap_to_latest_midpoint"]==115
        assert out["distance_outside_latest_range"]==15
        assert out["range_position"]=="ABOVE_RANGE"
        assert out["analyst_consensus_beat"] is None
        assert out["estimated_return"] is None
        assert out["rank_authority"] is False
        assert out["entry_authority"] is False
        assert out["signed_gap_to_initial_midpoint"]==(
            out["initial_to_latest_midpoint_change"]+out["signed_gap_to_latest_midpoint"])

    def test_input_order_does_not_change_the_selected_forecast(self):
        assert self.evaluate([self.guide(),self.updated()])==self.evaluate([self.updated(),self.guide()])

    def test_post_release_update_cannot_rewrite_pre_release_forecast(self):
        late=self.guide("late",12000,13000,public_at="2025-09-23T20:05:00Z",
            available_at="2025-09-23T20:06:00Z")
        out=self.evaluate([self.guide(),self.updated(),late])
        assert out["selected_revision_id"]=="update"
        assert out["excluded_revisions"]==[{"revision_id":"late","reason":"published_at_or_after_result"}]

    def test_late_ingestion_is_not_credited_to_the_earlier_decision(self):
        from dataclasses import replace
        late=replace(self.updated(),available_at="2025-09-23T20:00:00Z")
        out=self.evaluate([self.guide(),late])
        assert out["selected_revision_id"]=="initial"
        assert out["excluded_revisions"][0]["reason"]=="not_usable_before_result"

    def test_withdrawal_never_falls_back_to_old_guidance(self):
        withdraw=self.guide("withdrawal",None,None,public_at="2025-09-01T12:00:00Z",
            available_at="2025-09-01T12:01:00Z",state="WITHDRAWN")
        out=self.evaluate([self.guide(),self.updated(),withdraw])
        assert out["status"]=="GUIDANCE_WITHDRAWN"
        assert out["latest_range"] is None and out["range_position"] is None

    def test_expired_forecast_does_not_reactivate_old_range(self):
        out=self.evaluate([self.guide(),self.updated(valid_until="2025-09-20T00:00:00Z")])
        assert out["status"]=="GUIDANCE_EXPIRED"
        assert out["latest_range"] is None

    def test_missing_history_cannot_claim_the_latest_guidance(self):
        out=sue_engine.guidance_delivery(self.actual(),[self.guide()],
            decision_at="2025-09-23T21:00:00Z",source_history_complete=False)
        assert out["status"]=="GUIDANCE_HISTORY_UNAVAILABLE"
        assert out["selected_revision_id"] is None and out["range_position"] is None

    def test_no_qualified_forecast_is_missing_not_a_miss(self):
        out=self.evaluate([])
        assert out["status"]=="GUIDANCE_UNAVAILABLE" and out["range_position"] is None

    @pytest.mark.parametrize("basis",[
        basis.__func__(accounting_basis="NON_GAAP"),basis.__func__(fiscal_period="FY2026 Q1"),
        basis.__func__(metric="EPS",unit="USD_per_share",share_basis="DILUTED"),
        basis.__func__(issuer_id="cik:other"),basis.__func__(currency="EUR"),
    ])
    def test_incomparable_forecast_does_not_become_a_beat(self,basis):
        out=self.evaluate([self.guide(basis=basis)])
        assert out["status"]=="GUIDANCE_UNAVAILABLE"
        assert out["excluded_revisions"][0]["reason"]=="incomparable_basis_or_period"

    @pytest.mark.parametrize("value,position,distance",[
        (11000,"BELOW_RANGE",-100),(11100,"WITHIN_RANGE",0),(11200,"WITHIN_RANGE",0),
        (11300,"WITHIN_RANGE",0),(11301,"ABOVE_RANGE",1),
    ])
    def test_stated_range_boundaries_are_inclusive_not_probabilities(self,value,position,distance):
        out=sue_engine.guidance_delivery(self.actual(value),[self.updated()],
            decision_at="2025-09-23T21:00:00Z",source_history_complete=True)
        assert out["range_position"]==position
        assert out["distance_outside_latest_range"]==distance
        assert out["range_interpretation"]=="ISSUER_STATED_RANGE_NOT_PROBABILITY_INTERVAL"

    def test_equal_publication_disagreement_refused(self):
        from dataclasses import replace
        other=replace(self.updated(),low=11000,revision_id="conflicting")
        with pytest.raises(sue_engine.EvidenceError,match="ambiguous equal-publication"):
            self.evaluate([self.guide(),self.updated(),other])

    def test_duplicate_revision_refused(self):
        with pytest.raises(sue_engine.EvidenceError,match="duplicate guidance revision"):
            self.evaluate([self.guide(),self.guide()])

    @pytest.mark.parametrize("low,high",[(float("nan"),2),(1,float("inf")),(True,2),(3,2)])
    def test_invalid_range_refused(self,low,high):
        with pytest.raises(sue_engine.EvidenceError,match="invalid guidance range"):
            self.guide(low=low,high=high)

    def test_result_is_not_available_before_actual_source(self):
        with pytest.raises(sue_engine.EvidenceError,match="actual unavailable"):
            sue_engine.guidance_delivery(self.actual(),[self.guide()],
                decision_at="2025-09-23T20:00:00Z",source_history_complete=True)

    def test_explicit_history_state_not_truthy_string(self):
        with pytest.raises(sue_engine.EvidenceError):
            sue_engine.guidance_delivery(self.actual(),[self.guide()],
                decision_at="2025-09-23T21:00:00Z",source_history_complete="true")

    def test_guidance_reaches_existing_dossier_as_separate_evidence(self):
        observation=self.evaluate([self.guide(),self.updated()])
        dossier=sue_engine.factual_dossier(event_id="evt_fixture_mu_q4",issuer_id="cik:0000723125",
            decision_at="2025-09-23T21:00:00Z",source_contract_refs=["fixture:source-contract"],
            guidance_results=[observation])
        assert dossier["issuer_guidance_delivery"][0]["selected_revision_id"]=="update"
        assert dossier["expectation_surprises"]==[]
        observation["latest_range"]["low"]=0
        assert dossier["issuer_guidance_delivery"][0]["latest_range"]["low"]==11100
        assert all(x is False for x in dossier["authority"].values())

    def test_wrong_event_guidance_does_not_enter_dossier(self):
        with pytest.raises(sue_engine.EvidenceError,match="guidance evidence identity"):
            sue_engine.factual_dossier(event_id="wrong",issuer_id="cik:0000723125",
                decision_at="2025-09-23T21:00:00Z",source_contract_refs=["fixture:source-contract"],
                guidance_results=[self.evaluate([self.guide()])])

    def test_legacy_dossier_does_not_silently_add_guidance_field(self):
        out=sue_engine.factual_dossier(event_id="fixture",issuer_id="cik:0000723125",
            decision_at="2025-09-23T21:00:00Z",source_contract_refs=["fixture"])
        assert "issuer_guidance_delivery" not in out


class TestPreResultGuidanceChange:
    def test_upgrade_is_computable_before_final_results(self):
        h=TestIssuerGuidanceDelivery()
        result=sue_engine.guidance_change(h.guide(),h.updated(),
            decision_at="2025-08-11T12:02:00Z",source_pair_is_adjacent=True)
        assert result["status"]=="COMPARABLE_ISSUER_OUTLOOK_CHANGE"
        assert result["midpoint_change"]==500
        assert result["lower_bound_change"]==700
        assert result["upper_bound_change"]==300
        assert result["width_change"]==-400
        assert result["interval_relationship"]=="ENTIRE_RANGE_ABOVE_PREVIOUS"
        assert result["actual_result_used"] is False
        assert result["return_forecast"] is None

    def test_wider_uncertainty_does_not_masquerade_as_unambiguous_upgrade(self):
        h=TestIssuerGuidanceDelivery()
        result=sue_engine.guidance_change(h.guide(),h.guide("mixed",10000,12000,
            public_at="2025-08-11T12:00:00Z",available_at="2025-08-11T12:01:00Z"),
            decision_at="2025-08-11T12:02:00Z",source_pair_is_adjacent=True)
        assert result["midpoint_change"]>0
        assert result["lower_bound_change"]<0 and result["upper_bound_change"]>0
        assert result["interval_relationship"]=="OVERLAPPING_MIXED_BOUND_CHANGE"
        assert result["width_change"]>0

    def test_no_early_use_of_guidance_update(self):
        h=TestIssuerGuidanceDelivery()
        with pytest.raises(sue_engine.EvidenceError,match="unavailable at decision"):
            sue_engine.guidance_change(h.guide(),h.updated(),
                decision_at="2025-08-11T12:00:00Z",source_pair_is_adjacent=True)

    def test_nonadjacent_pair_is_not_a_latest_revision(self):
        h=TestIssuerGuidanceDelivery()
        result=sue_engine.guidance_change(h.guide(),h.updated(),
            decision_at="2025-08-11T12:02:00Z",source_pair_is_adjacent=False)
        assert result["status"]=="ADJACENT_REVISION_PAIR_UNAVAILABLE"
        assert result["midpoint_change"] is None

    def test_withdrawn_outlook_not_implicitly_restored(self):
        h=TestIssuerGuidanceDelivery()
        withdraw=h.guide("withdraw",None,None,state="WITHDRAWN",
            public_at="2025-07-01T12:00:00Z",available_at="2025-07-01T12:01:00Z")
        result=sue_engine.guidance_change(h.guide(),withdraw,
            decision_at="2025-07-02T00:00:00Z",source_pair_is_adjacent=True)
        assert result["status"]=="GUIDANCE_WITHDRAWN"
        result=sue_engine.guidance_change(withdraw,h.updated(),
            decision_at="2025-08-11T12:02:00Z",source_pair_is_adjacent=True)
        assert result["status"]=="GUIDANCE_REINTRODUCED_NO_CONTINUOUS_COMPARISON"
        assert result["midpoint_change"] is None

    def test_reversed_revision_order_is_rejected(self):
        h=TestIssuerGuidanceDelivery()
        with pytest.raises(sue_engine.EvidenceError,match="publication order"):
            sue_engine.guidance_change(h.updated(),h.guide(),
                decision_at="2025-08-11T12:02:00Z",source_pair_is_adjacent=True)


class TestEarningsEvidenceBrief:
    """Actual native calculations -> factual dossier -> deterministic explanation."""
    H = TestEarningsEvidenceEngine
    cut = "2026-07-30T20:35:00Z"

    def dossier(self, **kwargs):
        return sue_engine.factual_dossier(
            event_id=self.H._actual().event_id,
            issuer_id=self.H._basis().issuer_id,
            decision_at=self.cut,
            source_contract_refs=["synthetic-reviewed-input"], **kwargs)

    def change(self, now=120, prior=100):
        from dataclasses import replace
        a=self.H._actual(now)
        old=replace(a,value=prior,basis=self.H._basis(fiscal_period="FY2025 Q3",start="2025-03-30",end="2025-06-28"))
        return sue_engine.reported_change(a,old,decision_at=self.cut)

    def guidance(self,low,high,day,id):
        return sue_engine.IssuerGuidance(
            self.H._basis(),low,high,day,day,id,"fixture:"+id)

    def codes(self,brief,key):
        return [item["code"] for item in brief[key]]

    def test_growth_is_an_operating_fact_not_a_buy_recommendation(self):
        dossier=self.dossier(reported_changes=[self.change()])
        b=sue_engine.earnings_evidence_brief(dossier)
        assert b["supporting_facts"][0]["text"]=="Revenue rose 20.0% against the comparable period."
        assert "QUALIFIED_PRE_RELEASE_EXPECTATION" in b["not_established"]
        assert "CURRENT_MARKET_AND_PORTFOLIO_PERMISSION" in b["not_established"]
        assert all(v is False for v in b["authority"].values())
        assert "score" not in b and "probability" not in b

    def test_decline_is_counterevidence_not_negative_growth_headline(self):
        b=sue_engine.earnings_evidence_brief(self.dossier(reported_changes=[self.change(80)]))
        assert b["counterevidence"][0]["text"]=="Revenue fell 20.0% against the comparable period."
        assert b["summary_state"]=="CAUTIONARY_FACTS"

    def test_unchanged_is_not_an_upgrade(self):
        b=sue_engine.earnings_evidence_brief(self.dossier(reported_changes=[self.change(100)]))
        assert b["context_facts"][0]["code"]=="REPORTED_UNCHANGED"
        assert "unchanged" in b["context_facts"][0]["text"]

    def test_empty_dossier_explicitly_remains_incomplete(self):
        b=sue_engine.earnings_evidence_brief(self.dossier())
        assert b["summary_state"]=="EVIDENCE_INCOMPLETE"
        assert b["supporting_facts"]==b["counterevidence"]==[]

    def test_missing_expectation_object_is_not_a_qualified_beat(self):
        surprise=sue_engine.surprise(self.H._actual(),None,decision_at=self.cut)
        b=sue_engine.earnings_evidence_brief(self.dossier(surprises=[surprise]))
        assert "QUALIFIED_PRE_RELEASE_EXPECTATION" in b["not_established"]
        assert "ABOVE_EXPECTATION" not in self.codes(b,"supporting_facts")

    def test_seasonal_expectation_not_called_consensus(self):
        x=sue_engine.surprise(self.H._actual(),self.H._expectation(kind="SEASONAL_MODEL"),decision_at=self.cut)
        b=sue_engine.earnings_evidence_brief(self.dossier(surprises=[x]))
        assert "seasonal-model" in b["supporting_facts"][0]["text"]
        assert "analyst expectation" not in b["supporting_facts"][0]["text"]

    def test_eps_beat_does_not_hide_revenue_miss(self):
        epsb=self.H._basis(metric="EPS",unit="USD_per_share",share_basis="DILUTED")
        eps=sue_engine.surprise(self.H._actual(2,basis=epsb),self.H._expectation(1.8,basis=epsb),decision_at=self.cut)
        rev=sue_engine.surprise(self.H._actual(90000),self.H._expectation(100000),decision_at=self.cut)
        b=sue_engine.earnings_evidence_brief(self.dossier(surprises=[eps,rev]))
        assert "ABOVE_EXPECTATION" in self.codes(b,"supporting_facts")
        assert "BELOW_EXPECTATION" in self.codes(b,"counterevidence")
        assert b["summary_state"]=="MIXED_FACTS"

    def test_matched_roster_change_cannot_create_upgrade(self):
        f=self.H._forecast
        revision=sue_engine.matched_revisions([
            f("A",100,"2026-07-01T00:00:00Z","a"),f("B",100,"2026-07-01T00:00:00Z","b"),
            f("C",200,"2026-07-15T00:00:00Z","c")],basis=self.H._basis(),
            before="2026-07-02T00:00:00Z",after="2026-07-16T00:00:00Z")
        b=sue_engine.earnings_evidence_brief(self.dossier(revisions=[revision]))
        assert "ROSTER_CHANGE_NOT_UPGRADE" in self.codes(b,"counterevidence")
        assert "did not change" in b["context_facts"][0]["text"]

    def test_negative_matched_revision_is_counterevidence(self):
        f=self.H._forecast
        revision=sue_engine.matched_revisions([f("A",100,"2026-07-01T00:00:00Z","a0"),
            f("A",80,"2026-07-15T00:00:00Z","a1")],basis=self.H._basis(),
            before="2026-07-02T00:00:00Z",after="2026-07-16T00:00:00Z")
        b=sue_engine.earnings_evidence_brief(self.dossier(revisions=[revision]))
        assert "MATCHED_FORECAST_REVISION" in self.codes(b,"counterevidence")

    def test_pre_result_guidance_upgrade_has_no_actual_input(self):
        before=self.guidance(90,100,"2026-07-01T00:00:00Z","old")
        after=self.guidance(110,120,"2026-07-15T00:00:00Z","new")
        update=sue_engine.guidance_change(before,after,decision_at="2026-07-15T00:01:00Z",source_pair_is_adjacent=True)
        d=self.dossier(guidance_updates=[update]);b=sue_engine.earnings_evidence_brief(d)
        assert "ISSUER_RANGE_CHANGE" in self.codes(b,"supporting_facts")
        assert d["expectation_surprises"]==[]
        assert update["actual_result_used"] is False
        assert update["previous_range"]["midpoint"]==95
        assert update["current_range"]["midpoint"]==115

    def test_higher_midpoint_with_weaker_lower_bound_is_mixed(self):
        old=self.guidance(90,100,"2026-07-01T00:00:00Z","old")
        new=self.guidance(80,130,"2026-07-15T00:00:00Z","new")
        update=sue_engine.guidance_change(old,new,decision_at=self.cut,source_pair_is_adjacent=True)
        b=sue_engine.earnings_evidence_brief(self.dossier(guidance_updates=[update]))
        assert update["midpoint_change"]==10
        assert "ISSUER_RANGE_CHANGE" in self.codes(b,"counterevidence")
        assert b["supporting_facts"]==[]

    def test_earlier_upgrade_is_not_counted_again_as_new_result(self):
        first=self.guidance(10400,11000,"2026-06-25T00:00:00Z","initial")
        updated=self.guidance(11100,11300,"2026-07-20T00:00:00Z","updated")
        # Deliberately synthetic timeline; only the amounts illustrate the historical decomposition.
        delivery=sue_engine.guidance_delivery(self.H._actual(11315),[first,updated],
            decision_at=self.cut,source_history_complete=True)
        b=sue_engine.earnings_evidence_brief(self.dossier(guidance_results=[delivery]))
        assert "EARLIER_GUIDANCE_ALREADY_KNOWN" in self.codes(b,"counterevidence")
        counter=next(x for x in b["counterevidence"] if x["code"]=="EARLIER_GUIDANCE_ALREADY_KNOWN")
        assert counter["values"]["earlier_midpoint_change"]==500
        assert counter["values"]["new_result_residual"]==115
        assert "not analyst consensus" in b["supporting_facts"][0]["text"]

    def test_incomplete_guidance_history_does_not_get_delivery_claim(self):
        delivery=sue_engine.guidance_delivery(self.H._actual(),[],decision_at=self.cut,source_history_complete=False)
        b=sue_engine.earnings_evidence_brief(self.dossier(guidance_results=[delivery]))
        assert "COMPLETE_PRE_RELEASE_ISSUER_GUIDANCE_HISTORY" in b["not_established"]
        assert not b["supporting_facts"]

    def test_dilution_scenario_is_not_promoted_to_verified_company_fact(self):
        bridge=sue_engine.per_share_bridge(old_income=100,new_income=120,old_shares=100,new_shares=150)
        b=sue_engine.earnings_evidence_brief(self.dossier(per_share=bridge))
        assert "INCOME_GROWTH_NOT_PER_SHARE_GROWTH" in self.codes(b,"counterevidence")
        assert "supplied per-share scenario" in b["counterevidence"][0]["text"]
        assert "not a source-qualified company fact" in b["counterevidence"][0]["text"]

    def test_price_ceiling_is_scenario_not_live_buy_permission(self):
        e=sue_engine.entry_economics(price=108,target=112,stop=96,win_cost=.4,loss_cost=.4,required_reward_risk=2)
        b=sue_engine.earnings_evidence_brief(self.dossier(entry=e))
        assert "PRICE_ABOVE_SCENARIO_CEILING" in self.codes(b,"counterevidence")
        assert "not a live quote" in b["counterevidence"][0]["text"]
        assert "CURRENT_MARKET_AND_PORTFOLIO_PERMISSION" in b["not_established"]

    def test_no_fact_count_can_change_authority(self):
        d=self.dossier(reported_changes=[self.change() for _ in range(30)])
        b=sue_engine.earnings_evidence_brief(d)
        assert len(b["supporting_facts"])==30
        assert all(v is False for v in b["authority"].values())
        assert "conviction" in b["interpretation"]

    def test_output_deepcopy_does_not_mutate_evidence(self):
        from copy import deepcopy
        d=self.dossier(reported_changes=[self.change()]);before=deepcopy(d)
        b=sue_engine.earnings_evidence_brief(d);b["supporting_facts"][0]["values"]["change_pct"]=999
        assert d==before

    def test_guidance_updates_reject_wrong_issuer(self):
        from dataclasses import replace
        x=self.guidance(90,100,"2026-07-01T00:00:00Z","old")
        y=self.guidance(110,120,"2026-07-15T00:00:00Z","new")
        update=sue_engine.guidance_change(x,y,decision_at=self.cut,source_pair_is_adjacent=True)
        update["basis"]["issuer_id"]="cik:other"
        with pytest.raises(sue_engine.EvidenceError,match="identity"):
            self.dossier(guidance_updates=[update])

    def test_guidance_update_after_decision_is_refused(self):
        x=self.guidance(90,100,"2026-07-01T00:00:00Z","old")
        y=self.guidance(110,120,"2026-07-15T00:00:00Z","new")
        update=sue_engine.guidance_change(x,y,decision_at="2026-08-01T00:00:00Z",source_pair_is_adjacent=True)
        with pytest.raises(sue_engine.EvidenceError,match="future"):
            self.dossier(guidance_updates=[update])

    def test_dossier_cannot_accept_update_that_used_future_actual(self):
        x=self.guidance(90,100,"2026-07-01T00:00:00Z","old")
        y=self.guidance(110,120,"2026-07-15T00:00:00Z","new")
        update=sue_engine.guidance_change(x,y,decision_at=self.cut,source_pair_is_adjacent=True)
        update["actual_result_used"]=True
        with pytest.raises(sue_engine.EvidenceError,match="future actual"):
            self.dossier(guidance_updates=[update])

    @pytest.mark.parametrize("value",[True,1,"false",None])
    def test_authority_cannot_be_smuggled_as_a_dossier_value(self,value):
        d=self.dossier();d["authority"]["entry"]=value
        with pytest.raises(sue_engine.EvidenceError,match="authoritative"):
            sue_engine.earnings_evidence_brief(d)

    def test_wrong_schema_is_not_an_earnings_case(self):
        with pytest.raises(sue_engine.EvidenceError,match="dossier required"):
            sue_engine.earnings_evidence_brief({"schema":"other"})

    def test_corrupted_child_authority_is_not_a_fact(self):
        d=self.dossier(reported_changes=[self.change()]);d["reported_changes"][0]["rank_authority"]=True
        with pytest.raises(sue_engine.EvidenceError,match="authoritative child"):
            sue_engine.earnings_evidence_brief(d)

    def test_corrupted_scenario_does_not_grant_buy_permission(self):
        d=self.dossier(entry=sue_engine.entry_economics(price=100,target=112,stop=96,win_cost=.4,loss_cost=.4,required_reward_risk=2))
        d["entry_economics"]["entry_permission"]=True
        with pytest.raises(sue_engine.EvidenceError,match="grant permission"):
            sue_engine.earnings_evidence_brief(d)



    def test_higher_cost_measure_is_not_treated_as_favorable_evidence(self):
        from dataclasses import replace
        change=self.change();change["metric"]="operating_expenses"
        b=sue_engine.earnings_evidence_brief(self.dossier(reported_changes=[change]))
        assert not b["supporting_facts"] and not b["counterevidence"]
        assert len(b["context_facts"])==1
        assert "DIRECTION_FOR_UNSUPPORTED_METRIC" in b["not_established"]

    def test_above_expected_costs_do_not_create_a_bullish_beat(self):
        basis=self.H._basis(metric="operating_expenses")
        x=sue_engine.surprise(self.H._actual(120,basis=basis),self.H._expectation(100,basis=basis),decision_at=self.cut)
        assert x["analyst_consensus_beat"] is None
        b=sue_engine.earnings_evidence_brief(self.dossier(surprises=[x]))
        assert not b["supporting_facts"]
        assert b["context_facts"][0]["code"]=="ABOVE_EXPECTATION"
        assert "DIRECTION_FOR_UNSUPPORTED_METRIC" in b["not_established"]


class TestProfitabilityBridge:
    H=TestEarningsEvidenceEngine
    cut="2026-07-30T20:35:00Z"

    def inputs(self,cr=1200,pr=1000,cp=108,pp=100,metric="operating_income"):
        from dataclasses import replace
        now=self.H._actual(cr)
        prior_basis=self.H._basis(fiscal_period="FY2025 Q3",start="2025-03-30",end="2025-06-28")
        prior=replace(now,value=pr,basis=prior_basis)
        now_profit=replace(now,value=cp,basis=replace(now.basis,metric=metric))
        prior_profit=replace(prior,value=pp,basis=replace(prior.basis,metric=metric))
        return [now,prior,now_profit,prior_profit]

    def compute(self,items=None):
        return sue_engine.profitability_bridge(*(items or self.inputs()),decision_at=self.cut)

    def test_profit_growth_can_hide_margin_compression(self):
        b=self.compute()
        assert b["revenue_change_fraction"]==pytest.approx(.2)
        assert b["profit_change"]==8
        assert b["margin_change_bps"]==pytest.approx(-100)
        assert b["revenue_component"]==pytest.approx(19)
        assert b["margin_component"]==pytest.approx(-11)
        assert b["revenue_component"]+b["margin_component"]==pytest.approx(8)
        assert "NOT_CAUSAL" in b["decomposition"]

    def test_constant_margin_has_only_revenue_component(self):
        b=self.compute(self.inputs(cp=120))
        assert b["margin_component"]==0
        assert b["revenue_component"]==20

    def test_flat_revenue_has_only_margin_component(self):
        b=self.compute(self.inputs(cr=1000,cp=120))
        assert b["revenue_component"]==0
        assert b["margin_component"]==pytest.approx(20)

    def test_loss_narrowing_does_not_require_positive_profit(self):
        b=self.compute(self.inputs(cp=-50,pp=-100))
        assert b["profit_change"]==50
        assert b["margin_change_bps"]>0
        assert b["current_profit"]<0
        assert "profit_growth_pct" not in b

    def test_crossing_break_even_is_preserved(self):
        b=self.compute(self.inputs(cp=50,pp=-100))
        assert b["profit_change"]==150
        assert b["current_margin"]>0 and b["prior_margin"]<0

    @pytest.mark.parametrize("metric",["gross_profit","operating_income","net_income"])
    def test_named_profit_measures_remain_separate(self,metric):
        b=self.compute(self.inputs(metric=metric));assert b["profit_metric"]==metric

    @pytest.mark.parametrize("field,value",[("unit","USD"),("currency","EUR"),
        ("accounting_basis","ADJUSTED"),("fiscal_period","FY2026 9M"),
        ("issuer_id","cik:other"),("share_basis","DILUTED")])
    def test_within_period_basis_mismatch_refused(self,field,value):
        from dataclasses import replace
        items=self.inputs();items[2]=replace(items[2],basis=replace(items[2].basis,**{field:value}))
        with pytest.raises(sue_engine.EvidenceError,match="basis mismatch"):
            self.compute(items)

    def test_different_source_event_refused(self):
        from dataclasses import replace
        items=self.inputs();items[2]=replace(items[2],event_id="other-event")
        with pytest.raises(sue_engine.EvidenceError,match="event mismatch"):
            self.compute(items)

    def test_same_period_reused_as_prior_is_not_a_comparison(self):
        from dataclasses import replace
        items=self.inputs();items[1]=replace(items[1],basis=items[0].basis)
        items[3]=replace(items[3],basis=items[2].basis)
        with pytest.raises(sue_engine.EvidenceError,match="overlap"):
            self.compute(items)

    def test_ytd_profit_cannot_be_divided_by_quarter_revenue(self):
        from dataclasses import replace
        items=self.inputs();items[2]=replace(items[2],basis=replace(items[2].basis,
            period_role="NINE_MONTHS",period_start="2025-09-28"))
        with pytest.raises(sue_engine.EvidenceError,match="basis mismatch"):
            self.compute(items)

    def test_future_available_comparator_is_not_usable(self):
        from dataclasses import replace
        items=self.inputs();items[3]=replace(items[3],available_at="2026-07-31T00:00:00Z")
        with pytest.raises(sue_engine.EvidenceError,match="unavailable"):
            self.compute(items)

    @pytest.mark.parametrize("value",[0,-1])
    def test_nonpositive_revenue_is_not_a_valid_margin_base(self,value):
        with pytest.raises(sue_engine.EvidenceError,match="denominators"):
            self.compute(self.inputs(pr=value))

    def test_income_and_revenue_scales_cannot_silently_mix(self):
        from dataclasses import replace
        items=self.inputs();items[2]=replace(items[2],basis=replace(items[2].basis,unit="USD_thousands"))
        with pytest.raises(sue_engine.EvidenceError,match="basis mismatch"):
            self.compute(items)

    def test_symmetric_identity_and_scale_invariance(self):
        from dataclasses import replace
        import random
        rng=random.Random(20261001)
        for _ in range(120):
            items=self.inputs(cr=rng.uniform(10,10000),pr=rng.uniform(10,10000),
                cp=rng.uniform(-500,3000),pp=rng.uniform(-500,3000))
            b=self.compute(items)
            assert b["revenue_component"]+b["margin_component"]==pytest.approx(b["profit_change"])
            scaled=self.compute([replace(x,value=float(x.value)*1000) for x in items])
            assert scaled["current_margin"]==pytest.approx(b["current_margin"])
            assert scaled["margin_change_bps"]==pytest.approx(b["margin_change_bps"])
            assert scaled["revenue_component"]==pytest.approx(b["revenue_component"]*1000)
            assert scaled["margin_component"]==pytest.approx(b["margin_component"]*1000)

    def test_comparable_same_release_prior_clock_is_not_fabricated(self):
        b=self.compute()
        assert b["current_event_id"]==b["prior_event_id"]
        assert len(set(b["source_available_at"]))==1

    def test_bridge_reaches_dossier_and_user_explanation(self):
        b=self.compute()
        d=sue_engine.factual_dossier(event_id=b["current_event_id"],issuer_id=b["issuer_id"],
            decision_at=self.cut,profit_bridges=[b],source_contract_refs=["fixture-qualified"])
        out=sue_engine.earnings_evidence_brief(d)
        c=next(x for x in out["counterevidence"] if x["code"]=="MARGIN_COMPRESSION")
        assert c["values"]["margin_change_bps"]==pytest.approx(-100)
        assert c["values"]["profit_change"]==8
        assert "Operating margin" in c["text"]
        assert all(v is False for v in out["authority"].values())

    def test_foreign_bridge_cannot_be_put_in_another_dossier(self):
        b=self.compute()
        with pytest.raises(sue_engine.EvidenceError,match="identity mismatch"):
            sue_engine.factual_dossier(event_id="other",issuer_id=b["issuer_id"],
                decision_at=self.cut,profit_bridges=[b],source_contract_refs=["fixture"])

    def test_three_profit_metrics_are_not_three_independent_confidence_votes(self):
        bridges=[self.compute(self.inputs(metric=x)) for x in ["gross_profit","operating_income","net_income"]]
        d=sue_engine.factual_dossier(event_id=bridges[0]["current_event_id"],issuer_id=bridges[0]["issuer_id"],
            decision_at=self.cut,profit_bridges=bridges,source_contract_refs=["same-financial-statement"])
        out=sue_engine.earnings_evidence_brief(d)
        assert len(out["counterevidence"])==3
        assert "score" not in out and all(v is False for v in out["authority"].values())


class TestReportedChangeChronology:
    """A restatement, reversed pair or overlapping period is not operating growth."""
    @staticmethod
    def actual(value, start, end, *, event="fixture-release", metric="revenue"):
        basis=sue_engine.MetricBasis(
            issuer_id="cik:fixture", issuer_name="Fictional statement issuer",
            metric=metric, fiscal_period=start+":"+end,
            period_role="QUARTER", period_start=start, period_end=end,
            currency="USD", unit="USD_millions", accounting_basis="GAAP")
        return sue_engine.Actual(basis=basis,value=value,
            public_at="2026-09-28T12:00:00Z",available_at="2026-09-28T12:01:00Z",
            source_ref="fixture:comparative-statement",event_id=event)

    @pytest.mark.parametrize("current_dates,prior_dates", [
        (("2025-04-01","2025-06-30"),("2026-04-01","2026-06-30")),
        (("2026-04-01","2026-06-30"),("2026-04-01","2026-06-30")),
        (("2026-05-01","2026-07-31"),("2026-04-01","2026-06-30")),
        (("2026-06-30","2026-09-28"),("2026-04-01","2026-06-30")),
    ])
    def test_reversed_identical_overlapping_and_shared_boundary_refused(self,current_dates,prior_dates):
        with pytest.raises(sue_engine.EvidenceError,match="periods must be nonoverlapping and chronological"):
            sue_engine.reported_change(self.actual(120,*current_dates),
                self.actual(100,*prior_dates),decision_at="2026-09-28T13:00:00Z")

    def test_sequential_periods_remain_comparable(self):
        out=sue_engine.reported_change(self.actual(120,"2026-04-01","2026-06-30"),
            self.actual(100,"2026-01-01","2026-03-31"),decision_at="2026-09-28T13:00:00Z")
        assert out["change_pct"]==pytest.approx(20)
        assert out["current_event_id"]==out["prior_event_id"]=="fixture-release"

    def test_same_table_prior_year_remains_source_bound(self):
        out=sue_engine.reported_change(self.actual(120,"2026-04-01","2026-06-30"),
            self.actual(100,"2025-04-01","2025-06-30"),decision_at="2026-09-28T13:00:00Z")
        d=sue_engine.factual_dossier(event_id="fixture-release",issuer_id="cik:fixture",
            decision_at="2026-09-28T13:00:00Z",reported_changes=[out],
            source_contract_refs=["fixture:comparative-statement"])
        assert d["reported_changes"][0]["change_pct"]==pytest.approx(20)
        assert out["current_available_at"]==out["prior_available_at"]
        assert all(x is False for x in d["authority"].values())

    def test_changed_source_identity_cannot_turn_restatement_into_growth(self):
        with pytest.raises(sue_engine.EvidenceError,match="periods must be nonoverlapping and chronological"):
            sue_engine.reported_change(self.actual(120,"2026-04-01","2026-06-30",event="revision2"),
                self.actual(100,"2026-04-01","2026-06-30",event="revision1"),
                decision_at="2026-09-28T13:00:00Z")

    def test_loss_reduction_preserves_signed_economic_change(self):
        out=sue_engine.reported_change(self.actual(-80,"2026-04-01","2026-06-30",metric="net_income"),
            self.actual(-100,"2025-04-01","2025-06-30",metric="net_income"),decision_at="2026-09-28T13:00:00Z")
        assert out["signed_difference"]==20
        assert out["change_pct"]==pytest.approx(20)

    def test_difference_overflow_does_not_produce_nonfinite_evidence(self):
        with pytest.raises(sue_engine.EvidenceError,match="reported-change difference overflow"):
            sue_engine.reported_change(self.actual(1e308,"2026-04-01","2026-06-30",metric="net_income"),
                self.actual(-1e308,"2025-04-01","2025-06-30",metric="net_income"),
                decision_at="2026-09-28T13:00:00Z")


class TestEarningsValuationScenario:
    """Explicit scenario economics, never a forecast or observed live quote."""
    @staticmethod
    def actual(value=5, *, role="ANNUAL", unit="USD_per_share", share_basis="DILUTED", available="2026-01-30T13:00:00Z"):
        basis=sue_engine.MetricBasis(issuer_id="cik:scenario",issuer_name="Fictional annual issuer",
            metric="EPS",fiscal_period="FY2025",period_role=role,
            period_start="2025-01-01",period_end="2025-12-31",currency="USD",
            unit=unit,accounting_basis="GAAP",share_basis=share_basis)
        return sue_engine.Actual(basis=basis,value=value,public_at="2026-01-30T12:00:00Z",
            available_at=available,source_ref="fixture:annual-eps",event_id="fixture:annual")

    def scenario(self, actual=None, **changes):
        args=dict(reference_price=100,terminal_eps=7,terminal_pe=14,cash_distributions=4,
                  horizon_years=3,required_annual_return=.1,decision_at="2026-09-28T13:00:00Z")
        args.update(changes)
        return sue_engine.earnings_valuation_scenario(actual or self.actual(),**args)

    def dossier(self,scenario):
        return sue_engine.factual_dossier(event_id="fixture:annual",issuer_id="cik:scenario",
            decision_at="2026-09-28T13:00:00Z",source_contract_refs=["fixture:annual-eps"],
            valuation_case=scenario)

    def test_earnings_growth_does_not_hide_multiple_compression(self):
        out=self.scenario()
        assert out["terminal_price_assumption"]==98
        assert out["scenario_total_return_before_costs"]==pytest.approx(.02)
        assert out["eps_change_price_component"]==pytest.approx(34)
        assert out["multiple_change_price_component"]==pytest.approx(-36)
        assert out["cash_distribution_price_component"]==4
        assert out["within_scenario_price_ceiling"] is False
        assert out["estimated_win_probability"] is None
        assert out["entry_permission"] is False

    def test_hurdle_is_earnings_required_not_forecast(self):
        out=self.scenario()
        assert out["required_terminal_eps_for_hurdle"]==pytest.approx((100*1.1**3-4)/14)
        assert out["required_terminal_eps_change_fraction"]==pytest.approx(((100*1.1**3-4)/14)/5-1)
        assert out["maximum_reference_price_for_hurdle"]==pytest.approx(102/1.1**3)
        assert out["forecast_origin"]=="SUPPLIED_SCENARIO_NOT_MODEL_PREDICTION"

    def test_higher_price_lowers_scenario_return_not_terminal_value(self):
        a=self.scenario();b=self.scenario(reference_price=110)
        assert b["scenario_total_return_before_costs"]<a["scenario_total_return_before_costs"]
        assert b["maximum_reference_price_for_hurdle"]==a["maximum_reference_price_for_hurdle"]
        assert b["required_terminal_eps_for_hurdle"]>a["required_terminal_eps_for_hurdle"]

    def test_twice_eps_half_multiple_does_not_double_share_price(self):
        out=self.scenario(terminal_eps=10,terminal_pe=10,cash_distributions=0)
        assert out["terminal_price_assumption"]==100
        assert out["scenario_total_return_before_costs"]==0
        assert out["eps_change_price_component"]+out["multiple_change_price_component"]==pytest.approx(0)

    def test_common_per_share_currency_rescaling_preserves_return(self):
        a=self.scenario();b=self.scenario(self.actual(5000),reference_price=100000,terminal_eps=7000,cash_distributions=4000)
        for key in ["reference_price_to_annual_eps","scenario_total_return_before_costs","scenario_annualized_return_before_costs","required_terminal_eps_change_fraction"]:
            assert b[key]==pytest.approx(a[key])
        assert b["maximum_reference_price_for_hurdle"]==pytest.approx(1000*a["maximum_reference_price_for_hurdle"])

    @pytest.mark.parametrize("actual_eps,terminal_eps",[(0,7),(-5,7),(5,0),(5,-7)])
    def test_nonpositive_earnings_do_not_create_a_pe_valuation(self,actual_eps,terminal_eps):
        out=self.scenario(self.actual(actual_eps),terminal_eps=terminal_eps)
        assert out["status"]=="PE_MODEL_NOT_APPLICABLE_NONPOSITIVE_EARNINGS"
        assert "required_terminal_eps_for_hurdle" not in out

    @pytest.mark.parametrize("change",[
        {"reference_price":0},{"terminal_pe":0},{"cash_distributions":-1},
        {"horizon_years":0},{"required_annual_return":-1},{"reference_price":True},
        {"terminal_eps":float("nan")},{"terminal_pe":float("inf")},
    ])
    def test_invalid_scenario_assumptions_refused(self,change):
        with pytest.raises(sue_engine.EvidenceError):self.scenario(**change)

    def test_quarterly_earnings_cannot_be_implicitly_annualized(self):
        with pytest.raises(sue_engine.EvidenceError,match="annual or TTM"):
            self.scenario(self.actual(role="QUARTER"))

    def test_total_dollars_cannot_be_treated_as_per_share_eps(self):
        with pytest.raises(sue_engine.EvidenceError,match="currency/per-share unit"):
            self.scenario(self.actual(unit="USD_millions"))

    def test_basic_and_diluted_share_bases_are_not_interchangeable(self):
        with pytest.raises(sue_engine.EvidenceError,match="diluted EPS"):
            self.scenario(self.actual(share_basis="BASIC"))

    def test_future_source_eps_cannot_enter_the_current_scenario(self):
        with pytest.raises(sue_engine.EvidenceError,match="unavailable at decision"):
            self.scenario(self.actual(available="2026-09-29T13:00:00Z"))

    def test_large_assumptions_fail_without_nonfinite_json(self):
        with pytest.raises(sue_engine.EvidenceError,match="overflow"):
            self.scenario(terminal_eps=1e308,terminal_pe=1e308)

    def test_assumed_cash_hurdle_does_not_require_negative_earnings(self):
        out=self.scenario(cash_distributions=200)
        assert out["required_terminal_eps_for_hurdle"]==0
        assert out["hurdle_covered_by_assumed_distributions"] is True
        assert out["entry_permission"] is False

    def test_existing_dossier_and_brief_preserve_scenario_identity(self):
        case=self.scenario();d=self.dossier(case);brief=sue_engine.earnings_evidence_brief(d)
        assert brief["valuation_scenario"]==case
        assert brief["valuation_scenario"]["price_origin"]=="SUPPLIED_SCENARIO_NOT_VERIFIED_QUOTE"
        assert all(x is False for x in d["authority"].values())
        case["terminal_eps_assumption"]=999
        assert d["valuation_scenario"]["terminal_eps_assumption"]==7
        assert brief["valuation_scenario"]["terminal_eps_assumption"]==7

    @pytest.mark.parametrize("field,value",[("issuer_id","cik:other"),("event_id","other"),("decision_at","2026-10-01T00:00:00Z"),("entry_permission",True),("price_origin","OBSERVED_LIVE_QUOTE")])
    def test_wrong_binding_or_false_permission_refused(self,field,value):
        x=self.scenario();x[field]=value
        with pytest.raises(sue_engine.EvidenceError):self.dossier(x)

    def test_original_dossier_without_valuation_remains_unchanged(self):
        d=sue_engine.factual_dossier(event_id="fixture:annual",issuer_id="cik:scenario",
            decision_at="2026-09-28T13:00:00Z",source_contract_refs=["fixture:annual-eps"])
        assert "valuation_scenario" not in d
        assert "valuation_scenario" not in sue_engine.earnings_evidence_brief(d)


    @pytest.mark.parametrize("field,value",[("within_scenario_price_ceiling",True),
        ("scenario_total_return_before_costs",1.0),("estimated_win_probability",.99),
        ("maximum_reference_price_for_hurdle",1000)])
    def test_altered_arithmetic_or_invented_probability_cannot_enter_brief(self,field,value):
        case=self.scenario();case[field]=value
        with pytest.raises(sue_engine.EvidenceError,match="arithmetic or shape mismatch"):
            self.dossier(case)

    def test_unavailable_pe_case_remains_unavailable_through_brief(self):
        case=self.scenario(self.actual(-1));d=self.dossier(case)
        brief=sue_engine.earnings_evidence_brief(d)
        assert brief["valuation_scenario"]["status"]=="PE_MODEL_NOT_APPLICABLE_NONPOSITIVE_EARNINGS"
        assert "maximum_reference_price_for_hurdle" not in brief["valuation_scenario"]


class TestEarningsFiniteOutput:
    """Exact review regressions; extreme synthetic values are not market cases."""
    H = TestEarningsEvidenceEngine

    def test_reported_percent_overflow_is_typed_error(self):
        current=self.H._actual(1e308)
        prior=self.H._actual(1,basis=self.H._basis(fiscal_period="FY2025 Q3",
            start="2025-03-30",end="2025-06-28"))
        with pytest.raises(sue_engine.EvidenceError,match="overflow"):
            sue_engine.reported_change(current,prior,decision_at="2026-07-30T21:00:00Z")

    def test_even_median_avoids_overflowing_intermediate_sum(self):
        import json
        rows=[self.H._forecast(c,0,"2026-07-01T00:00:00Z",c+"0") for c in ["A","B"]]
        rows += [self.H._forecast(c,1e308,"2026-07-15T00:00:00Z",c+"1") for c in ["A","B"]]
        out=sue_engine.matched_revisions(rows,basis=self.H._basis(),
            before="2026-07-02T00:00:00Z",after="2026-07-16T00:00:00Z")
        assert out["matched_median_change"]==1e308
        json.dumps(out,allow_nan=False)

    def test_changing_roster_aggregate_overflow_is_not_serialized(self):
        rows=[self.H._forecast("OLD",-1e308,"2026-07-01T00:00:00Z","old",
                valid_until="2026-07-10T00:00:00Z"),
              self.H._forecast("NEW",1e308,"2026-07-15T00:00:00Z","new")]
        with pytest.raises(sue_engine.EvidenceError,match="overflow"):
            sue_engine.matched_revisions(rows,basis=self.H._basis(),
                before="2026-07-02T00:00:00Z",after="2026-07-16T00:00:00Z")

    def test_ordinary_reported_change_retains_numeric_contract(self):
        import json
        current=self.H._actual(12)
        prior=self.H._actual(10,basis=self.H._basis(fiscal_period="FY2025 Q3",
            start="2025-03-30",end="2025-06-28"))
        out=sue_engine.reported_change(current,prior,decision_at="2026-07-30T21:00:00Z")
        assert out["change_pct"]==20 and out["change_fraction"]==.2
        json.dumps(out,allow_nan=False)


class TestCashFlowReconciliation:
    H=TestEarningsEvidenceEngine
    decision="2026-07-30T21:00:00Z"

    @classmethod
    def fact(cls,metric,value,**kwargs):
        from dataclasses import replace
        b=cls.H._basis(metric=metric)
        b=replace(b,**kwargs.pop("basis_changes",{}))
        return cls.H._actual(value,basis=b,source_ref="fixture:cash:"+metric,**kwargs)

    @classmethod
    def component(cls,item_id,value,category="WORKING_CAPITAL",**kwargs):
        return sue_engine.CashFlowComponent(item_id,category,cls.fact("cash_flow_adjustment",value,**kwargs))

    @classmethod
    def build(cls,ni=100,cfo=160,complete=True,components=None,capex=40):
        return sue_engine.cash_flow_reconciliation(cls.fact("net_income",ni),cls.fact("operating_cash_flow",cfo),
            components=components if components is not None else [
                cls.component("da",20,"DEPRECIATION_AMORTIZATION"),
                cls.component("sbc",10,"SHARE_BASED_COMPENSATION"),
                cls.component("wc",30)],
            source_reconciliation_complete=complete,
            capex_outflow=None if capex is None else cls.fact("capital_expenditures",capex),
            decision_at=cls.decision)

    @classmethod
    def dossier(cls,case):
        return sue_engine.factual_dossier(event_id=case["event_id"],issuer_id=case["issuer_id"],
            decision_at=cls.decision,source_contract_refs=["fixture:qualified_cash_input"],cash_flows=[case])

    def test_source_components_reconcile_without_automatic_quality_bonus(self):
        import json
        out=self.build()
        assert out["reconciliation_state"]=="COMPLETE_RECONCILIATION"
        assert out["reported_adjustments_total"]==60 and out["unexplained_residual"]==0
        assert out["operating_cash_to_positive_income"]==1.6
        assert out["cash_less_gross_capex"]==120
        assert out["component_totals"]["WORKING_CAPITAL"]==30
        brief=sue_engine.earnings_evidence_brief(self.dossier(out))
        assert brief["supporting_facts"]==[]
        assert {x["code"] for x in brief["context_facts"]}>={"WORKING_CAPITAL_CASH_RELEASE","NONCASH_COMPENSATION_RECONCILIATION","OPERATING_CASH_LESS_GROSS_CAPEX"}
        assert all(x is False for x in brief["authority"].values())
        json.dumps(out,allow_nan=False);json.dumps(brief,allow_nan=False)

    def test_profit_with_negative_operating_cash_is_visible_counterevidence(self):
        out=self.build(cfo=-20,components=[self.component("wc",-120)],capex=None)
        brief=sue_engine.earnings_evidence_brief(self.dossier(out))
        assert out["operating_cash_to_positive_income"]==-.2
        assert out["cash_less_gross_capex"] is None
        assert any(x["code"]=="PROFIT_WITHOUT_POSITIVE_OPERATING_CASH" for x in brief["counterevidence"])

    @pytest.mark.parametrize("income,cash",[(0,10),(-100,-20),(-100,20)])
    def test_nonpositive_income_has_no_misleading_conversion_ratio(self,income,cash):
        out=self.build(ni=income,cfo=cash,components=[],complete=False)
        assert out["operating_cash_to_positive_income"] is None
        assert out["ratio_unavailable_reason"]=="NONPOSITIVE_INCOME"
        assert out["reconciliation_state"]=="PARTIAL_RECONCILIATION"

    def test_zero_residual_does_not_certify_missing_components(self):
        out=self.build(ni=100,cfo=100,components=[],complete=False)
        assert out["unexplained_residual"]==0
        assert out["reconciliation_state"]=="PARTIAL_RECONCILIATION"
        assert out["component_totals"]=={}
        assert "COMPLETE_CASH_FLOW_COMPONENT_RECONCILIATION" in sue_engine.earnings_evidence_brief(self.dossier(out))["not_established"]

    def test_incorrect_complete_assertion_is_unreconciled_not_a_pass(self):
        out=self.build(cfo=200)
        assert out["unexplained_residual"]==40
        assert out["reconciliation_state"]=="UNRECONCILED"
        brief=sue_engine.earnings_evidence_brief(self.dossier(out))
        assert "COMPLETE_CASH_FLOW_COMPONENT_RECONCILIATION" in brief["not_established"]

    def test_partial_reported_adjustments_are_not_filled_with_zeros(self):
        out=self.build(components=[self.component("da",20,"DEPRECIATION_AMORTIZATION")],complete=False)
        assert out["unexplained_residual"]==40
        assert "WORKING_CAPITAL" not in out["component_totals"]

    def test_same_amounts_different_sources_of_cash_are_not_independent_votes(self):
        one=self.build(components=[self.component("da",60,"DEPRECIATION_AMORTIZATION")])
        two=self.build(components=[self.component("wc",60)])
        assert one["operating_cash_to_positive_income"]==two["operating_cash_to_positive_income"]
        assert one["component_totals"]!=two["component_totals"]
        assert all(sue_engine.earnings_evidence_brief(self.dossier(x))["supporting_facts"]==[] for x in [one,two])

    def test_capex_outflow_sign_cannot_be_guessed(self):
        with pytest.raises(sue_engine.EvidenceError,match="outflow magnitude"):
            self.build(capex=-40)

    @pytest.mark.parametrize("changes",[
        {"issuer_id":"cik:other"},{"period_role":"NINE_MONTHS"},
        {"period_start":"2026-01-01"},{"period_end":"2026-06-28"},
        {"fiscal_period":"FY2026 9M"},{"currency":"EUR"},{"unit":"USD"},
        {"accounting_basis":"ADJUSTED"},{"share_basis":"DILUTED"}])
    def test_cash_comparison_refuses_inconsistent_reporting_basis(self,changes):
        with pytest.raises(sue_engine.EvidenceError,match="basis mismatch"):
            sue_engine.cash_flow_reconciliation(self.fact("net_income",100),
                self.fact("operating_cash_flow",100,basis_changes=changes),
                source_reconciliation_complete=False,decision_at=self.decision)

    def test_cash_components_cannot_come_from_another_event(self):
        with pytest.raises(sue_engine.EvidenceError,match="event mismatch"):
            self.build(components=[self.component("wc",60,event_id="other-event")])

    def test_future_adjustment_cannot_enter_an_earlier_decision(self):
        with pytest.raises(sue_engine.EvidenceError,match="unavailable"):
            self.build(components=[self.component("wc",60,available_at="2026-07-31T00:00:00Z")])

    def test_duplicate_statement_item_is_refused(self):
        row=self.component("wc",30)
        with pytest.raises(sue_engine.EvidenceError,match="duplicate"):
            self.build(components=[row,row])

    @pytest.mark.parametrize("complete",[None,1,"true"])
    def test_completeness_is_explicit_boolean(self,complete):
        with pytest.raises(sue_engine.EvidenceError,match="completeness"):
            self.build(complete=complete)

    def test_capex_does_not_equal_issuer_adjusted_free_cash_flow(self):
        out=self.build(ni=8539,cfo=17525,components=[],complete=False,capex=15857)
        assert out["cash_less_gross_capex"]==1668
        assert out["cash_less_gross_capex"]!=3721
        assert "NOT_ISSUER_ADJUSTED" in out["cash_after_capex_interpretation"]

    def test_micron_annual_statement_values_reconcile_in_synthetic_clock_fixture(self):
        components=[self.component("da",8352,"DEPRECIATION_AMORTIZATION"),
            self.component("sbc",972,"SHARE_BASED_COMPENSATION"),
            self.component("ar",-1776),self.component("inventory",520),
            self.component("ap",862),self.component("other_current_liabilities",-272),
            self.component("other",328,"OTHER")]
        # Numeric exercise only; source period/clock classes are fictional here.
        out=self.build(ni=8539,cfo=17525,components=components,capex=15857)
        assert out["reported_adjustments_total"]==8986 and out["unexplained_residual"]==0
        assert out["component_totals"]["WORKING_CAPITAL"]==-666
        assert out["reconciliation_state"]=="COMPLETE_RECONCILIATION"

    def test_common_unit_scaling_preserves_ratios_and_state(self):
        from dataclasses import replace
        original=self.build();scale=1e6
        inputs=original["source_inputs"]
        def actual(raw):
            basis=sue_engine.MetricBasis(**{**raw["basis"],"unit":"USD"})
            return sue_engine.Actual(**{**raw,"basis":basis,"value":raw["value"]*scale})
        rescaled=sue_engine.cash_flow_reconciliation(actual(inputs["income"]),actual(inputs["operating_cash"]),
            components=[sue_engine.CashFlowComponent(x["item_id"],x["category"],actual(x["fact"])) for x in inputs["components"]],
            source_reconciliation_complete=True,capex_outflow=actual(inputs["capex_outflow"]),decision_at=self.decision)
        assert rescaled["operating_cash_to_positive_income"]==original["operating_cash_to_positive_income"]
        assert rescaled["cash_less_gross_capex"]==original["cash_less_gross_capex"]*scale
        assert rescaled["reconciliation_state"]==original["reconciliation_state"]

    def test_child_recomputation_refuses_altered_explanation(self):
        from copy import deepcopy
        for key,value in [("reported_operating_cash",999),("unexplained_residual",99),
            ("rank_authority",1),("cash_less_gross_capex",999),("reconciliation_state","ALL_GOOD")]:
            with pytest.raises(sue_engine.EvidenceError,match="changed"):
                out=deepcopy(self.build());out[key]=value;self.dossier(out)

    def test_cross_issuer_and_cross_event_dossier_refuse(self):
        out=self.build()
        for kwargs in [{"issuer_id":"other","event_id":out["event_id"]},
                       {"issuer_id":out["issuer_id"],"event_id":"other"}]:
            with pytest.raises(sue_engine.EvidenceError,match="identity"):
                sue_engine.factual_dossier(**kwargs,decision_at=self.decision,
                    source_contract_refs=["fixture"],cash_flows=[out])

    def test_future_dossier_cut_refused(self):
        out=self.build()
        with pytest.raises(sue_engine.EvidenceError,match="future"):
            sue_engine.factual_dossier(issuer_id=out["issuer_id"],event_id=out["event_id"],
                decision_at="2026-07-30T20:59:59Z",source_contract_refs=["fixture"],cash_flows=[out])

    def test_output_copies_do_not_share_inputs_or_dossier(self):
        from copy import deepcopy
        out=self.build();before=deepcopy(out);d=self.dossier(out)
        d["cash_flow_reconciliations"][0]["source_inputs"]["components"][0]["fact"]["value"]=999
        assert out==before

    def test_no_cash_inputs_are_truthfully_missing_in_existing_brief(self):
        d=sue_engine.factual_dossier(event_id="fixture",issuer_id="cik:fixture",
            decision_at=self.decision,source_contract_refs=["fixture"])
        assert "cash_flow_reconciliations" not in d
        assert "MATCHED_PERIOD_CASH_FLOW_RECONCILIATION" in sue_engine.earnings_evidence_brief(d)["not_established"]

    def test_tiny_positive_income_does_not_serialize_infinite_ratio(self):
        import json
        out=self.build(ni=1e-308,cfo=1e308,components=[],complete=False,capex=None)
        assert out["operating_cash_to_positive_income"] is None
        assert out["ratio_unavailable_reason"]=="RATIO_OUT_OF_RANGE"
        json.dumps(out,allow_nan=False)

    def test_extreme_cash_gap_returns_typed_overflow(self):
        with pytest.raises(sue_engine.EvidenceError,match="overflow"):
            self.build(ni=-1e308,cfo=1e308,components=[],complete=False,capex=None)


# Program-CEO whole-source repair regressions — #8189 / 5968194695
class TestEarningsWholeSourceRepair:
    decision = "2026-07-01T21:00:00Z"
    public = "2026-07-01T20:00:00Z"

    @staticmethod
    def basis(metric="revenue", *, current=True):
        return sue_engine.MetricBasis(
            issuer_id="ISS:A", issuer_name="Issuer A", metric=metric,
            fiscal_period="FY2026 Q2" if current else "FY2025 Q2",
            period_role="QUARTER",
            period_start="2026-04-01" if current else "2025-04-01",
            period_end="2026-06-30" if current else "2025-06-30",
            currency="USD", unit="USD_millions", accounting_basis="GAAP",
            share_basis="NOT_APPLICABLE",
        )

    @classmethod
    def actual(cls, value=120.0, *, current=True, event="evt"):
        return sue_engine.Actual(
            cls.basis(current=current), value, cls.public, "2026-07-01T20:01:00Z",
            f"source:{'cur' if current else 'prior'}", event,
        )

    @classmethod
    def reported(cls):
        return sue_engine.reported_change(
            cls.actual(), cls.actual(100, current=False, event="evt-prior"),
            decision_at=cls.decision,
        )

    @classmethod
    def dossier(cls, **kwargs):
        return sue_engine.factual_dossier(
            event_id="evt", issuer_id="ISS:A", decision_at=cls.decision,
            source_contract_refs=["contract:test"], **kwargs,
        )

    def test_entry_extreme_finite_inputs_fail_typed_before_infinite_output(self):
        with pytest.raises(sue_engine.EvidenceError, match="entry scenario arithmetic overflow"):
            sue_engine.entry_economics(
                price=1e-308, target=1e308, stop=5e-324,
                win_cost=0.0, loss_cost=0.0, required_reward_risk=1.0,
            )

    @pytest.mark.parametrize("value", [1, 0, "false"])
    def test_reported_child_authority_must_be_literal_false(self, value):
        item = self.reported()
        item["rank_authority"] = value
        with pytest.raises(sue_engine.EvidenceError, match="authoritative child"):
            self.dossier(reported_changes=[item])

    @pytest.mark.parametrize("value", [1, 0, "false"])
    def test_entry_permission_must_be_literal_false(self, value):
        item = sue_engine.entry_economics(
            price=100, target=120, stop=90, win_cost=0, loss_cost=0,
            required_reward_risk=2,
        )
        item["entry_permission"] = value
        with pytest.raises(sue_engine.EvidenceError, match="authoritative child"):
            self.dossier(entry=item)

    def test_dossier_recomputes_reported_arithmetic(self):
        item = self.reported()
        item["signed_difference"] = 999.0
        item["change_pct"] = 999.0
        with pytest.raises(sue_engine.EvidenceError, match="reported-change .* mismatch"):
            self.dossier(reported_changes=[item])

    def test_dossier_rejects_reported_source_after_child_decision(self):
        item = self.reported()
        item["current_available_at"] = "2099-01-01T00:00:00Z"
        with pytest.raises(sue_engine.EvidenceError, match="source evidence is from the future"):
            self.dossier(reported_changes=[item])

    def test_brief_revalidates_reported_child_after_dossier_construction(self):
        dossier = self.dossier(reported_changes=[self.reported()])
        dossier["reported_changes"][0]["change_pct"] = 999.0
        with pytest.raises(sue_engine.EvidenceError, match="reported-change percent mismatch"):
            sue_engine.earnings_evidence_brief(dossier)

    def test_guidance_delivery_preserves_actual_first_revision_public_time(self):
        b = self.basis()
        actual = sue_engine.Actual(
            b, 125, self.public, "2026-07-01T20:01:00Z", "source:a", "evt")
        first = sue_engine.IssuerGuidance(
            b, 100, 110, "2026-04-01T12:00:00Z", "2026-04-01T12:01:00Z",
            "g1", "source:g1")
        latest = sue_engine.IssuerGuidance(
            b, 110, 120, "2026-06-01T12:00:00Z", "2026-06-01T12:01:00Z",
            "g2", "source:g2")
        out = sue_engine.guidance_delivery(
            actual, [first, latest], decision_at=self.decision,
            source_history_complete=True)
        assert out["selected_revision_id"] == "g2"
        assert out["earlier_revision_public_at"] == first.public_at

    def test_guidance_withdrawal_restart_withholds_continuous_earlier_clock(self):
        b = self.basis()
        actual = sue_engine.Actual(
            b, 125, self.public, "2026-07-01T20:01:00Z", "source:a", "evt")
        first = sue_engine.IssuerGuidance(
            b, 100, 110, "2026-03-01T12:00:00Z", "2026-03-01T12:01:00Z",
            "g1", "source:g1")
        withdrawn = sue_engine.IssuerGuidance(
            b, None, None, "2026-04-01T12:00:00Z", "2026-04-01T12:01:00Z",
            "g2", "source:g2", state="WITHDRAWN")
        restarted = sue_engine.IssuerGuidance(
            b, 110, 120, "2026-06-01T12:00:00Z", "2026-06-01T12:01:00Z",
            "g3", "source:g3")
        out = sue_engine.guidance_delivery(
            actual, [first, withdrawn, restarted], decision_at=self.decision,
            source_history_complete=True)
        assert out["selected_revision_id"] == "g3"
        assert out["initial_to_latest_midpoint_change"] is None
        assert out["earlier_revision_public_at"] is None

    def test_same_release_comparative_clocks_remain_valid(self):
        current = self.actual()
        prior = self.actual(100, current=False, event="evt-prior")
        current = sue_engine.Actual(
            current.basis, current.value, self.public, "2026-07-01T20:01:00Z",
            current.source_ref, current.event_id)
        prior = sue_engine.Actual(
            prior.basis, prior.value, self.public, "2026-07-01T20:01:00Z",
            prior.source_ref, prior.event_id)
        change = sue_engine.reported_change(current, prior, decision_at=self.decision)
        dossier = self.dossier(reported_changes=[change])
        assert dossier["reported_changes"][0]["change_pct"] == pytest.approx(20.0)
        assert sue_engine.earnings_evidence_brief(dossier)["schema"] == "prophet.earnings_evidence_brief/v1"
