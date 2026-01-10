from datetime import datetime

from django.core.mail import send_mail
from django.core.management.base import BaseCommand

from infrastructure import email
from infrastructure.models import Application, ParticipationClass
import infrastructure.event_context as event_context


class Command(BaseCommand):  # pragma: no cover
    help = "Sends RSVP emails to those that have not received them"
    event = event_context.get_active_event()

    def add_arguments(self, parser):
        parser.add_argument("--email", nargs=1, type=str, required=False)
        parser.add_argument("--force-email", nargs=1, type=str, required=False)

    def send_email(self, application):
        subject, body = None, None
        if application.participation_class == ParticipationClass.PARTICIPANT:
            subject, body = email.get_hacker_rsvp_request_template(
                application.first_name, application.id
            )
        elif application.participation_class == ParticipationClass.MENTOR:
            subject, body = email.get_mentor_rsvp_request_template(
                application.first_name, application.id
            )
        elif application.participation_class == ParticipationClass.JUDGE:
            subject, body = email.get_judge_rsvp_request_template(
                application.first_name, application.id
            )
        if subject and body:
            send_mail(
                subject,
                body,
                "no-reply@realityhackinc.org",
                [application.email],
                fail_silently=False,
            )
            application.rsvp_email_sent_at = datetime.now()
            application.save()
            print(f"Email sent for {application.first_name} {application.last_name}"
                  f" Participation Class: {application.participation_class}"
                  f" Email: ({application.email})")
        else:
            print(f"Error with {application.first_name} {application.last_name}"
                  f" Participation Class: {application.participation_class}"
                  f" Email: {application.email}")

    def handle(self, *args, **kwargs):  # noqa: C901
        accepted_applications_with_unsent_rsvp_emails = []
        try:
            if "force_email" in kwargs and kwargs["force_email"] is not None:
                for attendee_email in kwargs["force_email"]:
                    found_results = Application.objects.all().filter(
                        email=attendee_email
                    )
                    if found_results:
                        accepted_applications_with_unsent_rsvp_emails.append(
                           found_results[0]
                        )
            if "email" in kwargs and kwargs["email"] is not None:
                for attendee_email in kwargs["email"]:
                    found_results = Application.objects.all().filter(
                        email=attendee_email,
                        rsvp_email_sent_at=None
                    )
                    if found_results:
                        accepted_applications_with_unsent_rsvp_emails.append(
                           found_results[0]
                        )
        except (KeyError, IndexError):
            pass
        if not kwargs.get("force_email") and not kwargs.get("email"):
            queryset = Application.objects.for_event(
                self.event
            ).filter(
                status=Application.Status.ACCEPTED_IN_PERSON, rsvp_email_sent_at=None
            )
            accepted_applications_with_unsent_rsvps = queryset
        for application in accepted_applications_with_unsent_rsvps:
            self.send_email(application)
