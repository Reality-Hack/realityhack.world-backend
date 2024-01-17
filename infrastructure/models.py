import json
import os
import re
import secrets
import shutil
import sys
import urllib
import uuid
from datetime import datetime

import language_tags
import pycountry
import requests
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
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
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        re.sub(r'[^a-zA-Z0-7\_\-\ ]', '', self.name)
        self.name = self.name.lower()
        self.name.replace(" ", "_").replace("-", "_").replace("__", "_")
        return super(Skill, self).save(*args, **kwargs)

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
    is_xr_specific = models.BooleanField(default=False, null=False)
    attendee = models.ForeignKey('Attendee', on_delete=models.CASCADE, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "skill proficiencies"
        unique_together = [['attendee', 'skill']]

    def __str__(self) -> str:  # pragma: no cover
        return f"Skill: {self.skill}, Proficiency: {self.proficiency}, RSVP: {self.rsvp}"
    

class ShirtSize(models.TextChoices):
        XS = '1', _('XS')
        S = '2', _('S')
        M = '3', _('M')
        L = '4', _('L')
        XL = '5', _('XL')
        XXL = '6', _('XXL')


# RFC 5646-compliant mapping of languages
SPOKEN_LANGUAGES = [
    (x["Subtag"], ", ".join(x["Description"]))
    for x in language_tags.data.cache['registry']
    if x["Type"] == "language" and x.get("Scope") != "special"
]


class DisabilityIdentity(models.TextChoices):
    A = 'A', _('Yes')
    B = 'B', _('No')
    C = 'C', _('I prefer not to say')


class DietaryRestrictions(models.TextChoices):
    VEGETARIAN = '1', _('Vegetarian')
    VEGAN = '2', _('Vegan')
    GLUTEN_FREE = '3', _('Gluten free')
    HALAL = '4', _('Halal')
    LACTOSE_INTOLERANT = '5', _('Lactose Intolerant')
    KOSHER = '6', _('Kosher')
    OTHER = '7', _('Other')


class DietaryAllergies(models.TextChoices):
    NUT= '1', _('Nut allergy')
    SHELLFISH = '2', _('Shellfish allergy')
    DAIRY = '3', _('Dairy allergy')
    SOY = '4', _('Soy allergy')
    OTHER = '5', _('Other')

DISABILITIES = (('A', 'Hearing difficulty - Deaf or having serious difficulty hearing (DEAR).'),
                ('B', 'Vision difficulty - Blind or having serious difficulty seeing, even when wearing glasses (DEYE).'),
                ('C', 'Cognitive difficulty - Because of a physical, mental, or emotional problem, having difficulty remembering, concentrating, or making decisions (DREM).'),
                ('D', 'Ambulatory difficulty - Having serious difficulty walking or climbing stairs (DPHY).'),
                ('E', 'Self-care difficulty - Having difficulty bathing or dressing (DDRS).'),
                ('F', 'Independent living difficulty - Because of a physical, mental, or emotional problem, having difficulty doing errands alone such as visiting a doctor\'s office or shopping (DOUT).'),
                ('G', 'I prefer not to say'),
                ('O', 'Other'))


class HeardAboutUs(models.TextChoices):
    FRIEND = 'F', _('A friend')
    VOLUNTEER = 'V', _('A Reality Hack organizer or volunteer')
    NETWORK = 'N', _('A teacher or someone in my professional network')
    SOCIAL = 'S', _('Social media')
    CAMPUS = 'C', _('Campus poster or ad')
    PARTICIPATED = 'P', _('I participated in the MIT XR Hackathon before')
    OTHER = 'O', _('Other')


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
    DISABILITIES = DISABILITIES
    HeardAboutUs = HeardAboutUs

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

    PREVIOUS_PARTICIPATION = (('A', '2016'),
                              ('B', '2017'),
                              ('C', '2018'),
                              ('D', '2019'),
                              ('E', '2020'),
                              ('F', '2022'),
                              ('G', '2023'))

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
    def post_save(cls, sender, instance, created, **kwargs):
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
        UploadedFile, on_delete=models.SET_NULL,
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
    # rsvp
    rsvp_email_sent_at = models.DateTimeField(null=True)

    def __str__(self) -> str:  # pragma: nocover
        return f"Participation Class: {self.participation_class}, Name: {self.first_name} {self.last_name}"


class Track(models.TextChoices):
    FUTURE_CONSTRUCTORS = 'F', _('Future Constructors')
    LEARNING = 'L', _('Learning')
    WORK = 'W', _('Work')
    HEALTH = 'H', _('Health and Well-Being')
    SMART_CITIES = 'S', _('Smart Cities and Sustainability')
    COMMUNITY_HACKS = 'C', ('Community Hacks')


class DestinyHardware(models.TextChoices):
    HARDWARE_HACK = 'H', _('Hardware Hack')
    META = 'M', _('Meta')
    SNAPDRAGON_SPACES = 'Q', _('Snapdragon Spaces')
    XREAL = 'X', _('XREAL')
    SNAP = 'S', _('Snap Spectacles')


class Attendee(AbstractUser):

    class ParticipationClass(models.TextChoices):
        PARTICIPANT = 'P', _('Participant')
        MENTOR = 'M', _('Mentor')
        JUDGE = 'J', _('Judge')
        SPONSOR = 'S', _('Sponsor')
        VOLUNTEER = 'V', _('Volunteer')
        ORGANIZER = 'O', _('Organizer')
        GUARDIAN = 'G', _('Guardian')
        MEDIA = 'E', _('Media')

    class Status(models.TextChoices):
        RSVP = 'R', _("RSVP'd")
        ARRIVED = 'A', _('Arrived')
        CANCELED = 'C', _('Canceled')

    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        if instance.profile_image:
            instance.profile_image.claimed = True
            instance.profile_image.save()
        if "test" not in sys.argv and "setup_test_data" not in sys.argv:
            if created:
                instance.create_authentication_account()

    @classmethod
    def post_delete(cls, sender, instance, **kwargs):
        if instance.profile_image:
            instance.profile_image.delete()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, null=True)
    authentication_id = models.CharField(max_length=36, null=True)
    authentication_roles_assigned = models.BooleanField(default=False, null=False)
    participation_role = models.CharField(
        max_length=1,
        choices=ParticipationRole.choices,
        default=ParticipationRole.SPECIALIST,
        null=True
    )
    bio = models.TextField(max_length=1000, blank=True)
    email = models.EmailField(unique=True)
    guardian_of = models.ManyToManyField("Attendee", related_name='attendee_guardian_of', blank=True)
    sponsor_handler = models.ForeignKey("Attendee", related_name="attendee_sponsor_of", null=True, on_delete=models.SET_NULL)
    shirt_size = models.CharField(
        max_length=1,
        choices=ShirtSize.choices,
        default=ShirtSize.M,
        null=True
    )
    initial_setup = models.BooleanField(default=False)
    profile_image = models.OneToOneField(
        UploadedFile, on_delete=models.SET_NULL,
        related_name="attendee_profile_image_uploaded_file",
        null=True
    )
    communications_platform_username = models.CharField(
        max_length=40, null=True, help_text="I.e., a Discord username")
    intended_tracks = MultiSelectField(max_choices=2, max_length=7, null=True, choices=Track.choices)
    intended_hardware_hack = models.BooleanField(default=False, null=False)
    hardware_hack = models.BooleanField(default=False, null=False)
    prefers_destiny_hardware = MultiSelectField(max_choices=len(DestinyHardware.choices), max_length=len(DestinyHardware.choices) * 2 + 1, null=True)
    dietary_restrictions = MultiSelectField(
        max_length=15, max_choices=7, null=True, choices=DietaryRestrictions.choices
    )
    dietary_restrictions_other = models.CharField(max_length=40, null=True)
    dietary_allergies = MultiSelectField(
        max_length=10, max_choices=5, null=True, choices=DietaryAllergies.choices
    )
    dietary_allergies_other = models.CharField(max_length=40, null=True)
    additional_accommodations = models.TextField(max_length=200, blank=False, null=True)
    us_visa_support_is_required = models.BooleanField(null=False)
    us_visa_letter_of_invitation_required = models.BooleanField(null=True, default=False)
    us_visa_support_full_name = models.CharField(max_length=200, blank=False, null=True)
    us_visa_support_document_number = models.CharField(max_length=50, blank=False, null=True)
    us_visa_support_national_identification_document_type = models.CharField(
        choices=[('P', 'Passport'), ('N', 'National/State/Municipal ID')],
        max_length=1, blank=False, null=True
    )  # passport or national ID
    us_visa_support_citizenship = models.CharField(
        max_length=2,
        choices=[(x.alpha_2, x.name) for x in pycountry.countries],
        blank=False,
        null=True
    )
    us_visa_support_address = models.TextField(max_length=500, null=True, blank=False)
    under_18_by_date = models.BooleanField(null=True, help_text="Will you be under 18 on January 25, 2024")
    parental_consent_form_signed = models.BooleanField(null=True, default=None)
    agree_to_media_release = models.BooleanField(null=False, default=False)
    agree_to_liability_release = models.BooleanField(null=False, default=False)
    agree_to_rules_code_of_conduct = models.BooleanField(null=False, default=False)
    emergency_contact_name = models.CharField(max_length=200, null=False, blank=False)
    personal_phone_number = PhoneNumberField(blank=False, null=False)
    emergency_contact_phone_number = PhoneNumberField(blank=False, null=False)
    emergency_contact_email = models.EmailField(blank=False, null=False)
    emergency_contact_relationship = models.CharField(max_length=100, null=False, blank=False)
    special_track_snapdragon_spaces_interest = models.CharField(
        max_length=1,
        choices=[('Y', 'Yes'),('N', 'No')],
        null=True
    )
    special_track_future_constructors_interest = models.CharField(
        max_length=1,
        choices=[('Y', 'Yes'),('N', 'No')],
        null=True
    )
    app_in_store = models.CharField(
        max_length=250, null=True, blank=False,
        help_text="Do you already have an AR or VR app in any store? And if so, which store(s)?"
    )
    currently_build_for_xr = models.CharField(max_length=250, null=True, blank=False)
    currently_use_xr = models.CharField(max_length=250, null=True, blank=False)
    non_xr_talents = models.CharField(max_length=250, null=True, blank=False)
    ar_vr_ap_in_store = models.CharField(max_length=250, null=True, blank=False)
    reality_hack_project_to_product = models.BooleanField(default=False, null=False)
    participation_class = models.CharField(
        choices=ParticipationClass.choices,
        max_length=1,
        null=False,
        default=ParticipationClass.PARTICIPANT
    )
    status = models.CharField(
        max_length=1,
        choices=Status.choices,
        null=False,
        default=Status.RSVP
    )
    checked_in_at = models.DateTimeField(null=True)
    # sponsor
    sponsor_company = models.CharField(max_length=100, null=True, blank=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self) -> str:  # pragma: nocover
        return f"Name: {self.first_name} {self.last_name}, Username: {self.communications_platform_username}"

    def get_authentication_token(self):
        access_token_params = {"grant_type": "client_credentials", "client_id": os.environ['KEYCLOAK_CLIENT_ID'], "client_secret": os.environ['KEYCLOAK_CLIENT_SECRET_KEY']}
        return requests.post(
            url=f"{os.environ['KEYCLOAK_SERVER_URL']}/realms/master/protocol/openid-connect/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=urllib.parse.urlencode(access_token_params)
        )

    def assign_authentication_roles(self):
        access_token = self.get_authentication_token()
        realm_role = None
        if self.participation_class == self.ParticipationClass.PARTICIPANT:
            realm_role = "attendee"
        elif self.participation_class == self.ParticipationClass.MENTOR:
            realm_role = "mentor"
        elif self.participation_class == self.ParticipationClass.JUDGE:
            realm_role = "judge"
        elif self.participation_class == self.ParticipationClass.SPONSOR:
            realm_role = "sponsor"
        elif self.participation_class == self.ParticipationClass.VOLUNTEER:
            realm_role = "volunteer"
        elif self.participation_class == self.ParticipationClass.ORGANIZER:
            realm_role = "organizer"
        role_by_name = requests.get(
        url=f"{os.environ['KEYCLOAK_SERVER_URL']}/admin/realms/master/roles/{realm_role}",
            headers={"Authorization": f"Bearer {access_token.json()['access_token']}", "Content-Type": "application/json"},\
        )
        realm_roles = [role_by_name.json()]
        created_realm_roles = requests.post(
            url=f"{os.environ['KEYCLOAK_SERVER_URL']}/admin/realms/master/users/{self.authentication_id}/role-mappings/realm",
            headers={"Authorization": f"Bearer {access_token.json()['access_token']}", "Content-Type": "application/json"},
            data=json.dumps(realm_roles)
        )
        if created_realm_roles.ok:
            self.authentication_roles_assigned = True
            self.save()
        return created_realm_roles

    def create_authentication_account(self):
        temporary_password = secrets.token_hex(10 // 2)
        access_token = self.get_authentication_token()
        auth_user_dict = {
            "id": str(uuid.uuid4()),
            "username": f"{self.first_name}.{self.last_name}.{uuid.uuid4()}",
            "enabled": True,
            "email": self.email,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "credentials": [
                {
                    "type": "password",
                    "value": temporary_password,
                    "temporary": True
                }
            ],
            "clientRoles": {
                "account": [
                    "manage-account",
                    "view-profile"
                ]
            }
        }
        authentication_account = requests.post(
            url=f"{os.environ['KEYCLOAK_SERVER_URL']}/admin/realms/master/users",
            headers={"Authorization": f"Bearer {access_token.json()['access_token']}", "Content-Type": "application/json"},
            data=json.dumps(auth_user_dict)
        )
        if authentication_account.ok:
            authentication_account_id = authentication_account.headers["Location"].split("/")[-1]
            self.authentication_id = authentication_account_id
            self.save()
            self.assign_authentication_roles()
            # send email with credentials
            subject, body = None, None
            if self.participation_class == Attendee.ParticipationClass.PARTICIPANT:
                subject, body = email.get_hacker_rsvp_confirmation_template(self.first_name, temporary_password)
            else:
                subject, body = email.get_non_hacker_rsvp_confirmation_template(self.first_name, temporary_password)
            send_mail(
                subject,
                body,
                "no-reply@mitrealityhack.com",
                [self.email],
                fail_silently=False,
            )

    class Meta:
        verbose_name = "attendees"
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['first_name',]),
            models.Index(fields=['last_name']),
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['is_staff'])
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
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.number}"


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    attendees = models.ManyToManyField(Attendee, related_name="team_attendees", blank=True)
    table = models.OneToOneField(Table, on_delete=models.SET_NULL, null=True)
    track = models.CharField(choices=Track.choices, max_length=1, null=True)
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
    team = models.OneToOneField(Team, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name}"


