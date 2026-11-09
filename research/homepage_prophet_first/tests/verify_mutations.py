"""Deliberate structural regressions against a passing proposal, not claims of model evaluation."""
import importlib.util, json
from pathlib import Path
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('contract',ROOT/'tests/test_product_contract.py')
contract=importlib.util.module_from_spec(spec);spec.loader.exec_module(contract)
source=(ROOT/'prototype.html').read_text()

def hidden_flagship(s): s.select_one('.eyebrow')['hidden']=''
def remove_identity(s): s.select_one('.eyebrow').decompose()
def collapse(s):
    d=s.new_tag('details'); s.select_one('#signal-example').wrap(d)
def wrong_cta(s): s.select_one('#primary-cta')['href']='https://app.mastermind-x.com/terminal'
def wrong_nav(s): s.select_one('nav .product-link').string='Company Research'
def hide_date(s): s.select_one('#sample-disclosure')['hidden']=''
def omit_selection(s): s.select_one('#sample-disclosure').string='Historical example 2026-08-21, not current signals.'
def score_probability(s): s.select_one('#edge-grade').string='61%'
def reverse_caution(s):
    e=s.select_one('#prepared-read p');e.string=e.get_text().replace('accounting-quality concerns','accounting-quality strength')
def require_input(s): s.select_one('#signal-example').insert_before(s.new_tag('input'))

cases=[(remove_identity,'test_flagship_is_visible_in_the_hero_not_just_anywhere'),
(hidden_flagship,'test_flagship_is_visible_in_the_hero_not_just_anywhere'),
(collapse,'test_delivered_example_is_not_behind_a_closed_disclosure_or_research_work'),
(wrong_cta,'test_primary_navigation_and_cta_reach_existing_prophet_route'),
(wrong_nav,'test_primary_navigation_and_cta_reach_existing_prophet_route'),
(hide_date,'test_historical_and_winner_selection_disclosures_are_explicit'),
(omit_selection,'test_historical_and_winner_selection_disclosures_are_explicit'),
(score_probability,'test_example_fields_preserve_the_public_source_without_probability_claims'),
(reverse_caution,'test_cautions_are_not_recast_as_bullish_confirmation'),
(require_input,'test_delivered_example_is_not_behind_a_closed_disclosure_or_research_work')]
result=[]
for mutation,test in cases:
    s=BeautifulSoup(source,'html.parser');contract.load=lambda:s
    getattr(contract,test)() # Unchanged candidate must pass the same discriminator.
    mutation(s)
    try: getattr(contract,test)()
    except AssertionError as error:
        result.append({'mutation':mutation.__name__,'discriminator':test,'detected':True,'message':str(error)})
    else: raise AssertionError(f'Mutation escaped: {mutation.__name__}')
(ROOT/'evidence/mutation-results.json').write_text(json.dumps(result,indent=2)+'\n')
print(f'{len(result)} deliberate regressions rejected by the intended assertion; original proposal passed each control.')
