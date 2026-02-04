import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Prefetch

from infrastructure.models import (
    Event,
    EventDestinyHardware,
    EventRsvp,
    EventTrack,
    Team,
)


class Command(BaseCommand):
    help = "Export teams and projects for the current event to CSV"

    MAX_PARTICIPANTS = 5
    MAX_DESTINY_HARDWARE = 3

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default="exports",
            help="Directory to save CSV (default: exports)"
        )
        parser.add_argument(
            "--csv-filename",
            default="teams_projects.csv",
            help="CSV filename (default: teams_projects.csv)"
        )

    def handle(self, *args, **options):
        # Get the active event
        event = Event.get_active()
        if not event:
            self.stderr.write(self.style.ERROR("No active event found"))
            return

        self.stdout.write(f"Exporting teams/projects for event: {event.name}")

        # Setup output directory
        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_path = output_dir / options["csv_filename"]

        # Get all teams for the current event
        # Use Prefetch for event-scoped relations to satisfy EventScopedManager
        teams = Team.objects.for_event(event).prefetch_related(
            "attendees",
            Prefetch(
                "event_tracks",
                queryset=EventTrack.objects.for_event(event)
            ),
            Prefetch(
                "event_destiny_hardware",
                queryset=EventDestinyHardware.objects.for_event(event)
            ),
        ).select_related("table", "table__location")

        self.stdout.write(f"Found {teams.count()} teams")

        # Build CSV header
        fieldnames = [
            "team_id",
            "team_number",
            "team_name",
            "table_number",
            "project_name",
            "hardware_hack",
            "community_hack",
            "founders_lab",
            "event_special_track",
            "destiny_hardware_1",
            "destiny_hardware_2",
            "destiny_hardware_3",
            "devpost_url",
            "repository_location",
        ]

        # Add participant columns (name and email for each)
        for i in range(1, self.MAX_PARTICIPANTS + 1):
            fieldnames.append(f"participant_{i}_name")
            fieldnames.append(f"participant_{i}_email")

        # Prepare CSV rows
        csv_rows = []

        for team in teams:
            row = {
                "team_id": team.id,
                "team_number": team.number,
                "team_name": team.name,
                "table_number": team.table.number if team.table else "",
                "project_name": self._get_project_name(team),
                "hardware_hack": "Yes" if team.hardware_hack else "No",
                "community_hack": "Yes" if team.community_hack else "No",
                "founders_lab": "Yes" if team.startup_hack else "No",
                "event_special_track": self._get_event_tracks(team),
                "devpost_url": self._get_submission_location(team),
                "repository_location": self._get_repository_location(team),
            }

            # Add destiny hardware columns
            destiny_hardware = list(team.event_destiny_hardware.all())
            for i in range(self.MAX_DESTINY_HARDWARE):
                col_name = f"destiny_hardware_{i + 1}"
                if i < len(destiny_hardware):
                    row[col_name] = destiny_hardware[i].name
                else:
                    row[col_name] = ""

            # Add participant columns from EventRsvp
            participants = self._get_participant_info(team, event)
            for i in range(self.MAX_PARTICIPANTS):
                name_col = f"participant_{i + 1}_name"
                email_col = f"participant_{i + 1}_email"
                if i < len(participants):
                    row[name_col] = participants[i]["name"]
                    row[email_col] = participants[i]["email"]
                else:
                    row[name_col] = ""
                    row[email_col] = ""

            csv_rows.append(row)

        # Write CSV file
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

        self.stdout.write(self.style.SUCCESS("\nExport complete!"))
        self.stdout.write(f"  CSV saved to: {csv_path}")
        self.stdout.write(f"  Total teams: {len(csv_rows)}")

    def _get_project_name(self, team: Team) -> str:
        """Get project name if the team has a project."""
        try:
            if hasattr(team, "project") and team.project:
                return team.project.name
        except Exception:
            pass
        return ""

    def _get_repository_location(self, team: Team) -> str:
        """Get repository location from the team's project."""
        try:
            if hasattr(team, "project") and team.project:
                return team.project.repository_location or ""
        except Exception:
            pass
        return ""

    def _get_submission_location(self, team: Team) -> str:
        """Get submission location (devpost) from the team's project."""
        try:
            if hasattr(team, "project") and team.project:
                return team.project.submission_location or ""
        except Exception:
            pass
        return ""

    def _get_event_tracks(self, team: Team) -> str:
        """Get event tracks as comma-separated string."""
        tracks = team.event_tracks.all()
        if tracks:
            return ", ".join(track.name for track in tracks)
        return ""

    def _get_participant_info(self, team: Team, event: Event) -> list[dict]:
        """
        Get participant names and emails from EventRsvp.
        Returns list of dicts with 'name' and 'email' keys.
        """
        participants = []
        attendees = team.attendees.all()

        for attendee in attendees:
            # Get EventRsvp for this attendee and event
            rsvp = EventRsvp.objects.for_event(event).filter(
                attendee=attendee
            ).select_related("application").first()

            if rsvp and rsvp.application:
                # Prefer application data
                name = f"{rsvp.application.first_name} {rsvp.application.last_name}"
                email = rsvp.application.email
            else:
                # Fallback to attendee data
                name = f"{attendee.first_name} {attendee.last_name}"
                email = attendee.email

            participants.append({"name": name, "email": email})

            if len(participants) >= self.MAX_PARTICIPANTS:
                break

        return participants