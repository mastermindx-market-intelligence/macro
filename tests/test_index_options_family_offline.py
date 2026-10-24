"""Opt-in Hub GEX family staging must be inert for the scheduled publisher."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from engine.index_options_family import FamilySourceUnavailable
from scripts import build_options_hub_nightly as hub

ASOF = "2026-10-23"


def _frames(root):
    g = pd.DataFrame([{
        "date": ASOF, "expiration": "2026-11-20", "strike": 20000.0,
        "right": "C", "gamma": 0.004, "underlying_price": 20000.0,
        "implied_vol": 0.25, "delta": 0.5, "vanna": 0.0, "charm": 0.0,
    }])
    oi = pd.DataFrame([{
        "date": ASOF, "expiration": "2026-11-20",
        "strike": 20000.0, "right": "C", "open_interest": 100.0,
    }])
    return g, oi


def test_offline_candidate_uses_existing_loader_and_retains_two_contract_roots(monkeypatch, tmp_path):
    monkeypatch.setattr(hub, "greeks_for_date",
                        lambda session, root, store: _frames(root)[0])
    monkeypatch.setattr(hub, "oi_for_date",
                        lambda session, root, store: _frames(root)[1])
    out = hub.build_ndx_family_offline(ASOF, tmp_path, tmp_path / "candidate")
    assert out.name == "NDX.json"
    parsed = json.loads(out.read_text())
    assert parsed["root"] == "NDX"
    assert parsed["family_source"]["root_contract_counts"] == {"NDX": 1, "NDXP": 1}
    assert parsed["family_source"]["historical_first_available_at"] is None
    assert parsed["family_source"]["state"] == "OFFLINE_SOURCE_QUALIFIED_NOT_PUBLISHABLE"
    assert len(list((tmp_path / "candidate").rglob("*.json"))) == 1


def test_existing_target_is_preserved(monkeypatch, tmp_path):
    target = tmp_path / "candidate" / "gex" / "NDX.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"prior-publisher-bytes")
    monkeypatch.setattr(hub, "greeks_for_date",
                        lambda session, root, store: _frames(root)[0])
    monkeypatch.setattr(hub, "oi_for_date",
                        lambda session, root, store: _frames(root)[1])
    with pytest.raises(FileExistsError):
        hub.build_ndx_family_offline(ASOF, tmp_path, tmp_path / "candidate")
    assert target.read_bytes() == b"prior-publisher-bytes"


def test_missing_root_refuses_and_leaves_no_output(monkeypatch, tmp_path):
    monkeypatch.setattr(hub, "greeks_for_date",
                        lambda session, root, store:
                        pd.DataFrame() if root == "NDXP" else _frames(root)[0])
    monkeypatch.setattr(hub, "oi_for_date",
                        lambda session, root, store: _frames(root)[1])
    with pytest.raises(FamilySourceUnavailable, match="NDXP"):
        hub.build_ndx_family_offline(ASOF, tmp_path, tmp_path / "candidate")
    assert not (tmp_path / "candidate").exists()


@pytest.mark.parametrize("args", [
    ["--ndx-family-offline", "--date", ASOF, "--out", "/tmp/a", "--theta-store", "/tmp/store"],
    ["--ndx-family-offline", "--no-publish", "--date", ASOF, "--out", "/tmp/a"],
    ["--ndx-family-offline", "--no-publish", "--out", "/tmp/a", "--theta-store", "/tmp/store"],
    ["--ndx-family-offline", "--no-publish", "--date", ASOF, "--theta-store", "/tmp/store"],
    ["--ndx-family-offline", "--no-publish", "--date", ASOF, "--out", "relative", "--theta-store", "/tmp/store"],
    ["--ndx-family-offline", "--no-publish", "--date", ASOF, "--out", "/var/lib/macro-live/public/live/options_hub", "--theta-store", "/tmp/store"],
    ["--ndx-family-offline", "--no-publish", "--date", ASOF, "--out", "/tmp/a", "--theta-store", "/tmp/store", "--roots", "NDX"],
])
def test_cli_declines_implicit_publication_and_missing_scoped_inputs(monkeypatch, args):
    def forbidden(*a, **kw):
        raise AssertionError("must fail before touching scheduled producer")
    monkeypatch.setattr(hub, "_arm_stall_watchdog", forbidden)
    monkeypatch.setattr("sys.argv", ["build_options_hub_nightly.py", *args])
    with pytest.raises(SystemExit) as exc:
        hub.main()
    assert exc.value.code == 2


def test_cli_explicit_offline_never_arms_scheduled_path(monkeypatch, tmp_path):
    monkeypatch.setattr(hub, "_arm_stall_watchdog", lambda: pytest.fail("watchdog was armed"))
    observed = []
    def fake_build(asof, store, output):
        observed.append((asof, store, output))
        return output / "gex" / "NDX.json"
    monkeypatch.setattr(hub, "build_ndx_family_offline", fake_build)
    monkeypatch.setattr("sys.argv", [
        "build_options_hub_nightly.py", "--ndx-family-offline", "--no-publish",
        "--date", ASOF, "--theta-store", str(tmp_path / "store"), "--out", str(tmp_path / "candidate"),
    ])
    assert hub.main() is None
    assert observed == [(ASOF, tmp_path / "store", tmp_path / "candidate")]


def test_real_parquet_store_via_actual_cli_offline_only(monkeypatch, tmp_path):
    """Qualify actual ThetaData-shaped Parquet loader, not only monkeypatched frames."""
    for root, gamma, oi in (("NDX", 0.004, 100), ("NDXP", 0.010, 5)):
        greek, interest = _frames(root)
        greek["gamma"] = gamma
        interest["open_interest"] = oi
        greek["root"] = interest["root"] = root
        greek["date"] = pd.to_datetime(greek["date"])
        interest["date"] = pd.to_datetime(interest["date"])
        for kind, frame in (("greeks", greek), ("oi", interest)):
            path = tmp_path / "theta" / kind / root / "2026.parquet"
            path.parent.mkdir(parents=True)
            frame.to_parquet(path, index=False)
    stage = tmp_path / "offline"
    monkeypatch.setattr("sys.argv", [
        "build_options_hub_nightly.py", "--ndx-family-offline", "--no-publish",
        "--date", ASOF, "--theta-store", str(tmp_path / "theta"),
        "--out", str(stage),
    ])
    assert hub.main() is None
    result = json.loads((stage / "gex" / "NDX.json").read_text())
    assert result["schema"] == "options_hub.gex/v1"
    assert result["coverage"]["n_contracts"] == 2
    assert result["net_gex_bn"] == pytest.approx(0.18, abs=0.0001)
    assert result["family_source"]["source_roots"] == ["NDX", "NDXP"]
    assert result["family_source"]["complete_chain_receipt"] is False
    assert result["family_source"]["redistribution_grant"] is None
    assert [p.name for p in stage.rglob("*.json")] == ["NDX.json"]


def test_offline_writer_rejects_a_gex_parent_symlink_before_any_escape(monkeypatch, tmp_path):
    """Regression: the old write_text followed candidate/gex -> outside."""
    target = tmp_path / "candidate"
    outside = tmp_path / "outside"
    target.mkdir(mode=0o700)
    outside.mkdir(mode=0o700)
    (target / "gex").symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(hub, "greeks_for_date",
                        lambda session, root, store: _frames(root)[0])
    monkeypatch.setattr(hub, "oi_for_date",
                        lambda session, root, store: _frames(root)[1])
    with pytest.raises(FileExistsError):
        hub.build_ndx_family_offline(ASOF, tmp_path, target)
    assert not (outside / "NDX.json").exists()


def test_offline_writer_rejects_output_directory_symlink(monkeypatch, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir(mode=0o700)
    target = tmp_path / "candidate"
    target.symlink_to(outside, target_is_directory=True)
    monkeypatch.setattr(hub, "greeks_for_date",
                        lambda session, root, store: _frames(root)[0])
    monkeypatch.setattr(hub, "oi_for_date",
                        lambda session, root, store: _frames(root)[1])
    with pytest.raises((FileExistsError, ValueError)):
        hub.build_ndx_family_offline(ASOF, tmp_path, target)
    assert list(outside.iterdir()) == []


def test_offline_writer_exclusive_new_private_tree(monkeypatch, tmp_path):
    import stat

    monkeypatch.setattr(hub, "greeks_for_date",
                        lambda session, root, store: _frames(root)[0])
    monkeypatch.setattr(hub, "oi_for_date",
                        lambda session, root, store: _frames(root)[1])
    target = tmp_path / "candidate"
    written = hub.build_ndx_family_offline(ASOF, tmp_path, target)
    assert written == target / "gex" / "NDX.json"
    assert written.is_file()
    assert stat.S_IMODE(target.stat().st_mode) == 0o700
    assert stat.S_IMODE((target / "gex").stat().st_mode) == 0o700
    assert stat.S_IMODE(written.stat().st_mode) == 0o600
    first_bytes = written.read_bytes()
    with pytest.raises(FileExistsError):
        hub.build_ndx_family_offline(ASOF, tmp_path, target)
    assert written.read_bytes() == first_bytes
