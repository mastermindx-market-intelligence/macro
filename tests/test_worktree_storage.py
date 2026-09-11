"""Exercise real temporary Git repos; fake only the diskutil volume probe."""
import concurrent.futures
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('worktree_storage', Path(__file__).resolve().parents[1] / 'scripts/worktree_storage.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)

class StorageTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve(); self.mount = self.base / 'SSD'; self.mount.mkdir()
        self.policy = dict(version=1, mount_point=str(self.mount), volume_uuid='approved', root=str(self.mount / 'workspaces'), min_free_bytes=0)
        self.info = dict(VolumeUUID='approved', MountPoint=str(self.mount), Internal=False, Writable=True, FilesystemType='apfs')
        probe = patch.object(s, 'volume_info', return_value=self.info); probe.start(); self.addCleanup(probe.stop)
    def git(self, repo, *args):
        return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.STDOUT, text=True).strip()
    def repository(self):
        r = self.base / 'repo'; r.mkdir(); self.git(r, 'init', '-b', 'main')
        self.git(r, 'config', 'user.name', 'Test'); self.git(r, 'config', 'user.email', 'test@example.invalid')
        for name in ['src/code.py', 'data/heavy.txt', 'config/sparse_worktree.json']:
            p=r/name; p.parent.mkdir(exist_ok=True)
            p.write_text(json.dumps(dict(enabled=True, exclude_dirs=['data'])) if name.endswith('.json') else 'fixture\n')
        self.git(r,'add','.'); self.git(r,'commit','-m','fixture'); return r
    def create(self, r, name='test', session='one'):
        return s.create_worktree(self.policy, r, name, session, base='HEAD', fetch=False)
    def test_valid_root(self):
        root=s.prepare_root(self.policy); self.assertEqual(root,self.mount/'workspaces')
        self.assertEqual(root.stat().st_dev,self.mount.stat().st_dev)
    def test_bad_volume_has_no_directory_effect(self):
        for change in [dict(VolumeUUID='wrong'),dict(Internal=True),dict(Writable=False),dict(MountPoint=str(self.base)),dict(FilesystemType='exfat')]:
            with self.subTest(change=change), patch.object(s,'volume_info',return_value={**self.info,**change}):
                with self.assertRaises(s.StorageError): s.prepare_root(self.policy)
                self.assertFalse(Path(self.policy['root']).exists())
    def test_missing_mount_is_never_recreated(self):
        self.mount.rmdir()
        with self.assertRaises(s.StorageError): s.prepare_root(self.policy)
        self.assertFalse(self.mount.exists())
    def test_low_space_refuses_before_mkdir(self):
        with self.assertRaisesRegex(s.StorageError,'space'): s.prepare_root({**self.policy,'min_free_bytes':2**70})
        self.assertFalse(Path(self.policy['root']).exists())
    def test_symlinks_and_parent_escape_are_rejected(self):
        outside=self.base/'outside'; outside.mkdir(); (self.mount/'link').symlink_to(outside,target_is_directory=True)
        for root in [self.mount/'link'/'work',self.mount/'..'/'escape']:
            with self.subTest(root=root), self.assertRaises(s.StorageError): s.prepare_root({**self.policy,'root':str(root)})
        self.assertEqual(list(outside.iterdir()),[])
    def test_sparse_registered_locked_idempotent(self):
        r=self.repository(); d=self.create(r)
        self.assertTrue((d/'src/code.py').exists()); self.assertFalse((d/'data/heavy.txt').exists())
        self.assertEqual(self.git(d,'status','--porcelain'),'')
        self.assertIn('locked '+s.LOCK_REASON,self.git(r,'worktree','list','--porcelain'))
        self.assertEqual(self.create(r),d); self.assertNotEqual(self.create(r,session='two'),d)
    def test_parallel_same_session_mints_once(self):
        r=self.repository()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool: result=list(pool.map(lambda _:self.create(r),range(2)))
        self.assertEqual(result[0],result[1]); self.assertEqual(self.git(r,'worktree','list','--porcelain').count('worktree '),2)
    def test_foreign_directory_is_preserved(self):
        r=self.repository(); s.prepare_root(self.policy); d,_=s.destination(self.policy,r,'test','one'); d.mkdir(parents=True)
        (d/'owned.txt').write_text('foreign')
        with self.assertRaisesRegex(s.StorageError,'unreceipted'): self.create(r)
        self.assertEqual((d/'owned.txt').read_text(),'foreign')
        self.assertEqual(self.git(r,'worktree','list','--porcelain').count('worktree '),1)
    def test_dirty_same_session_is_preserved(self):
        r=self.repository(); d=self.create(r); (d/'src/code.py').write_text('unfinished')
        self.assertEqual(self.create(r),d); self.assertEqual((d/'src/code.py').read_text(),'unfinished')
    def test_failed_fetch_has_no_branch_or_worktree_effect(self):
        r=self.repository(); self.git(r,'remote','add','origin',str(self.base/'missing.git')); before=self.git(r,'show-ref')
        with self.assertRaises(s.StorageError): s.create_worktree(self.policy,r,'test','one',base='main',fetch=True)
        self.assertEqual(self.git(r,'show-ref'),before); self.assertEqual(self.git(r,'worktree','list','--porcelain').count('worktree '),1)
    def test_storage_lock_does_not_hide_live_process_from_gc(self):
        from scripts import worktree_gc as gc
        r=self.repository(); d=self.create(r)
        wt=gc.Worktree(path=d, locked=True, lock_reason=s.LOCK_REASON)
        cfg={**gc.DEFAULT_CONFIG, 'min_age_days':0, '_storage_policy':self.policy}
        with patch.object(gc, 'worktree_storage', s, create=True):
            gc.classify(wt,r,cfg,{str(d):['active-test-owner']},{},True,r,0)
        self.assertEqual(wt.verdict,'LIVE_PROC')
    def test_other_git_lock_remains_protected(self):
        from scripts import worktree_gc as gc
        r=self.repository(); d=self.create(r)
        wt=gc.Worktree(path=d,locked=True,lock_reason='operator hold')
        with patch.object(gc,'worktree_storage',s,create=True):
            gc.classify(wt,r,{**gc.DEFAULT_CONFIG,'_storage_policy':self.policy},{},{},True,r,0)
        self.assertEqual(wt.verdict,'LOCKED')
    def test_gc_refuses_unavailable_external_volume_before_pruning(self):
        from scripts import worktree_gc as gc
        r=self.repository(); d=self.create(r)
        with patch.object(gc,'worktree_storage',s,create=True), patch.object(s,'volume_info',return_value={**self.info,'VolumeUUID':'wrong'}):
            result=gc.apply_deletions(r,[],{'_storage_policy':self.policy},[Path(self.policy['root'])])
        self.assertFalse(result['pruned']); self.assertTrue(result['errors'])
        self.assertTrue(d.exists())
    def test_gc_removes_safe_storage_locked_tree_without_force(self):
        from scripts import worktree_gc as gc
        r=self.repository(); d=self.create(r)
        wt=gc.Worktree(path=d,head=self.git(d,'rev-parse','HEAD'),locked=True,lock_reason=s.LOCK_REASON,verdict='SAFE_MERGED')
        with patch.object(gc,'worktree_storage',s,create=True), patch.object(gc,'proc_cwd_map',return_value={}), patch.object(gc,'_ledger_write'):
            result=gc.apply_deletions(r,[wt],{'_storage_policy':self.policy},[Path(self.policy['root'])])
        self.assertEqual(result['errors'],[]); self.assertEqual(result['deleted'],[str(d)]); self.assertFalse(d.exists())
    def test_gc_final_process_scan_matches_root_and_children_only(self):
        from scripts import worktree_gc as gc
        r=self.repository(); d=self.create(r)
        lsof = '\n'.join((
            'p4321','croot-owner',f'n{d}',
            'p4322','cchild-owner',f'n{d / "src"}',
            'p4323','csibling-owner',f'n{d.with_name(d.name + "-sibling")}',
        )) + '\n'
        with patch.object(gc,'_run',return_value=(0,lsof,'')):
            procs=gc.proc_cwd_map([d])
        self.assertEqual(procs,{str(d):['4321:root-owner'],str(d/'src'):['4322:child-owner']})

        wt=gc.Worktree(path=d,head=self.git(d,'rev-parse','HEAD'),locked=True,lock_reason=s.LOCK_REASON,verdict='SAFE_MERGED')
        with patch.object(gc,'worktree_storage',s), patch.object(gc,'_run',return_value=(0,f'p4321\ncfinal-owner\nn{d}\n','')), patch.object(gc,'_ledger_write'):
            result=gc.apply_deletions(r,[wt],{'_storage_policy':self.policy},[Path(self.policy['root'])])
        self.assertEqual(result['deleted'],[])
        self.assertTrue(result['errors'])
        self.assertTrue(d.exists())
        self.assertIn('locked '+s.LOCK_REASON,self.git(r,'worktree','list','--porcelain'))
    def test_gc_managed_registration_flows_from_discovery_to_apply(self):
        from scripts import worktree_gc as gc
        r=self.repository(); d=self.create(r)
        self.git(r,'update-ref','refs/remotes/origin/main','HEAD')
        registered=gc.parse_worktree_list(self.git(r,'worktree','list','--porcelain'))
        operator=self.base/'operator-checkout'; operator.mkdir()
        audit=Path(self.policy['root'])/'audit'/'receipt'; audit.mkdir(parents=True)
        control=Path(self.policy['root'])/'control'; control.mkdir(parents=True)
        registered.extend((gc.Worktree(path=operator),gc.Worktree(path=audit),gc.Worktree(path=control)))
        hosts=gc.host_checkouts(r,registered,gc.DEFAULT_CONFIG['roots'],self.policy)
        roots=gc.expand_roots(hosts,[*gc.DEFAULT_CONFIG['roots'],*map(str,s.client_roots(self.policy))])
        discovered=next(w for w in registered if w.path==d)
        self.assertNotIn(d.resolve(),hosts)
        self.assertIn(r.resolve(),hosts)
        self.assertIn(operator.resolve(),hosts)
        self.assertIn(audit.resolve(),hosts)
        self.assertIn(control.resolve(),hosts)
        self.assertTrue(any(gc._under(d,root) for root in roots))
        with patch.object(gc,'worktree_storage',s), patch.object(gc,'activity_age_days',return_value=(8,{'test':8})), patch.object(gc,'status_clean',return_value=True):
            gc.classify(discovered,r,{**gc.DEFAULT_CONFIG,'min_age_days':0,'_storage_policy':self.policy},{},{},True,r,0)
        self.assertEqual(discovered.verdict,'SAFE_MERGED')
        with patch.object(gc,'worktree_storage',s), patch.object(gc,'proc_cwd_map',return_value={}), patch.object(gc,'_ledger_write'):
            result=gc.apply_deletions(r,[discovered],{'_storage_policy':self.policy},roots,hosts=hosts)
        self.assertEqual(result['errors'],[])
        self.assertEqual(result['deleted'],[str(d)])
    def test_gc_keeps_work_that_became_dirty_after_report(self):
        from scripts import worktree_gc as gc
        r=self.repository(); d=self.create(r)
        wt=gc.Worktree(path=d,head=self.git(d,'rev-parse','HEAD'),locked=True,lock_reason=s.LOCK_REASON,verdict='SAFE_MERGED')
        (d/'src/code.py').write_text('new unfinished work')
        with patch.object(gc,'worktree_storage',s,create=True), patch.object(gc,'proc_cwd_map',return_value={}), patch.object(gc,'_ledger_write'):
            result=gc.apply_deletions(r,[wt],{'_storage_policy':self.policy},[Path(self.policy['root'])])
        self.assertEqual(result['deleted'],[]); self.assertTrue(result['errors'])
        self.assertIn('locked '+s.LOCK_REASON,self.git(r,'worktree','list','--porcelain'))
        self.assertEqual((d/'src/code.py').read_text(),'new unfinished work')
    def test_native_external_checkout_is_sparsified_and_locked(self):
        r=self.repository(); root=s.prepare_root(self.policy); d=root/'codex'/'native'; d.parent.mkdir()
        self.git(r,'worktree','add','--detach',str(d),'HEAD')
        self.assertTrue((d/'data/heavy.txt').exists())
        self.assertTrue(s.protect_worktree(self.policy,d))
        self.assertFalse((d/'data/heavy.txt').exists())
        self.assertIn('locked '+s.LOCK_REASON,self.git(r,'worktree','list','--porcelain'))
    def test_existing_primary_checkout_is_unchanged_at_startup(self):
        r=self.repository()
        self.assertFalse(s.protect_worktree(self.policy,r))
        self.assertTrue((r/'data/heavy.txt').exists())
    def test_audit_checkout_is_not_a_client_session(self):
        from scripts import worktree_sparse as sparse, worktree_storage as storage
        r=self.repository(); root=s.prepare_root(self.policy); d=root/'audit'/'native'; d.parent.mkdir()
        self.git(r,'worktree','add','--detach',str(d),'HEAD')
        with patch.object(storage,'load_policy',return_value=self.policy), patch.object(storage,'volume_info',return_value=self.info):
            self.assertFalse(sparse.is_session_worktree(d))
        self.assertFalse(s.protect_worktree(self.policy,d))
        self.assertTrue((d/'data/heavy.txt').exists())
    def test_codex_auto_entry_point_protects_external_checkout(self):
        from scripts import worktree_sparse as sparse, worktree_storage as storage
        r=self.repository(); root=s.prepare_root(self.policy); d=root/'codex'/'native'; d.parent.mkdir()
        self.git(r,'worktree','add','--detach',str(d),'HEAD')
        with patch.object(storage,'load_policy',return_value=self.policy), patch.object(storage,'volume_info',return_value=self.info):
            self.assertEqual(sparse.auto_profile(d),0)
        self.assertFalse((d/'data/heavy.txt').exists())
        self.assertIn('locked '+s.LOCK_REASON,self.git(r,'worktree','list','--porcelain'))
    def test_gc_relocks_missing_registration_after_remove_failure_or_exception(self):
        from scripts import worktree_gc as gc
        r=self.repository()
        for raises in (False, True):
            with self.subTest(raises=raises):
                d=self.create(r,session=str(raises))
                wt=gc.Worktree(path=d,head=self.git(d,'rev-parse','HEAD'),locked=True,lock_reason=s.LOCK_REASON,verdict='SAFE_MERGED')
                original=gc._git
                def disappear(repo,*args,**kwargs):
                    if args[:2] == ('worktree','remove'):
                        d.rename(d.with_name(d.name+'-disconnected'))
                        if raises:
                            raise OSError('simulated disconnect')
                        return 1,'','simulated disconnect'
                    return original(repo,*args,**kwargs)
                with patch.object(gc,'worktree_storage',s), patch.object(gc,'proc_cwd_map',return_value={}), patch.object(gc,'_ledger_write'), patch.object(gc,'_git',side_effect=disappear):
                    result=gc.apply_deletions(r,[wt],{'_storage_policy':self.policy},[Path(self.policy['root'])])
                self.assertEqual(result['deleted'],[]); self.assertTrue(result['errors'])
                record=next(w for w in gc.parse_worktree_list(self.git(r,'worktree','list','--porcelain')) if w.path==d)
                self.assertTrue(record.locked); self.assertEqual(record.lock_reason,s.LOCK_REASON)


