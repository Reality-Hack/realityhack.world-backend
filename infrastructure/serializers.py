from rest_framework import serializers
from infrastructure.models import Skill, Attendee, Location, Table, Team, HelpDesk, Project, SkillProficiency
from django.contrib.auth.models import Group


class AttendeeSerializer(serializers.HyperlinkedModelSerializer):
    skill_proficiencies = serializers.ReadOnlyField
    class Meta:
        model = Attendee
        fields = ['url', 'username', 'email', 'is_staff', 'roles', 'skills']


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
        fields = ['url', 'room']

    
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
        fields = ['url', 'location']


class GroupSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Group
        fields = ['url', 'name']