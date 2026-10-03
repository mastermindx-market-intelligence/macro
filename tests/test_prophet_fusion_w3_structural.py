"""PR-3B: outcome-blind LOFO + member census. Zero authority.

These tests pin the structural diagnostic path against the ten required
mutations. They never load grades, never compute IC/alpha/returns, and never
touch ``data/us_prophet_rank/w3``.
"""

from __future__ import annotations

import copy
import json

import pytest

from engine import us_board_rank as ubr
from engine import us_prophet_fusion as fus


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


def _live_pool():
    return [
        _row("BROAD", alpha=0.1, off_high=-3.0, tier="T2", sue_z=2.0,
             smartmoney=True, insiders=3, gex="confirm", news=5),
        _row("NARROW", alpha=9.0, off_high=-1.0, tier="T2", gex="neutral"),
        _row("MID", alpha=4.0, off_high=-8.0, tier="T1", sue_z=1.0,
             smartmoney=True, insiders=0, gex="neutral", news=0),
    ]


def _plane(family_scores, *, voting=None, dropped=None, collapsed=None,
           extracted=None, admission=None, families_present=None):
    scores = []
    for families in family_scores:
        present = [value for value in families.values()]
        scores.append(None if not present else (sum(present) / len(present)) * 100.0)
    present_names = families_present if families_present is not None else sorted({
        family for row in family_scores for family in row
    })
    return fus.FusionPlane(
        scores=scores,
        family_scores=family_scores,
        member_percentiles=[{} for _ in family_scores],
        families_present=list(present_names),
        families_absent=[],
        members_voting=list(voting or []),
        members_dropped=list(dropped or []),
        members_collapsed=list(collapsed or []),
        admission=admission,
        extracted_members=tuple(extracted or ()),
    )


def _keys(tickers, stages, ranks=None):
    out = []
    for i, ticker in enumerate(tickers):
        item = {"ticker": ticker, "stage": stages[i]}
        if ranks is not None:
            item["score_rank"] = ranks[i]
        out.append(item)
    return out


# --------------------------------------------------------------------------- #
# 1. high tie-share still shows planted LOFO movement
# --------------------------------------------------------------------------- #

class TestHighTieShareIsNotAUsefulnessProxy:
    def test_a_high_tie_share_family_still_shows_large_planted_lofo_movement(self):
        """38/40 rows share one F1 value (tie-share 0.95); two stars sit at 1.0.

        After ablation every remaining family is flat, so the stars fall from
        rank 1-2 to ticker-last. Tie-share cannot be allowed to hide that.
        """
        pack = [f"A{i:02d}" for i in range(38)]
        stars = ["YYY", "ZZZ"]
        tickers = stars + pack
        stages = ["live"] * 40
        family_scores = []
        for ticker in tickers:
            f1 = 1.0 if ticker in stars else 0.5
            family_scores.append({
                "F1_TECHNICAL_CONFLUENCE": f1,
                "F2_MOMENTUM_EXTENSION": 0.5,
            })
        plane = _plane(family_scores)
        diag = fus.diagnose_structure(_keys(tickers, stages), plane)
        row = {item["family"]: item for item in diag["lofo"]}["F1_TECHNICAL_CONFLUENCE"]
        assert row["tie_share"] == pytest.approx(0.95)
        assert row["tie_share_is_descriptive_only"] is True
        assert row["max_abs_rank_displacement"] >= 30
        assert row["rows_moved"] >= 2


# --------------------------------------------------------------------------- #
# 2. variance-floor eligibility != LOFO usefulness
# --------------------------------------------------------------------------- #

class TestVarianceFloorIsNotLofoUsefulness:
    def test_a_near_constant_event_family_can_pass_the_floor_and_barely_move_ranks(self):
        tickers = [f"T{i:02d}" for i in range(40)]
        stages = ["live"] * 40
        family_scores = []
        extracted = []
        for i, ticker in enumerate(tickers):
            # F2 is the real ranker. F4 fires on one row — two distinct values,
            # so the variance floor would admit it — but removing it barely
            # moves the board.
            family_scores.append({
                "F2_MOMENTUM_EXTENSION": (i + 1) / 40.0,
                "F4_CATALYST_EVENT": 0.5001 if i == 0 else 0.5,
            })
            extracted.append({"alpha": float(i), "sue_fresh": i == 0})
        admission = fus.Admission(
            admitted=("alpha", "sue_fresh"), dropped=(), frame_dates=1, frame_rows=40)
        plane = _plane(
            family_scores,
            voting=[{"column": "alpha"}, {"column": "sue_fresh"}],
            extracted=extracted,
            admission=admission,
        )
        diag = fus.diagnose_structure(_keys(tickers, stages), plane)
        by_family = {item["family"]: item for item in diag["lofo"]}
        by_member = {item["member"]: item for item in diag["census"]}
        assert by_member["sue_fresh"]["status"] == "voting"
        assert by_member["sue_fresh"]["distinct_values"] == 2
        assert by_family["F4_CATALYST_EVENT"]["distinct_values"] == 2
        assert by_family["F4_CATALYST_EVENT"]["mean_abs_rank_displacement"] < 1.0
        assert by_family["F2_MOMENTUM_EXTENSION"]["mean_abs_rank_displacement"] > 5.0


# --------------------------------------------------------------------------- #
# 3. floor recomputation during ablation reds
# --------------------------------------------------------------------------- #

