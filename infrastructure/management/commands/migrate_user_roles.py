from django.core.management.base import BaseCommand
from infrastructure.keycloak import KeycloakClient
from infrastructure.models import Attendee


class Command(BaseCommand):
    help = "Migrate user roles"

    def handle(self, *args, **options):
        keycloak_client = KeycloakClient()

        for attendee in Attendee.objects.filter(authentication_id__isnull=False):
            try:
                print(f"Migrating user roles for {attendee.email}")
                print(f"Attendee Roles: {attendee.participation_class}")
                roles = keycloak_client.assign_authentication_roles(attendee)
                print(f"Roles: {roles}")
            except Exception as e:
                print(f"Error migrating user roles for {attendee.email}: {e}")
