"""Real retained SEC submission and fail-closed parser boundary tests.

The parser and shared 13G helpers are imported from this checkout. The primary
submission is retained bytes; modified variants below are controlled fixtures.
"""
import dataclasses
import hashlib
import re
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from lib.dataos import sec_schedule13d as _13D
from lib.dataos import sec_filing_identity as _13G

_PRIMARY_RAW = (Path(__file__).parent / "fixtures/sec_schedule13d/0001104659-26-053223.txt").read_bytes()
_PRIMARY_TEXT = _PRIMARY_RAW.decode("utf-8")
_PRIMARY_SOURCE_SHA256 = "bdf3e6e7c77485bb6ccb461beb8db59e8c1199b9e16bcfab7ec4956c61c8a7df"
assert len(_PRIMARY_RAW) == 34155
assert hashlib.sha256(_PRIMARY_RAW).hexdigest() == _PRIMARY_SOURCE_SHA256

_RETAINED = datetime(2026, 10, 19, 19, 23, 43, 620825, tzinfo=timezone.utc)
_ACCEPTED = datetime(2026, 4, 30, 22, 26, 24, tzinfo=timezone.utc)

def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _parse(raw=_PRIMARY_RAW, retained=_RETAINED, sha=None):
    return _13D.parse_schedule13d_evidence(
        raw,
        expected_sha256=sha if sha is not None else _digest(raw),
        retained_at=retained,
    )


def _replace(old, new, count=1, text=_PRIMARY_TEXT):
    found = text.count(old)
    assert found == count, "fixture drift: %r occurs %d times, expected %d" % (
        old[:72],
        found,
        count,
    )
    return text.replace(old, new)


def _person_blocks(text=_PRIMARY_TEXT):
    return re.findall(
        r"      <reportingPersonInfo>.*?</reportingPersonInfo>", text, re.S
    )


def _swap_block(index, old, new):
    """Apply one mutation inside reporting person block ``index`` only."""
    blocks = _person_blocks()
    mutated = blocks[index].replace(old, new)
    assert mutated != blocks[index], "fixture drift: %r not in block %d" % (old[:72], index)
    return _PRIMARY_TEXT.replace(blocks[index], mutated, 1)


def _person(evidence, name):
    for person in evidence.reporting_persons:
        if person.name == name:
            return person
    raise AssertionError("no reporting person named %r" % name)


def _mutated_parse(text):
    return _parse(text.encode("utf-8"))


_MINIMAL_13G = """<SEC-DOCUMENT>0000000000-26-000001.txt : 20260115
<SEC-HEADER>0000000000-26-000001.hdr.sgml : 20260115
<ACCEPTANCE-DATETIME>20260115103000
ACCESSION NUMBER:\t\t0000000000-26-000001
CONFORMED SUBMISSION TYPE:\tSCHEDULE 13G
PUBLIC DOCUMENT COUNT:\t\t1
FILED AS OF DATE:\t\t20260115

SUBJECT COMPANY:\t

\tCOMPANY DATA:\t
\t\tCOMPANY CONFORMED NAME:\t\t\tApple Inc.
\t\tCENTRAL INDEX KEY:\t\t\t0000320193

FILED BY:\t\t

\tCOMPANY DATA:\t
\t\tCOMPANY CONFORMED NAME:\t\t\tSample Holder
\t\tCENTRAL INDEX KEY:\t\t\t0000000001
</SEC-HEADER>
<DOCUMENT>
<TYPE>SCHEDULE 13G
<SEQUENCE>1
<FILENAME>primary_doc.xml
<TEXT>
<XML>
<edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13g">
  <schemaVersion>X0202</schemaVersion>
  <headerData>
    <submissionType>SCHEDULE 13G</submissionType>
  </headerData>
  <formData>
    <coverPageHeader>
      <securitiesClassTitle>Common Stock</securitiesClassTitle>
      <eventDateRequiresFilingThisStatement>01/10/2026</eventDateRequiresFilingThisStatement>
      <issuerInfo>
        <issuerCik>0000320193</issuerCik>
        <issuerCusips>
          <issuerCusipNumber>037833100</issuerCusipNumber>
        </issuerCusips>
        <issuerName>Apple Inc.</issuerName>
      </issuerInfo>
    </coverPageHeader>
  </formData>
</edgarSubmission>
</XML>
</TEXT>
</DOCUMENT>
</SEC-DOCUMENT>
"""


