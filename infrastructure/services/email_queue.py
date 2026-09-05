import logging

from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
from django.utils import timezone
from huey.contrib.djhuey import db_task

from infrastructure import email
from infrastructure.models import Application, Attendee, ParticipationClass

logger = logging.getLogger(__name__)

FROM_EMAIL = "no-reply@realityhackinc.org"


def _get_application_confirmation_template(application: Application):
    if application.participation_class == ParticipationClass.MENTOR:
        return email.get_mentor_application_confirmation_template(
            application.first_name,
            response_email_address="Mentors <mentors@realityhackinc.org>",
        )
    if application.participation_class == ParticipationClass.JUDGE:
        return email.get_judge_application_confirmation_template(
            application.first_name,
            response_email_address="Catherine Dumas <catherine@realityhackinc.org>",
        )
    return email.get_hacker_application_confirmation_template(application.first_name)


def _get_rsvp_confirmation_template(
    attendee: Attendee,
    participation_class: str,
    temp_password: str | None,
):
    if participation_class == ParticipationClass.PARTICIPANT:
        return email.get_hacker_rsvp_confirmation_template(
            attendee.first_name,
            temp_password,
        )
    return email.get_non_hacker_rsvp_confirmation_template(
        attendee.first_name,
        temp_password,
    )


@db_task(retries=3, retry_delay=60)
def send_application_confirmation_email(application_id: str):
    """Send the initial application confirmation email for a single application."""
    try:
        application = Application.objects.all_events().get(id=application_id)
    except ObjectDoesNotExist:
        logger.warning(
            "Application confirmation skipped; application %s no longer exists",
            application_id,
        )
        return

    subject, body = _get_application_confirmation_template(application)
    send_mail(
        subject,
        body,
        FROM_EMAIL,
        [application.email],
        fail_silently=False,
    )
    logger.info("Application confirmation email sent to %s", application.email)


@db_task(retries=3, retry_delay=60)
def send_rsvp_email(event_id: str, application_id: str, resend: bool = False):
    """Send an RSVP request email for a single application."""
    try:
        application = Application.objects.for_event(event_id).get(id=application_id)

        if application.rsvp_email_sent_at and not resend:
            logger.info("RSVP email already sent to %s", application.email)
            return

        subject = body = None
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

        if not subject or not body:
            logger.warning(
                "No RSVP email template for application %s (%s)",
                application.id,
                application.participation_class,
            )
            return

        send_mail(
            subject,
            body,
            FROM_EMAIL,
            [application.email],
            fail_silently=False,
        )

        application.rsvp_email_sent_at = timezone.now()
        application.save(update_fields=["rsvp_email_sent_at"])

        logger.info("RSVP request email sent to %s", application.email)
    except Exception:
        logger.exception(
            "Failed to send RSVP email for event %s application %s",
            event_id,
            application_id,
        )
        raise


@db_task(retries=3, retry_delay=60)
def send_rsvp_confirmation_email(
    attendee_id: str,
    participation_class: str,
    temp_password: str | None = None,
):
    """Send the post-RSVP confirmation email for a single attendee."""
    try:
        attendee = Attendee.objects.get(id=attendee_id)
    except ObjectDoesNotExist:
        logger.warning(
            "RSVP confirmation skipped; attendee %s no longer exists",
            attendee_id,
        )
        return

    subject, body = _get_rsvp_confirmation_template(
        attendee,
        participation_class,
        temp_password,
    )
    send_mail(
        subject,
        body,
        FROM_EMAIL,
        [attendee.email],
        fail_silently=False,
    )
    logger.info("RSVP confirmation email sent to %s", attendee.email)


@db_task(retries=3, retry_delay=60)
def send_multiple_users_found_email(attendee_email: str):
    """Notify the attendee and organizers when multiple Keycloak users match."""
    subject, body = email.get_multiple_users_found_template(attendee_email)
    send_mail(
        subject,
        body,
        FROM_EMAIL,
        [attendee_email, "apply@realityhackinc.org"],
        fail_silently=False,
    )
    logger.info("Multiple-users-found notification sent for %s", attendee_email)


@db_task(retries=3, retry_delay=60)
def send_keycloak_account_error_email(attendee_email: str, error_message: str):
    """Notify the attendee and tech team when Keycloak RSVP account setup fails."""
    subject, body = email.get_keycloak_account_error_template(
        attendee_email,
        error_message,
    )
    send_mail(
        subject,
        body,
        FROM_EMAIL,
        [attendee_email, "tech@realityhackinc.org"],
        fail_silently=False,
    )
    logger.info("Keycloak account error notification sent for %s", attendee_email)


def queue_rsvp_emails(event_id: str, force_resend: bool = False):
    """Queue one Huey job per application that should receive an RSVP email."""
    queryset = Application.objects.for_event(event_id)

    if not force_resend:
        queryset = queryset.filter(rsvp_email_sent_at__isnull=True)

    count = 0
    for app in queryset.iterator():
        send_rsvp_email(str(event_id), str(app.id), resend=force_resend)
        count += 1

    logger.info("Queued %s RSVP email jobs for event %s", count, event_id)
    return count
