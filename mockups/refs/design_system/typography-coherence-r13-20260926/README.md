# Typography source-law coherence — R13

Defect: the design-system constitution described an Inter-only identity while the canonical theme has long shipped a governed system-first UI stack: San Francisco via system keywords on Apple, self-hosted Inter as the cross-platform carrier, then platform/CJK fallbacks.

Repair: documentation only. The constitution now describes the shipped stack exactly; no theme/font files or product pixels changed.

TDD:
- focused RED: 1 failure before source repair;
- focused GREEN: 1 passed / 102 deselected;
- full tests/test_design_system_foundations.py: 103 passed.

Native follow-up held: the Paper atlas currently projects --font-ui as Inter and the builder template uses a 44px target while repository law/theme use an effective >=40x40 touch floor. Do not mutate Paper until its catalog qualification and file window are both valid.
