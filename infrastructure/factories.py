import factory
import factory.fuzzy
import pycountry
from django.contrib.auth.models import Group
from factory.django import DjangoModelFactory

from infrastructure import models


class UploadedFileFactory(DjangoModelFactory):
    class Meta:
        model = models.UploadedFile

    file = factory.django.ImageField(
        color="green", filename="saved_file.pdf")
    claimed = False


class ApplicationFactory(DjangoModelFactory):
    class Meta:
        model = models.Application
    
    first_name = factory.Faker("first_name")
    middle_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    nationality = factory.Faker("country")
    current_country = factory.Faker("country")
    current_city = factory.Faker("city")
    pronouns = factory.fuzzy.FuzzyText(length=10)
    age_group = factory.Faker("random_element", elements=[
        x[0] for x in models.Application.AgeGroup.choices])
    bio = factory.fuzzy.FuzzyText(length=1000)
    email = factory.Faker("email")
    portfolio = factory.Faker("url")
    resume = factory.Faker("url")
    city = factory.Faker("city")
    country = factory.Faker("country")
    nationality = factory.Faker("country")
    gender_identity = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.GENDER_IDENTITIES]
    )
    race_ethnic_group = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.RACE_ETHNIC_GROUPS]
    )
    disability_identity = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.DisabilityIdentity.choices]
    )
    disabilities = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.DISABILITIES]
    )
    disability_accommodations = factory.fuzzy.FuzzyText(length=500)
    participation_capacity = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.ParticipationCapacity.choices]
    )
    student_school = factory.fuzzy.FuzzyText(length=90)
    student_field_of_study = factory.fuzzy.FuzzyText(length=90)
    occupation = factory.fuzzy.FuzzyText(length=90)
    employer = factory.fuzzy.FuzzyText(length=90)
    previously_participated = factory.Faker("boolean")
    previous_participation = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.PREVIOUS_PARTICIPATION]
    )
    participation_role = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.ParticipationRole.choices]
    )
    experience_with_xr = factory.fuzzy.FuzzyText(length=900)
    theme_essay = factory.fuzzy.FuzzyText(length=900)
    theme_essay_follow_up = factory.fuzzy.FuzzyText(length=900)
    heard_about_us = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.HeardAboutUs.choices]
    )
    shirt_size = factory.Faker(
        'random_element', elements=[x[0] for x in models.ShirtSize.choices]
    )
    communications_platform_username = factory.Faker("user_name")
    dietary_restrictions = factory.fuzzy.FuzzyText(length=80)
    additional_accommodations = factory.fuzzy.FuzzyText(length=80)
    us_visa_support_is_required = factory.Faker("boolean")
    us_visa_support_full_name = factory.Faker("name")
    us_visa_support_passport_number = factory.fuzzy.FuzzyText(length=10)
    us_visa_support_national_identification_document_information = factory.fuzzy.FuzzyText(length=99)
    us_visa_support_citizenship = factory.Faker(
        'random_element', elements=[x.alpha_2 for x in pycountry.countries]
    )
    us_visa_support_address_line_1 = factory.Faker("address")
    us_visa_support_address_line_2 = factory.Faker("address")
    parental_consent_form = factory.SubFactory(UploadedFileFactory)
    media_release = factory.SubFactory(UploadedFileFactory)
    liability_release = factory.SubFactory(UploadedFileFactory)


class AttendeeFactory(DjangoModelFactory):
    class Meta:
        model = models.Attendee
        django_get_or_create = ('username', )

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    bio = factory.fuzzy.FuzzyText(length=1000)
    email = factory.Faker("email")
    username = factory.Faker("user_name")
    metadata = factory.Dict({"shirt_size": factory.Faker("name")})


class GroupFactory(DjangoModelFactory):
    class Meta:
        model = Group

    name = factory.Faker('job')


class SkillFactory(DjangoModelFactory):
    class Meta:
        model = models.Skill

    name = factory.Faker("company")


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


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = models.Project

    name = factory.Faker("company")
    repository_location = factory.Faker("url")
    submission_location = factory.Faker("url")

    @factory.post_generation
    def team(self, create, team, **kwargs):
        if not create:
            return  # pragma: no cover

        if team:
            self.team = team


class SkillProficiencyFactory(DjangoModelFactory):
    class Meta:
        model = models.SkillProficiency

    skill = factory.Iterator(models.Skill.objects.all())
    proficiency = factory.Faker(
        'random_element', elements=[x[0] for x in models.SkillProficiency.Proficiency]
    )


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = models.Team

    name = factory.Faker("company")
    table = factory.Iterator(models.Table.objects.all())

    @factory.post_generation
    def attendees(self, create, extracted, **kwargs):
        if not create:
            return  # pragma: no cover

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