class FilesystemMetadataTests(unittest.TestCase):
    """Admission uses observed diskutil fields, before any destination allocation."""
    setUp = StorageTests.setUp

    HFS = dict(FilesystemType='hfs',
               FilesystemName='Case-sensitive Journaled HFS+',
               JournalOffset=30523392, JournalSize=83886080)

    def filesystems(self):
        return ({'FilesystemType': 'apfs'},
                {'FilesystemType': 'apfs', 'FilesystemName': 'APFS'},
                {'FilesystemType': 'apfs', 'FilesystemName': 'Case-sensitive APFS'},
                self.HFS,
                {**self.HFS, 'FilesystemName': 'Journaled HFS+'})

    def test_observed_m1_journaled_hfs_is_admitted(self):
        self.info.update(self.HFS, SolidState=True, GlobalPermissionsEnabled=False)
        try:
            root = s.prepare_root(self.policy)
        except s.StorageError as exc:
            self.fail(f'Observed journaled HFS+ was refused before allocation: {exc}')
        self.assertEqual(root, self.mount / 'workspaces')
        self.assertTrue(root.is_dir())
        self.assertEqual(root.stat().st_dev, self.mount.stat().st_dev)

    def test_supported_filesystems_allocate_on_the_verified_device(self):
        for i, metadata in enumerate(self.filesystems()):
            with self.subTest(metadata=metadata), patch.object(s, 'volume_info', return_value={**self.info, **metadata}):
                root = self.mount / f'accepted-{i}'
                self.assertEqual(s.prepare_root({**self.policy, 'root': str(root)}), root)
                self.assertEqual(root.stat().st_dev, self.mount.stat().st_dev)

    def test_incomplete_or_contradictory_filesystem_metadata_has_no_effect(self):
        invalid = [
            {}, {'FilesystemType': None}, {'FilesystemType': []},
            {'FilesystemType': 'exfat'}, {'FilesystemType': 'ntfs'},
            {'FilesystemType': 'hfs'},
            {**self.HFS, 'FilesystemType': 'apfs'},
            {**self.HFS, 'FilesystemName': 'APFS'},
            {**self.HFS, 'FilesystemName': 'HFS+'},
            {**self.HFS, 'FilesystemName': 'Case-sensitive HFS+'},
            {**self.HFS, 'FilesystemName': 'unknown Journaled HFS+'},
            {**self.HFS, 'FilesystemName': None},
            {**self.HFS, 'FilesystemName': []},
            {**self.HFS, 'Journaled': False},
            {**self.HFS, 'Journaled': 1},
            {'FilesystemType': 'apfs', 'FilesystemName': 'unknown'},
            {'FilesystemType': 'apfs', 'FilesystemName': 'Journaled HFS+'},
            {'FilesystemType': 'apfs', 'Journaled': True},
            {'FilesystemType': 'apfs', 'JournalOffset': 1},
            {'FilesystemType': 'apfs', 'JournalSize': 1},
        ]
        for key in ('FilesystemName', 'JournalOffset', 'JournalSize'):
            invalid.append({k: v for k, v in self.HFS.items() if k != key})
        for key in ('JournalOffset', 'JournalSize'):
            for value in (None, False, True, 0, -1, '83886080', 1.5):
                invalid.append({**self.HFS, key: value})
        identity = {k: v for k, v in self.info.items() if k != 'FilesystemType'}
        for metadata in invalid:
            with self.subTest(metadata=metadata), patch.object(s, 'volume_info', return_value={**identity, **metadata}):
                with self.assertRaises(s.StorageError):
                    s.prepare_root(self.policy)
                self.assertEqual(list(self.mount.iterdir()), [])

    def test_explicit_true_journal_flag_is_consistent(self):
        self.info.update(self.HFS, Journaled=True)
        self.assertEqual(s.prepare_root(self.policy), self.mount / 'workspaces')

    def test_identity_and_space_guards_apply_to_each_supported_filesystem(self):
        for metadata in self.filesystems():
            for change in ({'VolumeUUID': 'wrong'}, {'Internal': True},
                           {'Writable': False}, {'MountPoint': str(self.base)}):
                with self.subTest(metadata=metadata, change=change), patch.object(s, 'volume_info', return_value={**self.info, **metadata, **change}):
                    with self.assertRaises(s.StorageError):
                        s.prepare_root(self.policy)
                    self.assertEqual(list(self.mount.iterdir()), [])
            with self.subTest(metadata=metadata, guard='space'), patch.object(s, 'volume_info', return_value={**self.info, **metadata}):
                with self.assertRaisesRegex(s.StorageError, 'space'):
                    s.prepare_root({**self.policy, 'min_free_bytes': 2**70})
                self.assertEqual(list(self.mount.iterdir()), [])

    def test_containment_and_symlinks_apply_to_each_supported_filesystem(self):
        outside = self.base / 'outside'; outside.mkdir()
        (self.mount / 'link').symlink_to(outside, target_is_directory=True)
        for metadata in self.filesystems():
            with patch.object(s, 'volume_info', return_value={**self.info, **metadata}):
                for root in (outside / 'work', self.mount, self.mount / '..' / 'escape',
                             self.mount / 'link' / 'work'):
                    with self.subTest(metadata=metadata, root=root), self.assertRaises(s.StorageError):
                        s.prepare_root({**self.policy, 'root': str(root)})
                with self.subTest(metadata=metadata, target='outside'), self.assertRaises(s.StorageError):
                    s.check_storage(self.policy, outside / 'work')
                self.assertFalse(Path(self.policy['root']).exists())
                self.assertEqual(list(outside.iterdir()), [])

    def test_other_device_refuses_before_mkdir_for_each_supported_filesystem(self):
        import os
        ancestor = self.mount / 'foreign'; ancestor.mkdir()
        real_stat = Path.stat
        def different_device(path, *args, **kwargs):
            result = real_stat(path, *args, **kwargs)
            if path == ancestor:
                fields = list(result); fields[2] += 1
                return os.stat_result(fields)
            return result
        for metadata in self.filesystems():
            with self.subTest(metadata=metadata), patch.object(s, 'volume_info', return_value={**self.info, **metadata}), patch.object(Path, 'stat', different_device):
                with self.assertRaisesRegex(s.StorageError, 'another filesystem'):
                    s.prepare_root({**self.policy, 'root': str(ancestor / 'work')})
            self.assertEqual(list(ancestor.iterdir()), [])


