"""tests/test_options_occ_contract_terms.py — OCC DDS full-snapshot terms decoder tests.

Every fixture here is hand-authored SYNTHETIC markup written for this file only.  It is not
market data, not an OCC transmission, and it asserts nothing about source admission, feed
availability, or effective times.  The parser itself is exercised for real: no stubs.
"""
from __future__ import annotations

import hashlib
from decimal import Decimal
from engine.options_nbbo_cohort import canonical_occ_symbol
import re
import unittest
from pathlib import Path

from engine.options_occ_contract_terms import (
    MAX_INPUT_BYTES,
    SCHEMA,
    TermsDecodeError,
    decode_contract_terms,
)

ROOT = "SYNX"
BIZ_DT = "2026-08-14"
EXPIRY = "2026-09-18"
STRIKE = "105.5"
NS_44 = "http://www.fixprotocol.org/FIXML-4-4"
NS_50 = "http://www.fixprotocol.org/FIXML-5-0-SP2"
DAY_RE = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")

_SECDEF = {"verb": "I", "BizDt": BIZ_DT, "RptID": "PD-SYNTH-1", "Ccy": "USD"}
_INSTRMT = {"Sym": ROOT, "Desc": "STAN", "CFI": "OCASPS", "StrkCcy": "USD",
            "StrkMult": "1", "Mult": "100", "StrkValu": "100"}
_UNDLY = {"Sym": ROOT, "CFI": "EXXXXX", "Qty": "100", "ID": "E", "Src": "C"}
_SECLIST = {"BizDt": BIZ_DT, "RptID": "SL-SYNTH-1"}
_SERIES = {"Sym": ROOT, "MatDt": EXPIRY, "MMY": "20260918", "StrkPx": STRIKE, "CFI": "OCASPS"}
_PRODUCT_EVENT = '<Evnt EventTyp="5" Dt="2026-03-02"/>'
_SERIES_EVENT = f'<Evnt EventTyp="5" Dt="{BIZ_DT}"/>'


def _attributes(attributes: dict) -> str:
    return "".join(f' {key}="{value}"' for key, value in attributes.items())


def _open(tag: str, attributes: dict) -> str:
    return f"<{tag}{_attributes(attributes)}>"


def _leaf(tag: str, attributes: dict) -> str:
    return f"<{tag}{_attributes(attributes)}/>"


def _wrap(document: str, wrapper: str | None, namespace: str | None) -> str:
    if wrapper is None:
        return document
    declared = f' xmlns="{namespace}"' if namespace else ""
    if wrapper == "FIXML":
        return f'<FIXML v="4.4"{declared}><Batch>{document}</Batch></FIXML>'
    return f'<Batch{declared}>{document}</Batch>'


def _merged(base: dict, changes: dict | None, drops: tuple = ()) -> dict:
    values = dict(base)
    values.update(changes or {})
    for key in drops:
        values.pop(key, None)
    return values


def product(*, secdef=None, instrmt=None, undly=None, undly2=None, events=None, extra_children="",
            wrapper=None, namespace=None, drops=(), undly_drops=(), no_undly=False) -> bytes:
    undly_attributes = _merged(_UNDLY, undly, tuple(drops) + tuple(undly_drops))
    body = (f'{_open("Instrmt", _merged(_INSTRMT, instrmt, drops))}'
            f'{_PRODUCT_EVENT if events is None else events}</Instrmt>')
    if undly_attributes and not no_undly:
        body += _leaf("Undly", undly_attributes)
    if undly2 is not None:
        body += _leaf("Undly", undly2)
    document = f'{_open("SecDef", _merged(_SECDEF, secdef, drops))}{body}{extra_children}</SecDef>'
    return _wrap(document, wrapper, namespace).encode()


def series(*, seclist=None, item=None, items=(), events=None, extra_children="", tag="Instrmt",
           wrapper=None, namespace=None, drops=()) -> bytes:
    body = (f'<SecL>{_open(tag, _merged(_SERIES, item, drops))}'
            f'{_SERIES_EVENT if events is None else events}</{tag}></SecL>')
    for attributes in items:
        body += f'<SecL>{_open(tag, _merged(_SERIES, attributes))}{_SERIES_EVENT}</{tag}></SecL>'
    document = f'{_open("SecList", _merged(_SECLIST, seclist, drops))}{body}{extra_children}</SecList>'
    return _wrap(document, wrapper, namespace).encode()


