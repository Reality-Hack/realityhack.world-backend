from datetime import datetime

from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.db import transaction

from infrastructure import email
from infrastructure.models import Attendee


class Command(BaseCommand):  # pragma: no cover
    help = "Assigns authentication Roles"

    def handle(self, *args, **kwargs):  # noqa: C901
        for attendee in Attendee.objects.all():
            if not attendee.authentication_roles_assigned:
                attendee.assign_authentication_roles()
