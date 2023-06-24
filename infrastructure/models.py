import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from multiselectfield import MultiSelectField

# settings.AUTH_USER_MODEL

class Skill(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)

    def __str__(self) -> str:
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
    attendee = models.ForeignKey('Attendee', on_delete=models.CASCADE)

    class Meta:
        verbose_name = "skill proficiencies"

    def __str__(self) -> str:
        return f"Skill: {self.skill}, Proficiency: {self.proficiency}"


class Attendee(AbstractUser):
    ROLES = (('P', 'Participant'),
        ('O', 'Organizer'),
        ('M', 'Mentor'),
        ('S', 'Sponsor'))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bio = models.TextField(max_length=1000, blank=True)
    roles = MultiSelectField(choices=ROLES, max_choices=3, max_length=3)

    class Meta:
        verbose_name = "attendees"

    def __str__(self) -> str:
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

    def __str__(self) -> str:
        return f"Building: {self.building}, Room: {self.room}"


class Table(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.PositiveBigIntegerField()
    location = models.ForeignKey(Location, on_delete=models.DO_NOTHING)

    def __str__(self) -> str:
        return f"{self.number}"


class Project(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    repository_location = models.URLField()
    submission_location = models.URLField()

    def __str__(self) -> str:
        return f"{self.name}"


class Team(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    attendees = models.ManyToManyField(Attendee)
    table = models.OneToOneField(Table, on_delete=models.DO_NOTHING)
    project = models.OneToOneField(Project, on_delete=models.DO_NOTHING)

    def __str__(self) -> str:
        return f"Name: {self.name}, Table: {self.table}, Project: {self.project}"


class HelpDesk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    table = models.ForeignKey(Table, on_delete=models.CASCADE)
    ip_address = models.GenericIPAddressField()
    announcement_pending = models.BooleanField(default=False)
    mentor_requested = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Table: {self.table}, IP: {self.ip_address}"


class Hardware(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=1000, blank=True)
    image = models.URLField()

    def __str__(self) -> str:
        return f"Name: {self.name}"


class HardwareDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hardware = models.ForeignKey(Hardware, on_delete=models.CASCADE)
    serial = models.CharField(max_length=100)
    checked_out_to = models.ForeignKey(Attendee, on_delete=models.CASCADE)

    def __str__(self) -> str:
        return f"Hardware: {self.hardware}, Serial: {self.serial}"
