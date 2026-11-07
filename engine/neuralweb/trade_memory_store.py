"""Private Supabase adapter for Prophet Trade Memory.

The adapter is intentionally operator-scoped even though it uses a service-role
credential.  ``SUPABASE_OPERATOR_USER_ID`` is mandatory and every read/write carries
that UUID.  It never enumerates other users and never logs tickers, notes, prices, or
autopsy text.
"""
from __future__ import annotations

import json
import copy
import logging
import os
import re
from typing import Any
from urllib.parse import quote

log = logging.getLogger("neuralweb.trade_memory_store")

try:
    import requests
except Exception:  # pragma: no cover - production requirements include requests
    requests = None  # type: ignore

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)

_CLAIM_KEY = "_fabric_operation_v1"
_FACT_COLUMNS = ("schema", "source", "ticker", "market", "side", "entry_date",
                 "exit_date", "entry_price", "exit_price", "outcome",
                 "thesis_at_entry", "observed_result", "prophet_pick_ref")


def fabric_claim_present(row):
    packet = row.get("evidence_packet") if isinstance(row, dict) else None
    # A malformed non-null packet is not proof of an absent original claim.
    return packet is not None and (type(packet) is not dict or _CLAIM_KEY in packet)


def _claim_envelope(record):
    from scripts.metabolism_journal import validate_operation, fabric_digest
    validate_operation(record)
    return {"schema": "mastermind.trade_memory_fabric_claim.v1",
            "record": copy.deepcopy(record), "record_digest": fabric_digest(record)}


def _row_claim(row):
    from scripts.metabolism_journal import FabricHeld, validate_operation, fabric_digest
    packet = row.get("evidence_packet")
    value = packet.get(_CLAIM_KEY) if isinstance(packet, dict) else None
    if (type(value) is not dict or set(value) != {"schema", "record", "record_digest"}
            or value["schema"] != "mastermind.trade_memory_fabric_claim.v1"):
        raise FabricHeld("trade_memory_claim_invalid")
    validate_operation(value["record"])
    if value["record_digest"] != fabric_digest(value["record"]):
        raise FabricHeld("trade_memory_claim_digest_invalid")
    return value["record"]


def _literal_filter(value):
    """PostgREST values, passed as params; never interpolate or log a private URL."""
    from scripts.metabolism_journal import fabric_json
    if value is None:
        return "is.null"
    if isinstance(value, str):
        return 'eq."' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'
    if type(value) in (int, float):
        return "eq." + fabric_json(value)
    raise ValueError("trade_memory_fact_type_invalid")


def _unclaimed_packet_filter(row):
    """Compare the entire original JSONB value, including a null/malformed race."""
    from scripts.metabolism_journal import fabric_json, FabricHeld
    if "evidence_packet" not in row or fabric_claim_present(row):
        raise FabricHeld("trade_memory_original_packet_held")
    packet = row["evidence_packet"]
    return "is.null" if packet is None else _literal_filter(fabric_json(packet))


