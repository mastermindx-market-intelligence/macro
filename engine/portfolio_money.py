"""Native entry-unit validation shared by Macro portfolio readers.

The declaration is bound to stored ticker/price, independently of current quotes.
No historical inference or FX conversion occurs here. Supported codes are frozen
from the same Intl supported currency set used by Terminal A09; reserved XXX/XTS
are excluded. Unknown/new codes fail closed until this contract is updated.
"""
from __future__ import annotations
import math

SUPPORTED_ENTRY_UNITS = frozenset("""AED AFN ALL AMD ANG AOA ARS AUD AWG AZN BAM BBD BDT BGN BHD BIF BMD BND BOB BRL BSD BTN BWP BYN BZD CAD CDF CHF CLP CNY COP CRC CUC CUP CVE CZK DJF DKK DOP DZD EGP ERN ETB EUR FJD FKP GBP GEL GHS GIP GMD GNF GTQ GYD HKD HNL HRK HTG HUF IDR ILS INR IQD IRR ISK JMD JOD JPY KES KGS KHR KMF KPW KRW KWD KYD KZT LAK LBP LKR LRD LSL LYD MAD MDL MGA MKD MMK MNT MOP MRU MUR MVR MWK MXN MYR MZN NAD NGN NIO NOK NPR NZD OMR PAB PEN PGK PHP PKR PLN PYG QAR RON RSD RUB RWF SAR SBD SCR SDG SEK SGD SHP SLE SLL SOS SRD SSP STN SVC SYP SZL THB TJS TMT TND TOP TRY TTD TWD TZS UAH UGX USD UYU UZS VES VND VUV WST XAF XCD XCG XDR XOF XPF XSU YER ZAR ZMW ZWG ZWL""".split())


def native_entry_currency(row: dict) -> str | None:
    currency = row.get("entry_currency")
    if not isinstance(currency, str) or currency not in SUPPORTED_ENTRY_UNITS:
        return None
    basis = row.get("entry_currency_basis")
    if not isinstance(basis, dict) or set(basis) != {"ticker", "price"}:
        return None
    ticker, price = row.get("ticker"), row.get("entry_price")
    if not isinstance(ticker, str) or basis.get("ticker") != ticker:
        return None
    if price is None:
        return currency if basis.get("price") is None else None
    recorded = basis.get("price")
    if (type(price) not in (int, float) or type(recorded) not in (int, float)
            or not math.isfinite(price) or not math.isfinite(recorded)
            or recorded != price):
        return None
    return currency
