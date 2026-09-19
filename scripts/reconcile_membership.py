"""Membership ↔ close-cache reconciler for the curated regional basket suites.

The regional basket suites (baskets_intl / _china / _canada / _hk) are curated
membership.json files whose members are validated against a REBUILDABLE close-matrix cache
(data/<region>_search/closes*.parquet). The seeders enforce that contract at seed time
(every emitted ticker is a live cache column — see scripts/seed_intl_baskets.py), and
tests/test_baskets_intl.py::test_seeder_only_emits_cache_validated_tickers enforces it on
live data. But the caches are rebuilt by their collectors, and a rebuild can drop a name
(delisting, acquisition, index churn) AFTER the membership was seeded — the member drifts
off-cache, its price history stops being computable, and the contract test breaks on main
(MONC.MI, fixed one-off in PR #854).

This reconciler closes that loop as part of the END-OF-COLLECT gate (scripts/collect.py):
for each suite it compares every members[].ticker against the cache columns and AUTO-PRUNES
off-cache member rows with a dated changelog entry (the exact remedy PR #854 applied by
hand), so the drift self-heals on the next collect instead of breaking the test suite.

Unlike the audit_* siblings this script WRITES the membership files — it is a reconciler,
not an audit — which is why it is not named audit_*. It still follows the suite's rules:
deterministic, idempotent (a second run on pruned data is a no-op), and it records its work
in data/quality/membership_reconcile.json for the run-over-run trend.

FAIL-LOUD GUARDS (PruneGuardError, the suite's membership file left untouched):
  - floor:  a prune that would leave a basket with fewer than `membership_min_present` (3)
            cache-present member rows means the basket itself is dying — that needs a human
            (re-curate or retire the basket), not a silent prune;
  - mass:   more than `membership_max_prune_pct` (20%) of a suite's member rows off-cache
            (and more than `membership_max_prune_abs` (3) names — a pct-only guard would
            misfire on a small suite) means the CACHE REBUILD is broken (truncated collect —
            the failure mode that made the THS seeder fabricate mass removals, macro#793),
            not genuine churn.
Guard thresholds are overridable via the config `quality:` block. A guarded suite refuses;
the other suites still reconcile, then the error propagates and aborts the collect run
exactly like the data-quality gate's >5% abort.

U.S. STRUCTURAL AUDIT: data/baskets remains human/PIT curated and is NEVER auto-mutated
here because the current S&P constituent snapshot cannot tell us the historical effective
date of an add/delete/GICS move. The same END-OF-COLLECT run nevertheless compares the
eleven us_sector_* active rosters against data/breadth/constituents.parquet and writes the
drift into membership_reconcile.json. Drift emits a GitHub warning and waits for an
evidence-backed dated membership edit; it does not prune/add/move a member automatically.

EXPLICIT NON-GOAL: data/baskets_china_ths is snapshot-driven with its own add/remove
lifecycle in its seeder and is not touched here.

Run:    python -m scripts.reconcile_membership [-v] [--dry-run]
Import: from scripts import reconcile_membership
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

import pandas as pd

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from lib import config  # noqa: E402

log = logging.getLogger("reconcile.membership")

# suite dir (under data/) -> (close-cache path under data/, cache label for changelog notes)
SUITES: list[tuple[str, str, str]] = [
    ("baskets_intl",   "intl_search/closes.parquet",    "intl_search"),
    ("baskets_china",  "china_search/closes.parquet",   "china_search"),
    ("baskets_canada", "canada_search/closes.parquet",  "canada_search"),
    ("baskets_hk",     "hk_search/closes_deep.parquet", "hk_search"),
]

# Existing U.S. structural sleeves: active membership must match the current
# S&P-500 constituent/sector owner. This map is structural classification only;
# it grants no authority to infer historical effective dates.
US_SECTOR_BASKETS: dict[str, str] = {
    "us_sector_tech": "Information Technology",
    "us_sector_financials": "Financials",
    "us_sector_health": "Health Care",
    "us_sector_discretionary": "Consumer Discretionary",
    "us_sector_comm": "Communication Services",
    "us_sector_industrials": "Industrials",
    "us_sector_staples": "Consumer Staples",
    "us_sector_energy": "Energy",
    "us_sector_utilities": "Utilities",
    "us_sector_realestate": "Real Estate",
    "us_sector_materials": "Materials",
}

_DEFAULTS = {
    "membership_min_present": 3,       # floor: min cache-present member rows a basket must keep
    "membership_max_prune_pct": 20.0,  # mass: > this % of a suite off-cache = broken cache rebuild
    "membership_max_prune_abs": 3,     # mass: never trip on this few prunes (small-suite churn is normal)
}


class PruneGuardError(RuntimeError):
    """A prune was refused (floor/mass guard) — surfaces as the collect run's abort."""


