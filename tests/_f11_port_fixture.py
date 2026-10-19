"""Qualified synthetic fetch envelope for retained Brain positive fixtures."""
from engine.research_vault import fulltext


def fetch_result(row, report_id, selectors):
    text = row.get("body") if isinstance(row.get("body"), str) else ""
    layer = row.get("text_layer")
    result = {
        "ok": True, "available": True, "report_id": report_id,
        "report": {k: row.get(k) or "" for k in ("title", "institution", "side", "published_at")},
        "source": {"state": "SOURCE_FRESH", "known_degradation": []},
        "coverage_state": "NO_TEXT_LAYER" if layer == "none" else "EXTRACTION_UNAVAILABLE",
        "text_layer_state": "none" if layer == "none" else None,
        "text_revision": None, "segment_count_total": 0, "segments": [],
    }
    if not text or layer == "none":
        return result
    record = fulltext.build_extracted_text(report_id=report_id,
        source_pdf_sha256=row.get("content_sha256") or "a" * 64,
        text=text, extractor_name="pdftotext", extractor_version="synthetic-fixture-v1",
        page_count=max(1, text.count("\f") + 1),
        text_layer_state="thin" if layer == "thin" else "full")
    segments = fulltext.build_segments(record, segmenter_version=fulltext.SEGMENTER_VERSION, max_bytes=4000)
    start = selectors.get("segment_start", 0)
    limit = selectors.get("max_segments", 4)
    result.update(coverage_state="FULL_TEXT", text_layer_state=record["text_layer_state"],
        segment_count_total=len(segments), segments=segments[start:start+limit],
        text_revision={"schema": "research_vault.text_revision.v1",
            **{k: record[k] for k in ("source_pdf_sha256", "extracted_text_sha256", "extractor_name", "extractor_version", "char_count", "byte_count")},
            "segmenter_version": fulltext.SEGMENTER_VERSION, "segment_max_bytes": 4000})
    if layer == "thin":
        result["source"]["known_degradation"] = ["FULL_TEXT_PARTIAL"]
    return result
