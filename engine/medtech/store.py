"""Private append-only evidence and revision history for the MedTech domain.

The application never opens this database. A worker commits complete, byte-backed
acquisitions here and separately publishes a validated product projection.
Unchanged re-fetches add a receipt, not another change; A -> B -> A is a real
third version. No observation time or source evidence is overwritten.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
from typing import Iterator

from collectors.medtech.openfda import SourceBatch, validate_batch
from engine.medtech.events import MedTechError, changes_between, instant, utc
from engine.sector_intelligence import canonical_json_bytes, canonical_json_sha256

SCHEMA_VERSION = 2
PARSER_VERSION = "medtech_openfda_v2"


class EventStore:
    def __init__(self, path: Path | str, *, create: bool = False):
        self.path = Path(path)
        if self.path.is_symlink():
            raise MedTechError("STORE_PATH_INVALID")
        if not self.path.exists() and not create:
            raise MedTechError("STORE_UNAVAILABLE")
        if create:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.db = sqlite3.connect(self.path, timeout=10)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA foreign_keys=ON")
            version = self.db.execute("PRAGMA user_version").fetchone()[0]
            existing = self.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if version == 0 and not existing and create:
                self._initialize()
            elif version != SCHEMA_VERSION:
                raise MedTechError("STORE_SCHEMA_MISMATCH")
            columns = {row[1] for row in self.db.execute("PRAGMA table_info(acquisitions)")}
            sighting_columns = {row[1] for row in self.db.execute("PRAGMA table_info(sightings)")}
            observation_columns = {row[1] for row in self.db.execute("PRAGMA table_info(observations)")}
            if ("parser_version" not in columns or "raw_record_hash" not in sighting_columns
                    or "change_kind" not in observation_columns):
                raise MedTechError("STORE_SCHEMA_MISMATCH")
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
        except (sqlite3.Error, MedTechError) as error:
            if hasattr(self, "db"):
                self.db.close()
            if isinstance(error, MedTechError):
                raise
            raise MedTechError("STORE_UNAVAILABLE") from None

    def _initialize(self) -> None:
        self.db.executescript("""
        BEGIN IMMEDIATE;
        CREATE TABLE acquisitions (
            run_id TEXT PRIMARY KEY,
            dataset TEXT NOT NULL,
            start_on TEXT NOT NULL,
            end_on TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            dataset_updated_at TEXT,
            record_count INTEGER NOT NULL CHECK(record_count >= 0),
            parser_version TEXT NOT NULL,
            UNIQUE(dataset, observed_at)
        );
        CREATE TABLE source_pages (
            run_id TEXT NOT NULL REFERENCES acquisitions(run_id),
            page_number INTEGER NOT NULL,
            request_url TEXT NOT NULL,
            payload BLOB NOT NULL,
            payload_sha256 TEXT NOT NULL,
            PRIMARY KEY(run_id, page_number)
        );
        CREATE TABLE observations (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            state_hash TEXT NOT NULL,
            event_json BLOB NOT NULL,
            run_id TEXT NOT NULL REFERENCES acquisitions(run_id),
            change_kind TEXT NOT NULL,
            UNIQUE(event_id, observed_at)
        );
        CREATE INDEX observation_event_time ON observations(event_id, observed_at, sequence);
        CREATE TABLE sightings (
            run_id TEXT NOT NULL REFERENCES acquisitions(run_id),
            event_id TEXT NOT NULL,
            raw_record_hash TEXT NOT NULL,
            PRIMARY KEY(run_id, event_id)
        );
        CREATE INDEX sighting_event ON sightings(event_id, run_id);
        PRAGMA user_version=2;
        COMMIT;
        """)

    def close(self) -> None:
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        try:
            self.db.execute("BEGIN IMMEDIATE")
            yield
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def ingest(self, batch: SourceBatch) -> dict:
        observations = validate_batch(batch)
        observed_at = utc(batch.observed_at)
        from hashlib import sha256

        run_id = canonical_json_sha256({
            "dataset": batch.dataset, "start": batch.start, "end": batch.end,
            "observed_at": observed_at, "parser_version": PARSER_VERSION,
            "pages": [sha256(raw).hexdigest() for raw in batch.pages],
        })
        try:
            with self._transaction():
                known = self.db.execute("SELECT run_id FROM acquisitions WHERE run_id=?",
                                        (run_id,)).fetchone()
                if known:
                    return {"run_id": run_id, "records": batch.total,
                            "new_versions": 0, "replayed": True}
                latest = self.db.execute(
                    "SELECT MAX(observed_at) FROM acquisitions WHERE dataset=?",
                    (batch.dataset,)).fetchone()[0]
                if latest and observed_at <= latest:
                    raise MedTechError("OBSERVATION_CLOCK_REGRESSION")
                self.db.execute("INSERT INTO acquisitions VALUES (?,?,?,?,?,?,?,?)",
                    (run_id, batch.dataset, batch.start, batch.end, observed_at,
                     batch.dataset_updated_at or None, batch.total, PARSER_VERSION))
                for i, (raw, url) in enumerate(zip(batch.pages, batch.request_urls)):
                    self.db.execute("INSERT INTO source_pages VALUES (?,?,?,?,?)",
                        (run_id, i, url, raw, sha256(raw).hexdigest()))
                new_versions = 0
                for observation in observations:
                    prior = self.db.execute(
                        "SELECT state_hash FROM observations WHERE event_id=? "
                        "ORDER BY observed_at DESC, sequence DESC LIMIT 1",
                        (observation.event_id,)).fetchone()
                    previous_sighting = self.db.execute(
                        "SELECT s.raw_record_hash,a.parser_version FROM sightings s "
                        "JOIN acquisitions a USING(run_id) WHERE s.event_id=? "
                        "ORDER BY a.observed_at DESC LIMIT 1", (observation.event_id,)).fetchone()
                    raw_hash = canonical_json_sha256(observation.raw)
                    self.db.execute("INSERT INTO sightings VALUES (?,?,?)",
                                    (run_id, observation.event_id, raw_hash))
                    if prior and prior["state_hash"] == observation.state_hash:
                        continue
                    kind = "first_observed"
                    if prior:
                        parser_changed = previous_sighting["parser_version"] != PARSER_VERSION
                        raw_changed = previous_sighting["raw_record_hash"] != raw_hash
                        if parser_changed:
                            kind = ("source_and_normalization_changed" if raw_changed
                                    else "normalization_changed")
                        elif raw_changed:
                            kind = "source_record_changed"
                        else:
                            raise MedTechError("UNVERSIONED_NORMALIZATION_CHANGE")
                    self.db.execute(
                        "INSERT INTO observations(event_id,observed_at,state_hash,event_json,run_id,change_kind) "
                        "VALUES (?,?,?,?,?,?)",
                        (observation.event_id, observed_at, observation.state_hash,
                         canonical_json_bytes(observation.event), run_id, kind))
                    new_versions += 1
                return {"run_id": run_id, "records": batch.total,
                        "new_versions": new_versions, "replayed": False}
        except sqlite3.Error:
            raise MedTechError("STORE_WRITE_FAILED") from None

    def snapshot(self, *, as_of: str) -> dict:
        as_of = utc(as_of)
        # One read transaction holds a coherent view across events and source health.
        try:
            with self._transaction():
                observations = self.db.execute(
                    "SELECT o.event_id,o.observed_at,o.event_json,o.state_hash,o.sequence,o.change_kind "
                    "FROM observations o JOIN acquisitions a USING(run_id) "
                    "WHERE o.observed_at<=? ORDER BY o.observed_at,o.sequence",
                    (as_of,)).fetchall()
                acquisitions = self.db.execute(
                    "SELECT * FROM acquisitions WHERE observed_at<=? ORDER BY observed_at",
                    (as_of,)).fetchall()
                sighting_rows = self.db.execute(
                    "SELECT s.event_id, MAX(a.observed_at) AS observed_at "
                    "FROM sightings s JOIN acquisitions a USING(run_id) "
                    "WHERE a.observed_at<=? GROUP BY s.event_id", (as_of,)).fetchall()
        except sqlite3.Error:
            raise MedTechError("STORE_READ_FAILED") from None
        last_seen = {row["event_id"]: row["observed_at"] for row in sighting_rows}
        grouped = {}
        for row in observations:
            from hashlib import sha256
            if sha256(row["event_json"]).hexdigest() != row["state_hash"]:
                raise MedTechError("STORE_STATE_DIGEST_MISMATCH")
            grouped.setdefault(row["event_id"], []).append(row)
        events = []
        for event_id, versions in grouped.items():
            event = json.loads(versions[-1]["event_json"])
            history = []
            for index, version in enumerate(versions):
                current = json.loads(version["event_json"])
                previous = json.loads(versions[index - 1]["event_json"]) if index else None
                # Public revision identifiers bind public state, never raw evidence paths.
                revision_id = canonical_json_sha256({
                    "event_id": event_id, "state": version["state_hash"],
                    "observed_at": version["observed_at"],
                })
                history.append({
                    "revision_id": revision_id,
                    "observed_at": version["observed_at"],
                    "decision_date": current["decision"]["date"],
                    "device_name": current["device"]["name"],
                    "kind": version["change_kind"],
                    "changes": changes_between(previous, current) if previous else [],
                })
            event["first_observed_at"] = versions[0]["observed_at"]
            event["last_observed_at"] = last_seen[event_id]
            event["last_changed_at"] = versions[-1]["observed_at"]
            event["revision_id"] = history[-1]["revision_id"]
            event["history"] = history
            events.append(event)
        events.sort(key=lambda item: (item["decision"]["date"] or "", item["event_id"]),
                    reverse=True)
        sources = {}
        for row in acquisitions:
            previous = sources.get(row["dataset"], {})
            sources[row["dataset"]] = {
                "dataset": row["dataset"], "last_checked_at": row["observed_at"],
                "dataset_updated_at": row["dataset_updated_at"] or previous.get("dataset_updated_at"),
                "cadence": "monthly", "timely_alert_source": False,
                "coverage": {"kind": "decision_date_range", "start": row["start_on"],
                             "end": row["end_on"], "records": row["record_count"],
                             "complete_for_query": True},
            }
        return {
            "schema": "medtech.watchdesk/v1",
            "generated_at": as_of,
            "sources": sorted(sources.values(), key=lambda item: item["dataset"]),
            "events": events,
            "capabilities": {
                "decision_history": True, "prospective_calendar": False,
                "company_economic_rights": False, "coverage_decisions": False,
                "safety_alerts": False, "delivered_notifications": False,
            },
        }
