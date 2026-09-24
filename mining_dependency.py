"""Consumption-side mining dependency binding for the future shared research."""

from __future__ import annotations

import copy
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.util import find_spec
from types import ModuleType
from typing import Any, Callable, Literal

Result = Mapping[str, object]


Query = Literal["query", "bundle", "object"]
Refusal = typing.__annotations__ if False else {"format": {}}
