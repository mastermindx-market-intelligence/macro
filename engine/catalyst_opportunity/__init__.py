"""Read-only Catalyst Opportunity views; no signal or allocation authority."""
from .projection import build_opportunity_view

__all__ = ["build_opportunity_view"]
