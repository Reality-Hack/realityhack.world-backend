from datetime import datetime

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
    current_country = factory.Faker(
        'random_element', elements=[[x.alpha_2] for x in pycountry.countries]
    )
    current_city = factory.Faker("city")
    pronouns = factory.fuzzy.FuzzyText(length=10)
    age_group = factory.Faker("random_element", elements=[
        x[0] for x in models.Application.AgeGroup.choices])
    email = factory.Faker("email")
    portfolio = factory.Faker("url")
    secondary_portfolio = factory.Faker("url")
    resume = factory.Iterator(models.UploadedFile.objects.all())
    nationality = factory.Faker(
        'random_element', elements=[[x.alpha_2] for x in pycountry.countries]
    )
    status = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.Status.choices]
    )
    gender_identity = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.GENDER_IDENTITIES]
    )
    race_ethnic_group = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.RACE_ETHNIC_GROUPS]
    )
    disability_identity = factory.Faker(
        'random_element', elements=[x[0] for x in models.DisabilityIdentity.choices]
    )
    disabilities = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.DISABILITIES]
    )
    disability_accommodations = factory.fuzzy.FuzzyText(length=500)
    participation_capacity = factory.Faker(
        'random_element', elements=[x[0] for x in models.ParticipationCapacity.choices]
    )
    student_school = factory.fuzzy.FuzzyText(length=90)
    student_field_of_study = factory.fuzzy.FuzzyText(length=90)
    occupation = factory.fuzzy.FuzzyText(length=90)
    employer = factory.fuzzy.FuzzyText(length=90)
    industry = factory.Faker(
        'random_element', elements=[[x[0]] for x in models.INDUSTRIES]
    )
    specialized_expertise = factory.fuzzy.FuzzyText(length=90)
    previously_participated = factory.Faker("boolean")
    previous_participation = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.PREVIOUS_PARTICIPATION]
    )
    participation_role = factory.Faker(
        'random_element', elements=[x[0] for x in models.ParticipationRole.choices]
    )
    experience_with_xr = factory.fuzzy.FuzzyText(length=900)
    theme_essay = factory.fuzzy.FuzzyText(length=900)
    theme_essay_follow_up = factory.fuzzy.FuzzyText(length=900)
    hardware_hack_interest = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.HardwareHackInterest.choices]
    )
    heard_about_us = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.HeardAboutUs.choices]
    )
    digital_designer_skills = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.DigitalDesignerProficientSkills.choices]
    )
    communications_platform_username = factory.Faker("user_name")
    outreach_groups = factory.fuzzy.FuzzyText(length=900)


class AttendeeFactory(DjangoModelFactory):
    class Meta:
        model = models.Attendee
        django_get_or_create = ('username', )

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    bio = factory.fuzzy.FuzzyText(length=1000)
    email = factory.Faker("email")
    username = factory.Faker("user_name")
    application = factory.Iterator(models.Application.objects.filter(status=models.Application.Status.ACCEPTED_IN_PERSON))
    authentication_id = None
    shirt_size = factory.Faker(
        'random_element', elements=[x[0] for x in models.ShirtSize.choices]
    )
    communications_platform_username = factory.Faker("user_name")
    dietary_restrictions = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.DietaryRestrictions.choices]
    )
    dietary_restrictions_other = None
    dietary_allergies = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.DietaryAllergies.choices]
    )
    dietary_allergies_other = None
    additional_accommodations = factory.fuzzy.FuzzyText(length=100)
    us_visa_support_is_required = False
    us_visa_letter_of_invitation_required = None
    us_visa_support_full_name = None
    us_visa_support_document_number = None
    us_visa_support_national_identification_document_type = None
    us_visa_support_citizenship = None
    us_visa_support_address = None
    under_18_by_date = False
    parental_consent_form_signed = None
    agree_to_media_release = True
    agree_to_liability_release = True
    agree_to_rules_code_of_conduct = True
    emergency_contact_name = factory.Faker("first_name")
    personal_phone_number = factory.Faker("phone_number")
    emergency_contact_phone_number = factory.Faker("phone_number")
    emergency_contact_email = email = factory.Faker("email")
    emergency_contact_relationship = factory.fuzzy.FuzzyText(length=10)
    special_track_snapdragon_spaces_interest = None
    special_track_future_constructors_interest = None
    app_in_store = False
    currently_build_for_xr = True
    currently_use_xr = True
    non_xr_talents = None
    ar_vr_ap_in_store = None
    reality_hack_project_to_product = False
    participation_class = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.ParticipationClass.choices]
    )
    # sponsor
    sponsor_company = None


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


class WorkshopFactory(DjangoModelFactory):
    class Meta:
        model = models.Workshop

    name = factory.Faker("company")
    datetime = datetime.now()
    duration = 10
    description = factory.fuzzy.FuzzyText(length=100)
    location = factory.Iterator(models.Location.objects.all())
    course_materials = factory.Faker("url")
    recommended_for = factory.Faker(
        'random_element', elements=[x[0] for x in models.ParticipationRole.choices]
    )

    @factory.post_generation
    def skills(self, create, extracted, **kwargs):
        if not create:
            return  # pragma: no cover

        if extracted:
            for skill in extracted:
                self.skills.add(skill)

    @factory.post_generation
    def hardware(self, create, extracted, **kwargs):
        if not create:
            return  # pragma: no cover

        if extracted:
            for hardware in extracted:
                self.hardware.add(hardware)


class WorkshopAttendeeFactory(DjangoModelFactory):
    class Meta:
        model = models.WorkshopAttendee

    workshop = factory.Iterator(models.Workshop.objects.all())
    attendee = factory.Iterator(models.Attendee.objects.all())
    participation = factory.Faker('random_element', elements=[
        x[0] for x in models.WorkshopAttendee.Participation.choices]
    )
