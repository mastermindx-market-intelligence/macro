"""Closed precomputed theme pair validation for publisher, renderer and API."""
from jsonschema import Draft202012Validator,FormatChecker
import json
from urllib.parse import urlsplit
from . import program_theme_context as t
from .program_theme_disclosure import validate_public_theme_disclosure

def validate_precomputed_theme_pair(reference,public):
 schema=json.loads((t._SCHEMA_ROOT/'government_program_theme_context.v1.schema.json').read_text())
 if next(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(reference),None) is not None:raise ValueError('theme_reference_shape_invalid')
 if reference['content_id']!=t.content_id(reference) or [x['theme_id'] for x in reference['themes']]!=list(t.THEMES):raise ValueError('theme_reference_identity_invalid')
 validate_public_theme_disclosure(public)
 if public['theme_content_id']!=reference['content_id'] or public['as_of']!=reference['as_of']:raise ValueError('theme_pair_binding_invalid')
 for canonical,row in zip(reference['themes'],public['themes']):
  expected='SOURCE_CONTEXT_COMPLETE' if all(x['state']=='supported' for x in canonical['rails'].values()) else 'EVIDENCE_INSUFFICIENT'
  if canonical['research_state']!=expected:raise ValueError('theme_reference_state_invalid')
  refs={(r['owner_key'],r['pointer'],r['row_id']) for item in canonical['rails'].values() for r in item['references']}
  for rail,state in row['rail_states'].items():
   if state in ('supported','partial') and state!=canonical['rails'][rail]['state']:raise ValueError('theme_public_state_promotion')
  for source in row['sources']:
   if (source['owner_key'],source['pointer'],source['row_id']) not in refs:raise ValueError('theme_public_reference_unbound')
   owner=reference['owner_bindings'].get(source['owner_key'])
   if not owner or owner['rights_state']!='qualified_public_display':raise ValueError('theme_public_owner_unqualified')
   url=urlsplit(source['url'])
   if url.scheme!='https' or not url.hostname or url.username or url.password:raise ValueError('theme_public_url_invalid')
 return True