class PrimarySubmissionTests(unittest.TestCase):
    """Parse the authentic retained Lucid/PIF Amendment No. 9 submission."""

    def test_full_evidence_extraction(self):
        evidence = _parse()
        self.assertEqual(evidence.accession, "0001104659-26-053223")
        self.assertEqual(evidence.form_type, "SCHEDULE 13D/A")
        self.assertEqual(evidence.amendment_no, 9)
        self.assertFalse(evidence.previously_filed)
        self.assertEqual(evidence.previous_accession, "0000929638-21-000927")
        self.assertEqual(evidence.issuer_cik, "0001811210")
        self.assertEqual(evidence.issuer_name, "Lucid Group, Inc.")
        self.assertEqual(
            evidence.share_class, "Class A Common Stock, par value $0.0001 per share"
        )
        self.assertEqual(evidence.cusip, "549498202")
        self.assertEqual(evidence.event_on, date(2026, 4, 28))
        self.assertEqual(evidence.accepted_at, _ACCEPTED)
        self.assertEqual(evidence.accepted_at.utcoffset(), timedelta(0))
        self.assertEqual(evidence.retained_at, _RETAINED)
        self.assertEqual(evidence.known_at, _RETAINED)
        self.assertGreater(evidence.known_at, evidence.accepted_at)
        self.assertEqual(evidence.raw_sha256, _PRIMARY_SOURCE_SHA256)

    def test_four_reporting_persons_in_order(self):
        evidence = _parse()
        persons = evidence.reporting_persons
        self.assertIsInstance(persons, tuple)
        self.assertEqual(
            [p.name for p in persons],
            [
                "Ayar Third Investment Company",
                "Public Investment Fund",
                "Turqi A. Alnowaiser",
                "Yasir Alsalman",
            ],
        )
        self.assertEqual(
            [p.cik for p in persons],
            ["0001874832", "0001767640", None, None],
        )
        self.assertEqual([p.no_cik for p in persons], [False, False, True, True])

    def test_amount_strings_canonical_and_separate(self):
        evidence = _parse()
        ayar = _person(evidence, "Ayar Third Investment Company")
        pif = _person(evidence, "Public Investment Fund")
        turqi = _person(evidence, "Turqi A. Alnowaiser")
        yasir = _person(evidence, "Yasir Alsalman")

        self.assertEqual(ayar.sole_voting_power, "0")
        self.assertEqual(ayar.shared_voting_power, "280188185")
        self.assertEqual(ayar.sole_dispositive_power, "0")
        self.assertEqual(ayar.shared_dispositive_power, "0")
        self.assertEqual(ayar.aggregate_amount_owned, "280188185")
        self.assertEqual(ayar.percent_of_class, "56.69")

        self.assertEqual(pif.sole_voting_power, "804139")
        self.assertEqual(pif.shared_voting_power, "280188185")
        self.assertEqual(pif.sole_dispositive_power, "280992324")
        self.assertEqual(pif.shared_dispositive_power, "0")
        self.assertEqual(pif.aggregate_amount_owned, "280992324")
        self.assertEqual(pif.percent_of_class, "56.85")

        self.assertEqual(turqi.sole_voting_power, "232427")
        self.assertEqual(turqi.shared_voting_power, "280188185")
        self.assertEqual(turqi.aggregate_amount_owned, "280420612")
        self.assertEqual(turqi.percent_of_class, "56.74")

        self.assertEqual(yasir.sole_voting_power, "40145")
        self.assertEqual(yasir.aggregate_amount_owned, "280228330")
        self.assertEqual(yasir.percent_of_class, "56.7")

        aggregates = {p.aggregate_amount_owned for p in evidence.reporting_persons}
        self.assertEqual(
            aggregates,
            {"280188185", "280992324", "280420612", "280228330"},
        )
        self.assertNotEqual(ayar.aggregate_amount_owned, pif.aggregate_amount_owned)
        for person in evidence.reporting_persons:
            for field in (
                person.sole_voting_power,
                person.shared_voting_power,
                person.sole_dispositive_power,
                person.shared_dispositive_power,
                person.aggregate_amount_owned,
                person.percent_of_class,
            ):
                self.assertNotIn("e", field.lower())
                self.assertLessEqual(len(field.replace(".", "", 1)), 30)

    def test_person_flags_and_comments_preserved(self):
        evidence = _parse()
        for person in evidence.reporting_persons:
            self.assertFalse(person.aggregate_exclude_shares)
            self.assertIs(person.legal_proceedings, False)
            self.assertEqual(person.comment, "See Item 5 below")
            self.assertEqual(person.member_of_group, "a")
        self.assertEqual(_person(evidence, "Public Investment Fund").fund_type, "WC")
        self.assertEqual(
            _person(evidence, "Turqi A. Alnowaiser").type_of_reporting_person, "IN"
        )
        self.assertEqual(
            _person(evidence, "Yasir Alsalman").citizenship_or_organization, "T0"
        )

    def test_narratives_carried_as_source_text(self):
        evidence = _parse()
        self.assertTrue(
            evidence.item2_principal_job.startswith(
                "PIF is the sovereign wealth fund of the Kingdom of Saudi Arabia."
            )
        )
        self.assertIn("wholly-owned subsidiary of PIF", evidence.item2_principal_job)
        self.assertIn("390,326,644", evidence.item5_percentage_of_class)
        self.assertIn("804,139 shares", evidence.item5_percentage_of_class)
        self.assertIn("33,258,443", evidence.item5_percentage_of_class)

    def test_result_dataclasses_are_frozen(self):
        evidence = _parse()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            evidence.issuer_cik = "0000000000"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            evidence.reporting_persons[0].cik = "0000000000"

    def test_uppercase_digest_accepted(self):
        evidence = _parse(sha=_digest(_PRIMARY_RAW).upper())
        self.assertEqual(evidence.accession, "0001104659-26-053223")

    def test_retention_equal_to_acceptance_gives_known_at_acceptance(self):
        evidence = _parse(retained=_ACCEPTED)
        self.assertEqual(evidence.known_at, _ACCEPTED)

    def test_optional_comment_absent_returns_none(self):
        evidence = _mutated_parse(
            _swap_block(
                0,
                "        <commentContent>See Item 5 below</commentContent>\n",
                "",
            )
        )
        self.assertIsNone(_person(evidence, "Ayar Third Investment Company").comment)
        self.assertEqual(_person(evidence, "Yasir Alsalman").comment, "See Item 5 below")

    def test_numeric_exactness_beyond_two_power_53(self):
        evidence = _mutated_parse(
            _PRIMARY_TEXT.replace("804139.00", "9007199254740993.00")
        )
        pif = _person(evidence, "Public Investment Fund")
        self.assertEqual(pif.sole_voting_power, "9007199254740993")
        self.assertEqual(int(pif.sole_voting_power), 2 ** 53 + 1)
        self.assertNotEqual(float(pif.sole_voting_power), 9007199254740993)


