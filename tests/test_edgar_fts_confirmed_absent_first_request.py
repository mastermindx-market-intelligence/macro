"""The first-request abort guard in the three EDGAR full-text-search sweeps must fire on
``collectors.edgar_facts._CONFIRMED_ABSENT`` exactly as it fires on ``None``.

#6921 changed ``edgar_facts._get_json`` to return a falsy-but-not-``None`` sentinel on a
confirmed SEC 404. ``collectors.edgar_fts._sweep_phrases``,
``collectors.edgar_emergence.fetch_emergence_hits`` and
``collectors.edgar_guidance.fetch_guidance_hits`` all import that ``_get_json`` and guard
their VERY FIRST call with an identity check so a genuine outage aborts the whole sweep
instead of grinding through one ~40s timeout per phrase and page. ``_CONFIRMED_ABSENT is
None`` is ``False``, so with the old ``data is None`` guard a confirmed 404 on the first
call fell through and the sweep made one request per phrase.

No network: ``_get_json`` is replaced at the module each collector imported it into.
Each collector re-exports the sentinel it compares against (falling back to ``None`` while
edgar_facts predates #6921, where a confirmed 404 IS plain ``None``), and the identity
assertion below pins that re-export to ``edgar_facts`` so the guard can never drift onto
a private look-alike object.
"""
from __future__ import annotations

import pytest

from collectors import edgar_emergence, edgar_facts, edgar_fts, edgar_guidance
from lib import config

_FTS_PHRASES = ["supply constraint", "on allocation", "sold out"]
_EMERGENCE_PHRASES = list(edgar_emergence.SCARCITY_PHRASES[:3])
_GUIDANCE_PHRASES = list(edgar_guidance.RAISE_PHRASES[:2]) + list(edgar_guidance.CUT_PHRASES[:1])

# (module the collector imported _get_json into, sweep runner, number of phrases swept)
SWEEPS = [
    pytest.param(
        edgar_fts,
        lambda tmp: edgar_fts._sweep_phrases(_FTS_PHRASES, {"AAPL"}, tmp / "fts.parquet",
                                             force=True),
        len(_FTS_PHRASES),
        id="edgar_fts",
    ),
    pytest.param(
        edgar_emergence,
        lambda tmp: edgar_emergence.fetch_emergence_hits(force=True,
                                                         phrases=_EMERGENCE_PHRASES),
        len(_EMERGENCE_PHRASES),
        id="edgar_emergence",
    ),
    pytest.param(
        edgar_guidance,
        lambda tmp: edgar_guidance.fetch_guidance_hits(force=True, phrases=_GUIDANCE_PHRASES),
        len(_GUIDANCE_PHRASES),
        id="edgar_guidance",
    ),
]


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    # cache parquets / mkdirs go to tmp_path, never the repo's data/ tree
    monkeypatch.setattr(config, "data_dir", lambda: tmp_path)
    # guidance returns before its first request on an empty theme universe
    monkeypatch.setattr(edgar_guidance, "_theme_universe", lambda: {"AAPL"})


def _install_fake_get_json(monkeypatch, mod, payloads):
    """Replace ``mod._get_json`` with a recorder yielding ``payloads`` in order (the last
    one repeats). Returns the list of requested URLs."""
    calls: list[str] = []

    def fake(url, retries=3):
        calls.append(url)
        i = min(len(calls) - 1, len(payloads) - 1)
        return payloads[i]

    monkeypatch.setattr(mod, "_get_json", fake)
    return calls


@pytest.mark.parametrize("mod, run, n_phrases", SWEEPS)
def test_sentinel_is_the_one_edgar_facts_returns(mod, run, n_phrases):
    assert mod._CONFIRMED_ABSENT is getattr(edgar_facts, "_CONFIRMED_ABSENT", None)


@pytest.mark.parametrize("mod, run, n_phrases", SWEEPS)
def test_confirmed_absent_on_first_request_aborts_the_sweep(monkeypatch, tmp_path, mod, run,
                                                            n_phrases):
    assert n_phrases > 1  # otherwise "one call" and "one call per phrase" coincide
    calls = _install_fake_get_json(monkeypatch, mod, [mod._CONFIRMED_ABSENT])
    assert run(tmp_path) is None  # no pre-existing cache to fall back to
    assert len(calls) == 1, f"sweep did not abort: {len(calls)} calls for {n_phrases} phrases"


@pytest.mark.parametrize("mod, run, n_phrases", SWEEPS)
def test_none_on_first_request_still_aborts_the_sweep(monkeypatch, tmp_path, mod, run,
                                                      n_phrases):
    calls = _install_fake_get_json(monkeypatch, mod, [None])
    assert run(tmp_path) is None
    assert len(calls) == 1


@pytest.mark.parametrize("mod, run, n_phrases", SWEEPS)
def test_confirmed_absent_after_first_request_does_not_abort(monkeypatch, tmp_path, mod, run,
                                                             n_phrases):
    # The widening is scoped to the FIRST request: a later confirmed 404 is an empty page
    # for that phrase (fall through, break to the next phrase), never an outage abort.
    empty_page = {"hits": {"hits": []}}
    calls = _install_fake_get_json(monkeypatch, mod, [empty_page, mod._CONFIRMED_ABSENT])
    assert run(tmp_path) is None  # no hits -> no cache written -> None
    assert len(calls) == n_phrases
