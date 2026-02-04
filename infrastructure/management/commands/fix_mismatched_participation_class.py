from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from infrastructure.models import EventRsvp, Event, ParticipationClass
from infrastructure.keycloak import KeycloakClient, EVENT_YEAR
import requests
import json
import csv


class Command(BaseCommand):
    help = (
        'Fix mismatched RSVP participation classes and update '
        'Keycloak roles'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making changes',
        )
        parser.add_argument(
            '--output',
            type=str,
            default='./mismatched_rsvps_log.csv',
            help='Path to output CSV file (default: ./mismatched_rsvps_log.csv)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        output_file = options['output']

        if dry_run:
            msg = 'DRY RUN MODE - No changes will be made'
            self.stdout.write(self.style.WARNING(msg))

        current_event = Event.get_active()
        rsvps = EventRsvp.objects.for_event(current_event).all()

        keycloak_client = None if dry_run else KeycloakClient()

        stats = {'mismatched': 0, 'fixed': 0, 'skipped': 0, 'errored': 0}
        csv_rows = []

        for rsvp in rsvps:
            self._process_rsvp(
                rsvp, keycloak_client, dry_run, stats, csv_rows
            )

        self._write_csv(output_file, csv_rows, dry_run)
        self._print_summary(stats, dry_run, output_file)

    def _process_rsvp(self, rsvp, keycloak_client, dry_run, stats, csv_rows):
        """Process a single RSVP, checking and fixing if mismatched."""
        application = rsvp.application

        # Skip RSVPs without an application
        if application is None:
            return

        if application.participation_class == rsvp.participation_class:
            return

        stats['mismatched'] += 1
        attendee = rsvp.attendee

        self._print_mismatch_info(application, rsvp, attendee)

        # Prepare CSV row data
        row_data = {
            'app_id': str(application.id),
            'rsvp_id': str(rsvp.id),
            'attendee_id': str(attendee.id),
            'first_name': application.first_name,
            'last_name': application.last_name,
            'email': application.email,
            'old_rsvp_class': rsvp.participation_class,
            'app_class': application.participation_class,
            'attendee_class': attendee.participation_class,
            'attendee_updated_at': (
                attendee.updated_at.isoformat() if attendee.updated_at else ''
            ),
            'attendee_created_at': (
                attendee.created_at.isoformat() if attendee.created_at else ''
            ),
            'rsvp_created_at': rsvp.created_at.isoformat() if rsvp.created_at else '',
            'processed_at': timezone.now().isoformat(),
            'status': 'pending',
        }

        if dry_run:
            status = self._handle_dry_run(attendee, application, stats)
            row_data['status'] = status
        else:
            status = self._handle_fix(
                keycloak_client, rsvp, attendee, application, stats
            )
            row_data['status'] = status

        csv_rows.append(row_data)

    def _print_mismatch_info(self, application, rsvp, attendee):
        """Print information about a mismatched RSVP."""
        self.stdout.write(
            f"\n{'='*80}\n"
            f"Mismatch found for: {application.email}\n"
            f"  Current RSVP class: "
            f"{rsvp.get_participation_class_display()}\n"
            f"  Application class: "
            f"{application.get_participation_class_display()}\n"
            f"  Attendee class: "
            f"{attendee.get_participation_class_display()}\n"
            f"  Attendee updated at: "
            f"{attendee.updated_at.isoformat() if attendee.updated_at else ''}\n"
            f"  Attendee created at: "
            f"{attendee.created_at.isoformat() if attendee.created_at else ''}\n"
        )

    def _handle_dry_run(self, attendee, application, stats):
        """Handle dry-run mode for a mismatched RSVP. Returns status string."""
        if not attendee.authentication_id:
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ [DRY RUN] Would skip - no "
                    f"authentication_id for {attendee.email}"
                )
            )
            stats['skipped'] += 1
            return 'would_skip_no_auth'
        else:
            role_name = self._get_role_name(application.participation_class)
            self.stdout.write(
                self.style.WARNING(
                    f"  [DRY RUN] Would update RSVP and assign "
                    f"role: {role_name}"
                )
            )
            return 'would_fix'

    def _handle_fix(self, keycloak_client, rsvp, attendee, application, stats):
        """Attempt to fix a mismatched RSVP. Returns status string."""
        try:
            self._fix_mismatch(keycloak_client, rsvp, attendee, application)
            stats['fixed'] += 1
            return 'fixed'
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"  ✗ Error fixing {application.email}: {e}"
                )
            )
            stats['errored'] += 1
            return f'error: {str(e)}'

    def _write_csv(self, output_file, csv_rows, dry_run):
        """Write the CSV log file."""
        if not csv_rows:
            self.stdout.write(
                self.style.WARNING('\nNo mismatched RSVPs found - no CSV written')
            )
            return

        fieldnames = [
            'app_id', 'rsvp_id', 'attendee_id',
            'first_name', 'last_name', 'email',
            'old_rsvp_class', 'app_class', 'attendee_class',
            'rsvp_created_at', 'processed_at', 'status',
            'attendee_updated_at', 'attendee_created_at'
        ]

        # Add suffix to filename if dry-run
        if dry_run:
            if output_file.endswith('.csv'):
                output_file = output_file[:-4] + '_dryrun.csv'
            else:
                output_file = output_file + '_dryrun.csv'

        with open(output_file, mode='w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)

        self.stdout.write(
            self.style.SUCCESS(f'\nCSV log written to: {output_file}')
        )

    def _print_summary(self, stats, dry_run, output_file):
        """Print the final summary of operations."""
        self.stdout.write(
            f"\n{'='*80}\n"
            f"Summary:\n"
            f"  Total mismatched RSVPs: {stats['mismatched']}\n"
        )

        if dry_run:
            would_fix = stats['mismatched'] - stats['skipped']
            self.stdout.write(
                self.style.WARNING(
                    f"  [DRY RUN] Would fix: {would_fix}\n"
                    f"  [DRY RUN] Would skip (no auth_id): {stats['skipped']}\n"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"  Successfully fixed: {stats['fixed']}")
            )
            if stats['errored'] > 0:
                self.stdout.write(
                    self.style.ERROR(f"  Errors: {stats['errored']}")
                )
            self.stdout.write('')

    @transaction.atomic
    def _fix_mismatch(self, keycloak_client, rsvp, attendee, application):
        """
        Fix a single mismatched RSVP within a database transaction.
        If Keycloak fails, the database changes are rolled back.
        """
        # Step 1: Update RSVP participation class
        old_class = rsvp.participation_class
        rsvp.participation_class = application.participation_class
        rsvp.save()
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ Updated RSVP participation_class "
                f"from {old_class} to "
                f"{application.participation_class}"
            )
        )

        # Step 2: Update attendee participation class
        attendee.participation_class = application.participation_class

        # Step 3: Handle Keycloak roles
        if attendee.authentication_id:
            # Remove all current year roles from Keycloak
            self._remove_current_year_roles(keycloak_client, attendee)

            # Assign correct role (pass participation_class explicitly)
            keycloak_client.assign_authentication_roles(
                attendee,
                application.participation_class
            )
            role_name = self._get_role_name(application.participation_class)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✓ Assigned correct role: {role_name}"
                )
            )
        else:
            # No Keycloak account - just save the attendee
            attendee.participation_class = application.participation_class
            attendee.save()
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ No authentication_id found "
                    f"for {attendee.email} - DB updated only"
                )
            )

    def _get_role_name(self, participation_class):
        """Get the Keycloak role name for a participation class"""
        if participation_class == ParticipationClass.PARTICIPANT:
            return f"attendee:{EVENT_YEAR}"
        # Get display name and convert to lowercase for role
        role_display = dict(ParticipationClass.choices)[participation_class]
        return f"{role_display.lower()}:{EVENT_YEAR}"

    def _remove_current_year_roles(self, keycloak_client, attendee):
        """Remove all current year roles from the attendee's Keycloak account"""
        if not keycloak_client.client_uuid:
            keycloak_client.get_client_uuid()

        # Get current roles for the user
        current_roles_response = requests.get(
            url=(
                f"{keycloak_client.base_url}/users/"
                f"{attendee.authentication_id}"
                f"/role-mappings/clients/{keycloak_client.client_uuid}"
            ),
            headers=keycloak_client.authentication_headers,
        )

        if not current_roles_response.ok:
            raise Exception(
                f"Error getting current roles: "
                f"{current_roles_response.json()}"
            )

        current_roles = current_roles_response.json()

        # Filter for current year roles
        current_year_roles = [
            role for role in current_roles
            if f":{EVENT_YEAR}" in role.get('name', '')
        ]

        if current_year_roles:
            self._delete_roles(keycloak_client, attendee, current_year_roles)

    def _delete_roles(self, keycloak_client, attendee, roles):
        """Delete specified roles from the attendee's Keycloak account."""
        delete_response = requests.delete(
            url=(
                f"{keycloak_client.base_url}/users/"
                f"{attendee.authentication_id}"
                f"/role-mappings/clients/"
                f"{keycloak_client.client_uuid}"
            ),
            headers=keycloak_client.authentication_headers,
            data=json.dumps(roles)
        )

        if not delete_response.ok:
            raise Exception(
                f"Error removing roles: {delete_response.text}"
            )

        role_names = [role['name'] for role in roles]
        self.stdout.write(
            self.style.SUCCESS(
                f"  ✓ Removed roles: {', '.join(role_names)}"
            )
        )
