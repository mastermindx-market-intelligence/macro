import pytest
import mountinfo_contract as m

RAW = b'99 1 0:50 / /sys/fs/cgroup rw - cgroup2 cgroup2 rw\n'

class IntSubclass(int):
    pass

class TupleSubclass(tuple):
    def __len__(self):
        raise RuntimeError('foreign len hook invoked')

class Foreign:
    @property
    def __class__(self):
        raise RuntimeError('foreign class hook invoked')

@pytest.mark.parametrize('argument', ('raw_foreign','mount_subclass','tuple_subclass','device_subclass'))
def test_exact_types_refuse_without_user_hooks(argument):
    raw=RAW;mid=99;device=(0,50)
    if argument=='raw_foreign':raw=Foreign()
    if argument=='mount_subclass':mid=IntSubclass(99)
    if argument=='tuple_subclass':device=TupleSubclass((0,50))
    if argument=='device_subclass':device=(IntSubclass(0),50)
    with pytest.raises(m.MountInfoRefused):
        m.parse_mountinfo(raw,expected_mount_id=mid,expected_device=device)

@pytest.mark.parametrize('before,after',[(b'99 ',b'099 '),(b' 1 ',b' 01 '),(b' 0:50 ',b' 00:50 '),(b' 0:50 ',b' 0:050 ')])
def test_canonical_numeric_fields_required(before,after):
    raw=RAW.replace(before,after,1)
    with pytest.raises(m.MountInfoRefused):
        m.parse_mountinfo(raw,expected_mount_id=99,expected_device=(0,50))
