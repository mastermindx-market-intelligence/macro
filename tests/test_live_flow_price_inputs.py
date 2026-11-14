"""Published prior-price input transport; no real network or producer effects."""
import io
import json
import subprocess
from types import SimpleNamespace

import pandas as pd
import pytest

from lib import live_flow_price_inputs as inputs

SESSION = "2026-10-19"
SHA = "a" * 40


def frame(day="2026-10-16", value=500.0):
    stream = io.BytesIO()
    pd.DataFrame({"close_price": [value], "close": [450.0]},
                 index=pd.to_datetime([day])).to_parquet(stream)
    return stream.getvalue()


def git_source(monkeypatch, blobs, *, origin=None, failure=None):
    calls = []

    def run(command, **kwargs):
        args = command[7:]
        calls.append(args)
        assert kwargs["check"] and kwargs["capture_output"]
        assert 0 < kwargs["timeout"] <= 120
        if args[:3] == ["remote", "get-url", "origin"]:
            return SimpleNamespace(stdout=(origin or sorted(inputs.ORIGINS)[0]).encode())
        if args[0] == "fetch":
            if failure:
                raise failure
            assert "--filter=blob:none" in args
            assert "--no-write-fetch-head" in args
            assert args[-1] == f"+refs/heads/main:{inputs.SOURCE_REF}"
            return SimpleNamespace(stdout=b"")
        if args[0] == "rev-parse":
            return SimpleNamespace(stdout=SHA.encode())
        root = args[-1].rsplit("/", 1)[-1].removesuffix(".parquet")
        raw = blobs.get(root)
        if isinstance(raw, Exception):
            raise raw
        if raw is None:
            raise subprocess.CalledProcessError(128, command)
        if args[0] == "cat-file":
            return SimpleNamespace(stdout=str(len(raw)).encode())
        assert args[0] == "show"
        return SimpleNamespace(stdout=raw)

    monkeypatch.setattr(inputs.subprocess, "run", run)
    return calls


