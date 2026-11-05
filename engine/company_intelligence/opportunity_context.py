"""Native earnings context -> K1/K3/K5, with no owner I/O or live claim."""
from engine.company_intelligence.opportunity_qualification import qualify_candidate_workspace
from lib import opportunity_evidence as oe


def compose_candidate_evidence(*, composed_at: str, **native_inputs) -> dict:
    """Qualify injected native reads, then compose one native CIK context.

    The candidate binding is a separate context receipt, not proof that the
    candidate's quote was this security. No caller-authored qualified output is
    accepted; qualification is rerun over the existing native inputs.
    """
    qualified = qualify_candidate_workspace(**native_inputs)
    evidence = qualified['evidence']
    rid, ref = next(iter(evidence['references'].items()))
    clocks = {c['field']:c['value'] for c in ref['clocks']}
    cutoff = qualified['candidate_binding']['candidate_at']
    from engine.company_intelligence.opportunity_qualification import _instant, EarningsQualificationError
    if _instant(composed_at) < _instant(cutoff):
        raise EarningsQualificationError('composition_clock_before_candidate')
    from engine.company_intelligence.events import FiscalPeriod
    selected = next(r['workspace'] for r in native_inputs['revisions']
                    if r['generation_id'] == ref['native_identity']['generation_id'])
    fiscal = FiscalPeriod(**selected['fiscal_period']).to_payload()
    link = {'fiscal_period':fiscal, 'schema':'earnings_context_read.v1', **ref['native_identity'],
            'workspace_sha256':ref['native_digest']['sha256'], 'cik':ref['subject']['key'],
            'source_available_at':clocks['lifecycle.source_available_at'],
            'observed_at':clocks['lifecycle.observed_at'], 'generated_at':clocks['generated_at'],
            'observation':qualified['observation']}
    recorded = {'value':link['generated_at'],'grain':'datetime','clock_class':'belief_or_build',
                'native_field':'generated_at','state':'known'}
    asof = {'value':cutoff,'grain':'datetime','t0_source':'earnings_workspace_context',
            't0_mode':'retrospective_research','t0_evidence_ref':{
                'owner_store':'earnings.workspace_generation','native_identity':ref['native_identity'],
                'native_digest':ref['native_digest'],'recorded_clock':recorded}}
    raw = {'construct':'earnings_reported_revenue','state':'observed',
           'value_or_null':{k:qualified['observation'][k] for k in ('value','unit','basis','period')},
           'asof':{'value':link['source_available_at'],'grain':'datetime'},
           'known_at':{'value':link['observed_at'],'grain':'datetime'},'earnings_context':link,
           'owner_ref':{**{k:oe.load_slot_registry()['constructs']['earnings_reported_revenue'][k]
                          for k in ('owner','artifact','reader')},'evidence_ref_id':rid},
           'coverage_flag':{'state':'partial','note':'native earnings context; whole-workspace rights/freshness unknown; no quote identity'}}
    vector = oe.compose_vector({'subject_type':'earnings_cik','value':link['cik'],
                                'identity_state':'single_owner_native','identity_bridge':None},
                               asof,[raw],generated_at=composed_at,permitted_consumers=['opportunity_case_k5'])
    if oe.validate_vector(vector):
        from engine.company_intelligence.opportunity_qualification import EarningsQualificationError
        raise EarningsQualificationError('earnings_context_vector_invalid')
    return {**evidence,'vector':vector,'candidate_context_binding':qualified['candidate_binding']}


def compose_candidate_case(**native_inputs) -> dict:
    """Research-session case only. Does not enroll or publish a LER attachment."""
    from lib.opportunity_case import compose_case
    evidence = compose_candidate_evidence(**native_inputs)
    return compose_case(**{k:evidence[k] for k in ('recipe','blocks','references','vector')})


def compose_earnings_candidate_case(*, episode: dict, event_id: str, revisions: list[dict],
                                     identity_read, vendor: str, composed_at: str) -> dict:
    """Pure consumer entry; pass native reads from BEFORE candidate creation.

    Filesystem/source I/O is external. Returns a validated K5 case plus a compact
    candidate-context receipt, not an eligible live Radar attachment.
    """
    from lib.opportunity_case import compose_case
    prepared=compose_candidate_evidence(composed_at=composed_at,episode=episode,event_id=event_id,revisions=revisions,
                                        identity_read=identity_read,vendor=vendor)
    case=compose_case(**{k:prepared[k] for k in ('recipe','blocks','references','vector')})
    return {'schema':'earnings.candidate_research.v1','case':case,
            'candidate_context_binding':prepared['candidate_context_binding'],
            'live_projection_eligible':False,
            'limitations':['whole_workspace_rights_unknown','freshness_policy_unknown',
                           'native_quote_use_not_established','owner_span_receipt_not_locally_replayed',
                           'no_surprise_calibration_or_entry_authority']}