class JournaledHFSStorageTests(StorageTests):
    """Run existing real-Git and lifecycle guards under the M1 volume metadata.

    The disposable files reside on the test runner's external SSD. These tests
    cover helper branching with a fake volume probe, not native HFS mechanics.
    """
    def setUp(self):
        super().setUp()
        self.info.update(FilesystemMetadataTests.HFS,
                         SolidState=True, GlobalPermissionsEnabled=False)


class ImmutableLocalTests(unittest.TestCase):
    """Real disposable Git fixtures; the runner must retain them on the SSD."""
    setUp = StorageTests.setUp
    git = StorageTests.git

    def repo(self, *, sparse=True):
        import uuid
        r = self.base / ('repo-' + uuid.uuid4().hex)
        r.mkdir()
        self.git(r, 'init', '-b', 'main')
        self.git(r, 'config', 'user.name', 'Test')
        self.git(r, 'config', 'user.email', 'test@example.invalid')
        self.git(r, 'config', 'extensions.worktreeConfig', 'true')
        for name, content in [('src/code.py', 'selected\n'), ('data/heavy.txt', 'excluded\n')]:
            p = r / name; p.parent.mkdir(exist_ok=True); p.write_text(content)
        if sparse:
            (r / 'config').mkdir()
            (r / 'config/sparse_worktree.json').write_text(json.dumps(dict(enabled=True, exclude_dirs=['data'])))
        self.git(r, 'add', '.'); self.git(r, 'commit', '-m', 'fixture')
        return r

    def create_local(self, r, *, session='actual-fixture-session', name='qualification', commit=None):
        return s.create_immutable_local(self.policy, r, name, session,
                                        commit or self.git(r, 'rev-parse', 'HEAD'))

    def driver(self, r, *, worktree=False):
        import shlex
        import sys
        marker = self.base / 'FILTER_EXECUTED'
        script = self.base / 'filter-sentinel.py'
        script.write_text('import pathlib,sys\npathlib.Path(' + repr(str(marker)) +
                          ').write_text("executed")\nsys.stdout.buffer.write(sys.stdin.buffer.read())\n')
        command = shlex.quote(sys.executable) + ' ' + shlex.quote(str(script))
        scope = ['--worktree'] if worktree else []
        self.git(r, 'config', *scope, 'filter.sentinel.clean', command)
        self.git(r, 'config', *scope, 'filter.sentinel.smudge', command)
        return marker

    def before(self, r):
        import hashlib
        return dict(head=self.git(r, 'rev-parse', 'HEAD'),
                    refs=self.git(r, 'for-each-ref', '--format=%(refname) %(objectname)'),
                    index=hashlib.sha256((r / '.git/index').read_bytes()).hexdigest(),
                    config=(r / '.git/config').read_bytes())

    def assert_before_status_refusal(self, r, d, message):
        original = s._immutable_git
        def observed(repo, *args, **kwargs):
            if Path(repo) == d and args[0] == 'status':
                self.fail('reuse reached status before refusing its changed input')
            return original(repo, *args, **kwargs)
        with patch.object(s, '_immutable_git', side_effect=observed):
            with self.assertRaisesRegex(s.StorageError, message):
                self.create_local(r)

    def test_configured_unused_driver_and_exact_detached_sparse_reuse(self):
        r = self.repo(); marker = self.driver(r); before = self.before(r)
        d = self.create_local(r)
        self.assertEqual(self.git(d, 'rev-parse', 'HEAD'), before['head'])
        p = subprocess.run(['git', '-C', str(d), 'symbolic-ref', '-q', 'HEAD'], capture_output=True)
        self.assertEqual(p.returncode, 1)
        self.assertTrue((d / 'src/code.py').exists()); self.assertFalse((d / 'data/heavy.txt').exists())
        self.assertEqual(self.git(d, 'ls-files', '-v', '--', 'data/heavy.txt'), 'S data/heavy.txt')
        self.assertEqual(self.git(d, 'ls-files', '-v', '--', 'src/code.py'), 'H src/code.py')
        self.assertEqual(self.create_local(r), d)
        self.assertEqual(self.before(r), before)
        self.assertFalse(marker.exists())

    def test_staged_unexpected_filter_path_refused_before_status(self):
        r = self.repo(sparse=False)
        (r / '.gitattributes').write_text('*.bin filter=sentinel\n')
        self.git(r, 'add', '.gitattributes'); self.git(r, 'commit', '-m', 'unused filter pattern')
        marker = self.driver(r); d = self.create_local(r)
        oid = self.git(r, 'rev-parse', 'HEAD:src/code.py')
        self.git(d, 'update-index', '--add', '--cacheinfo', '100644', oid, 'new.bin')
        content = b'modified\n'
        self.assertEqual(len(content), len((d / 'src/code.py').read_bytes()))
        (d / 'new.bin').write_bytes(content)
        index = Path(self.git(d, 'rev-parse', '--absolute-git-dir')) / 'index'
        prepared_index = index.read_bytes()
        self.assertFalse(marker.exists())
        self.assert_before_status_refusal(r, d, 'index does not match immutable tree')
        self.assertFalse(marker.exists())
        self.assertEqual(index.read_bytes(), prepared_index)
        self.assertEqual((d / 'new.bin').read_bytes(), content)

    def assert_hidden_required_file_refused(self, flag):
        r = self.repo(sparse=False); d = self.create_local(r)
        self.git(d, 'update-index', flag, 'src/code.py')
        content = b'modified\n'; (d / 'src/code.py').write_bytes(content)
        index = Path(self.git(d, 'rev-parse', '--absolute-git-dir')) / 'index'
        prepared_index = index.read_bytes()
        prepared_flags = self.git(d, 'ls-files', '-v', '--', 'src/code.py')
        self.assert_before_status_refusal(r, d, 'required materialized path has index flags')
        self.assertEqual(index.read_bytes(), prepared_index)
        self.assertEqual(self.git(d, 'ls-files', '-v', '--', 'src/code.py'), prepared_flags)
        self.assertEqual((d / 'src/code.py').read_bytes(), content)

    def test_modified_required_file_hidden_by_skip_worktree_is_refused(self):
        self.assert_hidden_required_file_refused('--skip-worktree')

    def test_modified_required_file_hidden_by_assume_unchanged_is_refused(self):
        self.assert_hidden_required_file_refused('--assume-unchanged')

    def test_full_checkout_and_reuse_preserve_source_state(self):
        r = self.repo(sparse=False); before = self.before(r)
        d = self.create_local(r)
        self.assertTrue((d / 'data/heavy.txt').exists())
        self.assertEqual(self.create_local(r), d); self.assertEqual(self.before(r), before)

    def test_selected_filter_is_refused_without_root_allocation(self):
        r = self.repo()
        (r / '.gitattributes').write_text('*.py filter=sentinel\n')
        self.git(r, 'add', '.gitattributes'); self.git(r, 'commit', '-m', 'attributes')
        marker = self.driver(r)
        with self.assertRaisesRegex(s.StorageError, 'selects a filter'): self.create_local(r)
        self.assertFalse(Path(self.policy['root']).exists()); self.assertFalse(marker.exists())

    def test_inherited_git_config_cannot_mask_a_selected_filter(self):
        r = self.repo()
        (r / '.gitattributes').write_text('*.py filter=sentinel\n')
        self.git(r, 'add', '.gitattributes'); self.git(r, 'commit', '-m', 'attributes')
        marker = self.driver(r)
        benign = self.base / 'benign.config'; benign.write_text('[extensions]\nworktreeConfig = true\n')
        with patch.dict(s.os.environ, {'GIT_CONFIG': str(benign)}):
            with self.assertRaisesRegex(s.StorageError, 'selects a filter'): self.create_local(r)
        self.assertFalse(marker.exists()); self.assertFalse(Path(self.policy['root']).exists())

    def test_destination_only_filter_and_attributes_refused_before_status(self):
        r = self.repo(); d = self.create_local(r); marker = self.driver(d, worktree=True)
        (d / '.gitattributes').write_text('*.py filter=sentinel\n')
        (d / 'src/code.py').touch()
        self.assert_before_status_refusal(r, d, 'selects a filter')
        self.assertFalse(marker.exists())

    def test_destination_only_attributes_file_refused_before_status(self):
        r = self.repo(); d = self.create_local(r); marker = self.driver(d, worktree=True)
        attrs = self.base / 'destination.attributes'; attrs.write_text('*.py filter=sentinel\n')
        self.git(d, 'config', '--worktree', 'core.attributesFile', str(attrs))
        self.assert_before_status_refusal(r, d, 'selects a filter')
        self.assertFalse(marker.exists())

    def test_changed_untracked_attributes_refused_even_without_filter(self):
        r = self.repo(); d = self.create_local(r)
        (d / '.gitattributes').write_text('*.py text\n')
        self.assert_before_status_refusal(r, d, 'drift')

    def test_clean_sparse_selection_drift_refused_without_repair(self):
        r = self.repo(); d = self.create_local(r)
        self.git(d, 'sparse-checkout', 'set', '--cone', '--', 'src')
        self.assertEqual(self.git(d, 'status', '--porcelain'), '')
        before = (Path(self.git(d, 'rev-parse', '--absolute-git-dir')) / 'info/sparse-checkout').read_bytes()
        self.assert_before_status_refusal(r, d, 'sparse selection changed|required materialized path')
        self.assertEqual((Path(self.git(d, 'rev-parse', '--absolute-git-dir')) / 'info/sparse-checkout').read_bytes(), before)

    def test_sparse_pattern_bytes_are_receipted(self):
        r = self.repo(); d = self.create_local(r)
        patterns = Path(self.git(d, 'rev-parse', '--absolute-git-dir')) / 'info/sparse-checkout'
        patterns.write_bytes(patterns.read_bytes() + b'\n')
        self.assert_before_status_refusal(r, d, 'drift')

    def test_excluded_tracked_path_restoration_refused_before_status(self):
        r = self.repo(); marker = self.driver(r); d = self.create_local(r)
        (d / 'data').mkdir(exist_ok=True)
        (d / 'data/heavy.txt').write_text('unexpected tracked file')
        (d / 'data/.gitattributes').write_text('*.txt filter=sentinel\n')
        self.assert_before_status_refusal(r, d, 'excluded tracked path')
        self.assertFalse(marker.exists())

    def test_executable_effect_hooks_are_not_run(self):
        for hook in ('post-checkout', 'post-index-change', 'reference-transaction'):
            with self.subTest(hook=hook):
                r = self.repo()
                marker = r.parent / ('HOOK_EXECUTED-' + hook)
                p = r / '.git/hooks' / hook
                p.parent.mkdir(exist_ok=True)
                p.write_text('#!/bin/sh\ntouch ' + str(marker) + '\n')
                p.chmod(0o700)
                with self.assertRaisesRegex(s.StorageError, 'executable checkout'):
                    self.create_local(r)
                self.assertFalse(marker.exists())
                self.assertFalse(Path(self.policy['root']).exists())

    def test_missing_required_path_hidden_by_index_flag_is_refused(self):
        r = self.repo(); d = self.create_local(r)
        self.git(d, 'update-index', '--skip-worktree', 'src/code.py')
        (d / 'src/code.py').unlink()
        self.assertEqual(self.git(d, 'status', '--porcelain'), '')
        self.assert_before_status_refusal(r, d, 'required materialized path')

    def test_dirty_exact_session_is_preserved_and_refused(self):
        r = self.repo(); d = self.create_local(r)
        (d / 'src/code.py').write_text('unfinished')
        with self.assertRaisesRegex(s.StorageError, 'dirty'): self.create_local(r)
        self.assertEqual((d / 'src/code.py').read_text(), 'unfinished')

    def test_raw_unsupported_names_refused_before_effects(self):
        import os
        cases = [b'bad\rdir/code', b'bad\ndir/code', b'bad\tdir/code',
                 b'bad /code', b'bad\\dir/code']
        for name in cases:
            with self.subTest(name=name):
                r = self.repo()
                path = os.fsencode(r) + b'/' + name
                os.makedirs(os.path.dirname(path))
                with open(path, 'wb') as out: out.write(b'fixture')
                self.git(r, 'add', '.'); self.git(r, 'commit', '-m', 'unsupported path')
                with self.assertRaisesRegex(s.StorageError, 'pathname'): self.create_local(r)
                self.assertFalse(Path(self.policy['root']).exists())

    def test_git_tree_nonutf8_name_refused_before_materialization(self):
        r = self.repo()
        blob = self.git(r, 'rev-parse', 'HEAD:src/code.py')
        raw_tree = b'100644 bad-' + bytes([255, 0]) + bytes.fromhex(blob)
        made = subprocess.run(['git', '-C', str(r), 'hash-object', '-t', 'tree', '-w', '--stdin'],
                              input=raw_tree, capture_output=True, check=True)
        tree = made.stdout.decode('ascii').strip()
        commit = self.git(r, 'commit-tree', tree, '-m', 'raw pathname fixture')
        with self.assertRaisesRegex(s.StorageError, 'non-UTF8 pathname'):
            self.create_local(r, commit=commit)
        self.assertFalse(Path(self.policy['root']).exists())

    def test_utf8_and_interior_space_paths_are_preserved(self):
        r = self.repo()
        p = r / 'café research' / 'code.txt'; p.parent.mkdir(); p.write_text('utf8')
        self.git(r, 'add', '.'); self.git(r, 'commit', '-m', 'supported path')
        d = self.create_local(r)
        self.assertEqual((d / 'café research/code.txt').read_text(), 'utf8')
        self.assertEqual(self.create_local(r), d)

    def test_missing_commit_tree_or_selected_blob_never_fetches(self):
        for kind in ('commit', 'tree', 'blob'):
            with self.subTest(kind=kind):
                r = self.repo()
                commit = self.git(r, 'rev-parse', 'HEAD')
                oid = ('f' * 40 if kind == 'commit' else
                       self.git(r, 'rev-parse', 'HEAD^{tree}' if kind == 'tree' else 'HEAD:src/code.py'))
                if kind != 'commit':
                    (r / '.git/objects' / oid[:2] / oid[2:]).unlink()
                self.git(r, 'config', 'extensions.partialClone', 'origin')
                self.git(r, 'config', 'remote.origin.promisor', 'true')
                transport = r.parent / ('transport-' + kind)
                marker = r.parent / ('TRANSPORT_EXECUTED-' + kind)
                transport.write_text('#!/bin/sh\ntouch ' + str(marker) + '\nexit 1\n')
                transport.chmod(0o700)
                self.git(r, 'config', 'remote.origin.url', 'ext::' + str(transport))
                self.git(r, 'config', 'protocol.ext.allow', 'always')
                with self.assertRaises(s.StorageError):
                    self.create_local(r, commit=oid if kind == 'commit' else commit)
                self.assertFalse(marker.exists())
                self.assertFalse(Path(self.policy['root']).exists())

    def test_missing_excluded_blob_can_remain_unmaterialized(self):
        r = self.repo(); oid = self.git(r, 'rev-parse', 'HEAD:data/heavy.txt')
        (r / '.git/objects' / oid[:2] / oid[2:]).unlink()
        d = self.create_local(r)
        self.assertTrue((d / 'src/code.py').exists()); self.assertFalse((d / 'data/heavy.txt').exists())

    def test_partial_creation_retains_intent_and_any_registration(self):
        for failure in ('add', 'read-tree', 'complete'):
            with self.subTest(failure=failure):
                r = self.repo(); name = 'partial-' + failure
                original = s._immutable_git
                def observed(repo, *args, **kwargs):
                    if (failure == 'add' and args[:2] == ('worktree', 'add')) or (failure == 'read-tree' and args[0] == 'read-tree'):
                        raise s.StorageError('injected fixture failure')
                    return original(repo, *args, **kwargs)
                replacement = patch.object(s.os, 'replace', side_effect=OSError('injected receipt replacement')) if failure == 'complete' else patch.object(s, '_immutable_git', side_effect=observed)
                with replacement, self.assertRaisesRegex(s.StorageError, 'creation incomplete'):
                    self.create_local(r, name=name)
                receipts = list((Path(self.policy['root']) / '.storage-receipts').glob('*.json'))
                matches = [json.loads(p.read_text()) for p in receipts if name in json.loads(p.read_text())['path']]
                self.assertEqual(len(matches), 1); self.assertEqual(matches[0]['state'], 'PREPARING')
                d = Path(matches[0]['path'])
                if failure != 'add':
                    self.assertTrue(d.exists())
                    self.assertIn('locked ' + s.LOCK_REASON, self.git(r, 'worktree', 'list', '--porcelain'))
                with self.assertRaises(s.StorageError): self.create_local(r, name=name)
                self.assertEqual(matches[0]['state'], 'PREPARING')

    def test_intent_and_complete_settle_receipt_directory(self):
        r = self.repo(); events = []; git_original = s._immutable_git; sync_original = s._immutable_fsync_directory
        def run(repo, *args, **kwargs):
            if args[:2] == ('worktree', 'add'): events.append('add')
            return git_original(repo, *args, **kwargs)
        def sync(path):
            events.append('sync'); return sync_original(path)
        with patch.object(s, '_immutable_git', side_effect=run), patch.object(s, '_immutable_fsync_directory', side_effect=sync):
            self.create_local(r)
        self.assertEqual(events[0], 'sync')
        self.assertLess(events.index('sync'), events.index('add'))
        self.assertEqual(events[-1], 'sync'); self.assertGreaterEqual(events.count('sync'), 3)

    def test_same_session_concurrency_mints_once(self):
        r = self.repo()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            result = list(pool.map(lambda _: self.create_local(r), range(2)))
        self.assertEqual(result[0], result[1])
        self.assertEqual(self.git(r, 'worktree', 'list', '--porcelain').count('worktree '), 2)

    def test_invalid_cli_inputs_do_not_reach_creation(self):
        import io
        import sys
        good = dict(cwd='/existing/repo', name='qualification', session_id='actual-session', commit='a' * 40)
        for bad in ({**good, 'commit': None}, {**good, 'session_id': ''},
                    {k: v for k, v in good.items() if k != 'session_id'}, {**good, 'fetch': False}):
            with self.subTest(bad=bad), patch.object(sys, 'argv', ['storage', 'create-immutable-local']), \
                 patch.object(sys, 'stdin', io.StringIO(json.dumps(bad))), patch.object(sys, 'stderr', io.StringIO()), \
                 patch.object(s, 'load_policy', return_value={}), patch.object(s, 'create_immutable_local') as create:
                self.assertEqual(s.main(), 1); create.assert_not_called()

    def test_nonregular_committed_attributes_refused_before_effects(self):
        for kind in ('symlink', 'directory'):
            with self.subTest(kind=kind):
                r = self.repo()
                p = r / '.gitattributes'
                if kind == 'symlink':
                    target = r.parent / 'attribute-target'
                    target.write_text('*.py filter=sentinel' + chr(10))
                    p.symlink_to(target)
                else:
                    p.mkdir()
                    (p / 'invalid').write_text('not an attributes file')
                self.git(r, 'add', '.')
                self.git(r, 'commit', '-m', 'nonregular attributes')
                with self.assertRaisesRegex(s.StorageError, 'not a regular committed file'):
                    self.create_local(r)
                self.assertFalse(Path(self.policy['root']).exists())

    def test_hermetic_binary_child_removes_git_config_and_preserves_cr(self):
        env = dict(GIT_CONFIG='/mask', GIT_DIR='/foreign', GIT_INDEX_FILE='/foreign-index',
                   GIT_CONFIG_COUNT='1', GIT_CONFIG_KEY_0='core.hooksPath',
                   GIT_CONFIG_VALUE_0='/foreign-hooks', GIT_ATTR_SOURCE='foreign',
                   GIT_ALLOW_PROTOCOL='https')
        result = subprocess.CompletedProcess([], 0, b'bad\rpath\0', b'')
        with patch.dict(s.os.environ, env), patch.object(s.subprocess, 'run', return_value=result) as run:
            self.assertEqual(s._immutable_git(Path('/existing/repo'), 'ls-tree', '-z', 'a' * 40), b'bad\rpath\0')
        kw = run.call_args.kwargs
        for key in env:
            if key != 'GIT_ALLOW_PROTOCOL': self.assertNotIn(key, kw['env'])
        self.assertEqual(kw['env']['GIT_ALLOW_PROTOCOL'], '')
        self.assertEqual(kw['env']['GIT_NO_LAZY_FETCH'], '1')
        self.assertNotIn('text', kw); self.assertEqual(kw['timeout'], 20)