def terms(**overrides) -> dict:
    base = {"root": ROOT, "expiration": EXPIRY, "right": "call", "strike": STRIKE}
    base.update(overrides)
    # Build synthetic six-field identities; deliberately invalid inputs remain
    # invalid and must be rejected by the decoder, not by the test helper.
    try:
        millis = int(Decimal(base["strike"]) * 1000)
        symbol = canonical_occ_symbol(root=base["root"], expiration=base["expiration"],
                                      right=base["right"], strike_millis=millis)
    except (TypeError, ValueError, ArithmeticError):
        millis, symbol = 0, "invalid-synthetic-identity"
    base.update(strike_millis=millis, occ_symbol=symbol)
    return base


def decode(product_xml: bytes, series_xml: bytes, **overrides) -> dict:
    return decode_contract_terms(product_xml, series_xml, contract=terms(**overrides))


def without_provenance(decoded: dict) -> dict:
    copy = dict(decoded)
    copy.pop("inputs")
    return copy


class TestStandardSnapshot(unittest.TestCase):
    def test_decodes_exact_terms_and_provenance(self) -> None:
        product_xml, series_xml = product(), series()
        decoded = decode(product_xml, series_xml)
        self.assertEqual(decoded["schema"], SCHEMA)
        self.assertEqual(decoded["contract"], terms())
        self.assertEqual(decoded["source_business_date"], BIZ_DT)
        self.assertEqual((decoded["product_report_id"], decoded["series_report_id"]),
                         ("PD-SYNTH-1", "SL-SYNTH-1"))
        self.assertEqual((decoded["product_cfi"], decoded["series_cfi"]), ("OCASPS", "OCASPS"))
        self.assertEqual(decoded["product_description"], "STAN")
        self.assertEqual((decoded["currency"], decoded["strike_currency"]), ("USD", "USD"))
        self.assertEqual((decoded["premium_multiplier"], decoded["strike_multiplier"],
                          decoded["strike_value"], decoded["series_strike_price"]),
                         ("100", "1", "100", "105.5"))
        self.assertEqual(decoded["product_activation_date"], "2026-03-02")
        self.assertEqual(decoded["series_activation_date"], BIZ_DT)
        self.assertIsNone(decoded["product_inactivation_date"])
        self.assertIsNone(decoded["series_inactivation_date"])
        self.assertTrue(decoded["standard_100_share_terms"])
        self.assertEqual(decoded["deliverable_components"], [{
            "symbol": ROOT, "cfi": "EXXXXX", "quantity": "100", "id": "E", "src": "C",
            "cash_amount": None, "cash_type": None, "settlement_method": None,
            "settlement_status": None, "allocation_percent": None,
            "raw_attributes": {"Sym": ROOT, "CFI": "EXXXXX", "Qty": "100", "ID": "E", "Src": "C"},
            "pending_alternate_ids": []}])
        self.assertEqual(decoded["raw_product_attributes"]["Mult"], "100")
        self.assertEqual(decoded["raw_series_attributes"]["StrkPx"], STRIKE)

    def test_byte_hash_provenance_is_the_raw_input(self) -> None:
        product_xml, series_xml = product(), series()
        decoded = decode(product_xml, series_xml)
        self.assertEqual(decoded["inputs"]["product"],
                         {"sha256": hashlib.sha256(product_xml).hexdigest(),
                          "bytes": len(product_xml)})
        self.assertEqual(decoded["inputs"]["series"],
                         {"sha256": hashlib.sha256(series_xml).hexdigest(), "bytes": len(series_xml)})

    def test_bare_and_fixml_wrappers_decode_the_same_terms(self) -> None:
        bare = decode(product(), series())
        for namespace in (None, NS_44, NS_50):
            wrapped = decode(product(wrapper="FIXML", namespace=namespace),
                             series(wrapper="FIXML", namespace=namespace))
            self.assertEqual(without_provenance(bare), without_provenance(wrapped))
        batched = decode(product(wrapper="Batch", namespace=NS_44),
                         series(wrapper="Batch", namespace=NS_44))
        self.assertEqual(without_provenance(bare), without_provenance(batched))

    def test_decimal_exactness_without_float(self) -> None:
        cases = (("105.5", STRIKE, "105.5"), ("105.5", "105.500", "105.5"),
                 ("0.1", "0.10", "0.1"), ("1000", "1000.00", "1000"),
                 ("12345.123", "12345.1230", "12345.123"))
        for strike, price, canonical in cases:
            with self.subTest(strike=strike, price=price):
                decoded = decode(product(), series(item={"StrkPx": price, "MatDt": "2027-01-15",
                                                         "MMY": "20270115"}),
                                 expiration="2027-01-15", strike=strike)
                self.assertEqual(decoded["contract"]["strike"], canonical)
                self.assertEqual(decoded["series_strike_price"], canonical)

    def test_near_but_unequal_strike_does_not_match(self) -> None:
        with self.assertRaisesRegex(TermsDecodeError, "no series matches"):
            decode(product(), series(item={"StrkPx": "105.51"}), strike="105.5")


