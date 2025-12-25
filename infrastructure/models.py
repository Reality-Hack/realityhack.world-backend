import re
import sys
import uuid
import time
import logging
import threading

import language_tags
import pycountry
from django.contrib.auth.models import AbstractUser
from django.core.mail import send_mail
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.utils.translation import gettext_lazy as _
from multiselectfield import MultiSelectField
from phonenumber_field.modelfields import PhoneNumberField
from simple_history.models import HistoricalRecords
from infrastructure.constants import MENTOR_HELP_REQUEST_TOPICS
from infrastructure import email
from infrastructure.managers import EventScopedManager

logger = logging.getLogger(__name__)


def send_email_background(subject, body, from_email, recipient_list):
    """Send email in background thread to avoid blocking HTTP response."""
    send_start = time.time()
    try:
        send_mail(subject, body, from_email, recipient_list, fail_silently=False)
        logger.info(
            f"[EMAIL_BACKGROUND] Email to {recipient_list} sent successfully in "
            f"{time.time() - send_start:.3f}s"
        )
    except Exception as e:
        logger.error(
            f"[EMAIL_BACKGROUND] Failed to send email to {recipient_list}: {e} "
            f"(after {time.time() - send_start:.3f}s)"
        )


# settings.AUTH_USER_MODEL

with open("infrastructure/industries.csv", "r") as f:
    industries = f.read().strip().split(",\n")
    INDUSTRIES = [(x, x) for x in industries]


class Event(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, null=False)
    start_date = models.DateTimeField(null=False)
    end_date = models.DateTimeField(null=False)
    is_active = models.BooleanField(
        default=False,
        help_text="Only one event should be active at a time"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.name}"

    @classmethod
    def get_active(cls):
        """Get the currently active event."""
        return cls.objects.filter(is_active=True).first()

    def activate(self):
        """Make this the active event (deactivates all others)."""
        Event.objects.update(is_active=False)
        self.is_active = True
        self.save(update_fields=['is_active'])


class ParticipationRole(models.TextChoices):
    DESIGNER = 'A', _('Digital/Creative Designer')
    DEVELOPER = 'D', _('Developer')
    SPECIALIST = 'S', _('Domain or other Specialized Skill Expert')
    PROJECT_MANAGER = 'P', _('Project Manager')


class ParticipationCapacity(models.TextChoices):
    STUDENT = 'S', _('Student'),
    PROFESSIONAL = 'P', _('Professional')
    HOBBYIST = 'H', _('Hobbyist')


class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventScopedManager()

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
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
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

    objects = EventScopedManager()

    class Meta:
        verbose_name = "skill proficiencies"
        unique_together = [['attendee', 'skill']]

    def __str__(self) -> str:  # pragma: no cover
        return f"Skill: {self.skill}, Proficiency: {self.proficiency}"


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
    NUT = '1', _('Nut allergy')
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


# TODO: test and implement refresh_uri to get around cloudflare r2 expiration
class UploadedFile(models.Model):
    @classmethod
    def post_delete(cls, sender, **kwargs):
        instance = kwargs.get('instance')
        if instance.file:
            instance.file.delete(save=False)
        else:
            # delete the file from cloudflare using the id as the bucket prefix
            # get the access token
            # get the bucket name
            # delete the file
            print(f"Deleting file from cloudflare: {instance.id}")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(upload_to=user_directory_path)
    claimed = models.BooleanField(null=False, default=False)  # If file remains unclaimed, eventually delete
    created_at = models.DateTimeField(auto_now_add=True)
    # expires_at = models.DateTimeField(null=True, blank=True)
    # uri = models.URLField(null=True, blank=True)

    class Meta:
        verbose_name = "uploaded files"

    def __str__(self):
        return f"Claimed: {self.claimed}, File: {self.file}"

    # def is_expired(self):
    #     return self.expires_at and self.expires_at < timezone.now()

    # def refresh_uri(self):
    #     # Implement the logic to generate a new pre-signed URL
    #     # This will depend on your storage backend (e.g., Cloudflare R2)
    #     new_uri, new_expiration = generate_new_presigned_url(self.file_path)
    #     self.uri = new_uri
    #     self.expires_at = new_expiration
    #     self.save()


class ParticipationClass(models.TextChoices):
    PARTICIPANT = 'P', _('Participant')
    MENTOR = 'M', _('Mentor')
    JUDGE = 'J', _('Judge')
    SPONSOR = 'S', _('Sponsor')
    VOLUNTEER = 'V', _('Volunteer')
    ORGANIZER = 'O', _('Organizer')
    GUARDIAN = 'G', _('Guardian')
    MEDIA = 'E', _('Media')


