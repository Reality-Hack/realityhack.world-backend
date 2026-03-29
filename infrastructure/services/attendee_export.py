import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from infrastructure.models import (
    Application,
    Attendee,
    EventRsvp,
    ParticipationCapacity,
    ParticipationClass,
    SkillProficiency,
    UploadedFile,
)
from infrastructure.utils.csv_export import choice_label, parse_multiselect_values


_PARTICIPATION_CLASS_MAP: dict[str, str] = {
    "participant": ParticipationClass.PARTICIPANT,
    "mentor": ParticipationClass.MENTOR,
    "judge": ParticipationClass.JUDGE,
}

PARTICIPATION_CSV_FIELDNAMES: list[str] = [
    "name", "email", "portfolio", "secondary_portfolio",
    "social_media", "student_school", "employer", "occupation",
]

EMPLOYMENT_SKILLS_CSV_FIELDNAMES: list[str] = [
    "event_name", "event_year", "participation_class",
    "name", "email", "portfolio", "secondary_portfolio", "social_media",
    "participation_capacity", "student_school", "student_field_of_study",
    "employer", "occupation", "industry",
    "specialized_expertise", "other_skills_experiences",
    "digital_designer_skills", "event_skills",
]


def sanitize_filename(name: str) -> str:
    """Remove/replace characters that are invalid in filenames."""
    name = name.replace(" ", "_")
    return re.sub(r"[^\w\-]", "", name)


def participation_class_filter_values(cli_choices: Sequence[str]) -> list[str]:
    """Map CLI choice strings (participant/mentor/judge)"""
    """ to ParticipationClass values."""
    return [
        _PARTICIPATION_CLASS_MAP[c]
        for c in cli_choices
        if c in _PARTICIPATION_CLASS_MAP
    ] or [ParticipationClass.PARTICIPANT]


@dataclass
class RsvpIdentityEmployment:
    first_name: str
    last_name: str
    email: str
    portfolio: str
    secondary_portfolio: str
    student_school: str
    employer: str
    occupation: str
    social_media: str
    resume: UploadedFile | None


def resolve_identity_and_employment_from_rsvp(
    rsvp: EventRsvp,
) -> RsvpIdentityEmployment:
    """Resolve identity and basic employment fields from an RSVP.

    Prefers Application fields when present; falls back to the linked Attendee.
    """
    application: Application | None = rsvp.application
    if application:
        return RsvpIdentityEmployment(
            first_name=application.first_name,
            last_name=application.last_name,
            email=application.email,
            portfolio=application.portfolio or "",
            secondary_portfolio=application.secondary_portfolio or "",
            student_school=application.student_school or "",
            employer=application.employer or "",
            occupation=application.occupation or "",
            social_media=application.communications_platform_username or "",
            resume=application.resume,
        )

    attendee: Attendee = rsvp.attendee
    return RsvpIdentityEmployment(
        first_name=attendee.first_name,
        last_name=attendee.last_name,
        email=attendee.email,
        portfolio="",
        secondary_portfolio="",
        student_school="",
        employer="",
        occupation="",
        social_media="",
        resume=None,
    )


@dataclass
class ResumeDownloadResult:
    downloaded_filename: str | None
    error: Exception | None


def download_resume_to_dir(
    identity: RsvpIdentityEmployment,
    resumes_dir: Path,
) -> ResumeDownloadResult:
    """Download an attendee's resume into resumes_dir.

    Returns a ResumeDownloadResult where:
    - downloaded_filename is set on success
    - error is set when the resume exists but the download failed
    - both None means the RSVP had no resume file to download
    """
    resume = identity.resume
    if not (resume and resume.file):
        return ResumeDownloadResult(downloaded_filename=None, error=None)

    try:
        extension = Path(resume.file.name).suffix or ".pdf"
        safe_name = sanitize_filename(f"{identity.first_name}_{identity.last_name}")
        filename = f"{safe_name}{extension}"
        dest = resumes_dir / filename

        counter = 1
        while dest.exists():
            filename = f"{safe_name}_{counter}{extension}"
            dest = resumes_dir / filename
            counter += 1

        with open(dest, "wb") as f:
            for chunk in resume.file.chunks():
                f.write(chunk)

        return ResumeDownloadResult(downloaded_filename=filename, error=None)

    except Exception as exc:
        return ResumeDownloadResult(downloaded_filename=None, error=exc)


def participant_csv_row_from_rsvp(rsvp: EventRsvp) -> dict[str, str]:
    """Build a CSV row matching the original export_rsvp_participants columns."""
    identity = resolve_identity_and_employment_from_rsvp(rsvp)
    return {
        "name": f"{identity.first_name} {identity.last_name}",
        "email": identity.email,
        "portfolio": identity.portfolio,
        "secondary_portfolio": identity.secondary_portfolio,
        "social_media": identity.social_media,
        "student_school": identity.student_school,
        "employer": identity.employer,
        "occupation": identity.occupation,
    }


def employment_skills_csv_row_from_rsvp(
    rsvp: EventRsvp,
    skill_proficiencies: list[SkillProficiency],
) -> dict[str, str]:
    """Build an extended CSV row with event context, employment, and skills fields.

    Pass pre-fetched skill_proficiencies for this (attendee, event) pair to
    avoid N+1 queries.
    """
    identity = resolve_identity_and_employment_from_rsvp(rsvp)
    application: Application | None = rsvp.application

    if application:
        industry_str = "; ".join(parse_multiselect_values(application.industry))
        digital_designer_skills_str = "; ".join(
            choice_label(Application.DigitalDesignerProficientSkills.choices, key)
            for key in parse_multiselect_values(application.digital_designer_skills)
        )
        participation_capacity_label = (
            choice_label(
                ParticipationCapacity.choices,
                application.participation_capacity
            )
            if application.participation_capacity
            else "N/A"
        )
        student_field_of_study = application.student_field_of_study or ""
        specialized_expertise = application.specialized_expertise or ""
        other_skills_experiences = application.other_skills_experiences or ""
    else:
        industry_str = ""
        digital_designer_skills_str = ""
        participation_capacity_label = ""
        student_field_of_study = ""
        specialized_expertise = ""
        other_skills_experiences = ""

    event_skills = "; ".join(
        f"{sp.skill.name} ({sp.get_proficiency_display()})"
        for sp in skill_proficiencies
    )

    return {
        "event_name": rsvp.event.name,
        "event_year": str(rsvp.event.start_date.year),
        "participation_class": rsvp.get_participation_class_display(),
        "name": f"{identity.first_name} {identity.last_name}",
        "email": identity.email,
        "portfolio": identity.portfolio,
        "secondary_portfolio": identity.secondary_portfolio,
        "social_media": identity.social_media,
        "participation_capacity": participation_capacity_label,
        "student_school": identity.student_school,
        "student_field_of_study": student_field_of_study,
        "employer": identity.employer,
        "occupation": identity.occupation,
        "industry": industry_str,
        "specialized_expertise": specialized_expertise,
        "other_skills_experiences": other_skills_experiences,
        "digital_designer_skills": digital_designer_skills_str,
        "event_skills": event_skills,
    }