class SupabaseTradeMemoryStore:
    """Small PostgREST client with an explicit single-owner boundary."""

    def __init__(
        self,
        base_url: str,
        service_key: str,
        operator_user_id: str,
        session: Any = None,
    ):
        self.base_url = str(base_url or "").rstrip("/")
        self.service_key = str(service_key or "")
        self.operator_user_id = str(operator_user_id or "").lower()
        self.session = session or requests

    @property
    def available(self) -> bool:
        return bool(
            self.base_url
            and self.service_key
            and _UUID_RE.fullmatch(self.operator_user_id)
            and self.session is not None
        )

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "apikey": self.service_key,
            "Authorization": f"Bearer {self.service_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _url(self, table: str) -> str:
        return f"{self.base_url}/rest/v1/{table}"

    def fetch_pending(self, limit: int = 8) -> list[dict[str, Any]]:
        if not self.available:
            return []
        params = {
            "select": "*",
            "user_id": f"eq.{self.operator_user_id}",
            "outcome": "in.(win,loss,flat)",
            "autopsy_state": "in.(pending,retry)",
            "order": "created_at.asc",
            "limit": str(max(1, min(25, int(limit)))),
        }
        try:
            response = self.session.get(
                self._url("trade_episodes"),
                headers=self._headers,
                params=params,
                timeout=25,
            )
            if response.status_code != 200:
                log.warning("trade_memory_store: pending read HTTP %s", response.status_code)
                return []
            rows = response.json()
            return rows if isinstance(rows, list) else []
        except Exception as exc:  # noqa: BLE001
            log.warning("trade_memory_store: pending read failed (%s)", type(exc).__name__)
            return []

    def fetch_autopsied(self, limit: int = 500) -> list[dict[str, Any]]:
        if not self.available:
            return []
        params = {
            "select": "id,entry_date,outcome,autopsy",
            "user_id": f"eq.{self.operator_user_id}",
            "autopsy_state": "eq.complete",
            "autopsy": "not.is.null",
            "order": "entry_date.desc",
            "limit": str(max(1, min(2_000, int(limit)))),
        }
        try:
            response = self.session.get(
                self._url("trade_episodes"),
                headers=self._headers,
                params=params,
                timeout=25,
            )
            if response.status_code != 200:
                log.warning("trade_memory_store: autopsy read HTTP %s", response.status_code)
                return []
            rows = response.json()
            return rows if isinstance(rows, list) else []
        except Exception as exc:  # noqa: BLE001
            log.warning("trade_memory_store: autopsy read failed (%s)", type(exc).__name__)
            return []

    def _strict_rows(self, response):
        from scripts.metabolism_journal import strict_json
        if response.status_code != 200 or type(getattr(response, "text", None)) is not str:
            raise ValueError("trade_memory_response_unqualified")
        value = strict_json(response.text)
        if type(value) is not list or any(type(row) is not dict for row in value):
            raise ValueError("trade_memory_rows_invalid")
        return value

    def read_episode(self, episode_id):
        """One owner-scoped read, with absence distinct from an unknown result."""
        if not self.available or not _UUID_RE.fullmatch(str(episode_id or "")):
            return {"state": "unknown", "row": None}
        try:
            response = self.session.get(self._url("trade_episodes"), headers=self._headers,
                params={"select": "*", "id": "eq."+episode_id,
                        "user_id": "eq."+self.operator_user_id, "limit": "2"}, timeout=25)
            rows = self._strict_rows(response)
            if not rows:
                return {"state": "absent", "row": None}
            if (len(rows) != 1 or rows[0].get("id") != episode_id
                    or rows[0].get("user_id") != self.operator_user_id):
                raise ValueError("trade_memory_row_identity_invalid")
            return {"state": "read", "row": rows[0]}
        except Exception:
            return {"state": "unknown", "row": None}

    def fetch_fabric_candidates(self, limit=8):
        """The same episode owner exposes unresolved rows; it creates no new queue."""
        if not self.available:
            raise ValueError("trade_memory_store_unavailable")
        cap = max(1, min(25, int(limit)))
        rows = []
        # Original holds remain visible without consuming the fresh-work cap.
        for states in ("eq.running", "in.(pending,retry)"):
            response = self.session.get(self._url("trade_episodes"), headers=self._headers,
                params={"select": "*", "user_id": "eq."+self.operator_user_id,
                        "outcome": "in.(win,loss,flat)", "autopsy_state": states,
                        "order": "created_at.asc", "limit": str(cap)}, timeout=25)
            current = self._strict_rows(response)
            if len(current) > cap or any(row.get("user_id") != self.operator_user_id for row in current):
                raise ValueError("trade_memory_candidate_identity_invalid")
            rows.extend(current)
        return rows

    def _fact_params(self, row):
        from engine.neuralweb.trade_memory import normalize_episode
        if (type(row) is not dict or any(key not in row for key in _FACT_COLUMNS)
                or row.get("user_id") != self.operator_user_id
                or not _UUID_RE.fullmatch(str(row.get("id") or ""))):
            raise ValueError("trade_memory_original_row_invalid")
        normalize_episode(row)
        return {"id": "eq."+row["id"], "user_id": "eq."+self.operator_user_id,
                **{key: _literal_filter(row[key]) for key in _FACT_COLUMNS}}

    def _matches_claim(self, row, original, packet, record, *, autopsy=None):
        from engine.neuralweb.trade_memory import normalize_episode
        try:
            expected_state = "complete" if record["state"] == "complete" else "running"
            if (type(row) is not dict or row.get("id") != original["id"]
                    or row.get("user_id") != self.operator_user_id
                    or normalize_episode(row) != normalize_episode(original)
                    or row.get("autopsy_state") != expected_state or _row_claim(row) != record):
                return False
            actual_packet = dict(row["evidence_packet"])
            actual_packet.pop(_CLAIM_KEY)
            if actual_packet != packet:
                return False
            if record["state"] == "complete" and (row.get("autopsy") != autopsy
                    or row.get("autopsy_model") != record["receipt"]["served_model"]):
                return False
            return True
        except Exception:
            return False

    def _conditional_write(self, original, params, body, packet, record, *, autopsy=None):
        """One mutation; only its own lost ACK may use one same-row reconciliation."""
        from scripts.metabolism_journal import fabric_json
        reconcile = False
        try:
            response = self.session.patch(self._url("trade_episodes"),
                headers={**self._headers, "Prefer": "return=representation"},
                params=params, data=fabric_json(body), timeout=25)
        except Exception:
            # The request may have committed. Do not repeat PATCH or reset retry.
            reconcile = True
        else:
            if response.status_code == 200:
                try:
                    rows = self._strict_rows(response)
                except Exception:
                    return {"state": "unknown", "row": None}
                if not rows:
                    return {"state": "conflict", "row": None}
                if len(rows) == 1 and self._matches_claim(rows[0], original, packet, record, autopsy=autopsy):
                    return {"state": "applied", "row": rows[0]}
                # A foreign/multiple/malformed positive representation is not an
                # acknowledgment and is not repaired by another request.
                return {"state": "unknown", "row": None}
            reconcile = response.status_code == 204 or response.status_code >= 500
        if reconcile:
            read = self.read_episode(original["id"])
            row = read.get("row")
            if read["state"] == "read" and self._matches_claim(row, original, packet, record, autopsy=autopsy):
                return {"state": "applied", "row": row}
        return {"state": "unknown", "row": None}

    def claim_episode(self, original, packet, record):
        """Claim the existing eligible row using all original facts and a unique nonce."""
        from scripts.metabolism_journal import FabricHeld, fabric_digest
        from engine.neuralweb.trade_memory import normalize_episode
        params = self._fact_params(original)
        if (original.get("autopsy_state") not in ("pending", "retry")
                or original.get("autopsy") is not None or fabric_claim_present(original)
                or record["kind"] != "trade_memory" or record["unit"] != original["id"]
                or record["logical"].get("operator") != self.operator_user_id
                or record["logical"].get("episode") != original["id"]
                or record["logical"].get("facts") != normalize_episode(original)
                or record["logical"].get("packet_digest") != fabric_digest(packet)
                or record["state"] != "claimed" or _CLAIM_KEY in packet):
            raise FabricHeld("trade_memory_original_held")
        params.update({"autopsy_state": "eq."+original["autopsy_state"], "autopsy": "is.null",
                       "evidence_packet": _unclaimed_packet_filter(original),
                       "evidence_packet->"+_CLAIM_KEY: "is.null"})
        body = {"evidence_packet": {**copy.deepcopy(packet), _CLAIM_KEY: _claim_envelope(record)},
                "autopsy_state": "running", "autopsy_error": None, "autopsy_model": None}
        return self._conditional_write(original, params, body, packet, record)

    def transition_claim(self, original, current_row, packet, record, *, autopsy=None):
        from scripts.metabolism_journal import validate_transition, fabric_digest
        previous = _row_claim(current_row)
        validate_transition(previous, record)
        params = self._fact_params(original)
        params.update({"autopsy_state": "eq.running",
            "evidence_packet->"+_CLAIM_KEY+"->>record_digest": "eq."+fabric_digest(previous),
            "evidence_packet->"+_CLAIM_KEY+"->record->>attempt_nonce": "eq."+previous["attempt_nonce"],
            "evidence_packet->"+_CLAIM_KEY+"->record->>operation_id": "eq."+previous["operation_id"]})
        body = {"evidence_packet": {**copy.deepcopy(packet), _CLAIM_KEY: _claim_envelope(record)},
                "autopsy_state": "complete" if record["state"] == "complete" else "running",
                "autopsy_error": record["error"]}
        if record["state"] == "complete":
            from datetime import datetime, timezone
            body.update(autopsy=copy.deepcopy(autopsy), autopsy_model=record["receipt"]["served_model"],
                        autopsied_at=datetime.now(timezone.utc).isoformat())
        return self._conditional_write(original, params, body, packet, record, autopsy=autopsy)

    def update_episode(self, episode_id: str, patch: dict[str, Any]) -> bool:
        if not self.available or not _UUID_RE.fullmatch(str(episode_id or "")):
            return False
        # Whitelist prevents a caller from moving a row to another owner or changing
        # the trade facts during the autopsy pass.
        allowed = {
            "evidence_packet",
            "autopsy",
            "autopsy_state",
            "autopsy_model",
            "autopsied_at",
            "autopsy_error",
            "updated_at",
        }
        body = {k: v for k, v in patch.items() if k in allowed}
        if not body:
            return False
        read = self.read_episode(episode_id)
        if read["state"] != "read":
            return False
        try:
            packet_filter = _unclaimed_packet_filter(read["row"])
        except ValueError:
            return False
        headers = {**self._headers, "Prefer": "return=representation"}
        params = {
            "id": f"eq.{episode_id}",
            "user_id": f"eq.{self.operator_user_id}",
            "evidence_packet": packet_filter,
            # Stale native exception handlers cannot erase a selected claim,
            # including an explicit malformed/null envelope or selector removal.
            "evidence_packet->" + _CLAIM_KEY: "is.null",
        }
        try:
            response = self.session.patch(
                self._url("trade_episodes"),
                headers=headers,
                params=params,
                data=json.dumps(body, ensure_ascii=False, default=str),
                timeout=25,
            )
            rows = self._strict_rows(response)
            return (len(rows) == 1 and rows[0].get("id") == episode_id
                    and rows[0].get("user_id") == self.operator_user_id
                    and all(rows[0].get(key) == value for key, value in body.items()))
        except Exception as exc:  # noqa: BLE001
            log.warning("trade_memory_store: episode update failed (%s)", type(exc).__name__)
            return False

    def replace_patterns(self, patterns: list[dict[str, Any]]) -> bool:
        """Replace the operator's derived pattern view (rebuildable from episodes)."""
        if not self.available:
            return False
        owner = quote(self.operator_user_id, safe="")
        try:
            deleted = self.session.delete(
                self._url("trade_memory_patterns"),
                headers={**self._headers, "Prefer": "return=minimal"},
                params={"user_id": f"eq.{owner}"},
                timeout=25,
            )
            if deleted.status_code not in (200, 204):
                log.warning("trade_memory_store: pattern reset HTTP %s", deleted.status_code)
                return False
            if not patterns:
                return True
            rows = [
                {
                    "user_id": self.operator_user_id,
                    "feature_key": p.get("feature_key"),
                    "pattern": p,
                    "status": p.get("status") or "accruing",
                }
                for p in patterns
            ]
            inserted = self.session.post(
                self._url("trade_memory_patterns"),
                headers={**self._headers, "Prefer": "return=minimal"},
                data=json.dumps(rows, ensure_ascii=False, default=str),
                timeout=25,
            )
            return inserted.status_code in (200, 201, 204)
        except Exception as exc:  # noqa: BLE001
            log.warning("trade_memory_store: pattern replace failed (%s)", type(exc).__name__)
            return False


