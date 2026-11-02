"""Pure display contract for the existing AI Daily Brief; no signal authority.

Keep the original producer, artifacts and ledger. Unknown inputs stay unknown.
The single-file writer provides atomic replacement, not a two-file transaction.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import tempfile

LIST_FIELDS = ('tldr', 'conflicts', 'transmission', 'watch_items')
TEXT_FIELDS = ('summary', 'regime_read', 'rotation_check', 'forward_read',
               'degraded_reason', 'generated_at', 'state_asof')
CONFIDENCE = ('low', 'medium', 'high')
TONES = ('good', 'warn', 'bad', 'neutral', 'info')


def text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        # A time with no zone has an unknown offset; date-only source dates
        # are handled separately below and never treated as generation times.
        if result.tzinfo is None:
            return None
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, OverflowError):
        return None


def source_day(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        result = date.fromisoformat(value)
        return result if result.isoformat() == value else None
    except (ValueError, TypeError):
        return None


def normalize_brief(payload: object, lens: str | None = None) -> dict:
    """Normalize untrusted rows without shifting their translated counterparts."""
    raw = payload if isinstance(payload, dict) else {}
    out = deepcopy(raw)
    out['is_context_only'] = True
    if lens is not None:
        out['lens'] = lens
    for key in TEXT_FIELDS:
        out[key] = text(raw.get(key))
    conf = raw.get('confidence')
    out['confidence'] = conf if isinstance(conf, str) and conf in CONFIDENCE else None
    zh_raw = raw.get('zh') if isinstance(raw.get('zh'), dict) else {}
    zh = {key: text(zh_raw.get(key)) for key in TEXT_FIELDS}
    for key in LIST_FIELDS:
        values = raw.get(key) if isinstance(raw.get(key), list) else []
        translations = zh_raw.get(key) if isinstance(zh_raw.get(key), list) else []
        retained = [(i, text(value)) for i, value in enumerate(values) if text(value)]
        out[key] = [value for _, value in retained]
        zh[key] = [text(translations[i]) if i < len(translations) else None for i, _ in retained]
    out['zh'] = zh
    facts = raw.get('key_facts') if isinstance(raw.get('key_facts'), list) else []
    out['key_facts'] = []
    for row in facts:
        if not isinstance(row, dict) or not text(row.get('value_en')):
            continue
        clean = {k: text(row.get(k)) for k in ('key', 'label_en', 'label_zh', 'value_en', 'value_zh')}
        tone = row.get('tone')
        clean['tone'] = tone if isinstance(tone, str) and tone in TONES else 'neutral'
        out['key_facts'].append(clean)
    refresh = raw.get('refresh_days')
    out['refresh_days'] = refresh if type(refresh) is int and 1 <= refresh <= 7 else None
    events = raw.get('forward_watch') if isinstance(raw.get('forward_watch'), list) else []
    out['forward_watch'] = [{k: text(row.get(k)) for k in ('date', 'label', 'kind', 'note')}
                            for row in events if isinstance(row, dict)
                            and source_day(row.get('date')) and text(row.get('label'))]
    out['theses'] = [t for t in raw.get('theses', []) if isinstance(t, dict)] if isinstance(raw.get('theses'), list) else []
    return out


def usable_brief(payload: object) -> bool:
    brief = normalize_brief(payload)
    return bool(brief['summary'] or brief['regime_read'] or brief['tldr'])


def compare_readings(current: dict, previous: object) -> dict:
    """Compare same-lens, strictly newer source vintages, never model prose."""
    unavailable = {'status': 'unavailable', 'rows': []}
    if not isinstance(previous, dict):
        return unavailable
    if current.get('lens') not in ('macro', 'china', 'btc') or previous.get('lens') != current.get('lens'):
        return unavailable
    now_day, old_day = source_day(current.get('state_asof')), source_day(previous.get('state_asof'))
    if not now_day or not old_day or now_day <= old_day:
        return unavailable
    if now_day > datetime.now(timezone.utc).date():
        return unavailable
    now, old = normalize_brief(current)['key_facts'], normalize_brief(previous)['key_facts']
    def indexed(rows):
        keys = [r['key'] for r in rows]
        return {r['key']: r for r in rows} if keys and all(keys) and len(set(keys)) == len(keys) else None
    a, b = indexed(now), indexed(old)
    if not a or not b or set(a) != set(b):
        return unavailable
    rows = []
    for key, row in a.items():
        prior = b[key]
        if row['value_en'] != prior['value_en']:
            rows.append({**row, 'previous_en': prior['value_en'],
                         'previous_zh': prior['value_zh'] or prior['value_en']})
    return {'status': 'compared', 'previous_asof': old_day.isoformat(),
            'current_asof': now_day.isoformat(), 'rows': rows}


def write_brief_atomic(path: Path, payload: dict) -> None:
    """Replace one existing producer artifact only after complete serialization.

    Failed replacement keeps previous bytes; the temp is in the target directory
    so os.replace stays on one filesystem. The site mirror is a separate write.
    """
    encoded = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