class F4ManagedAutoProfileTests(unittest.TestCase):
    """A startup must not sparsify away local work, even when index flags hide it."""

    def setUp(self):
        from scripts import worktree_sparse, worktree_storage
        self.ws = worktree_sparse
        self.storage = worktree_storage
        temporary = tempfile.TemporaryDirectory(prefix="f4-regression-")
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.mount = self.base / "SSD"
        self.mount.mkdir()
        self.policy = dict(version=1, mount_point=str(self.mount), volume_uuid="f4-fixture",
                           root=str(self.mount / "workspaces"), min_free_bytes=0)
        self.info = dict(VolumeUUID="f4-fixture", MountPoint=str(self.mount), Internal=False,
                         Writable=True, FilesystemType="apfs")

    def git(self, root, *args, input_bytes=None, allow_missing=False):
        result = subprocess.run(["git", "-C", str(root), *args], input=input_bytes,
                                capture_output=True, timeout=15)
        if not allow_missing:
            self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        return result.stdout

    def full_checkout(self, name="native", portable=False):
        repo = self.base / (name + "-repo")
        repo.mkdir()
        self.git(repo, "init", "-b", "main")
        self.git(repo, "config", "user.name", "F4 Fixture")
        self.git(repo, "config", "user.email", "f4@example.invalid")
        for rel, data in {"src/code.py": "original source\n", "data/heavy.txt": "original data\n",
                          "config/sparse_worktree.json": json.dumps(dict(enabled=True, exclude_dirs=["data"]))}.items():
            file = repo / rel
            file.parent.mkdir(exist_ok=True)
            file.write_text(data)
        self.git(repo, "add", ".")
        self.git(repo, "commit", "-m", "fixture")
        destination = (self.base / ".claude/worktrees" / name if portable
                       else Path(self.policy["root"]) / "codex" / name)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.git(repo, "worktree", "add", "--detach", str(destination), "HEAD")
        return repo, destination

    def snapshot(self, root):
        index = Path(self.git(root, "rev-parse", "--git-path", "index").decode().strip())
        if not index.is_absolute():
            index = root / index
        sparse = Path(self.git(root, "rev-parse", "--git-path", "info/sparse-checkout").decode().strip())
        if not sparse.is_absolute():
            sparse = root / sparse
        return {
            "files": {str(f.relative_to(root)): f.read_bytes() for f in root.rglob("*") if f.is_file()},
            "index": index.read_bytes(),
            "sparse_patterns": sparse.read_bytes() if sparse.exists() else None,
            "sparse_enabled": self.git(root, "config", "--get", "core.sparseCheckout", allow_missing=True),
        }

    def auto(self, root, policy=True):
        with patch.object(self.storage, "load_policy", return_value=self.policy if policy else None), \
             patch.object(self.storage, "volume_info", return_value=self.info), \
             patch.object(self.ws, "apply_profile", wraps=self.ws.apply_profile) as apply, \
             patch.object(self.ws, "refuse_if_locked", wraps=self.ws.refuse_if_locked) as healing:
            rc = self.ws.auto_profile(root)
        return rc, apply.call_count, healing.call_count

    def assert_preserved(self, repo, root, before, result, expected_rc=0):
        self.assertEqual(result[0], expected_rc)
        self.assertEqual(self.snapshot(root), before)
        self.assertEqual(result[1:], (0, 0), "startup entered sparse application/lock healing")
        self.assertIn("locked " + self.storage.LOCK_REASON,
                      self.git(repo, "worktree", "list", "--porcelain").decode())

    def test_f4_dirty_full_preserves_checkout(self):
        for kind in ("unstaged", "staged", "untracked"):
            with self.subTest(kind=kind):
                repo, root = self.full_checkout(kind)
                target = root / ("data/untracked.txt" if kind == "untracked" else "data/heavy.txt")
                target.write_text("unfinished local work\n")
                if kind == "staged":
                    self.git(root, "add", "data/heavy.txt")
                before = self.snapshot(root)
                self.assert_preserved(repo, root, before, self.auto(root))

    def test_f4_hidden_index_edits_are_preserved(self):
        for flag in ("--assume-unchanged", "--skip-worktree"):
            with self.subTest(flag=flag):
                repo, root = self.full_checkout(flag[2:])
                self.git(root, "update-index", flag, "data/heavy.txt")
                (root / "data/heavy.txt").write_text("hidden unfinished work\n")
                before = self.snapshot(root)
                self.assert_preserved(repo, root, before, self.auto(root))

    def test_f4_unmerged_index_is_preserved(self):
        repo, root = self.full_checkout()
        blob = self.git(root, "rev-parse", "HEAD:src/code.py").decode().strip()
        entries = "0 " + "0" * 40 + "\tsrc/code.py\n"
        entries += "".join(f"100644 {blob} {stage}\tsrc/code.py\n" for stage in (1, 2, 3))
        self.git(root, "update-index", "--index-info", input_bytes=entries.encode())
        before = self.snapshot(root)
        self.assert_preserved(repo, root, before, self.auto(root))

    def test_f4_unknown_index_or_status_refuses_without_mutation(self):
        for failed_read in ("ls-files", "status"):
            with self.subTest(failed_read=failed_read):
                repo, root = self.full_checkout(failed_read)
                before = self.snapshot(root)
                original = self.ws._git_bytes
                def read(path, *args, **kwargs):
                    return None if failed_read in args else original(path, *args, **kwargs)
                with patch.object(self.ws, "_git_bytes", side_effect=read):
                    result = self.auto(root)
                self.assert_preserved(repo, root, before, result, expected_rc=1)

    def test_f4_disabled_and_existing_sparse_are_protected_without_reapplication(self):
        for state in ("disabled", "already-sparse"):
            with self.subTest(state=state):
                repo, root = self.full_checkout(state)
                if state == "disabled":
                    (root / "config/sparse_worktree.json").write_text(json.dumps(dict(enabled=False, exclude_dirs=["data"])))
                else:
                    self.git(root, "sparse-checkout", "set", "--cone", "src", "data")
                before = self.snapshot(root)
                original = self.ws._git_bytes
                def read(path, *args, **kwargs):
                    if "ls-files" in args or "status" in args:
                        raise AssertionError("optional early exit probed index/status")
                    return original(path, *args, **kwargs)
                with patch.object(self.ws, "_git_bytes", side_effect=read):
                    result = self.auto(root)
                self.assert_preserved(repo, root, before, result)

    def test_f4_clean_managed_full_checkout_still_applies_profile(self):
        repo, root = self.full_checkout()
        rc, applies, _ = self.auto(root)
        self.assertEqual((rc, applies), (0, 1))
        self.assertFalse((root / "data/heavy.txt").exists())
        self.assertTrue((root / "src/code.py").exists())
        self.assertIn("locked " + self.storage.LOCK_REASON,
                      self.git(repo, "worktree", "list", "--porcelain").decode())

    def test_f4_portable_checkout_retains_existing_profile_behavior(self):
        _, root = self.full_checkout(portable=True)
        rc, applies, _ = self.auto(root, policy=False)
        self.assertEqual((rc, applies), (0, 1))
        self.assertFalse((root / "data/heavy.txt").exists())

    def test_f4_ssd_hook_success_and_failure_never_enter_portable_cleanup(self):
        import io
        repo, root = self.full_checkout()
        hook_path = Path(__file__).resolve().parents[1] / ".claude/hooks/worktree_create_sparse.py"
        hook_spec = importlib.util.spec_from_file_location("f4_hook", hook_path)
        hook = importlib.util.module_from_spec(hook_spec)
        hook_spec.loader.exec_module(hook)
        before = self.snapshot(root)
        for fail in (False, True):
            with self.subTest(fail=fail):
                output = io.StringIO()
                payload = json.dumps(dict(name="f4-hook", cwd=str(repo), session_id="f4-fixture"))
                with patch.object(hook.sys, "stdin", io.StringIO(payload)), \
                     patch.object(hook.sys, "stdout", output), \
                     patch.object(self.storage, "load_policy", return_value=self.policy), \
                     patch.object(self.storage, "create_worktree", return_value=root,
                                  side_effect=self.storage.StorageError("fixture refusal") if fail else None), \
                     patch.object(hook, "git", side_effect=AssertionError("portable Git path entered")):
                    rc = hook.main()
                self.assertEqual(rc, 1 if fail else 0)
                self.assertEqual(output.getvalue().strip(), "" if fail else str(root))
                self.assertEqual(self.snapshot(root), before)


