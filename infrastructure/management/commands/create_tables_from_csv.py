import csv
from typing import Optional, Tuple

from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from django.db import transaction

from infrastructure.models import Table, Location, Event


class Command(BaseCommand):
    help = "Create tables from a CSV file"
    event = Event.get_active()
    # CSV column headers
    BUILDING_COL = 'Building'
    ROOM_COL = 'Room'
    TABLE_RANGE_COL = 'Table Number Range'
    NOTES_COL = 'Notes'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the CSV file containing table data')
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate the CSV data without creating database entries'
        )

    def parse_table_range(self, range_str: str) -> Optional[Tuple[int, int]]:
        """Parse a table range string (e.g., '1-48') into a tuple of (start, end) numbers."""
        if not range_str or range_str.upper() == 'N/A':
            return None

        try:
            start, end = map(int, range_str.split('-'))
            return (start, end)
        except ValueError:
            return None

    def normalize_building(self, building: str) -> str:
        """Normalize building names to match model choices."""
        building = building.strip().upper()
        building_map = {
            'WALKER': 'WK',
            'STATA': 'ST',
            # Add more mappings as needed
        }
        return building_map.get(building, building)

    def normalize_room(self, room: str) -> str:
        """Normalize room names to match model choices."""
        room = room.strip().upper()
        room_map = {
            'MORSS HALL': 'MH',
            '32-124': '24',
            '32-144': '44',
            '32-141': '41',
            '32-155': '55',
            'ATLANTIS': 'AT',
            'NEPTUNE': 'NE',
            # Add more mappings as needed
        }
        return room_map.get(room, room)

    def validate_location(self, building: str, room: str) -> Optional[str]:
        """Validate that a Location object can be created with the given data."""
        try:
            normalized_building = self.normalize_building(building)
            normalized_room = self.normalize_room(room)
            location = Location(building=normalized_building, room=normalized_room, event=self.event)
            location.full_clean()
            return None
        except ValidationError as e:
            return f"Location validation error: {e}"

    def validate_table(self, number: int, location: Location) -> Optional[str]:
        """Validate that a Table object can be created with the given data."""
        try:
            table = Table(number=number, location=location, event=self.event)
            # Skip foreign key validation during the dry run
            table.full_clean(exclude=['location'])
            return None
        except ValidationError as e:
            return f"Table validation error: {e}"

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        print(csv_path)
        validate_only = options['validate_only']

        with open(csv_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            rows_to_process = []
            total_tables = 0
            validation_errors = []

            # First pass: validate all data
            for row_num, row in enumerate(reader, start=2):
                table_range = self.parse_table_range(row[self.TABLE_RANGE_COL])

                if not table_range:
                    self.stdout.write(f"Skipping row {row_num}: No valid table range found")
                    continue

                if not row[self.BUILDING_COL] or not row[self.ROOM_COL]:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Row {row_num}: Missing building or room information"
                        )
                    )
                    continue

                # Validate Location
                location_error = self.validate_location(
                    row[self.BUILDING_COL],
                    row[self.ROOM_COL]
                )
                if location_error:
                    validation_errors.append(f"Row {row_num}: {location_error}")
                    continue

                # Create temporary location for table validation
                temp_location = Location(
                    building=row[self.BUILDING_COL],
                    room=row[self.ROOM_COL]
                )

                # Validate each table in the range
                start_num, end_num = table_range
                table_errors = []
                for table_num in range(start_num, end_num + 1):
                    table_error = self.validate_table(table_num, temp_location)
                    if table_error:
                        table_errors.append(f"Table {table_num}: {table_error}")

                if table_errors:
                    validation_errors.append(
                        f"Row {row_num}: Table validation errors:\n" +
                        "\n".join(f"  - {e}" for e in table_errors)
                    )
                    continue

                num_tables = end_num - start_num + 1
                total_tables += num_tables

                rows_to_process.append({
                    'building': row[self.BUILDING_COL],
                    'room': row[self.ROOM_COL],
                    'table_range': table_range,
                    'notes': row.get(self.NOTES_COL, ''),
                    'num_tables': num_tables
                })

            if validation_errors:
                self.stdout.write(self.style.ERROR("\nValidation errors found:"))
                for error in validation_errors:
                    self.stdout.write(self.style.ERROR(error))
                return

            if validate_only:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\nValidation complete. Found {len(rows_to_process)} valid rows to process"
                    )
                )
                # Output validation details
                self.stdout.write("\nTables to be created:")
                for row in rows_to_process:
                    start_num, end_num = row['table_range']
                    self.stdout.write(
                        f"Building: {row['building']}, Room: {row['room']}, "
                        f"Tables: {start_num}-{end_num} ({row['num_tables']} tables)"
                        + (f", Notes: {row['notes']}" if row['notes'] else "")
                    )
                self.stdout.write(f"\nTotal tables to be created: {total_tables}")
                return

            # Second pass: create database entries
            with transaction.atomic():
                for row in rows_to_process:
                    location, _ = Location.objects.for_event(self.event).get_or_create(
                        building=self.normalize_building(row['building']),
                        room=self.normalize_room(row['room']),
                        event=self.event
                    )

                    start_num, end_num = row['table_range']
                    for table_num in range(start_num, end_num + 1):
                        Table.objects.create(
                            number=table_num,
                            location=location,
                            event=self.event
                        )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully processed {len(rows_to_process)} rows and created {total_tables} tables"
                )
            )
