"""Closed evaluation DATA primitives; parsing never grants native authority."""
from __future__ import annotations
import base64
import hashlib
import json
import re

FLAGS = {k: False for k in ('authenticated', 'qualification_verified', 'independence_verified', 'exposure_verified', 'operational_admission')}

ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z', re.ASCII)

SHA = re.compile(r'[a-f0-9]{64}\Z', re.ASCII)

class WireRefused(ValueError):
    def __init__(self): super().__init__('memory_issuer_wire_refused')

def fail(): raise WireRefused()

def canonical(value):
    try: return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, UnicodeError, RecursionError): raise WireRefused() from None

def exact(value, keys):
    if type(value) is not dict or set(value) != set(keys.split()): fail()

def token(value):
    if type(value) is not str or not ID.fullmatch(value): fail()

def digest(value):
    if type(value) is not str or not SHA.fullmatch(value): fail()

def integer(value, upper):
    if type(value) is not int or not 1 <= value <= upper: fail()

def _tree(value, depth=0, budget=None):
    if budget is None: budget = [8192]
    budget[0] -= 1
    if budget[0] < 0 or depth > 16: fail()
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str: fail()
            _tree(item, depth+1, budget)
    elif type(value) is list:
        for item in value: _tree(item, depth+1, budget)
    elif type(value) not in (str, int, bool, type(None)): fail()

def parse(raw, maximum):
    if type(raw) is not bytes or not 1 <= len(raw) <= maximum: fail()
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value: fail()
            value[key] = item
        return value
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _: fail())
        _tree(value)
        if canonical(value) != raw: fail()
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError): raise WireRefused() from None

def _reference(value):
    exact(value, 'schema object_id sha256 bytes')
    token(value['schema']); token(value['object_id']); digest(value['sha256']); integer(value['bytes'], 4194304)

def fingerprint(value):
    if type(value) is not str or not value.startswith('SHA256:'):fail()
    try:
        raw=base64.b64decode(value[7:]+'=',validate=True)
        if len(raw)!=32 or base64.b64encode(raw).decode().rstrip('=')!=value[7:]:fail()
    except (ValueError,TypeError):raise WireRefused() from None
