import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from infrastructure.models import Event, EventRsvp, ParticipationClass


def sanitize_filename(name: str) -> str:
    """Remove/replace characters that are invalid in filenames."""
    # Replace spaces with underscores
    name = name.replace(" ", "_")
    # Remove any characters that aren't alphanumeric, underscore, or hyphen
    name = re.sub(r'[^\w\-]', '', name)
    return name


class Command(BaseCommand):
    help = "Export RSVP'd participants to CSV and download their resumes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default="exports",
            help="Directory to save CSV and resumes (default: exports)"
        )
        parser.add_argument(
            "--csv-filename",
            default="participants.csv",
            help="CSV filename (default: participants.csv)"
        )
        parser.add_argument(
            "--resumes-dir",
            default="resumes",
            help="Subdirectory name for resumes (default: resumes)"
        )
        parser.add_argument(
            "--include-resumes",
            action="store_true",
            default=False,
            help="Include resumes in the export"
        )

    def handle(self, *args, **options):
        # Get the active event
        event = Event.get_active()
        if not event:
            self.stderr.write(self.style.ERROR("No active event found"))
            return

        self.stdout.write(f"Exporting participants for event: {event.name}")

        # Setup output directories
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        include_resumes = options["include_resumes"]
        if include_resumes:
            resumes_dir = output_dir / options["resumes_dir"]
            resumes_dir.mkdir(parents=True, exist_ok=True)

        csv_path = output_dir / options["csv_filename"]

        # Get RSVP'd participants for the current event
        rsvps = EventRsvp.objects.for_event(event).filter(
            participation_class=ParticipationClass.PARTICIPANT
        ).select_related("attendee", "application", "application__resume")

        self.stdout.write(f"Found {rsvps.count()} RSVP'd participants")

        # Prepare CSV data and download resumes
        csv_rows = []
        resume_count = 0
        skipped_resumes = 0

        for rsvp in rsvps:
            application = rsvp.application

            # Get data from application (preferred) or attendee as fallback
            if application:
                first_name = application.first_name
                last_name = application.last_name
                email = application.email
                portfolio = application.portfolio or ""
                secondary_portfolio = application.secondary_portfolio or ""
                student_school = application.student_school or ""
                employer = application.employer or ""
                occupation = application.occupation or ""
                resume = application.resume
                social_media = application.communications_platform_username or ""
            else:
                # Fallback to attendee if no application linked
                attendee = rsvp.attendee
                first_name = attendee.first_name
                last_name = attendee.last_name
                email = attendee.email
                portfolio = ""
                secondary_portfolio = ""
                student_school = ""
                employer = ""
                occupation = ""
                resume = None
                social_media = ""
            # Add to CSV data
            full_name = f"{first_name} {last_name}"
            csv_rows.append({
                "name": full_name,
                "email": email,
                "portfolio": portfolio,
                "secondary_portfolio": secondary_portfolio,
                "student_school": student_school,
                "employer": employer,
                "occupation": occupation,
                "social_media": social_media,
            })

            # Download resume if available and flag is set
            if include_resumes:
                if resume and resume.file:
                    try:
                        # Get original file extension
                        original_name = resume.file.name
                        extension = Path(original_name).suffix or ".pdf"

                        # Create sanitized filename
                        safe_name = sanitize_filename(f"{first_name}_{last_name}")
                        resume_filename = f"{safe_name}{extension}"
                        resume_path = resumes_dir / resume_filename

                        # Handle duplicate filenames
                        counter = 1
                        while resume_path.exists():
                            resume_filename = f"{safe_name}_{counter}{extension}"
                            resume_path = resumes_dir / resume_filename
                            counter += 1

                        # Download the file from storage backend
                        with open(resume_path, "wb") as f:
                            for chunk in resume.file.chunks():
                                f.write(chunk)

                        resume_count += 1
                        self.stdout.write(f"  Downloaded: {resume_filename}")

                    except Exception as e:
                        self.stderr.write(
                            self.style.WARNING(
                                f"  Failed to download resume for {full_name}: {e}"
                            )
                        )
                        skipped_resumes += 1
                else:
                    skipped_resumes += 1

        # Write CSV file
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "name", "email", "portfolio", "secondary_portfolio",
                "social_media", "student_school", "employer", "occupation"
            ])
            writer.writeheader()
            writer.writerows(csv_rows)

        # Summary
        self.stdout.write(self.style.SUCCESS("\nExport complete!"))
        self.stdout.write(f"  CSV saved to: {csv_path}")
        self.stdout.write(f"  Total participants: {len(csv_rows)}")
        if include_resumes:
            self.stdout.write(f"  Resumes downloaded: {resume_count}")
            self.stdout.write(f"  Resumes skipped (no file): {skipped_resumes}")