def build_store() -> SupabaseTradeMemoryStore | None:
    """Build the production store from the existing operator bridge secrets."""
    base_url = os.environ.get("SUPABASE_URL", "").strip()
    if not base_url:
        try:
            from lib import config  # noqa: PLC0415
            base_url = str(
                ((config.load().get("watchlist") or {}).get("supabase") or {}).get("url") or ""
            )
        except Exception:  # noqa: BLE001
            base_url = ""
    key = (
        os.environ.get("SUPABASE_SERVICE_KEY")
        or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        or ""
    )
    owner = os.environ.get("SUPABASE_OPERATOR_USER_ID") or ""
    store = SupabaseTradeMemoryStore(base_url, key, owner)
    return store if store.available else None


class PrivateFabricInvocation:
    """A live claim handle for the existing private row; never reconstruct to resend."""
    def __init__(self, store, original, packet, record, factory, cfg):
        from scripts.metabolism_journal import FabricHeld
        if not isinstance(store, SupabaseTradeMemoryStore):
            raise FabricHeld("trade_memory_conditional_owner_required")
        self.store, self.original = store, copy.deepcopy(original)
        self.packet, self.record = copy.deepcopy(packet), copy.deepcopy(record)
        self.factory, self.cfg = factory, copy.deepcopy(cfg)
        self._send_started = False
        result = store.claim_episode(self.original, self.packet, self.record)
        if result["state"] != "applied":
            raise FabricHeld("trade_memory_claim_" + result["state"])
        self.row = copy.deepcopy(result["row"])

    def confirm_claim(self):
        from scripts.metabolism_journal import FabricHeld
        result = self.store.read_episode(self.original["id"])
        if result["state"] != "read" or not self.store._matches_claim(
                result["row"], self.original, self.packet, self.record):
            raise FabricHeld("trade_memory_claim_changed_before_bind")

    def save(self, updated, *, autopsy=None):
        from scripts.metabolism_journal import FabricHeld
        result = self.store.transition_claim(self.original, self.row, self.packet, updated, autopsy=autopsy)
        if result["state"] != "applied":
            raise FabricHeld("trade_memory_completion_" + result["state"])
        self.record, self.row = copy.deepcopy(updated), copy.deepcopy(result["row"])

    def call(self):
        from scripts.metabolism_journal import FabricHeld, execute_claimed_model
        if self._send_started or self.record["state"] != "claimed":
            raise FabricHeld("trade_memory_send_not_owned")
        self._send_started = True
        return execute_claimed_model(self.record, self.factory, self.cfg, self.save, self.confirm_claim)

    def publication_intent(self, autopsy):
        from scripts.metabolism_journal import fabric_digest
        updated = copy.deepcopy(self.record)
        updated.update(state="publishing", business={"intent": {
            "owner": "private_episode", "autopsy_digest": fabric_digest(autopsy)}, "outcome": None})
        self.save(updated)

    def complete(self, autopsy):
        from scripts.metabolism_journal import fabric_digest
        updated = copy.deepcopy(self.record)
        updated["state"] = "complete"
        updated["business"]["outcome"] = {"status": "complete", "autopsy_digest": fabric_digest(autopsy)}
        self.save(updated, autopsy=autopsy)

    def hold(self, reason):
        if self.record["state"] in ("known", "publishing"):
            updated = copy.deepcopy(self.record)
            updated.update(state="held", error=reason)
            self.save(updated)
