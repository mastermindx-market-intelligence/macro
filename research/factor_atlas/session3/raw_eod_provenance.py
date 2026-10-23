"""Private read-only raw EOD Greek -> incumbent normalized parquet audit.

This does not fetch data, write a chain, manufacture source authorization or
reconstruct historical NBBO quote timestamps. The vendor's raw trade/report
timestamp and underlying mark timestamp are NOT market quotation publication.
The output is counts/field disagreements only, never restricted source values.
"""
from __future__ import annotations

from datetime import date,datetime
from math import isfinite
import pandas as pd
import numpy as np

_ID=['root','expiration','strike','right','date']
_FIELDS=['bid','ask','underlying_price','implied_vol','iv_error',
         'delta','gamma','vanna','charm']
_REQUIRED_RAW={'symbol','expiration','strike','right','timestamp',*_FIELDS}
_REQUIRED_PERSISTED={*_ID,*_FIELDS}


def _datetime_series(series: pd.Series) -> pd.Series:
    # Original vendor EOD clocks are ISO8601 timestamps, not epoch nanosecond
    # scalar IDs. Pandas' unconstrained parser can silently reinterpret
    # integer source values as Unix nanoseconds, corrupting provenance.
    if not series.map(lambda v: isinstance(v,(str,datetime)) or pd.isna(v)).all():
        raise ValueError('source timestamp requires textual ISO8601 or typed datetime')
    vals=pd.to_datetime(series,format='ISO8601',errors='coerce')
    # Mixed timezone offsets may have object dtype: refuse instead of
    # reconciling timezone conversion without the source owner's clock rule.
    if not pd.api.types.is_datetime64_any_dtype(vals.dtype):
        raise ValueError('source timestamp representation ambiguous')
    return vals