class Application(models.Model):
    DISABILITIES = DISABILITIES
    HeardAboutUs = HeardAboutUs

    class Status(models.TextChoices):
        ACCEPTED_IN_PERSON = 'AI', _('Accepted, In-Person')
        ACCEPTED_ONLINE = 'AO', _('Accepted, Online')
        WAITLIST_IN_PERSON = 'WI', _('Wait-list, In-Person')
        WAITLIST_ONLINE = 'WO', _('Wait-list, Online')
        DECLINED = 'D', _('Declined')

    class ThemeInterestTrackChoice(models.TextChoices):
        YES = 'Y', _('Yes')
        NO = 'N', _('No')

    class AgeGroup(models.TextChoices):
        A = 'A', _('17 or younger')
        B = 'B', _('18 to 20')
        C = 'C', _('21 to 29')
        D = 'D', _('30 to 39')
        E = 'E', _('40 to 49')
        F = 'F', _('50 to 59')
        G = 'G', _('60 or older')
        H = 'H', _('I prefer not to say')

    class GenderIdentities(models.TextChoices):
        CISGENDER_FEMALE = 'A', _('Cisgender female')
        CISGENDER_MALE = 'B', _('Cisgender male')
        TRANSGENDER_FEMALE = 'C', _('Transgender female')
        TRANSGENDER_MALE = 'D', _('Transgender male')
        GENDER_NONCORFORMING = 'E', _('Gender non-conforming, non-binary, or gender queer')
        TWO_SPIRIT = 'F', _('Two-spirit')
        PREFER_NONE = 'G', _('I prefer not to say')
        OTHER = 'O', _('Other')

    class RaceEthnicGroups(models.TextChoices):
        BLACK_AFRICAN = 'B', _('Black, African American, or of African descent')
        HISPANIC_LATINO = 'C', _('Hispanic, Latino, Latina, Latinx, or of Latinx or Spanish-speaking descent')
        MIDDLE_EASTERN_N_AFRICAN = 'D', _('Middle Eastern, North African, or of North African descent')
        NATIVE_AMERICAN_INDIGENOUS = 'E', _('Native American, American Indian, Alaska Native, or Indigenous')
        PACIFIC_ISLANDER = 'F', _('Pacific Islander or Native Hawaiian')
        WHITE_EUROPEAN = 'G', _('White or of European descent')
        MULTI_RACIAL_ETHNIC = 'H', _('Multi-racial or multi-ethnic')
        PREFER_NONE = 'I', _('I prefer not to say')
        EAST_ASIAN = 'J', _('East Asian')
        SOUTH_ASIAN = 'K', _('South Asian')
        SOUTHEAST_ASIAN = 'L', _('Southeast Asian')
        CENTRAL_ASIAN = 'M', _('Central Asian')
        OTHER = 'O', _('Other')

    class PreviousParticipation(models.TextChoices):
        YEAR_2016 = 'A', _('2016')
        YEAR_2017 = 'B', _('2017')
        YEAR_2018 = 'C', _('2018')
        YEAR_2019 = 'D', _('2019')
        YEAR_2020 = 'E', _('2020')
        YEAR_2022 = 'F', _('2022')
        YEAR_2023 = 'G', _('2023')
        YEAR_2024 = 'H', _('2024')
        YEAR_2025 = 'I', _('2025')

    class HardwareHackDetail(models.TextChoices):
        A = 'A', _("3D Printing")
        B = 'B', _("Soldering")
        C = 'C', _("Circuits")
        D = 'D', _("Arduino")
        E = 'E', _("ESP32")
        F = 'F', _("Unity")
        G = 'G', _("Physical Prototyping")
        H = 'H', _("I have no prior experience")
        O = 'O', _("Other")

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
            skip_email = (
                "create_test_applications" in sys.argv or
                "setup_test_data" in sys.argv or
                "setup_fake_users" in sys.argv or
                "test" in sys.argv
            )
            if not skip_email:
                subject, body = None, None
                cls_mentor = ParticipationClass.MENTOR
                cls_judge = ParticipationClass.JUDGE
                if instance.participation_class == cls_mentor:
                    subject, body = (
                        email.get_mentor_application_confirmation_template(
                            instance.first_name,
                            response_email_address=(
                                "Mentors <mentors@realityhackinc.org>"
                            )
                        )
                    )
                elif instance.participation_class == cls_judge:
                    subject, body = (
                        email.get_judge_application_confirmation_template(
                            instance.first_name,
                            response_email_address=(
                                "Catherine Dumas <catherine@realityhackinc.org>"
                            )
                        )
                    )
                else:
                    subject, body = (
                        email.get_hacker_application_confirmation_template(
                            instance.first_name
                        )
                    )

                thread = threading.Thread(
                    target=send_email_background,
                    args=(
                        subject,
                        body,
                        "no-reply@realityhackinc.org",
                        [instance.email]
                    )
                )
                thread.daemon = False
                thread.start()
                logger.info(
                    "[APPLICATION_POST_SAVE] Email queued in background thread"
                )

    @classmethod
    def post_delete(cls, sender, instance, **kwargs):
        if instance.resume:
            instance.resume.delete()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
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
    email = models.EmailField(blank=False, null=False)
    portfolio = models.URLField(null=True)
    secondary_portfolio = models.URLField(null=True)
    resume = models.OneToOneField(
        UploadedFile, on_delete=models.SET_NULL,
        related_name="application_resume_uploaded_file",
        null=True
    )
    gender_identity = MultiSelectField(choices=GenderIdentities.choices, max_choices=8, max_length=len(GenderIdentities) * 2)
    gender_identity_other = models.CharField(max_length=20, null=True)
    race_ethnic_group = MultiSelectField(choices=RaceEthnicGroups.choices, max_choices=10, max_length=len(RaceEthnicGroups) * 2)
    race_ethnic_group_other = models.CharField(max_length=20, null=True)
    disability_identity = models.CharField(
        max_length=1,
        choices=DisabilityIdentity.choices,
        default=DisabilityIdentity.C,
        null=True
    )
    # TODO: move to RSVP
    # disabilities = MultiSelectField(choices=DISABILITIES, max_choices=7, max_length=len(DISABILITIES), null=True)
    # disabilities_other = models.CharField(max_length=20, null=True)
    # disability_accommodations = models.TextField(max_length=1000, blank=True, null=True)
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
    other_skills_experiences = models.TextField(max_length=1000, blank=False, null=True)
    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        null=True,
        default=None
    )
    previously_participated = models.BooleanField(default=False, null=True)
    previous_participation = MultiSelectField(
        choices=PreviousParticipation.choices,
        max_choices=7,
        max_length=len(PreviousParticipation) * 2,
        null=True,
    )
    participation_role = models.CharField(
        max_length=1,
        choices=ParticipationRole.choices,
        default=ParticipationRole.SPECIALIST,
        null=True
    )
    experience_with_xr = models.TextField(max_length=2000, blank=True, null=True)
    experience_contribution = models.TextField(max_length=2000, blank=True, null=True)
    theme_essay = models.TextField(max_length=2000, blank=True, null=True)
    theme_essay_follow_up = models.TextField(max_length=2000, blank=True, null=True)
    theme_interest_track_one = models.CharField(
        max_length=1,
        choices=ThemeInterestTrackChoice.choices,
        default=ThemeInterestTrackChoice.NO,
        null=True
    )
    theme_interest_track_two = models.CharField(
        max_length=1,
        choices=ThemeInterestTrackChoice.choices,
        default=ThemeInterestTrackChoice.NO,
        null=True
    )
    theme_detail_one = models.CharField(
        max_length=1,
        choices=ThemeInterestTrackChoice.choices,
        default=ThemeInterestTrackChoice.NO,
        null=True
    )
    theme_detail_two = models.CharField(
        max_length=1,
        choices=ThemeInterestTrackChoice.choices,
        default=ThemeInterestTrackChoice.NO,
        null=True
    )
    theme_detail_three = models.CharField(
        max_length=1,
        choices=ThemeInterestTrackChoice.choices,
        default=ThemeInterestTrackChoice.NO,
        null=True
    )
    hardware_hack_interest = models.CharField(
        max_length=1,
        choices=HardwareHackInterest.choices,
        default=HardwareHackInterest.B,
        null=True
    )
    hardware_hack_detail = MultiSelectField(
        max_length=100,
        choices=HardwareHackDetail.choices,
        max_choices=7,
        null=True
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
    mentor_own_troubleshooting_devices = models.TextField(
        max_length=1000,
        blank=True,
        null=True,
        help_text="List devices you are willing to bring to assist with troubleshooting"
    )
    # judges
    judge_judging_steps = models.TextField(max_length=1000, blank=False, null=True)
    judge_invited_by = models.CharField(max_length=100, blank=False, null=True)
    judge_previously_judged = models.BooleanField(null=True)
    # rsvp
    rsvp_email_sent_at = models.DateTimeField(null=True)

    objects = EventScopedManager()

    class Meta:
        unique_together = [('email', 'event')]
        indexes = [
            models.Index(fields=['event', 'email']),
            models.Index(fields=['event', 'status']),
        ]

    def __str__(self) -> str:  # pragma: nocover
        return f"Participation Class: {self.participation_class}, Name: {self.first_name} {self.last_name}"


class ApplicationQuestion(models.Model):
    """Event-specific application questions"""
    class QuestionType(models.TextChoices):
        SINGLE_CHOICE = 'S', _('Single Choice')
        MULTIPLE_CHOICE = 'M', _('Multiple Choice')
        TEXT = 'T', _('Text Response')
        LONG_TEXT = 'L', _('Long Text/Essay')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event,
        on_delete=models.CASCADE, related_name='%(class)s_set'
    )

    # Question metadata
    question_key = models.CharField(
        max_length=100,
        help_text="Internal identifier like 'hardware_hack_interest'"
    )
    question_text = models.TextField()
    question_type = models.CharField(max_length=1, choices=QuestionType.choices)
    order = models.IntegerField(default=0)
    required = models.BooleanField(default=True)

    # Conditional logic for sub-questions
    parent_question = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='sub_questions',
        help_text="If set, this question only appears based on parent response"
    )
    trigger_choices = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of choice_keys from parent that trigger this question. "
            "Empty = always show"
        )
    )

    # essay question input configurations
    max_length = models.IntegerField(
        null=True,
        default=2000,
        blank=True,
        help_text="Maximum character length for text responses"
    )
    min_length = models.IntegerField(
        null=True,
        blank=True,
        help_text="Minimum character length for text responses"
    )
    placeholder_text = models.CharField(
        max_length=500,
        blank=True,
        help_text="Placeholder text for text inputs"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=['event', 'question_key']),
            models.Index(fields=['event', 'order']),
            models.Index(fields=['parent_question']),
        ]
        unique_together = [['event', 'question_key']]

    def __str__(self) -> str:
        return f"{self.event.name} - {self.question_key}"

    def should_show_for_response(self, parent_response):
        """Check if this question should be shown based on parent response"""
        if not self.parent_question:
            return True

        if not self.trigger_choices:
            return True

        # Check if any selected choices match trigger_choices
        selected = parent_response.selected_choices.values_list('choice_key', flat=True)
        return any(choice in self.trigger_choices for choice in selected)


