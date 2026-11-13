"""Explainable capacity planning from observed demand and incumbent quota reports.

Advice only: never purchases, changes routing, or treats route count as seats.
Catalog membership and routing classes come from the live router, not model lists.
"""
from __future__ import annotations

from collections import defaultdict
import math
import statistics
import time

from . import capacity_history, capacity_router


def analyze(snapshot, history=None, previous=None, *, now=None):
    now = time.time() if now is None else now
    if not snapshot.get("ok"):
        return {"ok": False, "message": "Live router telemetry is not available."}
    history = history or {}
    stale = now - snapshot.get("generated_at", 0) > 15
    routes = snapshot.get("routes", [])
    aliases = snapshot.get("aliases", {})
    demand = history.get("demand", []) if history.get("ok") else []
    basis = "durable_terminal_request_ledger"
    if not demand:
        basis = "retained_request_sample"
        grouped = {}
        for r in snapshot.get("recent", []):
            key = (r["provider"], r["served_model"] or r["requested_model"], r["lane"])
            item = grouped.setdefault(key, {"provider": key[0], "model": key[1], "lane": key[2],
                "requests": 0, "failed": 0, "input_tokens": 0, "output_tokens": 0,
                "input_tokens_known": 0, "output_tokens_known": 0})
            item["requests"] += 1
            item["failed"] += r["state"] != "completed"
            for k in ("input_tokens", "output_tokens"):
                item[k] += r["usage"].get(k) or 0
                item[k + "_known"] += r["usage"].get(k) is not None
        demand = list(grouped.values())
    by_model, by_pool = defaultdict(list), defaultdict(list)
    for row in demand:
        by_model[row["model"]].append(row)
        by_pool[row["provider"]].append(row)
    total_requests = sum(r["requests"] for r in demand)
    models = []
    for model in sorted({m for r in routes for m in r["models"]} | set(by_model)):
        rows = by_model[model]
        count = sum(r["requests"] for r in rows)
        pool_counts = defaultdict(int)
        for r in rows:
            pool_counts[r["provider"]] += r["requests"]
        configured = [r for r in routes if model in r["models"]]
        classes = [name for name, members in aliases.items() if model in members]
        alternatives = []
        for other in sorted({m for name in classes for m in aliases[name]} - {model}):
            eligible = [r for r in routes if other in r["models"]]
            if eligible:
                alternatives.append({"model": other, "classes": [c for c in classes if other in aliases[c]],
                    "pools": sorted({r["provider"] for r in eligible}),
                    "routes_outside_cooldown": sum(not r["cooling"] for r in eligible),
                    "basis": "configured_same_routing_class", "quota_available": None})
        output_known = sum(r.get("output_tokens_known", 0) for r in rows)
        models.append({"model": model, "requests": count,
            "share_pct": round(100*count/total_requests, 2) if total_requests else None,
            "output_tokens": sum(r.get("output_tokens", 0) for r in rows) if output_known else None,
            "output_known_requests": output_known,
            "failed": sum(r["failed"] for r in rows),
            "primary_pools": [{"pool": p, "requests": n} for p, n in sorted(pool_counts.items(), key=lambda x: (-x[1], x[0]))],
            "same_model_pools": [{"pool": p, "routes_outside_cooldown": sum(not r["cooling"] for r in configured if r["provider"]==p),
                                  "quota_available": None} for p in sorted({r["provider"] for r in configured})],
            "classes": classes, "alternatives": alternatives,
            "pool_concentration_pct": round(100*max(pool_counts.values())/count, 1) if count else None})
    models.sort(key=lambda r: (-r["requests"], r["model"]))
    pools, recommendations = [], []
    for pool in sorted({r["provider"] for r in routes} | set(by_pool)):
        selected = [r for r in routes if r["provider"] == pool]
        rows = by_pool[pool]
        requests = sum(r["requests"] for r in rows)
        failures = sum(r["failed"] for r in rows)
        cooling = sum(r["cooling"] for r in selected)
        pools.append({"pool": pool, "routes": len(selected), "subscriptions": None,
            "models": sorted({m for r in selected for m in r["models"]}), "requests": requests,
            "failed": failures, "failure_pct": round(100*failures/requests, 1) if requests else None,
            "cooling_routes": cooling, "active": sum(r["provider"] == pool for r in snapshot.get("active", [])),
            "quota_limit": None, "reset_at": None,
            "status": "cooling" if cooling else "observed", "limit_source": "not_reported"})
        if requests >= 20 and cooling:
            recommendations.append({"kind": "capacity_pressure", "target": pool, "severity": "warning",
                "confidence": "observed", "title": "Check constrained routes before adding subscriptions",
                "detail": f"{cooling} route(s) cooling while {requests} captured requests used this pool. A cooldown alone does not establish quota exhaustion.",
                "additional_subscriptions": None, "action": "Compare same-model pools and recorded quota/reset evidence."})
        if requests >= 30 and failures/requests >= .1:
            recommendations.append({"kind": "reliability", "target": pool, "severity": "warning", "confidence": "observed",
                "title": "Reliability investigation, not an automatic capacity purchase",
                "detail": f"{failures} of {requests} captured requests failed or were interrupted. Authentication, provider errors, and cancellation are not subscription shortages.",
                "additional_subscriptions": None, "action": "Inspect request attempts and error categories."})
    claude = snapshot.get("claude") or {}
    quota_fresh = bool(claude.get("reachable") and now - (claude.get("observed_at") or 0) <= 90 and not stale)
    accounts = claude.get("accounts", [])
    previous = previous or {}
    prior_accounts = {a["id"]: a for a in previous.get("accounts", [])}
    interval = (claude.get("observed_at") or 0) - (previous.get("observed_at") or 0)
    families = []
    for family in sorted({f for a in accounts for f in a.get("families", {})}):
        seats = [a for a in accounts if family in a.get("families", {})]
        lanes = [a["families"][family] for a in seats]
        budgets = [v["budget_weekly"] for v in lanes if v.get("budget_weekly") is not None]
        remaining = [v["remaining_weekly"] for v in lanes if v.get("remaining_weekly") is not None]
        resets = [v["weekly_resets_at"] for v in lanes if (v.get("weekly_resets_at") or 0) > now]
        sources = sorted({v.get("weekly_reset_source") for v in lanes if v.get("weekly_reset_source")})
        rate, sampled, unavailable = 0.0, 0, 0
        for a in seats:
            lane = a["families"][family]
            old = prior_accounts.get(a["id"], {}).get("families", {}).get(family, {})
            blocked = a.get("drain") or (a.get("cooldown_until") or 0)>now or (lane.get("cooldown_until") or 0)>now
            unavailable += bool(blocked)
            current_used, old_used = lane.get("used_weekly"), old.get("used_weekly")
            same_window = lane.get("weekly_resets_at") and old.get("weekly_resets_at") and abs(lane["weekly_resets_at"]-old["weekly_resets_at"]) <= 60
            if (3600 <= interval <= 86400 and same_window and current_used is not None and old_used is not None
                    and current_used >= old_used and lane.get("budget_weekly") == old.get("budget_weekly")):
                rate += (current_used-old_used)*3600/interval
                sampled += 1
        complete = bool(seats) and sampled == len(seats) and len(budgets) == len(seats) and len(remaining) == len(seats)
        budget = sum(budgets) if len(budgets) == len(seats) else None
        left = sum(remaining) if len(remaining) == len(seats) else None
        next_reset = min(resets) if resets else None
        pressure = round(100*(budget-left)/budget, 1) if budget and left is not None else None
        need_until_reset = rate*(next_reset-now)/3600 if complete and next_reset else None
        shortage = max(0, need_until_reset-left) if need_until_reset is not None and left is not None else None
        extra = None
        # A conditional scenario, not a forecast guarantee or a purchase. No
        # numeric recommendation from a short burst, a rolled window, stale data,
        # blocked accounts or incomplete budget reporting.
        if complete and quota_fresh and not unavailable and sources == ["provider"] and budgets and min(budgets)>0:
            extra = max(0, math.ceil(rate*168/(statistics.median(budgets)*.8))-len(seats))
        item = {"family": family, "observed_accounts": len(seats), "temporarily_unavailable_accounts": unavailable,
            "weekly_budget_units": budget, "weekly_remaining_units": left, "used_pct": pressure,
            "next_reset_at": next_reset, "reset_sources": sources, "units_per_hour": round(rate, 3) if complete else None,
            "sample_hours": round(interval/3600, 2) if complete else None,
            "projected_units_until_next_reset": round(need_until_reset, 2) if need_until_reset is not None else None,
            "shortfall_until_next_reset": round(shortage, 2) if shortage is not None else None,
            "suggested_additional_subscriptions": extra,
            "confidence": "conditional_observed_rate" if extra is not None else "insufficient_comparable_history",
            "unit": "gateway_weekly_budget_units_not_tokens", "fresh": quota_fresh,
            "shared_constraint": "These families share each account's five-hour window; family budgets must not be added as independent seats."}
        families.append(item)
        if extra and shortage and not stale:
            recommendations.append({"kind": "subscription_scenario", "target": family, "severity": "warning",
                "confidence": "conditional_observed_rate", "title": f"Evaluate {extra} additional equivalent subscription(s)",
                "detail": f"At the observed {round(rate, 2)} budget units/hour over {round(interval/3600, 1)} hours, a full-week scenario with 20% headroom exceeds installed family budget. This assumes unchanged workload and equivalent plans; shared five-hour limits still bind.",
                "additional_subscriptions": extra, "action": "Validate sustained demand, use compatible spare pools, and compare the next reset before purchasing."})
    pressure = [{"pool": key, **value, "basis": "router_local_input_rate_estimate_not_provider_balance"}
                for key, value in ((snapshot.get("overflow") or {}).get("keys") or {}).items()]
    if not recommendations:
        recommendations.append({"kind": "observe", "target": "fabric", "severity": "info", "confidence": "limited" if not quota_fresh else "observed",
            "title": "No evidence-backed subscription increase yet",
            "detail": "Demand ranking updates automatically with the live catalog. Numeric expansion scenarios require comparable quota samples spanning at least one hour; unreported provider limits remain unknown.",
            "additional_subscriptions": None, "action": "Review primary models, pool concentration, reset calendars and configured alternatives."})
    return {"ok": True, "generated_at": now, "source_at": snapshot["generated_at"], "stale": stale,
        "basis": basis, "captured_requests": total_requests, "model_count": len(models), "pool_count": len(pools),
        "models": models, "pools": pools, "quota_families": families, "pressure": pressure,
        "recommendations": recommendations, "coverage": history.get("coverage"),
        "method": {"adaptive": "Derived from current route catalog, routing classes and accumulated observations; no fixed model catalog.",
            "fallback": "Same routing-class membership is configured eligibility, not proof of equivalent quality, tools or available quota.",
            "expansion": "Conditional demand scenarios only. Never purchases or changes routing. Route identifiers are not subscription counts.",
            "learning": "Uses retained demand and comparable quota-window observations; resets and catalog changes invalidate incompatible samples."}}


def panel(minutes=1440, *, path=None, now=None):
    now = time.time() if now is None else now
    live = capacity_router.panel(120, path=path, now=now)
    # One-hour comparison avoids turning a short burst into a seat purchase.
    previous = capacity_history.previous_quota(path=capacity_history.database_path(path), before=now-3600)
    history = capacity_router.historical(minutes, path=path, now=now)
    return analyze(live, history, previous, now=now)
