# F04-X1 WTI Live Path — served journey at the baked revision (2026-09-25)

Anonymous evidence captured against the live origin `https://www.mastermind-x.com` after the shared nav
was baked and published: closing-bell full close render, commit `c4b705de8f29da0faf6676999effde31d9a81931`
(2026-09-25T00:45:29Z; closing-bell runs 36071377973 / 36074382548, both success). Served `ontology.html`
markers (`ontology.css?v=89e4af01`, `ontology.js?v=bb5bdf21`) and the served `ontology.js` sha256
(`bb5bdf21ac8446bc…`) equal the committed `site/` copies on `origin/main` at capture time.

- `manifest.json` / `smells.json` / `smells.md` + 24 PNGs — `scripts/capture_page_evidence.py --base-url https://www.mastermind-x.com --routes /macro.html,/ontology.html,/transmission.html --viewports desktop,mobile --locales en,zh --themes dark,light` (generated 2026-09-25T00:55:12Z); 24/24 states captured; anonymous only.
- `nav/nav-reachability.json` + 16 PNGs — `nav/nav_open_proof.cjs` (playwright, node): `macro.html` → shared nav (hamburger on mobile; hover on desktop) → "Research" → Capital & Regimes → **WTI Live Path** → real click → `ontology.html` (generated 2026-09-25T01:10:31Z); 8/8 cells (desktop 1440×900 / mobile 390×844 × EN / ZH × dark / light) reach `ontology.html` by ordinary navigation, landing on the anonymous gate state.

Honesty: no credential is entered; the entitled half of the journey (composer input → owner data) is not in
this pack and needs a signed-in entitled account. `macro.html` never reaches network idle (live polling),
so the nav proof waits for `load` + a settle; its anonymous 401s on live JSON are recorded in the manifest
and are the page's ordinary anonymous behaviour, not an F04 effect.
