from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand

from infrastructure.models import EventRsvp, SkillProficiency
from infrastructure.services.attendee_export import (
    EMPLOYMENT_SKILLS_CSV_FIELDNAMES,
    employment_skills_csv_row_from_rsvp,
    participation_class_filter_values,
)
from infrastructure.utils.csv_export import write_csv

_PARTICIPATION_CLASS_CHOICES = ["participant", "mentor", "judge"]


class Command(BaseCommand):
    help = (
        "Export employment and skills data for attendees across all events to CSV. "
        "Each row represents one RSVP (one person in one event year)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default="exports",
            help="Directory to save the CSV (default: exports)",
        )
        parser.add_argument(
            "--csv-filename",
            default="attendees_employment_skills.csv",
            help="CSV filename (default: attendees_employment_skills.csv)",
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
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / options["csv_filename"]

        participation_classes = participation_class_filter_values(
            options["participation_class"]
        )

        rsvps = list(
            EventRsvp.objects.all_events()
            .filter(participation_class__in=participation_classes)
            .select_related("attendee", "application", "event")
            .order_by("event__start_date", "attendee__email")
        )

        self.stdout.write(f"Found {len(rsvps)} RSVPs across all events")

        skill_lookup = self._build_skill_lookup(rsvps)

        rows = [
            employment_skills_csv_row_from_rsvp(
                rsvp,
                skill_lookup[(rsvp.attendee_id, rsvp.event_id)],
            )
            for rsvp in rsvps
        ]

        write_csv(csv_path, EMPLOYMENT_SKILLS_CSV_FIELDNAMES, rows)

        self.stdout.write(self.style.SUCCESS("\nExport complete!"))
        self.stdout.write(f"  CSV saved to: {csv_path}")
        self.stdout.write(f"  Total rows: {len(rows)}")

    def _build_skill_lookup(
        self, rsvps: list[EventRsvp]
    ) -> defaultdict[tuple, list[SkillProficiency]]:
        """Fetch all relevant SkillProficiency rows in one query and group by
        (attendee_id, event_id) for O(1) lookup during row building."""
        attendee_ids = {rsvp.attendee_id for rsvp in rsvps}
        event_ids = {rsvp.event_id for rsvp in rsvps}

        proficiencies = (
            SkillProficiency.objects.all_events()
            .filter(attendee_id__in=attendee_ids, event_id__in=event_ids)
            .select_related("skill")
        )

        lookup: defaultdict[tuple, list[SkillProficiency]] = defaultdict(list)
        for sp in proficiencies:
            lookup[(sp.attendee_id, sp.event_id)].append(sp)

        return lookup
