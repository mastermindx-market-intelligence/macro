"""Unit tests for agentos_standing_instructions (pure stdlib unittest).

Covers positive Unicode/newline/exact-preservation/detachment behaviour,
absence versus authored-empty declaration, boundary sizes (16/17 items,
4096/4097 codepoints), malformed instruction refs, source-ref mismatch,
unknown item fields, duplicate ids, booleans, NaN, control characters, the
32768-byte public envelope cap (including Unicode), and the revision digest
binding to exact ref and text content.
"""

import copy
import hashlib
import json
import os
import sys
import unittest
from unittest import mock

from scripts import agentos_standing_instructions as asi

INVALID = 'STANDING_INSTRUCTIONS_INVALID'
REPO = 'mastermindx-market-intelligence/macro'
COMMIT = '0123456789abcdef0123456789abcdef01234567'
SHA256 = 'fedcba9876543210fedcba9876543210fedcba9876543210fedcba9876543210'
DEFAULT_KEY = 'DOC-INGEST'
DEFAULT_REF = 'INS:CHECK-FRESHNESS'
DEFAULT_TEXT = 'Verify the source feed is fresh before each run.'


def make_source_ref(key=DEFAULT_KEY, commit=COMMIT, sha256=SHA256):
    return {
        'repository': REPO,
        'commit': commit,
        'path': 'agentos/workstreams/WS-%s.md' % key,
        'content_sha256': sha256,
    }


_UNSET = object()


def make_record(key=DEFAULT_KEY, standing=_UNSET, **extra):
    record = {'key': key, 'title': 'Doc ingest pipeline', 'status': 'ACTIVE'}
    record.update(extra)
    if standing is not _UNSET:
        record['standing_instructions'] = standing
    return record


def make_item(ref=DEFAULT_REF, text=DEFAULT_TEXT):
    return {'instruction_ref': ref, 'text': text}


