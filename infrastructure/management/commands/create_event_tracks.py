import csv
from typing import List, Dict, Any

from django.core.management.base import BaseCommand
from django.db import transaction

from infrastructure.models import EventTrack, EventDestinyHardware, Event


class Command(BaseCommand):
    help = "Create EventTracks and EventDestinyHardware from a CSV file"

    # CSV column headers
    ORDER_COL = 'Order'
    NAME_COL = 'Track Name'
    CODE_COL = '6-Letter Code'
    TYPE_COL = 'Track Type'

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--csv-path',
            type=str,
            default='tracks.csv',
            help='Path to the CSV file containing track data'
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate the CSV data without creating database entries'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Delete existing EventTracks and EventDestinyHardware for the current event before importing'
        )

    def parse_csv(self, csv_path: str, event: Event) -> List[Dict[str, Any]]:
        """Parse CSV file and return list of track data dictionaries."""
        tracks = []

        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row_num, row in enumerate(reader, start=2):
                order = row.get(self.ORDER_COL, '').strip()
                name = row.get(self.NAME_COL, '').strip()
                code = row.get(self.CODE_COL, '').strip()
                track_type = row.get(self.TYPE_COL, '').strip()

                if not all([order, name, code]):
                    self.stdout.write(
                        self.style.WARNING(f"Row {row_num}: Missing required data, skipping")
                    )
                    continue

                try:
                    order_int = int(order)
                except ValueError:
                    self.stdout.write(
                        self.style.WARNING(f"Row {row_num}: Invalid order '{order}', skipping")
                    )
                    continue

                tracks.append({
                    'order': order_int,
                    'name': name,
                    'code': code,
                    'track_type': track_type,
                    'row_num': row_num,
                    'event': event,
                })

        return tracks

    def handle(self, *args, **options) -> None:
        csv_path: str = options['csv_path']
        validate_only: bool = options['validate_only']
        clear_existing: bool = options['clear_existing']

        event = Event.get_active()
        if not event:
            self.stdout.write(self.style.ERROR("No active event found"))
            return

        self.stdout.write(f"Using event: {event}")

        tracks = self.parse_csv(csv_path, event)

        if not tracks:
            self.stdout.write(self.style.WARNING("No valid tracks found in CSV"))
            return

        # Check for duplicate codes
        codes = [t['code'] for t in tracks]
        if len(codes) != len(set(codes)):
            self.stdout.write(self.style.ERROR("Duplicate codes found in CSV"))
            return

        # Separate by track type
        sponsor_tracks = [t for t in tracks if t['track_type'] == 'Sponsor Track']
        special_tracks = [t for t in tracks if t['track_type'] == 'Special Track']

        if validate_only:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n=== EventDestinyHardware ({len(sponsor_tracks)} Sponsor Tracks) ==="
                )
            )
            for track in sponsor_tracks:
                self.stdout.write(
                    f"  {track['order']}: {track['name']} ({track['code']})"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n=== EventTrack ({len(special_tracks)} Special Tracks) ==="
                )
            )
            for track in special_tracks:
                self.stdout.write(
                    f"  {track['order']}: {track['name']} ({track['code']})"
                )
            return

        with transaction.atomic():
            if clear_existing:
                deleted_tracks, _ = EventTrack.objects.for_event(event).delete()
                deleted_hardware, _ = EventDestinyHardware.objects.for_event(event).delete()
                self.stdout.write(
                    f"Deleted {deleted_tracks} existing tracks, "
                    f"{deleted_hardware} existing destiny hardware"
                )

            # Create EventDestinyHardware for sponsor tracks
            hardware_created = 0
            hardware_updated = 0
            for track in sponsor_tracks:
                obj, created = EventDestinyHardware.objects.for_event(event).update_or_create(
                    code=track['code'],
                    defaults={
                        'name': track['name'],
                        'order': track['order'],
                        'event': event,
                    }
                )
                if created:
                    hardware_created += 1
                else:
                    hardware_updated += 1

            # Create EventTrack for special tracks
            track_created = 0
            track_updated = 0
            for track in special_tracks:
                obj, created = EventTrack.objects.for_event(event).update_or_create(
                    code=track['code'],
                    defaults={
                        'name': track['name'],
                        'order': track['order'],
                        'event': event,
                    }
                )
                if created:
                    track_created += 1
                else:
                    track_updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"EventDestinyHardware: {hardware_created} created, {hardware_updated} updated\n"
                f"EventTrack: {track_created} created, {track_updated} updated"
            )
        )
