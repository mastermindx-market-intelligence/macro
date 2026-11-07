"""Shared append-time discipline for the desks' theses.jsonl ledgers. NEVER-RAISES.

WHY THIS EXISTS (2026-08-03 experiments audit)
----------------------------------------------
Desk thesis ids were minted from the DATA date (`{asof}-{i}`), not run identity. A stale
detector state re-briefed on later run days reuses the same `state_asof`, so every re-run
collided with the prior run's ids: data/ai_desk/theses.jsonl held 124 rows under 51 ids
(73 silently discarded by the scorers' last-wins dedupe, 68 of them past-due and never
graded — graded coverage 28%), and data/stock_desk/theses.jsonl held 606 rows under 259
ids with 35 graded ids re-appended under MUTATED lean/check_by. A falsifier whose
direction or horizon is rewritten after logging is not pre-registered; that mutation is
the direct cause of desk_placebo's pairing failure on stock_desk ("reconstructed 24
graded predicates but the track record has 72"), which caps its placebo coverage and
makes the desk unpromotable.

The two invariants this module enforces, at every desk:

  1. RUN-SCOPED IDS — `run_token(generated_at)` yields the full UTC second of the run
     (YYYYMMDDHHMMSS), so two runs over the same state_asof mint disjoint ids.
  2. IMMUTABLE ROWS — `reject_existing_ids()` refuses to append a row whose id is
     already in the ledger, LOUDLY (a GitHub annotation + log line): first write wins,
     a live row's lean/check_by can never be rewritten by a later append.

MIGRATION STORY for the already-collided ledgers: docs/DESK_LEDGER_ID_MIGRATION.md.
History is NOT rewritten — scored rows stay as-scored, the scorers keep last-wins
dedupe for the legacy window, and coverage heals forward from the deploy date.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def run_token(generated_at) -> str:
    """The run's identity for id-minting: the leading 14 digits (YYYYMMDDHHMMSS, UTC)
    of the brief's `generated_at` ISO timestamp. Full-second precision — a token built
    from the time-of-day alone (policy_intent's original HHMMSS) still collides when
    two different run DAYS share a stale state_asof and happen to fire at the same
    wall-clock second. Returns "" when the timestamp is unusable (caller keeps the
    legacy id shape rather than minting a malformed one)."""
    digits = "".join(c for c in str(generated_at or "") if c.isdigit())[:14]
    return digits if len(digits) == 14 else ""


def existing_ids(ledger_path) -> set:
    """All ids already present in an append-only jsonl ledger. Unreadable/absent file
    -> empty set (cold start); unparseable lines are skipped, never fatal."""
    out: set = set()
    try:
        p = Path(ledger_path)
        if not p.exists():
            return out
        for line in p.read_text().splitlines():
            try:
                rid = json.loads(line).get("id")
                if rid:
                    out.add(rid)
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
    return out


def reject_existing_ids(ledger_path, rows: list, desk: str) -> list:
    """Filter `rows` down to those whose id is NOT already in the ledger — the
    append-time immutability gate. Logged theses are pre-registered predictions: an
    append that reuses a live id would rewrite that row's lean/check_by under the
    scorers' dedupe, so it is refused and announced (a rejection here means id minting
    regressed, or two runs shared a wall-clock second — either way a real defect
    signal, not noise). First write wins; never raises."""
    if not rows:
        return rows
    seen = existing_ids(ledger_path)
    if not seen:
        return rows
    kept = []
    for r in rows:
        rid = r.get("id")
        if rid in seen:
            # Annotation must START the line via bare print (never a logger — the
            # prefixing log format makes GitHub drop it silently); flush because CI
            # stdout is block-buffered when piped.
            print(f"::warning title=desk-ledger-id-collision::{desk}: refused to "
                  f"re-append thesis id {rid} — the logged row is immutable "
                  f"(first write wins; a re-run must mint a fresh run-scoped id)",
                  flush=True)
            log.warning("%s: ledger append refused for existing id %s (immutable row)",
                        desk, rid)
        else:
            kept.append(r)
    return kept


# --------------------------------------------------------------------------- #
# placebo-null disclosure — the measured no-skill base rate, printed BESIDE the
# hit-rate wherever a track record narrates itself. `hit` is a NOT-falsified
# endpoint whose null sits far above one-half (engine.desk_placebo); a bare
# "hit-rate 0.889" reads as skill and feeds back into the conviction-calibrating
# LLM prompt uncorrected.
# --------------------------------------------------------------------------- #
def placebo_lines(root, slug: str) -> tuple[str, str]:
    """(english, chinese) sentences for the desk's calibration note. Reads the desk's
    row out of data/calibration/summary.json under `root` (written by
    engine.calibration_hub — so the number is the PREVIOUS hub build's; nulls move
    slowly and this is a disclosure, not a gate). When no measured null exists the
    honest absence is printed instead — never a silent omission. Never raises."""
    nh = nd = None
    try:
        s = json.loads((Path(root) / "data" / "calibration" / "summary.json").read_text())
        for d in s.get("desks") or []:
            if d.get("slug") == slug:
                if d.get("placebo_available"):
                    nh, nd = d.get("null_hit_rate"), d.get("null_dir_rate")
                break
    except Exception:  # noqa: BLE001
        pass
    if nh is None:
        return ("The no-skill base rate for these exact conditions is not yet measured "
                "— read the hit-rate as unbenchmarked, not as evidence of skill.",
                "这些条件下的无技能基线尚未测得——命中率暂无基准，不应视作能力证据。")
    dir_en = f" (directional accuracy near {nd})" if nd is not None else ""
    dir_zh = f"（方向准确率约 {nd}）" if nd is not None else ""
    return (f"Chance alone would land a hit-rate near {nh}{dir_en} on these exact "
            f"conditions — judge the numbers above against that bar, not one-half.",
            f"同样条件下，无技能判断凭机会即可达到约 {nh} 的命中率{dir_zh}"
            f"——上述数字应与该基线比较，而非 0.5。")


# Selected desk runs extend Master Brain's existing reply-cache directory.
# Native admission, account choice, usage and close remain with the shared
# application factory/client. Consumer publication still targets its own files.
class _DeskFabricStop(BaseException):
    pass


def _fabric_cache():
    from engine import catalyst_tone
    return catalyst_tone


def _fabric_clone(value):
    cache = _fabric_cache()
    return cache._cache_decode(cache._cache_json(value))


def _fabric_path(key, root):
    from pathlib import Path
    allowed = {"ai-desk", "policy-intent", "regime-snap",
               "thematic-us", "thematic-china", "thematic-hk", "thematic-canada"}
    if key not in allowed:
        raise ValueError("desk_fabric_consumer_invalid")
    return Path(root) / "data/master_brain/reply_cache" / ("fabric-delegated-" + key + ".json")


def _fabric_root(root):
    from pathlib import Path
    from lib import config
    return (Path(root) if root is not None else Path(config.ROOT)).resolve(strict=True)


def fabric_selected(cfg):
    from engine import llm_auth
    return llm_auth.application_mode_id(cfg) is not None


def _fabric_slot_source(key, root, entry, slot):
    return {"consumer": key, "root": str(root), "run": entry["run_id"], "slot": slot}


def _fabric_waiting(entry):
    return (entry["state"] in ("pending", "held")
            or entry["publication_requested"]
            and (entry["publication"] is None or entry["publication"]["state"] != "complete"))


def _fabric_validate_plan(key, root, entry):
    cache = _fabric_cache()
    plan = entry["publication"]
    if plan is None:
        return
    if (type(plan) is not dict or set(plan) != {"state", "effects", "digest"}
            or plan["state"] not in ("pending", "complete")
            or type(plan["effects"]) is not list
            or any(type(s) is not dict or "effect" not in s for s in plan["effects"])
            or plan["digest"] != cache._cache_hash([s["effect"] for s in plan["effects"]])
            or entry["result"] is None or not entry["publication_requested"]):
        raise ValueError("desk_fabric_publication_invalid")
    result, context = entry["result"], entry["input"]["context"]
    if key == "regime-snap":
        expected = [("jsonl", context["journal_path"])]
    elif key.startswith("thematic-"):
        expected = [("jsonl", "data/thematic_desk/theses.jsonl"),
                    ("handoff", "thematic-qledger"),
                    ("json", "site/allocationdata/ai_desk_" + key[9:] + ".json")]
    else:
        slug = {"ai-desk": "ai_desk", "policy-intent": "policy_intent"}[key]
        expected = [("jsonl", "data/" + slug + "/theses.jsonl"),
                    ("json", "data/regime/" + slug + ".json")]
        if context["site_present"]:
            expected.append(("json", "site/" + slug + ".json"))
    if len(plan["effects"]) != len(expected):
        raise ValueError("desk_fabric_publication_shape")
    unfinished, previous_rows = False, None
    for step, (kind, target) in zip(plan["effects"], expected):
        if (set(step) != {"effect", "state", "receipt"}
                or step["state"] not in ("ready", "pending", "complete")
                or step["state"] in ("ready", "pending") and step["receipt"] is not None
                or step["state"] == "complete" and type(step["receipt"]) is not dict
                or unfinished and step["state"] != "ready"):
            raise ValueError("desk_fabric_publication_order")
        unfinished |= step["state"] != "complete"
        effect, receipt = step["effect"], step["receipt"]
        if type(effect) is not dict or effect.get("kind") != kind:
            raise ValueError("desk_fabric_effect_invalid")
        if kind == "json":
            public = ({k: v for k, v in result.items() if k != "raw_text"}
                      if key in ("ai-desk", "policy-intent") and target.startswith("site/") else result)
            if (set(effect) != {"kind", "path", "value"} or effect["path"] != target
                    or effect["value"] != public
                    or receipt is not None and receipt != {"digest": cache._cache_hash(public)}):
                raise ValueError("desk_fabric_projection_invalid")
        elif kind == "jsonl":
            if (set(effect) != {"kind", "path", "rows", "key", "guard", "keep_first", "eligible"}
                    or effect["path"] != target or type(effect["rows"]) is not list
                    or effect["key"] != ("date" if key == "regime-snap" else "id")
                    or effect["guard"] != ("nightly" if key in ("regime-snap", "policy-intent") else None)
                    or effect["keep_first"] is not (key == "regime-snap")
                    or type(effect["eligible"]) is not bool
                    or effect["guard"] is None and not effect["eligible"]):
                raise ValueError("desk_fabric_ledger_invalid")
            rows = effect["rows"]
            if not effect["eligible"]:
                if rows:
                    raise ValueError("desk_fabric_gated_rows")
            elif key == "regime-snap":
                if rows != [{"date": context["day"], "generated_at": result["generated_at"],
                        "lean": result["lean"], "confidence": result["confidence"],
                        "snap": context["bundle"]["snap"],
                        "headlines_n": len(context["bundle"]["recent_headlines"])}]:
                    raise ValueError("desk_fabric_journal_changed")
            else:
                theses = result["theses"]
                if len(rows) != len(theses) or len({r.get("id") for r in rows}) != len(rows):
                    raise ValueError("desk_fabric_theses_changed")
                for row, thesis in zip(rows, theses):
                    if key.startswith("thematic-"):
                        fixed = {**thesis, "market": result["market"],
                                 "logged_at": result["generated_at"], "state_asof": result["state_asof"]}
                        variable = {"entry_levels"}
                    else:
                        fields = ("id", "subject", "lean", "conviction", "horizon_d", "falsifier", "check_by")
                        fixed = {k: thesis[k] for k in fields}
                        fixed.update(logged_at=result["generated_at"], state_asof=result["state_asof"],
                                     status="open", scored_at=None, outcome=None, realized=None)
                        if key == "policy-intent":
                            fixed["actor"] = thesis.get("actor")
                        variable = {"entry_levels", "regime"}
                    if (type(row) is not dict or set(row) != set(fixed) | variable
                            or any(row[k] != v for k, v in fixed.items())
                            or type(row["entry_levels"]) is not dict
                            or any(type(v) not in (int, float) for v in row["entry_levels"].values())):
                        raise ValueError("desk_fabric_ledger_projection")
            if receipt is not None:
                if (set(receipt) != {"disposition", "written"}
                        or receipt["disposition"] not in ("written", "empty", "gated_out", "existing_first")
                        or receipt["disposition"] == "written" and (not rows or receipt["written"] != rows)
                        or receipt["disposition"] != "written" and receipt["written"] != []
                        or receipt["disposition"] == "empty" and rows
                        or receipt["disposition"] == "gated_out" and effect["guard"] is None
                        or not effect["eligible"] and receipt["disposition"] != "gated_out"
                        or receipt["disposition"] == "existing_first" and not effect["keep_first"]):
                    raise ValueError("desk_fabric_ledger_receipt")
                previous_rows = receipt["written"]
        else:
            if set(effect) != {"kind", "name"} or effect["name"] != target:
                raise ValueError("desk_fabric_handoff_invalid")
            if receipt is not None and (set(receipt) != {"invoked", "returned", "materialization_proven"}
                    or receipt["materialization_proven"] is not False
                    or receipt["invoked"] is not (bool(previous_rows) and key == "thematic-us")
                    or not receipt["invoked"] and receipt["returned"] is not None):
                raise ValueError("desk_fabric_handoff_receipt")
    if (plan["state"] == "complete") != all(s["state"] == "complete" for s in plan["effects"]):
        raise ValueError("desk_fabric_publication_completion")


def _fabric_load(key, root):
    import re
    cache = _fabric_cache()
    value = cache._cache_read(_fabric_path(key, root))
    if value is None:
        return {"schema": "macro.delegated_brain_fabric.v1",
                "consumer": key, "root": str(root), "entries": []}
    if (type(value) is not dict or set(value) != {"schema", "consumer", "root", "entries"}
            or value["schema"] != "macro.delegated_brain_fabric.v1"
            or value["consumer"] != key or value["root"] != str(root)
            or type(value["entries"]) is not list or len(value["entries"]) > 64):
        raise ValueError("desk_fabric_owner_invalid")
    ids, inputs = set(), set()
    for entry in value["entries"]:
        fields = {"run_id", "input", "input_digest", "created_at", "state", "steps",
                  "result", "result_digest", "reason", "publication_requested", "publication"}
        if (type(entry) is not dict or set(entry) != fields
                or type(entry["run_id"]) is not str
                or re.fullmatch(r"desk:[0-9a-f]{32}", entry["run_id"]) is None
                or entry["run_id"] in ids or entry["input_digest"] in inputs
                or entry["input_digest"] != cache._cache_hash(entry["input"])
                or entry["state"] not in ("pending", "held", "ready", "complete", "failed")
                or type(entry["publication_requested"]) is not bool
                or type(entry["created_at"]) is not str
                or type(entry["steps"]) is not dict or not 1 <= len(entry["steps"]) <= 6
                or type(entry["input"]) is not dict
                or type(entry["input"].get("systems")) is not dict
                or set(entry["steps"]) != set(entry["input"]["systems"])
                or entry["result"] is not None and (type(entry["result"]) is not dict
                    or entry["result_digest"] != cache._cache_hash(entry["result"]))
                or entry["result"] is None and entry["result_digest"] is not None):
            raise ValueError("desk_fabric_entry_invalid")
        ids.add(entry["run_id"])
        inputs.add(entry["input_digest"])
        data = entry["input"]
        if (type(data) is not dict
                or set(data) != {"state", "cfg", "systems", "context", "mode_id", "inspection"}
                or type(data["cfg"]) is not dict or type(data["systems"]) is not dict
                or type(data["context"]) is not dict
                or data["systems"] != _fabric_module(key)._fabric_systems()
                or type(data["cfg"].get("max_tokens")) is not int
                or not 1 <= data["cfg"]["max_tokens"] <= 32768
                or len(set(data["systems"].values())) != len(data["systems"])):
            raise ValueError("desk_fabric_input_invalid")
        unclosed = False
        final_steps = 0
        for name, step in entry["steps"].items():
            if (type(step) is not dict or set(step) != {"system", "user", "cache"}
                    or step["system"] != data["systems"][name]
                    or step["user"] is not None and type(step["user"]) is not str):
                raise ValueError("desk_fabric_step_invalid")
            state = cache._fabric_cache_value(step["cache"], _fabric_slot_source(key, root, entry, name))
            if len(state["entries"]) > 1 or state["entries"] and step["user"] is None:
                raise ValueError("desk_fabric_step_repeated")
            for row in state["entries"]:
                if row["inspection"] != data["inspection"] or row["mode_id"] != data["mode_id"]:
                    raise ValueError("desk_fabric_step_identity_changed")
                commitment = {"system": step["system"], "user": step["user"],
                    "max_tokens": data["cfg"]["max_tokens"],
                    "context": {"run_id": entry["run_id"], "slot": name,
                                "input_digest": entry["input_digest"]}}
                if row.get("schema") == cache._AUTO_CACHE_ENTRY:
                    commitment.update(application_inspection=data["inspection"],
                                      application_mode=data["mode_id"])
                    original, request = cache._cache_auto_request(row["operation_id"],
                        step["system"], step["user"], data["cfg"]["max_tokens"])
                    if row["request"] != request:
                        raise ValueError("desk_fabric_request_changed")
                    cache._cache_auto_validate(row, original)
                if row["input_digest"] != cache._cache_hash(commitment):
                    raise ValueError("desk_fabric_request_commitment")
                unclosed |= row["state"] != "terminal"
                if row["result"] is not None and row["result"] != {"text": row["text"]}:
                    raise ValueError("desk_fabric_step_result")
                final_steps += name in ("single", "adjudicator")
        if (unclosed and entry["state"] not in ("pending", "held")
                or final_steps > 1
                or entry["state"] in ("ready", "complete") and entry["result"] is None
                or entry["state"] == "failed" and entry["publication_requested"]):
            raise ValueError("desk_fabric_completion_invalid")
        if entry["state"] in ("ready", "complete", "failed"):
            _fabric_validate_output(key, entry)
        if (entry["state"] == "complete") != (entry["publication"] is not None
                and entry["publication"]["state"] == "complete"):
            raise ValueError("desk_fabric_entry_publication_state")
        _fabric_validate_plan(key, root, entry)
    if sum(_fabric_waiting(entry) for entry in value["entries"]) > 1:
        raise ValueError("desk_fabric_original_overlap")
    return value


def _fabric_save(key, root, value):
    _fabric_cache()._cache_save(_fabric_path(key, root), value)
    _fabric_load(key, root)


def fabric_held(reason="application_fabric_original_held"):
    return {"is_context_only": True, "theses": [], "model": None, "served_by": None,
            "raw_text": None, "confidence": "low", "regime_context": None,
            "generated_at": None, "degraded_reason": reason}


def fabric_pending(key, root):
    import os
    root = _fabric_root(root)
    path = _fabric_path(key, root)
    if not os.path.lexists(path):
        return None
    try:
        with _fabric_cache()._cache_lock(path, root):
            state = _fabric_load(key, root)
            if any(_fabric_waiting(entry) for entry in state["entries"]):
                return fabric_held()
    except Exception:
        return fabric_held("application_fabric_owner_refused")
    return None


def fabric_snapshot(key, root):
    root = _fabric_root(root)
    cache = _fabric_cache()
    with cache._cache_lock(_fabric_path(key, root), root):
        return cache._cache_hash(_fabric_load(key, root))


class _FabricDeskCall:
    def __init__(self, key, root, entry):
        import threading
        self.key, self.root, self.entry = key, root, _fabric_clone(entry)
        self.local_mutex = threading.RLock()

    def _read(self):
        state = _fabric_load(self.key, self.root)
        entry = next(e for e in state["entries"] if e["run_id"] == self.entry["run_id"])
        if entry["input"] != self.entry["input"] or entry["state"] != "pending":
            raise _DeskFabricStop("application_fabric_original_changed")
        return state, entry

    def __call__(self, system, user, cfg, served=None):
        # The incumbent compatibility helper may retry TypeError. An unexpected
        # selected callback error is a hold, never permission for that retry.
        try:
            return self._call(system, user, cfg, served)
        except TypeError as exc:
            raise _DeskFabricStop("application_fabric_callback_held") from exc

    def _call(self, system, user, cfg, served):
        cache = _fabric_cache()
        path = _fabric_path(self.key, self.root)
        names = [name for name, text in self.entry["input"]["systems"].items() if text == system]
        if len(names) != 1 or type(user) is not str:
            raise _DeskFabricStop("application_fabric_step_invalid")
        name = names[0]
        with self.local_mutex, cache._cache_lock(path, self.root):
            state, entry = self._read()
            step = entry["steps"][name]
            if step["user"] is not None and step["user"] != user:
                raise _DeskFabricStop("application_fabric_step_changed")
            if not step["cache"]["entries"]:
                if any(row["state"] == "held" for other in entry["steps"].values()
                       for row in other["cache"]["entries"]):
                    raise _DeskFabricStop("application_fabric_original_held")
                step["user"] = user
                _fabric_save(self.key, self.root, state)
        def load_cache():
            _, current = self._read()
            return current["steps"][name]["cache"]
        def store_cache(value):
            state, current = self._read()
            if (len(value["entries"]) > 1
                    or any(row["inspection"] != current["input"]["inspection"]
                           or row["mode_id"] != current["input"]["mode_id"]
                           for row in value["entries"])):
                raise ValueError("desk_fabric_frozen_identity_changed")
            current["steps"][name]["cache"] = value
            _fabric_save(self.key, self.root, state)
        result = cache._fabric_cached_document(path=path, root=self.root,
            logical_source=_fabric_slot_source(self.key, self.root, self.entry, name),
            cfg=self.entry["input"]["cfg"], lane=self.key.split("-")[0] + "-desk"
                if self.key.startswith("thematic-") else
                {"ai-desk": "ai-desk", "policy-intent": "policy-desk",
                 "regime-snap": "regime-snap"}[self.key],
            system=system, user=user,
            input_context={"run_id": self.entry["run_id"], "slot": name,
                           "input_digest": self.entry["input_digest"]},
            validate=lambda text: {"text": text}, load_cache=load_cache,
            store_cache=store_cache, local_mutex=self.local_mutex)
        with self.local_mutex, cache._cache_lock(path, self.root):
            _, current = self._read()
            rows = current["steps"][name]["cache"]["entries"]
            if (result is None or not rows or rows[0]["state"] != "terminal"
                    or result["receipt"] is None):
                raise _DeskFabricStop("application_fabric_original_held")
            row = rows[0]
            text = result["result"]["text"] if result["result"] is not None else None
            if isinstance(served, dict) and text is not None:
                served.update(provider=row["receipt"]["provider"], model=row["receipt"]["served_model"])
            return _fabric_reply(name, text, result["error"])


def fabric_synthesize(key, root, state, cfg, systems, render, *,
                      publication_requested=False, context=None, generated_at=None):
    import os
    from datetime import datetime, timezone
    from pathlib import Path
    from engine import llm_auth, provider_production_modes
    from lib import config
    cache = _fabric_cache()
    root = _fabric_root(root)
    held = fabric_pending(key, root)
    if held is not None:
        return {"result": held, "run_id": None, "held": True}
    mode = llm_auth.application_mode_id(cfg)
    if mode is None:
        return None
    if root != Path(config.ROOT).resolve(strict=True):
        return {"result": fabric_held("application_fabric_price_owner_root_mismatch"),
                "run_id": None, "held": True}
    selected_cfg = _fabric_clone(cfg)
    selected_cfg.setdefault("max_tokens", 4000)
    selected_cfg.setdefault("workload_profile", "site_batch")
    selected_cfg["provider_order"] = ["fabric"]
    lane = ("thematic-desk" if key.startswith("thematic-") else
            {"ai-desk": "ai-desk", "policy-intent": "policy-desk", "regime-snap": "regime-snap"}[key])
    factory = provider_production_modes.make_application_fabric_factory(
        mode_id=mode, lane=lane, root=root,
        workload_cfg={**selected_cfg, "workload_profile": "site_batch"})
    inspection = factory.inspect(selected_cfg)
    request = _fabric_clone({"state": state, "cfg": selected_cfg, "systems": systems,
                             "context": context or {}, "mode_id": mode, "inspection": inspection})
    digest = cache._cache_hash(request)
    path = _fabric_path(key, root)
    with cache._cache_lock(path, root):
        owner = _fabric_load(key, root)
        if any(_fabric_waiting(e) for e in owner["entries"]):
            return {"result": fabric_held(), "run_id": None, "held": True}
        prior = next((e for e in owner["entries"] if e["input_digest"] == digest), None)
        if prior is not None:
            if publication_requested and prior["result"] is not None and not prior["publication_requested"]:
                prior["publication_requested"] = True
                _fabric_save(key, root, owner)
            return {"result": _fabric_clone(prior["result"]), "run_id": prior["run_id"], "held": False}
        if len(owner["entries"]) >= 64:
            raise ValueError("desk_fabric_owner_bound")
        created_at = generated_at or datetime.now(timezone.utc).isoformat()
        if key == "regime-snap" and created_at[:10] != request["context"]["day"]:
            raise ValueError("desk_fabric_day_changed")
        entry = {"run_id": "desk:" + os.urandom(16).hex(), "input": request, "input_digest": digest,
            "created_at": created_at, "state": "pending",
            "steps": {}, "result": None, "result_digest": None, "reason": None,
            "publication_requested": bool(publication_requested), "publication": None}
        for name, system in systems.items():
            entry["steps"][name] = {"system": system, "user": None,
                "cache": cache._fabric_cache_value(None, _fabric_slot_source(key, root, entry, name))}
        owner["entries"].append(entry)
        _fabric_save(key, root, owner)
    caller = _FabricDeskCall(key, root, entry)
    result, failure = None, None
    try:
        result = render(_fabric_clone(request["state"]), _fabric_clone(request["cfg"]), caller,
                        {**_fabric_clone(request["context"]), "created_at": entry["created_at"]})
    except BaseException as exc:
        failure = exc
    try:
        with caller.local_mutex, cache._cache_lock(path, root):
            owner = _fabric_load(key, root)
            current = next(e for e in owner["entries"] if e["run_id"] == entry["run_id"])
            if current["state"] != "pending" or current["input"] != request:
                raise ValueError("desk_fabric_original_changed")
            rows = [row for step in current["steps"].values() for row in step["cache"]["entries"]]
            unknown = (failure is not None or not rows
                       or any(row["state"] != "terminal" for row in rows))
            if not unknown and type(result) is dict:
                result = _fabric_normalize(current, result)
                current.update(state="ready", result=result, result_digest=cache._cache_hash(result))
            elif not unknown and result is None:
                current.update(state="failed", publication_requested=False, reason="no_consumer_result")
            else:
                current.update(state="held", reason="application_fabric_original_held")
            _fabric_save(key, root, owner)
    except BaseException:
        if failure is not None and not isinstance(failure, _DeskFabricStop):
            raise failure
        if failure is None:
            raise
        return {"result": fabric_held(), "run_id": entry["run_id"], "held": True}
    if failure is not None and not isinstance(failure, _DeskFabricStop):
        raise failure
    if current["state"] == "held":
        return {"result": fabric_held(), "run_id": current["run_id"], "held": True}
    return {"result": _fabric_clone(current["result"]), "run_id": current["run_id"], "held": False}


def _fabric_rows(path, key):
    from engine import master_brain
    cache = _fabric_cache()
    raw, file_identity = master_brain._mb_auto_read_bytes(path)
    values = {}
    if raw is None:
        return values, raw, file_identity
    if raw and not raw.endswith(b"\n"):
        raise ValueError("desk_fabric_partial_ledger")
    for line in raw.splitlines():
        row = cache._cache_decode(line)
        if type(row) is not dict:
            raise ValueError("desk_fabric_ledger_invalid")
        identity = row.get(key)
        if key == "date":
            identity = identity or str(row.get("generated_at") or "")[:10]
        if type(identity) is not str or not identity:
            raise ValueError("desk_fabric_ledger_identity")
        # Historical desk ids collided before run-scoped identity. Membership
        # checks must not rewrite or reject that accepted legacy history.
        values.setdefault(identity, row)
    return values, raw, file_identity


def fabric_publish(key, root, run_id, prepare, *, handoff=None, guard=None):
    import os
    from engine import master_brain
    cache = _fabric_cache()
    root = _fabric_root(root)
    path = _fabric_path(key, root)
    with cache._cache_lock(path, root):
        owner = _fabric_load(key, root)
        entry = next(e for e in owner["entries"] if e["run_id"] == run_id)
        if entry["publication"] is not None:
            if entry["publication"]["state"] == "complete":
                return _fabric_clone(entry["result"])
            return fabric_held()
        if entry["state"] != "ready" or not entry["publication_requested"]:
            return fabric_held()
        effects = _fabric_clone(prepare(_fabric_clone(entry["result"]), _fabric_clone(entry["input"]["context"])))
        plan = {"state": "pending", "digest": cache._cache_hash(effects),
                "effects": [{"effect": effect, "state": "ready", "receipt": None} for effect in effects]}
        entry["publication"] = plan
        if not effects:
            plan["state"] = "complete"
            entry["state"] = "complete"
            _fabric_save(key, root, owner)
            return _fabric_clone(entry["result"])
        _fabric_save(key, root, owner)
        fresh = None
        try:
            for step in plan["effects"]:
                effect = step["effect"]
                step["state"] = "pending"
                _fabric_save(key, root, owner)
                if effect["kind"] == "jsonl":
                    if not effect["eligible"] or (effect["guard"] is not None
                            and (guard is None or not guard(effect["guard"]))):
                        receipt = {"disposition": "gated_out", "written": []}
                        fresh = []
                    else:
                        target = master_brain._mb_auto_safe_path(root, effect["path"], create=True)
                        # Thematic's regions share this same family ledger lock.
                        with _fabric_ledger_lock(target, root):
                            existing, original_raw, original_identity = _fabric_rows(target, effect["key"])
                            rows = effect["rows"]
                            overlap = [r for r in rows if r[effect["key"]] in existing]
                            if overlap and not effect["keep_first"]:
                                raise ValueError("desk_fabric_ledger_collision")
                            written = [r for r in rows if r[effect["key"]] not in existing]
                            if written:
                                flags = os.O_APPEND | os.O_WRONLY | os.O_NOFOLLOW
                                if original_identity is None:
                                    flags |= os.O_CREAT | os.O_EXCL
                                payload = b"".join(cache._cache_json(row) + b"\n" for row in written)
                                fd = os.open(target, flags, 0o600)
                                with os.fdopen(fd, "ab") as out:
                                    info = os.fstat(out.fileno())
                                    if original_identity is not None and (info.st_dev, info.st_ino, info.st_size) != original_identity:
                                        raise ValueError("desk_fabric_ledger_compare_failed")
                                    out.write(payload)
                                    out.flush()
                                    os.fsync(out.fileno())
                                cache._cache_sync_directory(target.parent)
                                actual, actual_raw, actual_identity = _fabric_rows(target, effect["key"])
                                if (actual_identity[:2] != (info.st_dev, info.st_ino)
                                        or actual_raw != (original_raw or b"") + payload
                                        or any(actual.get(r[effect["key"]]) != r for r in written)):
                                    raise ValueError("desk_fabric_ledger_readback")
                            fresh = _fabric_clone(written)
                            receipt = {"disposition": ("written" if written else
                                "existing_first" if rows else "empty"),
                                       "written": fresh}
                elif effect["kind"] == "handoff":
                    if fresh is None or handoff is None:
                        raise ValueError("desk_fabric_fresh_handoff_missing")
                    if fresh and key == "thematic-us":
                        returned = handoff(_fabric_clone(fresh))
                        receipt = {"invoked": True, "returned": returned, "materialization_proven": False}
                    else:
                        receipt = {"invoked": False, "returned": None, "materialization_proven": False}
                else:
                    target = master_brain._mb_auto_safe_path(root, effect["path"], create=True)
                    master_brain._mb_auto_read_bytes(target, 4 * 1024 * 1024)
                    cache._cache_save(target, effect["value"])
                    receipt = {"digest": cache._cache_hash(effect["value"])}
                step.update(state="complete", receipt=receipt)
                if all(s["state"] == "complete" for s in plan["effects"]):
                    plan["state"] = "complete"
                    entry["state"] = "complete"
                _fabric_save(key, root, owner)
            return _fabric_clone(entry["result"])
        except Exception:
            return fabric_held("application_fabric_publication_held")


def fabric_legacy_publish(key, root, snapshot, cfg, publish):
    root = _fabric_root(root)
    cache = _fabric_cache()
    with cache._cache_lock(_fabric_path(key, root), root):
        owner = _fabric_load(key, root)
        if fabric_selected(cfg) or cache._cache_hash(owner) != snapshot:
            return False
        publish()
        return True

def _fabric_module(key):
    from importlib import import_module
    name = ("thematic_desk" if key.startswith("thematic-") else
            {"ai-desk": "ai_desk", "policy-intent": "policy_intent_desk",
             "regime-snap": "regime_snap_veto"}[key])
    return import_module("engine." + name)


def _fabric_reply(name, text, error):
    if name.startswith("panel:") and text is not None:
        parsed = _fabric_cache()._extract_json(text)
        if (type(parsed) is not dict
                or "theses" in parsed and type(parsed["theses"]) is not list):
            return None, "panel_response_invalid"
    return text, error


def _fabric_normalize(entry, result):
    result = _fabric_clone(result)
    result["generated_at"] = entry["created_at"]
    for thesis in result.get("theses") or []:
        thesis["id"] = str(thesis["id"]) + "-" + entry["run_id"].split(":")[1]
    authors = [row for name in ("single", "adjudicator")
        for row in entry["steps"].get(name, {}).get("cache", {}).get("entries", [])
        if row["result"] is not None]
    result["model"] = authors[0]["receipt"]["served_model"] if len(authors) == 1 else None
    result["served_by"] = authors[0]["receipt"]["provider"] if len(authors) == 1 else None
    return result


class _FabricDeskReplay:
    """Pure source validation of saved results; never binds a provider."""
    def __init__(self, entry):
        self.entry, self.used = entry, set()

    def __call__(self, system, user, cfg, served=None):
        names = [name for name, text in self.entry["input"]["systems"].items() if text == system]
        if len(names) != 1:
            raise ValueError("desk_fabric_replay_step")
        name = names[0]
        step = self.entry["steps"][name]
        rows = step["cache"]["entries"]
        if step["user"] != user or len(rows) != 1 or rows[0]["state"] != "terminal":
            raise ValueError("desk_fabric_replay_original")
        self.used.add(name)
        row = rows[0]
        text = row["result"]["text"] if row["result"] is not None else None
        if isinstance(served, dict) and text is not None:
            served.update(provider=row["receipt"]["provider"], model=row["receipt"]["served_model"])
        return _fabric_reply(name, text, row["error"])


def _fabric_validate_output(key, entry):
    from datetime import datetime
    data, context = entry["input"], entry["input"]["context"]
    datetime.fromisoformat(entry["created_at"])
    if key == "regime-snap":
        if (set(context) != {"day", "bundle", "journal_path"}
                or context["day"] != entry["created_at"][:10]
                or type(context["journal_path"]) is not str
                or not context["journal_path"].endswith("/regime_snap/veto_log.jsonl")
                or Path(context["journal_path"]).is_absolute()
                or ".." in Path(context["journal_path"]).parts
                or context["bundle"] != data["state"]):
            raise ValueError("desk_fabric_context_invalid")
    elif (set(context) != ({"passport"} if key.startswith("thematic-") else {"passport", "site_present"})
            or not key.startswith("thematic-") and type(context["site_present"]) is not bool):
        raise ValueError("desk_fabric_context_invalid")
    replay = _FabricDeskReplay(entry)
    output = _fabric_module(key)._fabric_render(_fabric_clone(data["state"]), _fabric_clone(data["cfg"]),
                    replay, {**_fabric_clone(context), "created_at": entry["created_at"]})
    used = {name for name, step in entry["steps"].items() if step["cache"]["entries"]}
    if replay.used != used:
        raise ValueError("desk_fabric_result_source_changed")
    expected = None if output is None else _fabric_normalize(entry, output)
    if entry["result"] != expected:
        raise ValueError("desk_fabric_result_changed")


# Thread serialization complements the existing stable file lock. These short
# sections protect the incumbent shared family ledger, never provider calls.
from contextlib import contextmanager as _desk_contextmanager
import threading as _desk_threading
_FABRIC_LEDGER_MUTEX = _desk_threading.RLock()


@_desk_contextmanager
def _fabric_ledger_lock(path, root):
    with _FABRIC_LEDGER_MUTEX, _fabric_cache()._cache_lock(path, root):
        yield