class ApplicationQuestionChoice(models.Model):
    """Choices for single/multiple choice questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.ForeignKey(
        ApplicationQuestion,
        on_delete=models.CASCADE,
        related_name='choices'
    )

    choice_key = models.CharField(
        max_length=10,
        help_text="Short code like 'A', 'B', 'Y', 'N'"
    )
    choice_text = models.CharField(max_length=500)
    order = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['question', 'order']),
        ]
        ordering = ['order']
        unique_together = [['question', 'choice_key']]

    def __str__(self) -> str:
        return f"{self.question.question_key} - {self.choice_key}: {self.choice_text}"


class ApplicationResponse(models.Model):
    """User responses to application questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='question_responses'
    )
    question = models.ForeignKey(
        ApplicationQuestion,
        on_delete=models.PROTECT,
        related_name='responses'
    )

    # Store selected choices
    selected_choices = models.ManyToManyField(
        ApplicationQuestionChoice,
        blank=True,
        related_name='responses'
    )

    # Snapshot data - preserved even if question/choices are modified
    question_text_snapshot = models.TextField(
        help_text="Question text at time of response"
    )
    choices_snapshot = models.JSONField(
        default=dict,
        help_text="{'choice_key': 'choice_text'} at time of response"
    )
    selected_keys_snapshot = models.JSONField(
        default=list,
        help_text="List of choice_keys selected, preserved snapshot"
    )
    text_response = models.TextField(
        blank=True,
        help_text="Free-form text response for TEXT question types"
    )
    text_response_snapshot = models.TextField(
        blank=True,
        help_text="Snapshot of text response at time of submission"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [['application', 'question']]
        indexes = [
            models.Index(fields=['application']),
            models.Index(fields=['question']),
        ]

    def __str__(self) -> str:
        return f"{self.application.email} - {self.question.question_key}"

    def save(self, *args, **kwargs):
        """Auto-populate snapshots on creation"""
        super().save(*args, **kwargs)

        self.question_text_snapshot = self.question.question_text

        if self.question.question_type in ['S', 'M']:
            choices_dict = {}
            for choice in self.question.choices.all():
                choices_dict[choice.choice_key] = choice.choice_text
            self.choices_snapshot = choices_dict

        if self.question.question_type in ['T', 'L']:
            self.text_response_snapshot = self.text_response

        super().save(update_fields=[
            'question_text_snapshot',
            'choices_snapshot',
            'text_response_snapshot'
        ])

    def update_selected_snapshot(self):
        """Update the selected_keys_snapshot based on current selected_choices"""
        self.selected_keys_snapshot = list(
            self.selected_choices.values_list('choice_key', flat=True)
        )
        self.save(update_fields=['selected_keys_snapshot'])

    def clean(self):
        """Validate response based on question type"""

        if self.question.question_type in ['T', 'L']:
            if not self.text_response and self.question.required:
                raise ValidationError("Text response is required for this question")

            if (
                self.question.max_length and
                len(self.text_response) > self.question.max_length
            ):
                raise ValidationError(
                    "Response exceeds maximum length of "
                    f"{self.question.max_length} characters"
                )
            if (
                self.question.min_length and
                len(self.text_response) < self.question.min_length
            ):
                raise ValidationError(
                    f"Response must be at least {self.question.min_length} characters"
                )
        else:
            if self.text_response:
                raise ValidationError("Text responses are only for TEXT question types")


class Track(models.TextChoices): # limit to 1
    COMMUNITY_HACKS = 'C', ('Open Lab (AKA Community Hack)')
    SOCIAL_XR = 'S', ('Connecting for Change with Social XR')
    AUGMENTED_ENGINEERING = 'E', ('Augmented Design & Engineering')
    SUSTAINABILITY = 'D', ('Standing on the Shoulders of Sustainability')
    AEROSPATIAL_EXPLORATION = 'A', ('AeroSpatial Exploration')
    AUGMENTED_INTELLIGENCE = 'L', ('Augmented Intelligence')
    HEALTHCARE = 'H', ('Healthcare')


class DestinyHardware(models.TextChoices):
    META = 'M', _('Best MR Lifestyle App for Meta Quest')
    HORIZON = 'Q', _('Best Lifestyle World with Meta Horizons Worlds')
    HAPTICS = 'T', _('Best use of Haptics')
    SNAP = 'S', _('Snap Spectacles Challenge')
    NEUROADAPTIVE = 'N', _('Pioneering a Neuroadaptive Future')
    SHAPESXR = 'X', _('Best Use of ShapesXR')
    STYLY = 'Y', _('Best use of STYLY')
    LAMBDA = 'L', _('Best use of Lambda AI Cloud Services')
    QUALCOMM = 'U', _('Qualcomm IoT')
    APPLE_VISION = 'V', _('Best use of Apple Vision Pro')


class LoanerHeadsetPreference(models.TextChoices):
    # 1234567890123456789012
    META = 'META', _('Meta Quest 3')
    RB_META_AI = 'RB_META_AI', _('Ray-Ban Meta AI lasses')
    ARDUINO_UNO = 'ARDUINO_UNO', _('Arduino Uno Kits')
    SAMSUNG_GALAXY_XR = 'SAMSUNG_GALAXY_XR', _('Samsung Galaxy XR')
    RAYNEO = 'RAYNEO', _('RayNeo')
    RAVEN_AR = 'RAVEN_AR', _('Raven AR')
    SNAP = 'SNAP', _('Snap Spectacles')
    APPLE_VISION_PRO = 'APPLE_VISION_PRO', _('Apple Vision Pro')
    BLACKMAGIC = 'BLACKMAGIC', _('Blackmagic URSA Cine Immersive Camera')
    XREAL = 'XREAL', _('XREAL')
    PICO = 'PICO', _('Pico')
    OPENBCI = 'OPENBCI', _('OpenBCI Sensors')
    BYOD = 'BYOD', _('I am bringing my own XR device to work with.')
    HWHACK = 'HWHACK', _("I've chosen the Hardware Hack, so I will probably not need a headset.")
    TBD = 'TBD', _("I'm not sure yet")


class Attendee(AbstractUser):

    class Status(models.TextChoices):
        RSVP = 'R', _("RSVP'd")
        ARRIVED = 'A', _('Arrived')
        CANCELED = 'C', _('Canceled')

    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        if instance.profile_image:
            instance.profile_image.claimed = True
            instance.profile_image.save()

    @classmethod
    def post_delete(cls, sender, instance, **kwargs):
        if instance.profile_image:
            instance.profile_image.delete()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    authentication_id = models.CharField(max_length=36, null=True)
    authentication_roles_assigned = models.BooleanField(default=False, null=False)

    email = models.EmailField(unique=True)
    bio = models.TextField(max_length=1000, blank=True)
    initial_setup = models.BooleanField(default=False)
    profile_image = models.OneToOneField(
        UploadedFile, on_delete=models.SET_NULL,
        related_name="attendee_profile_image_uploaded_file",
        null=True
    )
    communications_platform_username = models.CharField(
        max_length=40, null=True, help_text="I.e., a Discord username")

    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, null=True)
    participation_role = models.CharField(
        max_length=1,
        choices=ParticipationRole.choices,
        default=ParticipationRole.SPECIALIST,
        null=True
    )
    guardian_of = models.ManyToManyField("Attendee", related_name='attendee_guardian_of', blank=True)
    sponsor_handler = models.ForeignKey("Attendee", related_name="attendee_sponsor_of", null=True, on_delete=models.SET_NULL)
    shirt_size = models.CharField(
        max_length=1,
        choices=ShirtSize.choices,
        default=ShirtSize.M,
        null=True
    )
    intended_tracks = MultiSelectField(max_choices=2, max_length=7, null=True, choices=Track.choices)
    intended_hardware_hack = models.BooleanField(default=False, null=False)
    prefers_destiny_hardware = MultiSelectField(max_choices=len(DestinyHardware.choices), max_length=len(DestinyHardware.choices) * 2 + 1, null=True, choices=DestinyHardware.choices)
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
    visa_support_form_confirmation = models.BooleanField(null=False, default=False)
    # getting rid of this, but keeping here for back compat
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
    under_18_by_date = models.BooleanField(null=True, help_text="Will you be under 18 on January 22, 2026")
    parental_consent_form_signed = models.BooleanField(null=True, default=None)
    agree_to_media_release = models.BooleanField(null=False, default=False)
    agree_to_liability_release = models.BooleanField(null=False, default=False)
    agree_to_rules_code_of_conduct = models.BooleanField(null=False, default=False)
    emergency_contact_name = models.CharField(max_length=200, null=False, blank=False)
    personal_phone_number = PhoneNumberField(blank=False, null=False)
    emergency_contact_phone_number = PhoneNumberField(blank=False, null=False)
    emergency_contact_email = models.EmailField(blank=False, null=False)
    emergency_contact_relationship = models.CharField(max_length=100, null=False, blank=False)
    special_interest_track_one = models.CharField(
        max_length=1,
        choices=[('Y', 'Yes'),('N', 'No')],
        null=True
    )
    special_interest_track_two = models.CharField(
        max_length=1,
        choices=[('Y', 'Yes'),('N', 'No')],
        null=True
    )
    breakthrough_hacks_interest = models.TextField(
        max_length=2000, null=True, blank=False
    )
    loaner_headset_preference = models.CharField(
        max_length=24,
        choices=LoanerHeadsetPreference.choices,
        null=True
    )
    device_preference_ranked = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="List other devices you are interested in ranked by preference."
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

    class Meta:
        verbose_name = "attendees"
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['first_name',]),
            models.Index(fields=['last_name']),
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['is_staff']),
            models.Index(fields=['authentication_id'])
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Name: {self.first_name} {self.last_name}, Email: {self.email}"