class RefusalTests(unittest.TestCase):
    """Every malformed, tampered, or ambiguous fixture fails closed."""

    def _expect_refusal(self, text_or_raw):
        raw = (
            text_or_raw.encode("utf-8")
            if isinstance(text_or_raw, str)
            else text_or_raw
        )
        with self.assertRaises(ValueError):
            _parse(raw)

    # --- hash / raw-bytes integrity -------------------------------------------------

    def test_tampered_byte_refused(self):
        tampered = bytearray(_PRIMARY_RAW)
        marker = _PRIMARY_RAW.index(b"Lucid Group, Inc.")
        tampered[marker] = ord("l")
        # The authentic expected digest no longer matches the mutated bytes.
        with self.assertRaises(ValueError):
            _parse(bytes(tampered), sha=_PRIMARY_SOURCE_SHA256)

    def test_wrong_digest_refused(self):
        with self.assertRaises(ValueError):
            _parse(sha="0" * 64)

    def test_malformed_digest_refused(self):
        for bad in ("deadbeef", "g" * 64, "b" * 63, 123, b"ab" * 32):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    _parse(sha=bad)
        with self.assertRaises(ValueError):
            _13D.parse_schedule13d_evidence(
                _PRIMARY_RAW, expected_sha256=None, retained_at=_RETAINED
            )

    def test_raw_type_and_size_refused(self):
        with self.assertRaises(ValueError):
            _13D.parse_schedule13d_evidence(
                _PRIMARY_TEXT, expected_sha256=_digest(_PRIMARY_RAW), retained_at=_RETAINED
            )
        with self.assertRaises(ValueError):
            _13D.parse_schedule13d_evidence(
                b"", expected_sha256=_digest(b""), retained_at=_RETAINED
            )
        with self.assertRaises(ValueError):
            _13D.parse_schedule13d_evidence(
                b"x" * (2 * 1024 * 1024 + 1),
                expected_sha256="a" * 64,
                retained_at=_RETAINED,
            )

    def test_non_utf8_refused(self):
        self._expect_refusal(_PRIMARY_RAW.replace(b"Lucid", b"Luc\xffid", 1))

    def test_byte_order_mark_refused(self):
        self._expect_refusal(b"\xef\xbb\xbf" + _PRIMARY_RAW)

    # --- clock / retention ----------------------------------------------------------

    def test_naive_retained_at_refused(self):
        with self.assertRaises(ValueError):
            _parse(retained=datetime(2026, 10, 19, 19, 23, 43))

    def test_non_utc_retained_at_refused(self):
        offset = timezone(timedelta(hours=1))
        with self.assertRaises(ValueError):
            _parse(retained=datetime(2026, 10, 19, 20, 23, 43, tzinfo=offset))

    def test_acceptance_after_retention_refused(self):
        with self.assertRaises(ValueError):
            _parse(retained=datetime(2026, 4, 30, 22, 26, 23, tzinfo=timezone.utc))

    # --- event / acceptance sanity --------------------------------------------------

    def test_future_event_date_refused(self):
        self._expect_refusal(
            _replace(
                "<dateOfEvent>04/28/2026</dateOfEvent>",
                "<dateOfEvent>05/15/2026</dateOfEvent>",
            )
        )

    def test_malformed_event_date_refused(self):
        self._expect_refusal(
            _replace(
                "<dateOfEvent>04/28/2026</dateOfEvent>",
                "<dateOfEvent>13/45/2026</dateOfEvent>",
            )
        )
        self._expect_refusal(
            _replace(
                "<dateOfEvent>04/28/2026</dateOfEvent>",
                "<dateOfEvent>4/28/2026</dateOfEvent>",
            )
        )

    def test_malformed_acceptance_datetime_refused(self):
        self._expect_refusal(
            _replace(
                "<ACCEPTANCE-DATETIME>20260430182624",
                "<ACCEPTANCE-DATETIME>20260430252624",
            )
        )

    # --- SGML structure -------------------------------------------------------------

    def test_accession_mismatch_refused(self):
        self._expect_refusal(
            _replace(
                "ACCESSION NUMBER:\t\t0001104659-26-053223",
                "ACCESSION NUMBER:\t\t0001104659-26-053224",
            )
        )

    def test_wrong_form_refused(self):
        self._expect_refusal(_PRIMARY_TEXT.replace("SCHEDULE 13D/A", "SCHEDULE 13G"))

    def test_document_type_mismatch_refused(self):
        self._expect_refusal(
            _replace("<TYPE>SCHEDULE 13D/A\n", "<TYPE>SCHEDULE 13D/A-X\n")
        )

    def test_xml_submission_type_mismatch_refused(self):
        self._expect_refusal(
            _replace(
                "<submissionType>SCHEDULE 13D/A</submissionType>",
                "<submissionType>SCHEDULE 13G/A</submissionType>",
            )
        )

    def test_wrong_issuer_cik_refused(self):
        self._expect_refusal(
            _replace(
                "<issuerCIK>0001811210</issuerCIK>",
                "<issuerCIK>0001874832</issuerCIK>",
            )
        )

    def test_dtd_and_entity_declarations_refused(self):
        doctype = '<!DOCTYPE edgarSubmission [<!ENTITY xxe "y">]>'
        self._expect_refusal(
            _replace(
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<?xml version="1.0" encoding="UTF-8"?>' + doctype,
            )
        )

    def test_malformed_xml_refused(self):
        self._expect_refusal(_replace("</edgarSubmission>", ""))

    # --- XML namespace / structure --------------------------------------------------

    def test_lowercase_namespace_refused(self):
        self._expect_refusal(
            _replace(
                "http://www.sec.gov/edgar/schedule13D",
                "http://www.sec.gov/edgar/schedule13d",
            )
        )

    def test_schedule13g_namespace_refused(self):
        self._expect_refusal(
            _replace(
                "http://www.sec.gov/edgar/schedule13D",
                "http://www.sec.gov/edgar/schedule13g",
            )
        )

    def test_unqualified_element_refused(self):
        self._expect_refusal(
            _replace(
                "<amendmentNo>9</amendmentNo>",
                '<amendmentNo xmlns="">9</amendmentNo>',
            )
        )

    def test_nested_identity_leaf_refused(self):
        self._expect_refusal(
            _replace(
                "<issuerName>Lucid Group, Inc.</issuerName>",
                "<issuerName><nested>Lucid Group, Inc.</nested></issuerName>",
                count=2,
            )
        )

    def test_blank_identity_leaf_refused(self):
        self._expect_refusal(
            _replace(
                "</issuerCusips>\n        <issuerName>Lucid Group, Inc.</issuerName>",
                "</issuerCusips>\n        <issuerName>   </issuerName>",
            )
        )

    def test_missing_required_leaf_refused(self):
        self._expect_refusal(
            _replace(
                "</issuerCusips>\n        <issuerName>Lucid Group, Inc.</issuerName>",
                "</issuerCusips>",
            )
        )

    def test_duplicate_issuer_info_refused(self):
        self._expect_refusal(
            _replace(
                "      </issuerInfo>",
                "      </issuerInfo>\n      <issuerInfo>\n"
                "        <issuerCIK>0001811210</issuerCIK>\n"
                "      </issuerInfo>",
            )
        )

    # --- numeric fields -------------------------------------------------------------

    def test_nan_infinity_exponent_negative_percent_refused(self):
        cases = [
            ("<soleVotingPower>0.00</soleVotingPower>",
             "<soleVotingPower>NaN</soleVotingPower>"),
            ("<soleVotingPower>0.00</soleVotingPower>",
             "<soleVotingPower>Infinity</soleVotingPower>"),
            ("<soleVotingPower>0.00</soleVotingPower>",
             "<soleVotingPower>-1</soleVotingPower>"),
            ("<sharedVotingPower>280188185.00</sharedVotingPower>",
             "<sharedVotingPower>2.80188185e8</sharedVotingPower>"),
            ("<percentOfClass>56.69</percentOfClass>",
             "<percentOfClass>100.01</percentOfClass>"),
            ("<percentOfClass>56.69</percentOfClass>",
             "<percentOfClass>NaN</percentOfClass>"),
        ]
        for old, new in cases:
            with self.subTest(new=new):
                self._expect_refusal(_swap_block(0, old, new))

    def test_giant_numeric_refused(self):
        self._expect_refusal(
            _PRIMARY_TEXT.replace("804139.00", "1234567890123456789012345678901.00")
        )

    def test_blank_numeric_refused(self):
        self._expect_refusal(
            _swap_block(
                0,
                "<soleVotingPower>0.00</soleVotingPower>",
                "<soleVotingPower></soleVotingPower>",
            )
        )

    def test_comment_inside_numeric_leaf_is_inert(self):
        # ElementTree drops comments before any value is read, so a comment
        # cannot inject or alter a numeric leaf; the parsed value is unchanged.
        evidence = _mutated_parse(
            _swap_block(
                0,
                "<soleVotingPower>0.00</soleVotingPower>",
                "<soleVotingPower>0.00<!--x--></soleVotingPower>",
            )
        )
        self.assertEqual(
            _person(evidence, "Ayar Third Investment Company").sole_voting_power, "0"
        )

    # --- reporting persons ----------------------------------------------------------

    def test_duplicate_person_identity_refused(self):
        ayar = _person_blocks()[0]
        for variant in (
            ayar,
            ayar.replace("0001874832", "0001111111"),
            ayar.replace("Ayar Third Investment Company", "Ayar Duplicate Entity"),
        ):
            with self.subTest(variant=variant[:60]):
                self._expect_refusal(
                    _replace(
                        "    </reportingPersons>",
                        variant + "\n    </reportingPersons>",
                    )
                )

    def test_person_over_bound_refused(self):
        turqi = _person_blocks()[2]
        extra = (turqi + "\n") * 62
        self._expect_refusal(
            _replace("    </reportingPersons>", extra + "    </reportingPersons>")
        )

    def test_nocik_flag_contradictions_refused(self):
        self._expect_refusal(
            _swap_block(
                2,
                "<reportingPersonNoCIK>Y</reportingPersonNoCIK>",
                "<reportingPersonCIK>0001111111</reportingPersonCIK>\n        "
                "<reportingPersonNoCIK>Y</reportingPersonNoCIK>",
            )
        )
        self._expect_refusal(
            _swap_block(
                0,
                "        <reportingPersonCIK>0001874832</reportingPersonCIK>\n",
                "",
            )
        )

    def test_missing_narrative_fields_refused(self):
        self._expect_refusal(
            re.sub(r"<principalJob>.*?</principalJob>", "", _PRIMARY_TEXT, flags=re.S)
        )
        self._expect_refusal(
            re.sub(
                r"<percentageOfClassSecurities>.*?</percentageOfClassSecurities>",
                "",
                _PRIMARY_TEXT,
                flags=re.S,
            )
        )

    def test_missing_amendment_and_flag_refused(self):
        self._expect_refusal(_replace("      <amendmentNo>9</amendmentNo>\n", ""))
        self._expect_refusal(
            _replace("      <previouslyFiledFlag>false</previouslyFiledFlag>\n", "")
        )

    def test_malformed_previous_accession_refused(self):
        self._expect_refusal(
            _replace(
                "<previousAccessionNumber>0000929638-21-000927</previousAccessionNumber>",
                "<previousAccessionNumber>not-an-accession</previousAccessionNumber>",
            )
        )

    def test_initial_13d_with_amendment_refused(self):
        self._expect_refusal(_PRIMARY_TEXT.replace("SCHEDULE 13D/A", "SCHEDULE 13D"))


