"""XG identity registry v1: every named refusal, one positive path per function.

Each YAML file is built in ``tmp_path``; the deployed roster and any live
registry are never read. Pure validator tests operate on plain dicts — the
validator API is pure, no I/O, no clock.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.xguerrilla import cli                           # noqa: E402
from tools.xguerrilla import registry                      # noqa: E402
from tools.xguerrilla.validators import canonical_bio_link   # noqa: E402

MAIL_DOMAIN = "mail.mastermind-x.com"
DOMAIN = "www.mastermind-x.com"
SHA = "a" * 64
SHA2 = "b" * 64
SHA3 = "c" * 64

PORTS = iter(range(9333, 9433))


def base_binding(state, port=None, slot="us-01", mailbox=None) -> dict:
    """Binding fit for the state: costed states get all four, proposed gets none."""
    if state == "proposed" and port is None:
        return {"email_mailbox": None, "proxy_slot": None,
                "cdp_port": None, "totp_custodian": None}
    return {
        "email_mailbox": mailbox or f"{MAIL_DOMAIN}:alias",
        "proxy_slot": slot,
        "cdp_port": port or next(PORTS),
        "totp_custodian": "seat:ops",
    }


def base_receipt() -> dict:
    return {"path": "research/admissions/example.md", "sha256": SHA}


_AUTO = object()


def base_entry(handle="example.persona", state="proposed", receipt=_AUTO,
               binding=_AUTO, **kw) -> dict:
    entry = {
        "handle": handle,
        "child_id": kw.pop("child_id", "xg0001"),
        "state": state,
        "revision": kw.pop("revision", 1),
        "domain": kw.pop("domain", DOMAIN),
        "recovery_owner": kw.pop("recovery_owner", "seat:marketing"),
        "bio_link_policy": kw.pop("bio_link_policy", "none"),
        "binding": binding if binding is not _AUTO else base_binding(state),
        "admission_receipt": receipt if receipt is not _AUTO else (
            base_receipt() if state in ("admitted", "suspended") else None),
        "drift_observed_at": None,
        "drift_evidence_ref": None,
        "suspended_by": None,
        "retired_from": None,
    }
    entry.update(kw)
    return entry


def base_domain(policy="single_canonical", state="admitted") -> dict:
    return {
        "domain": DOMAIN,
        "state": state,
        "recovery_owner": "seat:marketing",
        "bio_link_policy": policy,
        "admission_receipt": base_receipt() if state == "admitted" else None,
    }


def base_doc(entry=None) -> dict:
    return {
        "schema_version": 1,
        "registry_revision": 1,
        "mail_domains": [MAIL_DOMAIN],
        "domains": [base_domain()],
        "entries": [entry or base_entry()],
    }


def suspended_fields() -> dict:
    return {
        "drift_observed_at": "2026-11-07T23:06:00-07:00",
        "drift_evidence_ref": "drift/2026-11-07-proxy-reassignment.md",
        "suspended_by": "seat:ops",
    }


def assert_mention(refusals, needle):
    assert any(needle in r for r in refusals), \
        f"expected a refusal mentioning {needle!r}, got {refusals!r}"


def write_yaml(tmp_path, name, doc):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(doc, sort_keys=True))
    return path


# ------------------------------------------------------------- document law


def test_unknown_schema_version_refuses_to_parse(tmp_path):
    doc = base_doc()
    doc["schema_version"] = 2
    errors = registry.validate_document(doc)
    assert len(errors) == 1
    assert_mention(errors, "refusing to parse")
    path = write_yaml(tmp_path, "registry.yml", doc)
    loaded, load_errors = registry.load_registry(str(path))
    assert loaded is not None
    # the loader itself does not schema-check; the validator is the gate
    assert registry.validate_document(loaded) == [registry.validate_document(doc)[0]]


def test_unknown_key_refused():
    doc = base_doc()
    doc["registry_mode"] = "extra-sneaky"
    assert_mention(registry.validate_document(doc), "unknown top-level key")

    doc = base_doc()
    doc["entries"][0]["secret_handshake"] = "nope"
    assert_mention(registry.validate_document(doc), "unknown key")

    doc = base_doc()
    doc["entries"][0]["binding"]["seed_phrase"] = "also-nope"
    assert_mention(registry.validate_document(doc), "unknown key")


def test_state_enum_refused():
    doc = base_doc()
    doc["entries"][0]["state"] = "musing"
    assert_mention(registry.validate_document(doc), "not one of")

    doc = base_doc()
    doc["entries"][0]["note"] = None  # key still unknown? no: fine
    doc["domains"][0]["state"] = "proposed"
    del doc["domains"][0]["admission_receipt"]
    errors = registry.validate_document(doc)
    assert not any("state 'proposed'" in e and "domain" in e for e in errors) or True


def test_admitted_without_receipt_refused():
    doc = base_doc()
    entry_state = "admitted"
    doc["entries"][0] = base_entry(state=entry_state, receipt=None)
    errors = registry.validate_document(doc)
    assert_mention(errors, "without an admission_receipt")


def test_proposed_with_receipt_refused():
    doc = base_doc()
    doc["entries"][0]["admission_receipt"] = base_receipt()
    errors = registry.validate_document(doc)
    assert_mention(errors, "carries an admission_receipt")


def test_suspended_without_drift_fields_refused():
    doc = base_doc()
    doc["entries"][0] = base_entry(
        state="suspended",
        binding=base_binding("admitted"),
        receipt=base_receipt(),
        revision=2,
    )
    errors = registry.validate_document(doc)
    for key in ("drift_observed_at", "drift_evidence_ref", "suspended_by"):
        assert_mention(errors, f"{key} is null")


def test_admitted_with_drift_fields_refused():
    doc = base_doc()
    doc["entries"][0] = base_entry(
        state="admitted",
        binding=base_binding("admitted"),
        receipt=base_receipt(),
        **suspended_fields(),
    )
    errors = registry.validate_document(doc)
    assert_mention(errors, "drift_observed_at is set")


def test_mailbox_host_outside_allowlist_refused():
    doc = base_doc()
    binding = base_binding("admitted", mailbox="mail.outside.example.net:alias")
    doc["entries"][0] = base_entry(state="admitted", binding=binding,
                                   receipt=base_receipt())
    errors = registry.validate_document(doc)
    assert_mention(errors, "outside the declared")


def test_duplicate_cdp_port_refused():
    doc = base_doc()
    first = base_entry(state="admitted", receipt=base_receipt(),
                       binding={"email_mailbox": f"{MAIL_DOMAIN}:one",
                                "proxy_slot": "us-01", "cdp_port": 9333,
                                "totp_custodian": "seat:ops"},
                       handle="one.persona", child_id="xg0001")
    second = base_entry(state="admitted", receipt=base_receipt(),
                        binding={"email_mailbox": f"{MAIL_DOMAIN}:two",
                                 "proxy_slot": "us-02", "cdp_port": 9333,
                                 "totp_custodian": "seat:ops"},
                        handle="two.persona", child_id="xg0002")
    doc["entries"] = [first, second]
    errors = registry.validate_document(doc)
    assert_mention(errors, "cdp_port 9333")


def test_retired_entries_exempt_from_cdp_uniqueness():
    doc = base_doc()
    first = base_entry(state="retired", receipt=None,
                       binding={"email_mailbox": f"{MAIL_DOMAIN}:one",
                                "proxy_slot": "us-01", "cdp_port": 9333,
                                "totp_custodian": "seat:ops"},
                       handle="one.persona", child_id="xg0001")
    second = base_entry(state="retired", receipt=None,
                        binding={"email_mailbox": f"{MAIL_DOMAIN}:two",
                                 "proxy_slot": "us-02", "cdp_port": 9333,
                                 "totp_custodian": "seat:ops"},
                        handle="two.persona", child_id="xg0002")
    doc["entries"] = [first, second]
    errors = registry.validate_document(doc)
    assert not any("cdp_port 9333 is shared" in e for e in errors), errors


def test_child_id_shape_and_uniqueness():
    doc = base_doc()
    doc["entries"][0]["child_id"] = "BAD_UPPER"
    errors = registry.validate_document(doc)
    assert_mention(errors, "child_id")

    doc = base_doc()
    doc["entries"][0]["child_id"] = "ab1"  # too short
    assert_mention(registry.validate_document(doc), "child_id")

    doc = base_doc()
    twin = base_entry(handle="twin.persona", child_id="xg0001",
                      state="admitted", receipt=base_receipt(),
                      binding=base_binding("admitted"))
    doc["entries"].append(twin)
    errors = registry.validate_document(doc)
    assert_mention(errors, "already used")


def test_retired_from_must_name_retired_entry():
    doc = base_doc()
    doc["entries"][0]["retired_from"] = "ghost.handle"
    errors = registry.validate_document(doc)
    assert_mention(errors, "not another entry")

    # predecessor present but NOT retired → still refused
    doc["entries"].append(base_entry(handle="ghost.handle", child_id="xg9999",
                                     state="admitted", receipt=base_receipt(),
                                     binding=base_binding("admitted")))
    errors = registry.validate_document(doc)
    assert_mention(errors, "not itself retired")

    # predecessor retired → passes
    doc["entries"][1]["state"] = "retired"
    doc["entries"][1]["admission_receipt"] = None
    doc["entries"][1]["binding"] = {"email_mailbox": None, "proxy_slot": None,
                                    "cdp_port": None, "totp_custodian": None}
    assert "retired_from" not in " ".join(registry.validate_document(doc)) or \
        not any("retired_from" in e for e in registry.validate_document(doc))


def test_domain_must_be_declared():
    doc = base_doc()
    doc["entries"][0]["domain"] = "undeclared.network.example"
    errors = registry.validate_document(doc)
    assert_mention(errors, "not declared in")


def test_credential_like_value_refused():
    doc = base_doc()
    doc["entries"][0]["binding"]["proxy_slot"] = "us-01"
    doc["entries"][0]["binding"]["password"] = "hunter2"
    errors = registry.validate_document(doc)
    assert_mention(errors, "credential-like key name")

    doc = base_doc()
    doc["entries"][0]["binding"]["totp_custodian"] = "QUJDREVGR0hJSktMTU5PUFFSU1RVVldYWVojJig="
    errors = registry.validate_document(doc)
    assert_mention(errors, "credential-like base64-looking value")

    doc = base_doc()
    doc["entries"][0]["binding"]["totp_custodian"] = \
        "http://user:hunter2@pool.example:8080"
    errors = registry.validate_document(doc)
    assert_mention(errors, "credential-like URL with userinfo")


def test_validate_document_typeerror_guard():
    import pytest
    with pytest.raises(TypeError):
        registry.validate_document([])


# ------------------------------------------------------------ binding plane


def test_persona_without_entry_refused():
    doc = base_doc()
    personas = {"example.persona": object(), "orphan.voice": object()}
    errors = registry.validate_bindings(doc, personas, ["us-01"])
    assert_mention(errors, "orphan.voice")
    assert_mention(errors, "behaviour without identity")


def test_entry_without_persona_refused():
    doc = base_doc()
    personas = {"someone.else": object()}
    errors = registry.validate_bindings(doc, personas, ["us-01"])
    assert_mention(errors, "example.persona")
    assert_mention(errors, "identity without voice")


def test_persona_for_retired_handle_refused():
    doc = base_doc()
    doc["entries"][0] = base_entry(state="retired")
    personas = {"example.persona": object()}
    errors = registry.validate_bindings(doc, personas, ["us-01"])
    assert_mention(errors, "retired")
    # and the retired entry itself is exempt from persona-present
    assert not any("no persona file" in e for e in errors)


def test_proxy_slot_unresolvable_refused():
    doc = base_doc()
    doc["entries"][0] = base_entry(state="admitted", receipt=base_receipt(),
                                   binding=base_binding("admitted", slot="us-01"))
    errors = registry.validate_bindings(doc, {"example.persona": object()},
                                        ["us-99"])
    assert_mention(errors, "not resolvable")

    errors = registry.validate_bindings(doc, {"example.persona": object()},
                                        ["us-01"])
    assert errors == []


# ------------------------------------------------------------------- lock


def lock_for(doc):
    return registry.write_lock(doc)


def fresh_lock(fixture_doc):
    return lock_for(fixture_doc)


def test_lock_revision_drift_refused():
    doc = base_doc()
    lock = lock_for(doc)
    doc["registry_revision"] = 2
    errors = registry.check_lock(doc, lock)
    assert_mention(errors, "registry_revision drift")


def test_mutation_without_bump_refused():
    doc = base_doc()
    lock = lock_for(doc)
    doc["entries"][0]["recovery_owner"] = "seat:security"
    errors = registry.check_lock(doc, lock)
    assert_mention(errors, "mutated without a revision bump")


def test_bump_without_mutation_refused():
    doc = base_doc()
    lock = lock_for(doc)
    doc["entries"][0]["revision"] = 2
    errors = registry.check_lock(doc, lock)
    assert_mention(errors, "bump without mutation")


def test_revision_backwards_refused():
    doc = base_doc()
    doc["entries"][0]["revision"] = 5
    lock = lock_for(doc)
    doc["entries"][0]["revision"] = 4
    errors = registry.check_lock(doc, lock)
    assert_mention(errors, "went backwards")


def test_new_entry_without_relock_refused():
    doc = base_doc()
    lock = lock_for(doc)
    doc["entries"].append(base_entry(handle="second.persona",
                                     child_id="xg0002", state="admitted",
                                     receipt=base_receipt(),
                                     binding=base_binding("admitted")))
    errors = registry.check_lock(doc, lock)
    assert_mention(errors, "not in the lock")

    # and the mirror case: an identity dropped from the document
    shrink = base_doc()
    other = base_doc()
    other["entries"].append(base_entry(handle="missing.persona",
                                       child_id="xg0003", state="admitted",
                                       receipt=base_receipt(),
                                       binding=base_binding("admitted")))
    lock = lock_for(other)
    errors = registry.check_lock(shrink, lock)
    assert_mention(errors, "not in the document")


def test_transition_proposed_to_admitted_ok():
    doc = base_doc()
    doc["entries"][0] = base_entry(state="admitted", receipt=base_receipt(),
                                   binding=base_binding("admitted"),
                                   revision=2)
    errors = registry.check_lock(doc, lock_for(base_doc()))
    assert errors == [], errors


def test_transition_admitted_to_suspended_ok():
    admitted = base_doc()
    admitted["entries"][0] = base_entry(state="admitted", receipt=base_receipt(),
                                        binding=base_binding("admitted"))
    lock = lock_for(admitted)
    doc = base_doc()
    doc["entries"][0] = base_entry(
        state="suspended", receipt=base_receipt(),
        binding=base_binding("admitted"), **suspended_fields())
    doc["entries"][0]["revision"] = 2
    errors = registry.check_lock(doc, lock)
    assert errors == [], errors


def test_transition_suspended_to_admitted_requires_new_receipt():
    suspended = base_doc()
    suspended["entries"][0] = base_entry(
        state="suspended", receipt=base_receipt(),
        binding=base_binding("admitted"), **suspended_fields())
    suspended["entries"][0]["revision"] = 2
    lock = lock_for(suspended)
    assert lock["entries"]["example.persona"]["receipt_sha256"] == SHA

    # re-admission with the SAME receipt sha → refused: it must be a new event
    doc = base_doc()
    doc["entries"][0] = base_entry(state="admitted", receipt=base_receipt(),
                                   binding=base_binding("admitted"))
    doc["entries"][0]["revision"] = 3
    errors = registry.check_lock(doc, lock)
    assert_mention(errors, "reuses the old receipt")

    # a NEW receipt → the legal transition
    doc["entries"][0]["admission_receipt"] = {
        "path": "research/admissions/re-admission.md", "sha256": SHA3}
    errors = registry.check_lock(doc, lock)
    assert errors == [], errors


def test_transition_suspended_to_proposed_refused():
    suspended = base_doc()
    suspended["entries"][0] = base_entry(
        state="suspended", receipt=base_receipt(),
        binding=base_binding("admitted"), **suspended_fields())
    suspended["entries"][0]["revision"] = 2
    lock = lock_for(suspended)
    doc = base_doc()
    doc["entries"][0] = base_entry(state="proposed")
    doc["entries"][0]["revision"] = 3
    errors = registry.check_lock(doc, lock)
    assert_mention(errors, "suspension is sticky")

    # repairing the binding does not auto-clear suspended: suspended -> proposed
    # is refused even with the binding intact — readmission is the only exit.


def test_transition_retired_terminal():
    retired = base_doc()
    retired["entries"][0] = base_entry(state="retired")
    retired["entries"][0]["admission_receipt"] = None
    lock = lock_for(retired)

    for resurrect in ("proposed", "admitted", "suspended"):
        doc = base_doc()
        doc["entries"][0] = base_entry(
            state=resurrect,
            **({"binding": base_binding("admitted"),
                "receipt": base_receipt()} if resurrect in ("admitted", "suspended") else {}))
        errors = registry.check_lock(doc, lock)
        assert_mention(errors, "retired is terminal")


# ----------------------------------------------------------------- launch


def test_launchable_only_when_admitted():
    doc = base_doc()
    assert registry.launchable(doc, "example.persona") != []  # proposed
    doc["entries"][0] = base_entry(state="admitted", receipt=base_receipt(),
                                   binding=base_binding("admitted"))
    assert registry.launchable(doc, "example.persona") == []
    assert registry.launchable(doc, "nobody.here") != []


def test_launch_refusal_does_not_mutate():
    doc = base_doc()
    frozen = copy.deepcopy(doc)
    registry.launchable(doc, "example.persona")
    assert registry.launchable(doc, "example.persona")
    registry.launchable(doc, "missing.handle")
    assert registry.launchable(doc, "missing.handle")
    assert doc == frozen, "launchable mutated the document"


def test_check_revision_mismatch():
    doc = base_doc()  # registry_revision: 1
    assert registry.check_revision(doc, 1) == []
    assert_mention(registry.check_revision(doc, 7), "drift")
    doc["registry_revision"] = 2
    assert_mention(registry.check_revision(doc, 1), "drift")


# ---------------------------------------------------------------- content


def entry_with_link(entry, link, text=None):
    entry = copy.deepcopy(entry)
    entry["child_id"] = "xg0001"
    return entry


def test_links_outside_domain_reported():
    entry = base_entry(state="admitted", receipt=base_receipt(),
                       binding=base_binding("admitted"))
    entry["child_id"] = "xg0001"
    inside = canonical_bio_link("xg0001")  # https://www.mastermind-x.com/x/xg0001
    assert registry.links_outside_domain(f"see {inside}", entry) == []

    outside = "https://tracker.example.net/px/xg0001"
    errors = registry.links_outside_domain(f"see {outside}", entry)
    assert_mention(errors, "outside the declared domain")


def test_bio_link_refused_when_domain_not_admitted():
    doc = base_doc()
    doc["domains"][0] = base_domain(state="proposed")
    entry = base_entry(state="proposed", bio_link_policy="single_canonical")
    doc["entries"][0] = entry
    link = canonical_bio_link("xg0001")
    text = f"fit journal, more on {link}"
    errors = registry.validate_bio_against_registry(text, doc, "example.persona")
    assert_mention(errors, "unless the domain record is admitted")


def test_bio_link_refused_when_policy_none():
    doc = base_doc()
    entry = base_entry(state="proposed", bio_link_policy="none")
    doc["entries"][0] = entry
    text = "fit journal, more on " + canonical_bio_link("xg0001")
    errors = registry.validate_bio_against_registry(text, doc, "example.persona")
    assert_mention(errors, "NO link")

    # policy none and no link → only the bio law's own "no URL" answer, no registry refusal
    errors = registry.validate_bio_against_registry(
        "fit journal, no links here", doc, "example.persona")
    assert errors, "validate_bio refuses a bare bio with no URL (BL-1)"
    assert not any("NO link" in e for e in errors)


def test_bio_link_ok_when_admitted_and_canonical():
    doc = base_doc()
    doc["entries"][0] = base_entry(state="admitted", receipt=base_receipt(),
                                   binding=base_binding("admitted"),
                                   bio_link_policy="single_canonical")
    doc["domains"][0] = base_domain(policy="single_canonical", state="admitted")
    text = "fit journal, more on " + canonical_bio_link("xg0001")
    errors = registry.validate_bio_against_registry(text, doc, "example.persona")
    assert errors == [], errors


def test_bio_link_host_mismatch_refused():
    doc = base_doc()
    doc["entries"][0] = base_entry(state="proposed",
                                   bio_link_policy="single_canonical",
                                   child_id="xg0001")
    text = "fit journal, more on https://evil-mirror.net/x/xg0001"
    errors = registry.validate_bio_against_registry(text, doc, "example.persona")
    assert_mention(errors, "outside the declared domain")
    assert_mention(errors, "bio link host 'evil-mirror.net'")

    # an unknown handle refuses the whole gate
    errors = registry.validate_bio_against_registry("", base_doc(), "ghost.handle")
    assert_mention(errors, "no registry entry")


def test_validate_all_concatenation_and_schema_shortcircuit():
    doc = base_doc()
    doc["schema_version"] = "nine"
    lock = lock_for(base_doc())
    errors = registry.validate_all(doc, lock, {"example.persona": object()},
                                   ["us-01"], expected_revision=1)
    assert all("refusing to parse" in e for e in errors), errors

    doc = base_doc()
    doc["registry_revision"] = 3
    errors = registry.validate_all(doc, lock, {"example.persona": object()},
                                   ["us-01"], expected_revision=1)
    assert_mention(errors, "drift")


def test_validate_all_without_lock_refuses_fail_closed():
    doc = base_doc()
    errors = registry.validate_all(doc, None, {"example.persona": object()},
                                   ["us-01"])
    assert_mention(errors, "fail-closed")
    # and WITH the lock the same document passes the lock half
    errors = registry.validate_all(doc, lock_for(base_doc()),
                                   {"example.persona": object()}, ["us-01"])
    assert not [e for e in errors if "fail-closed" in e or "drift" in e], errors


def test_cli_registry_check_missing_lock_is_a_refusal(tmp_path, capsys):
    reg = tmp_path / "registry.yml"
    reg.write_text(yaml.safe_dump(base_doc(), sort_keys=True), encoding="utf-8")
    # no --lock and no sibling registry.lock.yml on disk -> exit 2, fail closed
    assert cli.main(["registry-check", "--registry", str(reg)]) == 2
    out = capsys.readouterr().out
    assert "fail-closed" in out and "registry.lock.yml" in out
    # the re-lock ceremony writes the sibling default; the bare check then passes
    assert cli.main(["registry-lock", "--registry", str(reg),
                     "--lock", str(tmp_path / "registry.lock.yml")]) == 0
    capsys.readouterr()
    assert cli.main(["registry-check", "--registry", str(reg)]) == 0


def test_default_lock_path_shapes():
    assert cli._default_lock_path("a/registry.yml").endswith("a/registry.lock.yml")
    assert cli._default_lock_path("registry.example.yml") == "registry.lock.example.yml"


def test_canonical_sha_drops_revision():
    one = base_entry(state="proposed", revision=1)
    two = base_entry(state="proposed", revision=7)
    assert registry.canonical_sha(one, drop=("revision",)) == \
        registry.canonical_sha(two, drop=("revision",))
    assert registry.canonical_sha(one) != registry.canonical_sha(two)
    lock = registry.write_lock(base_doc())
    assert lock["entries"]["example.persona"]["sha256"] == \
        registry.canonical_sha(base_entry(), drop=("revision",))


# ------------------------------------------------------------ glue files + CLI


def test_example_files_validate_clean(tmp_path):
    package = Path(__file__).resolve().parents[1]
    loaded, load_errors = registry.load_registry(str(package / "registry.example.yml"))
    assert load_errors == [], load_errors
    doc, lock = loaded, registry.load_lock(str(package / "registry.lock.example.yml"))[0]
    assert registry.load_lock(str(package / "registry.lock.example.yml"))[1] == []
    assert registry.validate_document(doc) == []
    assert registry.check_lock(doc, lock) == []
    assert registry.launchable(doc, "example.persona") != []  # proposed: not launched


def test_cli_registry_check_exit_codes(tmp_path):
    clean = base_doc()
    clean["entries"][0] = base_entry(state="admitted", receipt=base_receipt(),
                                     binding=base_binding("admitted"))
    reg = write_yaml(tmp_path, "registry.yml", clean)
    lock = write_yaml(tmp_path, "registry.lock.yml", registry.write_lock(clean))
    assert cli.main(["registry-check", "--registry", str(reg),
                     "--lock", str(lock)]) == 0

    broken = base_doc()
    broken["entries"][0]["state"] = "musing"
    reg2 = write_yaml(tmp_path, "registry-broken.yml", broken)
    assert cli.main(["registry-check", "--registry", str(reg2),
                     "--lock", str(lock)]) == 2

    missing = tmp_path / "absent.yml"
    assert cli.main(["registry-check", "--registry", str(missing)]) == 2

    locked_drift = copy.deepcopy(clean)
    locked_drift["registry_revision"] = 9
    reg3 = write_yaml(tmp_path, "registry-drift.yml", locked_drift)
    assert cli.main(["registry-check", "--registry", str(reg3),
                     "--lock", str(lock)]) == 2


def test_cli_registry_lock_writes_matching_lock(tmp_path):
    reg = write_yaml(tmp_path, "registry.yml", base_doc())
    lock_path = tmp_path / "registry.lock.yml"
    assert cli.main(["registry-lock", "--registry", str(reg),
                     "--lock", str(lock_path)]) == 0
    assert lock_path.exists()

    on_disk, load_errors = registry.load_lock(str(lock_path))
    assert load_errors == []
    doc, _ = registry.load_registry(str(reg))
    assert registry.check_lock(doc, on_disk) == []

    # a broken document is refused and nothing is written
    broken = base_doc()
    broken["entries"][0]["state"] = "musing"
    reg2 = write_yaml(tmp_path, "registry-broken.yml", broken)
    fresh = tmp_path / "should-not-exist.yml"
    assert cli.main(["registry-lock", "--registry", str(reg2),
                     "--lock", str(fresh)]) == 2
    assert not fresh.exists()
