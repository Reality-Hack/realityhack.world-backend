import random
import uuid

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from infrastructure import factories
from infrastructure.models import (Application, Attendee, Hardware,
                                   HardwareDevice, HelpDesk, Location, Project,
                                   Skill, SkillProficiency, Table, Team,
                                   UploadedFile, Workshop, WorkshopAttendee)

NUMBER_OF_ATTENDEES = 500
NUMBER_OF_GROUPS = 5
NUMBER_OF_SKILLS = 80
NUMBER_OF_TEAMS = 80
TEAM_SIZE = 5
NUMBER_OF_SKILL_PROFICIENCIES = 4
NUMBER_OF_HARDWARE_TYPES = 100
NUMBER_OF_HARDWARE_DEVICES = 25
SHIRT_SIZES = ["SHIRT_SIZE_S", "SHIRT_SIZE_M", "SHIRT_SIZE_L",
               "SHIRT_SIZE_XL", "SHIRT_SIZE_XXL"]
NUMBER_OF_WORKSHOPS = 20
NUMBER_OF_WORKSHOP_ATTENDEES = 100


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
    HardwareDevice.history.all().delete()
    Project.objects.all().delete()
    Group.objects.all().delete()
    Application.objects.all().delete()
    for uploaded_file in UploadedFile.objects.all():
        uploaded_file.delete()
    Workshop.objects.all().delete()
    WorkshopAttendee.objects.all().delete()


def add_all():  # noqa: C901
    groups = []
    for _ in range(NUMBER_OF_GROUPS):
        group = factories.GroupFactory()
        group.name = f"{group}{uuid.uuid4()}"
        groups.append(group)
    attendees = []
    for _ in range(NUMBER_OF_ATTENDEES):
        metadata_dict = dict()
        metadata_dict["shirt_size"] = random.choice(SHIRT_SIZES)
        attendee = factories.AttendeeFactory(metadata=metadata_dict)
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
        skill.name = skill.name.lower().replace(
            " ", "_").replace("-", "_").replace(",", "")
        skill.save()
        skills.append(skill)
    skill_proficiencies = []
    applications = []
    uploaded_files = []
    for _ in range(NUMBER_OF_ATTENDEES * 2):
        application_skill_proficiencies = []
        resume = factories.UploadedFileFactory()
        uploaded_files.append(resume)
        application = factories.ApplicationFactory(resume=resume)
        number_of_skill_proficiencies = random.randint(
            1, NUMBER_OF_SKILL_PROFICIENCIES)
        for _ in range(number_of_skill_proficiencies):
            skill_proficiency = factories.SkillProficiencyFactory()
            skill_proficiency.application = application
            skill_proficiency.save()
            skill_proficiencies.append(skill_proficiency)
            application_skill_proficiencies.append(skill_proficiency)
        application.email = f"{uuid.uuid4()}{application.email}"
        application.save()
        applications.append(application)
    uploaded_files.append(factories.UploadedFileFactory())
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
    hardware = []
    hardware_devices = []
    for _ in range(NUMBER_OF_HARDWARE_TYPES):
        hardware_type = factories.HardwareFactory()
        hardware.append(hardware_type)
    for _ in range(NUMBER_OF_HARDWARE_TYPES * NUMBER_OF_HARDWARE_DEVICES):
        checked_out = bool(random.getrandbits(1))
        if checked_out:
            hardware_device = factories.HardwareDeviceFactory()
        else:
            hardware_device = factories.HardwareDeviceFactory(
                checked_out_to=None)
        hardware_devices.append(hardware_device)
    workshops = []
    workshop_attendees = []
    for _ in range(NUMBER_OF_WORKSHOPS):
        workshop = factories.WorkshopFactory(
            skills=random.sample(skills, random.randint(1, 10)),
            hardware=random.sample(hardware, random.randint(1, 10)),
        )
        for _ in range(NUMBER_OF_WORKSHOP_ATTENDEES):
            workshop_attendee = factories.WorkshopAttendeeFactory(workshop=workshop)
            workshop_attendees.append(workshop_attendee)
        workshops.append(workshop)


class Command(BaseCommand):  # pragma: no cover
    help = "Generates test data"

    @transaction.atomic
    def handle(self, *args, **kwargs):  # noqa: C901
        self.stdout.write("Deleting old data...")
        delete_all()

        self.stdout.write("Creating new data...")
        add_all()
