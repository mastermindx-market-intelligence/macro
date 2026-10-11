---
key: A-BYTE-BUDGET-IS-WRONG-UNLESS-ITS-UNIT-IS-FIXED
claim: >
  A payload budget advertised to a responder must be the largest value that can still be
  RENDERED, and the escape expansion factor that bounds it depends entirely on whether the budget
  is denominated in bytes or characters. Measured 2026-09-25 on Mastermind
  `common/agent_dialogue_consultation_contract.py` at `87117418`: `clamp_response_budget`
  advertised `MAX_FRAME_BYTES - overhead = 2482` bytes, and a responder spending exactly those
  2,482 bytes on an all-backslash answer produced a 6,981-byte frame - 2,481 over a 4,500-byte
  ceiling. The largest text that actually fits is 1,241 bytes, and `(ceiling - overhead) // 2 =
  1241` is EXACTLY tight (1,241 renders to 4,499; 1,242 renders to 4,501). The factor is 2 and not
  more because the canonical encoder uses `ensure_ascii=False`, so only `"` and `\` expand, and
  because the string validator rejects every character with `ord(c) < 32 or ord(c) == 127` - so
  control characters, whose `\u00XX` escape would cost 6, are IMPOSSIBLE in a validated payload.
falsifier: >
  For each of `\`, `"`, an ASCII character, a CJK character and an astral character, build a text
  whose UTF-8 length equals the advertised budget and render the frame. If every one fits the
  ceiling, the clamp is sound for a byte-denominated budget. Measured largest fitting text, in
  UTF-8 bytes: backslash 1,241 - quote 1,241 - ASCII 2,483 - CJK 2,481 - astral 2,480. The
  non-ASCII cases are NOT the worst case under `ensure_ascii=False`.
so_what: >
  Fix the unit in the name and prove it with a non-ASCII discriminator, because the same budget is
  8x wrong under the other reading: in CHARACTERS an astral character is 4 UTF-8 bytes times the 2x
  escape. A byte-denominated budget needs no CJK or astral special case; a character-denominated
  one cannot be correct without them. Two traps this cost: (1) reasoning about "the second JSON
  encoding" without first identifying WHICH pass is load-bearing - a nested object is escaped once,
  and the doubly-escaped quantity is a different helper with a different ceiling; and (2) deriving
  an expansion bound from encoder flags alone, when a VALIDATOR upstream has already made the
  expensive characters unreachable.
kind: law
verified_at: 2026-09-25
verified_by: >
  Executed probes against Mastermind `87117418`: `_require_string` rejects newline, NUL, DEL,
  empty and untrimmed text (all `MESSAGE_INVALID`); binary search for the largest rendering text
  per character class gave the five figures above; `(4500-2018)//2 = 1241` admits 1,241 and refuses
  1,242. A 14-test instrument written before the repair failed exactly the two clamp falsifiers and
  passed all nine controls.
scope:
  - common/agent_dialogue_consultation_contract.py
  - any advertised payload or response budget
  - JSON escape-expansion reasoning
confidence: verified
---

The instructive part is that the obvious repair - subtract the overhead from the ceiling - is
already an improvement over no clamp at all, and it still fails. A budget that is *closer* to
right is not right: the responder is entitled to spend every byte it is offered.
