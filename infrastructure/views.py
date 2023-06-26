from django.contrib.auth.models import Group
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from infrastructure.models import (Attendee, Hardware, HardwareDevice,
                                   HelpDesk, Location, Project, Skill,
                                   SkillProficiency, Table, Team)
from infrastructure.serializers import (AttendeeSerializer,
                                        GroupDetailSerializer,
                                        HardwareDeviceSerializer,
                                        HardwareSerializer, HelpDeskSerializer,
                                        LocationSerializer, ProjectSerializer,
                                        SkillProficiencySerializer,
                                        SkillSerializer, TableSerializer,
                                        TeamCreateSerializer,
                                        TeamDetailSerializer, TeamSerializer)


class AttendeeViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Attendee.objects.all().order_by('-date_joined')
    serializer_class = AttendeeSerializer
    permission_classes = [permissions.AllowAny]


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
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return TeamSerializer
        if self.action == 'create':
            return TeamCreateSerializer
        if self.action == 'retrieve':
            return TeamDetailSerializer
        return TeamSerializer


class HelpDesksViewSet(viewsets.ViewSet):
    """
    API endpoint that allows Reality Kits to be viewed or edited.
    """
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        queryset = HelpDesk.objects.all()
        help_desks = []
        for help_desk in queryset:
            help_desks.append(
                {
                    "table": help_desk.table.number,
                    "ip_address": help_desk.ip_address,
                    "mentor_requested": help_desk.mentor_requested,
                    "announcement_pending": help_desk.announcement_pending
                }
            )
        serializer = HelpDeskSerializer(help_desks, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        import pdb
        pdb.set_trace()

    def create(self, request):
        help_desk_message = request.data
        # {'table': 1, 'ip_address': '10.198.1.112'}
        help_desk_query = HelpDesk.objects.filter(
            table__number=help_desk_message["table"])
        if len(help_desk_query) > 0:
            help_desk = help_desk_query[0]
            help_desk.ip_address = help_desk_message["ip_address"]
            help_desk.save()
        else:
            HelpDesk.objects.create(
                table=help_desk_message["table"],
                ip_address=help_desk_message["ip_address"]
            )
        help_desk_message["mentor_requested"] = help_desk.mentor_requested
        help_desk_message["announcement_pending"] = help_desk.announcement_pending
        return Response(data=help_desk_message, status=201)


class MentorRequestViewSet(viewsets.ViewSet):
    """
    API endpoint that allows Mentor Requests to be viewed or edited.
    """
    permission_classes = [permissions.AllowAny]

    def create(self, request):
        help_desk_message = request.data
        # {'table': 1, 'requested': True}
        help_desk_query = HelpDesk.objects.filter(
            table__number=help_desk_message["table"])
        if len(help_desk_query) > 0:
            help_desk = help_desk_query[0]
            if help_desk_message.get("mentor_requested"):
                help_desk.mentor_requested = True
                help_desk.save()
                return Response(help_desk_message, status=201)
            else:
                help_desk.mentor_requested = False
                help_desk.save()
                return Response(help_desk_message, status=204)
        else:
            return Response(status=404)

    def list(self, request):
        queryset = HelpDesk.objects.filter(mentor_requested=True)
        help_desks = []
        for help_desk in queryset:
            help_desks.append(
                {
                    "table": help_desk.table.number,
                    "ip_address": help_desk.ip_address,
                    "mentor_requested": help_desk.mentor_requested
                }
            )
        serializer = HelpDeskSerializer(help_desks, many=True)
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
    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.AllowAny]


class HardwareViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Hardware.objects.all()
    serializer_class = HardwareSerializer
    permission_classes = [permissions.AllowAny]


class HardwareDeviceViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = HardwareDevice.objects.all()
    serializer_class = HardwareDeviceSerializer
    permission_classes = [permissions.AllowAny]
