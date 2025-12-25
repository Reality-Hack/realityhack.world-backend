# TODO: add event rsvps
import random
import uuid
from datetime import datetime, timedelta

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.db import transaction

from infrastructure import event_context
from infrastructure import factories
from infrastructure.models import (Application, Attendee, AttendeePreference,
                                   DestinyTeam, DestinyTeamAttendeeVibe,
                                   Hardware, HardwareDevice, LightHouse,
                                   Location, MentorHelpRequest, Project, Skill,
                                   SkillProficiency, Table, Team, UploadedFile,
                                   Workshop, WorkshopAttendee, Event,
                                   ParticipationClass)

NUMBER_OF_ATTENDEES = 50
NUMBER_OF_GROUPS = 5
NUMBER_OF_SKILLS = 18
TEAM_SIZE = 5
NUMBER_OF_TEAMS = max(0, NUMBER_OF_ATTENDEES // TEAM_SIZE - 1)
NUMBER_OF_MENTOR_HELP_REQUESTS = 10
NUMBER_OF_SKILL_PROFICIENCIES = 4
NUMBER_OF_HARDWARE_TYPES = 10
NUMBER_OF_HARDWARE_REQUESTS = 5
NUMBER_OF_HARDWARE_DEVICES = 5
SHIRT_SIZES = ["SHIRT_SIZE_S", "SHIRT_SIZE_M", "SHIRT_SIZE_L",
               "SHIRT_SIZE_XL", "SHIRT_SIZE_XXL"]
NUMBER_OF_WORKSHOPS = 2
NUMBER_OF_WORKSHOP_ATTENDEES = 10


def delete_all():  # noqa: C901
    Attendee.objects.all().delete()
    Skill.objects.for_event(event_context.get_current_event()).delete()
    Location.objects.for_event(event_context.get_current_event()).delete()
    Table.objects.for_event(event_context.get_current_event()).delete()
    Team.objects.for_event(event_context.get_current_event()).delete()
    SkillProficiency.objects.for_event(event_context.get_current_event()).delete()
    LightHouse.objects.for_event(event_context.get_current_event()).delete()
    Hardware.objects.for_event(event_context.get_current_event()).delete()
    event_hardware_devices = HardwareDevice.objects.for_event(
        event_context.get_current_event()
    ).all()
    for hardware_device in event_hardware_devices:
        hardware_device.history.all().delete()
        hardware_device.delete()
    Project.objects.for_event(event_context.get_current_event()).delete()
    Group.objects.all().delete()
    Application.objects.for_event(event_context.get_current_event()).delete()
    for uploaded_file in UploadedFile.objects.all():
        uploaded_file.delete()
    Workshop.objects.for_event(event_context.get_current_event()).delete()
    WorkshopAttendee.objects.for_event(event_context.get_current_event()).delete()
    MentorHelpRequest.objects.for_event(event_context.get_current_event()).delete()
    event_mentor_help_requests = MentorHelpRequest.objects.for_event(
        event_context.get_current_event()
    ).all()
    for mentor_help_request in event_mentor_help_requests:
        mentor_help_request.history.all().delete()
        mentor_help_request.delete()
    AttendeePreference.objects.for_event(event_context.get_current_event()).delete()
    DestinyTeam.objects.for_event(event_context.get_current_event()).delete()
    DestinyTeamAttendeeVibe.objects.for_event(
        event_context.get_current_event()
    ).delete()


def format_skill_name(skill_name: str) -> str:
    return skill_name.lower().replace(" ", "_").replace("-", "_").replace(",", "")


def add_all():  # noqa: C901
    groups = []
    for _ in range(NUMBER_OF_GROUPS):
        group = factories.GroupFactory()
        group.name = f"{group}{uuid.uuid4()}"
        groups.append(group)
    skills = []
    for _ in range(NUMBER_OF_SKILLS):
        skill = factories.SkillFactory()
        skill.name = f'{format_skill_name(skill.name)}{str(uuid.uuid4()).split("-")[0]}'
        skill.save()
        skills.append(skill)
    skill_proficiencies = []
    applications = []
    uploaded_files = []
    # + 5 to account for mentors
    for i in range((NUMBER_OF_ATTENDEES + 5) * 2):
        application_skill_proficiencies = []
        resume = factories.UploadedFileFactory()
        uploaded_files.append(resume)
        application = factories.ApplicationFactory(
            resume=resume,
            **(dict(status=Application.Status.ACCEPTED_IN_PERSON)
               if i < NUMBER_OF_ATTENDEES + 5 else {}))
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
    attendees = []
    for i, application in enumerate(applications):
        if application.status != Application.Status.ACCEPTED_IN_PERSON:
            continue
        if i < NUMBER_OF_ATTENDEES:
            participation_class = ParticipationClass.PARTICIPANT
        elif i < NUMBER_OF_ATTENDEES + 5:
            participation_class = ParticipationClass.MENTOR
        else:
            participation_class = ParticipationClass.PARTICIPANT

        attendee = factories.AttendeeFactory(
            application=application,
            participation_class=participation_class
        )
        attendee.username = f"{attendee.username}{uuid.uuid4()}"
        attendee.email = f"{uuid.uuid4()}{attendee.email}"
        number_of_attendee_groups = random.randint(1, NUMBER_OF_GROUPS)
        attendee_groups = random.sample(groups, number_of_attendee_groups)
        attendee.groups.set(attendee_groups)
        attendee.save()
        attendees.append(attendee)
    factories.LocationFactory(room=Location.Room.ATLANTIS)
    factories.LocationFactory(room=Location.Room.MAIN_HALL)
    tables = []
    for _ in range(NUMBER_OF_TEAMS):
        table = factories.TableFactory()
        tables.append(table)
    lighthouses = []
    for _ in range(NUMBER_OF_TEAMS):
        lighthouse = factories.LightHouseFactory()
        lighthouses.append(lighthouse)
    attendee_subset_index = 0
    teams = []
    participants = list(Attendee.objects.filter(
        participation_class=ParticipationClass.PARTICIPANT)
    )
    team_participants = []
    for _ in range(NUMBER_OF_TEAMS):
        team_members = participants[
                attendee_subset_index:attendee_subset_index + TEAM_SIZE
            ]
        team = factories.TeamFactory(
            attendees=team_members
        )
        team_participants.extend(team_members)
        teams.append(team)
        attendee_subset_index += TEAM_SIZE
    projects = []
    for team in teams:
        project = factories.ProjectFactory(
            team=team
        )
        projects.append(project)
    mentor_help_requests = []
    for participant in random.sample(team_participants, NUMBER_OF_MENTOR_HELP_REQUESTS):
        try:
            team = Team.objects.for_event(
                event_context.get_current_event()
            ).filter(attendees__id=participant.id).first()
        except Team.DoesNotExist:
            continue
        mentor_help_request = factories.MentorHelpRequestFactory(
            reporter=participant,
            team=team,
        )
        mentor_help_requests.append(mentor_help_request)
    hardware = []
    hardware_devices = []
    hardware_requests = []
    for _ in range(NUMBER_OF_HARDWARE_TYPES):
        hardware_type = factories.HardwareFactory()
        hardware.append(hardware_type)
    for _ in range(NUMBER_OF_HARDWARE_REQUESTS):
        hardware_request = factories.HardwareRequestFactory()
        hardware_requests.append(hardware_request)
    for _ in range(NUMBER_OF_HARDWARE_TYPES * NUMBER_OF_HARDWARE_DEVICES):
        # no checkout.
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
    attendee_preferences = []
    for preferer in random.sample(attendees, NUMBER_OF_ATTENDEES):
        for preferee in random.sample(attendees, NUMBER_OF_TEAMS):
            if preferer != preferee:
                if (preferer.participation_class == "P" and
                        preferee.participation_class == "P"):
                    attendee_preference = factories.AttendeePreferenceFactory(
                        preferer=preferer, preferee=preferee
                    )
                    attendee_preferences.append(attendee_preference)


class Command(BaseCommand):  # pragma: no cover
    help = "Generates test data"

    @transaction.atomic
    def handle(self, *args, **kwargs):  # noqa: C901
        self.stdout.write("Deleting old data...")
        delete_all()
        active_event = Event.objects.get(is_active=True)
        if not active_event:
            active_event = Event.objects.create(
                name="Test Event",
                start_date=datetime.now(),
                end_date=datetime.now() + timedelta(days=3),
                is_active=True
            )

        event_context.set_current_event(active_event)
        self.stdout.write("Creating new data...")
        add_all()
        event_context.set_current_event(None)
