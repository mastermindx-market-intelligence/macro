"""One frozen study input assembly; no estimate, network, registry or publication."""
import csv
import io
import math
import pandas as pd


def assemble_panel(cpi, payrolls, start="1998-01-01", end="2026-09-01"):
    tables = {}
    for name, frame in (("cpi", cpi), ("payrolls", payrolls)):
        required = {"period", "realtime_start", "value"}
        if not required <= set(frame.columns):
            raise ValueError(f"{name}: missing required columns")
        table = frame[list(required)].copy()
        for col in ("period", "realtime_start"):
            dates = pd.to_datetime(table[col], errors="raise")
            if dates.isna().any() or dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
                raise ValueError(f"{name}: {col} must be date-only naive provider calendar dates")
            table[col] = dates
        if table.duplicated(["period", "realtime_start"]).any():
            raise ValueError(f"{name}: duplicate period/vintage keys")
        if not table.period.eq(table.period.dt.to_period("M").dt.to_timestamp()).all():
            raise ValueError(f"{name}: period must be monthly first day")
        tables[name] = {p: g.sort_values("realtime_start") for p, g in table.groupby("period")}
    months = pd.date_range(start, end, freq="MS")
    if len(months) == 0:
        raise ValueError("empty frozen period range")
    records, custody = [], []
    previous_anchor = previous_bound = None
    for period in months:
        current = tables["cpi"].get(period)
        if current is None:
            raise ValueError(f"{period.date()}: missing current CPI period")
        month_end = period + pd.offsets.MonthEnd(0)
        eligible = current[(current.realtime_start > month_end) &
                           (current.realtime_start <= month_end + pd.Timedelta(days=45))]
        if eligible.empty:
            raise ValueError(f"{period.date()}: no retained CPI vintage inside frozen45day bound")
        current_row = eligible.iloc[0]
        anchor = current_row.realtime_start
        selected = []
        for name, target in (("cpi", period - pd.offsets.MonthBegin(1)), ("payrolls", period)):
            group = tables[name].get(target)
            if group is None:
                raise ValueError(f"{period.date()}: missing {name} asof period")
            available = group[group.realtime_start <= anchor]
            if available.empty:
                raise ValueError(f"{period.date()}: missing {name} asof vintage")
            selected.append(available.iloc[-1])
        prior_cpi, payroll = selected
        values = [float(row.value) for row in (current_row, prior_cpi, payroll)]
        if any(not math.isfinite(value) or value <= 0 for value in values):
            raise ValueError(f"{period.date()}: selected level must be finite and positive")
        # Source has a calendar date only. This is a declared conservative delay,
        # never an assertion of exact intraday release time or forecast usability.
        bound = (anchor + pd.Timedelta(days=2)).tz_localize("UTC")
        if previous_anchor is not None and (anchor <= previous_anchor or previous_bound > bound):
            raise ValueError(f"{period.date()}: anchor/control clock order failed")
        records.append([anchor.date().isoformat(), format(math.log(values[2]), ".17g"),
                        format(100 * (math.log(values[0]) - math.log(values[1])), ".17g"),
                        bound.isoformat()])
        custody.append({"source_period": period.date().isoformat(),
                        "cpi_anchor": anchor.date().isoformat(),
                        "prior_cpi_vintage": prior_cpi.realtime_start.date().isoformat(),
                        "payroll_vintage": payroll.realtime_start.date().isoformat(),
                        "known_at_bound": bound.isoformat()})
        previous_anchor, previous_bound = anchor, bound
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["period", "y", "shock", "known_at"])
    writer.writerows(records)
    return stream.getvalue().encode(), {"rows": custody, "n_rows": len(records),
        "limitations": "Earliest retained vintage is not certified initial release. "
        "Date-only conservative availability bound, not exact release time. "
        "Descriptive research association only; no causal, forecast, trade or publication authority."}
