"""Check only the source-rendered review INPUT. No browser or acceptance claim."""
from __future__ import annotations

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import re
import unittest
from urllib.parse import unquote, urlsplit
import zipfile

HERE = Path(__file__).resolve().parent
FONT_SUFFIXES = {'.woff', '.woff2', '.ttf', '.otf', '.eot', '.ttc'}


class ResourceParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'img', 'source', 'iframe') and attrs.get('src'):
            self.urls.append(attrs['src'])
        if tag == 'link' and set(attrs.get('rel', '').split()) & {'stylesheet', 'icon', 'apple-touch-icon', 'preload', 'modulepreload'}:
            if attrs.get('href'):
                self.urls.append(attrs['href'])


def local_path(value, parent='site'):
    value = unquote(value.strip().strip('\"\''))
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or not parsed.path or value.startswith('#'):
        return None
    # Resolve relative CSS URLs, not arbitrary filesystem paths.
    items = [] if parsed.path.startswith('/') else list(PurePosixPath(parent).parts)
    for part in PurePosixPath(parsed.path.lstrip('/')).parts:
        if part == '..':
            if not items:
                raise ValueError('Reference escapes package')
            items.pop()
        elif part != '.':
            items.append(part)
    if not items or items[0] != 'site':
        items.insert(0, 'site')
    return '/'.join(items)


class ReviewInputChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads((HERE / 'SOURCE.json').read_text())
        with zipfile.ZipFile(HERE / 'candidate.zip') as archive:
            cls.names = archive.namelist()
            cls.members = {name: archive.read(name) for name in cls.names}
            cls.crc_error = archive.testzip()

    def test_safe_unique_archive_without_font_binaries(self):
        self.assertIsNone(self.crc_error)
        self.assertEqual(len(self.names), len(set(self.names)))
        for name in self.names:
            p = PurePosixPath(name)
            self.assertFalse(p.is_absolute())
            self.assertNotIn('..', p.parts)
            self.assertNotIn(p.suffix.lower(), FONT_SUFFIXES)

    def test_all_rendered_bytes_and_html_identity(self):
        files = self.source['rendered_files']
        self.assertEqual(set(files), {n for n in self.names if n.startswith('site/')})
        for name, record in files.items():
            self.assertEqual(len(self.members[name]), record['bytes'], name)
            self.assertEqual(hashlib.sha256(self.members[name]).hexdigest(), record['sha256'], name)
        self.assertEqual(hashlib.sha256(self.members['site/bonds.html']).hexdigest(), self.source['html_sha256'])
        self.assertEqual(self.source['html_sha256'], '6f99fcb52332dd57ed78b1b8477e8e977ca78370806a7615fe41da41d8614d3d')

    def test_apple_icon_has_exact_identity_and_bytes(self):
        self.assertIn('site/apple-touch-icon.png', self.members, 'Referenced icon was omitted in the reviewed input')
        record = self.source['assets']['apple-touch-icon.png']
        self.assertEqual(record['source_path'], 'site/apple-touch-icon.png')
        self.assertEqual(record['sha256'], '68ad76b7347d7302cea0a8c395c8315714f5972ac021f1fd54726044f3115da6')
        self.assertEqual(record['bytes'], 23722)

    def test_direct_html_and_css_resources_are_accounted_for(self):
        parser = ResourceParser(); parser.feed(self.members['site/bonds.html'].decode())
        refs = {local_path(url) for url in parser.urls}
        for name, content in self.members.items():
            if name.endswith('.css'):
                refs.update(local_path(url, str(PurePosixPath(name).parent))
                            for url in re.findall(r'url\(([^)]+)\)', content.decode()))
        excluded = {'site/' + name for name in self.source['font_assets_not_bundled']}
        missing = {name for name in refs if name is not None and name not in self.members and name not in excluded}
        self.assertEqual(missing, set(), 'Static resource omission; this is not a dynamic-network test')

    def test_rebuild_is_present_and_review_limits_remain_false(self):
        self.assertTrue((HERE / 'rebuild.py').is_file())
        self.assertIn('python3', self.source.get('rebuild_command', ''))
        for key in ['browser_navigation_performed', 'browser_admission_restored', 'screenshot_acceptance', 'production_deployment', 'server_started']:
            self.assertIs(self.source[key], False, key)
        self.assertIn('NOT_PROVEN', self.source['runtime_dynamic_network_closure'])

    def test_published_and_embedded_instructions_match(self):
        for name in ['SOURCE.json', 'README.md', 'rebuild.py', 'verify_input.py']:
            self.assertEqual(self.members.get(name), (HERE / name).read_bytes(), name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
