"""Minimal FastAPI surface for Phase 0.

Not the full app — just enough to prove the service can boot, import the
engine in-process, and serve the regime + a health check. The scheduler,
SSE feed, brain, loop and bridge are added in later phases.

Run:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

from app.deps import data_dir


_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEPLOY_MARKER = ".deployed_git_sha"
_FULL_GIT_SHA = re.compile(r"^[0-9a-f]{40}$")


def _resolve_deployed_git_sha(root: Path | None = None) -> str | None:
    """Return the exact release SHA without trusting malformed provenance.

    Production is deployed from a Git archive and deliberately has no ``.git``
    directory. The transactional deployer writes the validated full SHA to a
    marker before restarting the service. Developer checkouts fall back to
    their local Git HEAD so the open health contract remains useful locally.
    """
    checkout = Path(root) if root is not None else _REPO_ROOT
    try:
        marker_sha = (checkout / _DEPLOY_MARKER).read_text(encoding="utf-8").strip().lower()
    except (OSError, UnicodeError):
        marker_sha = ""
    if _FULL_GIT_SHA.fullmatch(marker_sha):
        return marker_sha

    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=checkout,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip().lower()
    except (OSError, subprocess.SubprocessError):
        return None
    return git_sha if _FULL_GIT_SHA.fullmatch(git_sha) else None


_MANUAL_BRAIN_RESPONSE_FIELDS = (
    "asof", "inaugural", "trading_day", "decided", "holdings",
    "executed", "skipped_unpriceable", "nav", "brain",
    "target_status", "decision_effective",
)


def _manual_brain_response(result: object, status: str, extra: dict | None) -> dict:
    """Return a bounded manual-run receipt without assuming the runner returned a mapping."""
    safe_extra = extra if isinstance(extra, dict) else {}
    if isinstance(result, dict):
        out = {key: result.get(key) for key in _MANUAL_BRAIN_RESPONSE_FIELDS}
    else:
        out = {"target_status": None, "decision_effective": False}
    out["run_status"] = str(status)
    out["run_reason"] = safe_extra.get("reason")
    return out


try:
    from fastapi import FastAPI, HTTPException
except ImportError:  # FastAPI is optional until Phase 1
    FastAPI = None  # type: ignore


def _regime_payload() -> dict:
    latest = json.loads((Path(data_dir()) / "regime" / "latest.json").read_text())
    return {
        "quad": latest["quad"],
        "quad_name": latest.get("quad_name"),
        "growth_score": latest["growth_score"],
        "inflation_score": latest["inflation_score"],
        "liquidity_overlay": latest["liquidity_overlay"],
        "as_of": latest["date"],
    }


if FastAPI is not None:
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
    from brain import cli_bridge

    class ReasonReq(BaseModel):
        prompt: str
        role: str = "pm"          # pm | deep | analyst | scout | fable
        append_system: str | None = None
        max_turns: int | None = None

    from app import web
    from app import pfolio

    app = FastAPI(title="Mastermind", version="0.0.1")

    app.include_router(web.router)
    # Portfolio Risk Desk CRUD proxy (W1). PRD-R8 (re-revised for the VPS cutover): the
    # personal Supabase portfolio panel. Its handlers act as the operator with the
    # SERVICE-ROLE key and take NO caller identity, so app/auth.py owns the boundary —
    # BLOCKED on a serve-only mirror, BEARER-REQUIRED on the authoritative public VPS
    # (all methods, GET included; blocked outright when no token is configured), open
    # only on a local/non-authoritative box. See app/auth.py _PFOLIO_PATH_PREFIX.
    app.include_router(pfolio.router)

    # Short-TTL response cache for GET /api/* — installed BEFORE auth so the auth gate stays
    # OUTERMOST (an unauthenticated request never reaches the cache). No-op unless
    # MASTERMIND_RESP_CACHE_TTL>0.
    from app import response_cache
    response_cache.install(app)

    # App-level middleware — the serve-only POST guard (MASTERMIND_SERVE_ONLY),
    # the bearer-token OPERATOR tier (MASTERMIND_AUTH_TOKEN) over mutating/LLM POSTs,
    # and operator-path rate limiting. There is NO browser login: read-only browsing
    # (the UI + read /api routes + the SSE stream) is always open. MUST be installed
    # before the server handles requests.
    from app import auth
    auth.install(app)

    # Resolved once at startup: /health is polled by uptime probes and must not
    # touch disk or spawn a subprocess per request. Fails closed to no commit.
    _git_sha = _resolve_deployed_git_sha()

    def _startup_flags() -> dict:
        """Snapshot of MASTERMIND_* env vars at startup time — embedded in the app_started event."""
        try:
            from control_plane import flags
            return flags.enumerate_flags()
        except Exception:
            return {}

    def _runtime_health() -> dict:
        """Shared body for /health and /ready.

        `status` is HONEST: it is "ok" only when every runtime this instance is
        expected to be running actually is. Uptime probes check `status == "ok"`
        only, so a hardcoded "ok" alongside `scheduled_runtime_ok: false` told a
        simple probe the box was fine while the canonical scheduler was dead.
        Serve-only instances expect NO scheduler, so their absence is not a fault.
        """
        from app.auth import serve_only as _serve_only
        from brain import client as _brain_client, codex_bridge as _codex_bridge
        reasoning_backend = _brain_client.backend()
        shared_reasoning_available = (
            _brain_client.available() if reasoning_backend == "waterfall" else False
        )
        reasoning_policy_ok = reasoning_backend == "waterfall" and shared_reasoning_available
        codex_available = _codex_bridge.available()
        is_serve_only = _serve_only()
        scheduler_obj = getattr(app.state, "scheduler", None)
        scheduler_running = bool(
            scheduler_obj is not None and getattr(scheduler_obj, "running", False)
        )
        scheduled_runtime_expected = not is_serve_only
        scheduled_runtime_ok = (not scheduled_runtime_expected) or scheduler_running
        out: dict = {
            "status": "ok" if scheduled_runtime_ok else "degraded",
            "paper_only": True,
            "reasoning_policy_scope": "scheduled_portfolio_reasoning",
            "reasoning_backend": reasoning_backend,
            "reasoning_policy": "codex_first_claude_oauth_fallback",
            "reasoning_policy_ok": reasoning_policy_ok,
            "shared_reasoning_available": shared_reasoning_available,
            "codex_available": codex_available,
            "reasoning_primary": (
                "unavailable" if not shared_reasoning_available
                else "codex" if codex_available
                else "claude_oauth_fallback"
            ),
            "scheduled_portfolio_reasoning_backend": reasoning_backend,
            "scheduled_portfolio_reasoning_policy": "codex_first_claude_oauth_fallback",
            "scheduled_portfolio_reasoning_available": shared_reasoning_available,
            "scheduled_portfolio_reasoning_policy_ok": reasoning_policy_ok,
            "scheduled_runtime_expected": scheduled_runtime_expected,
            "scheduler_running": scheduler_running,
            "scheduled_runtime_ok": scheduled_runtime_ok,
            "advisor_chat_backend": "claude_agent_sdk",
            "advisor_chat_uses_scheduled_reasoning_waterfall": False,
        }
        if _git_sha:
            out["commit"] = _git_sha
            out["version"] = _git_sha
        if is_serve_only:
            out["serve_only"] = True
        return out

    @app.get("/health")
    def health() -> dict:
        """LIVENESS + provenance. Always HTTP 200 while the process can answer —
        supervisors and scripts/deploy_code_to_vps.sh both curl this (the deploy probe
        uses `curl -fsS`, so a non-2xx here would break the release transaction) and
        then grep the body for reasoning_policy_ok / scheduled_runtime_ok / commit.
        Readiness lives in the `status` field and, as a hard signal, in /ready.

        Keep only non-sensitive fields; filesystem and CLI paths are omitted — they
        would leak on an open route.
        """
        return _runtime_health()

    @app.get("/ready")
    def ready() -> JSONResponse:
        """READINESS. 503 when a runtime this instance is expected to be running is
        not (today: the scheduler on a non-serve-only box). A serve-only mirror is
        ready WITHOUT a scheduler because its absence is intentional there."""
        out = _runtime_health()
        is_ready = bool(out.get("scheduled_runtime_ok"))
        return JSONResponse({"ready": is_ready, **out},
                            status_code=200 if is_ready else 503)

    @app.get("/regime")
    def regime() -> dict:
        return _regime_payload()

    class ResearchReq(BaseModel):
        prompt: str
        role: str = "deep"
        max_turns: int | None = None
        resume: str | None = None     # continue a prior research session by id

    def _reject_archived_run(portfolio_id: str) -> None:
        """HTTP 410 before locks/imports/model calls for a retired portfolio runner."""
        from portfolio import registry
        if not registry.is_archived(portfolio_id):
            return
        meta = registry.get(portfolio_id)
        raise HTTPException(status_code=410, detail={
            "error": "portfolio_archived",
            "portfolio_id": portfolio_id,
            "status": "archived",
            "superseded_by": meta.get("superseded_by"),
            "reason": meta.get("archived_reason"),
        })

    @app.post("/reason")
    async def reason(req: ReasonReq) -> dict:
        """Drive Claude Code headlessly for a reasoning pass over the dashboard context."""
        return await cli_bridge.reason(
            req.prompt, role=req.role, append_system=req.append_system, max_turns=req.max_turns)

    @app.on_event("startup")
    def _start_scheduler():
        from app import auth as _auth
        from app import scheduler

        # FAIL CLOSED before anything else binds or spawns: an authoritative instance
        # with no MASTERMIND_AUTH_TOKEN would expose every LLM-spending / book-running
        # route and the personal portfolio panel unauthenticated. The authoritative
        # systemd unit loads its secrets from an OPTIONAL EnvironmentFile, so a missing
        # or unreadable /etc/macro-api.env must abort the start rather than silently
        # degrade the security posture. Raises auth.AuthorizationMisconfigured.
        _auth.assert_authoritative_auth_configured()

        _is_serve_only = _auth.serve_only()

        # MW1: record an app_started event (survives restarts; JSONL is permanent).
        _current_flags = _startup_flags()
        try:
            from control_plane import run_events
            run_events.append({
                "kind": "app_started",
                "job": "startup",
                "book": "",
                "step": "init",
                "status": "ok",
                "actor": "system",
                "extra": {
                    "git_sha": _git_sha or "unknown",
                    "flags": _current_flags,
                    **({"serve_only": True} if _is_serve_only else {}),
                },
            })
        except Exception:
            pass

        # MW2: governance emitters — (a) flag-state diff vs previous startup,
        # (e) doctrine-hash change detection.  Both are additive; never raise.
        try:
            from control_plane import governance as _gov
            _prior_flags = _gov._last_startup_flags() or {}
            _gov.append_flag_diff(_prior_flags, _current_flags, source_artifact="startup")
        except Exception:
            pass
        try:
            from control_plane import governance as _gov
            _gov.check_doctrine_hash()
        except Exception:
            pass

        # MW6: serve-only mode — scheduler NEVER starts; all operator paths return 403.
        if _is_serve_only:
            import logging as _logging
            _logging.getLogger("app.main").info(
                "MASTERMIND_SERVE_ONLY=1 — scheduler NOT started (read-only mirror mode)")
            try:
                from control_plane import run_events as _re
                _re.append({
                    "kind": "app_started", "job": "startup", "book": "",
                    "step": "serve_only_skip", "status": "ok", "actor": "system",
                    "extra": {"serve_only": True, "detail": "scheduler skipped in serve-only mode"},
                })
            except Exception:
                pass
            app.state.scheduler = None
        else:
            started_scheduler = scheduler.start()
            if started_scheduler is None:
                # APScheduler is a declared runtime dependency. A reasoning API without daily,
                # settlement, or learning jobs is not a degraded portfolio service—it is a dead
                # one—so fail startup and let the supervisor/deployer roll back.
                raise RuntimeError("scheduler failed to start: APScheduler unavailable")
            app.state.scheduler = started_scheduler

        # SCHEDULER WATCHDOG (incident 2026-07-06 ×2): APScheduler's main-loop thread can die
        # silently (observed: sqlite jobstore flipping to "readonly database") while uvicorn keeps
        # serving — a zombie desk that marks nothing and settles nothing. Fail FAST instead:
        # detect the dead thread, write a HARD_STOP run-event, and exit the process so the
        # supervisor (launchd KeepAlive) restarts it clean. Never trades; strictly less risk
        # than a silent scheduler death (charter P2/P10).
        def _scheduler_watchdog(sch) -> None:
            import time as _time
            while True:
                _time.sleep(60)
                if not watchdog_check_once(sch):
                    return  # unreachable in production (exit_fn exits); reachable in tests

        if app.state.scheduler is not None:
            import threading as _threading
            _threading.Thread(target=_scheduler_watchdog, args=(app.state.scheduler,),
                              name="scheduler-watchdog", daemon=True).start()

        # First turn-on: let the autonomous book buy right away instead of waiting for the next
        # scheduled close. No-op once it has a track record; runs in a daemon thread (non-blocking).
        # MW6: serve-only mode — skip all first-run daemon threads.
        if _is_serve_only:
            app.state.autonomous_first_run = False
            app.state.heavyweight_first_run = False
            app.state.china_first_run = False
            app.state.hk_first_run = False
            app.state.etf_first_run = False
            return

        try:
            app.state.autonomous_first_run = scheduler.maybe_first_autonomous_run()
        except Exception:
            app.state.autonomous_first_run = False
        # Retired books retain their state/API history but never spawn startup workers.
        app.state.heavyweight_first_run = False
        # All-China book — kick its first build too (no-op once it has a track record). Runs on
        # Asia's clock thereafter via the china_daily cron.
        try:
            app.state.china_first_run = scheduler.maybe_first_china_run()
        except Exception:
            app.state.china_first_run = False
        try:
            app.state.hk_first_run = scheduler.maybe_first_hk_run()
        except Exception:
            app.state.hk_first_run = False
        app.state.etf_first_run = False

    @app.post("/daily")
    def daily(force: bool = False) -> dict:
        """Manually fire the daily loop (gated book + armed research)."""
        _reject_archived_run("flagship")
        from control_plane import run_ledger, locks
        handle = run_ledger.start_run("daily_loop", book="flagship", trigger="http")
        lock = locks.acquire_or_log("book:flagship", job="daily_loop", book="flagship")
        if lock is None:
            run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
            return {"skipped": True, "reason": "lock_held"}
        try:
            with lock:
                from bot.daily import run_daily
                out = run_daily(force=force)
            run_ledger.end_run(handle, "ok")
            return {k: out.get(k) for k in ("asof", "research")} | {
                "book_ran": (out.get("book") or {}).get("ran")}
        except Exception as exc:
            run_ledger.end_run(handle, "error")
            raise

    @app.post("/api/autonomous/run")
    async def autonomous_run(force: bool = False, wait: bool = False) -> dict:
        """Manually fire the autonomous Opus-Brain book (research → free-form rebalance).

        The Brain call is long; by default this starts it in the background and returns
        immediately. Pass ?wait=true to block until it finishes (returns the run summary)."""
        from control_plane import run_ledger, locks
        from app.scheduler import _brain_job_outcome
        from bot import autonomous
        if wait:
            import asyncio as _aio
            handle = run_ledger.start_run("autonomous_daily", book="autonomous", trigger="http")
            lock = locks.acquire_or_log("book:autonomous", job="autonomous_daily", book="autonomous")
            if lock is None:
                run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
                return {"skipped": True, "reason": "lock_held"}
            try:
                with lock:
                    out = await _aio.to_thread(autonomous.run_autonomous, force=force)
                _status, _severity, _extra = _brain_job_outcome(out)
                run_ledger.end_run(handle, _status, severity=_severity, extra=_extra)
                return _manual_brain_response(out, _status, _extra)
            except Exception:
                run_ledger.end_run(handle, "error")
                raise

        def _run():
            handle = run_ledger.start_run("autonomous_daily", book="autonomous", trigger="http")
            lock = locks.acquire_or_log("book:autonomous", job="autonomous_daily", book="autonomous")
            if lock is None:
                run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
                return
            try:
                with lock:
                    out = autonomous.run_autonomous(force=force)
                _status, _severity, _extra = _brain_job_outcome(out)
                run_ledger.end_run(handle, _status, severity=_severity, extra=_extra)
            except Exception as exc:
                run_ledger.end_run(handle, "error")
                raise

        import threading
        threading.Thread(target=_run, name="autonomous-manual-run", daemon=True).start()
        return {"started": True, "note": "Autonomous Brain run started in the background."}

    @app.post("/api/heavyweight/run")
    async def heavyweight_run(force: bool = False, wait: bool = False) -> dict:
        """Manually fire the Heavyweight Opus-Brain book (study Flagship → concentrated rebalance).

        Long call; by default starts in the background and returns immediately. ?wait=true blocks."""
        _reject_archived_run("heavyweight")
        from control_plane import run_ledger, locks
        from bot import heavyweight
        if wait:
            import asyncio as _aio
            handle = run_ledger.start_run("heavyweight_daily", book="heavyweight", trigger="http")
            lock = locks.acquire_or_log("book:heavyweight", job="heavyweight_daily", book="heavyweight")
            if lock is None:
                run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
                return {"skipped": True, "reason": "lock_held"}
            try:
                with lock:
                    out = await _aio.to_thread(heavyweight.run_heavyweight, force=force)
                run_ledger.end_run(handle, "ok")
                return {k: out.get(k) for k in
                        ("asof", "inaugural", "trading_day", "decided", "holdings", "flagship_universe_size",
                         "held_prior_book", "enforcement", "executed", "skipped_unpriceable", "nav", "brain")}
            except Exception:
                run_ledger.end_run(handle, "error")
                raise

        def _run():
            handle = run_ledger.start_run("heavyweight_daily", book="heavyweight", trigger="http")
            lock = locks.acquire_or_log("book:heavyweight", job="heavyweight_daily", book="heavyweight")
            if lock is None:
                run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
                return
            try:
                with lock:
                    heavyweight.run_heavyweight(force=force)
                run_ledger.end_run(handle, "ok")
            except Exception:
                run_ledger.end_run(handle, "error")
                raise

        import threading
        threading.Thread(target=_run, name="heavyweight-manual-run", daemon=True).start()
        return {"started": True, "note": "Heavyweight Brain run started in the background."}

    @app.post("/api/china/run")
    async def china_run(force: bool = False, wait: bool = False) -> dict:
        """Manually fire the all-China Opus-Brain book (research the China desks → free-form,
        multi-venue, USD-marked rebalance).

        Long call; by default starts in the background and returns immediately. ?wait=true blocks."""
        from control_plane import run_ledger, locks
        from app.scheduler import _brain_job_outcome
        from bot import china
        if wait:
            import asyncio as _aio
            handle = run_ledger.start_run("china_daily", book="china", trigger="http")
            lock = locks.acquire_or_log("book:china", job="china_daily", book="china")
            if lock is None:
                run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
                return {"skipped": True, "reason": "lock_held"}
            try:
                with lock:
                    out = await _aio.to_thread(china.run_china, force=force)
                _status, _severity, _extra = _brain_job_outcome(out)
                run_ledger.end_run(handle, _status, severity=_severity, extra=_extra)
                return _manual_brain_response(out, _status, _extra)
            except Exception:
                run_ledger.end_run(handle, "error")
                raise

        def _run():
            handle = run_ledger.start_run("china_daily", book="china", trigger="http")
            lock = locks.acquire_or_log("book:china", job="china_daily", book="china")
            if lock is None:
                run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
                return
            try:
                with lock:
                    out = china.run_china(force=force)
                _status, _severity, _extra = _brain_job_outcome(out)
                run_ledger.end_run(handle, _status, severity=_severity, extra=_extra)
            except Exception:
                run_ledger.end_run(handle, "error")
                raise

        import threading
        threading.Thread(target=_run, name="china-manual-run", daemon=True).start()
        return {"started": True, "note": "China Brain run started in the background."}

    @app.post("/api/hk/run")
    async def hk_run(force: bool = False, wait: bool = False) -> dict:
        """Manually fire the Hong-Kong Opus-Brain book (HK listings only, HKD-marked rebalance).

        Long call; by default starts in the background and returns immediately. ?wait=true blocks."""
        from control_plane import run_ledger, locks
        from app.scheduler import _brain_job_outcome
        from bot import hk
        if wait:
            import asyncio as _aio
            handle = run_ledger.start_run("hk_daily", book="hk", trigger="http")
            lock = locks.acquire_or_log("book:hk", job="hk_daily", book="hk")
            if lock is None:
                run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
                return {"skipped": True, "reason": "lock_held"}
            try:
                with lock:
                    out = await _aio.to_thread(hk.run_hk, force=force)
                _status, _severity, _extra = _brain_job_outcome(out)
                run_ledger.end_run(handle, _status, severity=_severity, extra=_extra)
                return _manual_brain_response(out, _status, _extra)
            except Exception:
                run_ledger.end_run(handle, "error")
                raise

        def _run():
            handle = run_ledger.start_run("hk_daily", book="hk", trigger="http")
            lock = locks.acquire_or_log("book:hk", job="hk_daily", book="hk")
            if lock is None:
                run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
                return
            try:
                with lock:
                    out = hk.run_hk(force=force)
                _status, _severity, _extra = _brain_job_outcome(out)
                run_ledger.end_run(handle, _status, severity=_severity, extra=_extra)
            except Exception:
                run_ledger.end_run(handle, "error")
                raise

        import threading
        threading.Thread(target=_run, name="hk-manual-run", daemon=True).start()
        return {"started": True, "note": "HK Brain run started in the background."}

    @app.post("/api/etf/run")
    async def etf_run(force: bool = False, wait: bool = False) -> dict:
        """Manually fire the ETF Opus-Brain book (rotate across US-listed ETFs under doctrine +
        risk guardrails).

        Long call; by default starts in the background and returns immediately. ?wait=true blocks."""
        _reject_archived_run("etf")
        from control_plane import run_ledger, locks
        from bot import etf
        if wait:
            import asyncio as _aio
            handle = run_ledger.start_run("etf_daily", book="etf", trigger="http")
            lock = locks.acquire_or_log("book:etf", job="etf_daily", book="etf")
            if lock is None:
                run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
                return {"skipped": True, "reason": "lock_held"}
            try:
                with lock:
                    out = await _aio.to_thread(etf.run_etf, force=force)
                run_ledger.end_run(handle, "ok")
                return {k: out.get(k) for k in
                        ("asof", "inaugural", "trading_day", "decided", "holdings", "risk_state",
                         "guardrails", "executed", "skipped_unpriceable", "nav", "brain")}
            except Exception:
                run_ledger.end_run(handle, "error")
                raise

        def _run():
            handle = run_ledger.start_run("etf_daily", book="etf", trigger="http")
            lock = locks.acquire_or_log("book:etf", job="etf_daily", book="etf")
            if lock is None:
                run_ledger.end_run(handle, "skip", severity="ADVISORY_ONLY")
                return
            try:
                with lock:
                    etf.run_etf(force=force)
                run_ledger.end_run(handle, "ok")
            except Exception:
                run_ledger.end_run(handle, "error")
                raise

        import threading
        threading.Thread(target=_run, name="etf-manual-run", daemon=True).start()
        return {"started": True, "note": "ETF Brain run started in the background."}

    @app.post("/research")
    async def research(req: ResearchReq) -> dict:
        """An ARMED, multi-turn research session: Claude reads the dashboard (MCP tools),
        searches the web/news, reasons through 2nd/3rd-order effects, and writes conclusions
        back to the app (research notes, proposed theses, emerging-theme flags). Paper-only —
        nothing auto-executes."""
        return await cli_bridge.research(
            req.prompt, role=req.role, max_turns=req.max_turns, resume=req.resume)

    # ---- Live advisor chat (streamed) -------------------------------------
    from fastapi.responses import StreamingResponse

    class ChatReq(BaseModel):
        message: str
        conversation_id: str | None = None   # carry across turns to keep context

    def _sse(obj: dict) -> str:
        return f"data: {json.dumps(obj, default=str)}\n\n"

    @app.post("/chat")
    async def chat(req: ChatReq) -> StreamingResponse:
        """Talk to the Brain live. Streams the armed advisor's reasoning, tool use, and
        verdict back over SSE. The Brain reads the dashboard / book on demand and can stage
        recommendations + theses into the review queue — it never executes a trade.

        Each SSE frame is a JSON event: start | text | tool | tool_result | done | error.
        Pass back `conversation_id` (from the `start` frame) on the next turn for continuity.
        """
        from brain import advisor

        conv_id = req.conversation_id or advisor.new_conversation_id()
        resume = advisor.get_session(conv_id)

        async def gen():
            yield _sse({"type": "start", "conversation_id": conv_id})
            advisor.append_turn(conv_id, "user", req.message)
            last_sid, acc, tools, papers = resume, "", [], []
            try:
                async for ev in cli_bridge.chat_stream(
                        req.message, resume=resume, append_system=advisor.SYSTEM):
                    et = ev.get("type")
                    if et == "text":
                        acc += ev.get("text") or ""
                    elif et == "tool":
                        tools.append({"name": ev.get("name"), "args": ev.get("args")})
                    elif et == "paper":
                        papers.append({k: ev.get(k) for k in
                                       ("paper_id", "ticker", "title", "combined", "confirmed",
                                        "research_score", "engine_score", "viability")})
                    elif et == "done" and ev.get("session_id"):
                        last_sid = ev["session_id"]
                    yield _sse(ev)
            except Exception as exc:                       # never leave the stream hanging
                yield _sse({"type": "error", "error": repr(exc)[:300]})
            finally:
                advisor.set_session(conv_id, last_sid)
                advisor.append_turn(conv_id, "brain", acc, tools, papers)

        return StreamingResponse(gen(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache",
                                          "X-Accel-Buffering": "no"})

    @app.get("/chat/history")
    def chat_history(conversation_id: str) -> dict:
        """The stored transcript for a conversation so the popup rehydrates on reload."""
        from brain import advisor
        return {"conversation_id": conversation_id,
                "turns": advisor.load_history(conversation_id)}

    @app.get("/chat/paper")
    def chat_paper(id: str) -> dict:
        """A filed research paper for the in-chat 'open paper' modal (also on the Research page)."""
        from brain import research_paper
        for p in research_paper.load_papers():
            if p.get("id") == id:
                return {"id": p["id"], "ticker": p.get("ticker"),
                        "title": f"{p.get('ticker')} — Research Report",
                        "report_md": p.get("report_md"), "summary": p.get("summary"),
                        "combined": p.get("combined"), "confirmed": p.get("confirmed"),
                        "research_score": p.get("research_score"),
                        "engine_score": p.get("engine_score"),
                        "viability": p.get("viability"), "key_risks": p.get("key_risks") or []}
        return {"error": "not found", "id": id}


def watchdog_check_once(sch, exit_fn=None, events_root=None) -> bool:
    """One scheduler-watchdog probe (MW1 incident hardening; extracted module-level
    so the M7 drill tests the PRODUCTION logic, not an inline copy — S10).

    Returns True when the APScheduler thread is alive (keep watching). On a dead
    thread: writes a HARD_STOP run-event, logs critically, then calls ``exit_fn(70)``
    (default ``os._exit`` — fail-fast for the supervisor to restart) and returns
    False. NEVER raises.
    """
    import os as _os
    if exit_fn is None:
        exit_fn = _os._exit
    try:
        th = getattr(sch, "_thread", None)
        if th is not None and th.is_alive():
            return True
        try:
            from control_plane import run_events as _re
            _re.append({
                "kind": "guardrail", "job": "scheduler", "book": "",
                "step": "watchdog", "status": "error", "severity": "HARD_STOP",
                "err": "APScheduler thread dead — exiting for supervisor restart",
                "actor": "system",
            }, root=events_root)
        except Exception:
            pass
        import logging as _logging
        _logging.getLogger("app.main").critical(
            "scheduler watchdog: APScheduler thread dead — exiting (supervisor restarts)")
        print("scheduler watchdog: APScheduler thread dead — exiting (supervisor restarts)",
              flush=True)
        exit_fn(70)
        return False
    except Exception:  # noqa: BLE001 — the watchdog itself must never crash the app
        return True
