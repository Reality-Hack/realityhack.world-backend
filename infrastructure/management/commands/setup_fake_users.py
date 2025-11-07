# For Docker-based testing. Ignore outside of docker-compose.yml
import os
import time
from argparse import Namespace

import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from PIL import Image

from infrastructure.factories import ApplicationFactory, UploadedFileFactory
from infrastructure.models import Application, Attendee, UploadedFile, Team
from infrastructure.serializers import AttendeeRSVPCreateSerializer
from infrastructure.keycloak import KeycloakClient
from infrastructure.event_context import get_active_event


class Command(BaseCommand):  # pragma: no cover
    help = "Create fake RSVP"
    base_rsvp_request = {
        "first_name": "Attendee",
        "last_name": "user",
        "communications_platform_username": "gorillapete",
        "personal_phone_number": "+1-415-335-5209",
        # "email": "attendee@test.com",
        # "authentication_id": "d9b4cfbf-0b5a-40b4-a03c-3b97a3678d26",
        "participation_class": "P",
        "dietary_restrictions": [
        ],
        "dietary_allergies": [
        ],
        "guardian_of": [
        ],
        "bio": " ",
        "shirt_size": None,
        "dietary_restrictions_other": None,
        "allergies_other": None,
        "additional_accommodations": None,
        "us_visa_support_is_required": False,
        "us_visa_support_full_name": None,
        "us_visa_letter_of_invitation_required": None,
        "us_visa_support_national_identification_document_type": None,
        "us_visa_support_document_number": None,
        "us_visa_support_citizenship": None,
        "us_visa_support_address": None,
        "agree_to_media_release": True,
        "under_18_by_date": None,
        "parential_consent_form_signed": None,
        "agree_to_rules_code_of_conduct": True,
        "emergency_contact_name": "Shane Engelman",
        "emergency_contact_phone_number": "+1-415-335-5209",
        "emergency_contact_email": "contact@shane.gg",
        "emergency_contact_relationship": "self",
        "special_interest_track_one": None,
        "special_interest_track_two": None,
        "app_in_store": None,
        "currently_build_for_xr": None,
        "currently_use_xr": None,
        "non_xr_talents": None,
        "ar_vr_app_in_store": None,
        "reality_hack_project_to_product": False,
        "identify_as_native_american": False,
        "sponsor_company": None,
        "us_visa_support_citizenship_option": None
    }
    keycloak_client = KeycloakClient()

    def add_arguments(self, parser):
        parser.add_argument(
            "--fake-initial-setup",
            action="store_true",
            help="Fake attendee's initial setup"
        )


    def rsvp_create(self, request):
        application = None
        sponsor_handler = None
        guardian_of = []

        try:
            if "sponsor_handler" in request.data:
                sponsor_handler = Attendee.objects.get(
                    pk=request.data["sponsor_handler"]
                )
                del request.data["sponsor_handler"]
        except Attendee.DoesNotExist:  # pragma: nocover
            pass
        try:
            if "guardian_of" in request.data:
                guardian_of_attendees = list(Attendee.objects.filter(
                    id__in=request.data["guardian_of"]
                ))
                guardian_of = guardian_of_attendees
                del request.data["guardian_of"]
        except Attendee.DoesNotExist:  # pragma: nocover
            pass
        if "application" in request.data:
            application = Application.objects.get(pk=request.data.get("application"))
            request.data["first_name"] = application.first_name
            request.data["middle_name"] = application.middle_name
            request.data["last_name"] = application.last_name
            request.data["participation_class"] = application.participation_class
            request.data["email"] = application.email.lower()
            del request.data["application"]
            request.data["application"] = str(application.id)
        else:  # Volunteer or Organizer, or null
            if request.data.get("email") is not None:
                request.data["email"] = request.data.get("email").lower()
        serializer = AttendeeRSVPCreateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer_data = serializer.data
        attendee = None
        if serializer_data.get("application"):
            del serializer_data["application"]
            attendee = Attendee(application=application, **serializer_data)
            attendee.participation_role = application.participation_role
        else:
            attendee = Attendee(**serializer_data)
        attendee.username = attendee.email
        if request.data.get("authentication_id"):
            attendee.authentication_id = request.data["authentication_id"]
        attendee.sponsor_handler = sponsor_handler
        attendee.save()
        if guardian_of:
            attendee.guardian_of.set(
                [guardian_of_attendee.id for guardian_of_attendee in guardian_of]
            )
        return attendee

    def create_authentication_account(self, attendee, password):
        self.keycloak_client.create_authentication_account(attendee, password)
        self.keycloak_client.assign_authentication_roles(attendee)

    @transaction.atomic
    def handle(self, *args, **kwargs):  # noqa: C901
        print("Checking that Keycloak is up...")
        keycloak_results = None
        for _ in range(10):
            try:
                if os.environ.get("KEYCLOAK_ADMIN_URL", None):
                    admin_url = os.environ.get("KEYCLOAK_ADMIN_URL")
                else:
                    admin_url = os.environ.get("KEYCLOAK_SERVER_URL")
                keycloak_results = requests.get(
                    f"{admin_url}/health/live",
                    timeout=10)
            except requests.exceptions.ConnectionError as e:
                print(f"ConnectionError: {e}")
                pass
            if keycloak_results and keycloak_results.status_code == 200:
                break
            time.sleep(2)
        else:
            raise Exception("Keycloak failed to start.")
        print("Creating fake application...")
        try:
            application = Application.objects.for_event(
                get_active_event()
            ).get(email="attendee@test.com")
        except Application.DoesNotExist:
            application = ApplicationFactory(
                resume=UploadedFileFactory(),
                email="attendee@test.com",
                event=get_active_event(),
                participation_class="P")
            application.save()
        try:
            attendee = Attendee.objects.get(email="attendee@test.com")
        except Attendee.DoesNotExist:
            attendee = self.rsvp_create(Namespace(data={
                **self.base_rsvp_request,
                "email": application.email,
                "participation_class": "P"
            }))
        self.create_authentication_account(attendee, "123456")
        event = get_active_event()
        if event:
            team = Team.objects.for_event(event).filter(attendees=attendee).first()
            if not team:
                team = Team.objects.for_event(event).first()
                if team:
                    team.attendees.add(attendee)
        else:
            self.stdout.write(self.style.WARNING(
                'No active event found. Skipping team assignment for fake user.'
            ))

        if False:  # kwargs.get("fake_initial_setup", False):
            attendee.initial_setup = True
            attendee.profile_image = UploadedFile.objects.create(
                file=ContentFile(Image.new("RGB", (100, 100)).tobytes()))
        attendee.save()
        print("Fake data created.")