class MentorRequestStatus(models.TextChoices):
        REQUESTED = "R"
        ACKNOWLEDGED = "A"
        EN_ROUTE = "E"
        RESOLVED = "F"


class LightHouse(models.Model):
    class MessageType(models.TextChoices):
        ANNOUNCEMENT = "A"
        MENTOR_REQUEST = "M"

    class AnnouncementStatus(models.TextChoices):
        SEND = "S"
        ALERT = "A"
        RESOLVE = "F"

    class ExtraData(models.TextChoices):
        AUDIO_FILE = "A"
        LIGHT_PATTERN = "L"

    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        channel_layer = get_channel_layer()
        room_group_name = f"lighthouse_{instance.table.number}"
        lighthouse = {
            # "id": instance.id,
            "table": instance.table.number,
            "ip_address": instance.ip_address,
            "mentor_requested": instance.mentor_requested,
            "announcement_pending": instance.announcement_pending
        }
        async_to_sync(channel_layer.group_send)(
            room_group_name, {"type": "chat.message", "message": lighthouse}
        )
        async_to_sync(channel_layer.group_send)(
            "lighthouses", {"type": "chat.message", "message": lighthouse}
        )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    announcement_pending = models.CharField(choices=AnnouncementStatus.choices ,max_length=1, default=AnnouncementStatus.RESOLVE.value)
    mentor_requested = models.CharField(choices=MentorRequestStatus.choices, max_length=1, default=MentorRequestStatus.RESOLVED.value)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Table: {self.table}, IP: {self.ip_address}"


