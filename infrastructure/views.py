from django.contrib.auth.models import Group
from rest_framework import viewsets
from rest_framework import permissions
from infrastructure.serializers import AttendeeSerializer, SkillSerializer, LocationSerializer, TableSerializer, TeamSerializer, RealityKitSerializer, SkillProficiencySerializer, ProjectSerializer, GroupSerializer, MentorRequestSerializer
from infrastructure.models import Attendee, Skill, Location, Table, Team, RealityKit, SkillProficiency, Project
from rest_framework.decorators import action
from rest_framework.response import Response
from infrastructure.models import RealityKit

class AttendeeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Attendee.objects.all().order_by('-date_joined')
    serializer_class = AttendeeSerializer
    permission_classes = [permissions.AllowAny]

    def detail(request, attendee_id):
        skill_proficiencies = SkillProficiency.objects.filter(
            attendee_id=attendee_id
        )
        return 


class SkillViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows skills to be viewed or edited.
    """
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.AllowAny]


class LocationViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows locations to be viewed or edited.
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.AllowAny]


class TableViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tables to be viewed or edited.
    """
    queryset = Table.objects.all()
    serializer_class = TableSerializer
    permission_classes = [permissions.AllowAny]


class TeamViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows teams to be viewed or edited.
    """
    queryset = Team.objects.all()
    serializer_class = TeamSerializer
    permission_classes = [permissions.AllowAny]


class RealityKitsViewSet(viewsets.ViewSet):
    """
    API endpoint that allows Reality Kits to be viewed or edited.
    """
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        queryset = RealityKit.objects.all()
        reality_kits = []
        for reality_kit in queryset:
            reality_kits.append(
                {
                    "table": reality_kit.table.number,
                    "ip_address": reality_kit.ip_address,
                    "mentor_requested": reality_kit.mentor_requested,
                    "announcement_pending": reality_kit.announcement_pending
                }
            )
        serializer = RealityKitSerializer(reality_kits, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        import pdb;pdb.set_trace()

    def create(self, request):
        reality_kit_message = request.data
        # {'table': 1, 'ip_address': '10.198.1.112'}
        reality_kit_query = RealityKit.objects.filter(table__number=reality_kit_message["table"])
        if len(reality_kit_query) > 0:
            reality_kit = reality_kit_query[0]
            reality_kit.ip_address = reality_kit_message["ip_address"]
            reality_kit.save()
        else:
            RealityKit.objects.create(
                table=reality_kit_message["table"],
                ip_address=reality_kit_message["ip_address"]
            )
        reality_kit_message["mentor_requested"] = reality_kit.mentor_requested
        reality_kit_message["announcement_pending"] = reality_kit.announcement_pending
        return Response(data=reality_kit_message, status=201)


class MentorRequestViewSet(viewsets.ViewSet):
    """
    API endpoint that allows Mentor Requests to be viewed or edited.
    """
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        reality_kit_message = request.data
        # {'table': 1, 'requested': True}
        reality_kit_query = RealityKit.objects.filter(table__number=reality_kit_message["table"])
        if len(reality_kit_query) > 0:
            reality_kit = reality_kit_query[0]
            if reality_kit_message.get("mentor_requested"):
                reality_kit.mentor_requested = True
                reality_kit.save()
                return Response(reality_kit_message, status=201)
            else:
                reality_kit.mentor_requested = False
                reality_kit.save()
                return Response(reality_kit_message, status=204)
        else:
            return Response(status=404)

    def list(self, request):
        queryset = RealityKit.objects.filter(mentor_requested=True)
        reality_kits = []
        for reality_kit in queryset:
            reality_kits.append(
                {
                    "table": reality_kit.table.number,
                    "ip_address": reality_kit.ip_address,
                    "mentor_requested": reality_kit.mentor_requested
                }
            )
        serializer = RealityKitSerializer(reality_kits, many=True)
        return Response(serializer.data)


class SkillProficiencyViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows skill proficiencies to be viewed or edited.
    """
    queryset = SkillProficiency.objects.all()
    serializer_class = SkillProficiencySerializer
    permission_classes = [permissions.AllowAny]


class ProjectViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows projects to be viewed or edited.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.AllowAny]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.AllowAny]