class TestAblationDoesNotRecomputeFloors:
    def test_admit_aggregate_and_percentile_are_not_called_during_lofo(self, monkeypatch):
        tickers = ["A", "B", "C"]
        stages = ["live"] * 3
        plane = _plane([
            {"F1_TECHNICAL_CONFLUENCE": 0.2, "F2_MOMENTUM_EXTENSION": 0.9},
            {"F1_TECHNICAL_CONFLUENCE": 0.5, "F2_MOMENTUM_EXTENSION": 0.4},
            {"F1_TECHNICAL_CONFLUENCE": 0.8, "F2_MOMENTUM_EXTENSION": 0.1},
        ])

        def boom(*_a, **_k):
            raise AssertionError("floors recomputed during ablation")

        monkeypatch.setattr(fus, "admit_members", boom)
        monkeypatch.setattr(fus, "percentile_rank", boom)
        monkeypatch.setattr(fus, "aggregate", boom)
        monkeypatch.setattr(fus, "fuse_board", boom)
        diag = fus.diagnose_structure(_keys(tickers, stages), plane)
        assert diag["canonical_observation"] is True
        assert diag["admitted_frozen"] == []


# --------------------------------------------------------------------------- #
# 4. ignoring stage buckets reds
# --------------------------------------------------------------------------- #

class TestStageBucketsAreLoadBearing:
    def test_ignoring_stage_buckets_reds(self):
        tickers = ["LOWLIVE", "HIGHBLOCK"]
        stages = [ubr.STAGE_LIVE, ubr.STAGE_BLOCKED]
        plane = _plane([
            {"F2_MOMENTUM_EXTENSION": 0.1},
            {"F2_MOMENTUM_EXTENSION": 0.9},
        ])
        diag = fus.diagnose_structure(_keys(tickers, stages), plane)
        # Reconstruct diagnostic order from the same key the function uses.
        scores = [10.0, 90.0]
        keys = [fus.diagnostic_sort_key(stages[i], scores[i], tickers[i])
                for i in range(2)]
        order = [tickers[i] for i in sorted(range(2), key=lambda i: keys[i])]
        score_only = [tickers[i] for i in sorted(
            range(2), key=lambda i: (-scores[i], tickers[i]))]
        assert order[0] == "LOWLIVE"
        assert score_only[0] == "HIGHBLOCK"
        assert diag["full_model_rank_matches_published"] is True


# --------------------------------------------------------------------------- #
# 5. null-as-zero reds
# --------------------------------------------------------------------------- #

class TestNullIsNotZeroInLofo:
    def test_null_as_zero_reds(self):
        tickers = ["AAA", "ZZZ"]
        stages = ["live", "live"]
        plane = _plane([
            {},
            {"F2_MOMENTUM_EXTENSION": 0.0},
        ], families_present=["F2_MOMENTUM_EXTENSION"])
        diag = fus.diagnose_structure(_keys(tickers, stages), plane)
        canonical = [fus.diagnostic_sort_key(stages[i], plane.scores[i], tickers[i])
                     for i in range(2)]
        canonical_order = [tickers[i] for i in sorted(range(2), key=lambda i: canonical[i])]
        coerced = [(-float(plane.scores[i] or 0.0), tickers[i]) for i in range(2)]
        coerced_order = [tickers[i] for i in sorted(range(2), key=lambda i: coerced[i])]
        assert canonical_order == ["ZZZ", "AAA"]
        assert coerced_order == ["AAA", "ZZZ"]
        assert diag["rows_unscored"] == 1
        assert diag["rows_scored"] == 1


# --------------------------------------------------------------------------- #
# 6. degraded / fallback board emits no canonical W3 observation
# --------------------------------------------------------------------------- #

class TestDegradedBoardEmitsNoCanonicalW3:
    def test_a_degraded_board_has_no_fusion_receipt_and_no_w3_block(self, monkeypatch):
        def _refuse(*_a, **_k):
            raise fus.FusionUnavailable("no family survived (synthetic)")

        monkeypatch.setattr(fus, "fuse_board", _refuse)
        floors: dict = {}
        scored = ubr.score_rows([_row("A"), _row("B", alpha=2.0)],
                                board_asof="2026-08-15", fusion_floors=floors)
        block = ubr.ranking_block(scored, fusion_floors=floors)
        assert block["definition"] == ubr.FALLBACK_DEFINITION
        assert block["fusion"] is None
        assert "w3_structural" not in (block.get("fusion") or {})
        assert floors.get("degraded") is True
        assert "w3_structural" not in floors


# --------------------------------------------------------------------------- #
# 7. injected outcome columns cannot affect diagnostics
# --------------------------------------------------------------------------- #

class TestOutcomesCannotAffectDiagnostics:
    def test_injected_outcome_columns_cannot_affect_diagnostics(self):
        tickers = ["A", "B", "C"]
        stages = ["live"] * 3
        plane = _plane([
            {"F2_MOMENTUM_EXTENSION": 0.1},
            {"F2_MOMENTUM_EXTENSION": 0.5},
            {"F2_MOMENTUM_EXTENSION": 0.9},
        ])
        clean = _keys(tickers, stages)
        dirty = []
        for i, item in enumerate(clean):
            dirty.append({
                **item,
                "excess_spy": 99.0 if i == 0 else -99.0,
                "fwd_ret": 12.0,
                "grade": "win",
                "ic": 0.8,
                "leader": "A",
                "alpha_fwd": 3.14,
            })
        a = fus.diagnose_structure(clean, plane)
        b = fus.diagnose_structure(dirty, plane)
        assert a == b


# --------------------------------------------------------------------------- #
# 8. input-row permutation cannot affect diagnostics
# --------------------------------------------------------------------------- #

class TestPermutationInvariance:
    def test_input_row_permutation_cannot_affect_diagnostics(self):
        pool = _live_pool()
        floors_a: dict = {}
        a = ubr.score_rows(copy.deepcopy(pool), board_asof="2026-08-15",
                           fusion_floors=floors_a)
        floors_b: dict = {}
        b = ubr.score_rows(list(reversed(copy.deepcopy(pool))),
                           board_asof="2026-08-15", fusion_floors=floors_b)
        diag_a = floors_a["w3_structural"]
        diag_b = floors_b["w3_structural"]
        assert diag_a["lofo"] == diag_b["lofo"]
        assert diag_a["census"] == diag_b["census"]
        assert [r["ticker"] for r in a] == [r["ticker"] for r in b]


