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
        parser.add_argument("--email", type=str, help="Send to specific email address")
        parser.add_argument(
            "--force", action="store_true", help="Resend even if already sent"
        )

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

    def handle(self, *args, **kwargs):
        queryset = Application.objects.for_event(self.event)

        # Filter by specific email if provided
        if kwargs["email"]:
            queryset = queryset.filter(email=kwargs["email"])
        else:
            # Default: only accepted in-person applicants
            queryset = queryset.filter(status=Application.Status.ACCEPTED_IN_PERSON)

        # Unless --force, only send to those who haven't received it
        if not kwargs["force"]:
            queryset = queryset.filter(rsvp_email_sent_at=None)
        print(f"Sending {queryset.count()} emails")
        for application in queryset:
            self.send_email(application)