class TestPublishedPriceInputs:
    def test_exact_price_and_provenance_are_saved_then_reused(self, tmp_path, monkeypatch):
        calls = git_source(monkeypatch, {"SPY": frame()})
        out = inputs.sync_prior_closes(tmp_path, tmp_path, ["SPY"], SESSION)
        assert out["status"] == "complete"
        assert inputs.load_prior_close(tmp_path, "SPY", SESSION) == 500
        doc = json.loads((tmp_path / inputs.RELATIVE_PATH).read_text())
        assert doc["source_git_sha"] == SHA
        assert doc["source_session"] == "2026-10-16"
        assert doc["prices"]["SPY"]["source_bytes"] == len(frame())
        previous_calls = len(calls)
        assert inputs.sync_prior_closes(tmp_path, tmp_path, ["SPY"], SESSION)["status"] == "already_current"
        assert len(calls) == previous_calls
        assert inputs.load_prior_close(tmp_path, "SPY", "2026-10-20") is None
        assert not any(call[0] in {"checkout", "reset", "pull", "merge", "switch"} for call in calls)

    def test_partial_does_not_fill_gaps_with_stale_or_total_return_prices(self, tmp_path, monkeypatch):
        git_source(monkeypatch, {"SPY": frame(), "ARKK": frame("2026-10-14")})
        out = inputs.sync_prior_closes(tmp_path, tmp_path, ["SPY", "ARKK", "SLV"], SESSION)
        assert out["available"] == 1 and out["status"] == "partial"
        assert out["unavailable"] == {"ARKK": "exact_prior_price_unavailable", "SLV": "published_blob_unavailable"}
        assert inputs.load_prior_close(tmp_path, "ARKK", SESSION) is None
        git_source(monkeypatch, {"SPY": frame(), "ARKK": frame(), "SLV": frame()})
        assert inputs.sync_prior_closes(tmp_path, tmp_path, ["SPY", "ARKK", "SLV"], SESSION)["status"] == "complete"

    @pytest.mark.parametrize("failure", [subprocess.CalledProcessError(128, "git"), subprocess.TimeoutExpired("git", 120), TimeoutError("bound")])
    def test_failed_fetch_preserves_original_bytes(self, tmp_path, monkeypatch, failure):
        output = tmp_path / inputs.RELATIVE_PATH
        output.parent.mkdir()
        output.write_bytes(b"original unavailable evidence\n")
        git_source(monkeypatch, {}, failure=failure)
        with pytest.raises(type(failure)):
            inputs.sync_prior_closes(tmp_path, tmp_path, ["SPY"], SESSION)
        assert output.read_bytes() == b"original unavailable evidence\n"

    def test_blob_deadline_does_not_replace_old_file_with_empty_success(self, tmp_path, monkeypatch):
        output = tmp_path / inputs.RELATIVE_PATH
        output.parent.mkdir()
        output.write_bytes(b"retained\n")
        git_source(monkeypatch, {"SPY": TimeoutError("bound")})
        with pytest.raises(TimeoutError):
            inputs.sync_prior_closes(tmp_path, tmp_path, ["SPY"], SESSION)
        assert output.read_bytes() == b"retained\n"

    def test_noncanonical_origin_refused_before_fetch(self, tmp_path, monkeypatch):
        calls = git_source(monkeypatch, {}, origin="https://other.example/macro.git")
        with pytest.raises(ValueError, match="origin"):
            inputs.sync_prior_closes(tmp_path, tmp_path, ["SPY"], SESSION)
        assert len(calls) == 1
        assert not (tmp_path / inputs.RELATIVE_PATH).exists()

    @pytest.mark.parametrize("root", ["../SPY", "SPY;rm", "", "a", "SPY/QQQ"])
    def test_invalid_root_has_no_transport_effect(self, tmp_path, monkeypatch, root):
        calls = git_source(monkeypatch, {})
        with pytest.raises(ValueError):
            inputs.sync_prior_closes(tmp_path, tmp_path, [root], SESSION)
        assert calls == []

    @pytest.mark.parametrize("field,value", [("close_price", True), ("close_price", 0), ("close_price", "500"), ("close_price", float("inf")), ("source_sha256", []), ("source_session", "2026-10-14"), ("source_path", "data/yahoo/QQQ.parquet"), ("source_bytes", True), ("close_price", 10**400)])
    def test_malformed_cached_entry_stays_unknown(self, tmp_path, monkeypatch, field, value):
        git_source(monkeypatch, {"SPY": frame()})
        inputs.sync_prior_closes(tmp_path, tmp_path, ["SPY"], SESSION)
        output = tmp_path / inputs.RELATIVE_PATH
        doc = json.loads(output.read_text())
        doc["prices"]["SPY"][field] = value
        output.write_text(json.dumps(doc))
        assert inputs.load_prior_close(tmp_path, "SPY", SESSION) is None

    def test_oversize_and_invalid_frames_remain_explicit(self, tmp_path, monkeypatch):
        git_source(monkeypatch, {"SPY": b"x" * (inputs.MAX_BLOB_BYTES + 1), "QQQ": b"not parquet"})
        out = inputs.sync_prior_closes(tmp_path, tmp_path, ["SPY", "QQQ"], SESSION)
        assert out["unavailable"] == {"SPY": "source_size_out_of_bounds", "QQQ": "published_frame_invalid"}
        assert out["available"] == 0

    def test_real_filtered_git_read_preserves_runtime_checkout(self, tmp_path, monkeypatch):
        """Exercise Git's public filtered-fetch path against an isolated fixture."""
        source = tmp_path / "source"
        runtime = tmp_path / "runtime"
        source.mkdir()
        def git(cwd, *args):
            return subprocess.run(["git", "-C", str(cwd), *args], check=True,
                                  capture_output=True, text=True).stdout.strip()
        git(source, "init", "-b", "main")
        git(source, "config", "user.name", "Fixture")
        git(source, "config", "user.email", "fixture@example.invalid")
        git(source, "config", "uploadpack.allowFilter", "true")
        (source / "runtime.txt").write_text("retain this runtime\n")
        git(source, "add", "runtime.txt")
        git(source, "commit", "-m", "fixture runtime")
        origin = source.as_uri()
        git(tmp_path, "clone", "--filter=blob:none", "--depth=1", origin, str(runtime))
        old_head = git(runtime, "rev-parse", "HEAD")
        old_index = (runtime / ".git/index").read_bytes()
        old_config = (runtime / ".git/config").read_bytes()
        (source / "data/yahoo").mkdir(parents=True)
        (source / "data/yahoo/SPY.parquet").write_bytes(frame())
        git(source, "add", "data/yahoo/SPY.parquet")
        git(source, "commit", "-m", "fixture published price")
        publication = git(source, "rev-parse", "HEAD")
        monkeypatch.setattr(inputs, "ORIGINS", frozenset({origin}))
        result = inputs.sync_prior_closes(runtime, tmp_path / "consumer-data", ["SPY"], SESSION)
        assert result["source_git_sha"] == publication
        assert result["status"] == "complete"
        assert inputs.load_prior_close(tmp_path / "consumer-data", "SPY", SESSION) == 500
        assert git(runtime, "rev-parse", "HEAD") == old_head
        assert (runtime / ".git/index").read_bytes() == old_index
        assert (runtime / ".git/config").read_bytes() == old_config
        assert not (runtime / "data").exists()