# --------------------------------------------------------------------------- #
# 9. reconstructed full-model order equals published canonical rank
# --------------------------------------------------------------------------- #

class TestFullModelReconstruction:
    def test_reconstructed_full_model_order_equals_published_canonical_rank(self):
        floors: dict = {}
        scored = ubr.score_rows(_live_pool(), board_asof="2026-08-15",
                                fusion_floors=floors)
        diag = floors["w3_structural"]
        assert diag["schema"] == fus.W3_DIAGNOSTICS_SCHEMA
        assert diag["canonical_observation"] is True
        assert diag["full_model_rank_matches_published"] is True
        published = [r["ticker"] for r in scored]
        plane = fus.fuse_board(_live_pool())
        keys = [{
            "ticker": row["ticker"],
            "stage": next(s["stage"] for s in scored if s["ticker"] == row["ticker"]),
            "score_rank": next(s["score_rank"] for s in scored
                               if s["ticker"] == row["ticker"]),
        } for row in _live_pool()]
        recon = fus.diagnose_structure(keys, plane)
        assert recon["full_model_rank_matches_published"] is True
        order = [ticker for ticker, _key in sorted(
            ((keys[i]["ticker"], fus.diagnostic_sort_key(
                keys[i]["stage"], plane.scores[i], keys[i]["ticker"]))
             for i in range(len(keys))),
            key=lambda pair: pair[1])]
        assert order == published


# --------------------------------------------------------------------------- #
# 10. diagnostics cannot mutate canonical score/rank/display/featured/population
# --------------------------------------------------------------------------- #

class TestDiagnosticsHaveZeroAuthority:
    def test_diagnostics_cannot_mutate_canonical_fields(self, monkeypatch):
        with_diag = ubr.score_rows(copy.deepcopy(_live_pool()),
                                   board_asof="2026-08-15")

        def _noop(*_a, **_k):
            return {"schema": "noop", "canonical_observation": True}

        monkeypatch.setattr(fus, "diagnose_structure", _noop)
        without = ubr.score_rows(copy.deepcopy(_live_pool()),
                                 board_asof="2026-08-15")

        def _canon(rows):
            return [{
                "ticker": r["ticker"],
                "score": r["prophet"]["score"],
                "score_rank": r["score_rank"],
                "display_rank": r["display_rank"],
                "featured": r["featured"],
                "version": r["prophet"]["version"],
            } for r in rows]

        assert _canon(with_diag) == _canon(without)
        assert {r["ticker"] for r in with_diag} == {r["ticker"] for r in without}

    def test_diagnose_structure_does_not_write_back_into_the_plane(self):
        family_scores = [
            {"F2_MOMENTUM_EXTENSION": 0.1},
            {"F2_MOMENTUM_EXTENSION": 0.9},
        ]
        plane = _plane(copy.deepcopy(family_scores))
        snapshot_scores = copy.deepcopy(plane.scores)
        snapshot_families = copy.deepcopy(plane.family_scores)
        fus.diagnose_structure(
            _keys(["A", "B"], ["live", "live"]), plane)
        assert plane.scores == snapshot_scores
        assert plane.family_scores == snapshot_families


class TestCensusCoversEveryRegisteredMember:
    def test_every_registered_member_has_a_nightly_structural_row(self):
        floors: dict = {}
        ubr.score_rows(_live_pool(), board_asof="2026-08-15", fusion_floors=floors)
        census = floors["w3_structural"]["census"]
        members = {row["member"] for row in census}
        assert members == set(fus.REGISTERED_SIGNS)
        statuses = {row["status"] for row in census}
        assert statuses <= set(fus.MEMBER_CENSUS_STATUSES)
        required = {"member", "family", "status", "coverage", "distinct_values",
                    "variation_share", "thresholds", "reason", "source",
                    "staleness_basis"}
        for row in census:
            assert required <= set(row)
            assert row["status"] in fus.MEMBER_CENSUS_STATUSES

    def test_statuses_distinguish_voting_inert_presence_collapse_and_absent(self):
        # voting + vote_inert: flags that are all-False are present and constant.
        inert_pool = [
            _row("A", alpha=1.0, off_high=-1.0, tier="T2", gex="confirm"),
            _row("B", alpha=2.0, off_high=-2.0, tier="T1", gex="neutral"),
            _row("C", alpha=3.0, off_high=-3.0, tier="T3", gex="caution"),
        ]
        floors: dict = {}
        ubr.score_rows(inert_pool, board_asof="2026-08-15", fusion_floors=floors)
        by_member = {row["member"]: row for row in floors["w3_structural"]["census"]}
        assert by_member["alpha"]["status"] == "voting"
        assert by_member["insider_cluster"]["status"] == "vote_inert"
        assert by_member["news_burst"]["status"] == "vote_inert"

        # below_presence: a continuous member that is almost entirely null.
        signs = {
            "thin": fus.RegisteredSign(
                column="thin", family="F2_MOMENTUM_EXTENSION", sign=+1,
                kind="continuous", source="test"),
            "wide": fus.RegisteredSign(
                column="wide", family="F2_MOMENTUM_EXTENSION", sign=+1,
                kind="continuous", source="test"),
        }
        rows = [{"thin": None, "wide": float(i)} for i in range(10)]
        rows[0]["thin"] = 1.0
        admission = fus.admit_members([("n", r) for r in rows], signs=signs)
        assert "thin" not in admission.admitted
        plane = fus.aggregate(rows, admission.admitted, signs=signs)
        plane.members_dropped = [dict(d) for d in admission.dropped]
        plane.admission = admission
        plane.extracted_members = tuple(rows)
        diag = fus.diagnose_structure(
            _keys([f"X{i}" for i in range(10)], ["live"] * 10), plane, signs=signs)
        by_member = {row["member"]: row for row in diag["census"]}
        assert by_member["thin"]["status"] == "below_presence"

        # collapsed_duplicate.
        a = fus.RegisteredSign(column="a", family="F2_MOMENTUM_EXTENSION", sign=+1,
                               kind="continuous", source="test")
        b = fus.RegisteredSign(column="b", family="F2_MOMENTUM_EXTENSION", sign=+1,
                               kind="continuous", source="test")
        dup_rows = [{"a": 1.0, "b": 10.0}, {"a": 2.0, "b": 20.0}]
        dup_plane = fus.aggregate(dup_rows, ["a", "b"], signs={"a": a, "b": b})
        dup_plane.extracted_members = tuple(dup_rows)
        dup_plane.admission = fus.Admission(
            admitted=("a", "b"), dropped=(), frame_dates=1, frame_rows=2)
        dup_diag = fus.diagnose_structure(
            _keys(["P", "Q"], ["live", "live"]), dup_plane, signs={"a": a, "b": b})
        by_member = {row["member"]: row for row in dup_diag["census"]}
        assert by_member["b"]["status"] == "collapsed_duplicate"

        # absent: registered but not extracted.
        missing = fus.RegisteredSign(
            column="ghost", family="F8_ATTENTION_CROWDING", sign=+1,
            kind="flag", source="test")
        ghost_plane = fus.aggregate(
            [{"wide": 1.0}, {"wide": 2.0}], ["wide"], signs={"wide": signs["wide"]})
        ghost_plane.extracted_members = ({"wide": 1.0}, {"wide": 2.0})
        ghost_diag = fus.diagnose_structure(
            _keys(["P", "Q"], ["live", "live"]), ghost_plane,
            signs={"wide": signs["wide"], "ghost": missing})
        by_member = {row["member"]: row for row in ghost_diag["census"]}
        assert by_member["ghost"]["status"] == "absent"


