from pathlib import Path

from django.core.management.base import BaseCommand

from infrastructure.models import Event, EventRsvp
from infrastructure.services.attendee_export import (
    PARTICIPATION_CSV_FIELDNAMES,
    ResumeDownloadResult,
    download_resume_to_dir,
    participant_csv_row_from_rsvp,
    participation_class_filter_values,
    resolve_identity_and_employment_from_rsvp,
)
from infrastructure.utils.csv_export import write_csv

_PARTICIPATION_CLASS_CHOICES = ["participant", "mentor", "judge"]


class Command(BaseCommand):
    help = "Export RSVP'd attendees to CSV and optionally download their resumes"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default="exports",
            help="Directory to save CSV and resumes (default: exports)",
        )
        parser.add_argument(
            "--csv-filename",
            default="participants.csv",
            help="CSV filename (default: participants.csv)",
        )
        parser.add_argument(
            "--resumes-dir",
            default="resumes",
            help="Subdirectory name for resumes (default: resumes)",
        )
        parser.add_argument(
            "--include-resumes",
            action="store_true",
            default=False,
            help="Include resumes in the export",
        )
        parser.add_argument(
            "--participation-class",
            nargs="+",
            choices=_PARTICIPATION_CLASS_CHOICES,
            default=["participant"],
            dest="participation_class",
            help=(
                "Filter by participation class. One or more of: "
                "participant, mentor, judge. (default: participant)"
            ),
        )

    def handle(self, *args, **options):
        event = Event.get_active()
        if not event:
            self.stderr.write(self.style.ERROR("No active event found"))
            return

        self.stdout.write(f"Exporting attendees for event: {event.name}")

        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        include_resumes = options["include_resumes"]
        if include_resumes:
            resumes_dir = output_dir / options["resumes_dir"]
            resumes_dir.mkdir(parents=True, exist_ok=True)

        csv_path = output_dir / options["csv_filename"]

        participation_classes = participation_class_filter_values(
            options["participation_class"]
        )
        rsvps = (
            EventRsvp.objects.for_event(event)
            .filter(participation_class__in=participation_classes)
            .select_related("attendee", "application", "application__resume")
        )

        self.stdout.write(f"Found {rsvps.count()} RSVP'd attendees")

        csv_rows = []
        resume_count = 0
        skipped_resumes = 0

        for rsvp in rsvps:
            csv_rows.append(participant_csv_row_from_rsvp(rsvp))
            if include_resumes:
                identity = resolve_identity_and_employment_from_rsvp(rsvp)
                result: ResumeDownloadResult = download_resume_to_dir(
                    identity, resumes_dir
                )
                if result.downloaded_filename:
                    resume_count += 1
                    self.stdout.write(f"  Downloaded: {result.downloaded_filename}")
                else:
                    self.stderr.write(self.style.WARNING(
                        f"  Failed to download resume for {identity.first_name} "
                        f"{identity.last_name}")
                    )
                    if result.error:
                        self.stderr.write(self.style.WARNING(
                            f"  Error: {result.error.message}")
                        )
                    skipped_resumes += 1

        write_csv(csv_path, PARTICIPATION_CSV_FIELDNAMES, csv_rows)

        self.stdout.write(self.style.SUCCESS("\nExport complete!"))
        self.stdout.write(f"  CSV saved to: {csv_path}")
        self.stdout.write(f"  Total attendees: {len(csv_rows)}")
        if include_resumes:
            self.stdout.write(f"  Resumes downloaded: {resume_count}")
            self.stdout.write(f"  Resumes skipped (no file): {skipped_resumes}")