class MentorHelpRequestCategory(models.TextChoices):
    DEVELOPMENT = 'D', _('Development')
    DESIGN = 'A', _('Design')
    PROTOTYPING = 'P', ('Prototyping')
    PROJECT_MANAGEMENT = 'M', ('Project Management and Leadership')
    SPECIALTY = 'S', ('Specialty')


MENTOR_HELP_REQUEST_TOPICS = [
    ('1', 'Development and Programming'), ('2', 'Unity Timeline Animations'), ('3', 'Embedded Systems (C)'), ('4', 'Embedded Systems (Python)'),
    ('5', 'C++ Android JavaScript'), ('6', 'Backend Development'), ('7', 'Unreal App Development'), ('8', 'Unreal Blueprints'),
    ('9', 'Unity AR Foundation'), ('10', 'WebXR'), ('11', 'Lens Studio'), ('12', 'Meta Spark'), ('13', 'Virtual Reality'), ('14', 'Augmented Reality'),
    ('15', 'Mixed Reality'), ('16', 'Mixed Reality Toolkit'), ('17', 'Meta XR SDK'), ('18', 'C#'), ('19', 'Regression Testing'),
    ('20', 'OOP Design Patterns'), ('21', 'Distributed Computing'), ('22', 'Cybersecurity'), ('23', 'Swift SwiftUI ARKit'), ('24', 'Software Builds'),
    ('25', 'Containers'), ('26', 'Deployment Automation'), ('27', 'Site-reliability engineering (SRE) Work'), ('28', 'Python Shell Scripting'),
    ('29', 'Search Implementation'), ('30', 'Generative AI'), ('31', 'IoT'), ('32', '3D Rendering'), ('33', 'Video Encoding'),
    ('34', 'Linux OS Configuration'), ('35', 'Cross-platform Work'), ('36', 'Web Frontend/Backend'), ('37', 'Project Scope'), ('38', 'Technical Approach'),
    ('39', 'App-driven Architecture'), ('40', 'Problem-solving'), ('41', 'Design and Prototyping'), ('42', 'ShapesXR'),
    ('43', 'Figma'), ('44', 'Miro'), ('45', 'Adobe Creative Suite'), ('46', 'Mocap'), ('47', '3D Stereoscopic Recording'),
    ('48', 'Mobile AR'), ('49', '3D Modeling'), ('50', 'Animation'), ('51', 'Motion Capture'), ('52', 'XR Design Execution'),
    ('53', 'Interactive Learning Programs'), ('54', 'Computer Vision'), ('55', 'Graphics Shaders'), ('56', 'Git'), ('57', 'XR/AR VR Expert'),
    ('58', 'Storytelling'), ('59', 'Visual Design'), ('60', 'Prototyping'), ('61', 'Analog Painting'), ('62', 'Drawing'), ('63', 'Sculpture'),
    ('64', 'Project Management and Leadership'), ('65', 'Producer'), ('66', 'Peace-maker Conflict Resolution'), ('67', 'Storyteller'),
    ('68', 'Project Management'), ('69', 'Agile Scrum'), ('70', 'Conflict Resolution'), ('71', 'Communication'), ('72', 'Digital Experience Production'),
    ('73', 'User Flow Design'), ('74', 'Hardware Development (Arduino)'), ('75', 'Hardware Development (Esp32)'),
    ('76', 'Hardware Development (Raspberry Pi)'), ('77', 'Innovation and Specialized Expertise'), ('78', 'Biometrics in VR'),
    ('79', 'Brain-Computer Interface (BCI)'), ('80', 'Game Design'), ('81', 'Lens Studio Projects'), ('82', 'Snap Lens'),
    ('83', '8thWall Expertise'), ('84', 'Web Development'), ('85', 'Blockchain'), ('86', 'Networking'), ('87', '.NET'), ('O', 'Other')
]