class TestReceiptIsCompactAndOutcomeBlind:
    def test_the_canonical_fusion_receipt_carries_the_compact_structural_block(self):
        floors: dict = {}
        scored = ubr.score_rows(_live_pool(), board_asof="2026-08-15",
                                fusion_floors=floors)
        block = ubr.ranking_block(scored, fusion_floors=floors)
        w3 = block["fusion"]["w3_structural"]
        assert w3["schema"] == fus.W3_DIAGNOSTICS_SCHEMA
        assert w3["canonical_observation"] is True
        assert "lofo" in w3 and "census" in w3
        assert "floors" in block["fusion"]
        assert "w3_structural" not in block["fusion"]["floors"]
        json.dumps(block, allow_nan=False)

    def test_no_new_persistent_engine_write_is_introduced(self):
        source = (ubr.__file__, fus.__file__)
        for path in source:
            text = open(path, encoding="utf-8").read()
            assert "data/us_prophet_rank/w3" not in text
            assert "us_prophet_rank/w3" not in text


# --------------------------------------------------------------------------- #
# Early Leadership source-bound evidence compiler -- no outcomes, no score
# --------------------------------------------------------------------------- #

from engine.prophet_early_leadership_evidence import (
    EarlyLeadershipEvidenceError,
    build_early_leadership_evidence,
)


_DECISION = "2026-09-29T20:10:00Z"
_ASOF = "2026-09-29T20:00:00Z"
_KNOWN = "2026-09-29T20:05:00Z"
_THEME = "theme:memory-storage"
_ISSUER = "ISS:A"
_SECURITY = "SEC:XNAS:A"


def _leadership_inputs():
    candidate = {
        "schema": "prophet.stock_window_observation/v1",
        "issuer_id": _ISSUER,
        "security_id": _SECURITY,
        "ticker": "AAA",
        "theme_id": _THEME,
        "asof": _ASOF,
        "known_at": _KNOWN,
        "return_window_sessions": 10,
        "return_basis": "split_adjusted_close_to_close",
        "stock_return": 0.12,
        "market_return": 0.03,
        "market_id": "SPY",
        "source_ref": "price-owner:aaa:10d",
    }
    peer = {
        "schema": "prophet.peer_ex_candidate/v1",
        "candidate_issuer_id": _ISSUER,
        "candidate_security_id": _SECURITY,
        "theme_id": _THEME,
        "asof": _ASOF,
        "known_at": _KNOWN,
        "membership_vintage": "2026-09-29",
        "return_window_sessions": 10,
        "return_basis": "split_adjusted_close_to_close",
        "candidate_excluded": True,
        "issuer_aliases_excluded": True,
        "peer_member_count": 8,
        "priced_peer_count": 6,
        "coverage": 0.75,
        "equal_weight_return": 0.06,
        "median_return": 0.05,
        "positive_share": 2 / 3,
        "source_ref": "gmi:peer-ex-aa",
    }
    theme = {
        "schema": "theme_state/v1",
        "theme_id": _THEME,
        "asof": _ASOF,
        "known_at": _KNOWN,
        "membership_vintage": "2026-09-29",
        "member_count": 10,
        "priced_member_count": 8,
        "coverage": 0.8,
        "performance": {
            "excess_5d_vs_spy": 0.04,
            "excess_20d_vs_sector": 0.08,
            "vol_normalized_10d": 1.4,
        },
        "dynamics": {
            "velocity": 0.6,
            "acceleration": 0.25,
            "persistence": 0.75,
            "decay_risk": 0.15,
        },
        "breadth": {
            "positive_5d": 0.75,
            "rising_rs": 0.625,
            "early_event_share": 0.25,
            "entry_open_share": 0.125,
        },
        "diffusion": {
            "subthemes_participating": 4,
            "leadership_entropy": 0.78,
            "leader_median_spread": 0.10,
        },
        "authority": "display",
        "rights_state": "internal_allowed",
        "receipts": ["gmi:theme-state:receipt"],
    }
    exposure = {
        "schema": "prophet.economic_exposure_read/v1",
        "issuer_id": _ISSUER,
        "theme_id": _THEME,
        "state": "CONFIRMED_DIRECT",
        "known_at": _KNOWN,
        "source_ref": "gmi:company-theme-exposure",
        "evidence_refs": ["issuer:segment-revenue"],
        "mapping_qualifier": "product_revenue_direct",
    }
    setup = {
        "schema": "prophet.owner_setup_observation/v1",
        "state": "ARMED",
        "observed_at": "2026-09-29T19:55:00Z",
        "known_at": "2026-09-29T19:56:00Z",
        "source_ref": "toi:setup:aaa",
        "invalidation_ref": "toi:setup:aaa:invalidates",
    }
    geometry = {
        "schema": "prophet.owner_entry_geometry_read/v1",
        "current_price": 100.0,
        "invalidation_price": 95.0,
        "chase_boundary": 105.0,
        "target_price": 115.0,
        "quote_asof": "2026-09-29T20:08:00Z",
        "known_at": "2026-09-29T20:09:00Z",
        "source_ref": "entry-owner:aaa",
    }
    lineage = {"identity_epoch": "epoch_0", "episode_id": "fixture:episode:AAA:1",
               "candidate_generation_id": "fixture:candidate-generation:1"}
    for row in (candidate, setup, geometry):
        row.update(lineage)
    for row in (setup, geometry):
        row.update(issuer_id=_ISSUER, security_id=_SECURITY)
    return candidate, peer, theme, exposure, setup, geometry


