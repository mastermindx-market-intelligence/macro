"""Review discriminators over owned ordinary files, never real cgroupfs."""
import os
import traceback
from types import SimpleNamespace

import pytest
import cgroup_observer as c
from test_cgroup_observer import tree, controls


def test_visible_root_is_never_a_complete_host_hierarchy(tree):
    root,parent,leaf,_,_,observe=tree
    controls(root, cpu='10000 100000',memory='1048576',pids='4')
    # Supply a narrower held root: its successful controls cannot prove that
    # nothing above it is more restrictive. No host namespace is authenticated.
    fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY)
    try:
        r=c.observe(fd,('docker-owned.scope',),expected_root_identity=c.identity(os.fstat(fd)),deadline=101.,clock=lambda:100.)
    finally:os.close(fd)
    assert r['ancestors_above_root_observed'] is False
    assert r['mid_read_stability_proven'] is False
    row=r['configured_visible_ancestor_limits']['pids.max']
    assert row['observed_minimum']==32 and row['visible_level_absent'] is False
    assert row['summary_is_complete'] is False and row['source_depths']==[0]
    assert row['unit']=='tasks'


def test_units_and_depths_preserve_cpu_ratio_meaning(tree):
    *_,observe=tree
    r=observe();rows=r['configured_visible_ancestor_limits']
    cpu=rows['cpu.max']
    assert cpu['observed_minimum']=={'numerator':1,'denominator':4}
    assert cpu['unit']=='cpu_seconds_per_second' and cpu['source_depths']==[1]
    assert cpu['visible_level_absent'] is True and cpu['summary_is_complete'] is False
    assert rows['memory.max']['unit']==rows['memory.swap.max']['unit']=='bytes'
    assert r['observation']['levels'][1]['limits']['cpu.max']['value']=={'quota':25000,'period':100000}


def test_missing_control_context_is_suppressed(tree):
    _,parent,*_,observe=tree
    (parent/'pids.max').unlink()
    with pytest.raises(c.ObservationRefused) as got:observe()
    assert str(got.value)=='required_control_missing'
    assert got.value.__suppress_context__ is True
    assert 'FileNotFoundError' not in ''.join(traceback.format_exception(got.value))


@pytest.mark.parametrize('root_fd',[True,-1,'3'])
def test_root_fd_refuses_before_duplicate(tree,monkeypatch,root_fd):
    *_,expected,observe=tree
    monkeypatch.setattr(c.os,'dup',lambda *_:pytest.fail('duplicate before identity check'))
    with pytest.raises(c.ObservationRefused,match='^root_fd$'):
        c.observe(root_fd,('child',),expected_root_identity=expected,deadline=101.,clock=lambda:100.)


@pytest.mark.parametrize('binding',[[1,2],(1,),(True,2),(-1,2)])
def test_root_binding_refuses_before_duplicate(tree,monkeypatch,binding):
    _,_,_,fd,_,_=tree
    monkeypatch.setattr(c.os,'dup',lambda *_:pytest.fail('duplicate before identity check'))
    with pytest.raises(c.ObservationRefused,match='^root_binding$'):
        c.observe(fd,('child',),expected_root_identity=binding,deadline=101.,clock=lambda:100.)


@pytest.mark.parametrize('target,reason',[('directory','directory_device'),('file','control_type'),('metadata','control_changed')])
def test_selected_child_or_control_guard_reached(tree,monkeypatch,target,reason):
    _,parent,leaf,_,_,observe=tree
    inode=(parent if target=='directory' else leaf/'memory.max').stat().st_ino
    real=c.os.fstat;hits=[]
    def changed(fd):
        info=real(fd)
        if info.st_ino!=inode:return info
        hits.append(1)
        fields={n:getattr(info,n) for n in ('st_mode','st_dev','st_ino','st_size','st_mtime_ns')}
        if target=='metadata':
            if len(hits)==2:fields['st_mtime_ns']+=1
        else:fields['st_dev']+=1
        return SimpleNamespace(**fields)
    with monkeypatch.context() as ctx:
        ctx.setattr(c.os,'fstat',changed)
        with pytest.raises(c.ObservationRefused,match='^'+reason+'$'):observe()
    assert hits


def test_events_line_guard(tree):
    _,_,leaf,*_,observe=tree
    (leaf/'cgroup.events').write_text('populated 1\nfrozen 0')
    with pytest.raises(c.ObservationRefused,match='^events_line$'):observe()
