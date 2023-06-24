import factory
import factory.fuzzy
from factory.django import DjangoModelFactory

from infrastructure import models


class AttendeeFactory(DjangoModelFactory):
    class Meta:
        model = models.Attendee
        django_get_or_create = ('username', )

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    bio = factory.fuzzy.FuzzyText(length=1000)
    email = factory.Faker("email")
    username = factory.Faker("user_name")
    roles = factory.Faker(
        'random_element', elements=[x[0] for x in models.Attendee.ROLES]
    )


class SkillFactory(DjangoModelFactory):
    class Meta:
        model = models.Skill

    name = factory.Faker("catch_phrase")


class TableFactory(DjangoModelFactory):
    class Meta:
        model = models.Table

    number = factory.Sequence(lambda n: n + 1)
    location = factory.Iterator(models.Location.objects.all())


class HelpDeskFactory(DjangoModelFactory):
    class Meta:
        model = models.HelpDesk

    table = factory.Iterator(models.Table.objects.all())
    ip_address = factory.Faker("ipv4_private")
    announcement_pending = factory.Faker("boolean")
    mentor_requested = factory.Faker("boolean")
    auxiliary_requested = factory.Faker("boolean")


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = models.Project

    name = factory.Faker("company")
    repository_location = factory.Faker("url")
    submission_location = factory.Faker("url")


class SkillProficiencyFactory(DjangoModelFactory):
    class Meta:
        model = models.SkillProficiency
    skill = factory.Iterator(models.Skill.objects.all())
    proficiency = factory.Faker(
        'random_element', elements=[x[0] for x in models.SkillProficiency.Proficiency]
    )
    attendee = factory.Iterator(models.Attendee.objects.all())


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = models.Team

    name = factory.Faker("company")
    table = factory.Iterator(models.Table.objects.all())
    project = factory.SubFactory(ProjectFactory)

    @factory.post_generation
    def attendees(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for attendee in extracted:
                self.attendees.add(attendee)


class HardwareFactory(DjangoModelFactory):
    class Meta:
        model = models.Hardware

    name = factory.Faker("company")
    description = factory.fuzzy.FuzzyText(length=100)
    image = factory.Faker("url")


class HardwareDeviceFactory(DjangoModelFactory):
    class Meta:
        model = models.HardwareDevice

    hardware = factory.Iterator(models.Hardware.objects.all())
    serial = factory.fuzzy.FuzzyText(length=50)
    checked_out_to = factory.Iterator(models.Attendee.objects.all())