class TestTermsVariation(unittest.TestCase):
    def test_adjusted_fifty_unit_deliverable_keeps_values_but_is_not_standard(self) -> None:
        decoded = decode(product(undly={"Qty": "150"}), series())
        self.assertEqual(decoded["deliverable_components"][0]["quantity"], "150")
        self.assertFalse(decoded["standard_100_share_terms"])

    def test_cash_and_multiple_components_are_all_preserved(self) -> None:
        second = {"Sym": "SYNY", "CFI": "BCXXXX", "Qty": "1", "CashAmt": "10.50",
                  "CashTyp": "CASH", "SetMeth": "T2", "SettlStat": "N", "AllocPct": "25"}
        decoded = decode(product(instrmt={"CFI": "OCAICS"}, undly2=second),
                         series(item={"CFI": "OCAICS"}))
        components = decoded["deliverable_components"]
        self.assertEqual(len(components), 2)
        self.assertEqual([item["symbol"] for item in components], [ROOT, "SYNY"])
        self.assertEqual(components[1]["cash_amount"], "10.5")
        self.assertEqual(components[1]["cash_type"], "CASH")
        self.assertEqual(components[1]["settlement_method"], "T2")
        self.assertEqual(components[1]["settlement_status"], "N")
        self.assertEqual(components[1]["allocation_percent"], "25")
        self.assertEqual(components[1]["raw_attributes"], second)
        self.assertEqual(decoded["series_cfi"], "OCAICS")
        self.assertFalse(decoded["standard_100_share_terms"])

    def test_explicit_nonstandard_and_styled_products_decode_as_not_standard(self) -> None:
        for cfi in ("OCASPN", "OCESPS", "OCAIPS"):
            with self.subTest(cfi=cfi):
                decoded = decode(product(instrmt={"CFI": cfi}), series(item={"CFI": cfi}))
                self.assertEqual(decoded["product_cfi"], cfi)
                self.assertFalse(decoded["standard_100_share_terms"])

    def test_product_call_put_x_is_resolved_by_the_series(self) -> None:
        decoded = decode(product(instrmt={"CFI": "OXASPS"}), series(item={"CFI": "OPASPS"}),
                         right="put")
        self.assertEqual((decoded["product_cfi"], decoded["series_cfi"]), ("OXASPS", "OPASPS"))
        self.assertTrue(decoded["standard_100_share_terms"])

    def test_empty_underlying_symbol_is_preserved_but_not_standard(self) -> None:
        decoded = decode(product(undly={"Sym": ""}), series())
        self.assertEqual(decoded["deliverable_components"][0]["symbol"], "")
        self.assertFalse(decoded["standard_100_share_terms"])

    def test_biny_description_decodes_and_is_not_standard(self) -> None:
        decoded = decode(product(instrmt={"Desc": "BINY"}), series())
        self.assertEqual(decoded["product_description"], "BINY")
        self.assertFalse(decoded["standard_100_share_terms"])

    def test_closing_only_exchanges_are_collected_from_both_documents(self) -> None:
        decoded = decode(
            product(events=f'{_PRODUCT_EVENT}<Evnt EventTyp="100" Txt="ARCX"/>'
                            f'<Evnt EventTyp="100" Txt="NMSQ"/>'),
            series(events=f'{_SERIES_EVENT}<Evnt EventTyp="100" Txt="NMSQ"/>'
                          f'<Evnt EventTyp="100" Txt="BATS"/>'))
        self.assertEqual(decoded["closing_only_exchanges"], ["ARCX", "NMSQ", "BATS"])

    def test_inactivation_days_are_returned_verbatim_as_local_market_days(self) -> None:
        decoded = decode(
            product(events=f'{_PRODUCT_EVENT}<Evnt EventTyp="6" Dt="2027-01-16"/>'),
            series(events=f'{_SERIES_EVENT}<Evnt EventTyp="6" Dt="2026-09-18"/>'))
        self.assertEqual((decoded["product_activation_date"], decoded["product_inactivation_date"]),
                         ("2026-03-02", "2027-01-16"))
        self.assertEqual((decoded["series_activation_date"], decoded["series_inactivation_date"]),
                         (BIZ_DT, "2026-09-18"))
        for key in ("product_activation_date", "product_inactivation_date",
                    "series_activation_date", "series_inactivation_date", "source_business_date"):
            self.assertRegex(decoded[key], DAY_RE)
        self.assertNotIn("T", decoded["series_inactivation_date"])

    def test_many_sibling_series_still_match_exactly_one(self) -> None:
        decoded = decode(product(), series(items=[{"StrkPx": "90"}, {"StrkPx": "120"}]))
        self.assertEqual(decoded["series_strike_price"], "105.5")

    def test_series_level_report_id_is_preferred(self) -> None:
        decoded = decode(product(), series(item={"RptID": "SL-ITEM-9"}))
        self.assertEqual(decoded["series_report_id"], "SL-ITEM-9")


