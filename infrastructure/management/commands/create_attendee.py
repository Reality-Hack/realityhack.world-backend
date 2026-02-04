from django.core.management.base import BaseCommand

from infrastructure.keycloak import KeycloakClient
from infrastructure.models import Attendee, Event, EventRsvp, ShirtSize
from datetime import datetime

now_str = datetime.now().strftime("%Y%m%d%H%M%S")


class Command(BaseCommand):  # pragma: no cover
    help = "Create an Attendee"
    current_event = Event.get_active()

    def add_arguments(self, parser):
        parser.add_argument(
            "--first_name",
            default="Reality",
            help="First name"
        )
        parser.add_argument(
            "--last_name",
            default="Hack",
            help="Last name"
        )
        parser.add_argument(
            "--email",
            default=f"albert+@{now_str}@realityhackinc.org",
            help="Email"
        )
        parser.add_argument(
            "--role",
            default="P",
            help="Participation class (P, M, J, S, V, O, G, E)",
        )
        parser.add_argument(
            "--phone_number",
            default="+1-000-000-0000",
            help="Phone number",
        )
        parser.add_argument(
            "--emergency_contact_phone_number",
            default="+1-000-000-0000",
            help="Emergency contact phone number",
        )
        parser.add_argument(
            "--emergency_contact_email",
            default="no-reply@realityhackinc.org",
            help="Emergency contact email",
        )
        parser.add_argument(
            "--emergency_contact_name",
            default="No Reply",
            help="Emergency contact name",
        )
        parser.add_argument(
            "--communication_platform_username",
            default="asdfasf",
            help="Communication platform username",
        )

    def create_attendee(self, **options):
        if existing_attendee := Attendee.objects.filter(email=options['email']).first():
            print(f"Attendee already exists: {existing_attendee.email}")
            return existing_attendee
        attendee = Attendee.objects.create(
            username=options['email'],  # Using email as username
            email=options['email'],
            first_name=options['first_name'],
            last_name=options['last_name'],
            participation_class=options['role'],
            us_visa_support_is_required=False,
            communications_platform_username=options['communication_platform_username'],
            emergency_contact_name=options['emergency_contact_name'],
            personal_phone_number=options['phone_number'],
            emergency_contact_phone_number=options['emergency_contact_phone_number'],
            emergency_contact_email=options['emergency_contact_email'],
            emergency_contact_relationship="None"
        )
        return attendee

    def handle(self, *args, **options):
        attendee = self.create_attendee(**options)
        print(f"Attendee created: {attendee.email}")
        print(f"Attendee name: {attendee.first_name} {attendee.last_name}")
        event_rsvp = EventRsvp.objects.create(
            attendee=attendee,
            event=self.current_event,
            status=EventRsvp.Status.RSVP,
            participation_class=options['role'],
            shirt_size=ShirtSize.M,
            communication_platform_username=options['communication_platform_username'],
            us_visa_support_is_required=False,
            emergency_contact_name=options['emergency_contact_name'],
            personal_phone_number=options['phone_number'],
            emergency_contact_phone_number=options['emergency_contact_phone_number'],
            emergency_contact_email=options['emergency_contact_email'],
            emergency_contact_relationship="None",
        )
        attendee.save()
        event_rsvp.save()
        keycloak_client = KeycloakClient()
        keycloak_client.handle_user_rsvp(attendee, event_rsvp.participation_class)
        print(f"Attendee created: {attendee.email}")
        print(f"Authentication account created: {attendee.authentication_id}")
