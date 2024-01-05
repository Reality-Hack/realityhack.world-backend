from datetime import datetime

from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction

from infrastructure import email
from infrastructure.models import Application


class Command(BaseCommand):  # pragma: no cover
    help = "Generates test data"

    def add_arguments(self, parser):
        parser.add_argument("--email", nargs=1, type=str, required=False)
        parser.add_argument("--force-email", nargs=1, type=str, required=False)

    def send_email(self, application):
        subject, body = None, None
        if application.participation_class == Application.ParticipationClass.PARTICIPANT:
            subject, body = email.get_hacker_rsvp_request_template(application.first_name, application.id)
        elif application.participation_class == Application.ParticipationClass.MENTOR:
            subject, body = email.get_mentor_rsvp_request_template(application.first_name, application.id)
        elif application.participation_class == Application.ParticipationClass.JUDGE:
            subject, body = email.get_judge_rsvp_request_template(application.first_name, application.id)
        if subject and body:
            send_mail(
                subject,
                body,
                "no-reply@mitrealityhack.com",
                [application.email],
                fail_silently=False,
            )
            application.rsvp_email_sent_at = datetime.now()
            application.save()
            print(f"Email sent for str({application})")
        else:
            print(f"Error with str({application})")

    @transaction.atomic
    def handle(self, *args, **kwargs):  # noqa: C901
        accepted_applications_with_unsent_rsvp_emails = []
        try:
            if "force_email" in kwargs and kwargs["force_email"] is not None:
                for email in kwargs["force_email"]:
                    found_results = Application.objects.all().filter(email=email)
                    if found_results:
                        accepted_applications_with_unsent_rsvp_emails.append(
                           found_results[0]
                        )
            if "email" in kwargs and kwargs["email"] is not None:
                for email in kwargs["email"]:
                    found_results = Application.objects.all().filter(email=email, rsvp_email_sent_at=None)
                    if found_results:
                        accepted_applications_with_unsent_rsvp_emails.append(
                           found_results[0]
                        )
        except (KeyError, IndexError):
            pass
        if not kwargs.get("force_email") and not kwargs.get("email"):
            accepted_applications_with_unsent_rsvp_emails = Application.objects.all().filter(
                status=Application.Status.ACCEPTED_IN_PERSON, rsvp_email_sent_at=None
            )
        for application in accepted_applications_with_unsent_rsvp_emails:
            self.send_email(application)
