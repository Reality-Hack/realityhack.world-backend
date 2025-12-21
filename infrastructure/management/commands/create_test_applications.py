import os
import logging
import uuid

from django.core.management.base import BaseCommand

from infrastructure.models import Application, Attendee, EventRsvp
from infrastructure.factories import ApplicationFactory, UploadedFileFactory
import infrastructure.event_context as event_context

logger = logging.getLogger(__name__)


returning_participant = True
new_participants = 1
mentors = 1
judges = 1

emails_to_test = [
    # "attendee@test.com",
]

event = event_context.get_active_event()
print(f"Event: {event.name}")
print(f"Event ID: {event.id}")
frontend_domain = os.environ["FRONTEND_DOMAIN"]


def get_rsvp_request_uri(application_id: str) -> str:
    return f"{frontend_domain}/rsvp/{application_id}"


class Command(BaseCommand):
    help = "Create test applications for the given emails"

    def handle(self, *args, **options):
        # first ensure we have existing attendees for the given emails
        for email in emails_to_test:
            if not (existing_attendee := Attendee.objects.filter(email=email).first()):
                raise Exception(f"Attendee not found for email: {email}")

        # create new and returning application objects
        for email in emails_to_test:
            print(f"Processing email: {email}")
            existing_attendee = Attendee.objects.filter(email=email).first()
            if existing_rsvp := EventRsvp.objects.for_event(event).filter(
                attendee=existing_attendee
            ).first():
                print(
                    f"Deleting existing RSVP for attendee: {existing_attendee.email}"
                )
                application = existing_rsvp.application
                existing_rsvp.delete()
            elif existing_application := Application.objects.for_event(event).filter(
                email=existing_attendee.email
            ).first():
                print(
                    f"Existing application for attendee: {existing_attendee.email}"
                )
                application = existing_application
            else:
                resume = UploadedFileFactory()
                application = ApplicationFactory(
                    event=event,
                    resume=resume,
                    email=existing_attendee.email,
                )
                application.save()
                print(f"Returning participant: {existing_attendee.email}")
            print(f"RSVP request URI: {get_rsvp_request_uri(application.id)}")

            # new participant
            resume = UploadedFileFactory()
            split_email = email.split("@")
            application_email = f"{split_email[0]}+{uuid.uuid4()}@{split_email[1]}"
            application = ApplicationFactory(
                event=event,
                resume=resume,
                email=application_email
            )
            application.save()
            print(f"New participant: {application_email}")
            print(f"RSVP request URI: {get_rsvp_request_uri(application.id)}")
