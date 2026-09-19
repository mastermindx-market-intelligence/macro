"""Pure investigation projection over Alert Triage's existing evidence.

No readers, persistence, new signal IDs, scoring or outbound authority live here.
The capped legacy board and its push consumers remain unchanged.
"""
from __future__ import annotations

from datetime import date
import unicodedata
import math

from engine import alert_time


def _json_safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_json_safe(v) for v in value)
    return value


def _key(row: dict) -> tuple[str, str, str]:
    source = str(row.get('source') or '')
    return source, str(row.get('type') or ''), str(row.get('asset') or source)


def _clock_key(row: dict) -> tuple:
    day = alert_time.parse_date(row.get('board_date')) or date.min
    instant = alert_time.parse_instant(row.get('event_ts'))
    return day, instant.timestamp() if instant is not None else 0.0


def _plain(text: str) -> str:
    text = str(text or '').strip()
    while text and (unicodedata.category(text[0])[0] in 'PS' or text[0].isspace()):
        text = text[1:]
    return text.strip()


def _subject(rows: list[dict], asset: str, language: str = 'en') -> str:
    # A display label only. Matching NEVER depends on title text or a generic link.
    field = 'headline_zh' if language == 'zh' else 'headline'
    for row in rows:
        headline = _plain(row.get(field) or '')
        for separator in (':', '：'):
            if separator in headline:
                label = headline.split(separator, 1)[0].strip()
                if 0 < len(label) <= 80:
                    return label
    return asset.replace('_', ' ') if asset.isupper() else asset.replace('_', ' ').title()


def _situations(signals: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = {}
    for row in signals:
        source, _, asset = _key(row)
        if not asset or asset.lower() in {source.lower(), 'macro', 'rates', 'vector', 'all'}:
            continue
        groups.setdefault((source, asset), []).append(row)
    result = []
    for (source, asset), rows in groups.items():
        if len({r.get('type') for r in rows}) < 2:
            continue
        result.append({'primary_alert_id': rows[0]['alert_id'],
                       'member_ids': list(dict.fromkeys(r['alert_id'] for r in rows)),
                       'subject': _subject(rows, asset), 'subject_zh': _subject(rows, asset, 'zh'),
                       'source': source, 'source_label': rows[0].get('source_label', source),
                       'source_label_zh': rows[0].get('source_label_zh', source),
                       'method': 'same_source_subject'})
    return result


def build_explorer(signals: list[dict], raw_events: list[dict], *,
                   history_limit: int = 1000) -> dict:
    """Expose uncapped signals and bounded observed history without promotion.

    The caller supplies the already-ranked, future-quarantined populations.
    Derived situations are same-source exact-subject views, not new entities.
    History rows refer to the existing parent alert_id; no synthetic event ID.
    """
    if isinstance(history_limit, bool) or not isinstance(history_limit, int) or history_limit < 0:
        raise ValueError('history_limit must be a non-negative integer')
    # Tenant-bound sentinel evidence must not expand into a shared page.
    signals = [_json_safe(r) for r in signals if r.get('source') != 'watchlist']
    index = {_key(row): row for row in signals}
    sources: dict[str, dict] = {}
    for row in signals:
        source = str(row.get('source') or '')
        info = sources.setdefault(source, {'source': source, 'count': 0,
            'label': row.get('source_label', source),
            'label_zh': row.get('source_label_zh', source)})
        info['count'] += 1
    history = []
    clock_fields = ('board_date', 'event_date', 'event_ts', 'source_asof',
                    'recorded_at', 'date_precision')
    for event in raw_events:
        parent = index.get(_key(event))
        if parent is None:
            continue
        history.append({
            'alert_id': parent['alert_id'], 'source': parent['source'],
            'asset': parent.get('asset'), 'type': parent.get('type'),
            'source_label': parent.get('source_label', parent['source']),
            'source_label_zh': parent.get('source_label_zh', parent['source']),
            'headline': _plain(event.get('headline') or parent.get('headline') or ''),
            'headline_zh': _plain(event.get('headline_zh') or event.get('headline') or ''),
            'detail': str(event.get('detail') or ''),
            'detail_zh': str(event.get('detail_zh') or event.get('detail') or ''),
            **{key: event.get(key) for key in clock_fields},
        })
    history.sort(key=_clock_key, reverse=True)
    return {'schema': 'mastermind.alert_center_view.v1',
            'signals': list(signals), 'total_signals': len(signals),
            'restricted_sources': ['watchlist'],
            'sources': sorted(sources.values(), key=lambda s: s['label']),
            'situations': _situations(signals), 'history': history[:history_limit],
            'history_total': len(history), 'history_limit': history_limit,
            'history_truncated': max(0, len(history) - history_limit)}
