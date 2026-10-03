def build_situations() -> pd.DataFrame:
    """Classify + enrich + floor every stored event. Returns the full frame
    (all rows, with category/stage/status/ticker/mc/floor_pass/cross_border)."""
    p = config.data_dir() / GROUP / "events.parquet"
    if not p.exists():
        return pd.DataFrame()
    df = pd.read_parquet(p)
    if df.empty:
        return df

    cats, stages, status = [], [], []
    for _, row in df.iterrows():
        c, s, st = classify(row.get("form_type"), row.get("items"))
        cats.append(c); stages.append(s); status.append(st)
    df = df.assign(category=cats, stage=stages, status=status)

    # confidence: structured-form / decisive-item classifications are HIGH; the keyword
    # text lane is a HEURISTIC (audit found ~67% FP on unvalidated extras) -> LOW, so the
    # desk + trading brain never treat keyword guesses as facts. The LLM lane (P1.3) or a
    # digest match upgrades a situation's standing downstream.
    df["confidence"] = "high"

    # text lane (P1.1b): deferred filings the enrichment step classified from document text.
    if "text_category" in df.columns:
        items_s = df["items"].astype(str) if "items" in df.columns else pd.Series("", index=df.index)
        promote = (df.status == "defer") & df.text_category.notna() & (df.text_category != "")
        # a 424B5 is a securities OFFERING (shelf raise) — its boilerplate trips M&A
        # keywords; only a genuine Rights Offering qualifies, never Acq/Divest/Spin/etc.
        promote &= ~((df.form_type == "424B5") & (df.text_category != RIGHTS))
        # Deal Terminations needs the 8-K termination item (1.02); without it, the keyword
        # is usually deal-ENTRY/progress boilerplate (audit: 5/6 Deal-Term extras were FPs).
        promote &= ~((df.text_category == TERM) & ~items_s.str.contains("1.02", na=False))
        df.loc[promote, "category"] = df.loc[promote, "text_category"]
        df.loc[promote, "stage"] = df.loc[promote, "text_stage"] if "text_stage" in df.columns else "announced"
        df.loc[promote, "status"] = "ok"
        df.loc[promote, "confidence"] = "low"        # keyword heuristic, not verified

    # LLM verify lane (P1.1): the model read the deferred filings and returned a verified
    # category + role + confidence. This OVERRIDES the noisy keyword text-lane — a real
    # category becomes high/medium-confidence; category "None" is the model judging it not a
    # special situation, which DROPS the keyword false positive (the ~67%-FP precision fix).
    if "llm_category" in df.columns:
        for col in ("llm_confidence", "llm_role", "role"):
            if col not in df.columns:
                df[col] = pd.NA
        llm = df.llm_category.astype("string").str.strip()
        valid = llm.isin(LLM_PROMOTABLE).fillna(False)
        is_none = llm.str.lower().eq("none").fillna(False)
        if valid.any():
            df.loc[valid, "category"] = llm[valid]
            df.loc[valid, "status"] = "ok"
            df.loc[valid, "role"] = df.loc[valid, "llm_role"]
            conf = df.loc[valid, "llm_confidence"].astype("string").str.lower()
            df.loc[valid, "confidence"] = conf.where(conf.isin(["high", "medium", "low"]), "medium")
            df.loc[valid, "stage"] = df.loc[valid].apply(
                lambda r: r["stage"] if (r.get("stage") and not (isinstance(r["stage"], float) and pd.isna(r["stage"])))
                else LLM_STAGE_DEFAULT.get(r["category"], "announced"), axis=1)
        if is_none.any():
            df.loc[is_none, ["status", "category", "stage", "confidence"]] = ["skip", None, None, "high"]

    # cross-filing Going-Private upgrade: any CIK with an SC 13E-3 -> its merger
    # proxy / third-party tender is an affiliate take-private (§B1).
    gp_ciks = set(df.loc[df.form_type.str.startswith("SC 13E3"), "cik"].astype(str))
    upg = df.cik.astype(str).isin(gp_ciks) & df.category.isin([ACQ, TO])
    df.loc[upg, ["category", "stage"]] = [GP, "live"]

    # SPAC reclassification: a de-SPAC S-4 / merger proxy / 8-K from a blank-check
    # shell is a SPAC combination, not a plain acquisition (benchmark gap §P1.5).
    spac_name = df.company.str.contains(r"ACQUISITION CORP|BLANK CHECK|\bSPAC\b",
                                        case=False, na=False, regex=True)
    spac = spac_name & (df.status == "ok") & df.category.isin([ACQ, SPIN])
    df.loc[spac, ["category", "stage"]] = [SPAC, "de-SPAC"]

    # collapse multi-security-class delistings: one filer files separate Form 25 for
    # common + warrants + units + rights (esp. de-SPACs) -> one event per filer/day.
    dl = df[(df.status == "ok") & (df.category == DELIST)]
    if not dl.empty:
        dup_idx = dl[dl.duplicated(subset=["cik", "date_filed"], keep="first")].index
        df.loc[dup_idx, "status"] = "skip"

    # drop high-confidence non-operating-company filers (ABS/ETF/exchange shells)
    noise = df.company.apply(_is_noise_filer)
    df.loc[noise, ["status", "category", "stage"]] = ["skip", None, None]

    df["cross_border"] = df.apply(_is_cross_border, axis=1)

    cik_ticker, mc = _universe_caps()
    df["ticker"] = df.cik.apply(lambda c: cik_ticker.get(int(c)) if str(c).isdigit() else None)
    df["mc_musd"] = df.ticker.apply(lambda t: mc.get(t))
    floor = float(_cfg().get("market_cap_floor_musd", 100))
    df["floor_pass"] = df.mc_musd.apply(lambda m: apply_floor(m, floor))

    # lifecycle / stage tracking (P3.1): link each deal's filings into a timeline and stamp
    # the current stage (incl. terminal "terminated"/"closed") + amendment count per row.
    lc = lifecycle(df)
    keys = list(zip(df.cik.astype(str), df.category))
    df["current_stage"] = [(lc.get(k) or {}).get("current_stage") for k in keys]
    df["n_amendments"] = [(lc.get(k) or {}).get("n_amendments") for k in keys]
    df["deal_terminal"] = [(lc.get(k) or {}).get("terminal") for k in keys]
    return df
