import uuid

from django.db import models
from multiselectfield import MultiSelectField
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.translation import gettext_lazy as _
# settings.AUTH_USER_MODEL

ROLES = (('P', 'Participant'),
        ('O', 'Organizer'),
        ('M', 'Mentor'))


class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)


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
    attendee = models.ForeignKey('Attendee', on_delete=models.CASCADE)

    class Meta:
        verbose_name = "skill proficiencies"


class Attendee(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bio = models.TextField(max_length=1000, blank=True)
    role = MultiSelectField(choices=ROLES, max_choices=3, max_length=3)
    skills = models.ManyToManyField(Skill, through=SkillProficiency)

    class Meta:
        verbose_name = "attendees"


class Location(models.Model):
    class Room(models.TextChoices):
        MAIN_HALL = 'MH', _('Main Hall')
        ATLANTIS = 'AT', _('Atlantis')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    room = models.CharField(
        max_length=2,
        choices=Room.choices,
        default=Room.MAIN_HALL
    )


class Table(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.PositiveBigIntegerField()
    location = models.ForeignKey(Location, on_delete=models.DO_NOTHING)


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.URLField()


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    attendees = models.ManyToManyField(Attendee)
    table = models.OneToOneField(Table, on_delete=models.DO_NOTHING)
    project = models.OneToOneField(Project, on_delete=models.DO_NOTHING)


class RealityKit(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    announcement_pending = models.BooleanField(default=False)
    mentor_requested = models.BooleanField(default=False)
    auxiliary_requested = models.BooleanField(default=False)

    def __str__(self):
        return f"Table: {self.table.number}, IP: {self.ip_address}"


class Hardware(models.Model):
    pass
