import os
import shutil
import sys
import uuid

import language_tags
import pycountry
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.utils.translation import gettext_lazy as _
from multiselectfield import MultiSelectField
from phonenumber_field.modelfields import PhoneNumberField
from simple_history.models import HistoricalRecords

from infrastructure import email

# settings.AUTH_USER_MODEL

with open("infrastructure/industries.csv", "r") as f:
    industries = f.read().strip().split(",\n")
    INDUSTRIES = [(x, x) for x in industries]

class ParticipationRole(models.TextChoices):
    DESIGNER = 'A', _('Digital Designer')
    DEVELOPER = 'D', _('Developer')
    SPECIALIST = 'S', _('Domain or other Specialized Skill Expert')
    PROJECT_MANAGER = 'P', _('Project Manager')


class ParticipationCapacity(models.TextChoices):
    STUDENT = 'S', _('Student'),
    PROFESSIONAL = 'P', _('Professional')
    HOBBYIST = 'H', _('Hobbyist')


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


# RFC 5646-compliant mapping of languages
SPOKEN_LANGUAGES = [
    (x["Subtag"], ", ".join(x["Description"]))
    for x in language_tags.data.cache['registry']
    if x["Type"] == "language" and x.get("Scope") != "special"
]


def user_directory_path(instance, filename):
    # file will be uploaded to MEDIA_ROOT/user_<id>/<filename>
    return f"{instance.id}/{filename}"


class UploadedFile(models.Model):
    @classmethod
    def post_delete(cls, sender, **kwargs):
        file_location = kwargs["origin"].file.path
        shutil.rmtree(os.path.dirname(file_location), ignore_errors=True)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=user_directory_path)
    claimed = models.BooleanField(null=False, default=False)  # If file remains unclaimed, eventually delete
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "uploaded files"

    def __str__(self):
        return f"Claimed: {self.claimed}, File: {self.file}"


