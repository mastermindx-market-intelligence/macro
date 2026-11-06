"""Synthetic FIXML cases at the suite's existing exact-contract boundary."""

from copy import deepcopy

import pytest

from engine.options_nbbo_cohort import validate_contract
from engine.options_occ_contract_terms import TermsDecodeError, decode_contract_terms


# Hand-authored test data. These are not OCC messages or admitted observations.
PRODUCT = b'''<FIXML><Batch><SecDef BizDt="2026-10-15" RptID="synthetic-product" Ccy="USD">
<Instrmt Sym="SPY" Desc="STAN" CFI="OXASPS" StrkCcy="USD" StrkMult="1" Mult="100" StrkValu="100">
<Evnt EventTyp="5" Dt="2026-01-01"/></Instrmt>
<Undly Sym="SPY" CFI="EXXXXX" Qty="100"/>
</SecDef></Batch></FIXML>'''
SERIES = b'''<FIXML><Batch><SecList BizDt="2026-10-15" RptID="synthetic-series">
<SecL><Instrmt Sym="SPY" MatDt="2026-12-18" MMY="20261218" StrkPx="500" CFI="OCASPS">
<Evnt EventTyp="5" Dt="2026-01-01"/></Instrmt></SecL>
</SecList></Batch></FIXML>'''
CONTRACT = {
    "root": "SPY", "expiration": "2026-12-18", "right": "call",
    "strike": "500", "strike_millis": 500000,
    "occ_symbol": "SPY   261218C00500000",
}


def test_native_contract_identity_is_preserved_without_authority():
    result = decode_contract_terms(PRODUCT, SERIES, contract=CONTRACT)
    assert result["contract"] == validate_contract(CONTRACT)
    assert CONTRACT == validate_contract(CONTRACT)
    assert result["standard_100_share_terms"] is True
    for key in ("source_available_at", "source_observed_at", "effective_timestamp_binding"):
        assert result[key] is None
    assert result["source_authenticated"] is False
    assert result["consumer_admitted"] is False


@pytest.mark.parametrize("field,value", [
    ("occ_symbol", "SPY   261218P00500000"),
    ("strike_millis", 501000),
    ("strike", "500.000"),
    ("expiration", "2026-12-19"),
])
def test_rejects_contradictory_or_noncanonical_native_contract(field, value):
    contract = deepcopy(CONTRACT)
    contract[field] = value
    with pytest.raises(TermsDecodeError):
        decode_contract_terms(PRODUCT, SERIES, contract=contract)


def test_does_not_invent_missing_native_identity_fields():
    legacy = {"root": "SPY", "expiry": "2026-12-18", "right": "call", "strike": "500"}
    with pytest.raises(TermsDecodeError):
        decode_contract_terms(PRODUCT, SERIES, contract=legacy)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16", "utf-32"])
def test_entity_declaration_is_refused_before_parsing_in_every_encoding(encoding):
    text = PRODUCT.decode().replace('Sym="SPY"', 'Sym="&symbol;"')
    malicious = '<!DOCTYPE FIXML [<!ENTITY symbol "SPY">]>' + text
    with pytest.raises(TermsDecodeError):
        decode_contract_terms(malicious.encode(encoding), SERIES, contract=CONTRACT)


def test_nested_unknown_namespace_cannot_supply_delivery_component():
    malicious = PRODUCT.replace(b'<Undly ', b'<Undly xmlns="urn:untrusted:delivery" ')
    with pytest.raises(TermsDecodeError):
        decode_contract_terms(malicious, SERIES, contract=CONTRACT)


def test_normal_exchange_parties_are_retained():
    product = PRODUCT.replace(b"</Instrmt>", b'<Pty ID="XTEST" R="22"><Sub ID="2026-01-01" Typ="27"/></Pty></Instrmt>')
    result = decode_contract_terms(product, SERIES, contract=CONTRACT)
    assert result["standard_100_share_terms"] is True
    assert result["product_parties"] == [{"attributes": {"ID": "XTEST", "R": "22"},
                                          "sub_ids": [{"ID": "2026-01-01", "Typ": "27"}]}]


def test_zero_percent_cash_component_is_retained_as_nonstandard():
    product = PRODUCT.replace(b'</SecDef>', b'<Undly Sym="USD" CFI="MRCXXX" Qty="100" CashAmt="22.04" CashTyp="FIXED" AllocPct="0"/></SecDef>')
    result = decode_contract_terms(product, SERIES, contract=CONTRACT)
    assert result["standard_100_share_terms"] is False
    assert result["deliverable_components"][1]["allocation_percent"] == "0"
    assert result["deliverable_components"][1]["cash_amount"] == "22.04"


def test_unsupported_equity_cfi_cannot_become_standard():
    product = PRODUCT.replace(b'CFI="EXXXXX"', b'CFI="ESXXXX"')
    assert decode_contract_terms(product, SERIES, contract=CONTRACT)["standard_100_share_terms"] is False


def test_unrecognized_wrapper_cannot_hide_product():
    product = PRODUCT.replace(b'<Batch>', b'<Batch><Unknown>').replace(b'</Batch>', b'</Unknown></Batch>')
    with pytest.raises(TermsDecodeError, match="wrapper child"):
        decode_contract_terms(product, SERIES, contract=CONTRACT)


def test_utf16_without_bom_cannot_hide_entity_declaration():
    text = PRODUCT.decode().replace('Sym="SPY"', 'Sym="&symbol;"')
    malicious = ('<!DOCTYPE FIXML [<!ENTITY symbol "SPY">]>' + text).encode('utf-16-le')
    with pytest.raises(TermsDecodeError):
        decode_contract_terms(malicious, SERIES, contract=CONTRACT)
