"""Pure projection of live pulse and board-quote payload fields into the dict
shape that ``/api/status`` publishes under ``checks[flow_pulse]`` and
``checks[intraday_quotes]``. The dead-man in
``scripts/check_vps_live_health.py`` (the ``evaluate`` function) consumes the
``source_asof`` key from each entry during weekday 15-19Z and fails when the
clock is missing, invalid, or older than the limit.

The module is stdlib-only so its tests run inside the
``washout-turn-organ`` CI job, which installs no fastapi/starlette/pydantic.
No I/O, no ``app.*`` import.
"""


def flow_pulse_fields(data: dict) -> dict:
    """Project the flow pulse payload into the ``/api/status`` row consumed by
    ``scripts/check_vps_live_health.py::evaluate`` for the 15-19Z source-clock
    check. Values pass through unchanged — a missing value stays ``None``,
    never ``0`` (missing is not zero).
    """
    rows = data.get("tickers") or []
    return {
        "mode": data.get("mode"),
        "n_tickers": data.get("n_tickers"),
        "with_bars": sum(
            1 for row in rows
            if isinstance(row, dict)
            and int(row.get("bars_today") or 0) > 0
        ),
        "n_universe": data.get("n_universe"),
        "source_asof": data.get("source_asof"),
    }


def intraday_quotes_fields(data: dict) -> dict:
    """Project the intraday board-quote payload into the ``/api/status`` row
    consumed by ``scripts/check_vps_live_health.py::evaluate`` for the 15-19Z
    source-clock check. Values pass through unchanged — a missing value stays
    ``None``, never ``0`` (missing is not zero).
    """
    raw_meta = data.get("meta")
    meta = raw_meta if isinstance(raw_meta, dict) else {}
    return {
        "requested": meta.get("requested"),
        "resolved": meta.get("resolved"),
        "coverage": meta.get("coverage"),
        "source_asof": meta.get("source_asof"),
        "built_at": meta.get("built_at"),
    }