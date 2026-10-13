from __future__ import annotations

# Structural diagnostic of undated units (no barrier, state, E or bound computed).
import collections
import importlib.util
import json

P = "/Volumes/Mastermind/agent-workspaces/claude/14851c4656838a3b/quant-staging-20261008/Q19/research/quant_assessment_2026_10/Q19_censoring_path_ambiguity/evaluate.py"
spec = importlib.util.spec_from_file_location("q19eval", P)
ev = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ev)

blobs = {rel: ev.read_pinned(rel, nb, dg) for rel, nb, dg in ev.PINS}
episodes = ev.load_episodes(blobs.pop("options_signal_episode/episodes.jsonl"))
blobs.pop("options_signal_episode/checkpoint.json")
rows = ev.load_rows([blobs[k] for k in sorted(blobs)])
blobs.clear()
out = {}
for horizon, finer in (("10d", ("eod", "1d", "3d", "5d")), ("5d", ("eod", "1d", "3d"))):
    units = ev.build_units(episodes, rows, horizon, finer)["units"]
    und = [u for u in units if not u["date"]]
    out[horizon] = {
        "undated_units": len(und),
        "undated_by_class": dict(collections.Counter(u["censoring"] for u in und)),
        "undated_episodes": sum(u["n_episodes"] for u in und),
        "undated_observed_episodes": sum(u["n_observed_episodes"] for u in und),
        "undated_key_kinds": dict(collections.Counter(
            "no_session_row" if u["key"][0] == "no_session_row" else
            ("entry_time_missing" if u["key"][1] is None else "other") for u in und)),
    }
print(json.dumps(out, indent=1, sort_keys=True))
