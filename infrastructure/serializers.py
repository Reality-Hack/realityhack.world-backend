from django.contrib.auth.models import Group
from rest_framework import serializers

from infrastructure.models import (Attendee, Hardware, HardwareDevice,
                                   HelpDesk, Location, Project, Skill,
                                   SkillProficiency, Table, Team)


class AttendeeSerializer(serializers.HyperlinkedModelSerializer):
    skill_proficiencies = serializers.ReadOnlyField

    class Meta:
        model = Attendee
        fields = ['url', 'first_name', 'last_name', 'groups',
                  'username', 'email', 'is_staff', 'roles']


class SkillSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Skill
        fields = ['url', 'name']


class SkillProficiencySerializer(serializers.HyperlinkedModelSerializer):
    attendee = AttendeeSerializer()
    skill = SkillSerializer()

    class Meta:
        model = SkillProficiency
        fields = ['url', 'skill', 'proficiency', 'attendee']


class LocationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Location
        fields = ['url', 'building', 'room']


class TableSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Table
        fields = ['url', 'number', 'location']


class TableDetailSerializer(serializers.HyperlinkedModelSerializer):
    location = LocationSerializer()

    class Meta:
        model = Table
        fields = ['url', 'number', 'location']


class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Project
        fields = ['url', 'name', 'repository_location', 'submission_location']


class TeamSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Team
        fields = ['url', 'name', 'attendees', 'table', 'project']


class TeamDetailSerializer(serializers.HyperlinkedModelSerializer):
    project = ProjectSerializer()
    table = TableDetailSerializer()
    attendees = AttendeeSerializer(many=True)

    class Meta:
        model = Team
        fields = ['url', 'name', 'attendees', 'table', 'project']


class HelpDeskSerializer(serializers.Serializer):
    table = serializers.IntegerField()
    ip_address = serializers.IPAddressField()
    mentor_requested = serializers.BooleanField()
    announcement_pending = serializers.BooleanField()


class MentorRequestSerializer(serializers.Serializer):
    table = serializers.IntegerField()


class HelpDesksSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = HelpDesk
        fields = ['url', 'table', 'ip_address', 'announcement_pending',
                  'mentor_requested', 'auxiliary_requested']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


class HardwareSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Hardware
        fields = ['url', 'name', 'description', 'image']


class HardwareDeviceHardwareSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Hardware
        fields = ['url', 'name']


class HardwareDeviceSerializer(serializers.HyperlinkedModelSerializer):
    hardware = HardwareDeviceHardwareSerializer()
    checked_out_to = AttendeeSerializer()

    class Meta:
        model = HardwareDevice
        fields = ['url', 'hardware', 'serial', 'checked_out_to']
