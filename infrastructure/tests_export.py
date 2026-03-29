"""Unit tests for the attendee export service and CSV utilities."""
import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from infrastructure.services.attendee_export import (
    ResumeDownloadResult,
    RsvpIdentityEmployment,
    download_resume_to_dir,
    employment_skills_csv_row_from_rsvp,
    participant_csv_row_from_rsvp,
    participation_class_filter_values,
    resolve_identity_and_employment_from_rsvp,
    sanitize_filename,
)
from infrastructure.utils.csv_export import (
    choice_label,
    parse_multiselect_values,
    write_csv,
)

# ---------------------------------------------------------------------------
# infrastructure.utils.csv_export
# ---------------------------------------------------------------------------


class TestWriteCsv(unittest.TestCase):
    def test_writes_header_and_rows(self):
        rows = [{"name": "Alice", "email": "alice@example.com"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.csv"
            write_csv(path, ["name", "email"], rows)

            with open(path, newline="", encoding="utf-8") as f:
                reader = list(csv.DictReader(f))

        self.assertEqual(len(reader), 1)
        self.assertEqual(reader[0]["name"], "Alice")
        self.assertEqual(reader[0]["email"], "alice@example.com")

    def test_empty_rows_writes_header_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "out.csv"
            write_csv(path, ["name"], [])

            with open(path, newline="", encoding="utf-8") as f:
                content = f.read()

        self.assertIn("name", content)
        lines = [line for line in content.splitlines() if line]
        self.assertEqual(len(lines), 1)


class TestParseMultiselectValues(unittest.TestCase):
    def test_none_returns_empty(self):
        self.assertEqual(parse_multiselect_values(None), [])

    def test_empty_string_returns_empty(self):
        self.assertEqual(parse_multiselect_values(""), [])

    def test_comma_separated_string(self):
        self.assertEqual(parse_multiselect_values("A,B,C"), ["A", "B", "C"])

    def test_string_with_spaces(self):
        self.assertEqual(parse_multiselect_values("A, B , C"), ["A", "B", "C"])

    def test_list_passthrough(self):
        self.assertEqual(parse_multiselect_values(["A", "B"]), ["A", "B"])

    def test_single_value(self):
        self.assertEqual(parse_multiselect_values("A"), ["A"])


class TestChoiceLabel(unittest.TestCase):
    _CHOICES = [("A", "Apple"), ("B", "Banana"), ("C", "Cherry")]

    def test_returns_label_for_known_key(self):
        self.assertEqual(choice_label(self._CHOICES, "B"), "Banana")

    def test_returns_key_for_unknown_key(self):
        self.assertEqual(choice_label(self._CHOICES, "Z"), "Z")

    def test_returns_first_match(self):
        choices = [("A", "Apple"), ("A", "Avocado")]
        self.assertEqual(choice_label(choices, "A"), "Apple")


# ---------------------------------------------------------------------------
# infrastructure.services.attendee_export
# ---------------------------------------------------------------------------


class TestSanitizeFilename(unittest.TestCase):
    def test_replaces_spaces_with_underscores(self):
        self.assertEqual(sanitize_filename("John Doe"), "John_Doe")

    def test_removes_special_characters(self):
        self.assertEqual(sanitize_filename("file!@#$.txt"), "filetxt")

    def test_keeps_hyphens_and_underscores(self):
        self.assertEqual(sanitize_filename("my-file_name"), "my-file_name")

    def test_empty_string(self):
        self.assertEqual(sanitize_filename(""), "")


class TestParticipationClassFilterValues(unittest.TestCase):
    def test_participant_maps_to_P(self):
        self.assertEqual(participation_class_filter_values(["participant"]), ["P"])

    def test_mentor_maps_to_M(self):
        self.assertEqual(participation_class_filter_values(["mentor"]), ["M"])

    def test_judge_maps_to_J(self):
        self.assertEqual(participation_class_filter_values(["judge"]), ["J"])

    def test_multiple_classes(self):
        result = participation_class_filter_values(["participant", "mentor"])
        self.assertEqual(result, ["P", "M"])

    def test_unknown_choice_is_ignored(self):
        result = participation_class_filter_values(["participant", "volunteer"])
        self.assertEqual(result, ["P"])

    def test_empty_input(self):
        self.assertEqual(participation_class_filter_values([]), [])


def _make_rsvp_with_application(**app_kwargs) -> MagicMock:
    """Return a mock EventRsvp whose application has the given field values."""
    application = MagicMock()
    application.first_name = app_kwargs.get("first_name", "Jane")
    application.last_name = app_kwargs.get("last_name", "Smith")
    application.email = app_kwargs.get("email", "jane@example.com")
    application.portfolio = app_kwargs.get(
        "portfolio", "https://portfolio.example.com"
    )
    application.secondary_portfolio = app_kwargs.get("secondary_portfolio", "")
    application.student_school = app_kwargs.get("student_school", "MIT")
    application.employer = app_kwargs.get("employer", "Acme Corp")
    application.occupation = app_kwargs.get("occupation", "Engineer")
    application.communications_platform_username = app_kwargs.get(
        "social_media", "jane#1234"
    )
    application.resume = app_kwargs.get("resume", None)
    application.industry = app_kwargs.get("industry", "")
    application.digital_designer_skills = app_kwargs.get(
        "digital_designer_skills", ""
    )
    application.participation_capacity = app_kwargs.get("participation_capacity", "P")
    application.student_field_of_study = app_kwargs.get("student_field_of_study", "CS")
    application.specialized_expertise = app_kwargs.get("specialized_expertise", "XR")
    application.other_skills_experiences = app_kwargs.get(
        "other_skills_experiences", "Unity"
    )

    rsvp = MagicMock()
    rsvp.application = application
    rsvp.get_participation_class_display.return_value = "Participant"
    rsvp.event.name = "Reality Hack 2025"
    rsvp.event.start_date.year = 2025
    return rsvp


def _make_rsvp_without_application() -> MagicMock:
    """Return a mock EventRsvp with no application (attendee fallback)."""
    attendee = MagicMock()
    attendee.first_name = "Bob"
    attendee.last_name = "Jones"
    attendee.email = "bob@example.com"

    rsvp = MagicMock()
    rsvp.application = None
    rsvp.attendee = attendee
    rsvp.get_participation_class_display.return_value = "Mentor"
    rsvp.event.name = "Reality Hack 2024"
    rsvp.event.start_date.year = 2024
    return rsvp


class TestResolveIdentityAndEmployment(unittest.TestCase):
    def test_prefers_application_fields(self):
        rsvp = _make_rsvp_with_application()
        result = resolve_identity_and_employment_from_rsvp(rsvp)

        self.assertIsInstance(result, RsvpIdentityEmployment)
        self.assertEqual(result.first_name, "Jane")
        self.assertEqual(result.last_name, "Smith")
        self.assertEqual(result.email, "jane@example.com")
        self.assertEqual(result.employer, "Acme Corp")
        self.assertEqual(result.occupation, "Engineer")
        self.assertEqual(result.social_media, "jane#1234")

    def test_falls_back_to_attendee_when_no_application(self):
        rsvp = _make_rsvp_without_application()
        result = resolve_identity_and_employment_from_rsvp(rsvp)

        self.assertEqual(result.first_name, "Bob")
        self.assertEqual(result.last_name, "Jones")
        self.assertEqual(result.email, "bob@example.com")
        self.assertEqual(result.employer, "")
        self.assertEqual(result.occupation, "")
        self.assertIsNone(result.resume)

    def test_none_portfolio_becomes_empty_string(self):
        rsvp = _make_rsvp_with_application(portfolio=None, secondary_portfolio=None)
        result = resolve_identity_and_employment_from_rsvp(rsvp)
        self.assertEqual(result.portfolio, "")
        self.assertEqual(result.secondary_portfolio, "")


class TestParticipantCsvRowFromRsvp(unittest.TestCase):
    def test_returns_expected_keys(self):
        rsvp = _make_rsvp_with_application()
        row = participant_csv_row_from_rsvp(rsvp)

        self.assertIn("name", row)
        self.assertIn("email", row)
        self.assertIn("portfolio", row)
        self.assertIn("secondary_portfolio", row)
        self.assertIn("social_media", row)
        self.assertIn("student_school", row)
        self.assertIn("employer", row)
        self.assertIn("occupation", row)

    def test_name_concatenated(self):
        rsvp = _make_rsvp_with_application(first_name="Alice", last_name="Wonder")
        row = participant_csv_row_from_rsvp(rsvp)
        self.assertEqual(row["name"], "Alice Wonder")

    def test_fallback_row_has_empty_employment_fields(self):
        rsvp = _make_rsvp_without_application()
        row = participant_csv_row_from_rsvp(rsvp)
        self.assertEqual(row["employer"], "")
        self.assertEqual(row["occupation"], "")


class TestEmploymentSkillsCsvRowFromRsvp(unittest.TestCase):
    def _make_skill_proficiency(
        self,
        skill_name: str,
        proficiency_display: str,
    ) -> MagicMock:
        sp = MagicMock()
        sp.skill.name = skill_name
        sp.get_proficiency_display.return_value = proficiency_display
        return sp

    def test_includes_event_context(self):
        rsvp = _make_rsvp_with_application()
        row = employment_skills_csv_row_from_rsvp(rsvp, [])
        self.assertEqual(row["event_name"], "Reality Hack 2025")
        self.assertEqual(row["event_year"], "2025")
        self.assertEqual(row["participation_class"], "Participant")

    def test_skills_formatted_as_semicolon_list(self):
        rsvp = _make_rsvp_with_application()
        proficiencies = [
            self._make_skill_proficiency("Unity", "Proficient"),
            self._make_skill_proficiency("Python", "Competent"),
        ]
        row = employment_skills_csv_row_from_rsvp(rsvp, proficiencies)
        self.assertEqual(row["event_skills"], "Unity (Proficient); Python (Competent)")

    def test_empty_skills_list(self):
        rsvp = _make_rsvp_with_application()
        row = employment_skills_csv_row_from_rsvp(rsvp, [])
        self.assertEqual(row["event_skills"], "")

    def test_no_application_yields_empty_skill_fields(self):
        rsvp = _make_rsvp_without_application()
        row = employment_skills_csv_row_from_rsvp(rsvp, [])
        self.assertEqual(row["employer"], "")
        self.assertEqual(row["industry"], "")
        self.assertEqual(row["digital_designer_skills"], "")
        self.assertEqual(row["participation_capacity"], "")

    def test_industry_as_semicolon_list(self):
        rsvp = _make_rsvp_with_application(industry="Tech,Healthcare")
        row = employment_skills_csv_row_from_rsvp(rsvp, [])
        self.assertEqual(row["industry"], "Tech; Healthcare")


def _make_identity(**kwargs) -> RsvpIdentityEmployment:
    return RsvpIdentityEmployment(
        first_name=kwargs.get("first_name", "Jane"),
        last_name=kwargs.get("last_name", "Smith"),
        email="jane@example.com",
        portfolio="",
        secondary_portfolio="",
        student_school="",
        employer="",
        occupation="",
        social_media="",
        resume=kwargs.get("resume", None),
    )


class TestDownloadResumeToDir(unittest.TestCase):
    def test_skipped_when_no_resume(self):
        identity = _make_identity(resume=None)
        with tempfile.TemporaryDirectory() as tmpdir:
            result: ResumeDownloadResult = download_resume_to_dir(
                identity, Path(tmpdir)
            )
        self.assertIsNone(result.downloaded_filename)
        self.assertIsNone(result.error)

    def test_skipped_when_resume_has_no_file(self):
        resume = MagicMock()
        resume.file = None
        identity = _make_identity(resume=resume)
        with tempfile.TemporaryDirectory() as tmpdir:
            result = download_resume_to_dir(identity, Path(tmpdir))
        self.assertIsNone(result.downloaded_filename)
        self.assertIsNone(result.error)

    def test_downloads_file_and_returns_filename(self):
        resume = MagicMock()
        resume.file.name = "original_cv.pdf"
        resume.file.chunks.return_value = [b"pdf content"]
        identity = _make_identity(first_name="Jane", last_name="Smith", resume=resume)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = download_resume_to_dir(identity, Path(tmpdir))
            saved = Path(tmpdir) / result.downloaded_filename
            self.assertIsNotNone(result.downloaded_filename)
            self.assertIsNone(result.error)
            self.assertTrue(saved.exists())
            self.assertEqual(saved.read_bytes(), b"pdf content")

    def test_deduplicates_filename_when_destination_exists(self):
        resume = MagicMock()
        resume.file.name = "cv.pdf"
        resume.file.chunks.return_value = [b"data"]
        identity = _make_identity(first_name="Jane", last_name="Smith", resume=resume)

        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir)
            (dest / "Jane_Smith.pdf").write_bytes(b"existing")
            result = download_resume_to_dir(identity, dest)

        self.assertEqual(result.downloaded_filename, "Jane_Smith_1.pdf")
        self.assertIsNone(result.error)

    def test_returns_error_on_failure(self):
        resume = MagicMock()
        resume.file.name = "cv.pdf"
        resume.file.chunks.side_effect = OSError("disk full")
        identity = _make_identity(resume=resume)

        with tempfile.TemporaryDirectory() as tmpdir:
            result = download_resume_to_dir(identity, Path(tmpdir))

        self.assertIsNone(result.downloaded_filename)
        self.assertIsInstance(result.error, OSError)


if __name__ == "__main__":
    unittest.main()