class F5F6HiddenIndexSafetyTests(F4ManagedAutoProfileTests):
    """Exact installed and external-GC routes; destructive GC calls are intercepted."""

    def cli(self, root):
        import io
        import sys
        original = self.storage.git
        applications = []
        def observed(repo, *args):
            if args[:2] == ('sparse-checkout', 'set'):
                applications.append(args)
            return original(repo, *args)
        with patch.object(self.storage, 'load_policy', return_value=self.policy), \
             patch.object(self.storage, 'volume_info', return_value=self.info), \
             patch.object(self.storage, 'git', side_effect=observed), \
             patch.object(sys, 'argv', ['storage', 'session-start']), \
             patch.object(sys, 'stdin', io.StringIO(json.dumps({'cwd': str(root)}))), \
             patch.object(sys, 'stdout', io.StringIO()), patch.object(sys, 'stderr', io.StringIO()):
            rc = self.storage.main()
        return rc, applications

    def unchanged_and_locked(self, repo, root, before):
        self.assertEqual(self.snapshot(root), before)
        self.assertIn('locked ' + self.storage.LOCK_REASON,
                      self.git(repo, 'worktree', 'list', '--porcelain').decode())

    def failed_read(self, command, *, malformed=False):
        original = subprocess.run
        def run(args, *positional, **kwargs):
            if command in args:
                binary = b'malformed-index\0' if malformed else b''
                out = binary.decode() if kwargs.get('text') else binary
                err = 'fixture read failure' if kwargs.get('text') else b'fixture read failure'
                return subprocess.CompletedProcess(args, 0 if malformed else 128, out, err)
            return original(args, *positional, **kwargs)
        return patch.object(self.storage.subprocess, 'run', side_effect=run)

    def gc_fixture(self, name, *, sparse=False):
        from scripts import worktree_gc
        repo, root = self.full_checkout(name)
        self.git(repo, 'update-ref', 'refs/remotes/origin/main', 'HEAD')
        if sparse:
            self.git(root, 'sparse-checkout', 'set', '--cone', 'src', 'config')
        self.git(repo, 'worktree', 'lock', '--reason', self.storage.LOCK_REASON, str(root))
        wt = next(w for w in worktree_gc.parse_worktree_list(
            self.git(repo, 'worktree', 'list', '--porcelain').decode()) if w.path == root)
        return worktree_gc, repo, root, wt

    def classify_gc(self, gc, repo, wt):
        with patch.object(gc, 'worktree_storage', self.storage), \
             patch.object(self.storage, 'volume_info', return_value=self.info), \
             patch.object(gc, 'activity_age_days', return_value=(8, {'fixture': 8})):
            gc.classify(wt, repo, {**gc.DEFAULT_CONFIG, 'min_age_days': 0,
                                  '_storage_policy': self.policy}, {}, {}, True, repo, 0)

    def apply_gc(self, gc, repo, root, wt, *, after_status=None):
        original = gc._git
        effects = []
        injected = []
        def intercepted(where, *args, **kwargs):
            if args[:2] in (('worktree', 'unlock'), ('worktree', 'remove')):
                effects.append(args)
                # Record admission without touching a lock or removing any checkout.
                return (0, '', '') if args[1] == 'unlock' else (1, '', 'fixture removal intercepted')
            if args[:2] in (('worktree', 'prune'), ('branch', '-D')):
                return 0, '', ''
            result = original(where, *args, **kwargs)
            if after_status and 'status' in args and not injected:
                injected.append(True)
                after_status()
            return result
        with patch.object(gc, 'worktree_storage', self.storage), \
             patch.object(self.storage, 'volume_info', return_value=self.info), \
             patch.object(gc, 'proc_cwd_map', return_value={}), \
             patch.object(gc, '_ledger_write'), patch.object(gc, '_git', side_effect=intercepted), \
             patch.object(gc.shutil, 'rmtree', side_effect=AssertionError('destructive GC primitive reached')):
            result = gc.apply_deletions(repo, [wt],
                {'_storage_policy': self.policy, 'delete_local_branches': False},
                [Path(self.policy['root'])])
        self.assertTrue(root.exists())
        self.assertIn('locked ' + self.storage.LOCK_REASON,
                      self.git(repo, 'worktree', 'list', '--porcelain').decode())
        return result, effects

    def test_f5_installed_session_start_preserves_hidden_edits(self):
        for flag in ('--assume-unchanged', '--skip-worktree'):
            with self.subTest(flag=flag):
                repo, root = self.full_checkout('f5-' + flag[2:])
                self.git(root, 'update-index', flag, 'data/heavy.txt')
                (root / 'data/heavy.txt').write_text('hidden unfinished work\n')
                before = self.snapshot(root)
                self.assertEqual(self.cli(root), (0, []))
                self.unchanged_and_locked(repo, root, before)

    def test_f5_installed_session_start_preserves_visible_dirty_work(self):
        for kind in ('unstaged', 'staged', 'untracked'):
            with self.subTest(kind=kind):
                repo, root = self.full_checkout('f5-' + kind)
                path = root / ('data/new.txt' if kind == 'untracked' else 'data/heavy.txt')
                path.write_text('unfinished work\n')
                if kind == 'staged':
                    self.git(root, 'add', 'data/heavy.txt')
                before = self.snapshot(root)
                self.assertEqual(self.cli(root), (0, []))
                self.unchanged_and_locked(repo, root, before)

    def test_f5_installed_session_start_preserves_conflicted_index(self):
        repo, root = self.full_checkout('f5-conflict')
        blob = self.git(root, 'rev-parse', 'HEAD:src/code.py').decode().strip()
        entries = '0 ' + '0' * 40 + '\tsrc/code.py\n'
        entries += ''.join(f'100644 {blob} {stage}\tsrc/code.py\n' for stage in (1, 2, 3))
        self.git(root, 'update-index', '--index-info', input_bytes=entries.encode())
        before = self.snapshot(root)
        self.assertEqual(self.cli(root), (0, []))
        self.unchanged_and_locked(repo, root, before)

    def test_f5_installed_session_start_unknown_reads_refuse(self):
        for command in ('config', 'ls-files', 'status'):
            with self.subTest(command=command):
                repo, root = self.full_checkout('f5-unknown-' + command)
                before = self.snapshot(root)
                with self.failed_read(command):
                    self.assertEqual(self.cli(root), (1, []))
                self.unchanged_and_locked(repo, root, before)

    def test_f5_installed_session_start_malformed_index_refuses(self):
        repo, root = self.full_checkout('f5-malformed')
        before = self.snapshot(root)
        with self.failed_read('ls-files', malformed=True):
            self.assertEqual(self.cli(root), (1, []))
        self.unchanged_and_locked(repo, root, before)

    def test_f5_installed_session_start_clean_full_is_still_sparsified(self):
        repo, root = self.full_checkout('f5-clean')
        rc, applications = self.cli(root)
        self.assertEqual(rc, 0)
        self.assertEqual(len(applications), 1)
        self.assertFalse((root / 'data/heavy.txt').exists())
        self.assertTrue((root / 'src/code.py').exists())
        self.assertIn('locked ' + self.storage.LOCK_REASON,
                      self.git(repo, 'worktree', 'list', '--porcelain').decode())

    def test_f5_installed_session_start_preserves_existing_sparse_and_disabled(self):
        for state in ('sparse', 'disabled'):
            with self.subTest(state=state):
                repo, root = self.full_checkout('f5-' + state)
                if state == 'sparse':
                    self.git(root, 'sparse-checkout', 'set', '--cone', 'src', 'config')
                    self.assertFalse((root / 'data/heavy.txt').exists())
                else:
                    (root / 'config/sparse_worktree.json').write_text(json.dumps({'enabled': False}))
                before = self.snapshot(root)
                self.assertEqual(self.cli(root), (0, []))
                self.unchanged_and_locked(repo, root, before)

    def test_f6_classification_preserves_hidden_materialized_work(self):
        for flag in ('--assume-unchanged', '--skip-worktree'):
            with self.subTest(flag=flag):
                gc, repo, root, wt = self.gc_fixture('f6-class-' + flag[2:])
                self.git(root, 'update-index', flag, 'data/heavy.txt')
                (root / 'data/heavy.txt').write_text('hidden unfinished GC work\n')
                before = self.snapshot(root)
                self.classify_gc(gc, repo, wt)
                self.assertNotIn(wt.verdict, gc.SAFE_VERDICTS)
                result, effects = self.apply_gc(gc, repo, root, wt)
                self.assertEqual(effects, [])
                self.assertEqual(result['deleted'], [])
                self.unchanged_and_locked(repo, root, before)

    def test_f6_final_guard_preserves_work_hidden_after_classification(self):
        for flag in ('--assume-unchanged', '--skip-worktree'):
            with self.subTest(flag=flag):
                gc, repo, root, wt = self.gc_fixture('f6-final-' + flag[2:])
                self.classify_gc(gc, repo, wt)
                self.assertEqual(wt.verdict, 'SAFE_MERGED')
                self.git(root, 'update-index', flag, 'data/heavy.txt')
                (root / 'data/heavy.txt').write_text('new hidden GC work\n')
                before = self.snapshot(root)
                result, effects = self.apply_gc(gc, repo, root, wt)
                self.assertEqual(effects, [])
                self.assertEqual(result['deleted'], [])
                self.assertTrue(result['errors'])
                self.unchanged_and_locked(repo, root, before)

    def test_f6_final_guard_keeps_materialized_skip_entry_in_sparse_checkout(self):
        gc, repo, root, wt = self.gc_fixture('f6-present-sparse', sparse=True)
        self.classify_gc(gc, repo, wt)
        self.assertEqual(wt.verdict, 'SAFE_MERGED')
        (root / 'data').mkdir(exist_ok=True)
        (root / 'data/heavy.txt').write_text('materialized hidden work\n')
        before = self.snapshot(root)
        result, effects = self.apply_gc(gc, repo, root, wt)
        self.assertEqual(effects, [])
        self.assertEqual(result['deleted'], [])
        self.unchanged_and_locked(repo, root, before)

    def test_f6_clean_full_and_legitimate_absent_sparse_are_admissible(self):
        for sparse in (False, True):
            with self.subTest(sparse=sparse):
                gc, repo, root, wt = self.gc_fixture('f6-clean-' + str(sparse), sparse=sparse)
                if sparse:
                    self.assertFalse((root / 'data/heavy.txt').exists())
                before = self.snapshot(root)
                self.classify_gc(gc, repo, wt)
                self.assertEqual(wt.verdict, 'SAFE_MERGED')
                result, effects = self.apply_gc(gc, repo, root, wt)
                self.assertEqual([x[:2] for x in effects], [('worktree', 'unlock'), ('worktree', 'remove')])
                self.assertEqual(result['deleted'], [])  # removal was intercepted
                self.unchanged_and_locked(repo, root, before)

    def test_f6_absent_skipped_included_file_is_not_legitimate_sparse_omission(self):
        gc, repo, root, wt = self.gc_fixture('f6-hidden-deletion', sparse=True)
        self.classify_gc(gc, repo, wt)
        self.assertEqual(wt.verdict, 'SAFE_MERGED')
        self.git(root, 'update-index', '--skip-worktree', 'src/code.py')
        (root / 'src/code.py').unlink()
        before = self.snapshot(root)
        result, effects = self.apply_gc(gc, repo, root, wt)
        self.assertEqual(effects, [])
        self.assertEqual(result['deleted'], [])
        self.unchanged_and_locked(repo, root, before)

    def test_f6_unknown_index_config_or_rules_keeps_lock_at_both_gates(self):
        for gate in ('classify', 'apply'):
            for command in ('ls-files', 'config', 'check-rules'):
                with self.subTest(gate=gate, command=command):
                    gc, repo, root, wt = self.gc_fixture('f6-unknown-' + gate + command, sparse=True)
                    self.classify_gc(gc, repo, wt)
                    self.assertEqual(wt.verdict, 'SAFE_MERGED')
                    before = self.snapshot(root)
                    with self.failed_read(command):
                        if gate == 'classify':
                            self.classify_gc(gc, repo, wt)
                            self.assertNotIn(wt.verdict, gc.SAFE_VERDICTS)
                        result, effects = self.apply_gc(gc, repo, root, wt)
                    self.assertEqual(effects, [])
                    self.assertEqual(result['deleted'], [])
                    self.unchanged_and_locked(repo, root, before)

    def test_f6_unknown_materialization_stat_keeps_lock_at_both_gates(self):
        original = Path.lstat
        for gate in ('classify', 'apply'):
            with self.subTest(gate=gate):
                gc, repo, root, wt = self.gc_fixture('f6-stat-' + gate, sparse=True)
                self.classify_gc(gc, repo, wt)
                self.assertEqual(wt.verdict, 'SAFE_MERGED')
                before = self.snapshot(root)
                def denied(path, *args, **kwargs):
                    if path == root / 'data':
                        raise PermissionError('fixture inspection denied')
                    return original(path, *args, **kwargs)
                with patch.object(Path, 'lstat', denied):
                    if gate == 'classify':
                        self.classify_gc(gc, repo, wt)
                        self.assertNotIn(wt.verdict, gc.SAFE_VERDICTS)
                    result, effects = self.apply_gc(gc, repo, root, wt)
                self.assertEqual(effects, [])
                self.assertEqual(result['deleted'], [])
                self.unchanged_and_locked(repo, root, before)

    def test_f6_hidden_edit_during_final_status_still_blocks_unlock(self):
        gc, repo, root, wt = self.gc_fixture('f6-last-boundary')
        self.classify_gc(gc, repo, wt)
        self.assertEqual(wt.verdict, 'SAFE_MERGED')
        injected = []
        def introduce_hidden_edit():
            self.git(root, 'update-index', '--assume-unchanged', 'data/heavy.txt')
            (root / 'data/heavy.txt').write_text('hidden after final status\n')
            injected.append(self.snapshot(root))
        result, effects = self.apply_gc(gc, repo, root, wt, after_status=introduce_hidden_edit)
        self.assertEqual(len(injected), 1)
        self.assertEqual(effects, [])
        self.assertEqual(result['deleted'], [])
        self.unchanged_and_locked(repo, root, injected[0])


if __name__=='__main__': unittest.main()