class Application(models.Model):
    class ParticipationClass(models.TextChoices):
        PARTICIPANT = 'P', _('Participant')
        MENTOR = 'M', _('Mentor')
        JUDGE = 'J', _('Judge')

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
                       ('G', 'I prefer not to say'),
                       ('O', 'Other'))
    
    RACE_ETHNIC_GROUPS = (('A', 'Asian, Asian American, or of Asian descent'),
                       ('B', 'Black, African American, or of African descent'),
                       ('C', 'Hispanic, Latino, Latina, Latinx, or of Latinx or Spanish-speaking descent'),
                       ('D', 'Middle Eastern, North African, or of North African descent'),
                       ('E', 'Native American, American Indian, Alaska Native, or Indigenous'),
                       ('F', 'Pacific Islander or Native Hawaiian'),
                       ('G', 'White or of European descent'),
                       ('H', 'Multi-racial or multi-ethnic'),
                       ('I', 'I prefer not to say'),
                       ('O', 'Other'))
    
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
                    ('G', 'I prefer not to say'),
                    ('O', 'Other'))

    PREVIOUS_PARTICIPATION = (('A', '2016'),
                              ('B', '2017'),
                              ('C', '2018'),
                              ('D', '2019'),
                              ('E', '2020'),
                              ('F', '2022'),
                              ('G', '2023'))

    class HeardAboutUs(models.TextChoices):
        FRIEND = 'F', _('A friend')
        VOLUNTEER = 'V', _('A Reality Hack organizer or volunteer')
        NETWORK = 'N', _('A teacher or someone in my professional network')
        SOCIAL = 'S', _('Social media')
        CAMPUS = 'C', _('Campus poster or ad')
        PARTICIPATED = 'P', _('I participated in the MIT XR Hackathon before')
        OTHER = 'O', _('Other')

    class HardwareHackInterest(models.TextChoices):
        A = 'A', _("Not at all interested; I'll pass")
        B = 'B', _("Some mild interest")
        C = 'C', _("Most likely")
        D = 'D', _("100%; I want to join")

    class DigitalDesignerProficientSkills(models.TextChoices):
        A = 'A', _('Digital Art')
        B = 'B', _('Animation')
        C = 'C', _('Sound')
        D = 'D', _('UX and UI')
        E = 'E', _('Video')
        F = 'F', _('Other')

    @classmethod
    def post_create(cls, sender, instance, created, **kwargs):
        if created:
            # claim resume file
            if instance.resume:
                instance.resume.claimed = True
                instance.resume.save()
            # send email
            if "test" not in sys.argv and "setup_test_data" not in sys.argv:
                subject, body = None, None
                if instance.participation_class == Application.ParticipationClass.MENTOR:
                    subject, body = email.get_mentor_application_confirmation_template(instance.first_name, response_email_address="Jared Bienz <jared@mitrealityhack.com>")
                elif instance.participation_class == Application.ParticipationClass.JUDGE:
                    subject, body = email.get_judge_application_confirmation_template(instance.first_name, response_email_address="Catherine Dumas <catherine@mitrealityhack.com>")
                else:
                    subject, body = email.get_hacker_application_confirmation_template(instance.first_name)
                send_mail(
                    subject,
                    body,
                    "no-reply@mitrealityhack.com",
                    [instance.email],
                    fail_silently=False,
                )

    @classmethod
    def post_delete(cls, sender, instance, **kwargs):
        if instance.resume:
            instance.resume.delete()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100, blank=False, null=False)
    middle_name = models.CharField(max_length=100, blank=False, null=True)
    last_name = models.CharField(max_length=100, blank=False, null=False)
    participation_class = models.CharField(
        choices=ParticipationClass.choices,
        max_length=1,
        null=False,
        default=ParticipationClass.PARTICIPANT
    )
    nationality = MultiSelectField(
        choices=[(x.alpha_2, x.name) for x in pycountry.countries],
        max_choices=8,
        max_length=len(pycountry.countries),
        null=True
    )
    current_country = MultiSelectField(
        choices=[(x.alpha_2, x.name) for x in pycountry.countries],
        max_choices=8,
        max_length=len(pycountry.countries),
        null=True
    )
    current_city = models.CharField(max_length=100, blank=False, null=True)
    pronouns = models.CharField(max_length=30, blank=False, null=True)
    age_group = models.CharField(
        max_length=1,
        choices=AgeGroup.choices,
        default=AgeGroup.H,
        null=True
    )
    email = models.EmailField(blank=False, null=False, unique=True)
    event_year = models.IntegerField(default=2024, null=False)
    portfolio = models.URLField(null=True)
    secondary_portfolio = models.URLField(null=True)
    resume = models.OneToOneField(
        UploadedFile, on_delete=models.DO_NOTHING,
        related_name="application_resume_uploaded_file",
        null=True
    )
    gender_identity = MultiSelectField(choices=GENDER_IDENTITIES, max_choices=8, max_length=len(GENDER_IDENTITIES) * 2)
    gender_identity_other = models.CharField(max_length=20, null=True)
    race_ethnic_group = MultiSelectField(choices=RACE_ETHNIC_GROUPS, max_choices=10, max_length=len(RACE_ETHNIC_GROUPS) * 2)
    race_ethnic_group_other = models.CharField(max_length=20, null=True)
    disability_identity = models.CharField(
        max_length=1,
        choices=DisabilityIdentity.choices,
        default=DisabilityIdentity.C,
        null=True
    )
    disabilities = MultiSelectField(choices=DISABILITIES, max_choices=7, max_length=len(DISABILITIES), null=True)
    disabilities_other = models.CharField(max_length=20, null=True)
    disability_accommodations = models.TextField(max_length=1000, blank=True, null=True)
    participation_capacity = models.CharField(
        max_length=1,
        choices=ParticipationCapacity.choices,
        default=ParticipationCapacity.HOBBYIST,
        null=True
    )
    student_school = models.CharField(max_length=100, null=True, blank=False)
    student_field_of_study = models.CharField(max_length=100, null=True, blank=False)
    occupation = models.CharField(max_length=100, null=True, blank=False)
    employer = models.CharField(max_length=100, null=True, blank=False)
    industry = MultiSelectField(
        max_length=1000,
        choices=INDUSTRIES,
        null=True
    )
    industry_other = models.CharField(max_length=20, null=True)
    specialized_expertise = models.TextField(max_length=1000, blank=False, null=True)
    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        null=True,
        default=None
    )
    previously_participated = models.BooleanField(default=False, null=True)
    previous_participation = MultiSelectField(choices=PREVIOUS_PARTICIPATION, max_choices=7, max_length=len(PREVIOUS_PARTICIPATION) * 2, null=True)
    participation_role = models.CharField(
        max_length=1,
        choices=ParticipationRole.choices,
        default=ParticipationRole.SPECIALIST,
        null=True
    )
    experience_with_xr = models.TextField(max_length=2000, blank=True, null=True)
    theme_essay = models.TextField(max_length=2000, blank=True, null=True)
    theme_essay_follow_up = models.TextField(max_length=2000, blank=True, null=True)
    hardware_hack_interest = models.CharField(
        max_length=1,
        choices=HardwareHackInterest.choices,
        default=HardwareHackInterest.B
    )
    heard_about_us = MultiSelectField(choices=HeardAboutUs.choices, max_length=30)
    heard_about_us_other = models.CharField(max_length=20, null=True)
    digital_designer_skills = MultiSelectField(
        choices=DigitalDesignerProficientSkills.choices, max_length=30, null=True)
    digital_designer_skills_other = models.CharField(max_length=20, null=True)
    communications_platform_username = models.CharField(max_length=300, null=True)
    outreach_groups = models.TextField(max_length=2000, blank=True, null=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # mentor
    mentor_qualified_fields = models.TextField(max_length=1000, blank=False, null=True)
    mentor_mentoring_steps = models.TextField(max_length=1000, blank=False, null=True)
    mentor_previously_mentored = models.BooleanField(null=True)
    # judges
    judge_judging_steps = models.TextField(max_length=1000, blank=False, null=True)
    judge_invited_by = models.CharField(max_length=100, blank=False, null=True)
    judge_previously_judged = models.BooleanField(null=True)

    def __str__(self) -> str:  # pragma: nocover
        return f"Participation Class: {self.participation_class}, Name: {self.first_name} {self.last_name}"


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


class Workshop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, null=False)
    datetime = models.DateTimeField(null=True)
    duration = models.IntegerField(null=True)
    description = models.TextField(blank=True, null=True)
    location = models.ForeignKey(
        Location, related_name="workshop_location",
        on_delete=models.CASCADE, null=True
    )
    course_materials = models.URLField(null=True, blank=True)
    recommended_for = MultiSelectField(
        choices=ParticipationRole.choices, max_choices=8, max_length=8, null=True)
    skills = models.ManyToManyField(Skill, related_name="workshop_skills")
    hardware = models.ManyToManyField(Hardware, related_name="workshop_hardware")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Name"


class WorkshopAttendee(models.Model):
    class Participation(models.TextChoices):
        RSVP = "R", _("RSVP'd")
        CONFIRMED = "C", _("Confirmed")
        INSTRUCTOR = "I", _("Instructor")
        VOLUNTEER = "V", _("Volunteer")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workshop = models.ForeignKey(
        Workshop, related_name="workshop_attendee_workshop",
        on_delete=models.CASCADE, null=False
    )
    attendee = models.ForeignKey(
        Attendee, related_name="workshop_attendee_attendee",
        on_delete=models.CASCADE, null=False
    )
    participation = models.CharField(
        max_length=1,
        choices=Participation.choices,
        default=Participation.RSVP,
        null=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        pass


post_delete.connect(
    UploadedFile.post_delete, sender=UploadedFile, dispatch_uid="file_entry_deleted"
)
post_delete.connect(
    Application.post_delete, sender=Application, dispatch_uid="application_entry_deleted"
)
post_save.connect(
    Application.post_create, sender=Application, dispatch_uid="application_entry_created"
)
