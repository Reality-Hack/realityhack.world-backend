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
    groups = GroupSerializer(many=True, read_only=True)

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name', 'groups',
                  'username', 'email', 'is_staff']


class AttendeeTruncatedSerializer(serializers.ModelSerializer):

    class Meta:
        model = Attendee
        fields = ['id']


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']


class SkillProficiencySerializer(serializers.ModelSerializer):
    attendee = AttendeeSerializer()
    skill = SkillSerializer()

    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency', 'attendee']


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'building', 'room']


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'number', 'location']


class TableTruncatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id']


class TableDetailSerializer(serializers.ModelSerializer):
    location = LocationSerializer()

    class Meta:
        model = Table
        fields = ['id', 'number', 'location']


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'repository_location', 'submission_location', 'team']


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table']


class TeamDetailSerializer(serializers.ModelSerializer):
    table = TableDetailSerializer()
    attendees = AttendeeSerializer(many=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table']


class TeamCreateSerializer(serializers.ModelSerializer):
    # table = TableTruncatedSerializer(read_only=True)
    # attendees = AttendeeTruncatedSerializer(many=True, read_only=True)

    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table']


class HelpDeskSerializer(serializers.Serializer):
    table = serializers.IntegerField()
    ip_address = serializers.IPAddressField()
    mentor_requested = serializers.BooleanField()
    announcement_pending = serializers.BooleanField()


class MentorRequestSerializer(serializers.Serializer):
    table = serializers.IntegerField()


class HelpDesksSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpDesk
        fields = ['id', 'table', 'ip_address', 'announcement_pending',
                  'mentor_requested', 'auxiliary_requested']


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class HardwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image']


class HardwareDeviceHardwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hardware
        fields = ['id', 'name']


class HardwareDeviceSerializer(serializers.ModelSerializer):
    hardware = HardwareDeviceHardwareSerializer()
    checked_out_to = AttendeeSerializer()

    class Meta:
        model = HardwareDevice
        fields = ['id', 'hardware', 'serial', 'checked_out_to']