class EventRsvp(models.Model):

    class Status(models.TextChoices):
        RSVP = 'R', _("RSVP'd")
        ARRIVED = 'A', _("Arrived")
        CANCELED = 'C', _("Canceled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name='%(class)s_set'
    )
    attendee = models.ForeignKey(
        Attendee, on_delete=models.CASCADE, related_name='%(class)s_set'
    )

    # start previous attendee fields
    communication_platform_username = models.CharField(
        max_length=40, null=True, help_text="I.e., a Discord username"
    )
    application = models.OneToOneField(
        Application, on_delete=models.CASCADE, null=True
    )
    participation_role = models.CharField(
        max_length=1,
        choices=ParticipationRole.choices,
        default=ParticipationRole.SPECIALIST,
        null=True
    )
    guardian_of = models.ManyToManyField(
        "Attendee",
        related_name='rsvp_attendee_guardian_of',
        blank=True
    )
    sponsor_handler = models.ForeignKey(
        "Attendee",
        related_name="rsvp_attendee_sponsor_of",
        null=True,
        on_delete=models.SET_NULL
    )
    shirt_size = models.CharField(
        max_length=1,
        choices=ShirtSize.choices,
        default=ShirtSize.M,
        null=True
    )
    intended_tracks = MultiSelectField(
        max_choices=2, max_length=7, null=True, choices=Track.choices
    )
    intended_hardware_hack = models.BooleanField(default=False, null=False)
    prefers_destiny_hardware = MultiSelectField(
        max_choices=len(DestinyHardware.choices),
        max_length=len(DestinyHardware.choices) * 2 + 1,
        null=True, choices=DestinyHardware.choices
    )
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
    visa_support_form_confirmation = models.BooleanField(null=False, default=False)
    # getting rid of this, but keeping here for back compat
    us_visa_letter_of_invitation_required = models.BooleanField(
        null=True, default=False
    )
    us_visa_support_full_name = models.CharField(max_length=200, blank=False, null=True)
    us_visa_support_document_number = models.CharField(
        max_length=50, blank=False, null=True
    )
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
    under_18_by_date = models.BooleanField(
        null=True, help_text="Will you be under 18 on January 22, 2026"
    )
    parental_consent_form_signed = models.BooleanField(null=True, default=None)
    agree_to_media_release = models.BooleanField(null=False, default=False)
    agree_to_liability_release = models.BooleanField(null=False, default=False)
    agree_to_rules_code_of_conduct = models.BooleanField(null=False, default=False)
    emergency_contact_name = models.CharField(max_length=200, null=False, blank=False)
    personal_phone_number = PhoneNumberField(blank=False, null=False)
    emergency_contact_phone_number = PhoneNumberField(blank=False, null=False)
    emergency_contact_email = models.EmailField(blank=False, null=False)
    emergency_contact_relationship = models.CharField(
        max_length=100, null=False, blank=False
    )
    special_interest_track_one = models.CharField(
        max_length=1,
        choices=[('Y', 'Yes'), ('N', 'No')],
        null=True
    )
    special_interest_track_two = models.CharField(
        max_length=1,
        choices=[('Y', 'Yes'), ('N', 'No')],
        null=True
    )
    breakthrough_hacks_interest = models.TextField(
        max_length=2000, null=True, blank=False
    )
    loaner_headset_preference = models.CharField(
        max_length=24,
        choices=LoanerHeadsetPreference.choices,
        null=True
    )
    device_preference_ranked = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
        help_text="List other devices you are interested in ranked by preference."
    )
    app_in_store = models.CharField(
        max_length=250, null=True, blank=False,
        help_text="AR or VR apps in any store? And if so, which ones?"
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

    objects = EventScopedManager()

    def __str__(self) -> str:  # pragma: no cover
        return f"Event: {self.event}, Email: {self.attendee.email}"

    class Meta:
        unique_together = [('attendee', 'event')]
        indexes = [
            models.Index(fields=['event', 'attendee']),
            models.Index(fields=['event', 'participation_role']),
        ]


class Location(models.Model):
    class Room(models.TextChoices):
        MAIN_HALL = 'MH', _('Morss Hall')
        ATLANTIS = 'AT', _('Atlantis')
        NEPTUNE = 'NE', _('Neptune')
        ROOM_124 = '24', _('32-124')
        ROOM_144 = '44', _('32-144')
        ROOM_141 = '41', _('32-141')

    class Building(models.TextChoices):
        STATA = 'ST', _('Stata')
        WALKER = 'WK', _('Walker')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    building = models.CharField(
        max_length=2,
        choices=Building.choices,
        default=Building.WALKER
    )
    room = models.CharField(
        max_length=2,
        choices=Room.choices,
        default=Room.MAIN_HALL
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventScopedManager()

    def __str__(self) -> str:  # pragma: no cover
        return f"Building: {self.building}, Room: {self.room}"


class Table(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    number = models.PositiveBigIntegerField()
    location = models.ForeignKey(Location, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventScopedManager()

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.number}"


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    number = models.IntegerField(null=True)
    name = models.CharField(max_length=50)
    attendees = models.ManyToManyField(Attendee, related_name="team_attendees", blank=True)
    table = models.OneToOneField(Table, on_delete=models.SET_NULL, null=True, blank=True)
    tracks = MultiSelectField(choices=Track.choices, max_length=len(Track.choices) * 2 + 1, max_choices=len(Track.choices), blank=True)
    hardware_hack = models.BooleanField(default=False, null=False)
    startup_hack = models.BooleanField(default=False, null=False)
    destiny_hardware = MultiSelectField(choices=DestinyHardware.choices, max_length=30, max_choices=len(DestinyHardware), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    devpost_url = models.URLField(null=True)
    github_url = models.URLField(null=True)
    team_description = models.TextField(max_length=2000, null=True)
    # add census field

    objects = EventScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=['event', 'name']),
            models.Index(fields=['name']),
            models.Index(fields=['table'])
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Name: {self.name}, Table: {self.table}, Number: {self.number}"
    
    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        if created:
            instance.number = Team.objects.for_event(instance.event).count() + 1
            instance.save()


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=1000, blank=False, null=False)
    repository_location = models.URLField()
    submission_location = models.URLField()
    team = models.OneToOneField(Team, on_delete=models.SET_NULL, null=True)
    census_location_override = models.CharField(max_length=75, null=True, blank=True)
    census_taker_name = models.CharField(max_length=75, null=True, blank=True)
    team_primary_contact = models.CharField(max_length=75, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventScopedManager()

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
        pass
        # channel_layer = get_channel_layer()
        # room_group_name = f"lighthouse_{instance.table.number}"
        # lighthouse = {
        #     # "id": instance.id,
        #     "table": instance.table.number,
        #     "ip_address": instance.ip_address,
        #     "mentor_requested": instance.mentor_requested,
        #     "announcement_pending": instance.announcement_pending
        # }
        # async_to_sync(channel_layer.group_send)(
        #     room_group_name, {"type": "chat.message", "message": lighthouse}
        # )
        # async_to_sync(channel_layer.group_send)(
        #     "lighthouses", {"type": "chat.message", "message": lighthouse}
        # )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    announcement_pending = models.CharField(choices=AnnouncementStatus.choices ,max_length=1, default=AnnouncementStatus.RESOLVE.value)
    mentor_requested = models.CharField(choices=MentorRequestStatus.choices, max_length=1, default=MentorRequestStatus.RESOLVED.value)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventScopedManager()

    def __str__(self) -> str:  # pragma: no cover
        return f"Table: {self.table}, IP: {self.ip_address}"


class MentorHelpRequestCategory(models.TextChoices):
    DEVELOPMENT = 'D', _('Development')
    DESIGN = 'A', _('Design')
    PROTOTYPING = 'P', ('Prototyping')
    PROJECT_MANAGEMENT = 'M', ('Project Management and Leadership')
    SPECIALTY = 'S', ('Specialty')


class MentorHelpRequest(models.Model):

    @classmethod
    def post_save(cls, sender, instance, created, **kwargs):
        pass
        # table = instance.team.table
        # lighthouse = LightHouse.objects.get(table=table.id)
        # lighthouse.mentor_requested = instance.status
        # lighthouse.save()

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    title = models.CharField(max_length=250, null=True)
    description = models.TextField(max_length=2000, null=True)
    category = models.CharField(choices=MentorHelpRequestCategory.choices, null=True, max_length=1)
    category_specialty = models.CharField(max_length=100, null=True)
    topic = MultiSelectField(choices=MENTOR_HELP_REQUEST_TOPICS, max_choices=85, max_length=len(MENTOR_HELP_REQUEST_TOPICS) * 3)
    topic_other = models.CharField(max_length=50, null=True)
    reporter = models.ForeignKey(Attendee, on_delete=models.SET_NULL, null=True, related_name="mentor_help_request_reporter")
    mentor = models.ForeignKey(Attendee, on_delete=models.SET_NULL, null=True, related_name="mentor_help_request_mentor")
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    reporter_location = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(choices=MentorRequestStatus.choices, max_length=1, default=MentorRequestStatus.REQUESTED.value)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    objects = EventScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=['event', 'status', 'created_at']),
        ]

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
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
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
        choices=HardwareTags.choices, max_length=len(HardwareTags.choices) * 2 * 2 + 1, null=True)
    relates_to_destiny_hardware = models.CharField(choices=DestinyHardware.choices, max_length=1, null=True)

    objects = EventScopedManager()

    def __str__(self) -> str:  # pragma: no cover
        return f"Name: {self.name}"


class HardwareDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    hardware = models.ForeignKey(Hardware, on_delete=models.CASCADE)
    serial = models.CharField(max_length=100)
    checked_out_to = models.OneToOneField(
        'HardwareRequest', on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    objects = EventScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=['event', 'hardware']),
        ]

    def __str__(self) -> str:  # pragma: no cover
        return f"Hardware: {self.hardware}, Serial: {self.serial}"


class HardwareRequestStatus(models.TextChoices):
    PENDING = 'P', _('Pending')
    APPROVED = 'A', _('Approved')
    REJECTED = 'R', _('Rejected')
    CHECKED_OUT = 'C', _('Checked out')


class HardwareRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
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

    objects = EventScopedManager()

    class Meta:
        indexes = [
            models.Index(fields=['event', 'hardware', 'status']),
        ]
    
    def __str__(self) -> str:  # pragma: no cover
        return f"Hardware: {self.hardware}, Requester: {self.requester} (Team: {self.team})"

class Workshop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    name = models.CharField(max_length=300, null=False)
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

    objects = EventScopedManager()

    def __str__(self):
        return f"Name: {self.name}, Date: {self.datetime}, Duration: {self.duration}"


class WorkshopAttendee(models.Model):
    class Participation(models.TextChoices):
        RSVP = "R", _("RSVP'd")
        CONFIRMED = "C", _("Confirmed")
        INSTRUCTOR = "I", _("Instructor")
        VOLUNTEER = "V", _("Volunteer")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
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

    objects = EventScopedManager()

    def __str__(self):
        return f"Attendee: {self.attendee}, Participation: {self.participation}, Workshop: {self.workshop}"


