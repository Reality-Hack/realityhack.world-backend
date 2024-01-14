from django.contrib.auth.models import Group
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django_keycloak_auth.decorators import keycloak_roles
from rest_framework import permissions, status, views, viewsets
from rest_framework.decorators import api_view
from rest_framework.mixins import RetrieveModelMixin, UpdateModelMixin
from rest_framework.response import Response

from infrastructure.mixins import LoggingMixin
from infrastructure.models import (Application, Attendee, Hardware,
                                   HardwareDevice, LightHouse, Location,
                                   MentorHelpRequest, Project, Skill,
                                   SkillProficiency, Table, Team, UploadedFile,
                                   Workshop, WorkshopAttendee)
from infrastructure.serializers import (ApplicationSerializer,
                                        AttendeeDetailSerializer,
                                        AttendeePatchSerializer,
                                        AttendeeRSVPCreateSerializer,
                                        AttendeeRSVPSerializer,
                                        AttendeeSerializer,
                                        DiscordUsernameRoleSerializer,
                                        FileUploadSerializer,
                                        GroupDetailSerializer,
                                        HardwareCountDetailSerializer,
                                        HardwareCountSerializer,
                                        HardwareDeviceDetailSerializer,
                                        HardwareDeviceHistorySerializer,
                                        HardwareDeviceSerializer,
                                        HardwareSerializer,
                                        LightHouseSerializer,
                                        LocationSerializer,
                                        MentorHelpRequestHistorySerializer,
                                        MentorHelpRequestSerializer,
                                        ProjectSerializer,
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
        attendee.skill_proficiencies = SkillProficiency.objects.filter(attendee=attendee)
        try:
            attendee.team = Team.objects.get(attendees__id=attendee.id)
        except Team.DoesNotExist:
            attendee.team = None
        attendee.hardware_devices = HardwareDevice.objects.filter(checked_out_to=attendee.id)
        attendee.workshops = WorkshopAttendee.objects.filter(attendee=attendee.id)
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
            attendee.skill_proficiencies = SkillProficiency.objects.filter(attendee=attendee)
            try:
                attendee.team = Team.objects.get(attendees__id=attendee.id)
            except Team.DoesNotExist:
                attendee.team = None
            attendee.hardware_devices = HardwareDevice.objects.filter(checked_out_to=attendee.id)
            attendee.workshops = WorkshopAttendee.objects.filter(attendee=attendee.id)
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
        'first_name', 'last_name', 'username', 'email', 'checked_in_at'
    ]
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.ATTENDEE],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
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
        'first_name', 'last_name', 'username', 'email', 'checked_in_at'
    ]
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
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
            table.lighthouse = LightHouse.objects.get(table=table)
        except LightHouse.DoesNotExist:
            table.lighthouse = None
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
            team.lighthouse = LightHouse.objects.get(table=team.table)
        except (Table.DoesNotExist, LightHouse.DoesNotExist):
            team.lighthouse = None
        serializer = TeamDetailSerializer(team)
        return Response(serializer.data)


class LightHouseViewSet(LoggingMixin, viewsets.ViewSet):
    """
    API endpoint that allows Reality Kits to be viewed or edited.
    """
    permission_classes = [permissions.AllowAny]
    lookup_field = "table__number"
    keycloak_roles = {
        'GET': [KeycloakRoles.ATTENDEE],
        'POST': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PUT': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN]
    }

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return LightHouseSerializer
        return LightHouseSerializer

    def list(self, request):
        queryset = LightHouse.objects.all()
        lighthouses = []
        for lighthouse in queryset:
            lighthouses.append(
                {
                    "id": lighthouse.id,
                    "table": lighthouse.table.number,
                    "ip_address": lighthouse.ip_address,
                    "mentor_requested": lighthouse.mentor_requested,
                    "announcement_pending": lighthouse.announcement_pending
                }
            )
        serializer = LightHouseSerializer(lighthouses, many=True)
        return Response(serializer.data)

    def retrieve(self, request, table__number=None):
        table = get_object_or_404(Table, number=table__number)
        lighthouse = get_object_or_404(LightHouse, table=table.id)
        serializer = LightHouseSerializer({
            "id": lighthouse.id,
            "table": lighthouse.table.number,
            "ip_address": lighthouse.ip_address,
            "mentor_requested": lighthouse.mentor_requested,
            "announcement_pending": lighthouse.announcement_pending
        })
        return Response(serializer.data)

    def create(self, request):
        lighthouse_message = request.data
        # {'table': 1, 'ip_address': '10.198.1.112'}
        lighthouse_query = LightHouse.objects.filter(
            table__number=lighthouse_message["table"])
        if len(lighthouse_query) > 0:
            lighthouse = lighthouse_query[0]
            lighthouse.ip_address = lighthouse_message["ip_address"]
            lighthouse.save()
        else:
            LightHouse.objects.create(
                table=lighthouse_message["table"],
                ip_address=lighthouse_message["ip_address"]
            )
        lighthouse_message["mentor_requested"] = lighthouse.mentor_requested
        lighthouse_message["announcement_pending"] = lighthouse.announcement_pending
        return Response(data=lighthouse_message, status=201)


class MentorHelpRequestViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows mentor help requests to be viewed or edited.
    """
    queryset = MentorHelpRequest.objects.all()
    permission_classes = [permissions.AllowAny]
    filterset_fields = [
        'reporter', 'mentor', 'team', 'status'
    ]
    serializer_class = MentorHelpRequestSerializer
    keycloak_roles = {
        'GET': [KeycloakRoles.ATTENDEE],
        'POST': [KeycloakRoles.ATTENDEE],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PUT': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN]
    }


class MentorHelpRequestViewSetHistoryViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows mentor help requests historical records to be viewed.
    """
    queryset = MentorHelpRequest.history.model.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = MentorHelpRequestHistorySerializer
    filterset_fields = [
        'id', 'reporter', 'mentor', 'team', 'status'
    ]
    keycloak_roles = {
        'GET': [KeycloakRoles.ATTENDEE],
        'POST': [KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ADMIN],
        'PUT': [KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ADMIN]
    }


class DiscordViewSet(LoggingMixin, viewsets.ViewSet):
    """
    API Endpoint that allows for Discord information to be viewed or edited.
    """
    permission_classes = [permissions.AllowAny]
    lookup_field = "attendee__communications_platform_username"

    def get_serializer_class(self):
        if self.action == 'list':
            return DiscordUsernameRoleSerializer
        return DiscordUsernameRoleSerializer

    def list(self, request):
        queryset = Attendee.objects.all()
        serializer = DiscordUsernameRoleSerializer(queryset, many=True)
        return Response(serializer.data)

    def destroy(self, request, attendee__communications_platform_username=None):
        attendee = get_object_or_404(Attendee, communications_platform_username=attendee__communications_platform_username)
        team = get_object_or_404(Team, attendees__id=attendee.id)
        table = team.table
        lighthouse = get_object_or_404(LightHouse, table=table.id)
        lighthouse.announcement_pending = LightHouse.AnnouncementStatus.RESOLVE
        lighthouse.save()
        serializer = LightHouseSerializer({
            "id": lighthouse.id,
            "table": lighthouse.table.number,
            "ip_address": lighthouse.ip_address,
            "mentor_requested": lighthouse.mentor_requested,
            "announcement_pending": lighthouse.announcement_pending
        })
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

def lighthouse(request):
    return render(request, "infrastructure/lighthouse.html")

def lighthouse_table(request, table_number):
    return render(request, "infrastructure/lighthouse_table.html", {"table_number": table_number})