def reconcile_cfg() -> dict:
    """Guard thresholds from the config `quality:` block, defaults filling gaps."""
    q = config.load().get("quality") or {}
    out = dict(_DEFAULTS)
    for k in _DEFAULTS:
        if k in q and q[k] is not None:
            out[k] = q[k]
    return out


def _cache_columns(path: Path) -> set[str] | None:
    if not path.exists():
        return None
    try:
        return {str(c) for c in pd.read_parquet(path).columns}
    except Exception as e:  # noqa: BLE001 — unreadable cache = suite unauditable, never mass-prune
        log.warning("close cache %s unreadable: %s", path, e)
        return None


def _display_name(m: dict) -> str:
    return str(m.get("name") or m.get("name_zh") or m.get("ticker") or "?")


def _reconcile_suite(suite: str, cache_rel: str, label: str, data_dir: Path,
                     asof: date, cfg: dict, dry_run: bool) -> dict:
    """Reconcile one suite. Returns its summary dict; never raises — guard refusals land in
    result['refused']/['reasons'] and the caller escalates after all suites ran."""
    res = {"suite": suite, "cache": f"data/{cache_rel}", "skipped": False, "note": "",
           "n_baskets": 0, "n_members": 0, "n_off_cache": 0, "pruned": [],
           "refused": False, "reasons": []}
    mem_path = data_dir / suite / "membership.json"
    if not mem_path.exists():
        res.update(skipped=True, note="membership.json absent — suite skipped")
        return res
    try:
        doc = json.loads(mem_path.read_text(encoding="utf-8"))
        baskets = doc["baskets"]
    except Exception as e:  # noqa: BLE001 — corrupt membership: skip, never prune blind
        res.update(skipped=True, note=f"membership.json unreadable: {e}")
        log.warning("[reconcile] %s membership unreadable: %s", suite, e)
        return res
    cols = _cache_columns(data_dir / cache_rel)
    if cols is None:
        res.update(skipped=True, note=f"close cache data/{cache_rel} absent/unreadable — suite skipped")
        return res

    res["n_baskets"] = len(baskets)
    res["n_members"] = sum(len(b.get("members") or []) for b in baskets.values())
    # ALL member rows must be cache columns (the contract-test definition), removed-dated
    # rows included — a ticker gone from the cache has no computable history in any window.
    off = [(bid, m) for bid, b in baskets.items()
           for m in (b.get("members") or []) if m.get("ticker") not in cols]
    res["n_off_cache"] = len(off)
    if not off:
        return res

    # mass guard: a cache rebuild that lost this much of a curated suite is itself broken.
    # The absolute floor keeps a pct-only guard from misfiring on a small suite, where one
    # genuine delisting is already a large percentage.
    max_pct = float(cfg["membership_max_prune_pct"])
    max_abs = int(cfg["membership_max_prune_abs"])
    pct = 100.0 * len(off) / res["n_members"] if res["n_members"] else 100.0
    if pct > max_pct and len(off) > max_abs:
        res["refused"] = True
        res["reasons"].append(
            f"{suite}: {len(off)}/{res['n_members']} members ({pct:.1f}%) off the {label} close "
            f"cache > {max_pct:.0f}% (and > {max_abs} names) — cache rebuild looks broken "
            "(truncated collect?); refusing to prune, fix the collector instead")
    # floor guard: a pruned basket must keep >= min_present cache-present member rows.
    min_present = int(cfg["membership_min_present"])
    for bid in sorted({bid for bid, _ in off}):
        present = sum(1 for m in (baskets[bid].get("members") or []) if m.get("ticker") in cols)
        if present < min_present:
            res["refused"] = True
            res["reasons"].append(
                f"{suite}/{bid}: prune would leave {present} cache-present member(s) < "
                f"{min_present} — basket needs re-curation or retirement, not a silent prune")
    if res["refused"]:
        for r in res["reasons"]:
            log.error("[reconcile] REFUSED: %s", r)
        return res

    for bid, m in off:
        b = baskets[bid]
        t = m["ticker"]
        b["members"] = [x for x in b["members"] if x is not m]
        n_remain = len(b["members"])
        b.setdefault("changelog", []).append({
            "date": asof.isoformat(),
            "action": "remove",
            "note": (f"{t}: removed — {_display_name(m)} dropped out of the {label} universe/close "
                     "cache, so its price history is no longer computable (cache-validation "
                     f"contract: every member must be a live close-cache column). "
                     f"{n_remain} members remain."),
        })
        res["pruned"].append({"basket": bid, "ticker": t})
        log.warning("[reconcile] PRUNED %s/%s: %s — off the %s close cache "
                    "(dated changelog entry written; %d members remain)%s",
                    suite, bid, t, label, n_remain, " [dry-run: not written]" if dry_run else "")
    if not dry_run:
        # exact serialization of the seeders (ensure_ascii=False, indent=2, no trailing \n)
        mem_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    return res