class TestContractValidation(unittest.TestCase):
    def test_contract_keys_are_exact(self) -> None:
        for contract in ({"root": ROOT}, {"root": ROOT, "expiration": EXPIRY, "right": "call"},
                         {"root": ROOT, "expiration": EXPIRY, "right": "call", "strike": STRIKE,
                          "underlying": ROOT},
                         {"root": ROOT, "expiration": EXPIRY, "right": "call", "strike": STRIKE,
                          "as_of": "2026-08-14T00:00:00Z"}):
            with self.subTest(contract=sorted(contract)), self.assertRaisesRegex(
                    TermsDecodeError, "fields are not exact"):
                decode_contract_terms(product(), series(), contract=contract)

    def test_root_expiry_right_and_strike_are_validated(self) -> None:
        cases = (
            {"root": ""}, {"root": " SYNX"}, {"root": "SYN X"}, {"root": 123},
            {"expiration": "20260918"}, {"expiration": "2026-9-18"}, {"expiration": "2026-02-30"},
            {"expiration": "2026-09-18T00:00:00"}, {"right": "X"}, {"right": "c"}, {"right": "CALL"},
            {"strike": "0"}, {"strike": "-105.5"}, {"strike": "NaN"}, {"strike": "INF"},
            {"strike": "1e3"}, {"strike": 105.5}, {"strike": 100}, {"strike": ""},
        )
        for change in cases:
            with self.subTest(change=change), self.assertRaises(TermsDecodeError):
                decode(product(), series(), **change)


