import os
import shutil
import uuid

import pycountry
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_delete
from django.utils.translation import gettext_lazy as _
from multiselectfield import MultiSelectField
from phonenumber_field.modelfields import PhoneNumberField
from simple_history.models import HistoricalRecords

# settings.AUTH_USER_MODEL


class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name}"


class SkillProficiency(models.Model):
    class Proficiency(models.TextChoices):
        NOVICE = 'N', _('Novice')
        COMPETENT = 'C', _('Competent')
        PROFICIENT = 'P', _('Proficient')
        MASTER = 'M', _('Master')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    proficiency = models.CharField(
        max_length=1,
        choices=Proficiency.choices,
        default=Proficiency.NOVICE
    )
    attendee = models.ForeignKey('Attendee', on_delete=models.CASCADE, null=True)
    application = models.ForeignKey('Application', on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "skill proficiencies"
        unique_together = [['attendee', 'skill']]

    def __str__(self) -> str:  # pragma: no cover
        return f"Skill: {self.skill}, Proficiency: {self.proficiency}"
    

class ShirtSize(models.TextChoices):
        XS = 1, _('XS')
        S = 2, _('S')
        M = 3, _('M')
        L = 4, _('L')
        XL = 5, _('XL')
        XXL = 6, _('XXL')


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f"{instance.id}/{filename}"


def file_cleanup(sender, **kwargs):
    file_location = kwargs["origin"].file.path
    shutil.rmtree(os.path.dirname(file_location), ignore_errors=True)


class UploadedFile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=user_directory_path)
    claimed = models.BooleanField(null=False, default=False)  # If file remains unclaimed, eventually delete
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "uploaded files"


