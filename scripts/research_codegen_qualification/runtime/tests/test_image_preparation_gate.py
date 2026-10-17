import json
import unittest
import image_preparation_gate as g


class ImageGateTests(unittest.TestCase):
    def call(self, **changes):
        args = dict(rc=1, raw=g.ABSENCE, timed_out=False, truncated=False,
                    collector_error=False, permission_refused=False,
                    client_version='29.1.3', server_version='29.1.3')
        args.update(changes)
        return g.classify_inspection(**args)

    def present(self):
        return [{'Id': g.IMAGE_ID, 'RepoDigests': [g.IMAGE], 'Os': 'linux',
                 'Architecture': 'amd64', 'Config': {'Entrypoint': None,
                 'Cmd': ['python3'], 'User': '', 'WorkingDir': '/',
                 'Volumes': None, 'Env': list(g.ENV)}}]

    def test_exact_absence_variants(self):
        for raw in (g.ABSENCE, b'[]\n' + g.ABSENCE):
            self.assertEqual('EXACT_ABSENCE', self.call(raw=raw))

    def test_absence_noise_and_reordered_channels_refuse(self):
        for raw in (g.ABSENCE+b'[]\n', g.ABSENCE*2, b'[]\n[]\n'+g.ABSENCE,
                    g.ABSENCE+b'permission denied\n', b'warning\n'+g.ABSENCE,
                    g.ABSENCE.rstrip(), g.ABSENCE.replace(b'python@', b'docker.io/library/python@'),
                    b'Error: NotFound\n', b'[]\n', g.ABSENCE.replace(b'bfebb8', b'aaaaaa')):
            with self.subTest(raw=raw), self.assertRaises(g.ImageGateRefused):
                self.call(raw=raw)

    def test_observation_must_be_complete(self):
        for key in ('timed_out', 'truncated', 'collector_error', 'permission_refused'):
            for value in (True, 0, None, ''):
                with self.subTest(key=key, value=value), self.assertRaises(g.ImageGateRefused):
                    self.call(**{key: value})

    def test_exit_version_and_bounds(self):
        for change in ({'rc': True}, {'rc': 0}, {'rc': 2}, {'rc': None}, {'rc': -9},
                       {'raw': b''}, {'raw': 'text'}, {'raw': b'x'*(g.CAP+1)},
                       {'client_version': '29.1.4'}, {'server_version': '29.1.2'}):
            with self.subTest(change=change), self.assertRaises(g.ImageGateRefused):
                self.call(**change)

    def test_exact_present(self):
        self.assertEqual('PRESENT', self.call(rc=0, raw=json.dumps(self.present()).encode()))

    def test_configuration_mutations(self):
        for key, value in [('Entrypoint', ['/bin/sh']), ('Cmd', ['sh']), ('User', None),
                           ('WorkingDir', ''), ('Volumes', {'/data': {}}),
                           ('Env', g.ENV + ['TOKEN=fixture']),
                           ('Healthcheck', {'Test': ['CMD', 'false']}), ('OnBuild', ['RUN false'])]:
            doc = self.present(); doc[0]['Config'][key] = value
            with self.subTest(key=key), self.assertRaises(g.ImageGateRefused):
                self.call(rc=0, raw=json.dumps(doc).encode())

    def test_missing_config_keys(self):
        for key in self.present()[0]['Config']:
            doc = self.present(); del doc[0]['Config'][key]
            with self.subTest(key=key), self.assertRaises(g.ImageGateRefused):
                self.call(rc=0, raw=json.dumps(doc).encode())

    def test_image_identity_and_shape(self):
        for key, value in [('Id', 'sha256:'+'1'*64), ('Os', 'windows'),
                           ('Architecture', 'arm64'), ('RepoDigests', ['evil.example/python@'+g.IMAGE_ID]),
                           ('RepoDigests', [g.IMAGE, 3]), ('Config', None)]:
            doc = self.present(); doc[0][key] = value
            with self.subTest(key=key), self.assertRaises(g.ImageGateRefused):
                self.call(rc=0, raw=json.dumps(doc).encode())
        for doc in ({}, [], self.present()*2, [None]):
            with self.subTest(doc=doc), self.assertRaises(g.ImageGateRefused):
                self.call(rc=0, raw=json.dumps(doc).encode())

    def test_json_ambiguity_and_trailing_stderr(self):
        raw = json.dumps(self.present()).encode()
        for bad in (raw+b'warning\n', raw[:-1]+b',NaN]', b'\xff',
                    raw.replace(b'"Os": "linux"', b'"Os": "linux", "Os": "linux"'),
                    b'['*2000+b']'*2000):
            with self.subTest(raw=bad[:20]), self.assertRaises(g.ImageGateRefused):
                self.call(rc=0, raw=bad)


if __name__ == '__main__':
    unittest.main()
