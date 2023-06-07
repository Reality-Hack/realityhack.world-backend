import factory
from factory.django import DjangoModelFactory
from faker import Faker

from infrastructure import models

class AttendeeFactory(DjangoModelFactory):
    class Meta:
        model = models.Attendee
        django_get_or_create = ('username', )

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    username = factory.Faker("user_name")


class SkillFactory(DjangoModelFactory):
    class Meta:
        model = models.Skill

    name = factory.Faker("catch_phrase")


class TableFactory(DjangoModelFactory):
    class Meta:
        model = models.Table

    number = factory.Sequence(lambda n: n + 1)
    location = factory.Iterator(models.Location.objects.all())


class RealityKitFactory(DjangoModelFactory):
    class Meta:
        model = models.RealityKit

    table = factory.Iterator(models.Table.objects.all())
    ip_address = factory.Faker("ipv4_private")
    announcement_pending = factory.Faker("boolean")
    mentor_requested = factory.Faker("boolean")
    auxiliary_requested = factory.Faker("boolean")


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = models.Project

    location = factory.Faker("url")


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