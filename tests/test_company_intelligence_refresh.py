from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
import pandas as pd

from scripts import refresh_company_intelligence as refresh


class _Response(io.BytesIO):
    def close(self) -> None:  # closing() requires close; BytesIO already does it.
        super().close()


def _opener(payload: dict):
    raw = json.dumps(payload).encode("utf-8")

    def open_index(_request, *, timeout: float):
        assert timeout > 0
        return _Response(raw)

    return open_index


def test_fetch_transcript_index_requires_terminal_v1_commit_marker(tmp_path: Path) -> None:
    payload = {
        "schema": "mastermind.tx-index/v1",
        "symbols": {"NVDA": ["2026Q1"]},
        "revisions": {},
        "dates": {"NVDA/2026Q1": "2026-05-20"},
        "body_count": 1,
        "symbol_count": 1,
        "generated_at": "2026-05-20T00:00:00Z",
    }
    target = tmp_path / "tx-index.json"
    written = refresh.fetch_transcript_index("https://example.test/index.json", target, opener=_opener(payload))
    assert written == payload
    assert json.loads(target.read_text(encoding="utf-8")) == payload


def test_fetch_transcript_index_refuses_invalid_marker_without_writing(tmp_path: Path) -> None:
    target = tmp_path / "tx-index.json"
    with pytest.raises(refresh.RefreshError, match="invalid"):
        refresh.fetch_transcript_index(
            "https://example.test/index.json",
            target,
            opener=_opener({"schema": "wrong", "symbols": {}}),
        )
    assert not target.exists()



def _write_score_rows(root: Path, rows: list[dict]) -> None:
    target = root / "earnings_calls" / "scores.parquet"
    target.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(target, index=False)


def _score_row(
    *,
    call_date: str,
    source_record_id: str = "defeatbeta:NVDA:2026Q1",
    degraded_reason: str = "",
    source: str = "transcript",
) -> dict:
    return {
        "call_date": call_date,
        "source": source,
        "source_record_id": source_record_id,
        "sentiment": 0.2,
        "performance": 7.0,
        "confidence": 0.9,
        "degraded_reason": degraded_reason,
        "is_context_only": True,
    }


def _terminal_index(dates: dict[str, str], *, generated_at: str = "2026-09-19T09:21:30Z") -> dict:
    symbols: dict[str, list[str]] = {}
    for pair in dates:
        ticker, tx_id = pair.split("/", 1)
        symbols.setdefault(ticker, []).append(tx_id)
    return {
        "schema": "mastermind.tx-index/v1",
        "symbols": symbols,
        "revisions": {},
        "dates": dates,
        "body_count": len(dates),
        "symbol_count": len(symbols),
        "generated_at": generated_at,
    }


def test_score_freshness_accepts_bounded_weekend_lag(tmp_path: Path) -> None:
    _write_score_rows(tmp_path, [_score_row(call_date="2026-09-17")])
    report = refresh.assert_earnings_score_freshness(
        tmp_path,
        _terminal_index({"NVDA/2026Q1": "2026-09-19"}),
        as_of="2026-09-20",
    )
    assert report["state"] == "fresh"
    assert report["lag_days"] == 2


def test_score_freshness_rejects_dead_worker_even_if_degraded_row_is_recent(
    tmp_path: Path,
) -> None:
    _write_score_rows(
        tmp_path,
        [
            _score_row(call_date="2026-08-28"),
            _score_row(
                call_date="2026-09-17",
                source_record_id="defeatbeta:AMD:2026Q3",
                degraded_reason="provider_unavailable",
            ),
        ],
    )
    with pytest.raises(refresh.RefreshError, match="lags newest causal Terminal call"):
        refresh.assert_earnings_score_freshness(
            tmp_path,
            _terminal_index(
                {
                    "NVDA/2026Q1": "2026-08-28",
                    "AMD/2026Q3": "2026-09-17",
                }
            ),
            as_of="2026-09-19",
        )


def test_score_freshness_ignores_future_labelled_terminal_rows(tmp_path: Path) -> None:
    _write_score_rows(tmp_path, [_score_row(call_date="2026-09-16")])
    report = refresh.assert_earnings_score_freshness(
        tmp_path,
        _terminal_index(
            {
                "NVDA/2026Q1": "2026-09-17",
                "HCM/2026Q2": "2026-09-25",
            }
        ),
        as_of="2026-09-19",
    )
    assert report["terminal_latest_call_date"] == "2026-09-17"
    assert report["lag_days"] == 1


def test_score_freshness_uses_terminal_linked_transcripts_not_newer_8k_rows(
    tmp_path: Path,
) -> None:
    _write_score_rows(
        tmp_path,
        [
            _score_row(call_date="2026-08-28"),
            _score_row(
                call_date="2026-09-17",
                source_record_id="sec:AMD:2026Q3",
                source="8k",
            ),
        ],
    )
    with pytest.raises(refresh.RefreshError, match="lags newest causal Terminal call"):
        refresh.assert_earnings_score_freshness(
            tmp_path,
            _terminal_index(
                {
                    "NVDA/2026Q1": "2026-08-28",
                    "AMD/2026Q3": "2026-09-17",
                }
            ),
            as_of="2026-09-19",
        )


def test_refresh_fails_closed_when_fail_soft_earnings_fetch_materializes_nothing(tmp_path: Path) -> None:
    # fetch_earnings_scores intentionally returns zero for an absent source so
    # the render can preserve its prior state. The publisher must not mistake
    # that zero for safe input and replace its public root marker.
    with pytest.raises(refresh.RefreshError, match="earnings manifest unavailable"):
        refresh.refresh(tmp_path, fetch_scores=lambda **_kwargs: 0)