class AttendeePreference(models.Model):
    class Preference(models.TextChoices):
        YAY = "Y"
        NAY = "N"
        TBD = "T"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    preferer = models.ForeignKey(Attendee, null=False, on_delete=models.CASCADE, related_name="attendee_preference_preferer")
    preferee = models.ForeignKey(Attendee, null=False, on_delete=models.CASCADE, related_name="attendee_preference_preferee")
    preference = models.CharField(choices=Preference.choices, null=False, max_length=1, blank=False)

    objects = EventScopedManager()

    def __str__(self):
        return f"Preferrer: {self.preferer}, Preferee: {self.preferee}, Preference: {self.preference}"


class DestinyTeam(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    attendees = models.ManyToManyField(Attendee, related_name="destiny_team_attendees", blank=True)
    table = models.ForeignKey(Table, on_delete=models.SET_NULL, null=True)
    track = models.CharField(choices=Track.choices, max_length=1, null=True)
    round = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    hardware_hack = models.BooleanField(default=False, null=False)
    destiny_hardware = MultiSelectField(choices=DestinyHardware.choices, max_length=30, max_choices=len(DestinyHardware), blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = EventScopedManager()

    def __str__(self):  # pragma: no cover
        return f"Table: {self.table}, Round: {self.round}"


class DestinyTeamAttendeeVibe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='%(class)s_set')
    destiny_team = models.ForeignKey(DestinyTeam, null=False, on_delete=models.CASCADE)
    attendee = models.ForeignKey(Attendee, null=False, on_delete=models.CASCADE)
    vibe = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    objects = EventScopedManager()

    def __str__(self):
        return f"Destiny Team: {self.destiny_team}, Attendee: {self.attendee}, Vibe: {self.vibe}"


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
# post_save.connect(
    # LightHouse.post_save, sender=LightHouse, dispatch_uid="lighthouse_entry_saved"
# )
post_save.connect(
    MentorHelpRequest.post_save, sender=MentorHelpRequest, dispatch_uid="mentor_help_request_entry_saved"
)

post_save.connect(
    Team.post_save, sender=Team, dispatch_uid='new_team_registered'   
)