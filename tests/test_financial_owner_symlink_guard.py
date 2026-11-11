from pathlib import Path
import pytest
from scripts.restore_event_workspace_owner import _assert_local_owner_paths


@pytest.mark.parametrize('redirect',['data','company_intelligence','event_workspaces','generations','generation','workspaces','leaf','dangling_leaf','marker'])
def test_any_owner_ancestor_or_leaf_symlink_refuses_before_writes(tmp_path,redirect):
    root=tmp_path/'requested';root.mkdir();outside=tmp_path/'outside';outside.mkdir()
    target=root/'data/company_intelligence/event_workspaces/generations/generation/workspaces/event.json'
    marker=root/'data/company_intelligence/event_workspaces/manifest.json'
    levels={'data':root/'data','company_intelligence':root/'data/company_intelligence','event_workspaces':root/'data/company_intelligence/event_workspaces','generations':root/'data/company_intelligence/event_workspaces/generations','generation':root/'data/company_intelligence/event_workspaces/generations/generation','workspaces':target.parent,'leaf':target,'dangling_leaf':target,'marker':marker}
    link=levels[redirect];link.parent.mkdir(parents=True,exist_ok=True)
    dest=outside/('missing' if redirect=='dangling_leaf' else 'redirected')
    if redirect not in ('leaf','dangling_leaf','marker'):dest.mkdir()
    elif redirect!='dangling_leaf':dest.write_bytes(b'protected outside bytes')
    link.symlink_to(dest)
    with pytest.raises(ValueError,match='symlink'):_assert_local_owner_paths(root,[target,marker])
    assert not (outside/'manifest.json').exists() and link.is_symlink()


def test_regular_paths_allowed_outside_target_or_file_ancestor_refused(tmp_path):
    root=tmp_path/'requested';root.mkdir();target=root/'data/company_intelligence/event_workspaces/manifest.json'
    _assert_local_owner_paths(root,[target]);assert not target.exists()
    with pytest.raises(ValueError,match='outside_root'):_assert_local_owner_paths(root,[tmp_path/'outside'])
    (root/'data').write_bytes(b'not a directory')
    with pytest.raises(ValueError,match='not_directory'):_assert_local_owner_paths(root,[target])


@pytest.mark.parametrize('location',['root','leaf'])
def test_nonregular_root_or_target_refuses_before_first_write(tmp_path,location):
    root=tmp_path/'requested';target=root/'data/company_intelligence/event_workspaces/manifest.json'
    if location=='root':root.write_bytes(b'protected root file')
    else:target.mkdir(parents=True)
    with pytest.raises(ValueError,match='not_directory|not_file'):_assert_local_owner_paths(root,[target])
