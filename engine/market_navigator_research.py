"""Research intake over the incumbent grounded extractor; no model or corpus effects.

This is a completeness/chronology audit, NOT source authentication, semantic proof,
forecast scoring, trial registration or a new claim store. Raw bodies remain with
existing rights-approved acquisition owners. Returned records contain hashes only.
"""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
import re
from typing import Mapping
from engine.market_navigator import AUTHORITY, ContractError, _clock, _ref
from engine.research_intelligence.extractor import parse_model_output

OUTCOMES=frozenset({'level_touch','terminal_close','path_order','realized_volatility',
    'stock_return','option_pnl','qualitative'})
_HEX=re.compile(r'[a-f0-9]{64}\Z')


def claim_identity(document_hash: str, statement: str) -> str:
    if not isinstance(document_hash,str) or not _HEX.fullmatch(document_hash):
        raise ContractError('exact source body hash required')
    if not isinstance(statement,str) or not statement.strip() or len(statement)>1800:
        raise ContractError('bounded statement required')
    return sha256((document_hash+'\n'+statement).encode('utf-8')).hexdigest()


@dataclass(frozen=True)
class ResearchRuler:
    """Externally reviewed annotation, not a market claim synthesized by this code."""
    claim_id: str
    annotation_ref: str
    annotation_available_at: str
    subject: str | None=None
    outcome: str | None=None
    decision_at: str | None=None
    deadline: str | None=None
    horizon: str | None=None
    conditional: bool | None=None
    trigger_ref: str | None=None
    invalidation_ref: str | None=None
    executable_expression_ref: str | None=None

    def __post_init__(self):
        if not isinstance(self.claim_id,str) or not _HEX.fullmatch(self.claim_id):
            raise ContractError('claim annotation needs exact source-bound identity')
        _ref(self.annotation_ref);_clock(self.annotation_available_at)
        if self.outcome is not None and self.outcome not in OUTCOMES:
            raise ContractError('unknown outcome ruler')
        if self.conditional is not None and type(self.conditional) is not bool:
            raise ContractError('conditional must be boolean or unknown')
        for key in ('subject','horizon','trigger_ref','invalidation_ref','executable_expression_ref'):
            value=getattr(self,key)
            if value is not None: _ref(value)
        for key in ('decision_at','deadline'):
            value=getattr(self,key)
            if value is not None: _clock(value)
        if self.decision_at is not None and self.deadline is not None:
            if _clock(self.deadline)<=_clock(self.decision_at):
                raise ContractError('forecast deadline must follow its decision time')


def audit_extraction(raw_output: str, *, document: Mapping, source_body: str,
        captured_at: str, revision_available_at: str | None,
        rulers: tuple[ResearchRuler,...]=()) -> dict:
    """Ground first through existing extractor, then audit source-bound annotations.

    Current download/capture never proves the originally published revision. Even
    an annotation predating its decision is only temporally consistent, not a
    prospective capture receipt or permission to run a research trial.
    """
    if not isinstance(source_body,str) or not source_body or len(source_body.encode('utf-8'))>1_000_000:
        raise ContractError('source body must be nonempty and at most one megabyte')
    if not isinstance(raw_output,str) or len(raw_output.encode('utf-8'))>256_000:
        raise ContractError('bounded extraction response required')
    if not isinstance(document,Mapping): raise ContractError('source document required')
    captured=_clock(captured_at)
    digest=sha256(source_body.encode('utf-8')).hexdigest()
    if document.get('content_sha256')!=digest:
        raise ContractError('source body differs from the document identity')
    publication=document.get('published_at')
    try: published=_clock(publication)
    except ContractError: published=None
    revision=None if revision_available_at is None else _clock(revision_available_at)
    if (published is not None and published>captured) or (revision is not None and revision>captured):
        raise ContractError('source evidence cannot become available after this capture')
    if published is not None and revision is not None and revision<published:
        raise ContractError('revision availability cannot precede original publication')
    if not isinstance(rulers,tuple) or len(rulers)>64 or not all(isinstance(r,ResearchRuler) for r in rulers):
        raise ContractError('bounded typed ruler tuple required')
    annotated={}
    for ruler in rulers:
        if ruler.claim_id in annotated: raise ContractError('duplicate claim annotation')
        annotated[ruler.claim_id]=ruler
    try:
        grounded=parse_model_output(raw_output,expected_document_id=str(document.get('id','')),
            expected_document=dict(document),source_body=source_body)
    except (ValueError,TypeError,KeyError) as exc:
        raise ContractError('extraction did not retain complete source grounding') from exc
    rows=[]; known=set()
    for claim in grounded['claims']:
        identity=claim_identity(digest,claim['statement']);known.add(identity)
        ruler=annotated.get(identity);gaps=[]
        if published is None: gaps.append('publication_clock_unknown')
        if revision is None: gaps.append('original_revision_availability_unknown')
        if ruler is None:
            gaps.append('reviewed_ruler_missing')
        else:
            for name in ('subject','outcome','decision_at','deadline','horizon','conditional'):
                if getattr(ruler,name) is None:gaps.append(name+'_unspecified')
            if ruler.conditional is True and ruler.trigger_ref is None:gaps.append('trigger_unspecified')
            if ruler.invalidation_ref is None:gaps.append('invalidation_unspecified')
            if ruler.outcome=='option_pnl' and ruler.executable_expression_ref is None:
                gaps.append('executable_option_expression_unspecified')
            if ruler.outcome=='qualitative':gaps.append('qualitative_not_scored')
            if ruler.decision_at is not None:
                decision=_clock(ruler.decision_at)
                if _clock(ruler.annotation_available_at)>decision:gaps.append('retrospective_annotation')
                if revision is not None and revision>decision:gaps.append('source_revision_after_decision')
                if published is not None and published>decision:gaps.append('publication_after_decision')
        rows.append({'claim_id':identity,'source_body_sha256':digest,
            'statement_sha256':sha256(claim['statement'].encode()).hexdigest(),
            'literal_grounding':'incumbent_extractor_passed',
            'annotation_status':'missing' if ruler is None else 'externally_supplied_not_semantically_verified',
            'outcome':None if ruler is None else ruler.outcome,
            'status':'not_scoreable_as_specified' if gaps else 'ruler_fields_present_not_validated',
            'gaps':gaps,'forecast_probability':None,'prospective_proof':False})
    if set(annotated)-known:
        raise ContractError('annotation refers to absent or ungrounded source claim')
    if len(known)!=len(rows): raise ContractError('duplicate source claim requires explicit deduplication')
    return {'schema':'market_navigator.research_intake/v1','source_body_sha256':digest,
        'captured_at':captured.isoformat(),'claims':rows,
        'counts':{'grounded_claims':len(rows),'unscoreable':sum(bool(r['gaps']) for r in rows)},
        'raw_source_included':False,'source_authenticity_proven':False,
        'trial_registered':False,'predictive_validation':False,'authority':dict(AUTHORITY)}
