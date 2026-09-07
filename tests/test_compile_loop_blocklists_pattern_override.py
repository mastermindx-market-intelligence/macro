"""tests/test_compile_loop_blocklists_pattern_override.py

PR #6925 review round 1, MAJOR-1 (ruling r4, amended): scripts/compile_loop_blocklists.py
gains an optional per-row `patterns:` override — read from the hand-curated
`pattern_overrides:` map in config/signal_foundry_blocklist.yml ("the blocklist
source it reads" per the ruling's alternative clause) — that the compiler emits
VERBATIM as a BL entry's `any_of`, replacing the derived three-word signature
when a matching DNR Key is present.

The bug this closes: `_topic_to_pattern` joins up to three >=4-char words from
the topic with `.{0,30}` (a conjunctive pattern), which cannot match a proposer
who writes just one of several forbidden phrasings on its own. Falsified live
at b283b69a: BL-G099's derived `any_of` was `['keyed.{0,30}webhook.{0,30}quota']`,
which matches none of "api key", "api_key", "public api", "webhook", "second
quota meter", or "keyed endpoint" written standalone.

All tests HERMETIC (tmp_path) except the final one, which pins the real
committed config/signal_foundry_blocklist.yml against the six ruling phrasings
per the reviewer's own instruction ("run the six phrasings through the
compiled blocklist").
"""
from __future__ import annotations

import importlib.util
import re
import textwrap
from pathlib import Path

import yaml


def _repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _load_compiler():
    path = _repo_root() / "scripts" / "compile_loop_blocklists.py"
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


FIXTURE_MD = textwrap.dedent("""\
    # DO NOT REBUILD

    ## 3. Wrong-ruler / estimator laws (methodology — using these invalidates the study)

    | Key | Topic | Verdict | Ruling / source |
    |---|---|---|---|
    | LAW-FIXTURE-OVERRIDE | Some override-eligible topic phrase here | FORBIDDEN | fixture source |
    | LAW-FIXTURE-DERIVED | Some derived-signature topic phrase here | FORBIDDEN | fixture source |
""")


