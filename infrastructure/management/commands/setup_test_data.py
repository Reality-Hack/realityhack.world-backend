import random
import uuid

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from infrastructure import factories
from infrastructure.models import (Attendee, Hardware, HardwareDevice,
                                   HelpDesk, Location, Project, Skill,
                                   SkillProficiency, Table, Team)

NUMBER_OF_ATTENDEES = 500
NUMBER_OF_GROUPS = 5
NUMBER_OF_SKILLS = 80
NUMBER_OF_TEAMS = 80
TEAM_SIZE = 5
NUMBER_OF_SKILL_PROFICIENCIES = 4
NUMBER_OF_HARDWARE_TYPES = 10
NUMBER_OF_HARDWARE_DEVICES = 25


def delete_all():  # noqa: C901
    Attendee.objects.all().delete()
    Skill.objects.all().delete()
    Location.objects.all().delete()
    Table.objects.all().delete()
    Team.objects.all().delete()
    SkillProficiency.objects.all().delete()
    HelpDesk.objects.all().delete()
    Hardware.objects.all().delete()
    HardwareDevice.objects.all().delete()
    Project.objects.all().delete()
    Group.objects.all().delete()


def add_all():  # noqa: C901
    groups = []
    for _ in range(NUMBER_OF_GROUPS):
        group = factories.GroupFactory()
        group.name = f"{group}{uuid.uuid4()}"
        groups.append(group)
    attendees = []
    for _ in range(NUMBER_OF_ATTENDEES):
        attendee = factories.AttendeeFactory()
        attendee.username = f"{attendee.username}{uuid.uuid4()}"
        attendee.email = f"{uuid.uuid4()}{attendee.email}"
        number_of_attendee_groups = random.randint(1, NUMBER_OF_GROUPS)
        attendee_groups = random.sample(groups, number_of_attendee_groups)
        attendee.groups.set(attendee_groups)
        attendee.save()
        attendees.append(attendee)
    skills = []
    for _ in range(NUMBER_OF_SKILLS):
        skill = factories.SkillFactory()
        skills.append(skill)
    Location.objects.create(room=Location.Room.ATLANTIS)
    Location.objects.create(room=Location.Room.MAIN_HALL)
    tables = []
    for _ in range(NUMBER_OF_TEAMS):
        table = factories.TableFactory()
        tables.append(table)
    help_desks = []
    for _ in range(NUMBER_OF_TEAMS):
        help_desk = factories.HelpDeskFactory()
        help_desks.append(help_desk)
    attendee_subset_index = 0
    teams = []
    for _ in range(NUMBER_OF_TEAMS):
        team = factories.TeamFactory(
            attendees=attendees[
                attendee_subset_index:attendee_subset_index + TEAM_SIZE
            ]
        )
        teams.append(team)
        attendee_subset_index += TEAM_SIZE
    projects = []
    for team in teams:
        project = factories.ProjectFactory(
            team=team
        )
        projects.append(project)
    skill_proficiencies = []
    for _ in range(NUMBER_OF_ATTENDEES):
        number_of_skill_proficiencies = random.randint(
            1, NUMBER_OF_SKILL_PROFICIENCIES)
        for _ in range(number_of_skill_proficiencies):
            skill_proficiency = factories.SkillProficiencyFactory()
            skill_proficiencies.append(skill_proficiency)
    hardware = []
    hardware_devices = []
    for _ in range(NUMBER_OF_HARDWARE_TYPES):
        hardware_type = factories.HardwareFactory()
        hardware.append(hardware_type)
    for _ in range(NUMBER_OF_HARDWARE_TYPES * NUMBER_OF_HARDWARE_DEVICES):
        hardware_device = factories.HardwareDeviceFactory()
        hardware_devices.append(hardware_device)


class Command(BaseCommand):  # pragma: no cover
    help = "Generates test data"

    @transaction.atomic
    def handle(self, *args, **kwargs):  # noqa: C901
        self.stdout.write("Deleting old data...")
        delete_all()

        self.stdout.write("Creating new data...")
        add_all()
