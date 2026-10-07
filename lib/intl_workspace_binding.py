"""Validation for explicitly versioned workspace envelopes."""
import re


_GENERATION_PREFIX = 'im-workspace-generation:'
VALID_BINDING_VERSIONS = frozenset((1, 2))
_UUID_V4 = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def binding_version(workspace):
    """Return (version, generation reference) for an explicitly bound envelope."""
    if (type(workspace) is not dict or type(workspace.get('config')) is not dict
            or type(workspace.get('panels')) is not list):
        raise ValueError('invalid workspace binding envelope')
    version = workspace.get('binding_version', 1)
    if type(version) is not int or version not in VALID_BINDING_VERSIONS:
        raise ValueError('invalid workspace binding version')
    panels = workspace['panels']
    for name in ('compares', 'inspectors'):
        if name in workspace:
            if type(workspace[name]) is not list:
                raise ValueError('invalid workspace binding envelope')
            panels = panels + workspace[name]
    if any(type(panel) is not dict for panel in panels):
        raise ValueError('invalid workspace binding envelope')
    if 'generation' in workspace:
        raise ValueError('unexpected workspace generation alias')
    if version == 1:
        if 'library_generation' in workspace or any('generation' in panel for panel in panels):
            raise ValueError('mixed workspace binding versions')
        return 1, None
    config = workspace.get("config")
    source_reference = config.get("source_reference") if type(config) is dict else None
    if (type(source_reference) is not str
            or not source_reference.startswith(_GENERATION_PREFIX)):
        raise ValueError("missing workspace generation")
    generation = source_reference[len(_GENERATION_PREFIX):]
    if _UUID_V4.fullmatch(generation) is None:
        raise ValueError("invalid workspace generation")
    for panel in panels:
        panel_generation(panel, source_reference)
    if ('library_generation' in workspace
            and workspace['library_generation'] != source_reference):
        raise ValueError('mixed Library generation')
    return 2, source_reference


def panel_generation(panel, generation):
    """Validate a per-panel sidecar and return the v2 generation."""
    if type(panel) is not dict:
        raise ValueError("invalid panel generation")
    if panel.get("generation") != generation:
        raise ValueError("missing or mismatched panel generation")
    return generation
