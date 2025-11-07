from django.core.management.base import BaseCommand
from infrastructure.models import Attendee
from infrastructure.keycloak import KeycloakClient
import os

KEYCLOAK_REALM = os.getenv('KEYCLOAK_REALM', 'reality-hack-2024')
KEYCLOAK_URL = os.getenv('KEYCLOAK_SERVER_URL', 'http://localhost:8080')


class Command(BaseCommand):  # pragma: no cover
    help = "resend keycloak account creation emails"

    def handle(self, *args, **kwargs):  # noqa: C901
        keycloak_client = KeycloakClient()
        attendees = Attendee.objects.filter(authentication_id__isnull=True)
        for attendee in attendees:
            try:
                keycloak_client.handle_user_rsvp(attendee)
            except Exception as e:
                print(f"Error creating keycloak account for {attendee.email}")
                print(f"Error: {e}")
