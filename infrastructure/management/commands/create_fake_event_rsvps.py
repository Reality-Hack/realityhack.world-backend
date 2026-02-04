import logging
import uuid

from django.core.management.base import BaseCommand

from infrastructure.models import (
    Application,
    Attendee,
    Event,
    EventRsvp,
    ParticipationClass,
)
from infrastructure.keycloak import KeycloakClient
from infrastructure.factories import ApplicationFactory, UploadedFileFactory
import infrastructure.event_context as event_context

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Fetch auth accounts from Keycloak and create missing applications "
        "and event RSVPs for the active event"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            help='Optional Keycloak role to filter users (e.g., "attendee:2026")',
            required=False,
        )

    def handle(self, *args, **options):
        # Get the active event
        active_event = Event.get_active()
        if not active_event:
            self.stderr.write(self.style.ERROR("No active event found"))
            return

        self.stdout.write(f"Active event: {active_event.name} (ID: {active_event.id})")

        # Set the event context for factories
        event_context.set_current_event(active_event)

        # Initialize Keycloak client
        keycloak = KeycloakClient()

        # Fetch users from Keycloak
        role = options.get('role')
        if role:
            self.stdout.write(f"Fetching users with role: {role}")
            keycloak_users = keycloak.get_users_by_role(role)
        else:
            self.stdout.write("Fetching all users from Keycloak")
            keycloak_users = keycloak.get_all_users()

        self.stdout.write(f"Found {len(keycloak_users)} users in Keycloak")

        created_attendees = 0
        updated_attendees = 0
        created_applications = 0
        created_rsvps = 0

        for kc_user in keycloak_users:
            kc_id = kc_user.get('id')
            kc_email = kc_user.get('email')
            kc_first_name = kc_user.get('firstName', '')
            kc_last_name = kc_user.get('lastName', '')

            if not kc_email:
                self.stdout.write(
                    self.style.WARNING(f"Skipping user {kc_id} - no email")
                )
                continue

            self.stdout.write(f"\nProcessing: {kc_email}")

            # Find or create attendee by authentication_id
            attendee = Attendee.objects.filter(authentication_id=kc_id).first()
            if not attendee:
                attendee = Attendee.objects.filter(email=kc_email).first()

            if attendee:
                # Update attendee details from Keycloak
                attendee.first_name = kc_first_name
                attendee.last_name = kc_last_name
                attendee.email = kc_email
                attendee.save()
                updated_attendees += 1
                self.stdout.write(f"  Updated attendee: {attendee.email}")
            else:
                # Create new attendee
                attendee = Attendee.objects.create(
                    authentication_id=kc_id,
                    email=kc_email,
                    first_name=kc_first_name,
                    last_name=kc_last_name,
                    username=f"{kc_first_name}.{kc_last_name}.{uuid.uuid4()}",
                    participation_class=ParticipationClass.PARTICIPANT,
                    us_visa_support_is_required=False,
                    emergency_contact_name="TBD",
                    personal_phone_number="+10000000000",
                    emergency_contact_phone_number="+10000000000",
                    emergency_contact_email="tbd@example.com",
                    emergency_contact_relationship="TBD",
                )
                created_attendees += 1
                self.stdout.write(
                    self.style.SUCCESS(f"  Created attendee: {attendee.email}")
                )

            # Find or create application for current event
            application = Application.objects.for_event(active_event).filter(
                event=active_event,
                email=kc_email
            ).first()

            if not application:
                resume = UploadedFileFactory()
                application = ApplicationFactory(
                    event=active_event,
                    resume=resume,
                    email=kc_email,
                    first_name=kc_first_name,
                    last_name=kc_last_name,
                    participation_class=ParticipationClass.PARTICIPANT,
                    status=Application.Status.ACCEPTED_IN_PERSON,
                )
                application.save()
                created_applications += 1
                self.stdout.write(
                    self.style.SUCCESS("  Created application for event")
                )
            else:
                self.stdout.write("  Application already exists")

            # Link application to attendee if not already linked
            if not attendee.application:
                attendee.application = application
                attendee.save()

            # Find or create EventRsvp for active event
            event_rsvp = EventRsvp.objects.for_event(active_event).filter(
                event=active_event,
                attendee=attendee
            ).first()

            if not event_rsvp:
                event_rsvp = EventRsvp.objects.create(
                    event=active_event,
                    attendee=attendee,
                    application=application,
                    participation_class=ParticipationClass.PARTICIPANT,
                    us_visa_support_is_required=False,
                    emergency_contact_name="TBD",
                    personal_phone_number="+10000000000",
                    emergency_contact_phone_number="+10000000000",
                    emergency_contact_email="tbd@example.com",
                    emergency_contact_relationship="TBD",
                )
                created_rsvps += 1
                self.stdout.write(
                    self.style.SUCCESS("  Created EventRsvp for active event")
                )
            else:
                self.stdout.write("  EventRsvp already exists")

        # Clear the event context
        event_context.clear_current_event()

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("Summary:"))
        self.stdout.write(f"  Attendees created: {created_attendees}")
        self.stdout.write(f"  Attendees updated: {updated_attendees}")
        self.stdout.write(f"  Applications created: {created_applications}")
        self.stdout.write(f"  EventRsvps created: {created_rsvps}")
