import random

from django.core.management.base import BaseCommand
from django.db import transaction

from infrastructure import factories
from infrastructure.models import DestinyTeam, DestinyTeamAttendeeVibe


def delete_all():  # noqa: C901
    DestinyTeamAttendeeVibe.objects.all().delete()


def add_all():  # noqa: C901
    destiny_team_attendee_vibes = []
    for destiny_team in DestinyTeam.objects.all():
        for attendee in destiny_team.attendees.all():
            # 20 percent do not report
            will_report_vibe = random.randint(1, 100) < 80
            if will_report_vibe:
                # 50% 5s, 30% 4s, 12% 3s, 2% 2s, 6% 1s
                vibe = random.choices([5, 4, 3, 2, 1], weights=[50, 30, 12, 2, 6])[0]
                destiny_team_attendee_vibe = factories.DestinyTeamAttendeeVibeFactory(
                    destiny_team=destiny_team, attendee=attendee, vibe=vibe
                )
                destiny_team_attendee_vibes.append(destiny_team_attendee_vibe)

class Command(BaseCommand):  # pragma: no cover
    help = "Generates test destiny team attendee vibe data"

    @transaction.atomic
    def handle(self, *args, **kwargs):  # noqa: C901
        self.stdout.write("Deleting old destiny team attendee vibes...")
        delete_all()

        self.stdout.write("Creating new detiny team attendee vibes...")
        add_all()
