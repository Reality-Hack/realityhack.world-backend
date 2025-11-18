import factory
import factory.fuzzy
import pycountry
from django.contrib.auth.models import Group
from factory.django import DjangoModelFactory
from django.utils import timezone

from infrastructure import models
from infrastructure import event_context


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
        'random_element', elements=[str(x[0]) for x in models.Application.GenderIdentities]
    )
    race_ethnic_group = factory.Faker(
        'random_element', elements=[str(x[0]) for x in models.Application.RaceEthnicGroups]
    )
    disability_identity = factory.Faker(
        'random_element', elements=[x[0] for x in models.DisabilityIdentity.choices]
    )
    # disabilities = factory.Faker(
    #     'random_element', elements=[str(x[0]) for x in models.Application.DISABILITIES]
    # )
    # disability_accommodations = factory.fuzzy.FuzzyText(length=500)
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
        'random_element', elements=[str(x[0]) for x in models.Application.PreviousParticipation]
    )
    participation_role = factory.Faker(
        'random_element', elements=[x[0] for x in models.ParticipationRole.choices]
    )
    experience_with_xr = factory.fuzzy.FuzzyText(length=900)
    other_skills_experiences = factory.fuzzy.FuzzyText(length=900)
    experience_contribution = factory.fuzzy.FuzzyText(length=900)
    theme_essay = factory.fuzzy.FuzzyText(length=900)
    theme_essay_follow_up = factory.fuzzy.FuzzyText(length=900)
    hardware_hack_interest = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.HardwareHackInterest.choices]
    )
    hardware_hack_detail = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.HardwareHackDetail.choices]
    )
    heard_about_us = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.HeardAboutUs.choices]
    )
    digital_designer_skills = factory.Faker(
        'random_element', elements=[x[0] for x in models.Application.DigitalDesignerProficientSkills.choices]
    )
    communications_platform_username = factory.Faker("user_name")
    outreach_groups = factory.fuzzy.FuzzyText(length=900)
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class AttendeeFactory(DjangoModelFactory):
    class Meta:
        model = models.Attendee
        django_get_or_create = ('username', )

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    bio = factory.fuzzy.FuzzyText(length=1000)
    authentication_id = factory.Faker("uuid4")
    email = factory.Faker("email")
    username = factory.Faker("user_name")
    application = factory.LazyFunction(
        lambda: models.Application.objects.for_event(
            event_context.get_current_event()
        ).filter(status=models.Application.Status.ACCEPTED_IN_PERSON).order_by('?').first()
    )
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
    participation_role = factory.Faker(
        'random_element', elements=[x[0] for x in models.ParticipationRole.choices]
    )
    intended_tracks = factory.Faker(
        'random_sample', elements=[x[0] for x in models.Track.choices], length=2
    )
    intended_hardware_hack = factory.Faker(
        'random_element', elements=[True, False]
    )
    prefers_destiny_hardware = factory.Faker(
        'random_sample', elements=[x[0] for x in models.DestinyHardware.choices], length=3
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
    special_interest_track_one = None
    special_interest_track_two = None
    app_in_store = False
    currently_build_for_xr = True
    currently_use_xr = True
    non_xr_talents = None
    ar_vr_ap_in_store = None
    reality_hack_project_to_product = False
    participation_class = factory.Faker(
        'random_element', 
        elements=[str(x[0]) for x in models.ParticipationClass.choices]
    )
    # sponsor
    sponsor_company = None


# https://github.com/FactoryBoy/factory_boy/issues/305
class UniqueFaker(factory.Faker):
    def evaluate(self, instance, step, extra):
        locale = extra.pop('locale')
        subfaker = self._get_faker(locale)
        unique_proxy = subfaker.unique
        return unique_proxy.format(self.provider, **extra)


class GroupFactory(DjangoModelFactory):
    class Meta:
        model = Group

    name = UniqueFaker('job')


class SkillFactory(DjangoModelFactory):
    class Meta:
        model = models.Skill

    name = UniqueFaker("company")
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class TableFactory(DjangoModelFactory):
    class Meta:
        model = models.Table

    number = factory.Sequence(lambda n: n + 1)
    location = factory.LazyFunction(
        lambda: models.Location.objects.for_event(
            event_context.get_current_event()
        ).order_by('?').first()
    )
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class LightHouseFactory(DjangoModelFactory):
    class Meta:
        model = models.LightHouse

    table = factory.LazyFunction(
        lambda: models.Table.objects.for_event(
            event_context.get_current_event()
        ).order_by('?').first()
    )
    ip_address = factory.Faker("ipv4_private")
    announcement_pending = "F"
    mentor_requested = "F"
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class MentorHelpRequestFactory(DjangoModelFactory):
    class Meta:
        model = models.MentorHelpRequest

    title = factory.fuzzy.FuzzyText(length=30)
    description = factory.fuzzy.FuzzyText(length=500)
    reporter = factory.Iterator(
        models.Attendee.objects.filter(
            participation_class=models.ParticipationClass.PARTICIPANT
        )
    )
    mentor = factory.Iterator(
        models.Attendee.objects.filter(
            participation_class=models.ParticipationClass.MENTOR
        )
    )
    team = factory.LazyFunction(
        lambda: models.Team.objects.for_event(
            event_context.get_current_event()
        ).order_by('?').first()
    )
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class ProjectFactory(DjangoModelFactory):
    class Meta:
        model = models.Project

    name = factory.Faker("company")
    repository_location = factory.Faker("url")
    submission_location = factory.Faker("url")
    description = factory.fuzzy.FuzzyText(length=200)
    event = factory.LazyFunction(lambda: event_context.get_current_event())

    @factory.post_generation
    def team(self, create, team, **kwargs):
        if not create:
            return  # pragma: no cover

        if team:
            self.team = team


class SkillProficiencyFactory(DjangoModelFactory):
    class Meta:
        model = models.SkillProficiency

    skill = factory.LazyFunction(
        lambda: models.Skill.objects.for_event(
            event_context.get_current_event()
        ).order_by('?').first()
    )
    proficiency = factory.Faker(
        'random_element', elements=[x[0] for x in models.SkillProficiency.Proficiency]
    )
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = models.Team

    name = factory.Faker("company")
    event = factory.LazyFunction(lambda: event_context.get_current_event())

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
    image = factory.SubFactory(UploadedFileFactory)
    tags = factory.Faker(
        'random_elements', elements=[x[0] for x in models.HardwareTags.choices],
        length=2
    )
    relates_to_destiny_hardware = factory.Faker(
        'random_element', elements=[x[0] for x in models.DestinyHardware.choices]
    )
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class HardwareDeviceFactory(DjangoModelFactory):
    class Meta:
        model = models.HardwareDevice

    hardware = factory.LazyFunction(
        lambda: models.Hardware.objects.for_event(
            event_context.get_current_event()
        ).order_by('?').first()
    )
    serial = factory.fuzzy.FuzzyText(length=50)
    checked_out_to = factory.Iterator(
        models.HardwareRequest.objects.for_event(
            event_context.get_current_event()
        ).filter(hardware_device__isnull=True)
    )
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class HardwareRequestFactory(DjangoModelFactory):
    class Meta:
        model = models.HardwareRequest

    hardware = factory.LazyFunction(
        lambda: models.Hardware.objects.for_event(
            event_context.get_current_event()
        ).order_by('?').first()
    )
    requester = factory.Iterator(models.Attendee.objects.all())
    reason = factory.fuzzy.FuzzyText(length=900)
    team = factory.LazyFunction(
        lambda: models.Team.objects.for_event(
            event_context.get_current_event()
        ).order_by('?').first()
    )
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class WorkshopFactory(DjangoModelFactory):
    class Meta:
        model = models.Workshop

    name = factory.Faker("company")
    datetime = timezone.now().replace(tzinfo=timezone.utc)
    duration = 10
    description = factory.fuzzy.FuzzyText(length=100)
    location = factory.LazyFunction(
        lambda: models.Location.objects.for_event(
            event_context.get_current_event()
        ).order_by('?').first()
    )
    course_materials = factory.Faker("url")
    recommended_for = factory.Faker(
        'random_element', elements=[x[0] for x in models.ParticipationRole.choices]
    )
    event = factory.LazyFunction(lambda: event_context.get_current_event())

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

    workshop = factory.LazyFunction(
        lambda: models.Workshop.objects.for_event(
            event_context.get_current_event()
        ).order_by('?').first()
    )
    attendee = factory.Iterator(models.Attendee.objects.all())
    participation = factory.Faker('random_element', elements=[
        x[0] for x in models.WorkshopAttendee.Participation.choices]
    )
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class AttendeePreferenceFactory(DjangoModelFactory):
    class Meta:
        model = models.AttendeePreference

    preferer = factory.Iterator(models.Attendee.objects.filter(participation_class="P"))
    preferee = factory.Iterator(models.Attendee.objects.filter(participation_class="P"))
    preference = factory.Faker('random_element', elements=[
        x[0] for x in models.AttendeePreference.Preference.choices]
    )
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class DestinyTeamAttendeeVibeFactory(DjangoModelFactory):
    class Meta:
        model = models.DestinyTeamAttendeeVibe

    destiny_team = factory.LazyFunction(
        lambda: models.DestinyTeam.objects.for_event(
            event_context.get_current_event()
        ).order_by('?').first()
    )
    attendee = factory.Iterator(
        models.Attendee.objects.filter(participation_class="P")
    )
    vibe = factory.fuzzy.FuzzyInteger(low=1, high=5)
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = models.Location

    building = factory.Faker(
        'random_element',
        elements=[x[0] for x in models.Location.Building.choices]
    )
    room = factory.Faker(
        'random_element',
        elements=[x[0] for x in models.Location.Room.choices]
    )
    event = factory.LazyFunction(lambda: event_context.get_current_event())


class EventFactory(DjangoModelFactory):
    class Meta:
        model = models.Event

    name = factory.Faker("company")
    start_date = factory.Faker(
        "date_time_between",
        start_date="-30d",
        end_date="+0d",
        tzinfo=timezone.utc
    )
    end_date = factory.Faker(
        "date_time_between",
        start_date="+1d",
        end_date="+60d",
        tzinfo=timezone.utc
    )
    is_active = False
