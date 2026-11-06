# News Intelligence — scan-first production evidence

Candidate source: `templates/news.html.j2` on the News Intelligence implementation carrier.

Primary manifest: `manifest.json`
- canonical `mastermind.p0_evidence.v2` capture
- eight required rest cells: desktop/mobile × EN/ZH × dark/light
- real browser interaction states for `hover(.nxi-open)`, `focus(.nxi-open)`, and `focus(.nx-depth-summary)`
- 32/32 attempted states captured

Story Brief manifest: `brief-manifest.json`
- same candidate page rendered with a deterministic `intelligence.desk/v1` fixture
- capture-only harness opens the first Story Brief after production hydration
- the proof shell hides underlying page siblings after open so full-page capture records the fixed viewport rather than a misleading long-page composite; production source is unchanged
- eight cells: desktop/mobile × EN/ZH × dark/light
- 8/8 attempted states captured

The deterministic fixture uses only fields already present in the public `intelligence.desk/v1` contract. It adds no product backend, ranking source, correction ledger, or persistence surface.

Capture provenance is recorded in each manifest. Screenshots are evidence for visual review, not an assertion of production deployment or product acceptance.