def _audit_us_sector_membership(
    data_dir: Path,
    *,
    asof: date,
    reference_status: str | None,
) -> dict:
    """Compare PIT-active us_sector_* rows with this run's S&P-500 sector snapshot.

    Evidence-only: this function NEVER edits membership. The reference is
    admissible only when the breadth adapter completed in this same full collect
    run with status ok or stale; both mean fetch() returned and wrote the
    constituent reference. A failed/dead/missing current run may leave an old
    parquet on disk, so it is unauditable instead of false-clean.

    Membership activity follows the house [added, removed) law at asof.
    Malformed membership/reference input makes the audit unavailable; it never
    raises into the regional prune-refusal path.
    """
    result = {
        "membership": "data/baskets/membership.json",
        "reference": "data/breadth/constituents.parquet",
        "reference_status": reference_status,
        "asof": asof.isoformat(),
        "skipped": False,
        "note": "",
        "drift": None,
        "n_extra": 0,
        "n_missing": 0,
        "missing_baskets": [],
        "baskets": [],
    }

    if reference_status not in {"ok", "stale"}:
        result.update(
            skipped=True,
            note=(
                "current breadth collection did not produce a qualified structural "
                f"reference (status={reference_status or 'unavailable'})"
            ),
        )
        return result

    mem_path = data_dir / "baskets" / "membership.json"
    ref_path = data_dir / "breadth" / "constituents.parquet"
    if not mem_path.exists() or not ref_path.exists():
        missing = [
            label for label, path in (("membership", mem_path), ("reference", ref_path))
            if not path.exists()
        ]
        result.update(
            skipped=True,
            note="required U.S. structural input(s) absent: " + ", ".join(missing),
        )
        return result

    try:
        raw_doc = json.loads(mem_path.read_text(encoding="utf-8"))
        baskets = raw_doc.get("baskets")
        constituents = pd.read_parquet(ref_path, columns=["sector"])
    except Exception as exc:  # noqa: BLE001 — unreadable means unauditable, never mutate
        result.update(skipped=True, note=f"U.S. structural inputs unreadable: {exc}")
        return result

    if not isinstance(baskets, dict):
        result.update(skipped=True, note="U.S. structural membership malformed: baskets is not an object")
        return result
    if constituents.index.has_duplicates:
        result.update(skipped=True, note="U.S. structural reference malformed: duplicate ticker index")
        return result
    if constituents.index.isna().any() or constituents["sector"].isna().any():
        result.update(
            skipped=True,
            note="U.S. structural reference classification incomplete: null ticker/sector",
        )
        return result
    allowed_sectors = set(US_SECTOR_BASKETS.values())
    observed_sectors = {str(value) for value in constituents["sector"].tolist()}
    unknown_sectors = sorted(observed_sectors - allowed_sectors)
    if unknown_sectors:
        result.update(
            skipped=True,
            note=(
                "U.S. structural reference classification incomplete: unknown sector(s) "
                + ", ".join(unknown_sectors)
            ),
        )
        return result

    def active_tickers(basket_id: str, basket: dict) -> set[str] | None:
        members = basket.get("members")
        if not isinstance(members, list):
            result.update(
                skipped=True,
                note=f"U.S. structural membership malformed: {basket_id}.members is not a list",
            )
            return None
        active: set[str] = set()
        for index, member in enumerate(members):
            if not isinstance(member, dict):
                result.update(
                    skipped=True,
                    note=f"U.S. structural membership malformed: {basket_id}.members[{index}]",
                )
                return None
            ticker = member.get("ticker")
            added_raw = member.get("added")
            removed_raw = member.get("removed")
            if not isinstance(ticker, str) or not ticker or not isinstance(added_raw, str):
                result.update(
                    skipped=True,
                    note=f"U.S. structural membership malformed: {basket_id}.members[{index}] identity/added",
                )
                return None
            try:
                added = date.fromisoformat(added_raw)
                removed = None if removed_raw in (None, "") else date.fromisoformat(str(removed_raw))
            except (TypeError, ValueError):
                result.update(
                    skipped=True,
                    note=f"U.S. structural membership malformed: {basket_id}.members[{index}] interval",
                )
                return None
            if removed is not None and removed < added:
                result.update(
                    skipped=True,
                    note=f"U.S. structural membership malformed: {basket_id}.members[{index}] removed<added",
                )
                return None
            if added <= asof and (removed is None or asof < removed):
                active.add(ticker)
        return active

    for basket_id, sector in US_SECTOR_BASKETS.items():
        basket = baskets.get(basket_id)
        if not isinstance(basket, dict):
            result["missing_baskets"].append(basket_id)
            continue
        active = active_tickers(basket_id, basket)
        if active is None:
            result["baskets"] = []
            result["n_extra"] = 0
            result["n_missing"] = 0
            result["missing_baskets"] = []
            result["drift"] = None
            return result
        expected = {
            str(ticker)
            for ticker in constituents[constituents["sector"].eq(sector)].index
        }
        extra = sorted(active - expected)
        missing = sorted(expected - active)
        result["n_extra"] += len(extra)
        result["n_missing"] += len(missing)
        result["baskets"].append({
            "basket_id": basket_id,
            "sector": sector,
            "active": len(active),
            "expected": len(expected),
            "extra": extra,
            "missing": missing,
        })

    result["drift"] = bool(
        result["n_extra"] or result["n_missing"] or result["missing_baskets"]
    )
    if result["drift"]:
        parts = []
        if result["n_extra"]:
            parts.append(f"{result['n_extra']} stale/excess")
        if result["n_missing"]:
            parts.append(f"{result['n_missing']} missing")
        if result["missing_baskets"]:
            parts.append(f"{len(result['missing_baskets'])} structural basket(s) absent")
        print(
            "::warning title=us-sector-membership-drift::"
            + ", ".join(parts)
            + "; current S&P/GICS roster differs from curated data/baskets membership; "
              "do not auto-mutate because effective dates require evidence",
            flush=True,
        )
    else:
        result["note"] = "PIT-active structural rosters match this run's qualified breadth reference"
    return result

