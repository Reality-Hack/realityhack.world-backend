from django.contrib.auth.models import Group
from rest_framework import serializers

from infrastructure.models import (Attendee, Hardware, HardwareDevice,
                                   HelpDesk, Location, Project, Skill,
                                   SkillProficiency, Table, Team)


class GroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = Group
        fields = ['id', 'name']


class GroupDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']


class AttendeeSerializer(serializers.ModelSerializer):
    # metadata = SerializerMethodField()

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name', 'groups',
                  'username', 'email', 'is_staff',
                  #   'metadata',
                  'created_at', 'updated_at']


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']


class SkillProficiencyDetailSerializer(serializers.ModelSerializer):
    attendee = AttendeeSerializer()
    skill = SkillSerializer()

    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency', 'attendee',
                  'created_at', 'updated_at']


class SkillProficiencySerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency', 'attendee',
                  'created_at', 'updated_at']


class SkillProficiencyCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency', 'attendee']


class SkillProficiencyAttendeeSerializer(serializers.ModelSerializer):
    skill = SkillSerializer()

    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency']


class AttendeeDetailSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    skill_proficiencies = SkillProficiencyAttendeeSerializer(many=True)

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name', 'groups',
                  #   'metadata',
                  'username', 'email', 'is_staff', 'skill_proficiencies',
                  'created_at', 'updated_at']


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'building', 'room',
                  'created_at', 'updated_at']


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'number', 'location', 'created_at', 'updated_at']


class TableTruncatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id']


class TableDetailSerializer(serializers.ModelSerializer):
    location = LocationSerializer()

    class Meta:
        model = Table
        fields = ['id', 'number', 'location', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'repository_location', 'submission_location',
                  'team', 'created_at', 'updated_at']


class HelpDeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpDesk
        fields = ['id', 'table', 'ip_address', 'mentor_requested',
                  'announcement_pending']


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table', 'created_at', 'updated_at']


class TeamProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'repository_location', 'submission_location',
                  'created_at', 'updated_at']


class TeamHelpDeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpDesk
        fields = ['id', 'announcement_pending', 'mentor_requested',
                  'created_at', 'updated_at']


class TeamDetailSerializer(serializers.ModelSerializer):
    table = TableDetailSerializer()
    attendees = AttendeeSerializer(many=True)
    project = TeamProjectSerializer()
    help_desk = TeamHelpDeskSerializer()

    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table', 'project', 'help_desk',
                  'created_at', 'updated_at']


class TeamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table']


class TableDetailSerializer(serializers.ModelSerializer):
    team = TeamSerializer()
    help_desk = HelpDeskSerializer()

    class Meta:
        model = Table
        fields = ['id', 'number', 'location', 'team', 'help_desk',
                  'created_at', 'updated_at']


class TableCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'number', 'location']


class MentorRequestSerializer(serializers.Serializer):
    table = serializers.IntegerField()


class HelpDesksSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpDesk
        fields = ['id', 'table', 'ip_address', 'announcement_pending',
                  'mentor_requested', 'auxiliary_requested',
                  'created_at', 'updated_at']


class HardwareCountSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField()
    checked_out = serializers.IntegerField()
    total = serializers.IntegerField()

    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image',
                  'available', 'checked_out', 'total',
                  'created_at', 'updated_at']


class HardwareDeviceHardwareCountDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareDevice
        fields = ['id', 'serial', 'checked_out_to',
                  'created_at', 'updated_at']


class HardwareCountDetailSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField()
    checked_out = serializers.IntegerField()
    total = serializers.IntegerField()
    hardware_devices = HardwareDeviceHardwareCountDetailSerializer(many=True)

    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image',
                  'available', 'checked_out', 'total',
                  'created_at', 'updated_at', 'hardware_devices']


class HardwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image',
                  'created_at', 'updated_at']


class HardwareDeviceHardwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hardware
        fields = ['id', 'name']


class HardwareDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareDevice
        fields = ['id', 'hardware', 'serial', 'checked_out_to',
                  'created_at', 'updated_at']


class HardwareDeviceDetailSerializer(serializers.ModelSerializer):
    hardware = HardwareDeviceHardwareSerializer(read_only=True)
    checked_out_to = AttendeeSerializer(read_only=True)

    class Meta:
        model = HardwareDevice
        fields = ['id', 'hardware', 'serial', 'checked_out_to',
                  'created_at', 'updated_at']
