from rest_framework import serializers
from infrastructure.models import Skill, Attendee, Location, Table, Team, HelpDesk, Project, SkillProficiency, Hardware, HardwareDevice
from django.contrib.auth.models import Group


class AttendeeSerializer(serializers.HyperlinkedModelSerializer):
    skill_proficiencies = serializers.ReadOnlyField
    class Meta:
        model = Attendee
        fields = ['url', 'username', 'email', 'is_staff', 'roles']


class SkillSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Skill
        fields = ['url', 'name']


class SkillProficiencySerializer(serializers.HyperlinkedModelSerializer):
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


class TeamSerializer(serializers.HyperlinkedModelSerializer):
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
        fields = ['url', 'table', 'ip_address', 'announcement_pending', 'mentor_requested', 'auxiliary_requested']


class ProjectSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Project
        fields = ['url', 'name', 'repository_location', 'submission_location']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']


class HardwareSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Hardware
        fields = ['url', 'name', 'description', 'image']


class HardwareDeviceSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = HardwareDevice
        fields = ['url', 'hardware', 'serial', 'checked_out_to']