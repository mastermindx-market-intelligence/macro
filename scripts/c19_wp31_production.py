"""C19 WP31 evaluator — PRODUCTION ADAPTERS (wave-3 spec §1).

Governing documents
-------------------
- Preregistration: ``research/C19_WP31_INCREMENTAL_INFORMATION_PREREG.md``
  at PREREG_COMMIT ``8e1950932b29f89a89da94c50ccef4ef5f2d8d1c`` (the
  registered design).  Sections 3 (sources), 6 (sample dependence /
  exposure) and 9 (owners / natural clock) bind this module: the
  prereg wins any conflict with the build spec; never redesign, never
  widen.
- Frozen wave-3 build spec: ``WP31_WAVE3_SPEC.md`` (seat stage),
  sha256 ``8b3cf32fab638a106921be7ae860a24b6892e71be75d3970eee1702fd31c56fe``.

This module is the production half of wave 3.  The runner
(:func:`scripts.c19_wp31_runner.run_evaluation`) is the injected-I/O
read; it never imports collectors, query_k3e, or anything that
opens the network.  ``ProductionInputs`` builds every injected
input of the runner from the EXISTING incumbents:

  - submissions (page0 + shards) and Item-2.02 8-K rows come from
    ``collectors.edgar_earnings_8k`` (``_sec_get_json``,
    ``_extract_8k_rows``; the submissions URL is its own
    :data:`SUBMISSIONS_URL` constant);
  - the filing-index manifest comes from
    ``collectors.edgar_8k._fetch_doc_text`` (requesting only the
    ``-index-headers.html`` page — never an exhibit body);
  - Company Facts come from
    :class:`collectors.fundamental_forensics_companyfacts.SecCompanyFactsCollector`,
    whose User-Agent is read from ``config.yml::edgar.user_agent``
    (the SAME key ``collectors.edgar_forensics._user_agent`` reads;
    we re-read it with ``yaml`` — we do not import that incumbent);
  - the K surface comes from
    ``scripts.query_k3e_expectation_surface.load_frozen_source`` and
    ``...load_frozen_aliases``, both loaded once per HEAD revision.

Every incumbent import is LAZY (inside the function that uses it),
so importing this module performs no network call, no file read and
no heavy import (spec R7; prereg §9: "no new collector, no schedule").
Standard library + ``yaml`` only at module level; pandas / pyarrow /
requests enter only via the lazy call paths.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

__all__ = ["UNIVERSE_CIK", "ProductionInputs"]


# ---------------------------------------------------------------------------
# 1.1  UNIVERSE_CIK  (literal; comments cite the source files but we do NOT
#      import them — keep the CI import closure small).
# ---------------------------------------------------------------------------

UNIVERSE_CIK: dict[str, str] = {
    "AAPL": "0000320193",   # engine/security_state.py PINNED_CIK
    "DHI":  "0000882184",   # engine/company_intelligence/issuer_profiles.py DHI_CIK
    "PHM":  "0000822416",   # issuer_profiles.py PHM_CIK
    "KBH":  "0000795266",   # issuer_profiles.py KBH_CIK
    "TOL":  "0000794170",   # issuer_profiles.py TOL_CIK
}

_HEAD_RE = re.compile(r"^[0-9a-f]{40}$")


# ---------------------------------------------------------------------------
# 1.2  ProductionInputs
# ---------------------------------------------------------------------------


def _resolve_user_agent(repo: Path) -> str:
    """Read ``config.yml::edgar.user_agent``; mirrors ``collectors/edgar_forensics._user_agent``.

    Empty or missing -> ``ValueError`` (spec §1.2: the default client UA must
    come from the same key the incumbent reads; an empty value is a hard
    refusal, not a silent default).
    """
    cfg_path = repo / "config.yml"
    with cfg_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}
    edgar = cfg.get("edgar") or {}
    ua = str(edgar.get("user_agent") or "").strip()
    if not ua:
        raise ValueError("config.yml edgar.user_agent is required")
    return ua


@dataclass
class ProductionInputs:
    """The full set of injected inputs that :func:`c19_wp31_runner.run_evaluation` consumes.

    Every production dependency is an OPTIONAL keyword-only constructor
    argument with a sensible default that resolves the incumbent lazily at
    call time; tests inject their own (spec §1.2 / R2).  The class carries
    no module-level network or file read — all of that happens behind the
    callables.
    """

    repo: Path
    now: datetime

    sec_get_json: Callable[[str], Any] | None = None
    extract_8k_rows: Callable[[str, int, Mapping[str, Any]], list[dict[str, Any]]] | None = None
    fetch_doc_text: Callable[..., Any] | None = None
    companyfacts_client: Any | None = None
    k3e_load_source: Callable[..., Any] | None = None
    k3e_load_aliases: Callable[..., Any] | None = None
    git_runner: Callable[..., subprocess.CompletedProcess] | None = None

    pace_seconds: float = 0.12
    sleeper: Callable[[float], Any] = time.sleep

    counts: dict[str, int] = field(default_factory=dict)

    # ------------------------------------------------------------------ ctor

    def __post_init__(self) -> None:
        if self.now.tzinfo is None or self.now.utcoffset() != timezone.utc.utcoffset(self.now):
            # Accept any tz-aware datetime that resolves to UTC; reject naive.
            if self.now.tzinfo is None:
                raise ValueError("now must be timezone-aware (UTC)")
            if self.now.utcoffset() != timedelta(0):
                raise ValueError("now must be in UTC (offset zero)")
        self._head_revision_cache: str | None = None
        self._submissions_cache: dict[str, list[dict[str, Any]]] = {}
        self._companyfacts_cache: dict[str, Any] = {}
        self._k_load_failed: bool | None = None
        self._k_obs_attempts_prov: tuple | None = None
        self._k_aliases: tuple | None = None
        # Counters the runner/CLI/audit read.
        for key in (
            "submissions_requests",
            "submissions_shards_missing",
            "submissions_unavailable",
            "companyfacts_requests",
            "companyfacts_unavailable",
            "k_inputs_unavailable",
            "k_inputs_requests",
            "index_headers_requests",
        ):
            self.counts.setdefault(key, 0)

    # ----------------------------------------------------- lazy incumbents

    def _sec_get_json(self) -> Callable[[str], Any]:
        if self.sec_get_json is not None:
            return self.sec_get_json
        from collectors import edgar_earnings_8k as e8k
        return e8k._sec_get_json  # type: ignore[return-value]

    def _extract_8k_rows(self) -> Callable[[str, int, Mapping[str, Any]], list[dict[str, Any]]]:
        if self.extract_8k_rows is not None:
            return self.extract_8k_rows
        from collectors import edgar_earnings_8k as e8k
        return e8k._extract_8k_rows  # type: ignore[return-value]

    def _fetch_doc_text(self) -> Callable[..., Any]:
        if self.fetch_doc_text is not None:
            return self.fetch_doc_text
        from collectors import edgar_8k as ed8k
        return ed8k._fetch_doc_text  # type: ignore[return-value]

    def _k3e_load_source(self) -> Callable[..., Any]:
        if self.k3e_load_source is not None:
            return self.k3e_load_source
        from scripts import query_k3e_expectation_surface as qk3
        return qk3.load_frozen_source  # type: ignore[return-value]

    def _k3e_load_aliases(self) -> Callable[..., Any]:
        if self.k3e_load_aliases is not None:
            return self.k3e_load_aliases
        from scripts import query_k3e_expectation_surface as qk3
        return qk3.load_frozen_aliases  # type: ignore[return-value]

    def _companyfacts_client(self) -> Any:
        if self.companyfacts_client is not None:
            return self.companyfacts_client
        from collectors import fundamental_forensics_companyfacts as fcfc
        return fcfc.SecCompanyFactsCollector(user_agent=_resolve_user_agent(self.repo))

    def _git_runner(self) -> Callable[..., subprocess.CompletedProcess]:
        if self.git_runner is not None:
            return self.git_runner

        def _run(args: list[str]) -> subprocess.CompletedProcess:
            return subprocess.run(  # noqa: S603 — argv list, cwd=repo, no shell
                ["git", *args],
                cwd=str(self.repo),
                capture_output=True,
                text=False,
                check=False,
                shell=False,
            )

        return _run

    # ----------------------------------------------------------------- 1.2a

    def doc_bytes(self) -> bytes:
        from scripts import c19_wp31_gates as gates
        return (self.repo / gates.PREREG_DOC).read_bytes()

    def is_ancestor_of_head(self, commit: str) -> bool:
        run = self._git_runner()
        proc = run(["merge-base", "--is-ancestor", commit, "HEAD"])
        if proc.returncode == 0:
            return True
        if proc.returncode == 1:
            return False
        raise RuntimeError(
            f"git merge-base --is-ancestor rc={proc.returncode} stderr={proc.stderr!r}"
        )

    def ledger_lines(self) -> list[str]:
        path = self.repo / "data" / "trial_ledger.jsonl"
        if not path.exists():
            return []
        return path.read_text(encoding="utf-8").splitlines()

    def head_revision(self) -> str:
        if self._head_revision_cache is not None:
            return self._head_revision_cache
        proc = self._git_runner()(["rev-parse", "HEAD"])
        sha = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
        if not _HEAD_RE.fullmatch(sha):
            raise ValueError(f"HEAD is not 40 lowercase hex: {sha!r}")
        self._head_revision_cache = sha
        return sha

    # ----------------------------------------------------------------- 1.2b

    def _submissions(self, ticker: str) -> list[dict[str, Any]]:
        if ticker in self._submissions_cache:
            return self._submissions_cache[ticker]
        cik = UNIVERSE_CIK[ticker]
        sec_get_json = self._sec_get_json()
        from collectors import edgar_earnings_8k as e8k

        url = e8k.SUBMISSIONS_URL.format(int(cik))
        try:
            page0 = sec_get_json(url)
            self.counts["submissions_requests"] += 1
            self.sleeper(self.pace_seconds)
        except Exception:
            self.counts["submissions_unavailable"] += 1
            self._submissions_cache[ticker] = []
            return []

        if page0 is None:
            self.counts["submissions_unavailable"] += 1
            self._submissions_cache[ticker] = []
            return []

        pages: list[dict[str, Any]] = [page0]
        older_files = (page0.get("filings") or {}).get("files") or []
        for entry in older_files:
            fname = entry.get("name") if isinstance(entry, Mapping) else None
            if not fname:
                continue
            older_url = f"https://data.sec.gov/submissions/{fname}"
            try:
                shard = sec_get_json(older_url)
                self.counts["submissions_requests"] += 1
                self.sleeper(self.pace_seconds)
            except Exception:
                self.counts["submissions_shards_missing"] += 1
                continue
            if shard is None:
                self.counts["submissions_shards_missing"] += 1
                continue
            pages.append(shard)

        self._submissions_cache[ticker] = pages
        return pages

    def filing_rows(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        extract = self._extract_8k_rows()
        for ticker in sorted(UNIVERSE_CIK):
            cik = UNIVERSE_CIK[ticker]
            pages = self._submissions(ticker)
            for page in pages:
                filings = page.get("filings") if isinstance(page, Mapping) else None
                rec = (filings or {}).get("recent") if isinstance(filings, Mapping) else None
                if rec is None:
                    rec = page if isinstance(page, Mapping) else None
                if rec is None:
                    continue
                rows.extend(extract(ticker, int(cik), rec))
        return rows

    def submissions_pages(self, issuer: str) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._submissions(issuer))

    # ----------------------------------------------------------------- 1.2c

    def fetch_index_headers(self, cik: Any, accession: Any) -> str | None:
        from collectors import edgar_earnings_8k as _e8k
        # The normalize helper in collectors/edgar_earnings_8k already
        # produces the dashed 10-2-6 form (same one the index-headers URL
        # carries).  The nodash form is the same minus dashes.
        dashed = _e8k._normalize_accession(accession)
        if not dashed:
            return None
        nodash = dashed.replace("-", "")
        fetch = self._fetch_doc_text()
        self.counts["index_headers_requests"] += 1
        try:
            text = fetch(int(cik), nodash, f"{dashed}-index-headers.html", strip=False)
        except Exception:
            return None
        if not isinstance(text, str):
            return None
        return text

    def companyfacts(self, issuer: str) -> Any:
        if issuer in self._companyfacts_cache:
            return self._companyfacts_cache[issuer]
        from collectors import fundamental_forensics_companyfacts as fcfc
        cik = UNIVERSE_CIK[issuer]
        client = self._companyfacts_client()
        self.counts["companyfacts_requests"] += 1
        try:
            body, _meta = client.fetch(cik, max_response_bytes=fcfc.DEFAULT_MAX_RESPONSE_BYTES)
        except (fcfc.CompanyFactsAcquisitionError, ValueError, OSError):
            self.counts["companyfacts_unavailable"] += 1
            self._companyfacts_cache[issuer] = None
            return None
        try:
            data = json.loads(body)
        except ValueError:
            self.counts["companyfacts_unavailable"] += 1
            self._companyfacts_cache[issuer] = None
            return None
        self._companyfacts_cache[issuer] = data
        return data

    # ----------------------------------------------------------------- 1.2d

    def _load_k(self) -> None:
        """Load the frozen K source + aliases ONCE per HEAD revision.

        ``k_inputs_unavailable`` is sticky: if either loader raises, every
        subsequent ``k_inputs`` returns ``None`` (spec §1.2 bullet 7).
        """
        if self._k_load_failed is True:
            return
        if self._k_obs_attempts_prov is not None and self._k_aliases is not None:
            return
        head = self.head_revision()
        try:
            obs, attempts, prov = self._k3e_load_source()(self.repo, head)
            aliases, alias_entry = self._k3e_load_aliases()(self.repo, head)
        except Exception:
            self._k_load_failed = True
            self.counts["k_inputs_unavailable"] += 1
            return
        self._k_obs_attempts_prov = (obs, attempts, prov)
        self._k_aliases = (aliases, alias_entry)

    def k_inputs(self, issuer: str, cutoff: datetime, period_end: str) -> dict[str, Any] | None:
        if self._k_load_failed is True:
            self.counts["k_inputs_unavailable"] += 1
            return None
        if self._k_obs_attempts_prov is None:
            self._load_k()
        if self._k_load_failed is True or self._k_obs_attempts_prov is None:
            self.counts["k_inputs_unavailable"] += 1
            return None
        self.counts["k_inputs_requests"] += 1
        obs, attempts, prov = self._k_obs_attempts_prov
        aliases, alias_entry = self._k_aliases  # type: ignore[misc]
        kw: dict[str, Any] = dict(
            observations=obs,
            attempts=attempts,
            cutoff=cutoff,
            period_end=period_end,
            source_provenance=prov,
            ticker=issuer,
        )
        if not (isinstance(alias_entry, Mapping) and alias_entry.get("absent_at_revision")):
            kw["identity_aliases"] = aliases
        return kw

    # ----------------------------------------------------------------- 1.2e

    def run_kwargs(self, exposure_path: Any, prior_reads: Sequence[Mapping[str, Any]] = ()
                   ) -> dict[str, Any]:
        return dict(
            doc_bytes=self.doc_bytes(),
            is_ancestor_of_head=self.is_ancestor_of_head,
            ledger_lines=self.ledger_lines(),
            filing_rows=self.filing_rows(),
            fetch_index_headers=self.fetch_index_headers,
            k_inputs=self.k_inputs,
            companyfacts=self.companyfacts,
            submissions_pages=self.submissions_pages,
            exposure_path=exposure_path,
            now=self.now,
            prior_reads=tuple(prior_reads),
            resolve_ticker=None,    # incumbent identity resolver
            revisions_reader=None,  # incumbent revision chain reader
            max_hops=500,
        )