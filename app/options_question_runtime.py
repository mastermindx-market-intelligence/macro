"""Lazy server-only Matrix question composition. No config writes or enrollment.

The existing Brain configuration loader is read at request and disclosure time.
Absent/invalid/OFF configuration withdraws prior runtime objects as well as new
requests. A valid configuration only pins evidence; native policy still decides.
"""
from __future__ import annotations

import re
import httpx
from app.options_matrix_http import MatrixHTTPRuntime
from engine.neuralweb.options_question_gateway import OptionsQuestionRuntime
from engine.intelligence_workspace.options_matrix_question import QuestionPolicyBinding
from engine.intelligence_workspace.options_source_use import ProcessorDestination, validate_processor
from lib.dataos.registry import RIGHTS_KEYS


def _text(value, limit=512):
    return (type(value) is str and 0 < len(value) <= limit and value == value.strip()
            and all(ord(c) >= 32 and ord(c) != 127 for c in value))


def _pins(config):
    if type(config) is not dict:
        return None
    block = config.get('options_question_gateway')
    if (type(block) is not dict or set(block) != {'enabled', 'policies'}
            or block['enabled'] is not True):
        return None
    rows = block['policies']
    if type(rows) is not list or not 1 <= len(rows) <= 32:
        return None
    pins, seen = [], set()
    fields = {'provider', 'endpoint', 'model', 'evidence_sha256',
              'registry_revision', 'required_rights_rationale'}
    for row in rows:
        if type(row) is not dict or set(row) != fields:
            return None
        if not all(_text(row[k]) for k in ('provider', 'endpoint', 'model', 'registry_revision')):
            return None
        dest = ProcessorDestination(row['provider'], row['endpoint'], row['model'])
        try:
            validate_processor(dest)
            if (dest.provider not in ('anthropic', 'oauth', 'deepseek')
                    or str(httpx.URL(dest.endpoint)) != dest.endpoint
                    or not dest.endpoint.endswith('/v1/messages') or dest in seen):
                return None
        except Exception:
            return None
        digest, rationale = row['evidence_sha256'], row['required_rights_rationale']
        if type(digest) is not str or not re.fullmatch('[0-9a-f]{64}', digest):
            return None
        if (type(rationale) is not dict or not rationale or set(rationale) - set(RIGHTS_KEYS)
                or not all(_text(v, 1024) for v in rationale.values())):
            return None
        seen.add(dest)
        pins.append((dest, QuestionPolicyBinding(digest, row['registry_revision'],
                                                 tuple(sorted(rationale.items())))))
    return tuple(pins)


class _RuntimeSource:
    def __init__(self, app, config_loader):
        self.app, self.config_loader = app, config_loader

    def resolve(self):
        try:
            matrix = getattr(self.app.state, 'options_matrix_display_runtime', None)
            pins = _pins(self.config_loader())
            if type(matrix) is not MatrixHTTPRuntime or not callable(matrix.capture) or pins is None:
                return None

            def current():
                # Reinstallation/withdrawal and replacement of native capture
                # invalidate in-flight preparations; no old runtime is authority.
                return (getattr(self.app.state, 'options_question_gateway_source', None) is self
                        and getattr(self.app.state, 'options_matrix_display_runtime', None) is matrix
                        and _pins(self.config_loader()) == pins)

            return OptionsQuestionRuntime(matrix, pins, True, current)
        except Exception:
            return None


def install_options_question_runtime(app, *, config_loader):
    """Install a lazy constructor, without reading configuration/source or sending."""
    app.state.options_question_gateway_runtime = None  # retire old injection
    app.state.options_question_gateway_source = (
        _RuntimeSource(app, config_loader) if callable(config_loader) else None)


def resolve_options_question_runtime(app):
    source = getattr(app.state, 'options_question_gateway_source', None)
    return source.resolve() if type(source) is _RuntimeSource else None