class ExistingSchedule13gHelperTests(unittest.TestCase):
    """The included 13G helper must keep its exact prior behavior."""

    def test_namespaces_stay_distinct(self):
        self.assertEqual(
            _13G.SCHEDULE13G_NAMESPACE, "http://www.sec.gov/edgar/schedule13g"
        )
        self.assertEqual(
            _13D.SCHEDULE13D_NAMESPACE, "http://www.sec.gov/edgar/schedule13D"
        )
        self.assertNotEqual(_13G.SCHEDULE13G_NAMESPACE, _13D.SCHEDULE13D_NAMESPACE)

    def test_minimal_13g_still_parses(self):
        raw = _MINIMAL_13G.encode("utf-8")
        evidence = _13G.parse_schedule13g_evidence(
            raw,
            expected_sha256=_digest(raw),
            retained_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(evidence.accession, "0000000000-26-000001")
        self.assertEqual(evidence.issuer_cik, "0000320193")
        self.assertEqual(evidence.issuer_name, "Apple Inc.")
        self.assertEqual(evidence.share_class, "Common Stock")
        self.assertEqual(evidence.cusip, "037833100")
        self.assertEqual(evidence.event_on, date(2026, 1, 10))
        self.assertEqual(
            evidence.accepted_at, datetime(2026, 1, 15, 15, 30, tzinfo=timezone.utc)
        )
        self.assertEqual(evidence.known_at, datetime(2026, 6, 1, tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            _13G.parse_schedule13g_evidence(
                raw,
                expected_sha256="0" * 64,
                retained_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
            )
        with self.assertRaises(ValueError):
            _13G.parse_schedule13g_evidence(
                _PRIMARY_RAW,
                expected_sha256=_digest(_PRIMARY_RAW),
                retained_at=_RETAINED,
            )


if __name__ == "__main__":
    unittest.main()