class TestRefusals(unittest.TestCase):
    def test_missing_required_terms_refuse(self) -> None:
        cases = (
            (product(drops=("Mult",)), series(), "Mult"),
            (product(drops=("StrkMult",)), series(), "StrkMult"),
            (product(drops=("StrkValu",)), series(), "StrkValu"),
            (product(drops=("Desc",)), series(), "Desc"),
            (product(drops=("Ccy",)), series(), "Ccy"),
            (product(drops=("StrkCcy",)), series(), "StrkCcy"),
            (product(drops=("BizDt",)), series(), "BizDt"),
            (product(drops=("RptID",)), series(), "RptID"),
            (product(drops=("CFI",)), series(), "CFI"),
            (product(), series(drops=("CFI",)), "CFI"),
            (product(), series(drops=("MatDt",)), "MatDt"),
            (product(), series(drops=("MMY",)), "MMY"),
            (product(), series(drops=("StrkPx",)), "StrkPx"),
            (product(undly_drops=("Qty",)), series(), "Qty"),
            (product(undly_drops=("Sym",)), series(), "Sym"),
            (product(undly_drops=("CFI",)), series(), "CFI"),
        )
        for product_xml, series_xml, needle in cases:
            with self.subTest(needle=needle), self.assertRaisesRegex(TermsDecodeError, needle):
                decode(product_xml, series_xml)

    def test_missing_underly_or_qty_refuses(self) -> None:
        with self.assertRaisesRegex(TermsDecodeError, "missing direct Undly"):
            decode(product(no_undly=True), series())
        with self.assertRaisesRegex(TermsDecodeError, "contains no series records"):
            decode(product(), b'<SecList BizDt="2026-08-14" RptID="SL-SYNTH-1"/>')

    def test_series_mismatch_variants_refuse(self) -> None:
        cases = (
            ({"root": "OTHER"}, {}, "does not match contract root"),
            ({"right": "put"}, {}, "no series matches"),
            ({"expiration": "2026-12-18"}, {}, "no series matches"),
            ({}, {"item": {"Sym": "OTHER"}}, "no series matches"),
            ({}, {"item": {"MatDt": "2026-12-18", "MMY": "20261218"}}, "no series matches"),
            ({}, {"item": {"CFI": "OPASPS"}}, "no series matches"),
        )
        for overrides, series_changes, needle in cases:
            with self.subTest(overrides=overrides, series=series_changes), self.assertRaisesRegex(
                    TermsDecodeError, needle):
                decode(product(), series(**series_changes), **overrides)

    def test_duplicate_series_refuse_even_when_identical(self) -> None:
        with self.assertRaisesRegex(TermsDecodeError, "ambiguous even if identical"):
            decode(product(), series(items=[{}]))
        duplicate = f'{_open("Instrmt", _INSTRMT)}{_PRODUCT_EVENT}</Instrmt>'
        with self.assertRaisesRegex(TermsDecodeError, "expected exactly one direct Instrmt"):
            decode(product(extra_children=duplicate), series())

    def test_agreement_rules_refuse(self) -> None:
        with self.assertRaisesRegex(TermsDecodeError, "business-date mismatch"):
            decode(product(), series(seclist={"BizDt": "2026-08-13"}))
        with self.assertRaisesRegex(TermsDecodeError, "CFI classification disagrees"):
            decode(product(instrmt={"CFI": "OCASPS"}), series(item={"CFI": "OCAIPS"}))
        with self.assertRaisesRegex(TermsDecodeError, "CFI exercise style disagrees"):
            decode(product(instrmt={"CFI": "OCASPS"}), series(item={"CFI": "OCESPS"}))
        with self.assertRaisesRegex(TermsDecodeError, "CFI call/put disagrees"):
            decode(product(instrmt={"CFI": "OPASPS"}), series(item={"CFI": "OCASPS"}))
        with self.assertRaisesRegex(TermsDecodeError, "MMY 20261018 disagrees with MatDt"):
            decode(product(), series(item={"MMY": "20261018"}))

    def test_scaled_strike_and_unsupported_values_refuse(self) -> None:
        cases = (
            (product(instrmt={"StrkMult": "2"}), series(), "StrkMult 2 is not 1"),
            (product(instrmt={"CFI": "RCASPS"}), series(item={"CFI": "RCASPS"}), "not an option"),
            (product(instrmt={"CFI": "OCQSPS"}), series(item={"CFI": "OCQSPS"}), "exercise style"),
            (product(instrmt={"CFI": "OCASPX"}), series(item={"CFI": "OCASPX"}), "standard"),
            (product(instrmt={"CFI": "OCA-S?"}), series(item={"CFI": "OCA-S?"}), "six ASCII letters"),
            (product(instrmt={"CFI": "OCASXS"}), series(item={"CFI": "OCASXS"}), "settlement"),
            (product(instrmt={"CFI": "OCAXPS"}), series(item={"CFI": "OCAXPS"}), "classification"),
            (product(instrmt={"CFI": "ocasps"}), series(item={"CFI": "ocasps"}), "six ASCII letters"),
            (product(instrmt={"Desc": "WEIRD"}), series(), "unsupported Desc"),
            (product(undly={"CFI": "ES"}), series(), "six-letter CFI"),
            (product(), series(item={"CFI": "OXASPS"}), "call/put"),
        )
        for product_xml, series_xml, needle in cases:
            with self.subTest(needle=needle), self.assertRaisesRegex(TermsDecodeError, needle):
                decode(product_xml, series_xml)

    def test_activation_and_interval_rules_refuse(self) -> None:
        with self.assertRaisesRegex(TermsDecodeError, "missing explicit activation date"):
            decode(product(events=""), series())
        with self.assertRaisesRegex(TermsDecodeError, "missing explicit activation date"):
            decode(product(), series(events=""))
        with self.assertRaisesRegex(TermsDecodeError, "duplicate activation"):
            decode(product(events=f'{_PRODUCT_EVENT}{_PRODUCT_EVENT}'), series())
        with self.assertRaisesRegex(TermsDecodeError, "duplicate inactivation"):
            decode(product(), series(
                events=f'{_SERIES_EVENT}<Evnt EventTyp="6" Dt="2026-09-19"/>'
                       f'<Evnt EventTyp="6" Dt="2026-09-19"/>'))
        with self.assertRaisesRegex(TermsDecodeError, "contradictory interval"):
            decode(product(), series(
                events=f'{_SERIES_EVENT}<Evnt EventTyp="6" Dt="2026-08-13"/>'))
        with self.assertRaisesRegex(TermsDecodeError, "not a LocalMktDate"):
            decode(product(events='<Evnt EventTyp="5" Dt="2026-09-18T09:30:00"/>'), series())
        with self.assertRaisesRegex(TermsDecodeError, "not a valid calendar day"):
            decode(product(), series(item={"MatDt": "2026-02-31", "MMY": "20260231"}))

    def test_invalid_numeric_fields_refuse(self) -> None:
        bad = ("NaN", "nan", "INF", "-Infinity", "Infinity", "1e3", "1E3", "100.0.0", "",
               " 100", "1_000", "0", "-100", "0.0", "-0.5")
        for value in bad:
            with self.subTest(mult=value):
                with self.assertRaises(TermsDecodeError):
                    decode(product(instrmt={"Mult": value}), series())
        for value in ("0", "-5", "NaN", "Inf"):
            with self.subTest(qty=value):
                with self.assertRaises(TermsDecodeError):
                    decode(product(undly={"Qty": value}), series())
        with self.assertRaisesRegex(TermsDecodeError, "between 0 and 100"):
            decode(product(undly={"Qty": "100", "AllocPct": "-1"}), series())
        decode(product(undly={"Qty": "100", "CashAmt": "-2.5"}), series())

    def test_incremental_records_refuse(self) -> None:
        bare_upd = b'<SecDefUpd BizDt="2026-08-14" RptID="PD-SYNTH-2" Ccy="USD"/>'
        wrapped = (b'<FIXML xmlns="http://www.fixprotocol.org/FIXML-4-4"><Batch>'
                   b'<SecDefUpd BizDt="2026-08-14" RptID="PD-SYNTH-2" Ccy="USD">'
                   b'<Instrmt Sym="SYNX" Desc="STAN" CFI="OCASPS" StrkCcy="USD" StrkMult="1" '
                   b'Mult="100" StrkValu="100"/></SecDefUpd></Batch></FIXML>')
        series_upd = b'<SecListUpd BizDt="2026-08-14" RptID="SL-SYNTH-2"/>'
        series_wrapped_upd = (b'<FIXML xmlns="http://www.fixprotocol.org/FIXML-4-4"><Batch>'
                              b'<SecList BizDt="2026-08-14" RptID="SL-SYNTH-2"><SecListUpd/></SecList>'
                              b'</Batch></FIXML>')
        for payload in (bare_upd, wrapped, series_upd, series_wrapped_upd):
            with self.subTest(payload=payload[:48]):
                with self.assertRaisesRegex(TermsDecodeError, "incremental update record"):
                    decode(payload, series())
                with self.assertRaisesRegex(TermsDecodeError, "incremental update record"):
                    decode(product(), payload)

    def test_malformed_dtd_entity_namespace_and_size_refuse(self) -> None:
        cases = (
            (b"<SecDef><Instrmt>", "malformed XML"),
            (b"<SecDef BizDt=\xc3\x28\x22/>", "not UTF-8"),
            (b"", "empty document"),
            (b'<!DOCTYPE SecDef SYSTEM "http://example.invalid/x.dtd"><SecDef/>', "DOCTYPE refused"),
            (b'<!DOCTYPE SecDef [<!ENTITY x "2026-08-14">]><SecDef BizDt="&x;"/>', "DOCTYPE refused"),
            (b'<SecDef BizDt="&undeclared;"/>', "malformed XML"),
            (b'<SecDef xmlns="http://example.com/fixml" BizDt="2026-08-14"/>', "is not allowlisted"),
            (b'<SecDef xmlns:x="http://www.w3.org/1999/xlink" x:hint="1" BizDt="2026-08-14"/>',
             "is not allowlisted"),
            (b'<SomethingElse/>', "expected SecDef or a FIXML/Batch wrapper"),
            (b'<FIXML><Batch><Instrmt/></Batch></FIXML>', "unexpected wrapper child"),
            (b'<FIXML><Batch><SecDef BizDt="2026-08-14"/><SecDef BizDt="2026-08-14"/></Batch></FIXML>',
             "contains 2 SecDef records; ambiguous"),
            (b'<SecDef><Header MsgType="X"/></SecDef>', "unexpected child element 'Header'"),
            (b'<SecDef BizDt="2026-08-14" RptID="R" Ccy="USD"><Instrmt CFI="OCASPS">'
             b'<Sym ID="SYNX"/></Instrmt><Undly Sym="SYNX" CFI="EXXXXX" Qty="100"/></SecDef>',
             "unexpected child element 'Sym'"),
            (b'<SecList/>', "expected SecDef or a FIXML/Batch wrapper"),
            (b'<SecDef BizDt="2026-08-14" RptID="R" Ccy="USD"><Instrmt Sym="SYNX" Desc="STAN" '
             b'CFI="OCASPS" StrkCcy="USD" StrkMult="1" Mult="100" StrkValu="100">'
             b'<Evnt EventTyp="5" Dt="2026-03-02"><EvntTxt>T</EvntTxt></Evnt></Instrmt>'
             b'<Undly Sym="SYNX" CFI="EXXXXX" Qty="100"/></SecDef>', "unexpected child element"),
        )
        for payload, needle in cases:
            with self.subTest(needle=needle):
                with self.assertRaisesRegex(TermsDecodeError, re.escape(needle)):
                    decode(payload, series())

    def test_oversized_and_non_bytes_inputs_refuse(self) -> None:
        padded = product(instrmt={"Desc": "STAN" + "Z" * MAX_INPUT_BYTES})
        self.assertGreater(len(padded), MAX_INPUT_BYTES)
        with self.assertRaisesRegex(TermsDecodeError, "exceeds the 16777216 byte"):
            decode(padded, series())
        for payload in (product().decode(), bytearray(product()), memoryview(product()), None, 7):
            with self.subTest(payload=type(payload).__name__):
                with self.assertRaisesRegex(TermsDecodeError, "expected bytes"):
                    decode(payload, series())
        for payload in (series().decode(), bytearray(series()), None):
            with self.subTest(series=type(payload).__name__):
                with self.assertRaisesRegex(TermsDecodeError, "expected bytes"):
                    decode(product(), payload)


