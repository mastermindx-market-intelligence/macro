"""PDF → Markdown abstraction supporting Marker, MinerU, and a no-op fallback."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import ParseResult, Status
from .utils import get_logger

logger = get_logger("parse_pdf")


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseParser(ABC):
    name: str

    @abstractmethod
    def to_markdown(self, pdf_path: Path) -> tuple[str, dict[str, Any]]:
        """Return (markdown_text, extra) where extra may include {'page_count': int}."""


# ---------------------------------------------------------------------------
# Cheap page-count helper (no deps)
# ---------------------------------------------------------------------------

def _cheap_page_count(pdf_path: Path) -> int | None:
    """Count b'/Type' … b'/Page' patterns in raw bytes; best-effort, None if unsure."""
    try:
        data = pdf_path.read_bytes()
        # PDF spec: /Type /Page (may have whitespace between them)
        import re
        count = len(re.findall(rb"/Type\s*/Page[^s]", data))
        return count if count > 0 else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Concrete parsers
# ---------------------------------------------------------------------------

class MarkerParser(BaseParser):
    """Marker (datalab-to/marker) PDF->Markdown.

    Supports both the modern ``marker-pdf>=1.0`` API (``PdfConverter`` /
    ``create_model_dict`` / ``text_from_rendered``) and the legacy ``<1.0`` API
    (``convert_single_pdf`` / ``load_all_models``). The (expensive) model set is
    loaded once per process and cached on the class, so parsing many PDFs in one
    run does not reload models each time.
    """

    name = "marker"
    _models: Any = None  # process-wide model cache (class attribute)

    def to_markdown(self, pdf_path: Path) -> tuple[str, dict[str, Any]]:
        # Prefer the modern (>=1.0) API; fall back to legacy only on ImportError.
        try:
            import marker.converters.pdf  # noqa: F401 — presence check for modern API
            modern = True
        except ImportError:
            modern = False

        try:
            if modern:
                return self._convert_modern(pdf_path)
            return self._convert_legacy(pdf_path)
        except ImportError as exc:
            logger.warning(
                "marker not installed (%s); falling back to noop for this call", exc
            )
            return "", {"page_count": _cheap_page_count(pdf_path)}

    def _convert_modern(self, pdf_path: Path) -> tuple[str, dict[str, Any]]:
        from marker.converters.pdf import PdfConverter  # type: ignore
        from marker.models import create_model_dict  # type: ignore
        from marker.output import text_from_rendered  # type: ignore

        if MarkerParser._models is None:
            MarkerParser._models = create_model_dict()
        converter = PdfConverter(artifact_dict=MarkerParser._models)
        rendered = converter(str(pdf_path))
        text, _, _images = text_from_rendered(rendered)

        page_count: int | None = None
        meta = getattr(rendered, "metadata", None)
        if isinstance(meta, dict):
            stats = meta.get("page_stats")
            if isinstance(stats, list):
                page_count = len(stats)
        if page_count is None:
            page_count = _cheap_page_count(pdf_path)
        return (text or ""), {"page_count": page_count}

    def _convert_legacy(self, pdf_path: Path) -> tuple[str, dict[str, Any]]:
        from marker.convert import convert_single_pdf  # type: ignore
        from marker.models import load_all_models  # type: ignore

        if MarkerParser._models is None:
            MarkerParser._models = load_all_models()
        full_text, _images, out_meta = convert_single_pdf(str(pdf_path), MarkerParser._models)
        page_count = out_meta.get("page_count") if isinstance(out_meta, dict) else None
        if page_count is None:
            page_count = _cheap_page_count(pdf_path)
        return (full_text or ""), {"page_count": page_count}


class MinerUParser(BaseParser):
    name = "mineru"

    def to_markdown(self, pdf_path: Path) -> tuple[str, dict[str, Any]]:
        try:
            from magic_pdf.data.data_reader_writer import FileBasedDataWriter  # type: ignore
            from magic_pdf.data.dataset import PymuDocDataset  # type: ignore
            from magic_pdf.model.doc_analyze_by_custom_model import doc_analyze  # type: ignore
            from magic_pdf.config.enums import SupportedPdfParseMethod  # type: ignore
        except ImportError as exc:
            logger.warning("mineru/magic_pdf not installed (%s); falling back to noop for this call", exc)
            return "", {"page_count": _cheap_page_count(pdf_path)}

        pdf_bytes = pdf_path.read_bytes()
        ds = PymuDocDataset(pdf_bytes)

        # Use a temp directory for MinerU intermediate files
        import tempfile, os
        with tempfile.TemporaryDirectory() as tmpdir:
            img_dir = os.path.join(tmpdir, "images")
            os.makedirs(img_dir, exist_ok=True)
            img_writer = FileBasedDataWriter(img_dir)
            md_writer = FileBasedDataWriter(tmpdir)

            if ds.classify() == SupportedPdfParseMethod.OCR:
                infer_result = ds.apply(doc_analyze, ocr=True)
                pipe = infer_result.pipe_ocr_mode(img_writer)
            else:
                infer_result = ds.apply(doc_analyze, ocr=False)
                pipe = infer_result.pipe_txt_mode(img_writer)

            pipe.dump_md(md_writer, "output.md", img_dir)
            md_path = os.path.join(tmpdir, "output.md")
            if os.path.exists(md_path):
                with open(md_path, "r", encoding="utf-8") as fh:
                    md_text = fh.read()
            else:
                md_text = ""

        page_count = _cheap_page_count(pdf_path)
        return md_text, {"page_count": page_count}


class NoopParser(BaseParser):
    name = "none"

    def to_markdown(self, pdf_path: Path) -> tuple[str, dict[str, Any]]:
        return "", {"page_count": _cheap_page_count(pdf_path)}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_parser(backend: str) -> BaseParser:
    """Return the right parser for *backend*. Unknown / 'none' -> NoopParser."""
    if backend == "marker":
        return MarkerParser()
    if backend == "mineru":
        return MinerUParser()
    return NoopParser()


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------

def parse_pdf(
    pdf_path: Path,
    markdown_path: Path,
    metadata_path: Path,
    *,
    backend: str,
    base_metadata: dict[str, Any],
) -> ParseResult:
    """Parse *pdf_path* to Markdown; write outputs; return ParseResult. Never raises."""
    parser: BaseParser = NoopParser()  # default in error path
    try:
        parser = get_parser(backend)
        md_text, extra = parser.to_markdown(pdf_path)

        written_md_path: str | None = None
        if md_text:
            markdown_path.parent.mkdir(parents=True, exist_ok=True)
            markdown_path.write_text(md_text, encoding="utf-8")
            written_md_path = str(markdown_path)

        page_count: int | None = extra.get("page_count")
        parsed_at = datetime.now(timezone.utc).isoformat()

        metadata: dict[str, Any] = {
            **base_metadata,
            "page_count": page_count,
            "parser": parser.name,
            "parsing_status": "PARSED",
            "markdown_path": written_md_path,
            "parsed_at": parsed_at,
        }
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        return ParseResult(
            markdown_path=written_md_path,
            metadata_path=str(metadata_path),
            page_count=page_count,
            parser=parser.name,
            status=Status.PARSED,
        )

    except Exception as exc:  # noqa: BLE001
        logger.warning("parse_pdf failed for %s: %s", pdf_path, exc, exc_info=True)
        error_str = str(exc)
        try:
            error_meta: dict[str, Any] = {
                **base_metadata,
                "page_count": None,
                "parser": parser.name,
                "parsing_status": "FAILED",
                "markdown_path": None,
                "parsed_at": datetime.now(timezone.utc).isoformat(),
                "error": error_str,
            }
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(json.dumps(error_meta, indent=2), encoding="utf-8")
        except Exception as write_exc:
            logger.warning("Could not write failure metadata to %s: %s", metadata_path, write_exc)

        return ParseResult(
            status=Status.FAILED,
            error=error_str,
            metadata_path=str(metadata_path),
            parser=parser.name,
        )