def audit_eod_report(*,raw:pd.DataFrame,persisted:pd.DataFrame,
                     root:str,requested_session:date)->dict:
    """Independently compare a single exact-date raw Greek report to archive.

    Numeric equality and root/contract parity are a necessary *reproduction*
    result, not a sufficient EOD mark/entitlement/quote-time proof.
    """
    if type(requested_session) is not date:
        raise ValueError('canonical requested cash session date required')
    if not isinstance(root,str) or not root or root!=root.strip():
        raise ValueError('typed source root required')
    if not isinstance(raw,pd.DataFrame) or not isinstance(persisted,pd.DataFrame) or raw.empty:
        raise ValueError('nonempty raw vendor source DataFrame required')
    if not _REQUIRED_RAW.issubset(raw.columns) or not _REQUIRED_PERSISTED.issubset(persisted.columns):
        raise ValueError('required original source normalization columns missing')
    if raw.columns.duplicated().any() or persisted.columns.duplicated().any():
        raise ValueError('ambiguous duplicate source columns')
    if not raw['symbol'].eq(root).fillna(False).all() or not persisted['root'].eq(root).fillna(False).all():
        raise ValueError('original raw/archived root identity mismatch')
    # The incumbent normalizer drops fully identical v3 CSV row duplicates;
    # conflicting rows with the same contract key remain an admission refusal.
    clean=raw.drop_duplicates().copy(deep=True)
    duplicate_full=len(raw)-len(clean)
    clean['root']=clean['symbol'].astype(str).str.strip().str.strip('"')
    # ThetaData EOD CSV uses ISO YYYY-MM-DD, whereas a few historical raw
    # fixtures and callers may present YYYYMMDD. Admit only those two
    # explicit 10/8-character calendar spellings; never infer UNIX nanos.
    expiry=clean['expiration'].astype(str).str.strip('"').str.strip()
    is_iso=expiry.str.fullmatch(r'\d{4}-\d{2}-\d{2}')
    is_compact=expiry.str.fullmatch(r'\d{8}')
    if not (is_iso | is_compact).all():
        raise ValueError('unrecognized raw expiry calendar format')
    normalized=pd.Series(pd.NaT,index=clean.index,dtype='datetime64[ns]')
    normalized.loc[is_iso]=pd.to_datetime(expiry.loc[is_iso],format='%Y-%m-%d',errors='coerce')
    normalized.loc[is_compact]=pd.to_datetime(expiry.loc[is_compact],format='%Y%m%d',errors='coerce')
    clean['expiration']=normalized
    clean['right']=clean['right'].astype(str).str.strip('"').str.strip().map(
        {'CALL':'C','PUT':'P','C':'C','P':'P'})
    clean['date']=_datetime_series(clean['timestamp']).dt.normalize()
    clean['strike']=pd.to_numeric(clean['strike'],errors='coerce')
    arc=persisted.copy(deep=True)
    arc['expiration']=pd.to_datetime(arc['expiration'],errors='coerce')
    arc['date']=pd.to_datetime(arc['date'],errors='coerce')
    arc['strike']=pd.to_numeric(arc['strike'],errors='coerce')
    if any(clean[k].isna().any() for k in _ID) or any(arc[k].isna().any() for k in _ID):
        raise ValueError('source contract identity parsing incomplete')
    if clean.duplicated(_ID).any() or arc.duplicated(_ID).any():
        raise ValueError('conflicting duplicate contract identity')
    clock=_datetime_series(raw['timestamp'])
    wrong=int((clock.dt.date!=requested_session).sum())
    underlier_present='underlying_timestamp' in raw
    underlier_clock=_datetime_series(raw['underlying_timestamp']) if underlier_present else None
    # The original EOD Greek report can carry an underlying mark from a
    # different source session. Matching numeric prices never repairs that
    # clock mismatch, and this audit cannot reconstruct quote known-at.
    underlier_wrong=(int((underlier_clock.dt.date!=requested_session).sum())
                     if underlier_clock is not None else None)
    m=clean[_ID+_FIELDS].merge(
        arc[_ID+_FIELDS],on=_ID,how='outer',
        suffixes=('_source','_persisted'),indicator=True,validate='one_to_one')
    both=m['_merge'].eq('both')
    disputes={}
    for field in _FIELDS:
        raw_source=m.loc[both,field+'_source']
        raw_archive=m.loc[both,field+'_persisted']
        source=pd.to_numeric(raw_source,errors='coerce').to_numpy(dtype=float)
        archive=pd.to_numeric(raw_archive,errors='coerce').to_numpy(dtype=float)
        if len(source)==0:
            disagreements=0
        else:
            # Coercion loss is NOT an authentic missing vendor observation.
            # In particular "INVALID" versus true NaN, and inf versus inf,
            # cannot be silently marked as reproduced by equal_nan=True.
            source_invalid=(raw_source.notna().to_numpy() & np.isnan(source))
            archive_invalid=(raw_archive.notna().to_numpy() & np.isnan(archive))
            source_bool=raw_source.map(lambda v:isinstance(v,(bool,np.bool_))).to_numpy()
            archive_bool=raw_archive.map(lambda v:isinstance(v,(bool,np.bool_))).to_numpy()
            invalid=(source_invalid|archive_invalid|source_bool|archive_bool|
                     np.isinf(source)|np.isinf(archive))
            matches=(
                (np.isfinite(source)&np.isfinite(archive)&
                 np.isclose(source,archive,rtol=1e-10,atol=1e-10)) |
                (np.isnan(source)&np.isnan(archive)&~invalid)
            ) & ~invalid
            disagreements=int((~matches).sum())
        disputes[field]=disagreements
    missing=int((m['_merge']=='left_only').sum())
    added=int((m['_merge']=='right_only').sum())
    reasons=[]
    if wrong>0:reasons.append('SOURCE_DATE_AMBIGUOUS')
    if underlier_wrong is not None and underlier_wrong>0:
        reasons.append('UNDERLIER_MARK_SESSION_MISMATCH')
    if missing or added:reasons.append('SOURCE_KEY_MISMATCH')
    if any(disputes.values()):reasons.append('NUMERIC_REPRODUCTION_MISMATCH')
    report_equal=not reasons
    return {
        'schema':'factor_atlas.s3.raw_eod_clock_and_archive_audit/v1',
        'root':root,
        'requested_source_session':requested_session.isoformat(),
        'raw_rows':len(raw),
        'vendor_duplicate_full_rows':duplicate_full,
        'archived_rows':len(arc),
        'matching_contract_keys':int(both.sum()),
        'missing_from_archive':missing,
        'not_in_new_vendor_report':added,
        'numeric_field_disagreements':disputes,
        'numeric_report_reproduced':report_equal,
        'source_consistency_reasons':reasons,
        'original_option_timestamp_in_vendor_report':'timestamp' in raw,
        'option_report_timestamp_distinct_count':int(clock.nunique()),
        'raw_report_timestamp_wrong_session_rows':wrong,
        'original_underlier_timestamp_in_vendor_report':underlier_present,
        'raw_underlier_timestamp_distinct_count':int(underlier_clock.nunique()) if underlier_clock is not None else None,
        'raw_underlier_timestamp_wrong_session_rows':underlier_wrong,
        'option_timestamp_lost_in_archive':'timestamp' in raw and 'timestamp' not in arc,
        'underlier_timestamp_lost_in_archive':underlier_present and 'underlying_timestamp' not in arc,
        'persisted_bid_ask_conditions_available':all(x in arc for x in ('bid_condition','ask_condition')),
        'historical_quote_time_qualified':False,
        'historical_known_at_qualified':False,
        'source_rights_for_publication_certified':False,
        'source_pricing_mark_convention_certified':False,
        'publishable_original_market_data':False,
    }