class TestEpistemicBoundary(unittest.TestCase):
    def test_authority_fields_are_inert_by_construction(self) -> None:
        decoded = decode(product(), series())
        self.assertIsNone(decoded["source_available_at"])
        self.assertIsNone(decoded["source_observed_at"])
        self.assertIsNone(decoded["effective_timestamp_binding"])
        self.assertIs(decoded["source_authenticated"], False)
        self.assertIs(decoded["consumer_admitted"], False)
        self.assertNotEqual(decoded["schema"], "options.contract_terms_observation/v1")
        self.assertNotIn("options.contract_terms_observation/v1", repr(decoded))

    def test_no_clocks_and_no_invented_timestamps(self) -> None:
        decoded = decode(product(), series())
        again = decode(product(), series())
        self.assertEqual(decoded, again)
        text = repr(decoded)
        self.assertNotIn("T00:00:00", text)
        for key, value in decoded.items():
            if key in {"inputs", "raw_product_attributes", "raw_series_attributes",
                       "deliverable_components"} or isinstance(value, (list, dict)):
                continue
            if isinstance(value, str) and re.search(r"\d{2}:\d{2}:\d{2}", value):
                raise AssertionError(f"invented clock value in {key}: {value!r}")

    def test_module_is_pure_and_importable_as_a_package_module(self) -> None:
        from engine import options_occ_contract_terms as module
        source = Path(module.__file__).read_text()
        for forbidden in ("import time", "from datetime import datetime", "utcnow", "date.today",
                          ".now(", "open(", "socket", "subprocess", "urllib", "requests"):
            self.assertNotIn(forbidden, source)
        self.assertIs(decode_contract_terms, module.decode_contract_terms)
        self.assertEqual(module.SCHEMA, SCHEMA)


if __name__ == "__main__":
    unittest.main()
