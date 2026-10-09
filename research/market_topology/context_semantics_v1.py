"""Research-only context/outcome specifications; no files, network or production calls.
All source identities, periods and economic outcomes are supplied by existing owners.
"""
from dataclasses import dataclass
from math import isfinite, log
from typing import Mapping


def economic_outcome(initial_wealth: float, terminal_wealth: float | None,
                     *, status: str) -> dict:
    """Represent zero as an observed atom; never silently discard it via log(0)."""
    if not isfinite(initial_wealth) or initial_wealth <= 0:
        raise ValueError('Positive formation wealth required')
    if status == 'unresolved':
        if terminal_wealth is not None:
            raise ValueError('Unresolved outcomes do not carry an observed terminal value')
        return {'simple_return':None, 'log_return':None, 'rank_eligible':False,
                'reason':'UNRESOLVED_ECONOMICS'}
    if status not in {'observed', 'observed_total_loss'} or terminal_wealth is None:
        raise ValueError('Explicit known outcome status/value required')
    if not isfinite(terminal_wealth) or terminal_wealth < 0:
        raise ValueError('Unlevered economic wealth must be finite and nonnegative')
    if (terminal_wealth == 0) != (status == 'observed_total_loss'):
        raise ValueError('A verified zero needs an explicit total-loss status')
    gross=terminal_wealth/initial_wealth
    if not isfinite(gross):
        raise ValueError('Unrepresentable economic wealth ratio')
    return {'simple_return':gross-1, 'log_return':log(gross) if gross>0 else None,
            'rank_eligible':True, 'reason':'OBSERVED_TOTAL_LOSS' if gross==0 else None}


def relative_return(security_return:float, benchmark_return:float) -> float:
    """Unlevered relative wealth; a common positive benchmark preserves rankings."""
    if not all(isfinite(x) for x in [security_return,benchmark_return]):
        raise ValueError('Finite returns required')
    if security_return < -1 or benchmark_return <= -1:
        raise ValueError('Nonnegative security wealth and positive benchmark wealth required')
    result=(1+security_return)/(1+benchmark_return)-1
    if not isfinite(result):
        raise ValueError('Unrepresentable relative return')
    return result


@dataclass(frozen=True)
class EstimateSet:
    """A fixed economic target, not the shifting label 'next fiscal year'."""
    security_id:str
    metric:str
    fiscal_period:str
    accounting_basis:str
    currency:str
    share_basis:str
    by_analyst:Mapping[str,float]

    def target_key(self) -> tuple:
        return (self.security_id,self.metric,self.fiscal_period,self.accounting_basis,
                self.currency,self.share_basis)

    def __post_init__(self) -> None:
        if not all(isinstance(x,str) and x for x in self.target_key()):
            raise ValueError('All economic target dimensions must be explicit')
        if any(not isinstance(k,str) or not k or not isfinite(v)
               for k,v in self.by_analyst.items()):
            raise ValueError('Known analyst identities and finite estimates required')


def revision_bridge(old:EstimateSet, new:EstimateSet) -> dict:
    """Equal-weight mean change: incumbent revision plus composition change.
    This is descriptive, not analyst alpha. Source availability must already pass.
    """
    if old.target_key()!=new.target_key():
        raise ValueError('Do not compare changed fiscal targets, basis, currency or identity')
    a,b=dict(old.by_analyst),dict(new.by_analyst)
    common=set(a)&set(b)
    if not a or not b or not common:
        return {'all_analyst_mean_change':None,'common_analyst_mean_revision':None,
                'composition_component':None,'n_common':len(common),
                'n_entered':len(set(b)-set(a)),'n_exited':len(set(a)-set(b)),
                'reason':'NO_COMMON_ANALYST_SUPPORT'}
    all_change=sum(b.values())/len(b)-sum(a.values())/len(a)
    common_change=sum(b[k]-a[k] for k in common)/len(common)
    return {'all_analyst_mean_change':all_change,
            'common_analyst_mean_revision':common_change,
            'composition_component':all_change-common_change,
            'n_common':len(common),'n_entered':len(set(b)-set(a)),
            'n_exited':len(set(a)-set(b)), 'reason':None}
