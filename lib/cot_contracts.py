"""Reviewed CFTC futures-only identities and actual Socrata field names.

Contract codes survive name changes (CFTC announcement 2022-02-11). Standard,
micro, ultra and other exchanges stay separate. Never choose by maximum OI.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Market:
    key: str
    code: str
    name: str
    name_zh: str
    category: str
    detail_family: str


MARKETS = (
    Market("es_spx", "13874A", "S&P 500", "\u6807\u666e500", "equities", "tff"),
    Market("nasdaq", "209742", "Nasdaq-100", "\u7eb3\u65af\u8fbe\u514b100", "equities", "tff"),
    Market("dow", "124603", "Dow Jones", "\u9053\u743c\u65af", "equities", "tff"),
    Market("russell", "239742", "Russell 2000", "\u7f57\u7d202000", "equities", "tff"),
    Market("ust30y", "020601", "30-Year Treasury Bond", "30\u5e74\u671f\u7f8e\u503a", "fixed_income", "tff"),
    Market("ust10y", "043602", "10-Year Treasury Note", "10\u5e74\u671f\u7f8e\u503a", "fixed_income", "tff"),
    Market("ust5y", "044601", "5-Year Treasury Note", "5\u5e74\u671f\u7f8e\u503a", "fixed_income", "tff"),
    Market("ust2y", "042601", "2-Year Treasury Note", "2\u5e74\u671f\u7f8e\u503a", "fixed_income", "tff"),
    Market("natgas", "023651", "Natural Gas", "\u5929\u7136\u6c14", "energy", "disaggregated"),
    Market("heating_oil", "022651", "Heating Oil / ULSD", "\u53d6\u6696\u6cb9", "energy", "disaggregated"),
    Market("gasoline", "111659", "RBOB Gasoline", "RBOB\u6c7d\u6cb9", "energy", "disaggregated"),
    Market("oil", "067651", "WTI Crude Oil", "WTI\u539f\u6cb9", "energy", "disaggregated"),
    Market("palladium", "075651", "Palladium", "\u94af", "metals", "disaggregated"),
    Market("gold", "088691", "Gold", "\u9ec4\u91d1", "metals", "disaggregated"),
    Market("silver", "084691", "Silver", "\u767d\u94f6", "metals", "disaggregated"),
    Market("copper", "085692", "Copper", "\u94dc", "metals", "disaggregated"),
    Market("platinum", "076651", "Platinum", "\u94c2", "metals", "disaggregated"),
    Market("ether", "146021", "Ethereum", "\u4ee5\u592a\u574a", "crypto", "tff"),
    Market("solana", "177741", "Solana", "Solana", "crypto", "tff"),
    Market("bitcoin", "133741", "Bitcoin", "\u6bd4\u7279\u5e01", "crypto", "tff"),
    Market("dollar", "098662", "US Dollar Index", "\u7f8e\u5143\u6307\u6570", "currencies", "tff"),
)
BY_CODE = {m.code: m for m in MARKETS}
BY_KEY = {m.key: m for m in MARKETS}
DATASETS = {"legacy": "6dca-aqww", "tff": "gpe5-46if", "disaggregated": "72hh-3qpy"}
# Tuple order: long, short, spreading. None = not a distinct spread category.
# Deliberate upstream spelling: postions, swap__, and truncated TFF names.
COHORT_FIELDS = {
    "legacy": {
        "commercial": ("comm_positions_long_all", "comm_positions_short_all", None),
        "noncommercial": ("noncomm_positions_long_all", "noncomm_positions_short_all", "noncomm_postions_spread_all"),
        "nonreportable": ("nonrept_positions_long_all", "nonrept_positions_short_all", None),
    },
    "tff": {
        "dealer": ("dealer_positions_long_all", "dealer_positions_short_all", "dealer_positions_spread_all"),
        "asset_manager": ("asset_mgr_positions_long", "asset_mgr_positions_short", "asset_mgr_positions_spread"),
        "leveraged_funds": ("lev_money_positions_long", "lev_money_positions_short", "lev_money_positions_spread"),
        "other_reportable": ("other_rept_positions_long", "other_rept_positions_short", "other_rept_positions_spread"),
        "nonreportable": ("nonrept_positions_long_all", "nonrept_positions_short_all", None),
    },
    "disaggregated": {
        "producer_merchant": ("prod_merc_positions_long", "prod_merc_positions_short", None),
        "swap_dealer": ("swap_positions_long_all", "swap__positions_short_all", "swap__positions_spread_all"),
        "managed_money": ("m_money_positions_long_all", "m_money_positions_short_all", "m_money_positions_spread"),
        "other_reportable": ("other_rept_positions_long", "other_rept_positions_short", "other_rept_positions_spread"),
        "nonreportable": ("nonrept_positions_long_all", "nonrept_positions_short_all", None),
    },
}
BASE_FIELDS = ("report_date_as_yyyy_mm_dd", "market_and_exchange_names", "cftc_contract_market_code", "open_interest_all")


def source_fields(family: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*BASE_FIELDS, *(f for fs in COHORT_FIELDS[family].values() for f in fs if f))))


def store_name(code: str, family: str = "legacy") -> str:
    if family not in DATASETS or code not in BY_CODE:
        raise ValueError("unknown COT family/contract")
    return f"cot_{family}_{code}"