def _build_leadership(**replace):
    candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
    values = {
        "candidate": candidate,
        "peer_ex_candidate": peer,
        "theme_state": theme,
        "economic_exposure": exposure,
        "setup_observation": setup,
        "entry_geometry": geometry,
    }
    values.update(replace)
    return build_early_leadership_evidence(decision_at=_DECISION, **values)


class TestEarlyLeadershipEvidenceContract:
    def test_decomposes_stock_group_and_market_without_a_score(self):
        out = _build_leadership()
        d = out["return_decomposition"]
        assert d["stock_excess_market"] == pytest.approx(0.09)
        assert d["peer_excess_market"] == pytest.approx(0.03)
        assert d["stock_excess_peer"] == pytest.approx(0.06)
        assert d["identity_error"] == pytest.approx(0.0)
        assert out["interpretation"]["score"] is None
        assert out["interpretation"]["probability"] is None
        assert out["interpretation"]["rank"] is None
        assert out["interpretation"]["recommendation"] is None
        assert out["interpretation"]["availability"] == "DEFER_TO_B4"
        assert all(value is False for value in out["authority"].values())

    def test_peer_receipt_must_exclude_candidate_and_all_issuer_aliases(self):
        for key in ("candidate_excluded", "issuer_aliases_excluded"):
            candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
            peer[key] = False
            with pytest.raises(EarlyLeadershipEvidenceError, match="excluded"):
                _build_leadership(peer_ex_candidate=peer)

    def test_peer_and_candidate_identity_must_match(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        peer["candidate_issuer_id"] = "ISS:OTHER"
        with pytest.raises(EarlyLeadershipEvidenceError, match="issuer_mismatch"):
            _build_leadership(peer_ex_candidate=peer)

        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        peer["candidate_security_id"] = "SEC:XNAS:OTHER"
        with pytest.raises(EarlyLeadershipEvidenceError, match="security_mismatch"):
            _build_leadership(peer_ex_candidate=peer)

    def test_theme_identity_asof_membership_and_return_basis_are_jointly_bound(self):
        mutators = [
            ("theme", lambda c,p,t,e,s,g: t.update(theme_id="theme:other"), "theme_identity_mismatch"),
            ("asof", lambda c,p,t,e,s,g: p.update(asof="2026-09-28T20:00:00Z"), "measurement_asof_mismatch"),
            ("vintage", lambda c,p,t,e,s,g: p.update(membership_vintage="2026-09-28"), "membership_vintage_mismatch"),
            ("window", lambda c,p,t,e,s,g: p.update(return_window_sessions=5), "return_window_mismatch"),
            ("basis", lambda c,p,t,e,s,g: p.update(return_basis="raw_close"), "return_basis_mismatch"),
        ]
        for name, mutate, error in mutators:
            candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
            mutate(candidate, peer, theme, exposure, setup, geometry)
            with pytest.raises(EarlyLeadershipEvidenceError, match=error):
                _build_leadership(
                    candidate=candidate, peer_ex_candidate=peer, theme_state=theme,
                    economic_exposure=exposure, setup_observation=setup, entry_geometry=geometry,
                )

    def test_singleton_or_empty_peer_support_is_unknown_not_zero(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        peer.update(
            peer_member_count=1, priced_peer_count=1, coverage=1.0,
            equal_weight_return=None, median_return=None, positive_share=None,
        )
        out = _build_leadership(peer_ex_candidate=peer)
        assert out["peer_ex_candidate"]["measurement_state"] == "UNAVAILABLE_SINGLETON_OR_EMPTY"
        assert out["return_decomposition"]["peer_excess_market"] is None
        assert out["return_decomposition"]["stock_excess_peer"] is None
        assert out["research_features"]["peer_positive_share"] is None
        assert out["research_state"] == "UNAVAILABLE"

    def test_partial_peer_coverage_remains_partial_and_keeps_denominator(self):
        out = _build_leadership()
        peer = out["peer_ex_candidate"]
        assert peer["measurement_state"] == "PARTIAL"
        assert peer["peer_member_count"] == 8
        assert peer["priced_peer_count"] == 6
        assert peer["coverage"] == pytest.approx(.75)

    def test_peer_coverage_must_match_counts(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        peer["coverage"] = .9
        with pytest.raises(EarlyLeadershipEvidenceError, match="coverage_count_mismatch"):
            _build_leadership(peer_ex_candidate=peer)

    def test_theme_state_is_projected_not_recomputed_or_promoted(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        original = copy.deepcopy(theme)
        out = _build_leadership(theme_state=theme)
        projected = out["theme_state_projection"]
        assert projected["dynamics"]["acceleration"] == .25
        assert projected["breadth"]["rising_rs"] == .625
        assert projected["diffusion"]["leadership_entropy"] == .78
        assert projected["authority"] == "display"
        assert theme == original

    def test_theme_state_must_remain_display_authority(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        theme["authority"] = "rank"
        with pytest.raises(EarlyLeadershipEvidenceError, match="authority_must_be_display"):
            _build_leadership(theme_state=theme)

    def test_membership_only_is_not_economic_exposure(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        exposure.update(state="MEMBERSHIP_ONLY", evidence_refs=[])
        out = _build_leadership(economic_exposure=exposure)
        assert out["economic_exposure"]["economic_exposure_confirmed"] is False
        assert out["research_state"] == "ACCRUING"

    @pytest.mark.parametrize("state", ["CONFIRMED_DIRECT", "CONFIRMED_INDIRECT"])
    def test_direct_or_indirect_confirmed_exposure_can_support_research(self, state):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        exposure["state"] = state
        out = _build_leadership(economic_exposure=exposure)
        assert out["economic_exposure"]["economic_exposure_confirmed"] is True
        assert out["research_state"] == "READY_FOR_RESEARCH_COMPARISON"

    def test_setup_state_is_preserved_not_scalarized(self):
        for state in ("FORMING", "ARMED", "TRIGGERED", "CONFIRMED", "FAILED", "EXTENDED"):
            candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
            setup["state"] = state
            out = _build_leadership(setup_observation=setup)
            assert out["setup_observation"]["state"] == state
            assert out["research_features"]["setup_state"] == state

    def test_unknown_setup_is_accruing_not_bearish(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        setup["state"] = "UNKNOWN"
        out = _build_leadership(setup_observation=setup)
        assert out["research_state"] == "ACCRUING"
        assert out["setup_observation"]["state"] == "UNKNOWN"

    def test_geometry_exposes_remaining_room_without_minting_availability(self):
        out = _build_leadership()
        geometry = out["entry_geometry"]
        assert geometry["risk_to_invalidation_pct"] == pytest.approx(.05)
        assert geometry["room_to_chase_pct"] == pytest.approx(.05)
        assert geometry["target_room_pct"] == pytest.approx(.15)
        assert geometry["gross_reward_risk"] == pytest.approx(3.0)
        assert geometry["past_chase_boundary"] is False
        assert geometry["availability_interpretation"] == "GEOMETRY_CONTEXT_ONLY_B4_REMAINS_OWNER"

    def test_extended_price_can_show_negative_room_without_becoming_a_sell(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        geometry.update(current_price=108.0, target_price=120.0)
        out = _build_leadership(entry_geometry=geometry)
        assert out["entry_geometry"]["room_to_chase_pct"] < 0
        assert out["entry_geometry"]["past_chase_boundary"] is True
        assert out["interpretation"]["recommendation"] is None
        assert out["authority"]["can_change_entry_open"] is False

    def test_invalid_long_geometry_is_refused(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        geometry["target_price"] = 99.0
        with pytest.raises(EarlyLeadershipEvidenceError, match="target_must_be_above"):
            _build_leadership(entry_geometry=geometry)

    def test_future_candidate_peer_theme_setup_or_geometry_evidence_is_refused(self):
        cases = [
            ("candidate", "known_at", "2026-09-29T20:11:00Z"),
            ("peer", "known_at", "2026-09-29T20:11:00Z"),
            ("theme", "known_at", "2026-09-29T20:11:00Z"),
            ("setup", "known_at", "2026-09-29T20:11:00Z"),
            ("geometry", "known_at", "2026-09-29T20:11:00Z"),
        ]
        for which, key, value in cases:
            candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
            mapping = {
                "candidate": candidate, "peer": peer, "theme": theme,
                "setup": setup, "geometry": geometry,
            }[which]
            mapping[key] = value
            with pytest.raises(EarlyLeadershipEvidenceError, match="clock_invalid|future_evidence"):
                _build_leadership(
                    candidate=candidate, peer_ex_candidate=peer, theme_state=theme,
                    economic_exposure=exposure, setup_observation=setup, entry_geometry=geometry,
                )

    def test_future_exposure_is_refused(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        exposure["known_at"] = "2026-09-29T20:11:00Z"
        with pytest.raises(EarlyLeadershipEvidenceError, match="future_evidence"):
            _build_leadership(economic_exposure=exposure)

    def test_feedback_outputs_cannot_enter_candidate_measurement(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        candidate["score_rank"] = 1
        with pytest.raises(EarlyLeadershipEvidenceError, match="prohibited_feedback_input"):
            _build_leadership(candidate=candidate)

    def test_theme_rights_block_is_unavailable_not_negative_support(self):
        candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
        theme["rights_state"] = "RIGHTS_BLOCKED"
        out = _build_leadership(theme_state=theme)
        assert out["research_state"] == "UNAVAILABLE"
        assert out["research_features"]["theme_acceleration"] == .25

    def test_output_is_content_addressed_and_deep_copy_safe(self):
        left = _build_leadership()
        right = _build_leadership()
        assert left == right
        assert left["evidence_id"].startswith("pele:")
        left["research_features"]["theme_acceleration"] = 999
        assert _build_leadership() == right


# Independent review #8240/5935977271: owner identity is data, not source-ref prose.
def _bound_leadership_values():
    candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
    lineage = {"identity_epoch": "epoch_0", "episode_id": "fixture:episode:AAA:1",
               "candidate_generation_id": "fixture:candidate-generation:1"}
    for row in (candidate, setup, geometry):
        row.update(lineage)
    for row in (setup, geometry):
        row.update(issuer_id=candidate["issuer_id"], security_id=candidate["security_id"])
    return {"candidate": candidate, "peer_ex_candidate": peer, "theme_state": theme,
            "economic_exposure": exposure, "setup_observation": setup, "entry_geometry": geometry}


def _bound_leadership(values):
    return build_early_leadership_evidence(decision_at=_DECISION, **values)


def test_bound_leadership_keeps_owner_identity_lineage_and_numeric_features():
    values = _bound_leadership_values()
    original = copy.deepcopy(values)
    result = _bound_leadership(values)
    assert result["research_state"] == "READY_FOR_RESEARCH_COMPARISON"
    assert result["setup_lineage"]["state"] == "BOUND"
    for owner in ("candidate_measurement", "setup_observation", "entry_geometry"):
        assert result[owner]["issuer_id"] == values["candidate"]["issuer_id"]
        assert result[owner]["security_id"] == values["candidate"]["security_id"]
        assert result[owner]["episode_id"] == "fixture:episode:AAA:1"
    assert result["research_features"]["risk_to_invalidation_pct"] == 0.05
    assert result["research_features"]["gross_reward_risk"] == 3.0
    assert values == original
    assert all(flag is False for flag in result["authority"].values())


@pytest.mark.parametrize("owner,prefix", [("setup_observation", "setup"), ("entry_geometry", "geometry")])
@pytest.mark.parametrize("field,identity", [("issuer_id", "issuer"), ("security_id", "security")])
def test_bound_leadership_refuses_independent_wrong_security_or_issuer(owner, prefix, field, identity):
    values = _bound_leadership_values()
    values[owner][field] = "fixture:OTHER"
    with pytest.raises(EarlyLeadershipEvidenceError, match=f"{prefix}_{identity}_mismatch"):
        _bound_leadership(values)


@pytest.mark.parametrize("owner,prefix", [("setup_observation", "setup"), ("entry_geometry", "geometry")])
@pytest.mark.parametrize("field,identity", [("issuer_id", "issuer"), ("security_id", "security")])
def test_bound_leadership_requires_explicit_owner_identity(owner, prefix, field, identity):
    values = _bound_leadership_values()
    values[owner].pop(field)
    with pytest.raises(EarlyLeadershipEvidenceError, match=f"{prefix}_{identity}_invalid"):
        _bound_leadership(values)


@pytest.mark.parametrize("owner", ["candidate", "setup_observation", "entry_geometry"])
@pytest.mark.parametrize("field", ["identity_epoch", "episode_id", "candidate_generation_id"])
def test_bound_leadership_refuses_same_security_wrong_lineage(owner, field):
    values = _bound_leadership_values()
    values[owner][field] = "fixture:other-lineage"
    with pytest.raises(EarlyLeadershipEvidenceError, match="setup_lineage_mismatch"):
        _bound_leadership(values)


@pytest.mark.parametrize("owner", ["candidate", "setup_observation", "entry_geometry"])
def test_bound_leadership_refuses_partial_lineage(owner):
    values = _bound_leadership_values()
    values[owner].pop("candidate_generation_id")
    with pytest.raises(EarlyLeadershipEvidenceError, match="setup_lineage_incomplete"):
        _bound_leadership(values)


def test_unbound_leadership_accrues_without_minting_setup_readiness():
    values = _bound_leadership_values()
    for owner in ("candidate", "setup_observation", "entry_geometry"):
        for field in ("identity_epoch", "episode_id", "candidate_generation_id"):
            values[owner].pop(field)
    result = _bound_leadership(values)
    assert result["research_state"] == "ACCRUING"
    assert result["setup_lineage"] == {
        "state": "UNAVAILABLE", "identity_epoch": None, "episode_id": None,
        "candidate_generation_id": None,
    }
    assert result["research_features"]["risk_to_invalidation_pct"] == 0.05
    assert all(flag is False for flag in result["authority"].values())


def test_owner_identity_is_not_inferred_from_opaque_ref_text():
    values = _bound_leadership_values()
    values["setup_observation"]["source_ref"] = "opaque:BBB-looking-text"
    values["entry_geometry"]["source_ref"] = "opaque:different-display-ticker"
    assert _bound_leadership(values)["research_state"] == "READY_FOR_RESEARCH_COMPARISON"


def test_matched_other_security_control_is_accepted_but_swaps_are_refused():
    values = _bound_leadership_values()
    other = copy.deepcopy(values)
    other["candidate"]["ticker"] = "BBB"
    for owner in ("candidate", "setup_observation", "entry_geometry"):
        other[owner].update(issuer_id="fixture:ISS:BBB", security_id="fixture:SEC:BBB",
                            episode_id="fixture:episode:BBB:1")
    other["peer_ex_candidate"].update(candidate_issuer_id="fixture:ISS:BBB", candidate_security_id="fixture:SEC:BBB")
    other["economic_exposure"]["issuer_id"] = "fixture:ISS:BBB"
    other["setup_observation"].update(state="CONFIRMED", source_ref="toi:setup:bbb")
    other["entry_geometry"].update(invalidation_price=85.0, target_price=130.0, source_ref="entry-owner:bbb")
    assert _bound_leadership(other)["research_state"] == "READY_FOR_RESEARCH_COMPARISON"
    for owners in (("setup_observation",), ("entry_geometry",), ("setup_observation", "entry_geometry")):
        swapped = copy.deepcopy(values)
        for owner in owners:
            swapped[owner] = other[owner]
        with pytest.raises(EarlyLeadershipEvidenceError, match="issuer_mismatch"):
            _bound_leadership(swapped)


# Program-CEO clock-integrity blocker 5966124623: preserve exact UTC instants.
def _clock_inputs(asof="2026-09-29T20:00:00.100Z"):
    candidate, peer, theme, exposure, setup, geometry = _leadership_inputs()
    for row in (candidate, peer, theme):
        row["asof"] = asof
    for row in (candidate, peer, theme):
        row["known_at"] = "2026-09-29T20:05:00.100Z"
    setup["observed_at"] = "2026-09-29T19:55:00.100Z"
    setup["known_at"] = "2026-09-29T19:56:00.100Z"
    exposure["known_at"] = "2026-09-29T19:57:00.100Z"
    geometry["quote_asof"] = "2026-09-29T20:08:00.100Z"
    geometry["known_at"] = "2026-09-29T20:09:00.100Z"
    return candidate, peer, theme, exposure, setup, geometry


@pytest.mark.parametrize("owner", ["candidate", "peer", "theme"])
def test_subsecond_measurement_mismatch_is_refused_and_cannot_alias_evidence_id(owner):
    candidate, peer, theme, exposure, setup, geometry = _clock_inputs()
    matched = build_early_leadership_evidence(
        decision_at="2026-09-29T20:10:00.100Z",
        candidate=candidate, peer_ex_candidate=peer, theme_state=theme,
        economic_exposure=exposure, setup_observation=setup, entry_geometry=geometry,
    )
    changed = {"candidate": candidate, "peer": peer, "theme": theme}[owner]
    changed["asof"] = "2026-09-29T20:00:00.900Z"
    with pytest.raises(EarlyLeadershipEvidenceError, match="measurement_asof_mismatch"):
        build_early_leadership_evidence(
            decision_at="2026-09-29T20:10:00.100Z",
            candidate=candidate, peer_ex_candidate=peer, theme_state=theme,
            economic_exposure=exposure, setup_observation=setup, entry_geometry=geometry,
        )
    assert matched["candidate_measurement"]["asof"] == "2026-09-29T20:00:00.100000Z"


def test_semantically_equal_subsecond_spellings_canonicalize_to_one_instant():
    candidate, peer, theme, exposure, setup, geometry = _clock_inputs()
    candidate["asof"] = "2026-09-29T20:00:00.100Z"
    peer["asof"] = "2026-09-29T20:00:00.100000Z"
    theme["asof"] = "2026-09-29T20:00:00.100000Z"
    out = build_early_leadership_evidence(
        decision_at="2026-09-29T20:10:00.100000Z",
        candidate=candidate, peer_ex_candidate=peer, theme_state=theme,
        economic_exposure=exposure, setup_observation=setup, entry_geometry=geometry,
    )
    assert out["candidate_measurement"]["asof"] == "2026-09-29T20:00:00.100000Z"
    assert out["peer_ex_candidate"]["asof"] == out["candidate_measurement"]["asof"]
    assert out["theme_state_projection"]["asof"] == out["candidate_measurement"]["asof"]


@pytest.mark.parametrize("delta", ["2026-09-29T20:10:00.000001Z", "2026-09-29T20:10:00.900Z"])
@pytest.mark.parametrize("owner", ["candidate", "peer", "theme", "exposure", "setup", "geometry"])
def test_subsecond_future_known_at_is_refused_for_every_owner(delta, owner):
    candidate, peer, theme, exposure, setup, geometry = _clock_inputs("2026-09-29T20:00:00Z")
    mapping = {
        "candidate": candidate, "peer": peer, "theme": theme, "exposure": exposure,
        "setup": setup, "geometry": geometry,
    }[owner]
    mapping["known_at"] = delta
    with pytest.raises(EarlyLeadershipEvidenceError, match="clock_invalid|future_evidence"):
        build_early_leadership_evidence(
            decision_at="2026-09-29T20:10:00Z",
            candidate=candidate, peer_ex_candidate=peer, theme_state=theme,
            economic_exposure=exposure, setup_observation=setup, entry_geometry=geometry,
        )


def test_exact_subsecond_known_at_boundary_is_accepted_and_content_addressed():
    candidate, peer, theme, exposure, setup, geometry = _clock_inputs("2026-09-29T20:00:00Z")
    decision = "2026-09-29T20:10:00.900Z"
    for row in (candidate, peer, theme, exposure, setup, geometry):
        row["known_at"] = decision
    out = build_early_leadership_evidence(
        decision_at=decision, candidate=candidate, peer_ex_candidate=peer,
        theme_state=theme, economic_exposure=exposure, setup_observation=setup,
        entry_geometry=geometry,
    )
    assert out["decision_at"] == "2026-09-29T20:10:00.900000Z"
    assert out["candidate_measurement"]["known_at"] == out["decision_at"]
    assert out["peer_ex_candidate"]["known_at"] == out["decision_at"]
    assert out["theme_state_projection"]["known_at"] == out["decision_at"]
    assert out["economic_exposure"]["known_at"] == out["decision_at"]
    assert out["setup_observation"]["known_at"] == out["decision_at"]
    assert out["entry_geometry"]["known_at"] == out["decision_at"]


def test_material_owner_clock_change_changes_evidence_identity():
    candidate, peer, theme, exposure, setup, geometry = _clock_inputs()
    first = build_early_leadership_evidence(
        decision_at="2026-09-29T20:10:00.100Z",
        candidate=candidate, peer_ex_candidate=peer, theme_state=theme,
        economic_exposure=exposure, setup_observation=setup, entry_geometry=geometry,
    )
    candidate2, peer2, theme2, exposure2, setup2, geometry2 = _clock_inputs()
    peer2["known_at"] = "2026-09-29T20:05:00.900Z"
    second = build_early_leadership_evidence(
        decision_at="2026-09-29T20:10:00.100Z",
        candidate=candidate2, peer_ex_candidate=peer2, theme_state=theme2,
        economic_exposure=exposure2, setup_observation=setup2, entry_geometry=geometry2,
    )
    assert first["evidence_id"] != second["evidence_id"]
