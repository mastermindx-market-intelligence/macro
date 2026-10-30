# OCC contract-terms decoding

This offline decoder connects retained OCC full-product and exact-series messages to the Options suite’s contract identity. It reads supplied bytes only. It neither retrieves market data nor establishes source authorization or prospective availability.

The format reference is [OCC DDS Developer Reference I, version 4.6, August 2026](https://www.theocc.com/getmedia/5bb03145-905b-4d83-b647-eaa2cb076e93/ENCORE_DDS_Guide_Non_Proprietary_Transmissions.pdf), printed pages 3, 9–14, 20–23 and 102–104. `Mult` represents the premium multiplier. `StrkMult` and `StrkValu` have different meanings. Each `Undly` describes a delivery component, including cash when present. Product and series identity must agree.

Keep business and activation/inactivation dates as dates. They do not establish when a consumer could observe the data. The decoded result retains original-byte hashes and lengths, explicit multipliers and every delivery component. Missing, ambiguous or unsupported input is refused. Adjusted, cash-settled and multiple-component terms must not become standard 100-share terms by default.

The output is decoding evidence, not `options.contract_terms_observation/v1`. A later admitted source binding must supply real source availability and observation clocks and the effective timestamp interpretation before the research-expression consumer can use it. Synthetic test messages prove parsing behavior only. No current entitlement, source ingestion, activation, publication or trade authority is claimed.

The decoder uses the suite's existing `validate_contract` identity: `root`, `expiration`, `right`, canonical `strike`, `strike_millis`, and `occ_symbol`. All fields must agree. It does not translate a shorter provider identity into an admitted contract or guess omitted identity fields.

The supported OCC series shape is `SecList/SecL/Instrmt`, with events inside `Instrmt`. Product `Pty/Sub` metadata and pending underlying `UndAID` attributes are retained without interpreting them as authorization or effective timestamps. A cash delivery component may explicitly have zero allocation percent. The standard-share flag requires the OCC equity CFI `EXXXXX`; another six-letter code is not silently treated as equivalent. XML is bounded UTF-8 with DTD/entities and unsupported wrappers refused.