class MentorHelpRequest(models.Model):

    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        table = instance.team.table
        lighthouse = LightHouse.objects.get(table=table.id)
        lighthouse.mentor_requested = instance.status
        lighthouse.save()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=250, null=True)
    description = models.TextField(max_length=2000, null=True)
    category = models.CharField(choices=MentorHelpRequestCategory.choices, null=True, max_length=1)
    category_specialty = models.CharField(max_length=100, null=True)
    topic = MultiSelectField(choices=MENTOR_HELP_REQUEST_TOPICS, max_choices=85, max_length=len(MENTOR_HELP_REQUEST_TOPICS) * 3)
    topic_other = models.CharField(max_length=50, null=True)
    reporter = models.ForeignKey(Attendee, on_delete=models.SET_NULL, null=True, related_name="mentor_help_request_reporter")
    mentor = models.ForeignKey(Attendee, on_delete=models.SET_NULL, null=True, related_name="mentor_help_request_mentor")
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    status = models.CharField(choices=MentorRequestStatus.choices, max_length=1, default=MentorRequestStatus.REQUESTED.value)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"Reporter: {self.reporter}, Mentor: {self.mentor}, Title: {self.title}"


class HardwareTags(models.TextChoices):
    AC = 'AC', _('Accessory')
    SE = 'SE', _('Sensor')
    VR = 'VR', _('Virtual Reality')
    AR = 'AR', _('Augmented Reality')
    MR = 'MR', _('Mixed Reality')
    CO = 'CO', _('Computer')
    HA = 'HA', _('Haptics')
    CA = 'CA', _('Camera')
    TA = 'TA', _('Tablet')
    HD = 'HD', _('Holographic Display')