def test_refresh_can_preserve_a_validated_output_tree_for_a_post_ci_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The sidecar must read CIE before TemporaryDirectory cleanup occurs."""
    output = tmp_path / "persistent-output"
    seen: dict[str, Path] = {}
    monkeypatch.setattr(refresh, "ensure_earnings_inputs", lambda _source: {})
    monkeypatch.setattr(
        refresh,
        "fetch_transcript_index",
        lambda _url, destination: (
            destination.write_text("{}", encoding="utf-8") and {}
        ),
    )
    monkeypatch.setattr(
        refresh,
        "assert_earnings_score_freshness",
        lambda *_args, **_kwargs: {"state": "fresh"},
    )

    def build(argv: list[str]) -> int:
        target = Path(argv[argv.index("--out-dir") + 1])
        target.mkdir(parents=True)
        (target / "manifest.json").write_text("{}")
        seen["build"] = target
        return 0

    monkeypatch.setattr(refresh, "build_company_intelligence", build)
    monkeypatch.setattr(refresh, "validate_generation", lambda path: {"status": "ready", "generation_id": "a" * 24, "company_count": 1, "event_count": 1, "warnings": []})

    def publish(path: Path, **_kwargs) -> int:
        seen["publish"] = path
        assert (path / "manifest.json").is_file()
        return 0

    assert refresh.refresh(
        tmp_path / "work",
        out_dir=output,
        fetch_scores=lambda **_kwargs: 0,
        publish_generation=publish,
    ) == 0
    assert seen == {"build": output, "publish": output}



def test_stale_score_plane_holds_v1_but_leaves_validated_tree_for_sibling(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "persistent-output"
    monkeypatch.setattr(refresh, "ensure_earnings_inputs", lambda _source: {})
    monkeypatch.setattr(
        refresh,
        "fetch_transcript_index",
        lambda _url, destination: (
            destination.write_text("{}", encoding="utf-8") and {}
        ),
    )

    def stale(*_args, **_kwargs):
        raise refresh.ScoreFreshnessError("score plane stale by fixture")

    monkeypatch.setattr(refresh, "assert_earnings_score_freshness", stale)

    def build(argv: list[str]) -> int:
        target = Path(argv[argv.index("--out-dir") + 1])
        target.mkdir(parents=True)
        (target / "manifest.json").write_text("{}", encoding="utf-8")
        return 0

    monkeypatch.setattr(refresh, "build_company_intelligence", build)
    monkeypatch.setattr(
        refresh,
        "validate_generation",
        lambda _path: {
            "status": "ready",
            "generation_id": "b" * 24,
            "company_count": 1,
            "event_count": 1,
            "warnings": [],
        },
    )

    def must_not_publish(*_args, **_kwargs):
        raise AssertionError("stale v1 root was published")

    rc = refresh.refresh(
        tmp_path / "work",
        out_dir=output,
        fetch_scores=lambda **_kwargs: 0,
        publish_generation=must_not_publish,
    )
    assert rc == refresh.SCORE_FRESHNESS_STALE
    assert (output / "manifest.json").is_file()


def test_workflow_is_scheduled_off_render_and_handles_only_safe_cas_conflict() -> None:
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/company-intelligence.yml").read_text(encoding="utf-8")
    assert 'cron: "17 */3 * * *"' in workflow
    assert "runs-on: ubuntu-latest" in workflow
    assert "python -m scripts.refresh_company_intelligence" in workflow
    assert 'if [ "$rc" -eq 2 ]' in workflow
    assert "R2_SECRET_ACCESS_KEY" in workflow
    assert "--out-dir \"$OUTPUT_DIR\"" in workflow
    assert "python -m scripts.build_company_theme_exposure" in workflow
    assert "python -m scripts.publish_company_theme_exposure_r2" in workflow
    assert 'if [ "$side_rc" -eq 2 ]' in workflow
    assert "timeout-minutes: 25" in workflow
    # A stale qualitative score plane holds only the v1 root. The independent
    # Event Workspace sibling still runs; dependent sidecars stay behind v1.
    stale_edges = [
        i for i in range(len(workflow))
        if workflow.startswith('elif [ "$rc" -eq 3 ]', i)
    ]
    workspace_call = workflow.index("python -m scripts.refresh_event_workspaces")
    assert len(stale_edges) == 2
    assert stale_edges[0] < workspace_call < stale_edges[1]
    assert "qualitative earnings score plane stale; v1 root held" in workflow


def test_scheduled_workflow_contains_its_sparse_import_closure() -> None:
    workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/company-intelligence.yml").read_text(encoding="utf-8")
    assert "lib/config.py" in workflow
    install_line = next(line for line in workflow.splitlines() if "pip install --quiet" in line)
    assert "pyyaml" in install_line
    assert "requests" in install_line
    for path in (
        "engine/company_theme_exposure",
        "scripts/build_company_theme_exposure.py",
        "scripts/publish_company_theme_exposure_r2.py",
        "data/baskets/membership.json",
        "config/theme_crosswalk.yml",
        "data/neuralweb/theme_state.json",
        "scripts/refresh_event_workspaces.py",
        "engine/earnings_release",
        "engine/earnings_narrative",
        "engine/fundamental_forensics",
        "config/fundamental_forensics_disclosure_diff.v1.json",
    ):
        assert path in workflow
    assert "python -m scripts.refresh_event_workspaces" in workflow
    assert 'if [ "$ws_rc" -eq 2 ]' in workflow
