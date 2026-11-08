#!/usr/bin/env python3
"""Exercise the incumbent Macro checkout path and real news consumers, offline.

Usage:
  python verify_news_freshness_transport.py --macro-source /path/to/macro \
    --mastermind-source /path/to/Mastermind [--receipt /path/to/receipt.json]

Requires the ordinary imports used by brain.bot_mcp (including claude-agent-sdk).
All git operations target temporary fixture repositories. The unrelated R2 leg
is stubbed; no production checkout, provider, scheduler, or model is invoked.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--macro-source", type=Path, required=True)
    parser.add_argument("--mastermind-source", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    macro_source = args.macro_source.resolve()
    mastermind_source = args.mastermind_source.resolve()
    sys.path[:0] = [str(macro_source), str(mastermind_source)]
    from engine import intelligence
    from brain import bot_mcp
    from portfolio import lenses
    from data_layer import macro_refresh

    origin = {
        "source_asof": "2026-10-29T21:00:00+00:00",
        "source_asof_basis": "financial_news.fetched_at",
        "retained_from_previous_build": True,
        "retained_reason": "candidate_darker_than_existing",
    }
    news = {
        "n_recent": 3,
        "sentiment_lean": "pos",
        "top": [{"title": "Fixture news report", "url": "https://example.test/NVDA"}],
    }
    rel = "site/intelligence/by_ticker.json"

    def write_json(root: Path, path: str, value: dict) -> bytes:
        data = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode()
        destination = root / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return data

    def git(root: Path, *argv: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *argv],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    def commit(root: Path, message: str) -> str:
        git(root, "add", "site", "data")
        git(root, "-c", "user.name=News provenance fixture",
            "-c", "user.email=news-fixture@example.test", "commit", "-m", message)
        return git(root, "rev-parse", "HEAD")

    with tempfile.TemporaryDirectory(prefix="news-refresh-proof-") as temporary:
        root = Path(temporary)
        remote = root / "source"
        remote.mkdir()
        git(remote, "init", "--initial-branch=main")
        write_json(remote, "site/news/by_ticker.json", {
            "asof": "2026-10-31", **origin, "tickers": {"NVDA": news},
        })
        for path, value in {
            "site/factordata/us_standouts.json": {"as_of": "2026-11-08"},
            "data/regime/latest.json": {"date": "2026-11-08"},
            "site/sectordata/sector_cycles.json": {"meta": {"asOf": "2026-11-08"}},
            "site/stockdata/SPY.json": {"asof": "2026-11-08"},
        }.items():
            write_json(remote, path, value)
        initial_bytes = write_json(remote, rel, {
            "as_of": "2026-11-07",
            "tickers": {"NVDA": {"has_news": True, "news": dict(news, n_recent=1)}},
        })
        initial_commit = commit(remote, "fixture: initial legacy intelligence artifact")

        destination = root / "vendor" / "macro_src"
        macro_refresh._REMOTE = remote.as_uri()
        macro_refresh._SRC = destination
        macro_refresh._GIT_SSH_COMMAND = ""
        r2_calls = []
        macro_refresh._sync_r2 = lambda log=print: r2_calls.append("unrelated R2 leg stubbed")
        messages = []
        first_asof = macro_refresh.refresh(log=messages.append)
        assert first_asof == "2026-11-08", first_asof
        assert git(destination, "rev-parse", "HEAD") == initial_commit
        assert (destination / rel).read_bytes() == initial_bytes

        intelligence.config.ROOT = remote
        produced = intelligence.load_and_build(today=date(2026, 11, 8))
        assert produced["news_freshness"] == origin
        final_bytes = write_json(remote, rel, produced)
        final_commit = commit(remote, "fixture: publish news component provenance")
        assert final_commit != initial_commit
        second_asof = macro_refresh.refresh(log=messages.append)
        assert second_asof == "2026-11-08", second_asof
        assert git(destination, "rev-parse", "HEAD") == final_commit
        assert (destination / rel).read_bytes() == final_bytes
        assert len(r2_calls) == 2

        bot_mcp._V = destination
        lenses._V = destination
        answer = asyncio.run(bot_mcp.get_intelligence.handler({"ticker": "NVDA"}))
        serialized = "\n".join(
            entry["text"] for entry in answer["content"] if entry.get("type") == "text"
        )
        readback = json.loads(serialized)
        row = lenses._news_row("NVDA")
        assert readback["news_freshness"] == origin
        assert readback["news"] == news
        assert readback["freshness"]["asof"] == "2026-11-08"
        assert readback["freshness"]["source_asof"] is None
        assert readback["freshness"]["source_file"] == rel
        assert readback["evidence_grade"] == "vendored_snapshot"
        assert row["status"] == "stale_retained"
        assert row["value"]["source_asof"] == origin["source_asof"]
        assert row["value"]["retained_from_previous_build"] is True
        assert row["value"]["n_recent"] == 3
        assert row["value"]["source_file"] == rel

        source_files = {
            "macro:engine/intelligence.py": macro_source / "engine/intelligence.py",
            "Mastermind:brain/bot_mcp.py": mastermind_source / "brain/bot_mcp.py",
            "Mastermind:portfolio/lenses.py": mastermind_source / "portfolio/lenses.py",
            "Mastermind:data_layer/macro_refresh.py": mastermind_source / "data_layer/macro_refresh.py",
        }
        receipt = {
            "scope": "offline real-git refresh and actual producer-to-consumer proof",
            "source_sha256": {
                name: hashlib.sha256(path.read_bytes()).hexdigest()
                for name, path in source_files.items()
            },
            "incumbent_functions_exercised": [
                "engine.intelligence.load_and_build",
                "data_layer.macro_refresh.ensure_clone",
                "data_layer.macro_refresh.refresh",
                "brain.bot_mcp.get_intelligence.handler",
                "portfolio.lenses._news_row",
            ],
            "fixture_initial_commit": initial_commit,
            "fixture_final_commit": final_commit,
            "actual_checkout_head_matches_committed_update": True,
            "artifact_bytes_preserved": True,
            "artifact_sha256": hashlib.sha256(final_bytes).hexdigest(),
            "news_origin": readback["news_freshness"],
            "intelligence_build_asof": readback["freshness"]["asof"],
            "bot_news_count": readback["news"]["n_recent"],
            "portfolio_status": row["status"],
            "r2_network_leg_stubbed": True,
            "new_transport_implementation_required": False,
            "production_refresh_executed": False,
            "external_managed_production_artifact_verified": False,
            "actual_model_call": False,
        }
        output = json.dumps(receipt, indent=2) + "\n"
        if args.receipt:
            args.receipt.parent.mkdir(parents=True, exist_ok=True)
            args.receipt.write_text(output)
        print(output, end="")


if __name__ == "__main__":
    main()
