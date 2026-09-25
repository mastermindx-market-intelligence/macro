---
key: A-LANE-HOSTS-PACKAGE-DRIFT-VOIDS-ITS-OWN-GATE
claim: >
  A remote build lane proves its work with a test-suite summary produced in the lane host's venv, so
  that venv drifting off the repository's own pin silently converts the lane's strongest evidence
  into an unreadable number - and the drift is invisible in the returned block unless the worker
  happens to notice and report it. Measured 2026-09-25: host `mb`'s shared `~/lanes/venv` carried
  `mcp 2.2.0` while Mastermind `pyproject.toml:38` pins `mcp==1.28.1` exactly, with a source comment
  recording that the historical `mcp>=` floor was deliberately retired for the maintained v1 line.
  In mcp 2.x `FastMCP` was renamed to `MCPServer`, so `import mcp.server.fastmcp` raises, five
  modules break, one of 42 suite files became uncollectable, and 4 spurious `AttributeError`
  failures appeared in suites the lane was forbidden to edit.
falsifier: >
  `ssh <host> '~/lanes/venv/bin/python3 -m pip show mcp'` reporting the pinned version retires this
  note for that host. To test whether a given drift is load-bearing rather than cosmetic, run the
  identical suite set at the identical commit in a venv holding the pin: if the failure sets differ,
  every cross-environment differential built on that host is void, including its "no new failures".
so_what: >
  Treat a remote lane's gate line as ADVISORY and run the authoritative differential yourself
  against the pin. Name the affected files in the brief up front as known-not-yours, because the
  alternative failure is worse than a confusing number: a diligent worker "repairs" the four
  failures and silently ports the repository off its own pin, shipping an API migration nobody
  asked for inside a slice about something else. The correct worker behaviour is to report them
  under DEVIATIONS and leave them, which is what happened here. Do not fix the venv from a delivery
  session either - a shared lane venv is capacity-owned support and installing into it is outside a
  delivery grant; the drift is an escalation, not a task.
kind: constraint
verified_at: 2026-09-25
verified_by: >
  Read `pyproject.toml:38` (`"mcp==1.28.1"`) in the repository; `pip show mcp` returned 2.2.0 on
  `mb`'s lane venv and 1.28.1 in the local gate venv; the mcp 2.x import error text names the
  `FastMCP` -> `MCPServer` rename itself. The same 42 files ran clean (`0 failed`) in the pinned
  venv at the same commit where the lane reported 4 failures and one uncollectable file.
scope:
  - remote pool lanes (pool remote <host> <mode>)
  - any brief requiring a CONSUMER_GATE summary line
  - Mastermind MCP suites (workbench_read_mcp, workbench_action_mcp, workspace_agent_return_app, paper_desktop)
confidence: verified
---

Worth separating two things this conflates. The lane host being wrong is ordinary infrastructure
drift. What makes it a landmine is that the lane's evidence and the lane's environment are produced
by the same process, so the evidence cannot report on its own environment - the summary line looks
identical whether the host is pinned or not. The only fix that generalises is an independently
pinned verifier on the accepting side, which is also what makes a worker's green gate acceptable
testimony rather than proof.
