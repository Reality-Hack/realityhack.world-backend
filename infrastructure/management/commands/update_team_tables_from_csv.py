import csv
import re
from typing import Optional, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction

from infrastructure.models import Team, Table, Event


class Command(BaseCommand):
    help = "Update team table assignments from a CSV file"

    ID_COL = 'Team ID'
    TABLE_NUMBER_COL = 'Table Number'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_path',
            type=str,
            help='Path to the CSV file containing team-table mappings'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without applying them'
        )

    def parse_table_number(self, table_str: str) -> Optional[int]:
        """
        Parse table number from string, handling formats like:
        - "1" -> 1
        - "71 change to 63" -> 63 (takes the target number)
        - "W401-65" -> 65 (extracts trailing number after dash)
        - "58 ( WILL GET MOVED TO 58)" -> 58
        """
        if not table_str or not table_str.strip():
            return None

        table_str = table_str.strip()

        # Handle "W401-XX" format
        if table_str.upper().startswith('W'):
            match = re.search(r'-(\d+)$', table_str)
            if match:
                return int(match.group(1))

        # Handle "XX change to YY" format
        change_pattern = r'change\s+to\s+(?:table\s+)?(\d+)'
        change_match = re.search(change_pattern, table_str, re.IGNORECASE)
        if change_match:
            return int(change_match.group(1))

        # Extract the first number
        first_num_match = re.match(r'^(\d+)', table_str)
        if first_num_match:
            return int(first_num_match.group(1))

        return None

    def find_team(self, team_id: str, event: Event) -> Tuple[Optional[Team], str]:
        """Find team by ID. Returns (team, error_message)."""
        try:
            team = Team.objects.for_event(event).get(id=team_id)
            return team, ""
        except Team.DoesNotExist:
            return None, f"Team not found: {team_id}"

    def find_table(
        self, table_number: int, team_name: str, event: Event
    ) -> Tuple[Optional[Table], str]:
        """Find table by number. Returns (table, error_message)."""
        try:
            table = Table.objects.for_event(event).get(number=table_number)
            return table, ""
        except Table.DoesNotExist:
            return None, f"Table {table_number} not found for team '{team_name}'"
        except Table.MultipleObjectsReturned:
            return None, f"Multiple tables with number {table_number} found"

    def check_table_conflict(
        self, table: Table, team: Team, table_number: int
    ) -> Optional[str]:
        """Check if table is assigned to another team. Returns warning or None."""
        try:
            existing_team = table.team
            if existing_team and existing_team.id != team.id:
                return (
                    f"Table {table_number} is already assigned to "
                    f"team '{existing_team.name}'. Will reassign to '{team.name}'"
                )
        except Team.DoesNotExist:
            pass
        return None

    def process_row(
        self, row: dict, row_num: int, event: Event, dry_run: bool
    ) -> Tuple[str, str]:
        """
        Process a single CSV row.
        Returns (status, message) where status is 'updated', 'skipped', or 'error'.
        """
        team_id = row.get(self.ID_COL, '').strip()
        table_number_str = row.get(self.TABLE_NUMBER_COL, '').strip()

        if not team_id:
            return 'skipped', f"Row {row_num}: Skipping - no team ID"

        table_number = self.parse_table_number(table_number_str)
        if table_number is None:
            msg = (
                f"Row {row_num}: Skipping team {team_id} - "
                f"invalid table number '{table_number_str}'"
            )
            return 'skipped', msg

        team, error = self.find_team(team_id, event)
        if error:
            return 'error', f"Row {row_num}: {error}"

        table, error = self.find_table(table_number, team.name, event)
        if error:
            return 'error', f"Row {row_num}: {error}"

        conflict_warning = self.check_table_conflict(table, team, table_number)
        if conflict_warning:
            self.stdout.write(self.style.WARNING(f"Row {row_num}: {conflict_warning}"))

        old_table = team.table
        if old_table and old_table.number == table_number:
            msg = f"Row {row_num}: Team '{team.name}' already at table {table_number}"
            return 'skipped', msg

        if not dry_run:
            # Clear existing team's table assignment first (OneToOneField constraint)
            try:
                existing_team = table.team
                if existing_team and existing_team.id != team.id:
                    existing_team.table = None
                    existing_team.save(update_fields=['table', 'updated_at'])
            except Team.DoesNotExist:
                pass

            team.table = table
            team.save(update_fields=['table', 'updated_at'])

        old_table_str = f"table {old_table.number}" if old_table else "no table"
        msg = (
            f"Row {row_num}: Updated team '{team.name}' "
            f"from {old_table_str} to table {table_number}"
        )
        return 'updated', msg

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        dry_run = options['dry_run']
        event = Event.get_active()

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN - no changes will be made\n")
            )

        updated_count = 0
        skipped_count = 0
        error_count = 0

        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    status, message = self.process_row(row, row_num, event, dry_run)

                    if status == 'updated':
                        self.stdout.write(self.style.SUCCESS(message))
                        updated_count += 1
                    elif status == 'skipped':
                        self.stdout.write(message)
                        skipped_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(message))
                        error_count += 1

                if dry_run:
                    transaction.set_rollback(True)

        self.stdout.write("\n" + "=" * 50)
        if updated_count:
            self.stdout.write(self.style.SUCCESS(f"Updated: {updated_count}"))
        else:
            self.stdout.write(f"Updated: {updated_count}")
        self.stdout.write(f"Skipped: {skipped_count}")
        if error_count:
            self.stdout.write(self.style.ERROR(f"Errors: {error_count}"))
        else:
            self.stdout.write(f"Errors: {error_count}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\nDRY RUN - no changes were saved")
            )
