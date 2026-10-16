#!/usr/bin/env python3
"""Run an isolated, executable CN interface experiment against immutable Git source.

Usage: python3 run_lab.py --repo /path/to/macro --out /tmp/cn-integration-results
No source-tree data writes, credential reads, network calls or production publish.
The next-session quotes and settlement board are explicitly SYNTHETIC fixtures.
"""
from __future__ import annotations

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256, sha1
import importlib
import gzip
from functools import partial
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tarfile
import tempfile
from unittest.mock import patch

from contract_prototype import (BOARD_PATH, EVENT_SCHEMA, INGEST_CONTRACT, MemoryR2,
    Refused, bind_pack, consume, digest, encoded, envelope, evaluate_checked,
    frozen_board, pack_key, reconcile_file, spool_key, stamp, validate_pack, SyntheticQuoteResolver)

PIN = "3d90aad6d83152dfeeaf8345bc995826ac9d3139"
UTC = timezone.utc
WATCHED_SOURCE = (
    "engine/live_quotes.py", "engine/marketing/live_verify.py", "scripts/build_live_quotes.py",
    "scripts/build_cn_live_pack.py", "engine/prophet_live/cn_pack.py",
    "scripts/cn_live_evaluator.py", "engine/prophet_live/cn_states.py",
    "scripts/reconcile_cn_live.py", "engine/prophet_live/cn_reconcile.py",
    "engine/prophet_live/r2io.py", "engine/prophet_live/live_states.py",
    "engine/prophet_live/armed_pack.py", "engine/prophet_live/interval.py",
    "engine/prophet_live/cn_clock.py", "lib/cn_calendar.py",
    "lib/exchange_holidays.py", "engine/signal_gate.py", "engine/confluence_latch.py",
    ".github/workflows/asia-close.yml", "config/dag.yml", "config.yml",
    "research/CN_BREATHING_PLATFORM_ARCHITECTURE_2026-08-15.md",
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--source-root", help="reuse this experiment's existing temporary export")
    parser.add_argument("--sha", default=PIN)
    args = parser.parse_args()
    if args.sha != PIN:
        raise ValueError("This recorded experiment is frozen to the commission study pin")
    out = Path(args.out).resolve()
    repo_path = Path(args.repo).resolve()
    if out == repo_path or out.is_relative_to(repo_path):
        raise ValueError("Laboratory output must be outside the source repository")
    out.mkdir(parents=True, exist_ok=True)
    provenance = {}

    def git(*parts):
        return subprocess.check_output(["git", "-C", args.repo, *parts])

    def blob(path):
        raw = git("show", f"{PIN}:{path}")
        provenance[path] = {"sha256": sha256(raw).hexdigest(), "bytes": len(raw),
            "git_blob": sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}
        return raw

    if args.source_root:
        source = Path(args.source_root).resolve()
        if source == repo_path or source.is_relative_to(repo_path):
            raise ValueError("Never import from the shared source worktree in this laboratory")
        if not any(part.startswith("mmx-cn-integration-lab-") for part in source.parts):
            raise ValueError("Only a separately created integration-lab temporary source is permitted")
    else:
        source = Path(tempfile.mkdtemp(prefix="mmx-cn-integration-lab-")) / "source"
        source.mkdir()
        archive = git("archive", PIN, "engine", "lib", "scripts")
        with tarfile.open(fileobj=io.BytesIO(archive)) as ar:
            for member in ar.getmembers():
                if member.name.startswith("/") or ".." in Path(member.name).parts or member.issym() or member.islnk():
                    raise ValueError(member.name)
            ar.extractall(source)
    for path in WATCHED_SOURCE:
        original = blob(path)
        dest = source / path
        if path.startswith(("engine/", "lib/", "scripts/")):
            assert dest.read_bytes() == original, path
    for path in ("config.yml", "data/confluence_latch/cn_t2.parquet",
                 "data/china/000001.SS.parquet", BOARD_PATH):
        dest = source / path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(blob(path))
    import yaml
    storage = yaml.safe_load((source / "config.yml").read_text())["storage"]
    assert not Path(storage["data_dir"]).is_absolute()
    os.environ["CN_PROPHET_LIVE_NO_PUBLISH"] = "1"
    os.environ["PROPHET_LIVE_NO_PUBLISH"] = "1"
    os.chdir(source)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    import pandas as pd
    from engine.prophet_live import cn_pack as CP, cn_states as CS, cn_clock as clock
    from engine.prophet_live import armed_pack as AP, live_states as LS, cn_reconcile as CR
    from engine.prophet_live import r2io as R2, interval
    from lib import cn_calendar as calendar
    from scripts import build_cn_live_pack as BD, cn_live_evaluator as ED, reconcile_cn_live as RD
    from engine.confluence_latch import EventLatch

    quote_resolver = SyntheticQuoteResolver(blob("engine/live_quotes.py"))
    checked_evaluate = partial(evaluate_checked, quote_resolver=quote_resolver)

    results = {"schema": "cn-integration-contract-repair/v1", "study_source_sha": PIN,
        "isolated_source_export": str(source),
        "status": "RUNNING", "safety": {"all_quotes_synthetic": True,
        "settlement_board_synthetic": True, "object_store": "memory only",
        "ledger": "temporary file only", "no_publish_switches": True,
        "production_source_or_data_changed": False, "natural_process_proof": False},
        "native_controls": {}, "prototype_checks": [], "hostile_checks": []}
    checks = results["prototype_checks"]
    hostile = results["hostile_checks"]
    log = io.StringIO()

    def check(name, test, **detail):
        assert test, name
        checks.append({"name": name, "status": "PASS", **detail})

    def refusal(name, fn, expected):
        try:
            fn()
        except Refused as exc:
            assert exc.reason == expected, (name, exc.reason, expected)
            hostile.append({"name": name, "status": "PASS", "reason": exc.reason})
        else:
            raise AssertionError(f"{name}: invalid evidence accepted")

    raw_board = (source / BOARD_PATH).read_bytes()
    board = json.loads(raw_board)
    asof = board["as_of"]
    rows, board_id = frozen_board(raw_board, expected_asof=asof)
    results["native_controls"]["real_canonical_reader_rows"] = len(BD.load_frozen(source))
    assert len(BD.load_frozen(source)) == 0
    first = board["buy"][0]
    raw_attach = CP.attach_frozen({}, first)
    results["native_controls"]["raw_attach_frozen"] = raw_attach["frozen"]
    assert "score" not in raw_attach["frozen"] and "rank" not in raw_attach["frozen"]
    with tempfile.TemporaryDirectory(prefix="reader-control-", dir=out) as temp:
        old_path = Path(temp) / "site/china_standouts.json"
        old_path.parent.mkdir(parents=True)
        old_path.write_bytes(raw_board)
        assert BD.load_frozen(Path(temp)) == {}
        results["native_controls"]["path_only_repair_rows"] = 0
    check("canonical_primary_lanes_read_once", len(rows) == 180,
          rows=len(rows), alias_watch_rows_ignored=len(board["watch"]))

    # Every canonical score and published board rank goes through the actual
    # native CP.assemble/attach_frozen. This is an I/O check, not a 180-name probe.
    projection_entries = {t: {"as_of_close": float(row["price"]), "probed": False,
                             "state": "dormant", "center_buyable": False}
                          for t, row in rows.items()}
    projected = CP.assemble(projection_entries, as_of=asof, cfg=CP.pack_cfg(None),
        universe_n=len(rows), wanted_n=0, gate_calls=0, build_seconds=0,
        skipped={}, frozen=rows, now=datetime(2026, 10, 9, 12, tzinfo=UTC))
    projected = bind_pack(projected, rows, board_id)
    check("exact_frozen_projection_all_180", all(
        projected["names"][t]["frozen"]["score"] == row["prophet"]["score"] and
        projected["names"][t]["frozen"]["rank"] == row["board_rank"]
        for t, row in rows.items()))
    check("no_projection_rank_reordering", list(projected["names"]) == list(rows))
    changed = deepcopy(board)
    changed["buy"][0]["score_rank"] = 999
    changed["buy"][0]["prophet"]["score"] = 0.0
    mapped, _ = frozen_board(encoded(changed), expected_asof=asof)
    zero = CP.attach_frozen({}, mapped[first["ticker"]])["frozen"]
    check("zero_score_and_board_vs_score_rank_semantics", zero["score"] == 0.0
          and zero["rank"] == first["board_rank"] and zero["rank"] != 999)

    # A small genuine probe on immutable price/latch inputs, with no gate stub.
    selected = [board["buy"][0]["ticker"], board["buy"][1]["ticker"],
                board["forming"][0]["ticker"]]
    prices = {t: pd.read_parquet(io.BytesIO(blob(f"data/china_stocks/{t}.parquet"))).close
              for t in selected}
    latch = EventLatch("CN", record=False).load()
    gate = CP.make_cn_gate(latch)
    center_verdicts = {t: gate(t, close) for t, close in prices.items()}
    check("native_gate_dependencies_complete", all(v.get("reason") != "engine error"
          for v in center_verdicts.values()))
    with redirect_stdout(log):
        native_pack = BD.build(root=source, series=prices, frozen=rows,
            cfg={"cn_prophet_live": {"max_probe": 3}}, gate_fn=gate,
            now=datetime(2026, 10, 9, 12, tzinfo=UTC))
    pack = bind_pack(native_pack, rows, board_id)
    validate_pack(pack, expected_asof=asof)
    results["real_probe"] = {"tickers": selected, "names": pack["names"], "meta": pack["meta"],
                              "latch_record": False, "gate": "native signal_gate.gate",
                              "center_verdicts": {t: {k: v.get(k) for k in ("eligible", "tier", "tier_cascade", "reason")}
                                                  for t, v in center_verdicts.items()}}
    (out / "native_probe_debug.json").write_bytes(encoded(results["real_probe"]))
    check("native_gate_probe_no_mismatches", not pack["meta"]["edge_mismatches"]
          and not AP.membership_mismatches(pack["names"]),
          edges=pack["meta"]["edges_checked"], probed=pack["meta"]["probed_n"])
    check("real_pack_has_armed_observation", any(e.get("buyable_in_band") for e in pack["names"].values()))

    def quotes_for(now, *, quote_at=None, price_changes=None):
        # Provider-shaped bytes are synthetic observations. Their units are
        # defined by the explicit research contract; the pinned parser is real.
        qts = quote_at or (now.replace(hour=7, minute=0, second=0)
                           if clock.phase(now) == "post_close" else now)
        payload = {"spark": {"result": [], "error": None}}
        for ticker, e in pack["names"].items():
            px = e["as_of_close"]
            if e.get("buyable_in_band"):
                low = max(float(interval.lower_edge(e) or 0), float(e.get("band_lo_px") or 0), .01)
                high = float(e.get("fade_hi_px") or e["band_hi_px"])
                px = round((low + high) / 2, 4)
            px = (price_changes or {}).get(ticker, px)
            payload["spark"]["result"].append({"symbol": ticker, "response": [{"meta": {
                "regularMarketPrice": px, "previousClose": e["as_of_close"],
                "regularMarketTime": int(qts.timestamp()), "currency": "CNY"}}]})
        return quote_resolver.quotes(encoded(payload), recorded_at=now)

    morning = datetime(2026, 10, 12, 2, 0, tzinfo=UTC)
    cfg = LS.live_cfg({"live": {"delayed_min": 0}})
    unmodified = CS.evaluate(pack, quotes_for(morning), None, now=morning, cfg=cfg, delay_min=0)
    native_events = unmodified["events"]
    assert native_events
    lost = CR.events_to_rows(native_events, session="2026-10-12")
    results["native_controls"]["real_evaluator_events"] = native_events
    results["native_controls"]["native_reconciled_event_rows"] = lost
    assert all(row["first_px"] is None for row in lost)
    assert any(ev["session_phase"] != "morning" for ev in native_events)
    assert any(ev["kind"] == "confirming_into_close" for ev in native_events)

    store = MemoryR2(page_size=2)
    store.put(R2.CN_PACK_KEY, pack)
    store.put(pack_key(pack, R2), pack)
    native_evaluate = CS.evaluate
    passes = []
    conf = {"live": {"delayed_min": 0},
            "cn_prophet_live": {"served_path": "", "local_quote_paths": []}}
    for now in (morning, morning + timedelta(minutes=5),
                morning.replace(hour=3, minute=35), morning.replace(hour=5),
                morning.replace(hour=7, minute=1), morning.replace(hour=7, minute=6)):
        captured = {}

        def guarded(p, q, prev, **kw):
            got = checked_evaluate(native_evaluate, LS, clock, p, q, prev, **kw)
            captured["events"] = deepcopy(got.get("events", []))
            return got

        def local_publish(key, payload, **kw):
            if key.startswith(R2.CN_EVENTS_PREFIX + "/"):
                current = json.loads(store.objects[R2.CN_LIVE_KEY])
                doc = envelope(current, payload["events"], pack)
                return store.put(spool_key(doc, R2), doc)
            return store.put(key, payload)

        class FrozenDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return now.astimezone(tz or UTC)

        with patch.object(R2, "client", lambda: store), \
             patch.object(R2, "put_json", local_publish), \
             patch.object(CS, "evaluate", guarded), \
             patch.object(ED, "load_local_quotes", lambda _: {"quotes": quotes_for(now),
                 "asof": now.isoformat(), "source": "SYNTHETIC_RESEARCH_FIXTURE"}), \
             patch.object(ED, "datetime", FrozenDatetime), redirect_stdout(log):
            rc = ED.run(source, now=now, cfg=conf)
        assert rc == 0
        current = json.loads(store.objects[R2.CN_LIVE_KEY])
        # Proposed driver extension persists the close snapshot even with no new
        # transitions; the unchanged driver only spools non-empty events.
        if current.get("close_board"):
            doc = envelope(current, captured["events"], pack)
            store.put(spool_key(doc, R2), doc)
        passes.append({"time": now.isoformat(), "phase": current["market_phase"],
            "event_count": len(captured["events"]), "states": current["meta"]["states"],
            "close_board": bool(current.get("close_board"))})
    results["driver_passes"] = passes
    check("real_driver_six_offline_passes", len(passes) == 6)
    check("lunch_keeps_state_without_new_events", passes[2]["event_count"] == 0)
    check("zero_event_close_board_persisted", passes[-1]["event_count"] == 0
          and passes[-1]["close_board"])
    check("native_publish_switches_remain_set", os.environ["CN_PROPHET_LIVE_NO_PUBLISH"] == "1"
          and os.environ["PROPHET_LIVE_NO_PUBLISH"] == "1")

    final_live = json.loads(store.objects[R2.CN_LIVE_KEY])
    session = "2026-10-12"
    settled_at = datetime(2026, 10, 12, 12, tzinfo=UTC)
    # Explicit synthetic N settlement fixture. No October 12 market observations
    # existed when this lab was commissioned; these are NOT price/performance data.
    settle_board = deepcopy(board)
    settle_board["as_of"] = session
    settle_board["research_fixture"] = "SYNTHETIC_NEXT_SESSION_CANONICAL_INTERFACE_ONLY"
    dropped = selected[1]
    for lane in ("buy", "more_actionable", "late_or_unfillable", "forming"):
        settle_board[lane] = [r for r in settle_board[lane] if r["ticker"] != dropped]
        for row in settle_board[lane]:
            row["data_through"] = session
    settle_rows, settle_id = frozen_board(encoded(settle_board), expected_asof=session)
    settle_names = deepcopy(native_pack["names"])
    for ticker, entry in settle_names.items():
        entry.pop("frozen", None)
        entry["center_buyable"] = ticker != dropped
    settlement = CP.assemble(settle_names, as_of=session, cfg=CP.pack_cfg(None),
        universe_n=len(settle_names), wanted_n=0, gate_calls=0, build_seconds=0,
        skipped={}, frozen=settle_rows, now=settled_at - timedelta(minutes=5))
    settlement = bind_pack(settlement, settle_rows, settle_id)
    store.put(R2.CN_PACK_KEY, settlement)  # exact workflow rollover sequence
    store.put(pack_key(settlement, R2), settlement)

    def ingest(s=store, *, prior=None, settle=settlement, canon=settle_board):
        return consume(s, R2, CR, clock, calendar, LS, session=session, now=settled_at,
            existing=[] if prior is None else prior, settlement_pack=settle, canonical_board=canon,
            canonical_board_raw=(raw_board if canon is board else encoded(canon)) if canon is not None else None,
            quote_resolver=quote_resolver)

    ledger, receipt = ingest()
    check("events_reconciled_after_current_pack_rollover", bool(ledger)
          and all(row["first_pack_id"] == pack["pack_id"] for row in ledger)
          and receipt["archived_packs"] == [pack["pack_id"]])
    check("native_event_price_survives", all(row["first_px"] > 0 for row in ledger))
    check("cn_event_phase_survives", all(row["session_phase"] == "morning" for row in ledger))
    check("no_us_close_marker", all(row["kind"] != "confirming_into_close" for row in ledger))
    check("board_observation_and_true_cross_remain_distinct", all(
        row["entered"] == ("cross" if row["ticker"] == selected[2] else "board") for row in ledger))
    check("score_rank_frozen_through_ledger", all(row["frozen_score"] == rows[row["ticker"]]["prophet"]["score"]
        and row["frozen_rank"] == rows[row["ticker"]]["board_rank"] for row in ledger))
    check("confirmation_uses_settlement_gate_not_provisional_presence",
          any(row["ticker"] == dropped and row["confirmed"] is False for row in ledger))
    check("membership_receipt_is_separate", dropped in receipt["receipt"]["dropped"])
    again, replay_receipt = ingest(prior=ledger)
    check("duplicate_replay_exact_idempotence", encoded(ledger) == encoded(again))
    unconfirmed, _ = ingest(settle=None, canon=board)
    check("unavailable_same_session_confirmation_stays_null", all(r["confirmed"] is None for r in unconfirmed))
    _, stale_receipt = ingest(canon=board)
    check("old_canonical_board_cannot_confirm_new_session", stale_receipt["receipt"] is None)
    output_ledger = out / "synthetic_forward.parquet"
    # This is a fresh lab output, never an existing production ledger. Remove a
    # prior lab run's artifact so nondeterministic measured build time cannot make
    # two independently constructed pack generations look like one replay.
    if output_ledger.exists():
        output_ledger.unlink()
    file_rows, _ = reconcile_file(output_ledger, read_frame=pd.read_parquet,
        write_rows=RD._write_parquet, reconcile=lambda old: ingest(prior=old))
    got = pd.read_parquet(output_ledger).to_dict(orient="records")
    check("native_atomic_parquet_writer_roundtrip", len(got) == len(ledger)
          and [r["first_px"] for r in got] == [r["first_px"] for r in ledger])
    replayed_file_rows, _ = reconcile_file(output_ledger, read_frame=pd.read_parquet,
        write_rows=RD._write_parquet, reconcile=lambda old: ingest(prior=old))
    check("actual_parquet_read_replay_idempotence", encoded(replayed_file_rows) == encoded(file_rows))

    # Actual old driver accepts the native event shape but drops its price and
    # labels every observed provisional close member confirmed, even a drop.
    native_dir = out / "native_driver_control"
    native_dir.mkdir(exist_ok=True)
    for name, obj in {"events.json": {"session": session, "events": native_events},
                      "close.json": final_live, "standouts.json": settle_board}.items():
        (native_dir / name).write_bytes(encoded(obj))
    with patch.dict(os.environ, {"CN_LANE": "asia"}), redirect_stdout(log):
        RD.run_asia(pack_path=None, events_path=native_dir / "events.json",
            close_board_path=native_dir / "close.json", standouts_path=native_dir / "standouts.json",
            out_path=native_dir / "forward.parquet", now=settled_at)
    old_rows = pd.read_parquet(native_dir / "forward.parquet").to_dict(orient="records")
    results["native_controls"]["real_driver_rows"] = json.loads(json.dumps(old_rows, default=str))
    assert all(r["first_px"] is None for r in old_rows)
    assert any(r["ticker"] == dropped and r["confirmed"] is True for r in old_rows)
    corrupt = native_dir / "corrupt.parquet"
    corrupt.write_bytes(b"INTENTIONALLY_INVALID_RESEARCH_LEDGER")
    with patch.dict(os.environ, {"CN_LANE": "asia"}), redirect_stdout(log):
        RD.run_asia(pack_path=None, events_path=native_dir / "events.json",
            close_board_path=None, standouts_path=native_dir / "standouts.json",
            out_path=corrupt, now=settled_at)
    results["native_controls"]["unreadable_ledger_replaced_by_native_driver"] = len(pd.read_parquet(corrupt))
    assert len(pd.read_parquet(corrupt)) == len(lost)

    # Hostile evidence tests: each must be refused before a ledger writer runs.
    for name, mutate, expected in (
        ("duplicate_board_ticker", lambda b: b["forming"].append(deepcopy(b["buy"][0])), "duplicate_primary_ticker"),
        ("invalid_board_rank", lambda b: b["buy"][0].update(board_rank=0), "invalid_frozen_rank"),
        ("invalid_board_score", lambda b: b["buy"][0]["prophet"].update(score=True), "invalid_frozen_score"),
        ("row_wrong_day", lambda b: b["buy"][0].update(data_through="2026-10-08"), "row_date_disagreement"),
    ):
        bad = deepcopy(board); mutate(bad)
        refusal(name, lambda b=bad: frozen_board(encoded(b), expected_asof=asof), expected)
    refusal("stale_board", lambda: frozen_board(raw_board, expected_asof="2026-10-12"), "board_asof_mismatch")
    bad_pack = deepcopy(pack); bad_pack["names"][selected[0]]["frozen"]["rank"] += 1
    refusal("tampered_pack_rank", lambda: validate_pack(bad_pack), "pack_hash_mismatch")
    refusal("new_settlement_pack_cannot_evaluate_old_session", lambda: checked_evaluate(
        native_evaluate, LS, clock, settlement, quotes_for(morning), None, now=morning, cfg=cfg),
        "stale_or_future_pack")
    for name, field, val, reason in (
        ("future_quote", "quote_ts", (morning + timedelta(days=1)).isoformat(), "future_quote"),
        ("prior_session_quote", "quote_ts", "2026-10-09T07:00:00Z", "wrong_quote_session"),
        ("invalid_quote_price", "price", -1.0, "invalid_quote_price"),
    ):
        q = quotes_for(morning); q[selected[0]][field] = val
        art = checked_evaluate(native_evaluate, LS, clock, pack, q, None, now=morning, cfg=cfg)
        check(name + "_per_name_dark", art["names"][selected[0]]["reason"] == reason
              and not any(e["ticker"] == selected[0] for e in art["events"]))
    stale_q = quotes_for(morning, quote_at=morning.replace(hour=1))
    stale_art = checked_evaluate(native_evaluate, LS, clock, pack, stale_q, None, now=morning, cfg=cfg)
    check("native_stale_quote_guard_preserved", stale_art["names"][selected[0]]["reason"] == "stale_quote")
    prev = deepcopy(final_live); prev["pack_id"] = "f" * 64
    reset = checked_evaluate(native_evaluate, LS, clock, pack, quotes_for(morning), prev, now=morning, cfg=cfg)
    check("wrong_generation_predecessor_resets_debounce", reset["meta"]["generation_reset"])

    event_keys = sorted(k for k in store.objects if k.startswith(R2.CN_EVENTS_PREFIX + "/"))
    active_key = next(k for k in event_keys if json.loads(store.objects[k])["events"])

    def changed_spool(change, *, key=active_key):
        s = deepcopy(store)
        doc = json.loads(s.objects.pop(key))
        change(doc)
        s.objects[spool_key(doc, R2)] = encoded(doc)
        return s

    for name, mutate, reason in (
        ("wrong_envelope_session", lambda d: d.update(session="2026-10-13"), "no_spool_evidence"),
        ("legacy_unbound_envelope", lambda d: d.update(schema="legacy"), "legacy_or_unknown_spool_schema"),
        ("wrong_event_generation", lambda d: d["source_board"].update(artifact_sha256="f" * 64), "event_generation_mismatch"),
        ("wrong_event_pack_day", lambda d: d.update(pack_as_of=session), "wrong_event_pack_session"),
        ("event_unknown_ticker", lambda d: d["events"][0].update(ticker="999999.SZ"), "event_ticker_outside_pack"),
        ("event_unknown_kind", lambda d: d["events"][0].update(kind="buy_now_forever"), "invalid_event_kind"),
        ("event_future_clock", lambda d: d["events"][0].update(ts="2026-10-13T02:00:00Z"), "future_event"),
        ("event_us_phase", lambda d: d["events"][0].update(session_phase="rth"), "wrong_event_phase"),
        ("event_invalid_price", lambda d: d["events"][0].update(price=-1), "invalid_event_price"),
        ("event_stale_quote", lambda d: d["events"][0].update(quote_ts="2026-10-12T01:00:00Z"), "stale_event_quote"),
        ("event_wrong_entry_class", lambda d: d["events"][0].update(entered="cross"), "event_entry_class_disagreement"),
        ("event_ambiguous_price_alias", lambda d: d["events"][0].update(px=0.01), "ambiguous_event_price"),
        ("event_unknown_adjustment", lambda d: d["events"][0].update(price_adjustment="maybe_raw"), "unknown_event_price_adjustment"),
        ("event_identity_modified", lambda d: d["events"][0].update(event_id="f" * 64), "event_identity_mismatch"),
    ):
        if name == "wrong_envelope_session":
            # Keep the original path to model a body/path mismatch, rather than
            # move all future-session data out of the requested listing.
            s = deepcopy(store); d = json.loads(s.objects[active_key]); mutate(d)
            s.objects[active_key] = encoded(d)
            refusal(name, lambda s=s: ingest(s), "spool_session_mismatch")
        else:
            s = changed_spool(mutate)
            refusal(name, lambda s=s: ingest(s), reason)
    bad_listing = deepcopy(store); bad_listing.fail_page = 2
    refusal("partial_spool_listing", lambda: ingest(bad_listing), "incomplete_spool_list")
    bad_read = deepcopy(store); bad_read.fail_get.add(active_key)
    refusal("missing_spool_body", lambda: ingest(bad_read), "unreadable_spool_object")
    repeated = changed_spool(lambda d: d["events"].append(deepcopy(d["events"][0])))
    repeated_rows, repeated_receipt = ingest(repeated)
    check("duplicate_event_id_not_double_counted", encoded(repeated_rows) == encoded(ledger)
          and repeated_receipt["distinct_events"] == receipt["distinct_events"])
    no_archive = deepcopy(store); del no_archive.objects[pack_key(pack, R2)]
    refusal("lost_prior_pack_archive", lambda: ingest(no_archive), "unreadable_spool_object")
    forged = deepcopy(ledger); forged[0]["first_pack_id"] = "f" * 64
    refusal("existing_row_generation_conflict", lambda: ingest(prior=forged), "existing_identity_conflict")
    legacy = deepcopy(ledger); legacy[0].pop("ingest_contract")
    refusal("legacy_row_cannot_gain_invented_provenance", lambda: ingest(prior=legacy), "legacy_unbound_row")
    prior_more = deepcopy(ledger); prior_more[0]["event_ids"].append("a" * 64)
    refusal("spool_regression_cannot_overwrite_counts", lambda: ingest(prior=prior_more), "spool_regression")
    confirm_conflict = deepcopy(ledger); confirm_conflict[0]["confirmed"] = not confirm_conflict[0]["confirmed"]
    refusal("confirmation_revision_requires_separate_adjudication", lambda: ingest(prior=confirm_conflict),
            "confirmation_revision_conflict")
    wrong_canonical = deepcopy(settle_board); wrong_canonical["research_fixture"] += "_DIFFERENT_GENERATION"
    refusal("same_day_canonical_generation_must_match_settlement_pack", lambda: ingest(canon=wrong_canonical),
            "settlement_canonical_generation_disagreement")
    close_key = next(k for k in event_keys if json.loads(store.objects[k])["close_board"])
    wrong_close = changed_spool(lambda d: d["close_board"].update(session="2026-10-09"), key=close_key)
    refusal("wrong_close_session", lambda: ingest(wrong_close), "close_board_session_mismatch")
    wrong_close_gen = changed_spool(lambda d: d["close_board"].update(pack_id="a" * 64), key=close_key)
    refusal("wrong_close_generation", lambda: ingest(wrong_close_gen), "close_board_generation_mismatch")

    # The strict adapter must stop before native _write_parquet on unreadable
    # input. Distinguish absent from corrupt; do not copy native _read_parquet's
    # corrupt->empty behavior into the production repair.
    sentinel = out / "unreadable_ledger_guard.parquet"
    sentinel.write_bytes(b"INTENTIONALLY_INVALID_RESEARCH_LEDGER")
    before = sentinel.read_bytes()
    refusal("unreadable_ledger_refuses_write", lambda: reconcile_file(sentinel,
        read_frame=pd.read_parquet, write_rows=RD._write_parquet,
        reconcile=lambda old: ingest(prior=old)), "unreadable_existing_ledger")
    check("refusal_preserves_existing_bytes", sentinel.read_bytes() == before)

    from repair_checks import run_repair_checks
    results["repair_assessments"] = run_repair_checks(
        check=check, refusal=refusal, ingest=ingest, store=store, pack=pack,
        ledger=ledger, morning=morning, settled_at=settled_at,
        quote_resolver=quote_resolver, quotes_for=quotes_for,
        native_evaluate=native_evaluate, LS=LS, clock=clock, CR=CR, RD=RD, R2=R2,
        pd=pd, out=out, cfg=cfg)

    # Retain exact object envelopes as reviewable synthetic evidence, not a
    # production store. Their archived generations are all under the same owner.
    canonical_bytes = encoded(settle_board)
    compressed_canonical = gzip.compress(canonical_bytes, mtime=0)
    (out / "synthetic_settlement_board.json.gz").write_bytes(compressed_canonical)
    fixture = {"SYNTHETIC_RESEARCH_ONLY": True,
        "quote_contract": quote_resolver.contract, "quote_contract_id": quote_resolver.contract_id,
        "synthetic_settlement_board": {"path": "synthetic_settlement_board.json.gz",
            "sha256": sha256(compressed_canonical).hexdigest(),
            "uncompressed_sha256": sha256(canonical_bytes).hexdigest()},
        "base_pack": pack,
        "settlement_pack": settlement, "settlement_board_subset": {
            "as_of": settle_board["as_of"], "research_fixture": settle_board["research_fixture"],
            "buy": [{"ticker": r["ticker"]} for r in settle_board["buy"]],
            "more_actionable": [{"ticker": r["ticker"]} for r in settle_board["more_actionable"]],
            "forming": [{"ticker": r["ticker"]} for r in settle_board["forming"]]},
        "events": {k: json.loads(store.objects[k]) for k in event_keys},
        "ledger": ledger, "reconciliation": receipt}
    (out / "integration_fixture.json").write_bytes(encoded(fixture) + b"\n")
    results["roundtrip"] = {"ledger": ledger, "reconciliation": receipt,
        "intraday_pack_id": pack["pack_id"], "settlement_pack_id": settlement["pack_id"],
        "canonical_source_board_sha256": board_id["artifact_sha256"]}
    results["status"] = "PASS"
    results["counts"] = {"prototype_checks": len(checks), "hostile_checks": len(hostile)}
    results["limitations"] = [
        "Research wrappers/injected transport are not a production patch or deployed proof.",
        "Quotes and October 12 settlement fixture are synthetic; no natural live event was generated.",
        "The pinned Yahoo/Tencent adapters do not establish adjustment-basis receipts; natural provider input is unqualified by this prototype.",
        "The source contract defines synthetic unadjusted units; it is not certification of natural vendor prices.",
        "Only three actual names were gate-probed; the 180-name pass proves frozen-field projection only.",
        "Prices and frozen source fields are from the study pin, not original publication-time receipts.",
        "Close/fill economics remain unresolved; no return, fill feasibility or alpha claim is made.",
        "A changed generation colliding with the same daily key is refused for existing-owner adjudication.",
        "The 60-second future-clock allowance is an explicit laboratory parameter requiring production ratification."]
    loaded = {}
    for name, module in sorted(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if path and Path(path).is_relative_to(source) and path.endswith(".py"):
            rel = str(Path(path).relative_to(source))
            loaded[rel] = sha256(Path(path).read_bytes()).hexdigest()
    results["source_manifest"] = provenance
    results["loaded_source_hashes"] = loaded
    results["runtime"] = {"python": sys.version.split()[0], "pandas": pd.__version__}
    results["laboratory_code"] = {name: {"sha256": sha256(
        (Path(__file__).resolve().parent / name).read_bytes()).hexdigest(),
        "bytes": (Path(__file__).resolve().parent / name).stat().st_size}
        for name in ("contract_prototype.py", "run_lab.py", "repair_checks.py", "pinned_quote_adapter.py")}
    results["executed_at_utc"] = datetime.now(UTC).isoformat()
    (out / "integration_results.json").write_bytes(json.dumps(results, ensure_ascii=False,
        sort_keys=True, indent=2, allow_nan=False).encode() + b"\n")
    (out / "execution.log").write_text(log.getvalue())
    print(json.dumps({"status": results["status"], "counts": results["counts"],
        "real_probe": {"tickers": selected, "gate_calls": pack["meta"]["gate_calls"],
                       "edges_checked": pack["meta"]["edges_checked"]},
        "spool_objects": receipt["spool_objects"], "ledger_rows": len(ledger),
        "outputs": {p.name: {"bytes": p.stat().st_size, "sha256": sha256(p.read_bytes()).hexdigest()}
                    for p in out.iterdir() if p.is_file()}}))


if __name__ == "__main__":
    # Refuse network even if an imported helper accidentally attempts it. The
    # experiment's Git object reads use subprocess and its fake R2 uses memory.
    def no_network(*args, **kwargs):
        raise RuntimeError("network disabled in the offline integration laboratory")
    with patch.object(socket.socket, "connect", no_network), \
         patch.object(socket, "create_connection", no_network):
        main()
