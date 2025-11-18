from django.core.management.base import BaseCommand

from infrastructure.keycloak import KeycloakClient
from infrastructure.models import Attendee
from datetime import datetime

now_str = datetime.now().strftime("%Y%m%d%H%M%S")


class Command(BaseCommand):  # pragma: no cover
    help = "Create an Attendee"

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

    def create_attendee(self, **options):

        attendee = Attendee.objects.create(
            username=options['email'],  # Using email as username
            email=options['email'],
            first_name=options['first_name'],
            last_name=options['last_name'],
            participation_class=options['role'],
            us_visa_support_is_required=False,
            emergency_contact_name="No Reply",
            personal_phone_number="+1-555-123-4567",
            emergency_contact_phone_number="+1-555-987-6543",
            emergency_contact_email="no-reply@realityhackinc.org",
            emergency_contact_relationship="None"
        )
        return attendee

    def handle(self, *args, **options):
        attendee = self.create_attendee(**options)
        attendee.save()
        keycloak_client = KeycloakClient()
        keycloak_client.handle_user_rsvp(attendee)
        print(f"Attendee created: {attendee.email}")
        print(f"Authentication account created: {attendee.authentication_id}")
