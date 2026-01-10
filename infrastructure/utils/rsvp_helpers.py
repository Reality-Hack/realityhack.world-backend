from typing import List
import logging

from django.core.mail import send_mail
from django.core.exceptions import ValidationError

from infrastructure.models import Attendee, Application, EventRsvp
from infrastructure.event_context import get_active_event
from infrastructure.serializers import AttendeeRSVPCreateSerializer, EventRsvpSerializer
from infrastructure.keycloak import KeycloakClient
from infrastructure import email

logger = logging.getLogger(__name__)


def get_sponsor_handler(
    attendee_id: str | None
) -> Attendee | None:
    if not attendee_id:
        return None

    try:
        return Attendee.objects.get(id=attendee_id)
    except Attendee.DoesNotExist:  # pragma: nocover
        logger.error(f"Attendee with id {attendee_id} does not exist")
        return None


def get_guardian_of(
    attendee_ids: List[str] | None
) -> List[Attendee]:
    if not attendee_ids:
        return []

    guardian_of = []

    for attendee_id in attendee_ids:
        try:
            attendee = Attendee.objects.get(id=attendee_id)
            guardian_of.append(attendee)
        except Attendee.DoesNotExist:  # pragma: nocover
            logger.error(f"Attendee with id {attendee_id} does not exist")
            continue
    return guardian_of


def get_application(application_id: str) -> Application | None:
    try:
        return Application.objects.for_event(get_active_event()).get(pk=application_id)
    except Application.DoesNotExist:  # pragma: nocover
        logger.error(
            f"RSVPApplication with id {application_id} does not exist"
        )
        return None


def _get_attendee_rsvp_create_serializer_from_request(
    request: dict,
    application: Application | None = None,
) -> AttendeeRSVPCreateSerializer:
    if application:
        request.data["first_name"] = application.first_name
        request.data["middle_name"] = application.middle_name
        request.data["last_name"] = application.last_name
        request.data["participation_class"] = application.participation_class
        request.data["application"] = str(application.id)

    if request.data.get("sponsor_handler"):
        del request.data["sponsor_handler"]

    if request.data.get("guardian_of"):
        del request.data["guardian_of"]

    return AttendeeRSVPCreateSerializer(data=request.data, partial=True)


def _get_event_rsvp_create_serializer_from_request(
    request: dict,
    event_id: str,
    application: Application | None = None,
) -> EventRsvpSerializer:
    rsvp_data = request.data.copy()
    if application:
        rsvp_data["application"] = str(application.id)
    rsvp_data["event"] = event_id
    return EventRsvpSerializer(data=rsvp_data, partial=True)


def _create_attendee_from_validated_data(
    serializer: AttendeeRSVPCreateSerializer,
    email: str,
    application: Application | None = None,
) -> Attendee:
    logger.info(f"creating new attendee for email: {email}")
    serializer_data = serializer.data
    if serializer_data.get("application"):
        del serializer_data["application"]
    attendee = Attendee(
        application=application,
        **serializer_data
    )
    attendee.username = attendee.email
    attendee.participation_role = application.participation_role
    logger.info(f"Successfully created attendee: {attendee.id}")
    return attendee


def create_event_rsvp_from_request(
    request: dict,
    attendee: Attendee,
    application: Application,
) -> EventRsvp:
    event = get_active_event()
    rsvp_create_serializer = _get_event_rsvp_create_serializer_from_request(
        request, str(event.id), application
    )
    if rsvp_create_serializer.is_valid():
        rsvp_data = rsvp_create_serializer.data
        rsvp_data.pop("event")
        attendee.save()
        event_rsvp = EventRsvp(
            attendee=attendee,
            event=event,
            application=application,
            **rsvp_data
        )
        logger.info(f"Successfully created event rsvp for user: {attendee.email}")
        return event_rsvp
    else:
        logger.error(f"Error creating event rsvp: {rsvp_create_serializer.errors}")
        raise ValidationError(rsvp_create_serializer.errors)


def get_or_create_attendee_from_request(
    request: dict,
    application: Application | None = None,
) -> Attendee:
    if application:
        email = application.email
    elif request_email := request.data.get("email"):
        email = request_email
    else:
        logger.error("No email found in request or application")
        raise ValueError("No email found in request or application")
    email = email.lower()
    if attendee := Attendee.objects.filter(email=email).first():
        logger.info(
            f"attendee exists, updating fields from application: {attendee.email}"
        )
        attendee.first_name = application.first_name
        attendee.last_name = application.last_name
        attendee.application = application
        attendee.participation_role = application.participation_role
        return attendee
    else:
        logger.info(
            f"attendee does not exist, creating new attendee for email: {email}"
        )
        request.data["email"] = email
        attendee_serializer = _get_attendee_rsvp_create_serializer_from_request(
            request, application
        )
        if attendee_serializer.is_valid():
            return _create_attendee_from_validated_data(
                attendee_serializer, email, application
            )
        else:
            raise ValidationError(attendee_serializer.errors)


def handle_keycloak_account_creation(attendee: Attendee) -> None:
    keycloak_client = KeycloakClient()
    try:
        keycloak_client.handle_user_rsvp(attendee)
    except Exception as error:
        logger.error(f"Error handling user RSVP: {error}")
        subject, body = email.get_keycloak_account_error_template(
            attendee.email, error
        )
        send_mail(
            subject,
            body,
            "no-reply@realityhackinc.org",
            [attendee.email, "tech@realityhackinc.org"],
            fail_silently=False,
        )