def run(cfg: dict | None = None, asof: date | None = None,
        data_dir: Path | None = None, out_dir: Path | None = None,
        dry_run: bool = False,
        us_sector_reference_status: str | None = None) -> dict:
    """Reconcile every suite, write data/quality/membership_reconcile.json, and THEN raise
    PruneGuardError if any suite refused (healthy suites are healed either way; the summary
    doc is on disk before the abort so the evidence survives). Test seams mirror the audit_*
    scripts: cfg / asof / data_dir / out_dir."""
    cfg = cfg or reconcile_cfg()
    asof = asof or date.today()
    data_dir = data_dir or config.data_dir()

    suites = [_reconcile_suite(s, c, lb, data_dir, asof, cfg, dry_run) for s, c, lb in SUITES]
    reasons = [r for s in suites for r in s["reasons"]]
    try:
        us_sector_audit = _audit_us_sector_membership(
            data_dir, asof=asof, reference_status=us_sector_reference_status
        )
    except Exception as exc:  # noqa: BLE001 — observational audit never masks prune refusal
        us_sector_audit = {
            "membership": "data/baskets/membership.json",
            "reference": "data/breadth/constituents.parquet",
            "reference_status": us_sector_reference_status,
            "asof": asof.isoformat(),
            "skipped": True,
            "note": f"U.S. structural audit internal failure: {type(exc).__name__}: {exc}",
            "drift": None,
            "n_extra": 0,
            "n_missing": 0,
            "missing_baskets": [],
            "baskets": [],
        }
    n_pruned = sum(len(s["pruned"]) for s in suites)
    doc = {
        "asof": asof.isoformat(),
        "config": dict(cfg),
        "n_suites": len(suites),
        "n_pruned": n_pruned,
        "n_refused": sum(1 for s in suites if s["refused"]),
        "suites": suites,
        "us_sector_audit": us_sector_audit,
    }
    if not dry_run:
        out_dir = out_dir or (data_dir / "quality")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "membership_reconcile.json").write_text(json.dumps(doc, indent=1))

    if reasons:
        raise PruneGuardError(
            "[reconcile] membership prune REFUSED:\n  - " + "\n  - ".join(reasons))
    log.info("[reconcile] membership↔cache: %d suite(s), %d member(s) pruned, 0 refused.",
             len(suites), n_pruned)
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Prune off-cache basket members (dated changelog).")
    ap.add_argument("--data-dir", type=Path, default=None,
                    help="override the data root (default: config data_dir)")
    ap.add_argument("--asof", type=str, default=None, help="YYYY-MM-DD asof override")
    ap.add_argument("--dry-run", action="store_true", help="report prunes without writing files")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s")

    asof = date.fromisoformat(args.asof) if args.asof else None
    try:
        doc = run(asof=asof, data_dir=args.data_dir, dry_run=args.dry_run)
    except PruneGuardError as e:
        print(e)
        return 1
    print(f"membership reconcile asof={doc['asof']}  suites={doc['n_suites']}  "
          f"pruned={doc['n_pruned']}" + ("  [dry-run]" if args.dry_run else ""))
    for s in doc["suites"]:
        tag = "SKIPPED" if s["skipped"] else f"members={s['n_members']:>4} pruned={len(s['pruned'])}"
        print(f"  {s['suite']:16s} {tag}"
              + (f"  [{s['note']}]" if s["skipped"] else "")
              + ("".join(f"\n    - {p['basket']}: {p['ticker']}" for p in s["pruned"])))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