class Hardware(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=1000, blank=True)
    image = models.OneToOneField(
        UploadedFile, on_delete=models.SET_NULL,
        related_name="hardware_image_uploaded_file",
        null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = MultiSelectField(
        choices=HardwareTags.choices, max_length=2, null=True)
    relates_to_destiny_hardware = models.CharField(choices=DestinyHardware.choices, max_length=1, null=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"Name: {self.name}"


class HardwareDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hardware = models.ForeignKey(Hardware, on_delete=models.CASCADE)
    serial = models.CharField(max_length=100)
    checked_out_to = models.OneToOneField(
        'HardwareRequest', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self) -> str:  # pragma: no cover
        return f"Hardware: {self.hardware}, Serial: {self.serial}"


class HardwareRequestStatus(models.TextChoices):
    PENDING = 'P', _('Pending')
    APPROVED = 'A', _('Approved')
    REJECTED = 'R', _('Rejected')
    CHECKED_OUT = 'C', _('Checked out')


class HardwareRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hardware = models.ForeignKey(Hardware, on_delete=models.CASCADE)
    hardware_device = models.OneToOneField(HardwareDevice, on_delete=models.CASCADE, null=True, blank=True)
    requester = models.ForeignKey(Attendee, on_delete=models.CASCADE, null=True)
    team = models.ForeignKey(Team, on_delete=models.CASCADE, null=True)
    reason = models.TextField(max_length=1000, blank=True)
    status = models.CharField(
        max_length=1,
        choices=HardwareRequestStatus.choices,
        default=HardwareRequestStatus.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self) -> str:  # pragma: no cover
        return f"Hardware: {self.hardware}, Requester: {self.requester} (Team: {self.team})"

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
    skills = models.ManyToManyField(Skill, related_name="workshop_skills", blank=True)
    hardware = models.ManyToManyField(Hardware, related_name="workshop_hardware", blank=True)
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
    Application.post_save, sender=Application, dispatch_uid="application_entry_saved"
)
post_save.connect(
    Attendee.post_save, sender=Attendee, dispatch_uid="attendee_entry_saved"
)
post_delete.connect(
    Attendee.post_delete, sender=Attendee, dispatch_uid="attendee_entry_deleted"
)
post_save.connect(
    LightHouse.post_save, sender=LightHouse, dispatch_uid="lighthouse_entry_saved"
)
post_save.connect(
    MentorHelpRequest.post_save, sender=MentorHelpRequest, dispatch_uid="mentor_help_request_entry_saved"
)