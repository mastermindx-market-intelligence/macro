"""Pure prompt parity against the accepted writer before the ISO wording change."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))
from engine.press import writer
from tests import press_fixtures as F

BASE = 'e7112006a5d69b9fb125ff5e36f2f61a6174dadd'
old_bytes = subprocess.check_output(
    ['git', 'show', BASE + ':engine/press/writer.py'], cwd=ROOT)
old = types.ModuleType('engine.press._iso_prompt_baseline')
old.__file__ = str(ROOT / 'engine/press/writer.py')
old.__package__ = 'engine.press'
sys.modules[old.__name__] = old
exec(compile(old_bytes, old.__file__, 'exec'), old.__dict__)
cfg = F.config()
slots = {
    'brief': F.slot(),
    'external_brief': F.external_slot(),
    'earnings_claim_scope_fixture': F.slot(approved_claim_ids=['claim-1']),
}
parity = {}
for name, slot in slots.items():
    before = copy.deepcopy(slot)
    parity[name] = old.build_prompt(slot, cfg) == writer.build_prompt(slot, cfg)
    assert parity[name] and slot == before
selected = json.loads((Path(__file__).parent.parent /
    'planner_preflight_20261014_1507/selected_slot.json').read_text())
before = copy.deepcopy(selected)
old_system, old_user = old.build_prompt(selected, cfg)
new_system, new_user = writer.build_prompt(selected, cfg)
assert old_user == new_user and selected == before
instruction = ('DATES: render each observation date with its supplied YYYY-MM-DD '
    'value. Do not spell it into separate month/day numerals or replace '
    'it with the run date. A date is a vintage, not a numeric receipt.\n')
assert new_system.replace(instruction, '', 1) == old_system
print(json.dumps({
    'baseline': BASE,
    'unchanged_prompt_bytes': parity,
    'selected_slot_and_user_prompt_unchanged': True,
    'system_delta_is_only_iso_instruction': True,
    'writer_sha256': hashlib.sha256(Path(writer.__file__).read_bytes()).hexdigest(),
    'provider_calls': 0, 'staging_writes': 0, 'publication': False,
}, indent=2))