class Application(models.Model):
    class Status(models.TextChoices):
        ACCEPTED_IN_PERSON = 'AI', _('Accepted, In-Person')
        ACCEPTED_ONLINE = 'AO', _('Accepted, Online')
        WAITLIST_IN_PERSON = 'WI', _('Wait-list, In-Person')
        WAITLIST_ONLINE = 'WO', _('Wait-list, Online')
        DECLINED = 'D', _('Declined')

    class AgeGroup(models.TextChoices):
        A = 'A', _('17 or younger')
        B = 'B', _('18 to 20')
        C = 'C', _('21 to 29')
        D = 'D', _('30 to 39')
        E = 'E', _('40 to 49')
        F = 'F', _('50 to 59')
        G = 'G', _('60 or older')
        H = 'H', _('I prefer not to say')

    GENDER_IDENTITIES = (('A', 'Cisgender female'),
                       ('B', 'Cisgender male'),
                       ('C', 'Transgender female'),
                       ('D', 'Transgender male'),
                       ('E', 'Gender non-conforming, non-binary, or gender queer'),
                       ('F', 'Two-spirit'),
                       ('G', 'Other'),
                       ('H', 'I prefer not to say'))
    
    RACE_ETHNIC_GROUPS = (('A', 'Asian, Asian American, or of Asian descent'),
                       ('B', 'Black, African American, or of African descent'),
                       ('C', 'Hispanic, Latino, Latina, Latinx, or of Latinx or Spanish-speaking descent'),
                       ('D', 'Middle Eastern, North African, or of North African descent'),
                       ('E', 'Native American, American Indian, Alaska Native, or Indigenous'),
                       ('F', 'Pacific Islander or Native Hawaiian'),
                       ('G', 'White or of European descent'),
                       ('H', 'Multi-racial or multi-ethnic'),
                       ('I', 'Other'),
                       ('J', 'I prefer not to say'))
    
    class DisabilityIdentity(models.TextChoices):
        A = 'A', _('Yes')
        B = 'B', _('No')
        C = 'C', _('I prefer not to say')

    DISABILITIES = (('A', 'Hearing difficulty - Deaf or having serious difficulty hearing (DEAR).'),
                    ('B', 'Vision difficulty - Blind or having serious difficulty seeing, even when wearing glasses (DEYE).'),
                    ('C', 'Cognitive difficulty - Because of a physical, mental, or emotional problem, having difficulty remembering, concentrating, or making decisions (DREM).'),
                    ('D', 'Ambulatory difficulty - Having serious difficulty walking or climbing stairs (DPHY).'),
                    ('E', 'Self-care difficulty - Having difficulty bathing or dressing (DDRS).'),
                    ('F', 'Independent living difficulty - Because of a physical, mental, or emotional problem, having difficulty doing errands alone such as visiting a doctor\'s office or shopping (DOUT).'),
                    ('G', 'I prefer not to say'))
    
    class ParticipationCapacity(models.TextChoices):
        STUDENT = 'S', _('Student'),
        PROFESSIONAL = 'P', _('Professional')
        HOBBYIST = 'H', _('Hobbyist')

    PREVIOUS_PARTICIPATION = (('A', '2016'),
                              ('B', '2017'),
                              ('C', '2018'),
                              ('D', '2019'),
                              ('E', '2020'),
                              ('F', '2022'),
                              ('G', '2023'))

    class ParticipationRole(models.TextChoices):
        DESIGNER = 'A', _('Designer')
        DEVELOPER = 'D', _('Developer')
        SPECIALIST = 'S', _('Specialist')

    class HeardAboutUs(models.TextChoices):
        FRIEND = 'F', _('A friend')
        VOLUNTEER = 'V', _('A Reality Hack organizer or volunteer')
        NETWORK = 'N', _('A teacher or someone in my professional network')
        SOCIAL = 'S', _('Social media')
        CAMPUS = 'C', _('Campus poster or ad')
        PARTICIPATED = 'P', _('I participated in the MIT XR Hackathon before')
        OTHER = 'O', _('Other')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100, blank=False, null=False)
    middle_name = models.CharField(max_length=100, blank=False, null=True)
    last_name = models.CharField(max_length=100, blank=False, null=False)
    nationality = models.CharField(max_length=100, blank=False, null=False)
    current_country = models.CharField(max_length=100, blank=False, null=False)
    current_city = models.CharField(max_length=100, blank=False, null=False)
    pronouns = models.CharField(max_length=30, blank=False, null=True)
    age_group = models.CharField(
        max_length=1,
        choices=AgeGroup.choices,
        default=AgeGroup.H,
        null=False
    )
    bio = models.TextField(max_length=1000, blank=True)
    email = models.EmailField(blank=False, null=False)
    event_year = models.IntegerField(default=2024, null=False)
    portfolio = models.URLField()
    resume = models.URLField()
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    nationality = models.CharField(max_length=100)
    gender_identity = MultiSelectField(choices=GENDER_IDENTITIES, max_choices=8, max_length=8)
    race_ethnic_group = MultiSelectField(choices=RACE_ETHNIC_GROUPS, max_choices=10, max_length=10)
    disability_identity = models.CharField(
        max_length=1,
        choices=DisabilityIdentity.choices,
        default=DisabilityIdentity.C,
        null=False
    )
    disabilities = MultiSelectField(choices=DISABILITIES, max_choices=7, max_length=7, null=True)
    disability_accommodations = models.TextField(max_length=1000, blank=True, null=True)
    participation_capacity = models.CharField(
        max_length=1,
        choices=ParticipationCapacity.choices,
        default=ParticipationCapacity.HOBBYIST,
        null=False
    )
    student_school = models.CharField(max_length=100, null=True, blank=False)
    student_field_of_study = models.CharField(max_length=100, null=True, blank=False)
    occupation = models.CharField(max_length=100, null=True, blank=False)
    employer = models.CharField(max_length=100, null=True, blank=False)
    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        null=True,
        default=None
    )
    previously_participated = models.BooleanField(default=False, null=False)
    previous_participation = MultiSelectField(choices=PREVIOUS_PARTICIPATION, max_choices=7, max_length=7)
    participation_role = models.CharField(
        max_length=1,
        choices=ParticipationRole.choices,
        default=ParticipationRole.SPECIALIST,
        null=True
    )
    experience_with_xr = models.BooleanField(default=False, null=False)
    theme_essay = models.TextField(max_length=1000, blank=True, null=True)
    theme_essay_follow_up = models.TextField(max_length=1000, blank=True, null=True)
    heard_about_us = models.CharField(
        max_length=1,
        choices=HeardAboutUs.choices,
        null=True,
        default=None
    )
    shirt_size = models.CharField(
        max_length=1,
        choices=ShirtSize.choices,
        default=ShirtSize.M,
        null=True
    )
    communications_platform_username = models.CharField(max_length=40, null=True)
    dietary_restrictions = models.TextField(max_length=200, blank=True, null=True)
    additional_accommodations = models.TextField(max_length=200, blank=True, null=True)
    phone_number_country_alpha_2_options = models.CharField(
        max_length=2,
        choices=[(x.alpha_2, x.name) for x in pycountry.countries],
        default='US',
        null=True
    )
    phone_number = PhoneNumberField(blank=False, null=False)
    emergency_contact_name = models.CharField(max_length=200, null=False, blank=False)
    emergency_contact_phone_number = PhoneNumberField(blank=False, null=False)
    emergency_contact_email = models.EmailField(blank=False, null=False)
    emergency_contact_relationship = models.CharField(max_length=100, null=False, blank=False)
    parental_consent_form = models.OneToOneField(
        UploadedFile, on_delete=models.DO_NOTHING,
        related_name="application_parental_constent_form_uploaded_file",
        null=True
    )
    us_visa_support_is_required = models.BooleanField(null=False)
    us_visa_support_full_name = models.CharField(max_length=200, blank=False, null=True)
    us_visa_support_passport_number = models.CharField(max_length=50, blank=False, null=True)
    us_visa_support_national_identification_document_information = models.CharField(max_length=100, blank=False, null=True)
    us_visa_support_citizenship = models.CharField(
        max_length=2,
        choices=[(x.alpha_2, x.name) for x in pycountry.countries],
        blank=False,
        null=True
    )
    us_visa_support_address_line_1 = models.CharField(max_length=200, null=True, blank=False)
    us_visa_support_address_line_2 = models.CharField(max_length=200, null=True, blank=False)
    media_release = models.OneToOneField(
        UploadedFile, on_delete=models.DO_NOTHING,
        related_name="application_media_release_form_uploaded_file",
        null=True
    )
    liability_release = models.OneToOneField(
        UploadedFile, on_delete=models.DO_NOTHING,
        related_name="application_liability_release_form_uploaded_file",
        null=True
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: nocover
        return f"Name: {self.first_name} {self.last_name}, Portfolio: {self.portfolio}"


class Attendee(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, null=True, blank=True)
    bio = models.TextField(max_length=1000, blank=True)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = "attendees"
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['first_name',]),
            models.Index(fields=['last_name']),
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['is_staff']),
            models.Index(fields=['metadata'])
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Name: {self.first_name} {self.last_name}, Email: {self.email}"


