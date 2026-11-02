# Prophet public workspace evidence

The fixture renders the candidate dashboard with the committed October 30 US board, action board and Plan-book snapshot. It passes data through the native board, panel and Plan preview splits, including the shell-only Plan relation filter. Auxiliary page fields use the existing dashboard test fixture. The render records input hashes in `public-inputs.json` and excludes withheld Plan IDs from its HTML. It serves only the public preview and static assets. External services, live quotes, production adoption and authenticated accounts are outside this capture.

The canonical material evidence is `manifest.json`. It covers the public stock workspace at 1440, 768, 390 and 320 pixels in English and Chinese, light and dark. Each cell captures the resting page, focus on the first reachable Today card’s View setup control, and hover on the page navigation. `smells.json` retains fixture resource failures and layout measurements. The scope includes the rendered cards, the chart and dated terms, the action footer, and the workspace order ahead of market context. Some cards are obscured by the existing anonymous access rules. The absence of a protected payload and of auxiliary live services is visible in the fixture.

The additional `public-sources/` screenshots use actual public controls to open FLS, select Sources, and open its source disclosure. They record the visible candidate identity, dates, Plan notice, and overflow checks. FLS's related record requires full access. The public journey ends there. These screenshots do not claim an authenticated Plan hop, a live deployment, or approval of the Paper design.

The assessed Paper frames are LKU-0 (Setup), 8OM-0 (Evidence), 4U6-0 (Plans) and VBF-0 (R7 Setup) in document `01M3NT5Y3G5HTJHVR0K5W2MDJM`. The production template uses an overlaid Sources disclosure. The Paper studies also show a selected evidence item with an adjacent inspector, or persistent timing and Plan panels. The fixture verifies the actual template layout and interaction states without promoting either design to product acceptance.

Run from the repository root with a fresh local fixture directory. The HTML capture input is separate from production output.

\x60\x60\x60sh
proof=mockups/evidence/prophet-opportunity-workspace
fixture=site/_tmp/prophet-acceptance-89dcceeb
python3 "$proof/render_public_fixture.py" "$fixture" > "$proof/public-inputs.json"
python3 scripts/capture_page_evidence.py --repo macro --site-dir "$fixture" \\
  --routes /us_stocks.html --viewports desktop,mobile,tablet-768,narrow-320 \\
  --locales en,zh --themes light,dark \\
  --force-state 'setup-focus:focus(#us-today-grid .po-card summary.po-setup)' \\
  --force-state 'nav-hover:hover(.prophet-section-nav a)' \\
  --output-dir "$proof/cells" --manifest "$proof/manifest.json" --smells "$proof/smells.json"
python3 "$proof/inspect_public_sources.py" "$fixture" "$proof/public-sources"
\x60\x60\x60

The HK/Canada P0B receipts are separate. Their pinned recipe, executable, fixture assets and historical baseline are derived from `mockups/evidence/prophet-p0b-zero-fouc/mobile-layout*.json` by `scripts/check_p0b_receipt_closure.py`.
