"""FIF Z0 A52: source-rights reader, typed hold, and capture admission wiring.

Hermetic: no network, no env vars, no keychain.  A rights hold is decided
from contract bytes alone, so every test here either builds contract bytes or
copies the real frozen contract read-only, then asserts the typed outcome.
Independence is explicit: a hold on one contract refuses only that contract's
dependent capture — a second contract whose rights pass proceeds past the
gate, a held run constructs no pacer/fetcher and performs no network call,
and the publisher + specialist-pack scripts must not mention
``source_rights`` at BASE, so a future import there is a deliberate seat
ruling rather than drift.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any, Callable

import pytest

from engine.fundamental_forensics.source_rights import (
    RightsHold,
    SourceRights,
    SourceRightsError,
    read_source_rights,
    rights_hold,
)
from scripts import capture_fif_issuer_packages as gsrc

_REPO = Path(__file__).resolve().parents[1]
_D0_PATH = _REPO / "config" / "fundamental_forensics" / "coverage" / "five_issuer_v1.json"
_PUBLISHER = _REPO / "scripts" / "publish_fif_production_datasets.py"
_SPECIALIST_PACKS = _REPO / "scripts" / "fif_specialist_packs.py"
_CLOCK = "2026-10-12T00:00:00Z"
_PROVIDER = "sec_edgar_public_filings"
_POLICY = "sec_fair_access_declared_user_agent"


def _rights_block(**overrides: Any) -> dict[str, Any]:
    block: dict[str, Any] = {
        "access_policy": _POLICY,
        "credentials_required": [],
        "licences_accepted": [],
        "provider": _PROVIDER,
        "purchases": [],
    }
    block.update(overrides)
    return block


def _contract(block: Any) -> dict[str, Any]:
    return {"schema": "fundamental_forensics.coverage_contract/v1", "source_rights": block}


def _block_without(field: str) -> dict[str, Any]:
    block = _rights_block()
    del block[field]
    return block


# S1: every malformed shape is the one typed code, never a coercion or default.


def _malformed_cases() -> list[tuple[str, Any]]:
    blocks = [
        ("missing provider", _block_without("provider")),
        ("empty provider", _rights_block(provider="")),
        ("non-string provider", _rights_block(provider=7)),
        ("missing access_policy", _block_without("access_policy")),
        ("empty access_policy", _rights_block(access_policy="")),
        ("non-string access_policy", _rights_block(access_policy=None)),
        ("missing credentials_required", _block_without("credentials_required")),
        (
            "credentials_required not a list",
            _rights_block(credentials_required="EXAMPLE_NAME"),
        ),
        ("credentials_required non-string item", _rights_block(credentials_required=[7])),
        (
            "credentials_required empty-string item",
            _rights_block(credentials_required=[""]),
        ),
        ("missing licences_accepted", _block_without("licences_accepted")),
        (
            "licences_accepted not a list",
            _rights_block(licences_accepted="EXAMPLE_LICENCE"),
        ),
        ("licences_accepted non-string item", _rights_block(licences_accepted=[None])),
        ("missing purchases", _block_without("purchases")),
        ("purchases not a list", _rights_block(purchases="EXAMPLE_PURCHASE")),
        ("purchases empty-string item", _rights_block(purchases=[""])),
    ]
    cases = [
        ("contract not a mapping", ["not", "a", "mapping"]),
        ("missing source_rights", {"schema": "fundamental_forensics.coverage_contract/v1"}),
        ("source_rights not a mapping (list)", _contract(["nope"])),
        ("source_rights not a mapping (string)", _contract("nope")),
        ("source_rights not a mapping (null)", _contract(None)),
        ("empty source_rights mapping", _contract({})),
    ]
    cases.extend((label, _contract(block)) for label, block in blocks)
    return cases


@pytest.mark.parametrize(
    "payload",
    [pytest.param(payload, id=label) for label, payload in _malformed_cases()],
)
def test_read_source_rights_refuses_malformed_shapes(payload: Any) -> None:
    with pytest.raises(SourceRightsError) as caught:
        read_source_rights(payload)
    assert caught.value.code == "source_rights_malformed"
    assert issubclass(SourceRightsError, Exception)


def test_read_source_rights_returns_frozen_record_without_coercion() -> None:
    rights = read_source_rights(_contract(_rights_block()))
    assert isinstance(rights, SourceRights)
    assert rights.provider == _PROVIDER
    assert rights.access_policy == _POLICY
    for field in ("credentials_required", "licences_accepted", "purchases"):
        value = getattr(rights, field)
        assert isinstance(value, tuple)
        assert value == ()
    declared = read_source_rights(
        _contract(
            _rights_block(
                credentials_required=["EXAMPLE_NAME"],
                licences_accepted=["EXAMPLE_LICENCE"],
                purchases=["EXAMPLE_PURCHASE"],
            )
        )
    )
    assert declared.credentials_required == ("EXAMPLE_NAME",)
    assert declared.licences_accepted == ("EXAMPLE_LICENCE",)
    assert declared.purchases == ("EXAMPLE_PURCHASE",)


# S2: every hold code, and the None case on the frozen contract's own bytes.


def test_rights_hold_is_none_for_established_rights() -> None:
    assert rights_hold(read_source_rights(_contract(_rights_block()))) is None


def test_rights_hold_is_none_on_the_frozen_contract_bytes() -> None:
    contract = json.loads(_D0_PATH.read_text(encoding="utf-8"))
    assert rights_hold(read_source_rights(contract)) is None


def test_hold_record_carries_only_code_provider_reason() -> None:
    assert [field.name for field in dataclasses.fields(RightsHold)] == [
        "code",
        "provider",
        "reason",
    ]
    assert dataclasses.is_dataclass(RightsHold)


def test_hold_credentials_undeclared() -> None:
    rights = read_source_rights(_contract(_rights_block(credentials_required=["EXAMPLE_NAME"])))
    hold = rights_hold(rights)
    assert isinstance(hold, RightsHold)
    assert hold.code == "source_rights_credentials_undeclared"
    assert hold.provider == _PROVIDER
    assert "EXAMPLE_NAME" not in repr(hold)


def test_hold_licence_unestablished_for_accepted_licence() -> None:
    rights = read_source_rights(_contract(_rights_block(licences_accepted=["EXAMPLE_LICENCE"])))
    hold = rights_hold(rights)
    assert isinstance(hold, RightsHold)
    assert hold.code == "source_rights_licence_unestablished"
    assert hold.provider == _PROVIDER
    assert "EXAMPLE_LICENCE" not in repr(hold)


def test_hold_licence_unestablished_for_purchase() -> None:
    rights = read_source_rights(_contract(_rights_block(purchases=["EXAMPLE_PURCHASE"])))
    hold = rights_hold(rights)
    assert isinstance(hold, RightsHold)
    assert hold.code == "source_rights_licence_unestablished"
    assert hold.provider == _PROVIDER
    assert "EXAMPLE_PURCHASE" not in repr(hold)


def test_hold_policy_unknown() -> None:
    rights = read_source_rights(_contract(_rights_block(access_policy="paid_brokerage_api")))
    hold = rights_hold(rights)
    assert isinstance(hold, RightsHold)
    assert hold.code == "source_rights_policy_unknown"
    assert hold.provider == _PROVIDER


def test_hold_policy_gate_honours_the_allowed_set_argument() -> None:
    frozen = read_source_rights(_contract(_rights_block()))
    assert rights_hold(frozen, allowed_access_policies=frozenset({"other_policy"})) is not None
    assert (
        rights_hold(frozen, allowed_access_policies=frozenset({_POLICY, "other_policy"}))
        is None
    )


def test_hold_precedence_credentials_then_licence_then_policy() -> None:
    everything = read_source_rights(
        _contract(
            _rights_block(
                credentials_required=["EXAMPLE_NAME"],
                licences_accepted=["EXAMPLE_LICENCE"],
                access_policy="paid_brokerage_api",
            )
        )
    )
    assert rights_hold(everything).code == "source_rights_credentials_undeclared"
    no_credentials = read_source_rights(
        _contract(
            _rights_block(
                licences_accepted=["EXAMPLE_LICENCE"],
                access_policy="paid_brokerage_api",
            )
        )
    )
    assert rights_hold(no_credentials).code == "source_rights_licence_unestablished"


# S3: the capture script refuses a held contract with rc=2 and the typed line,
# before any issuer row is read and before any pacer/fetcher is constructed.


def _write_tmp_contract(
    directory: Path, mutate: Callable[[dict[str, Any]], None]
) -> Path:
    payload = json.loads(_D0_PATH.read_text(encoding="utf-8"))
    mutate(payload)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "five_issuer_v1.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _require_credentials(payload: dict[str, Any]) -> None:
    # A credential NAME only, never a value: this lane establishes no credential.
    payload["source_rights"]["credentials_required"] = ["EXAMPLE_NAME"]


def _main(contract_path: Path, issuer: str) -> int:
    return gsrc.main(
        ["--contract", str(contract_path), "--issuer", issuer, "--captured-at", _CLOCK]
    )


def test_main_refuses_held_contract_with_typed_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    held = _write_tmp_contract(tmp_path / "held", _require_credentials)
    assert _main(held, "SNOW") == 2
    out = capsys.readouterr().out
    assert "gsrc_refusal: source_rights_credentials_undeclared: sec_edgar_public_filings" in (
        out.splitlines()
    )


def test_main_refuses_malformed_rights_with_typed_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    def _drop_provider(payload: dict[str, Any]) -> None:
        del payload["source_rights"]["provider"]

    malformed = _write_tmp_contract(tmp_path / "malformed", _drop_provider)
    assert _main(malformed, "SNOW") == 2
    out = capsys.readouterr().out
    assert f"gsrc_refusal: source_rights_malformed: {malformed}" in out.splitlines()


def test_frozen_contract_passes_the_admission_hold(
    capsys: pytest.CaptureFixture[str],
) -> None:
    # The frozen D0 bytes yield no hold, so a run proceeds past the rights gate
    # to a later, independent refusal (unknown issuer) — same shape the
    # existing capture tests rely on.
    assert _main(_D0_PATH, "NOSUCH") == 2
    out = capsys.readouterr().out
    assert "gsrc_refusal: unknown_issuer: NOSUCH" in out.splitlines()
    assert "source_rights" not in out


# S4: the hold blocks exactly the dependent source and nothing else.


def test_hold_on_one_contract_does_not_refuse_a_passing_contract(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    held = _write_tmp_contract(tmp_path / "held", _require_credentials)
    passing = _write_tmp_contract(tmp_path / "passing", lambda payload: None)
    assert _main(held, "SNOW") == 2
    assert (
        "gsrc_refusal: source_rights_credentials_undeclared: sec_edgar_public_filings"
        in capsys.readouterr().out.splitlines()
    )
    # Second invocation, second contract: its rights pass, so the run crosses
    # the rights gate and stops at the later unknown-issuer refusal instead.
    assert _main(passing, "NOSUCH") == 2
    out = capsys.readouterr().out
    assert "gsrc_refusal: unknown_issuer: NOSUCH" in out.splitlines()
    assert "source_rights_credentials_undeclared" not in out


def test_held_capture_constructs_no_fetcher_and_performs_no_network(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def _touched(*args: object, **kwargs: object) -> None:
        raise AssertionError("constructed/reached during a held capture")

    monkeypatch.setattr(gsrc, "SecRequestPacer", _touched)
    monkeypatch.setattr(gsrc, "PacedFetcher", _touched)
    monkeypatch.setattr(gsrc.urllib.request, "urlopen", _touched)
    held = _write_tmp_contract(tmp_path / "held", _require_credentials)
    assert _main(held, "SNOW") == 2
    assert (
        "gsrc_refusal: source_rights_credentials_undeclared: sec_edgar_public_filings"
        in capsys.readouterr().out.splitlines()
    )


def test_publisher_and_specialist_pack_scripts_do_not_use_source_rights() -> None:
    # The independence is explicit at BASE: neither the publisher nor the
    # specialist-pack script reads source_rights, so extending the hold to
    # them stays a deliberate future seat ruling rather than silent drift.
    for path in (_PUBLISHER, _SPECIALIST_PACKS):
        text = path.read_text(encoding="utf-8")
        assert "source_rights" not in text, path