class TestPatternOverrideVerbatimEmission:
    def _setup_tmp_repo(self, tmp_path: Path, sf_prefix: str = "") -> None:
        (tmp_path / "research").mkdir()
        (tmp_path / "config").mkdir()
        (tmp_path / "scripts").mkdir()
        (tmp_path / "research" / "DO_NOT_REBUILD.md").write_text(FIXTURE_MD, encoding="utf-8")
        if sf_prefix:
            (tmp_path / "config" / "signal_foundry_blocklist.yml").write_text(
                sf_prefix, encoding="utf-8"
            )

    def test_no_override_falls_back_to_derived_signature(self, tmp_path: Path) -> None:
        """Without a pattern_overrides entry, behavior is unchanged (derived
        three-word signature)."""
        self._setup_tmp_repo(tmp_path)
        compiler = _load_compiler()
        rc = compiler.compile_blocklists(tmp_path)
        assert rc == 0
        sf = tmp_path / "config" / "signal_foundry_blocklist.yml"
        data = yaml.safe_load(sf.read_text(encoding="utf-8"))
        entries = {e["id"]: e for e in data["entries"]}
        assert len(entries) == 2
        for entry in entries.values():
            any_of = entry["match"]["any_of"]
            assert len(any_of) == 1
            assert ".{0,30}" in any_of[0]  # the derived-signature shape

    def test_override_emitted_verbatim_replaces_derived_signature(self, tmp_path: Path) -> None:
        """A pattern_overrides entry keyed by DNR Key replaces that entry's
        any_of with the override list VERBATIM — the other (unkeyed) entry
        in the same run still gets the derived signature."""
        sf_prefix = textwrap.dedent("""\
            pattern_overrides:
              LAW-FIXTURE-OVERRIDE:
                - '\\bfoo bar\\b'
                - '\\bbaz_qux\\b'
                - 'literal-no-boundary'

            entries:
        """)
        self._setup_tmp_repo(tmp_path, sf_prefix=sf_prefix)
        compiler = _load_compiler()
        rc = compiler.compile_blocklists(tmp_path)
        assert rc == 0
        sf = tmp_path / "config" / "signal_foundry_blocklist.yml"
        data = yaml.safe_load(sf.read_text(encoding="utf-8"))
        entries = {e["id"]: e for e in data["entries"]}
        assert len(entries) == 2

        overridden = next(e for e in entries.values() if e["match"]["any_of"] == [
            r"\bfoo bar\b", r"\bbaz_qux\b", "literal-no-boundary",
        ])
        # Exact verbatim round-trip — no transformation, no truncation.
        assert overridden["match"]["any_of"] == [
            r"\bfoo bar\b",
            r"\bbaz_qux\b",
            "literal-no-boundary",
        ]

        derived = next(
            e for e in entries.values() if e["match"]["any_of"] != overridden["match"]["any_of"]
        )
        assert ".{0,30}" in derived["match"]["any_of"][0]

    def test_override_survives_a_second_compile_pass(self, tmp_path: Path) -> None:
        """The override lives in the hand-curated header, above the generated
        marker, so recompiling twice does not lose or duplicate it."""
        sf_prefix = textwrap.dedent("""\
            pattern_overrides:
              LAW-FIXTURE-OVERRIDE:
                - '\\bsolo\\b'

            entries:
        """)
        self._setup_tmp_repo(tmp_path, sf_prefix=sf_prefix)
        compiler = _load_compiler()
        compiler.compile_blocklists(tmp_path)
        compiler.compile_blocklists(tmp_path)
        sf = tmp_path / "config" / "signal_foundry_blocklist.yml"
        text = sf.read_text(encoding="utf-8")
        assert text.count("pattern_overrides:") == 1
        data = yaml.safe_load(text)
        entries = {e["id"]: e for e in data["entries"]}
        overridden = next(e for e in entries.values() if e["match"]["any_of"] == [r"\bsolo\b"])
        assert overridden["match"]["any_of"] == [r"\bsolo\b"]

    def test_missing_or_malformed_overrides_never_raise(self, tmp_path: Path) -> None:
        """No signal_foundry_blocklist.yml yet, or a non-dict pattern_overrides,
        must not crash the compiler — first-run and malformed-hand-edit cases."""
        self._setup_tmp_repo(tmp_path)  # no sf file at all
        compiler = _load_compiler()
        assert compiler.compile_blocklists(tmp_path) == 0

        sf = tmp_path / "config" / "signal_foundry_blocklist.yml"
        sf.write_text("pattern_overrides: 'not a dict'\nentries:\n", encoding="utf-8")
        assert compiler.compile_blocklists(tmp_path) == 0


class TestRealBlG099MatchesTheSixRulingPhrasings:
    """Pins the ACTUAL committed config/signal_foundry_blocklist.yml — the
    reviewer's own falsification instruction: 'run the six phrasings through
    the compiled blocklist.' Mirrors engine/signal_foundry/screen.py's match
    (`re.search(pattern, text, re.IGNORECASE)`)."""

    PHRASINGS = [
        "api key",
        "api_key",
        "public api",
        "webhook",
        "second quota meter",
        "keyed endpoint",
    ]

    def _bl_g099_any_of(self):
        sf_path = _repo_root() / "config" / "signal_foundry_blocklist.yml"
        data = yaml.safe_load(sf_path.read_text(encoding="utf-8"))
        entry = next(e for e in data["entries"] if e["id"] == "BL-G099")
        return entry["match"]["any_of"]

    def test_each_phrasing_matches_standalone(self):
        any_of = self._bl_g099_any_of()
        for phrase in self.PHRASINGS:
            text = f"we would like to add {phrase} to the product"
            hit = any(re.search(pat, text, re.IGNORECASE) for pat in any_of)
            assert hit, f"{phrase!r} did not match any BL-G099 pattern {any_of}"

    def test_each_phrasing_matches_case_insensitively(self):
        any_of = self._bl_g099_any_of()
        for phrase in self.PHRASINGS:
            text = f"PROPOSAL: {phrase.upper()} SUPPORT"
            hit = any(re.search(pat, text, re.IGNORECASE) for pat in any_of)
            assert hit, f"{phrase!r} (uppercased) did not match any BL-G099 pattern {any_of}"

    def test_old_conjunctive_signature_is_gone(self):
        """The pre-fix derived signature required all three of keyed/webhook/
        quota within a 90-char span — it must no longer be the only pattern."""
        any_of = self._bl_g099_any_of()
        assert any_of != ["keyed.{0,30}webhook.{0,30}quota"]
