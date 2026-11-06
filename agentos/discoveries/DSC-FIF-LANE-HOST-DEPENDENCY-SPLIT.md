---
key: FIF-LANE-HOST-DEPENDENCY-SPLIT
claim: >
  Among the external FIF lane hosts, only one (the host the seat calls
  "ubuntu2") carries the fastapi/openpyxl/lxml/pandas stack, and none carries
  the stripe SDK, so a test module that imports the app factory fails on a
  lane host with `SystemExit: The stripe SDK is required` rather than a test
  failure. HOST FACTS ARE REPORTED-BY-THE-SEAT (the FIF e2e wave-1 seat),
  not independently verified by the recording lane; the in-repo mechanism
  anchors were verified.
falsifier: >
  On the lane host in question, `python3 -c "import stripe"` succeeding (and
  likewise `import fastapi, openpyxl, lxml, pandas` failing only on hosts
  other than ubuntu2) would disprove the host inventory; separately, a
  module importing only `app.forensics` (not the full app factory) NOT
  raising the stripe SystemExit would disprove the failure-mode attribution.
so_what: >
  On lane hosts, run API/Excel-adjacent suites per-file and off the app
  factory (import the narrow module under test, not `app.main` /
  `from app import billing` chains), and treat CI (where the full dependency
  set is installed) as the acceptance signal for those suites — do not burn
  lane time debugging a dependency absence as if it were a code defect.
kind: runtime
verified_at: 2026-10-12
verified_by: >
  Host inventory + failure mode: reported by the FIF e2e wave-1 seat
  (unverified here — no lane-host shell was available to the recording
  lane). In-repo mechanism anchors, verified in this worktree:
  scripts/stripe_bootstrap.py:40-44 — module-level `sys.exit("The stripe SDK
  is required (pip install 'stripe>=11,<13')")` on ImportError, the literal
  source of the reported SystemExit text; app/requirements.txt:62 —
  `stripe>=11,<13` is an app dependency lane hosts do not install;
  tests/test_plans_catalog.py:106 — an existing suite doing `from app import
  billing`, the import shape that drags the billing/stripe surface in;
  app/billing.py:231-233 — the runtime `HTTPException(503, "billing
  unavailable: stripe SDK not installed")` sibling (request-path, exempt
  from the import-time SystemExit).
scope:
  - macro
  - app/
  - tests/test_fundamental_forensics_financial_*.py
  - tests/test_fundamental_forensics_excel_export.py
confidence: probable
---

# Lane hosts split: one carries the web stack, none carries stripe

FIF wave 1's API-adjacent and Excel suites (D3's provider/service/API suites,
X1's excel_export suite) run green in CI but cannot be trusted from an
arbitrary external lane host: the fastapi/openpyxl/lxml/pandas stack exists
on exactly one lane host, and the stripe SDK on none — and the stripe
absence surfaces as an import-time `SystemExit` ("The stripe SDK is
required", minted at scripts/stripe_bootstrap.py:44), which pytest reports
as a collection error, not a skip. The practical rule for any future lane
running these suites: import the narrow module under test, never the app
factory chain, and let CI be the acceptance signal. The host census itself
is the seat's observation — re-verify with `python3 -c "import stripe"` on
the host before relying on it for a new lane.
