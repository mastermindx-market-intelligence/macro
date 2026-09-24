"""Refresh the existing Security State allowlist after Prophet nightly succeeds.

This is not a second Security State producer. It reuses the canonical owner-I/O
helpers and pure security_state.v1 compiler after the Prophet owner has written
its same-run index, then re-renders only the already-enabled ticker dossiers.
The refresh is transactional over the small bounded file set: a compile/render
failure restores the pre-refresh bytes rather than publishing a split surface.
"""
from __future__ import annotations

import argparse
import copy
import json
import logging
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from engine import security_state as ss  # noqa: E402
import engine.neuralweb.company_intelligence_reader as security_state_reader  # noqa: E402
from lib import config  # noqa: E402
from scripts import security_state_producer as producer  # noqa: E402
from scripts import build_ticker_pages  # noqa: E402

ROOT = _ROOT
SITE = ROOT / "site"
log = logging.getLogger("security_state_prophet_refresh")


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.prophet-refresh-{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _snapshot(paths: Iterable[Path]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.exists() else None for path in paths}


def _restore(snapshot: dict[Path, bytes | None]) -> None:
    for path, prior in snapshot.items():
        if prior is None:
            path.unlink(missing_ok=True)
        else:
            _atomic_write(path, prior)


def _without_prophet_delta(state: dict) -> dict:
    """Normalize a Security State so only the Prophet subread may differ.

    The post-checkpoint pass exists solely to connect one newly accepted owner
    read. If recomputing the full canonical object would change any other leg,
    coverage, identity, authority, or evidence, this maintenance pass must
    preserve the prior publication and leave that change to the normal owner.
    """
    normalized = copy.deepcopy(state)
    normalized.pop("generated_at", None)
    normalized.pop("content_sha256", None)
    legs = normalized.get("legs")
    if isinstance(legs, dict):
        opportunity = legs.get("opportunity_context")
        if isinstance(opportunity, dict):
            opportunity["prophet"] = {"_post_checkpoint_prophet_slot": True}
    return normalized


def _assert_prophet_only_delta(*, prior: dict, updated: dict, ticker: str) -> None:
    if _without_prophet_delta(prior) != _without_prophet_delta(updated):
        raise RuntimeError(
            f"security-state Prophet refresh for {ticker} changed non-Prophet state; "
            "preserving prior publication"
        )


def _render_context_html(context: dict) -> str:
    """Render one already-built ticker context through the canonical template."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(
        loader=FileSystemLoader(str(build_ticker_pages.TEMPLATES_DIR)),
        autoescape=True,
    )
    template = env.get_template("ticker.html.j2")
    return template.render(**context)


def _element_span_by_id(html: str, element_id: str) -> tuple[int, int]:
    """Return the exact outer-element span for one unique HTML id.

    Security State markup contains nested sections/divs, so a non-greedy regex
    to the first closing tag is unsafe. This scanner counts only the matching
    tag type and is deliberately limited to the already-rendered static HTML.
    """
    marker = f'id="{element_id}"'
    marker_i = html.find(marker)
    if marker_i < 0:
        raise RuntimeError(f"rendered page has no element id={element_id!r}")
    if html.find(marker, marker_i + len(marker)) >= 0:
        raise RuntimeError(f"rendered page duplicates element id={element_id!r}")

    start = html.rfind("<", 0, marker_i)
    if start < 0:
        raise RuntimeError(f"cannot locate opening tag for id={element_id!r}")
    tag_match = re.match(r"<([A-Za-z][A-Za-z0-9:-]*)\b", html[start:])
    if tag_match is None:
        raise RuntimeError(f"cannot parse opening tag for id={element_id!r}")
    tag = tag_match.group(1)

    token_re = re.compile(rf"</?{re.escape(tag)}\b[^>]*>", re.IGNORECASE)
    depth = 0
    for token in token_re.finditer(html, start):
        raw = token.group(0)
        if raw.startswith("</") or raw.startswith("</".upper()):
            depth -= 1
            if depth == 0:
                return start, token.end()
        elif not raw.rstrip().endswith("/>"):
            depth += 1
    raise RuntimeError(f"unterminated element id={element_id!r}")


def _patch_security_state_html(existing_html: str, rendered_html: str) -> str:
    """Replace only Security State card/dialog fragments, preserving all other bytes."""
    ids = ["security-state"]
    ids.extend(
        match.group(1)
        for match in re.finditer(
            r'\bid="(dlg-ss-[^"]+)"',
            rendered_html,
        )
    )
    if len(ids) < 2:
        raise RuntimeError("rendered Security State produced no drilldown dialogs")

    patched = existing_html
    for element_id in ids:
        new_start, new_end = _element_span_by_id(rendered_html, element_id)
        old_start, old_end = _element_span_by_id(patched, element_id)
        patched = (
            patched[:old_start]
            + rendered_html[new_start:new_end]
            + patched[old_end:]
        )
    return patched


def _render_allowlisted_pages(
    *,
    site: Path,
    page_dir: Path,
    tickers: tuple[str, ...],
) -> None:
    """Render only allowlisted dossier pages with no hub/share-card side effects."""
    with tempfile.TemporaryDirectory(prefix="security-state-prophet-render.") as tmp:
        tmp_root = Path(tmp)
        context_dir = tmp_root / "context"
        rc = build_ticker_pages.run(
            out=tmp_root / "out",
            site=site,
            context_only=True,
            dump_context=context_dir,
            only_tickers=set(tickers),
        )
        if rc != 0:
            raise RuntimeError(f"ticker context refresh returned {rc}")

        rendered: dict[str, bytes] = {}
        for ticker in tickers:
            context_path = context_dir / f"{ticker}.json"
            if not context_path.exists():
                raise RuntimeError(
                    f"ticker context refresh produced no context for {ticker}"
                )
            context = json.loads(context_path.read_text(encoding="utf-8"))
            if not isinstance(context, dict):
                raise RuntimeError(
                    f"ticker context refresh produced invalid context for {ticker}"
                )
            rendered_html = _render_context_html(context)
            existing_path = page_dir / f"{ticker}.html"
            if not existing_path.exists():
                raise RuntimeError(
                    f"security-state refresh has no prior dossier page for {ticker}"
                )
            existing_html = existing_path.read_text(encoding="utf-8")
            patched_html = _patch_security_state_html(existing_html, rendered_html)
            rendered[ticker] = patched_html.encode("utf-8")

        for ticker, html in rendered.items():
            _atomic_write(page_dir / f"{ticker}.html", html)


def refresh(
    *,
    site: Path = SITE,
    data_dir: Path | None = None,
    tickers: tuple[str, ...] = ss.SECURITY_STATE_TICKERS,
    now: str | None = None,
    prophet_index_path: Path | None = None,
) -> list[str]:
    """Recompile the existing allowlisted Security State rows with current Prophet owner truth."""
    data_dir = data_dir or config.data_dir()
    now = now or datetime.now(timezone.utc).isoformat()
    now_date = datetime.fromisoformat(now.replace("Z", "+00:00")).date()

    stockdir = site / "stockdata"
    index_path = stockdir / "index.json"
    prophet_index_path = prophet_index_path or (site / "prophet" / "index.json")
    page_dir = site / "stocks"

    records: dict[str, dict] = {}
    for ticker in tickers:
        path = stockdir / f"{ticker}.json"
        if not path.exists():
            raise FileNotFoundError(f"security-state refresh missing stockdata for {ticker}: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or str(payload.get("ticker") or "").upper() != ticker:
            raise ValueError(f"security-state refresh ticker mismatch for {ticker}")
        records[ticker] = payload

    index = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(index, list):
        raise ValueError("stockdata index must be a list")

    validator = producer._load_security_state_validator(ss.SCHEMA_PATH)
    identities, identity_failures = producer._read_security_state_identity_rows(
        data_dir,
        tickers,
        decision_date=now_date,
    )

    compiled: dict[str, dict] = {}
    for ticker in tickers:
        rec = records[ticker]
        prior_state = rec.get("security_state")
        if not isinstance(prior_state, dict):
            raise RuntimeError(
                f"security-state Prophet refresh has no prior Security State for {ticker}"
            )

        identity = identities.get(ticker)
        if identity is None:
            reason = identity_failures.get(ticker, "owner identity unavailable")
            raise RuntimeError(
                f"security-state Prophet refresh identity unavailable for {ticker}: {reason}"
            )

        owner_read = producer._read_prophet_owner_read(prophet_index_path, ticker)
        updated_state = producer._compile_security_state_for_ticker(
            ticker,
            rec,
            now=now,
            identity=identity,
            validator=validator,
            find_event_id=security_state_reader.find_current_event_id_for_company,
            load_workspace=security_state_reader.load_workspace_with_disposition,
            fetch_manifest=security_state_reader.fetch_generation_manifest,
            prophet_owner_read=owner_read,
        )
        _assert_prophet_only_delta(
            prior=prior_state,
            updated=updated_state,
            ticker=ticker,
        )
        compiled[ticker] = updated_state

    affected = [
        *(stockdir / f"{ticker}.json" for ticker in tickers),
        index_path,
        *(page_dir / f"{ticker}.html" for ticker in tickers),
    ]
    prior = _snapshot(affected)

    try:
        for ticker, state in compiled.items():
            rec = records[ticker]
            rec["security_state"] = state
            _atomic_write(
                stockdir / f"{ticker}.json",
                json.dumps(rec, default=str).encode("utf-8"),
            )
            index_row_found = False
            for row in index:
                if isinstance(row, dict) and row.get("t") == ticker:
                    row["security_state"] = {
                        "overall_state": state["coverage"]["overall_state"],
                        "dominant_degradation": state["dominant_degradation"],
                        "generated_at": state["generated_at"],
                    }
                    index_row_found = True
                    break
            if not index_row_found:
                raise RuntimeError(
                    f"security-state refresh stockdata index has no row for {ticker}"
                )
        _atomic_write(index_path, json.dumps(index).encode("utf-8"))

        _render_allowlisted_pages(
            site=site,
            page_dir=page_dir,
            tickers=tickers,
        )
    except Exception:
        _restore(prior)
        raise

    return list(tickers)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Refresh the existing Security State allowlist from one accepted Prophet index."
    )
    parser.add_argument(
        "--prophet-index",
        type=Path,
        default=None,
        help="Accepted Prophet index to consume (default: site/prophet/index.json).",
    )
    args = parser.parse_args(argv)

    refreshed = refresh(prophet_index_path=args.prophet_index)
    print(
        "::notice title=security-state Prophet refresh::updated "
        + ", ".join(refreshed),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    from lib.procutil import hard_exit

    hard_exit(main())