class Location(models.Model):
    class Room(models.TextChoices):
        MAIN_HALL = 'MH', _('Main Hall')
        ATLANTIS = 'AT', _('Atlantis')

    class Building(models.TextChoices):
        pass

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    building = models.CharField(
        max_length=2,
        choices=Building.choices
    )
    room = models.CharField(
        max_length=2,
        choices=Room.choices,
        default=Room.MAIN_HALL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Building: {self.building}, Room: {self.room}"


class Table(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.PositiveBigIntegerField()
    location = models.ForeignKey(Location, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.number}"


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    attendees = models.ManyToManyField(Attendee)
    table = models.OneToOneField(Table, on_delete=models.DO_NOTHING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['table'])
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Name: {self.name}, Table: {self.table}"


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    repository_location = models.URLField()
    submission_location = models.URLField()
    team = models.OneToOneField(Team, on_delete=models.DO_NOTHING, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name}"


class HelpDesk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    announcement_pending = models.BooleanField(default=False)
    mentor_requested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Table: {self.table}, IP: {self.ip_address}"


class Hardware(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=1000, blank=True)
    image = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Name: {self.name}"


class HardwareDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hardware = models.ForeignKey(Hardware, on_delete=models.CASCADE)
    serial = models.CharField(max_length=100)
    checked_out_to = models.ForeignKey(
        Attendee, on_delete=models.CASCADE, null=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self) -> str:  # pragma: no cover
        return f"Hardware: {self.hardware}, Serial: {self.serial}"


post_delete.connect(
    file_cleanup, sender=UploadedFile, dispatch_uid="file"
)