def expected_revision(ref, text):
    payload = json.dumps(
        {'instruction_ref': ref, 'text': text},
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def project(record=_UNSET, source_ref=_UNSET):
    if record is _UNSET:
        record = make_record()
    if source_ref is _UNSET:
        source_ref = make_source_ref()
    return asi.project_standing_instructions(record, source_ref)


class ProjectorTestCase(unittest.TestCase):

    def assertInvalid(self, fn, *args, **kwargs):
        with self.assertRaises(ValueError) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(str(ctx.exception), INVALID)
        return ctx


class BodyShapeTests(ProjectorTestCase):

    def test_absent_field_is_not_declared(self):
        body = project()
        self.assertEqual(body['schema'], asi.BODY_SCHEMA)
        self.assertEqual(body['selection'], {'work_ref': 'WS:' + DEFAULT_KEY})
        self.assertEqual(body['declaration'], asi.DECLARATION_NOT_DECLARED)
        self.assertEqual(body['instructions'], [])
        self.assertEqual(
            body['source'],
            {
                'repository': REPO,
                'commit': COMMIT,
                'path': 'agentos/workstreams/WS-%s.md' % DEFAULT_KEY,
                'content_sha256': SHA256,
            },
        )

    def test_top_level_keys_are_exact(self):
        self.assertEqual(
            frozenset(project()),
            frozenset((
                'schema', 'selection', 'source', 'declaration',
                'instructions')),
        )

    def test_supplied_empty_list_is_supplied(self):
        body = project(make_record(standing=[]))
        self.assertEqual(body['declaration'], asi.DECLARATION_SUPPLIED)
        self.assertEqual(body['instructions'], [])

    def test_absence_differs_from_authored_empty_list(self):
        absent = project()
        supplied = project(make_record(standing=[]))
        self.assertNotEqual(absent['declaration'], supplied['declaration'])
        self.assertEqual(absent['instructions'], supplied['instructions'])

    def test_instruction_entry_keys_are_exact(self):
        body = project(make_record(standing=[make_item()]))
        self.assertEqual(len(body['instructions']), 1)
        self.assertEqual(
            frozenset(body['instructions'][0]),
            frozenset(('instruction_ref', 'text', 'revision')),
        )
        self.assertEqual(
            frozenset(body['source']),
            frozenset(('repository', 'commit', 'path', 'content_sha256')),
        )

    def test_arbitrary_other_fields_are_never_returned(self):
        record = make_record(
            standing=[make_item()],
            grant='grant-internal',
            clock='2026-11-04T00:00:00Z',
            revision='SHOULD-NOT-LEAK',
            owner='SHOULD-NOT-LEAK',
        )
        body = project(record)
        serialized = json.dumps(body, ensure_ascii=False)
        self.assertNotIn('SHOULD-NOT-LEAK', serialized)
        self.assertNotIn('grant-internal', serialized)
        self.assertNotIn('2026-11-04T00:00:00Z', serialized)
        self.assertNotIn('revision', body)
        self.assertNotIn('status', body)
        self.assertNotIn('title', body)

    def test_no_revision_status_clock_grant_authored_on_result(self):
        # The projector authors no body-level revision/status/clock/grant
        # metadata; the per-instruction `revision` digest is required output.
        body = project(make_record(standing=[make_item()]))
        for forbidden in ('revision', 'status', 'clock', 'grant'):
            self.assertNotIn(forbidden, body)
        for instruction in body['instructions']:
            for forbidden in ('status', 'clock', 'grant'):
                self.assertNotIn(forbidden, instruction)


class RevisionTests(ProjectorTestCase):

    def test_revision_matches_canonical_digest(self):
        text = 'Keep \n the feed fresh.\t'
        body = project(make_record(standing=[make_item(text=text)]))
        self.assertEqual(
            body['instructions'][0]['revision'],
            expected_revision(DEFAULT_REF, text),
        )

    def test_revision_is_deterministic(self):
        standing = [make_item(), make_item(ref='INS:SECOND-CHECK')]
        first = project(make_record(standing=copy.deepcopy(standing)))
        second = project(make_record(standing=copy.deepcopy(standing)))
        self.assertEqual(first, second)

    def test_content_change_changes_revision(self):
        first = project(make_record(standing=[make_item(text='alpha')]))
        second = project(make_record(standing=[make_item(text='alpha ')]))
        self.assertNotEqual(
            first['instructions'][0]['revision'],
            second['instructions'][0]['revision'],
        )

    def test_ref_change_changes_revision(self):
        first = project(make_record(standing=[make_item()]))
        second = project(
            make_record(standing=[make_item(ref='INS:OTHER-REF')]))
        self.assertNotEqual(
            first['instructions'][0]['revision'],
            second['instructions'][0]['revision'],
        )

    def test_unrelated_record_field_change_keeps_revisions(self):
        plain = project(make_record(standing=[make_item()]))
        decorated = project(
            make_record(standing=[make_item()], owner='someone',
                        priority=7, tags=['x', 'y']))
        self.assertEqual(plain['instructions'], decorated['instructions'])
        self.assertEqual(plain['declaration'], decorated['declaration'])


class PreservationTests(ProjectorTestCase):

    def test_newlines_carriage_returns_and_tabs_preserved(self):
        text = '  line one\nline two\r\nline three\ttabbed\n\n'
        body = project(make_record(standing=[make_item(text=text)]))
        self.assertEqual(body['instructions'][0]['text'], text)

    def test_unicode_preserved_unescaped(self):
        text = '验证 過程 — vérification \U0001f9ec محتوى'
        body = project(make_record(standing=[make_item(text=text)]))
        self.assertEqual(body['instructions'][0]['text'], text)
        encoded = asi.encode_public_envelope(body)
        self.assertIn('验证 過程'.encode('utf-8'), encoded)
        self.assertNotIn(b'\\u', encoded)

    def test_whitespace_only_edges_kept_verbatim(self):
        text = '   padded core   '
        body = project(make_record(standing=[make_item(text=text)]))
        self.assertEqual(body['instructions'][0]['text'], text)

    def test_internal_whitespace_blank_not_confused_with_blank(self):
        text = '\n\treal content\r\n'
        body = project(make_record(standing=[make_item(text=text)]))
        self.assertEqual(body['instructions'][0]['text'], text)


class DetachmentTests(ProjectorTestCase):

    def test_result_structures_are_detached(self):
        items = [make_item()]
        record = make_record(standing=items)
        source_ref = make_source_ref()
        body = project(record, source_ref)
        self.assertIsNot(body['source'], source_ref)
        self.assertIsNot(body['instructions'], record['standing_instructions'])
        self.assertIsNot(body['instructions'][0], items[0])
        self.assertIsNot(body['selection'], record)

    def test_later_input_mutation_does_not_affect_result(self):
        items = [make_item()]
        record = make_record(standing=items)
        source_ref = make_source_ref()
        body = project(record, source_ref)
        snapshot = copy.deepcopy(body)
        items.append(make_item(ref='INS:LATE-ARRIVAL'))
        record['title'] = 'mutated'
        record['key'] = 'OTHER-KEY'
        source_ref['commit'] = 'a' * 40
        self.assertEqual(body, snapshot)

    def test_inputs_are_not_mutated(self):
        items = [make_item(text='unchanged\n')]
        record = make_record(standing=items)
        record_snapshot = copy.deepcopy(record)
        source_ref = make_source_ref()
        source_snapshot = copy.deepcopy(source_ref)
        project(record, source_ref)
        self.assertEqual(record, record_snapshot)
        self.assertEqual(source_ref, source_snapshot)

    def test_projection_performs_no_file_io(self):
        record = make_record(standing=[make_item()])
        with mock.patch('builtins.open', side_effect=AssertionError('io')):
            with mock.patch('os.open', side_effect=AssertionError('io')):
                project(record)


class CountBoundaryTests(ProjectorTestCase):

    @staticmethod
    def _items(count, text=DEFAULT_TEXT):
        return [
            make_item(ref='INS:ITEM-%02d' % index, text=text)
            for index in range(count)
        ]

    def test_sixteen_items_accepted(self):
        body = project(make_record(standing=self._items(16)))
        self.assertEqual(asi.DECLARATION_SUPPLIED, body['declaration'])
        self.assertEqual(len(body['instructions']), 16)
        self.assertEqual(len({entry['revision']
                              for entry in body['instructions']}), 16)

    def test_seventeen_items_refused(self):
        self.assertInvalid(
            project, make_record(standing=self._items(17)), make_source_ref())


class TextBoundaryTests(ProjectorTestCase):

    def test_4096_codepoints_accepted(self):
        text = 'A' * asi.MAX_TEXT_CODEPOINTS
        body = project(make_record(standing=[make_item(text=text)]))
        self.assertEqual(body['instructions'][0]['text'], text)

    def test_4097_codepoints_refused(self):
        self.assertInvalid(
            project,
            make_record(standing=[make_item(text='A' * 4097)]),
            make_source_ref(),
        )

    def test_4096_codepoints_counts_codepoints_not_bytes(self):
        # Astral-plane characters occupy 4 UTF-8 bytes but 1 codepoint each.
        text = '\U0001d11e' * asi.MAX_TEXT_CODEPOINTS
        body = project(make_record(standing=[make_item(text=text)]))
        self.assertEqual(body['instructions'][0]['text'], text)

    def test_multibyte_4096_codepoints_still_within_envelope_cap(self):
        text = '字' * asi.MAX_TEXT_CODEPOINTS  # 3 UTF-8 bytes each
        body = project(make_record(standing=[make_item(text=text)]))
        envelope = asi.encode_public_envelope(body)
        self.assertLessEqual(len(envelope), asi.MAX_ENVELOPE_BYTES)


class RefRulesTests(ProjectorTestCase):

    def test_minimum_and_maximum_ref_key_lengths_accepted(self):
        short = project(make_record(standing=[make_item(ref='INS:AB')]))
        self.assertEqual(short['instructions'][0]['instruction_ref'], 'INS:AB')
        long_key = 'A' * 64
        long = project(
            make_record(standing=[make_item(ref='INS:' + long_key)]))
        self.assertEqual(
            long['instructions'][0]['instruction_ref'], 'INS:' + long_key)
        self.assertEqual(len(long['instructions'][0]['instruction_ref']), 68)

    def test_ref_key_length_one_refused(self):
        self.assertInvalid(
            project,
            make_record(standing=[make_item(ref='INS:A')]),
            make_source_ref(),
        )

    def test_ref_key_length_sixty_five_refused(self):
        self.assertInvalid(
            project,
            make_record(standing=[make_item(ref='INS:' + 'A' * 65)]),
            make_source_ref(),
        )

    def test_missing_ins_prefix_refused(self):
        for bad in ('CHECK-FRESHNESS', 'INS', 'ins:CHECK-FRESHNESS',
                    'INSTRUCTION:CHECK-FRESHNESS'):
            self.assertInvalid(
                project,
                make_record(standing=[make_item(ref=bad)]),
                make_source_ref(),
            )

    def test_lowercase_after_prefix_refused(self):
        self.assertInvalid(
            project,
            make_record(standing=[make_item(ref='INS:check-freshness')]),
            make_source_ref(),
        )

    def test_bare_prefix_refused(self):
        self.assertInvalid(
            project,
            make_record(standing=[make_item(ref='INS:')]),
            make_source_ref(),
        )

    def test_ref_with_space_or_trailing_newline_refused(self):
        for bad in ('INS:CHECK FRESHNESS', 'INS:CHECK-FRESHNESS\n',
                    ' INS:CHECK-FRESHNESS', 'INS:-CHECK', 'INS:CHECK-',
                    'INS:CHECK--FRESHNESS'):
            self.assertInvalid(
                project,
                make_record(standing=[make_item(ref=bad)]),
                make_source_ref(),
            )

    def test_non_string_ref_refused(self):
        for bad in (True, False, 7, None, ['INS:AB'], {'a': 1}):
            self.assertInvalid(
                project,
                make_record(standing=[make_item(ref=bad)]),
                make_source_ref(),
            )

    def test_duplicate_refs_refused(self):
        standing = [
            make_item(ref='INS:DUP-REF', text='first'),
            make_item(ref='INS:DUP-REF', text='second'),
        ]
        self.assertInvalid(
            project, make_record(standing=standing), make_source_ref())

    def test_distinct_refs_with_same_text_accepted(self):
        standing = [
            make_item(ref='INS:FIRST-REF', text='same text'),
            make_item(ref='INS:SECOND-REF', text='same text'),
        ]
        body = project(make_record(standing=standing))
        revisions = {entry['revision'] for entry in body['instructions']}
        self.assertEqual(len(revisions), 2)


class TextRulesTests(ProjectorTestCase):

    def test_blank_text_refused(self):
        for bad in ('', ' ', '   ', '\t', '\n', ' \r\n\t ', '　'):
            self.assertInvalid(
                project,
                make_record(standing=[make_item(text=bad)]),
                make_source_ref(),
            )

    def test_non_string_text_refused(self):
        for bad in (True, False, 0, 3.5, None, ['text'], {'t': 1}):
            self.assertInvalid(
                project,
                make_record(standing=[make_item(text=bad)]),
                make_source_ref(),
            )

    def test_nul_and_non_permitted_c0_refused(self):
        for bad in ('\x00', '\x01', '\x1f', '\x1b', 'bad\x02text'):
            self.assertInvalid(
                project,
                make_record(standing=[make_item(text=bad)]),
                make_source_ref(),
            )

    def test_del_refused(self):
        self.assertInvalid(
            project,
            make_record(standing=[make_item(text='bad\x7ftext')]),
            make_source_ref(),
        )

    def test_lf_cr_tab_permitted(self):
        text = 'a\tb\nc\rd'
        body = project(make_record(standing=[make_item(text=text)]))
        self.assertEqual(body['instructions'][0]['text'], text)

    def test_lone_surrogate_text_refused(self):
        self.assertInvalid(
            project,
            make_record(standing=[make_item(text='bad \ud800 text')]),
            make_source_ref(),
        )


class ItemShapeTests(ProjectorTestCase):

    def test_unknown_item_field_refused(self):
        item = make_item()
        item['note'] = 'extra'
        self.assertInvalid(
            project, make_record(standing=[item]), make_source_ref())

    def test_missing_text_refused(self):
        self.assertInvalid(
            project,
            make_record(
                standing=[{'instruction_ref': DEFAULT_REF}]),
            make_source_ref(),
        )

    def test_missing_instruction_ref_refused(self):
        self.assertInvalid(
            project,
            make_record(standing=[{'text': DEFAULT_TEXT}]),
            make_source_ref(),
        )

    def test_non_dict_item_refused(self):
        for bad in ('INS:AB', 5, True, None, [make_item()], ('a',)):
            self.assertInvalid(
                project,
                make_record(standing=[bad]),
                make_source_ref(),
            )

    def test_field_must_be_list(self):
        for bad in (True, False, 0, 'x', {'instruction_ref': DEFAULT_REF,
                                          'text': DEFAULT_TEXT}, None,
                    (make_item(),), 3.5):
            self.assertInvalid(
                project, make_record(standing=bad), make_source_ref())


class RecordKeyTests(ProjectorTestCase):

    def test_minimum_and_maximum_key_lengths_accepted(self):
        body = project(make_record(key='AB'), make_source_ref(key='AB'))
        self.assertEqual(body['selection'], {'work_ref': 'WS:AB'})
        long_key = 'K' * 64
        body = project(
            make_record(key=long_key),
            make_source_ref(key=long_key),
        )
        self.assertEqual(body['selection'], {'work_ref': 'WS:' + long_key})

    def test_key_length_one_and_sixty_five_refused(self):
        self.assertInvalid(project, make_record(key='A'), make_source_ref())
        self.assertInvalid(
            project,
            make_record(key='K' * 65),
            make_source_ref(key='K' * 65),
        )

    def test_non_canonical_keys_refused(self):
        for bad in ('doc-ingest', 'DOC_INGEST', 'DOC INGEST', '-LEAD',
                    'TRAIL-', 'DOU--BLE', 'DOC\n', 'DOC.INGEST', 7, True,
                    None, ''):
            self.assertInvalid(project, make_record(key=bad),
                               make_source_ref())

    def test_digit_segments_accepted(self):
        body = project(make_record(key='WS-123'), make_source_ref('WS-123'))
        self.assertEqual(body['selection'], {'work_ref': 'WS:WS-123'})

    def test_record_must_be_dict(self):
        for bad in (None, [], 'record', 7, True, (make_item(),)):
            self.assertInvalid(project, bad, make_source_ref())

    def test_missing_key_refused(self):
        record = make_record()
        del record['key']
        self.assertInvalid(project, record, make_source_ref())


class SourceRefTests(ProjectorTestCase):

    def test_exact_source_ref_accepted(self):
        body = project()
        self.assertEqual(
            body['source'],
            {
                'repository': REPO,
                'commit': COMMIT,
                'path': 'agentos/workstreams/WS-%s.md' % DEFAULT_KEY,
                'content_sha256': SHA256,
            },
        )

    def test_source_ref_must_be_dict(self):
        for bad in (None, [], 'ref', 7, True):
            self.assertInvalid(project, make_record(), bad)

    def test_missing_and_extra_fields_refused(self):
        complete = make_source_ref()
        for missing in ('repository', 'commit', 'path', 'content_sha256'):
            broken = dict(complete)
            del broken[missing]
            self.assertInvalid(project, make_record(), broken)
        for extra_value in ('x', 5, None):
            broken = dict(complete)
            broken['extra'] = extra_value
            self.assertInvalid(project, make_record(), broken)

    def test_wrong_repository_refused(self):
        for bad in ('other/repo', '', REPO.upper(),
                    'mastermindx-market-intelligence/macro/'):
            broken = dict(make_source_ref(), repository=bad)
            self.assertInvalid(project, make_record(), broken)

    def test_commit_rules(self):
        for bad in ('g' * 40, COMMIT + '8', COMMIT.upper(), COMMIT[:-1],
                    COMMIT + 'a', 5, None, True, COMMIT + '\n'):
            self.assertInvalid(
                project, make_record(), make_source_ref(commit=bad))

    def test_content_sha256_rules(self):
        for bad in ('e' * 63, 'e' * 65, SHA256.upper(), SHA256[:-1],
                    SHA256 + 'f', 0, None, True, SHA256 + '\n'):
            self.assertInvalid(
                project, make_record(), make_source_ref(sha256=bad))

    def test_path_must_match_record_key(self):
        mismatches = (
            'agentos/workstreams/WS-OTHER-KEY.md',
            'agentos/workstreams/WS-.md',
            'agentos/workstreams/ws-%s.md' % DEFAULT_KEY.lower(),
            'agentos/workstreams/WS-%s' % DEFAULT_KEY,
            'agentos/workstreams/WS-%s.md.txt' % DEFAULT_KEY,
            'other/workstreams/WS-%s.md' % DEFAULT_KEY,
            'agentos/workstreams/WS-%s.md\n' % DEFAULT_KEY,
            'agentos/workstreams/WS-%s.md ' % DEFAULT_KEY,
            'agentos/other/WS-%s.md' % DEFAULT_KEY,
            5, None, True,
        )
        for bad in mismatches:
            broken = dict(make_source_ref(), path=bad)
            self.assertInvalid(project, make_record(), broken)

    def test_matching_path_accepted_for_non_default_key(self):
        record = make_record(key='ALERT-ROUTING')
        body = project(record, make_source_ref(key='ALERT-ROUTING'))
        self.assertEqual(
            body['source']['path'],
            'agentos/workstreams/WS-ALERT-ROUTING.md',
        )
        self.assertEqual(
            body['selection'], {'work_ref': 'WS:ALERT-ROUTING'})


class EnvelopeTests(ProjectorTestCase):

    def test_envelope_shape_and_trailing_newline(self):
        body = project(make_record(standing=[make_item()]))
        encoded = asi.encode_public_envelope(body)
        self.assertIsInstance(encoded, bytes)
        self.assertTrue(encoded.endswith(b'\n'))
        self.assertEqual(encoded.count(b'\n'), 1)
        decoded = json.loads(encoded.decode('utf-8'))
        self.assertEqual(decoded, {'ok': True, 'result': body})
        self.assertLessEqual(len(encoded), asi.MAX_ENVELOPE_BYTES)

    def test_encoder_refuses_nan_body(self):
        self.assertInvalid(asi.encode_public_envelope,
                           {'bad': float('nan')})

    def test_encoder_refuses_unserializable_body(self):
        self.assertInvalid(asi.encode_public_envelope, {'bad': object()})

    def test_encoder_refuses_surrogate_body(self):
        self.assertInvalid(asi.encode_public_envelope, {'bad': '\ud800'})

    def test_unrelated_nan_and_nested_fields_permitted_and_not_returned(self):
        record = make_record(notes={'a': [1, float('nan')]})
        body = project(record)
        self.assertEqual(body['declaration'], asi.DECLARATION_NOT_DECLARED)
        asi.encode_public_envelope(body)

    def test_unicode_overcap_refused_without_truncation(self):
        # 16 items x 1500 CJK codepoints = 72000 UTF-8 bytes: far over cap.
        standing = [
            make_item(ref='INS:ITEM-%02d' % index, text='字' * 1500)
            for index in range(16)
        ]
        ctx = self.assertInvalid(
            project, make_record(standing=standing), make_source_ref())
        self.assertEqual(str(ctx.exception), INVALID)

    def test_ascii_overcap_refused(self):
        # 12 items x 3000 ASCII codepoints = 36000 bytes plus overhead.
        standing = [
            make_item(ref='INS:ITEM-%02d' % index, text='A' * 3000)
            for index in range(12)
        ]
        self.assertInvalid(
            project, make_record(standing=standing), make_source_ref())

    def test_unicode_undercap_accepted(self):
        standing = [
            make_item(ref='INS:ITEM-%02d' % index, text='字' * 1000)
            for index in range(8)
        ]
        body = project(make_record(standing=standing))
        envelope = asi.encode_public_envelope(body)
        self.assertLessEqual(len(envelope), asi.MAX_ENVELOPE_BYTES)
        self.assertEqual(len(body['instructions']), 8)

    def test_sixteen_full_size_instructions_refused_by_envelope_cap(self):
        standing = [
            make_item(ref='INS:ITEM-%02d' % index,
                      text='A' * asi.MAX_TEXT_CODEPOINTS)
            for index in range(16)
        ]
        self.assertInvalid(
            project, make_record(standing=standing), make_source_ref())

    def test_exact_capacity_boundary_accepted_and_exceeded_refused(self):
        base_items = [make_item(ref='INS:ITEM-%02d' % index, text='A')
                      for index in range(16)]
        base_body = project(make_record(standing=base_items))
        base_len = len(asi.encode_public_envelope(base_body))
        slack = asi.MAX_ENVELOPE_BYTES - base_len
        per_item, remainder = divmod(slack, 16)
        sizes = [1 + per_item] * 16
        sizes[0] += remainder
        for size in sizes:
            self.assertLessEqual(size, asi.MAX_TEXT_CODEPOINTS)
        accepted = project(make_record(standing=[
            make_item(ref='INS:ITEM-%02d' % index, text='A' * size)
            for index, size in enumerate(sizes)]))
        self.assertEqual(
            len(asi.encode_public_envelope(accepted)),
            asi.MAX_ENVELOPE_BYTES,
        )
        over_sizes = list(sizes)
        over_sizes[0] += 1
        self.assertLessEqual(over_sizes[0], asi.MAX_TEXT_CODEPOINTS)
        self.assertInvalid(project, make_record(standing=[
            make_item(ref='INS:ITEM-%02d' % index, text='A' * size)
            for index, size in enumerate(over_sizes)]), make_source_ref())


class ErrorContractTests(ProjectorTestCase):

    def test_error_is_value_error_with_fixed_message(self):
        with self.assertRaises(ValueError) as ctx:
            project(make_record(key='bad-lowercase'), make_source_ref())
        self.assertEqual(str(ctx.exception), INVALID)
        self.assertEqual(repr(ctx.exception),
                         repr(ValueError(INVALID)))

    def test_no_input_echo_in_error_message(self):
        secret = 'SENSITIVE-LEAK-DOC-INGEST'
        cases = [
            # Lowercase (non-canonical) key that embeds the secret.
            (make_record(key=secret.lower()), make_source_ref()),
            # Valid record, but source path embedding the secret.
            (make_record(), make_source_ref(key='DOC-INGEST') | {
                'path': 'agentos/workstreams/WS-%s.md' % secret}),
            # Over-length key carrying the secret.
            (make_record(key=secret + '-X' * 30), make_source_ref()),
        ]
        for record, source_ref in cases:
            with self.assertRaises(ValueError) as ctx:
                project(record, source_ref)
            self.assertNotIn(secret, str(ctx.exception))
            self.assertNotIn(secret, repr(ctx.exception))
            self.assertNotIn(DEFAULT_KEY, str(ctx.exception))

    def test_tuple_positions_do_not_confuse_validation(self):
        # record and source_ref swapped: both are dicts, so validation must
        # still reject on field structure rather than crash.
        self.assertInvalid(project, make_source_ref(), make_record())


if __name__ == '__main__':
    unittest.main()
