from django.contrib.auth.models import Group
from django.http import Http404
from django.shortcuts import get_object_or_404
from django_keycloak_auth.decorators import keycloak_roles
from rest_framework import permissions, status, views, viewsets
from rest_framework.decorators import api_view
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response

from infrastructure.mixins import LoggingMixin
from infrastructure.models import (Application, Attendee, Hardware,
                                   HardwareDevice, HelpDesk, Location, Project,
                                   Skill, SkillProficiency, Table, Team,
                                   UploadedFile, Workshop, WorkshopAttendee)
from infrastructure.serializers import (ApplicationSerializer,
                                        AttendeeDetailSerializer,
                                        AttendeePatchSerializer,
                                        AttendeeRSVPCreateSerializer,
                                        AttendeeRSVPSerializer,
                                        AttendeeSerializer,
                                        FileUploadSerializer,
                                        GroupDetailSerializer,
                                        HardwareCountDetailSerializer,
                                        HardwareCountSerializer,
                                        HardwareDeviceDetailSerializer,
                                        HardwareDeviceHistorySerializer,
                                        HardwareDeviceSerializer,
                                        HardwareSerializer, HelpDeskSerializer,
                                        LocationSerializer, ProjectSerializer,
                                        SkillProficiencyCreateSerializer,
                                        SkillProficiencyDetailSerializer,
                                        SkillProficiencySerializer,
                                        SkillSerializer, TableCreateSerializer,
                                        TableDetailSerializer, TableSerializer,
                                        TeamCreateSerializer,
                                        TeamDetailSerializer, TeamSerializer,
                                        WorkshopAttendeeSerializer,
                                        WorkshopSerializer)


class KeycloakRoles(object):
    ATTENDEE = "attendee"
    ORGANIZER = "organizer"
    ADMIN = "admin"
    MENTOR = "mentor"
    JUDGE = "judge"
    VOLUNTEER = "volunteer"


@keycloak_roles([KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.ATTENDEE])
@api_view(['GET', 'PATCH'])
def me(request):
    """
    API endpoint for getting detailed information about an authenticated user.
    """
    if request.method == "GET":
        try:
            attendee = get_object_or_404(Attendee, authentication_id=request.userinfo.get("sub"))
        except Application.DoesNotExist:
            raise Http404(f"No attendee matches the authentication_id: \"{request.userinfo.get('sub')}\"")
        attendee.skill_proficiencies = SkillProficiency.objects.filter(
            attendee=attendee)
        serializer = AttendeeDetailSerializer(attendee)
        return Response(serializer.data)
    else:  # PATCH
        try:
            attendee = get_object_or_404(Attendee, authentication_id=request.userinfo.get("sub"))
        except Application.DoesNotExist:
            raise Http404(f"No attendee matches the authentication_id: \"{request.userinfo.get('sub')}\"")
        serializer = AttendeePatchSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            for key in request.data.keys():
                if key == "profile_image":
                    try:
                        uploaded_file = UploadedFile.objects.get(id=request.data["profile_image"])
                        attendee.profile_image = uploaded_file
                    except UploadedFile.DoesNotExist:
                        raise Http404(f"No uploaded file matches the id: \"{request.userinfo.get('sub')}\"")
                else:
                    setattr(attendee, key, request.data[key])
            attendee.skill_proficiencies = SkillProficiency.objects.filter(
            attendee=attendee)
            attendee.save()
            serializer = AttendeeDetailSerializer(attendee)
            return Response(serializer.data, status=200)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


class AttendeeViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Attendee.objects.all().order_by('-date_joined')
    serializer_class = AttendeeSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = [
        'first_name', 'last_name', 'username', 'email', 'is_staff', 'groups',
    ]
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.ATTENDEE],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PUT': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
    }

    def retrieve(self, request, pk=None):
        attendee = get_object_or_404(Attendee, pk=pk)
        attendee.skill_proficiencies = SkillProficiency.objects.filter(
            attendee=attendee)
        serializer = AttendeeDetailSerializer(attendee)
        return Response(serializer.data)


class AttendeeRSVPViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Attendee.objects.all().order_by('-date_joined')
    serializer_class = AttendeeRSVPSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = [
        'first_name', 'last_name', 'username', 'email', 'is_staff', 'groups',
    ]
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PUT': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
    }

    def get_serializer_class(self):
        if self.action == 'create':
            return AttendeeRSVPCreateSerializer
        return AttendeeRSVPSerializer
    
    def create(self, request):
        application = None
        if "application" in request.data:
            try:
                application = Application.objects.get(pk=request.data.get("application"))
            except Application.DoesNotExist:
                return Response(
                    f"No application matches the query: \"{request.data.get('application')}\"",
                    status=status.HTTP_400_BAD_REQUEST
                )
            request.data["first_name"] = application.first_name
            request.data["middle_name"] = application.middle_name
            request.data["last_name"] = application.last_name
            request.data["participation_class"] = application.participation_class
            request.data["email"] = application.email.lower()
            del request.data["application"]
        else:  # Volunteer or Organizer, or null
            if request.data.get("email") is not None:
                request.data["email"] = request.data.get("email").lower()
        serializer = AttendeeRSVPSerializer(data=request.data)
        if serializer.is_valid():
            serializer_data = serializer.data
            del serializer_data["application"]
            attendee = Attendee(application=application, **serializer_data)
            attendee.username = attendee.email
            attendee.participation_role = application.participation_role
            attendee.save()
            serializer = AttendeeRSVPSerializer(attendee)
            return Response(serializer.data, status=201)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)



class SkillViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows skills to be viewed or edited.
    """
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.AllowAny]


class LocationViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows locations to be viewed or edited.
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.AllowAny]


class TableViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows tables to be viewed or edited.
    """
    queryset = Table.objects.all()
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'list':
            return TableSerializer
        if self.action == 'create':
            return TableCreateSerializer
        return TableSerializer
    
    def retrieve(self, request, pk=None):
        table = get_object_or_404(Table, pk=pk)
        try:
            table.team = Team.objects.get(table=table)
        except Team.DoesNotExist:
            table.team = None
        try:
            table.help_desk = HelpDesk.objects.get(table=table)
        except HelpDesk.DoesNotExist:
            table.help_desk = None
        serializer = TableDetailSerializer(table)
        return Response(serializer.data)


class TeamViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows teams to be viewed or edited.
    """
    queryset = Team.objects.all()
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['name', 'attendees', 'table', 'table__number']

    def get_serializer_class(self):
        if self.action == 'list':
            return TeamSerializer
        if self.action == 'create':
            return TeamCreateSerializer
        return TeamSerializer

    def retrieve(self, request, pk=None):
        team = get_object_or_404(Team, pk=pk)
        try:
            team.project = Project.objects.get(team=team)
        except Project.DoesNotExist:
            team.project = None
        try:
            team.help_desk = HelpDesk.objects.get(table=team.table)
        except (Table.DoesNotExist, HelpDesk.DoesNotExist):
            team.help_desk = None
        serializer = TeamDetailSerializer(team)
        return Response(serializer.data)


class HelpDesksViewSet(LoggingMixin, viewsets.ViewSet):
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


class MentorRequestViewSet(LoggingMixin, viewsets.ViewSet):
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


class SkillProficiencyViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows skill proficiencies to be viewed or edited.
    """
    queryset = SkillProficiency.objects.all()
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return SkillProficiencyCreateSerializer
        if self.action == 'update':
            return SkillProficiencyCreateSerializer
        if self.action == 'partial_update':
            return SkillProficiencyCreateSerializer
        if self.action == 'retrieve':
            return SkillProficiencyDetailSerializer
        return SkillProficiencySerializer


class ProjectViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows projects to be viewed or edited.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.AllowAny]


class GroupViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.AllowAny]


class HardwareViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows hardware to be viewed or edited.
    """
    queryset = Hardware.objects.all()
    serializer_class = HardwareSerializer
    permission_classes = [permissions.AllowAny]

    @classmethod
    def _iterate_hardware_count(cls, hardware_type):
        hardware_devices = HardwareDevice.objects.filter(
            hardware=hardware_type)
        hardware_devices_available = hardware_devices.filter(
            checked_out_to__isnull=True).count()
        hardware_devices_checked_out = hardware_devices.filter(
            checked_out_to__isnull=False).count()
        hardware_devices_total = (
            hardware_devices_available + hardware_devices_checked_out
        )
        hardware_type.available = hardware_devices_available
        hardware_type.checked_out = hardware_devices_checked_out
        hardware_type.total = hardware_devices_total


    def retrieve(self, request, pk=None):
        hardware_type = get_object_or_404(Hardware, pk=pk)
        self._iterate_hardware_count(hardware_type)
        hardware_type.hardware_devices = HardwareDevice.objects.filter(
            hardware=hardware_type)
        serializer = HardwareCountDetailSerializer(hardware_type)
        return Response(serializer.data)


    def list(self, request):
        hardware_types = list(Hardware.objects.all())
        for hardware_type in hardware_types:
            self._iterate_hardware_count(hardware_type)
        serializer = HardwareCountSerializer(hardware_types, many=True)
        return Response(serializer.data)


class HardwareDeviceViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows hardware devices to be viewed or edited.
    """
    queryset = HardwareDevice.objects.all()
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['hardware', 'checked_out_to', 'serial']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return HardwareDeviceDetailSerializer
        return HardwareDeviceSerializer
    

class HardwareDeviceHistoryViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows hardware device historical records to be viewed.
    """
    queryset = HardwareDevice.history.model.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = HardwareDeviceHistorySerializer
    filterset_fields = ['hardware', 'checked_out_to', 'serial']


class ApplicationViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = Application.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = ApplicationSerializer
    filterset_fields = ['participation_capacity', 'participation_role', 'email']
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PUT': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
    }


class UploadedFileViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows files to be viewed or edited.
    """
    queryset = UploadedFile.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = FileUploadSerializer
    filterset_fields = ['claimed']
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PUT': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
    }


class WorkshopViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows workshops to be viewed ot edited.
    """
    queryset = Workshop.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkshopSerializer
    filterset_fields = ['datetime', 'location', 'recommended_for', 'hardware']


class WorkshopAttendeeViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows workshops to be viewed or edited.
    """
    queryset = WorkshopAttendee.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkshopAttendeeSerializer
    filterset_fields = ['workshop', 'attendee', 'participation']
