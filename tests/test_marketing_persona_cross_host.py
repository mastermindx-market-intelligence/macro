"""Cross-host durability of persona publication memory.

THE DEFECT THESE TESTS PIN. `scripts/marketing_publisher` writes two records on
one `if receipt.ok:` branch, forty lines apart, with opposite durability:

    _append_publication(...)   -> data/marketing/publications.jsonl   TRACKED,
                                  committed back by marketing-publish.yml,
                                  therefore visible to every host
    _record_persona_post(...)  -> data/marketing/personas_host/...    GITIGNORED,
                                  therefore visible to NO host but the writer

The publisher runs on `macstudio-light`, the nightly consolidator on
`macstudio`, the reply desk on the VPS — three checkouts. So a post shipped by
one host was invisible to the persona ledger advanced by another, and silently
so: an absent spool and an idle host leave identical evidence. Measured on main
at 2026-09-18, `data/marketing/publications.jsonl` held 1,138 live publications
over 46 days and 7 accounts while `data/marketing/personas/` did not exist at
all, so every per-quirk frequency cap was evaluating against an empty store.

THE HARNESS IS THE POINT. `Fleet` below models three real checkouts and the ONE
thing that actually moves state between them — the git commit-back of the
tracked ledgers. It deliberately does NOT copy `personas_host/`, because
`.gitignore` does not. Publications are made through the publisher's OWN
`_publication_row` / `_record_persona_post`, not through a hand-rolled stand-in,
so a change to the production receipt shape breaks these tests rather than
quietly invalidating them.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engine.marketing import expression_dial as ed  # noqa: E402
from engine.marketing import persona_memory as pm  # noqa: E402

#: A dial-governed account (has a voice codex, therefore has caps to feed) and
#: an ungoverned one. Both are real roster accounts — on the production ledger
#: `flagship` and `mastermind_news` account for 944 of 1,138 live publications
#: and the live path stores NONE of them, so an over-eager reconciler would
#: invent 944 records rather than recover any.
GOVERNED = "meagan"
UNGOVERNED = "flagship"

NOW = datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def publisher():
    """The real `scripts/marketing_publisher` module, loaded by path.

    Same technique `tests/test_marketing_desk_feeds.py` already uses. Loading the
    production module is what makes this a test of the shipping code rather than
    of a re-implementation of it.
    """
    spec = importlib.util.spec_from_file_location(
        "_mp_cross_host", ROOT / "scripts" / "marketing_publisher.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Fleet:
    """Three checkouts and the git commit-back that is the only link between them."""

    #: What `marketing-publish.yml` actually runs:
    #:   git add data/marketing/outbox
    #:   git add data/marketing/publications.jsonl
    #: `personas_host/` is absent from that list because `.gitignore` excludes it.
    SHARED = ("data/marketing/publications.jsonl", "data/marketing/outbox/items.jsonl")

    def __init__(self, tmp_path: Path, publisher):
        self.pub = publisher
        self.hosts = {}
        for name in ("vps", "light", "mac"):
            root = tmp_path / name
            (root / "data" / "marketing" / "outbox").mkdir(parents=True, exist_ok=True)
            self.hosts[name] = root

    def root(self, host: str) -> Path:
        return self.hosts[host]

    def publish(
        self,
        host: str,
        account: str,
        text: str,
        *,
        item_id: str,
        as_of: str = "2026-09-18",
        published_at: str = "2026-09-18T15:00:00Z",
        kind: str = "macro",
        franchise: str = "",
        mode: str = "live",
        record_memory: bool = True,
    ) -> dict:
        """Ship one post from `host`, exactly as the posting-success branch does."""
        root = self.hosts[host]
        item = {
            "id": item_id,
            "account": account,
            "as_of": as_of,
            "kind": kind,
            "text": text,
            "status": "posted",
            "source": {"franchise": franchise} if franchise else {},
            "schema": "v1",
        }
        self._append(root / "data/marketing/outbox/items.jsonl", item)

        receipt = SimpleNamespace(
            ok=True, backend="x", external_id=f"x-{item_id}",
            external_url=f"https://x.com/i/{item_id}", at=published_at, error=None,
        )
        row = self.pub._publication_row(item, text, receipt, published_at=published_at)
        row["mode"] = mode
        self._append(root / "data/marketing/publications.jsonl", row)

        if record_memory:
            # The gitignored half. `record_memory=False` models the host whose
            # spool write failed (the helper is fail-soft by design).
            self.pub._record_persona_post(root, item, account, text, NOW)
        return item

    def commit_back(self) -> None:
        """Union every host's TRACKED ledgers and hand the union to every host.

        This is `git add <tracked> && git pull --rebase && git push` compressed to
        its observable effect on append-only JSONL. The gitignored persona spool
        is pointedly not included — that omission IS the defect under test.
        """
        for rel in self.SHARED:
            merged: list[str] = []
            seen: set[str] = set()
            for root in self.hosts.values():
                p = root / rel
                if not p.exists():
                    continue
                for line in p.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and line not in seen:
                        seen.add(line)
                        merged.append(line)
            body = "".join(x + "\n" for x in merged)
            for root in self.hosts.values():
                out = root / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(body, encoding="utf-8")

    def consolidate(self, host: str, **kw) -> dict:
        return pm.consolidate(now=NOW, root=self.hosts[host], **kw)

    def phrases(self, host: str, account: str) -> list[dict]:
        p = pm.repo_dir(self.hosts[host], account) / "phrases.jsonl"
        if not p.exists():
            return []
        return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]

    @staticmethod
    def _append(path: Path, obj: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n")


@pytest.fixture()
def fleet(tmp_path, publisher):
    return Fleet(tmp_path, publisher)


# ═════════════════════════════════════════════════════════════════════════════
# §1 THE DEFECT — reproduced, then closed
# ═════════════════════════════════════════════════════════════════════════════
def test_the_persona_spool_does_not_travel_but_the_receipt_does(fleet):
    """The asymmetry itself, stated as an assertion.

    Both writes happen on one success branch. After the commit-back that every
    host really performs, exactly one of the two has crossed.
    """
    fleet.publish("vps", GOVERNED, "Breadth is the tell, not the index.", item_id="ob-1")
    fleet.commit_back()

    mac = fleet.root("mac")
    assert (mac / "data/marketing/publications.jsonl").exists(), \
        "the publication receipt did not cross hosts — the harness does not model the real lane"
    assert not (mac / "data/marketing/personas_host").exists(), \
        "the gitignored persona spool crossed hosts; .gitignore says it cannot"


def test_cross_host_loss_reproduces_when_reconciliation_is_removed(fleet, monkeypatch, capsys):
    """PRE-FIX BEHAVIOUR, on the same harness: the post is lost, silently.

    Disabling reconciliation is exactly the old code path — fold the local spool
    and nothing else. The consolidating host has no spool of its own, so it
    produced no accounts and skipped every publication another host had shipped.
    """
    monkeypatch.setattr(
        pm, "reconcile_publications",
        lambda **kw: ({}, {"recovered": 0, "considered": 0, "unresolved": [], "sources": {}}),
    )
    fleet.publish("vps", GOVERNED, "Breadth is the tell, not the index.", item_id="ob-1")
    fleet.commit_back()

    summary = fleet.consolidate("mac")

    assert fleet.phrases("mac", GOVERNED) == [], \
        "the pre-fix path must lose the VPS post — otherwise this test proves nothing"
    assert summary["accounts"] == {}, "pre-fix, the consolidator saw no accounts at all"
    # And it said nothing about it. That silence is the whole bug.
    assert "::warning" not in capsys.readouterr().out


def test_one_publication_from_another_host_converges_exactly_once(fleet):
    """POST-FIX: the same run recovers the post, once."""
    fleet.publish("vps", GOVERNED, "Breadth is the tell, not the index.", item_id="ob-1")
    fleet.commit_back()

    fleet.consolidate("mac")

    rows = fleet.phrases("mac", GOVERNED)
    assert len(rows) == 1, f"expected exactly one record, got {len(rows)}"
    assert rows[0]["text"] == "Breadth is the tell, not the index."
    assert rows[0]["item_id"] == "ob-1"
    assert rows[0]["source"] == "reconciled", \
        "provenance must say the record was recovered, not emitted here"


def test_recovered_record_is_identical_in_identity_to_the_emitted_one(fleet):
    """The recovered record carries the SAME id the emitting host minted.

    This is what makes exactly-once hold across hosts without a new identity
    scheme: `_record_key` is already host-independent.
    """
    fleet.publish("vps", GOVERNED, "Credit is the test.", item_id="ob-1")
    emitted = fleet.phrases("vps", GOVERNED)  # not yet consolidated on the VPS
    spool = pm.host_dir(fleet.root("vps"), GOVERNED) / "phrases.jsonl"
    emitted = [json.loads(x) for x in spool.read_text(encoding="utf-8").splitlines() if x.strip()]
    fleet.commit_back()
    fleet.consolidate("mac")

    got = fleet.phrases("mac", GOVERNED)
    assert len(got) == 1 and len(emitted) == 1
    assert got[0]["id"] == emitted[0]["id"], (
        "the recovered record has a different identity than the emitted one — "
        "they would survive dedup as two copies of one post"
    )


# ═════════════════════════════════════════════════════════════════════════════
# §2 IDEMPOTENCE — replay, duplicate receipts, stale spools, self-healing
# ═════════════════════════════════════════════════════════════════════════════
def test_replay_of_the_consolidator_does_not_double_count(fleet):
    """A retried nightly must converge, not accumulate.

    A doubled phrase record inflates both sides of `max_share_7d` and doubles
    `max_per_day` — a replay bug here silently TIGHTENS the caps.
    """
    fleet.publish("vps", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    fleet.commit_back()

    for _ in range(3):
        fleet.consolidate("mac")

    assert len(fleet.phrases("mac", GOVERNED)) == 1


def test_a_duplicated_publication_receipt_yields_one_record(fleet):
    """Two identical receipt rows — what a rebase or a re-append leaves behind."""
    item = fleet.publish("vps", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    # Re-append the same receipt row to the shared ledger.
    src = fleet.root("vps") / "data/marketing/publications.jsonl"
    row = src.read_text(encoding="utf-8").splitlines()[-1]
    with src.open("a", encoding="utf-8") as fh:
        fh.write(row + "\n")
    fleet.commit_back()

    fleet.consolidate("mac")

    assert len(fleet.phrases("mac", GOVERNED)) == 1, "a duplicated receipt double-counted"
    assert item["id"] == "ob-1"


def test_the_emitting_host_keeps_its_own_record_and_does_not_duplicate_it(fleet):
    """STALE LOCAL SPOOL: the publishing host consolidates its own post.

    The spool has it and the shared receipt ledger offers it again. One record
    must survive, and it must keep the `emit` provenance — a host that actually
    observed the send is a better witness than a reconstruction of it.
    """
    fleet.publish("light", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    fleet.commit_back()

    fleet.consolidate("light")

    rows = fleet.phrases("light", GOVERNED)
    assert len(rows) == 1, "the host's own spool and its receipt produced two records"
    assert rows[0]["source"] == "emit", "the emitted record lost to its reconciled twin"


def test_a_stale_spool_reconsolidated_after_the_ledger_already_has_it(fleet):
    """The spool is re-fed after a completed consolidation; nothing doubles."""
    fleet.publish("light", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    fleet.commit_back()
    fleet.consolidate("light")  # truncates the local spool

    # A restarted daemon re-appends the same post it already shipped.
    pm.record_post(GOVERNED, "Breadth is the tell.", now=NOW, as_of="2026-09-18",
                   item_id="ob-1", root=fleet.root("light"))
    fleet.consolidate("light")

    assert len(fleet.phrases("light", GOVERNED)) == 1


def test_interrupted_transfer_is_reported_then_self_heals(fleet, capsys):
    """PARTIAL TRANSPORT FAILURE must be observable, never read as 'no publication'.

    The receipt crosses but its outbox item has not yet been committed — a real
    interleaving, since the two `git add` lines are separate paths in one push.
    The post is NOT recorded (its copy is unknown), it IS reported, and the next
    night — once the item lands — it converges without intervention.
    """
    fleet.publish("vps", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    fleet.commit_back()
    # The item half of the push did not land on the consolidator.
    (fleet.root("mac") / "data/marketing/outbox/items.jsonl").write_text("", encoding="utf-8")

    summary = fleet.consolidate("mac")
    out = capsys.readouterr().out

    assert fleet.phrases("mac", GOVERNED) == [], "copy text was unknown; nothing may be recorded"
    unresolved = summary["reconciliation"]["unresolved"]
    assert [u["reason"] for u in unresolved] == ["no_outbox_item"]
    assert "::warning title=persona_memory::" in out and "could not be reconciled" in out, \
        "a lost publication was not announced — this is the silence the fix exists to remove"

    # The missing half arrives; no operator action, no watermark to rewind.
    fleet.commit_back()
    fleet.consolidate("mac")
    assert len(fleet.phrases("mac", GOVERNED)) == 1, "the gap did not self-heal"


def test_a_missing_receipt_ledger_is_announced_not_assumed_empty(fleet, capsys):
    """No ledger is 'we cannot tell', not 'nothing published'."""
    (fleet.root("mac") / "data/marketing/publications.jsonl").unlink(missing_ok=True)

    summary = fleet.consolidate("mac")
    out = capsys.readouterr().out

    assert summary["reconciliation"]["unavailable"]
    assert "UNAVAILABLE" in out and "::warning title=persona_memory::" in out


# ═════════════════════════════════════════════════════════════════════════════
# §3 TWO HOSTS AT ONCE
# ═════════════════════════════════════════════════════════════════════════════
def test_two_hosts_publishing_concurrently_both_converge_exactly_once(fleet):
    """VPS and macstudio-light each ship a post; the consolidator sees both, once."""
    fleet.publish("vps", GOVERNED, "Breadth is the tell.", item_id="ob-vps")
    fleet.publish("light", GOVERNED, "Credit is the test.", item_id="ob-light")
    fleet.commit_back()

    fleet.consolidate("mac")

    rows = fleet.phrases("mac", GOVERNED)
    assert len(rows) == 2, f"expected both hosts' posts exactly once, got {len(rows)}"
    assert {r["item_id"] for r in rows} == {"ob-vps", "ob-light"}


def test_concurrent_hosts_converge_even_when_one_spool_write_failed(fleet):
    """`_record_persona_post` is fail-soft; the receipt is the durable witness.

    A spool write that raised used to mean the post was gone from memory
    forever. It is now recoverable, because the record the publisher committed
    is the one that crosses.
    """
    fleet.publish("vps", GOVERNED, "Breadth is the tell.", item_id="ob-1", record_memory=False)
    fleet.publish("light", GOVERNED, "Credit is the test.", item_id="ob-2")
    fleet.commit_back()

    fleet.consolidate("mac")

    assert {r["item_id"] for r in fleet.phrases("mac", GOVERNED)} == {"ob-1", "ob-2"}


# ═════════════════════════════════════════════════════════════════════════════
# §4 WHAT MUST *NOT* BE RECOVERED
# ═════════════════════════════════════════════════════════════════════════════
def test_an_ungoverned_account_is_never_reconciled(fleet):
    """No codex, no caps, no record — the live path stores nothing either.

    On the production ledger this is 944 of 1,138 live publications. A
    reconciler that ignored the codex filter would invent them.
    """
    assert ed.codex_for(UNGOVERNED) is None, "fixture assumption broke: this account gained a codex"
    fleet.publish("light", UNGOVERNED, "Index up, breadth flat.", item_id="ob-1")
    fleet.commit_back()

    summary = fleet.consolidate("mac")

    assert fleet.phrases("mac", UNGOVERNED) == []
    assert summary["reconciliation"]["recovered"] == 0


def test_a_dry_run_receipt_is_never_reconciled(fleet):
    """A post nobody saw must not spend a frequency budget."""
    fleet.publish("light", GOVERNED, "Breadth is the tell.", item_id="ob-1", mode="dry_run")
    fleet.commit_back()

    fleet.consolidate("mac")

    assert fleet.phrases("mac", GOVERNED) == []


def test_edited_copy_is_refused_and_reported(fleet, capsys):
    """The receipt's copy hash is the integrity gate on recovery.

    If the outbox row was edited after the post shipped, recording today's text
    against yesterday's publication puts words in a persona's mouth it never
    said. That is a gap, not a record.
    """
    fleet.publish("vps", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    fleet.commit_back()
    p = fleet.root("mac") / "data/marketing/outbox/items.jsonl"
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows[0]["text"] = "Breadth is the tell. (edited later)"
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")

    summary = fleet.consolidate("mac")

    assert fleet.phrases("mac", GOVERNED) == []
    assert [u["reason"] for u in summary["reconciliation"]["unresolved"]] == ["copy_hash_mismatch"]
    assert "copy_hash_mismatch" in capsys.readouterr().out


def test_publications_older_than_retention_are_not_resurrected(fleet):
    """Reconciliation respects the tracked ledger's own retention horizon."""
    old = (NOW - timedelta(days=pm.RETENTION_DAYS + 5))
    fleet.publish(
        "vps", GOVERNED, "An ancient take.", item_id="ob-old",
        as_of=old.strftime("%Y-%m-%d"), published_at=old.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    fleet.commit_back()

    fleet.consolidate("mac")

    assert fleet.phrases("mac", GOVERNED) == []


# ═════════════════════════════════════════════════════════════════════════════
# §5 THE BUSINESS-DATE HINGE — the one detail that decides exactly-once
# ═════════════════════════════════════════════════════════════════════════════
def test_a_post_whose_business_day_differs_from_its_wall_clock_folds_to_one(fleet):
    """`as_of` != `published_at` day, recorded live on one host and reconciled on another.

    `_record_key("phrases", ...)` hashes `date|text`, and `record_post` takes
    `date` from the content plan's `as_of`, not the wall clock. A reconciler
    that reached for `published_at` would mint a second id for the same post.
    On the production ledger 63 of 1,138 live publications sit in exactly this
    position — Cici's 08:00 Hong Kong post is still the previous UTC day.
    """
    fleet.publish(
        "light", GOVERNED, "The HK morning read.", item_id="ob-1",
        as_of="2026-09-17", published_at="2026-09-18T00:30:00Z",
    )
    fleet.commit_back()

    fleet.consolidate("light")   # the emitting host folds its own spool
    fleet.consolidate("mac")     # a different host reconciles the same post

    light_rows = fleet.phrases("light", GOVERNED)
    mac_rows = fleet.phrases("mac", GOVERNED)
    assert len(light_rows) == 1 and len(mac_rows) == 1
    assert light_rows[0]["date"] == mac_rows[0]["date"] == "2026-09-17", \
        "the two writers disagreed about the post's business day"
    assert light_rows[0]["id"] == mac_rows[0]["id"], \
        "same post, two identities — this is the 63/1138 double-count hazard"


# ═════════════════════════════════════════════════════════════════════════════
# §6 THE DOWNSTREAM CONSUMER — the reason any of this matters
# ═════════════════════════════════════════════════════════════════════════════
def test_the_frequency_cap_sees_a_post_shipped_by_another_host(fleet):
    """THE PAYOFF. A signature opener spent on the VPS must be spent everywhere.

    `expression_dial.frequency_violations` returns `[]` against an empty
    `recent`, so before this repair an account could open with the same
    capped line every single day from a host the consolidator never read.
    """
    codex = ed.codex_for(GOVERNED)
    decl = codex.declared["okay_so_opener"]
    assert decl.max_per_day == 1

    text = "okay so — the tape is quiet today. Breadth is the tell."
    fleet.publish("vps", GOVERNED, text, item_id="ob-1", as_of="2026-09-18")
    fleet.commit_back()

    # Before consolidation the Mac Studio has never heard of this post.
    blind = ed.frequency_violations(
        text, codex=codex, as_of="2026-09-18",
        recent=pm.recent_posts(GOVERNED, now=NOW, root=fleet.root("mac")),
    )
    assert blind == [], "fixture assumption broke: the cap fired before the post was known"

    fleet.consolidate("mac")

    recent = pm.recent_posts(GOVERNED, now=NOW, root=fleet.root("mac"))
    assert len(recent) == 1, "the consumer does not see the reconciled post"
    violations = ed.frequency_violations(text, codex=codex, as_of="2026-09-18", recent=recent)
    assert violations and any("max_per_day" in v for v in violations), (
        "the per-day cap is still blind to a post shipped by another host — "
        "the fatigue/cadence reader has not converged"
    )


def test_ngram_fatigue_counts_reconciled_posts(fleet):
    """The anti-sameness diagnostic reads the converged store too."""
    line = "the base rate says wait for the retest"
    for i, day in enumerate(("2026-09-16", "2026-09-17", "2026-09-18")):
        fleet.publish("vps", GOVERNED, f"{line} number {i}.", item_id=f"ob-{i}",
                      as_of=day, published_at=f"{day}T15:00:00Z")
    fleet.commit_back()
    fleet.consolidate("mac")

    fatigue = pm.ngram_fatigue(GOVERNED, now=NOW, root=fleet.root("mac"))
    assert fatigue.get("the base rate") == 3, \
        f"repetition across reconciled posts is invisible to the fatigue reader: {fatigue}"


# ═════════════════════════════════════════════════════════════════════════════
# §7 STRUCTURAL GUARDS
# ═════════════════════════════════════════════════════════════════════════════
def test_the_publications_path_cannot_drift_from_the_publisher(publisher):
    """Two modules name one ledger; a rename must not silently unhook the join."""
    assert Path(*pm._PUBLICATIONS_REL) == publisher._PUBLICATIONS_REL, (
        "persona_memory and marketing_publisher disagree about where the publication "
        "receipt ledger lives — reconciliation would read an empty file forever"
    )


def test_reconciliation_reads_only_and_names_what_it_cannot_cover(fleet):
    """No new ledger, no new transport, and an honest scope statement.

    The two inputs are pre-existing TRACKED ledgers; reconciliation must leave
    both untouched, and must say in its own report which stores a per-post
    receipt cannot speak for.
    """
    fleet.publish("vps", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    fleet.commit_back()
    before = {
        rel: (fleet.root("mac") / rel).read_bytes()
        for rel in Fleet.SHARED
    }

    summary = fleet.consolidate("mac")

    for rel, blob in before.items():
        assert (fleet.root("mac") / rel).read_bytes() == blob, \
            f"reconciliation mutated {rel}; it must be read-only"
    recon = summary["reconciliation"]
    assert recon["stores_reconciled"] == ["phrases"]
    assert recon["stores_not_reconciled"] == ["promises", "relations"]


def test_copy_hash_verification_matches_the_publishers_own_hash(fleet, publisher):
    """The gate uses the publisher's hash spelling, not a parallel one."""
    text = "Breadth is the tell."
    receipt = SimpleNamespace(external_id="x-1", external_url="u", at="2026-09-18T15:00:00Z")
    row = publisher._publication_row({"id": "ob-1", "account": GOVERNED}, text, receipt,
                                     published_at="2026-09-18T15:00:00Z")
    assert row["effective_copy_hash"] == "sha256:" + hashlib.sha256(text.encode()).hexdigest()


# ═════════════════════════════════════════════════════════════════════════════
# §8 HARDENING — the identity must be REPRODUCED, never approximated
# ═════════════════════════════════════════════════════════════════════════════
def test_a_publication_with_no_business_date_is_refused_and_reported(fleet, capsys):
    """Without `as_of` the two writers would fall back to DIFFERENT wall clocks.

    `_phrase_day` falls back to `now` for `record_post` and to the receipt's
    `published_at` here. Those agree almost always and disagree exactly when a
    post straddles midnight UTC — minting a second id for a post that shipped
    once. The identity has to be reproduced, not approximated, so a missing
    business date is a reported gap rather than a guessed record.
    """
    fleet.publish("vps", GOVERNED, "A post with no plan date.", item_id="ob-1", as_of="")
    fleet.commit_back()

    summary = fleet.consolidate("mac")

    assert fleet.phrases("mac", GOVERNED) == []
    assert [u["reason"] for u in summary["reconciliation"]["unresolved"]] == ["no_business_date"]
    assert "no_business_date" in capsys.readouterr().out, "the refusal was not announced"


def test_midnight_straddle_cannot_double_count(fleet):
    """The concrete scenario the refusal above exists to prevent.

    Publisher records at 23:59:58 on one day; the receipt is stamped 00:00:04 the
    next. With a business date both writers agree; the record folds to one.
    """
    late = datetime(2026, 9, 17, 23, 59, 58, tzinfo=timezone.utc)
    text = "The last print before the bell."
    item = {"id": "ob-1", "account": GOVERNED, "as_of": "2026-09-17",
            "kind": "macro", "text": text, "source": {}, "schema": "v1"}
    Fleet._append(fleet.root("light") / "data/marketing/outbox/items.jsonl", item)
    receipt = SimpleNamespace(external_id="x-1", external_url="u", at="2026-09-18T00:00:04Z")
    row = fleet.pub._publication_row(item, text, receipt, published_at="2026-09-18T00:00:04Z")
    row["mode"] = "live"
    Fleet._append(fleet.root("light") / "data/marketing/publications.jsonl", row)
    # The live write happens on the PREVIOUS day's wall clock.
    fleet.pub._record_persona_post(fleet.root("light"), item, GOVERNED, text, late)

    fleet.commit_back()
    fleet.consolidate("light")

    rows = fleet.phrases("light", GOVERNED)
    assert len(rows) == 1, f"a midnight straddle double-counted: {[r['date'] for r in rows]}"
    assert rows[0]["date"] == "2026-09-17", "the business day lost to the wall clock"


def test_a_malformed_item_row_does_not_crash_the_nightly(fleet):
    """`source` is free-form; a non-dict must degrade, not raise.

    `consolidate()` is a nightly step whose contract is never-raise.
    """
    fleet.publish("vps", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    fleet.commit_back()
    p = fleet.root("mac") / "data/marketing/outbox/items.jsonl"
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows[0]["source"] = "not-a-dict"
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")

    fleet.consolidate("mac")  # must not raise

    rows = fleet.phrases("mac", GOVERNED)
    assert len(rows) == 1 and rows[0]["franchise"] == ""


def test_a_reconciliation_failure_still_advances_the_local_spool(fleet, monkeypatch, capsys):
    """A degraded reconciliation must not cost the host its own consolidation."""
    def boom(**kw):
        raise RuntimeError("ledger unreadable")

    fleet.publish("light", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    monkeypatch.setattr(pm, "reconcile_publications", boom)

    summary = fleet.consolidate("light")
    out = capsys.readouterr().out

    assert len(fleet.phrases("light", GOVERNED)) == 1, \
        "the host's own spool was lost because reconciliation failed"
    assert "reconciliation raised" in str(summary["reconciliation"]["unavailable"])
    assert "::warning title=persona_memory::" in out and "UNAVAILABLE" in out


def test_non_dict_ledger_rows_are_skipped(fleet):
    """Ledger files are append-only text; junk lines must not stop the join."""
    fleet.publish("vps", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    fleet.commit_back()
    for rel in Fleet.SHARED:
        p = fleet.root("mac") / rel
        p.write_text('"a bare string"\n[1,2,3]\nnot json at all\n' + p.read_text(encoding="utf-8"),
                     encoding="utf-8")

    fleet.consolidate("mac")

    assert len(fleet.phrases("mac", GOVERNED)) == 1


def test_a_malformed_receipt_is_reported_not_skipped(fleet, capsys):
    """A LIVE receipt we cannot even address is the archetype of silent loss.

    Something published and we cannot say what or for whom. Dropping it quietly
    is the exact behaviour this repair exists to remove.
    """
    fleet.publish("vps", GOVERNED, "Breadth is the tell.", item_id="ob-1")
    fleet.commit_back()
    p = fleet.root("mac") / "data/marketing/publications.jsonl"
    rows = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows[0]["asset_id"] = ""
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")

    summary = fleet.consolidate("mac")

    assert [u["reason"] for u in summary["reconciliation"]["unresolved"]] == ["malformed_receipt"]
    assert "malformed_receipt" in capsys.readouterr().out


def test_the_report_arithmetic_reconciles(fleet):
    """`considered` must equal recovered + aged_out + the unresolved it counted.

    A report whose numbers do not add up sends a reader hunting for a loss that
    is really an accounting gap — or worse, lets a real one hide in the slack.
    """
    old = NOW - timedelta(days=pm.RETENTION_DAYS + 5)
    fleet.publish("vps", GOVERNED, "A current take.", item_id="ob-new")
    fleet.publish("vps", GOVERNED, "An ancient take.", item_id="ob-old",
                  as_of=old.strftime("%Y-%m-%d"),
                  published_at=old.strftime("%Y-%m-%dT%H:%M:%SZ"))
    fleet.publish("vps", GOVERNED, "An unjoinable take.", item_id="ob-gone")
    fleet.commit_back()
    # Drop one item so its publication cannot be resolved.
    p = fleet.root("mac") / "data/marketing/outbox/items.jsonl"
    keep = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    keep = [r for r in keep if r["id"] != "ob-gone"]
    p.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in keep), encoding="utf-8")

    recon = fleet.consolidate("mac")["reconciliation"]

    counted = len([u for u in recon["unresolved"] if u["reason"] != "malformed_receipt"])
    assert recon["considered"] == recon["recovered"] + recon["aged_out"] + counted, recon
    assert recon["recovered"] == 1 and recon["aged_out"] == 1 and counted == 1


def test_an_absent_ledger_and_an_empty_one_do_not_print_the_same(fleet):
    """'we cannot tell' and 'nothing published' are different facts."""
    (fleet.root("mac") / "data/marketing/publications.jsonl").unlink(missing_ok=True)
    absent = fleet.consolidate("mac")["reconciliation"]["unavailable"]

    (fleet.root("mac") / "data/marketing/publications.jsonl").write_text("", encoding="utf-8")
    empty = fleet.consolidate("mac")["reconciliation"]["unavailable"]

    assert absent and empty and absent != empty, (absent, empty)
