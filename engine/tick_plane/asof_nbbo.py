"""Bounded event-time NBBO ring and fail-closed as-seen trade/quote join.

This is an in-memory leaf beneath canonical TP-1, not a socket, watermark
generator, historical tape owner, correction reconciler, event lifecycle or
publisher. Original receipt and completeness must be qualified upstream.
A trade and quote sharing the same millisecond SIP clock are UNORDERED absent
independently verified cross-channel ordering; never break ties by arrival order.
"""

from __future__ import annotations

from bisect import bisect_left
from collections import defaultdict
from copy import deepcopy

from engine.tick_plane.stream_events import (
    MAX_UNIVERSE, SCHEMA, FrameContractError, _SESSION, _SYMBOL, _integer,
)

MATCH_SCHEMA = "equity.tick_plane.nbbo_join/v0"
MAX_QUOTE_EVENTS_PER_SYMBOL = 8192
MAX_TOTAL_QUOTE_EVENTS = 131072  # global pilot ceiling; never silently exceed


class InFlightNBBO:
    """Explicitly session-scoped, bounded NBBO buffer with permanent gap fence."""

    def __init__(self, *, session, symbols, per_symbol_cap=4096,
                 total_cap=MAX_TOTAL_QUOTE_EVENTS):
        if not isinstance(session, str) or not _SESSION.fullmatch(session):
            raise FrameContractError("invalid quote-ring session")
        if not isinstance(symbols, (set, frozenset, list, tuple)):
            raise FrameContractError("ring needs a frozen symbol set")
        names = set(symbols)
        if not names or len(names) > MAX_UNIVERSE or any(
            not isinstance(s, str) or _SYMBOL.fullmatch(s) is None for s in names
        ):
            raise FrameContractError("invalid or unbounded ring universe")
        _integer(per_symbol_cap, "per_symbol_cap", minimum=1)
        if per_symbol_cap > MAX_QUOTE_EVENTS_PER_SYMBOL:
            raise FrameContractError("ring cap exceeds bounded maximum")
        _integer(total_cap, "total_cap", minimum=1)
        if total_cap > MAX_TOTAL_QUOTE_EVENTS:
            raise FrameContractError("global quote budget exceeds bounded maximum")
        self.session = session
        self.symbols = frozenset(names)
        self.cap = per_symbol_cap
        self.total_cap = total_cap
        self._quotes = defaultdict(list)
        # Parallel chronological sort keys enable constant-time normal append,
        # binary search for matches and rare bounded out-of-order insertion.
        self._keys = defaultdict(list)
        self._head = defaultdict(int)  # logical oldest offset; amortized compaction
        self._active_total = 0
        self._reordered = defaultdict(int)
        self._ids = defaultdict(dict)
        self._gaps = set()
        self._evicted = defaultdict(int)

    def mark_gap(self, ticker):
        """Permanent fail-closed fence; a source owner must create a NEW ring."""
        if ticker not in self.symbols:
            raise FrameContractError("gap symbol outside pilot")
        self._gaps.add(ticker)

    def ingest_quote(self, quote):
        if not isinstance(quote, dict) or quote.get("schema") != SCHEMA or quote.get("event_type") != "Q":
            raise FrameContractError("only normalized native quotes enter NBBO ring")
        ticker = quote.get("ticker")
        if ticker not in self.symbols or quote.get("session") != self.session:
            raise FrameContractError("quote outside ring symbol/session")
        if ticker in self._gaps:
            raise FrameContractError("quote ring gap fence remains active")
        for k in ("sip_timestamp_ns", "original_frame_received_ns", "native_sequence", "frame_event_index"):
            _integer(quote.get(k), "quote." + k)
        if quote["original_frame_received_ns"] < quote["sip_timestamp_ns"]:
            raise FrameContractError("quote receipt before SIP")
        if not isinstance(quote.get("source_frame_sha256"), str) or len(quote["source_frame_sha256"]) != 64:
            raise FrameContractError("quote has no source-frame digest")
        if not isinstance(quote.get("source_receipt_id"), str) or not quote["source_receipt_id"].strip():
            raise FrameContractError("quote has no original receipt ID")
        # SIP Q sequence is ticker/session scoped; it is NOT assumed gap-free.
        identity = quote["native_sequence"]
        previous = self._ids[ticker].get(identity)
        if previous is not None:
            if previous != quote:
                self.mark_gap(ticker)
                raise FrameContractError("conflicting native quote sequence; ring quarantined")
            return False
        events = self._quotes[ticker]
        keys = self._keys[ticker]
        head = self._head[ticker]
        active = len(keys) - head
        if self._active_total >= self.total_cap and active < self.cap:
            self.mark_gap(ticker)
            raise FrameContractError("global quote-ring budget exhausted; symbol quarantined")
        event = deepcopy(quote)
        key = (event["sip_timestamp_ns"], identity)
        if active and key < keys[head] and self._evicted[ticker]:
            self.mark_gap(ticker)
            raise FrameContractError("out-of-order quote predates evicted history; ring quarantined")
        if not active or key >= keys[-1]:
            events.append(event)
            keys.append(key)
        else:
            # Out-of-order data is never silently treated as a newer BBO.
            # This slow path is bounded by cap; source watermark must still attest
            # completeness before any resulting match can be used.
            idx = bisect_left(keys, key, lo=head)
            events.insert(idx, event)
            keys.insert(idx, key)
            self._reordered[ticker] += 1
        self._ids[ticker][identity] = event
        self._active_total += 1
        if len(keys) - head > self.cap:
            dropped = events[head]
            self._ids[ticker].pop(dropped["native_sequence"], None)
            head += 1
            self._evicted[ticker] += 1
            self._active_total -= 1
        # Avoid pop(0) on every tick. A fixed 512-event compaction interval
        # also bounds physical overhang independently of insertion cadence.
        if head >= min(self.cap, 512):
            del events[:head]
            del keys[:head]
            head = 0
        self._head[ticker] = head
        return True

    def match(self, trade, *, decision_ns, source_complete_through_ns,
              watermark_available_ns, watermark_receipt_id,
              source_completeness_attested, max_quote_age_ns,
              quote_condition_eligible, quote_condition_rules_ref):
        """Resolve one original-available PRE-trade quote, never infer eligibility.

        A declared watermark is NOT proven by its numeric value; source owner must
        verify and attest it. Missing or false confirmation yields a typed NULL.
        Matched quote remains internal/private; price-location signing is owned by
        engine.flow_signing.classify_print after an explicit trade-condition check.
        """
        def null(reason):
            return {"schema": MATCH_SCHEMA, "state": "UNKNOWN", "reason": reason,
                    "quote": None, "quote_age_ns": None, "authority": "SOURCE_CONTEXT_ONLY"}

        if not isinstance(trade, dict) or trade.get("schema") != SCHEMA or trade.get("event_type") != "T":
            return null("NOT_A_QUALIFIED_TRADE_RECORD")
        ticker = trade.get("ticker")
        if ticker not in self.symbols or trade.get("session") != self.session:
            return null("SESSION_OR_TICKER_MISMATCH")
        if ticker in self._gaps:
            return null("SOURCE_GAP_QUARANTINED")
        for key, value in (
            ("decision_ns", decision_ns),
            ("source_complete_through_ns", source_complete_through_ns),
            ("watermark_available_ns", watermark_available_ns),
            ("max_quote_age_ns", max_quote_age_ns),
        ):
            if type(value) is not int or value < 0:
                return null("INVALID_DECISION_OR_WATERMARK_CLOCK")
        if (not isinstance(watermark_receipt_id, str) or not watermark_receipt_id.strip()
                or source_completeness_attested is not True):
            return null("SOURCE_COMPLETENESS_UNATTESTED")
        if watermark_available_ns < source_complete_through_ns or watermark_available_ns > decision_ns:
            return null("WATERMARK_NOT_KNOWABLE")
        if source_complete_through_ns < trade.get("sip_timestamp_ns", 0):
            return null("TRADE_WINDOW_NOT_COMPLETE")
        if trade.get("original_frame_received_ns", decision_ns + 1) > decision_ns:
            return null("TRADE_NOT_AVAILABLE_AT_DECISION")
        if quote_condition_eligible is not True or not isinstance(quote_condition_rules_ref, str) or not quote_condition_rules_ref.strip():
            return null("QUOTE_CONDITION_POLICY_UNQUALIFIED")
        quotes = self._quotes[ticker]
        keys = self._keys[ticker]
        head = self._head[ticker]
        if head >= len(keys):
            return null("NO_AS_SEEN_QUOTES")
        stamp = trade["sip_timestamp_ns"]
        i = bisect_left(keys, (stamp, -1), lo=head)
        # A quote with exactly the trade's millisecond SIP time is not
        # causally ordered against the trade. Only as-seen quotes count.
        j = i
        while j < len(keys) and keys[j][0] == stamp:
            if quotes[j]["original_frame_received_ns"] <= decision_ns:
                return null("UNORDERED_SAME_MILLISECOND")
            j += 1
        j = i - 1
        while j >= head and quotes[j]["original_frame_received_ns"] > decision_ns:
            j -= 1
        if j < head:
            return null("QUOTE_HISTORY_EVICTED" if self._evicted[ticker]
                        else "NO_AS_SEEN_QUOTES")
        q = quotes[j]
        # Multiple quote updates at the same SIP millisecond are ambiguous
        # unless a separate native-order contract establishes precedence.
        k = j - 1
        while k >= head and keys[k][0] == keys[j][0]:
            if quotes[k]["original_frame_received_ns"] <= decision_ns:
                return null("AMBIGUOUS_PRIOR_QUOTE_ORDER")
            k -= 1
        age = stamp - q["sip_timestamp_ns"]
        if age > max_quote_age_ns:
            return null("QUOTE_STALE")
        if not q.get("valid_firm_nbbo"):
            return null("INVALID_OR_ONE_SIDED_NBBO")
        return {"schema": MATCH_SCHEMA, "state": "MATCHED_SOURCE_CONTEXT",
                "reason": None, "quote": deepcopy(q), "quote_age_ns": age,
                "watermark_receipt_id": watermark_receipt_id,
                "quote_condition_rules_ref": quote_condition_rules_ref,
                "ring_dropped_old_updates": self._evicted[ticker],
                "ring_out_of_order_updates": self._reordered[ticker],
                "ring_active_events": self._active_total,
                "authority": "SOURCE_CONTEXT_ONLY"}
