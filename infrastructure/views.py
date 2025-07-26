from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django_keycloak_auth.decorators import keycloak_roles
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response

from infrastructure.mixins import LoggingMixin
from infrastructure.models import (Application, Attendee, AttendeePreference,
                                   DestinyTeam, DestinyTeamAttendeeVibe,
                                   Hardware, HardwareDevice, HardwareRequest,
                                   LightHouse, Location, MentorHelpRequest,
                                   Project, Skill, SkillProficiency, Table,
                                   Team, UploadedFile, Workshop,
                                   WorkshopAttendee)
from infrastructure.serializers import (ApplicationSerializer,
                                        AttendeeDetailSerializer,
                                        AttendeeListSerializer,
                                        AttendeePatchSerializer,
                                        AttendeePreferenceSerializer,
                                        AttendeeRSVPCreateSerializer,
                                        AttendeeRSVPSerializer,
                                        AttendeeSerializer,
                                        DestinyTeamAttendeeVibeSerializer,
                                        DestinyTeamSerializer,
                                        DestinyTeamUpdateSerializer,
                                        DiscordUsernameRoleSerializer,
                                        FileUploadSerializer,
                                        GroupDetailSerializer,
                                        HardwareCountDetailSerializer,
                                        HardwareCountSerializer,
                                        HardwareCreateSerializer,
                                        HardwareDeviceDetailSerializer,
                                        HardwareDeviceHistorySerializer,
                                        HardwareDeviceSerializer,
                                        HardwareRequestCreateSerializer,
                                        HardwareRequestDetailSerializer,
                                        HardwareRequestListSerializer,
                                        HardwareRequestSerializer,
                                        HardwareSerializer,
                                        LightHouseSerializer,
                                        LocationSerializer,
                                        MentorHelpRequestHistorySerializer,
                                        MentorHelpRequestReadSerializer,
                                        MentorHelpRequestSerializer,
                                        ProjectSerializer,
                                        SkillProficiencyCreateSerializer,
                                        SkillProficiencyDetailSerializer,
                                        SkillProficiencySerializer,
                                        SkillSerializer, TableCreateSerializer,
                                        TableDetailSerializer, TableSerializer,
                                        TeamCreateSerializer, TeamUpdateSerializer,
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
    SPONSOR = "sponsor"


def attendee_from_userinfo(request):  # pragma: nocover
    try:
        return Attendee.objects.get(authentication_id=request.userinfo.get("sub"))
    except Attendee.DoesNotExist:
        raise Http404(f"No attendee matches the authentication_id: \"{request.userinfo.get('sub')}\"")


def check_user(request, pk, special_roles={KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER}):
    if any(special_role in request.roles for special_role in special_roles):
        return "admin"
    if str(attendee_from_userinfo(request).id) != str(pk):
        raise PermissionDenied("You cannot modify people other than yourself.")
    return "user"


def prepare_attendee_for_detail(attendee):
    attendee.skill_proficiencies = SkillProficiency.objects.filter(attendee=attendee)
    attendee.team = attendee.team_attendees.first() or None
    attendee.hardware_devices = HardwareDevice.objects.filter(checked_out_to=attendee.id)
    attendee.workshops = WorkshopAttendee.objects.filter(attendee=attendee.id)
    return attendee


@cache_page(60 * 3)
@vary_on_headers("Authorization")
@keycloak_roles([KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.ATTENDEE, KeycloakRoles.MENTOR])
@api_view(['GET', 'PATCH'])
def me(request):
    """
    API endpoint for getting detailed information about an authenticated user.
    """
    if request.method == "GET":
        attendee = attendee_from_userinfo(request)
        attendee.skill_proficiencies = SkillProficiency.objects.filter(
            attendee=attendee)
        attendee = prepare_attendee_for_detail(attendee)
        serializer = AttendeeDetailSerializer(attendee)
        return Response(serializer.data)
    else:  # PATCH
        attendee = attendee_from_userinfo(request)
        serializer = AttendeePatchSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            for key in request.data.keys():
                if key == "profile_image":
                    try:
                        uploaded_file = UploadedFile.objects.get(id=request.data["profile_image"])
                        attendee.profile_image = uploaded_file
                    except UploadedFile.DoesNotExist:  # pragma: nocover
                        raise Http404(f"No uploaded file matches the id: \"{request.data['profile_image']}\"")
                else:
                    setattr(attendee, key, request.data[key])
            attendee.save()
            serializer = AttendeePatchSerializer(attendee)
            return Response(serializer.data, status=200)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)


class AttendeeViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Attendee.objects.all().order_by('-date_joined')
    permission_classes = [permissions.AllowAny]
    filterset_fields = [
        'first_name', 'last_name', 'communications_platform_username', 'email',
        'participation_class', 'participation_role', 'checked_in_at'
    ]
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.ATTENDEE],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.ATTENDEE]
    }

    def get_serializer_class(self):
        if self.action == 'partial_update':
            return AttendeePatchSerializer
        elif self.action == "list":
            return AttendeeListSerializer
        return AttendeeSerializer

    def retrieve(self, request, pk=None):
        check_user(request, pk)
        attendee = get_object_or_404(Attendee, pk=pk)
        attendee = prepare_attendee_for_detail(attendee)
        serializer = AttendeeDetailSerializer(attendee)
        return Response(serializer.data)

    def update(self, request, pk=None, **kwargs):
        check_user(request, pk)
        return super().update(request, pk=pk, **kwargs)

    def partial_update(self, request, pk=None, **kwargs):
        check_user(request, pk)
        return super().partial_update(request, pk, **kwargs)

    @method_decorator(cache_page(60 * 60 * 2))
    def list(self, request):
        return super().list(request)


class AttendeeRSVPViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Attendee.objects.all().order_by('-date_joined')
    serializer_class = AttendeeRSVPSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = [
        'first_name', 'last_name', 'communications_platform_username', 'email', 'checked_in_at',
        'participation_class', 'participation_role'
    ]
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
    }

    def get_serializer_class(self):
        if self.action == 'create':  # pragma: nocover
            return AttendeeRSVPCreateSerializer
        return AttendeeRSVPSerializer
    
    def create(self, request):
        application = None
        sponsor_handler = None
        guardian_of = []

        try:
            if "sponsor_handler" in request.data:
                sponsor_handler = Attendee.objects.get(pk=request.data["sponsor_handler"])
                del request.data["sponsor_handler"]
        except Attendee.DoesNotExist:  # pragma: nocover
            pass
        try:
            if "guardian_of" in request.data:
                guardian_of_attendees = list(Attendee.objects.filter(id__in=request.data["guardian_of"]))
                guardian_of = guardian_of_attendees
                del request.data["guardian_of"]
        except Attendee.DoesNotExist:  # pragma: nocover
            pass
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
            request.data["application"] = str(application.id)
        else:  # Volunteer or Organizer, or null
            if request.data.get("email") is not None:
                request.data["email"] = request.data.get("email").lower()
        serializer = AttendeeRSVPCreateSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            serializer_data = serializer.data
            attendee = None
            if serializer_data.get("application"):
                del serializer_data["application"]
                attendee = Attendee(application=application, **serializer_data)
                attendee.participation_role = application.participation_role
            else:
                attendee = Attendee(**serializer_data)
            attendee.username = attendee.email
            if request.data.get("authentication_id"):
                attendee.authentication_id = request.data["authentication_id"]
            attendee.sponsor_handler = sponsor_handler
            attendee.save()
            if guardian_of:
                attendee.guardian_of.set([guardian_of_attendee.id for guardian_of_attendee in guardian_of])
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
        except Team.DoesNotExist:  # pragma: nocover
            table.team = None
        try:
            table.lighthouse = LightHouse.objects.get(table=table)
        except LightHouse.DoesNotExist:
            table.lighthouse = None
        serializer = TableDetailSerializer(table)
        return Response(serializer.data)
    
    def list(self, request):
        queryset = Table.objects.all()
        serializer = TableSerializer(queryset, many=True)
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
        if self.action == 'partial_update':
            return TeamUpdateSerializer
        if self.action == 'retrieve':
            return TeamDetailSerializer
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
    
    def partial_update(self, request, *args, **kwargs):
        team = self.get_object()
        
        # Handle project fields
        project_fields = request.data.get('project')
        if project_fields:
            request.data.pop('project', None)
            try:
                team.project = Project.objects.get(team=team)
            except Project.DoesNotExist:
                team.project = Project(**project_fields)
            serialized_project = ProjectSerializer(team.project, project_fields, partial=True)
            if serialized_project.is_valid():
                serialized_project.update(team.project, serialized_project.validated_data)
            else:
                return Response(serialized_project.errors, status=status.HTTP_400_BAD_REQUEST)
            team.project.save()

        # Handle table fields
        table_fields = request.data.get('table')
        if table_fields:
            request.data.pop('table', None)
            try:
                table = Table.objects.get(id=table_fields.get('id'))
                team.table = table
                team.save()
            except Table.DoesNotExist:
                return Response(
                    {"table": f"Table with id {table_fields.get('id')} does not exist"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            except AttributeError:
                return Response(
                    {"table": "Invalid table data format. Expected {'id': <table_id>}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return super().partial_update(request, *args, **kwargs)


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

    def create(self, request):
        lighthouse_message = request.data
        lighthouse_message._mutable = True
        # {'table': 1, 'ip_address': '10.198.1.112'}
        lighthouse_query = LightHouse.objects.filter(
            table__number=lighthouse_message["table"])
        if len(lighthouse_query) > 0:
            lighthouse = lighthouse_query[0]
            lighthouse.ip_address = lighthouse_message["ip_address"]
            lighthouse.save()
        else:
            lighthouse = LightHouse.objects.create(
                table=Table.objects.get(number=lighthouse_message["table"]),
                ip_address=lighthouse_message["ip_address"]
            )
        lighthouse_message["mentor_requested"] = lighthouse.mentor_requested
        lighthouse_message["announcement_pending"] = lighthouse.announcement_pending
        return Response(data=lighthouse_message, status=201)


class MentorHelpRequestViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows mentor help requests to be viewed or edited.
    """
    queryset = MentorHelpRequest.objects.all().order_by('created_at')
    permission_classes = [permissions.AllowAny]
    filterset_fields = [
        'reporter', 'mentor', 'team', 'status', 'team__table__number'
    ]
    serializer_class = MentorHelpRequestSerializer
    read_serializer_class = MentorHelpRequestReadSerializer
    keycloak_roles = {
        'GET': [KeycloakRoles.ATTENDEE, KeycloakRoles.MENTOR, KeycloakRoles.ADMIN,],
        'POST': [KeycloakRoles.ATTENDEE],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.ATTENDEE],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.MENTOR, KeycloakRoles.ATTENDEE]
    }
	    
    def get_serializer_class(self):
        if self.action == 'list':
            return self.read_serializer_class
        return self.serializer_class


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
    filterset_fields = ["team"]


class GroupViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.AllowAny]


def hardware_count(hardware_type):
    hardware_devices = HardwareDevice.objects.filter(
        hardware=hardware_type)
    hardware_requests = HardwareRequest.objects.filter(
        hardware=hardware_type)
    hardware_devices_total = hardware_devices.count()
    requests_checked_out = hardware_requests.filter(status="C").count()
    requests_approved = hardware_requests.filter(status="A").count()
    # not necessarily true with one of the ways this could work
    # assert requests_checked_out == hardware_devices.filter(checked_out_to__isnull=False).count()
    hardware_devices_taken = requests_approved + requests_checked_out
    hardware_devices_available = (
        hardware_devices_total - hardware_devices_taken
    )
    return hardware_devices_available, requests_checked_out, hardware_devices_total


class HardwareViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows hardware to be viewed or edited.
    """
    queryset = Hardware.objects.all()
    serializer_class = HardwareSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['relates_to_destiny_hardware', 'tags']
    keycloak_roles = {
        'OPTIONS': [KeycloakRoles.ATTENDEE, KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER, KeycloakRoles.SPONSOR, KeycloakRoles.VOLUNTEER, KeycloakRoles.MENTOR, KeycloakRoles.JUDGE],
        # organizers need GET to view hardware in requests
        'GET': [KeycloakRoles.ATTENDEE, KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER, KeycloakRoles.SPONSOR],
        'POST': [KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER, KeycloakRoles.VOLUNTEER, KeycloakRoles.SPONSOR],
        'DELETE': [KeycloakRoles.ADMIN, KeycloakRoles.SPONSOR],
        'PATCH': [KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER, KeycloakRoles.VOLUNTEER, KeycloakRoles.SPONSOR]
    }

    def get_queryset(self):
        queryset = Hardware.objects.all()
        filters = {}
        for filterset_field in self.filterset_fields:
            if self.request.query_params.get(filterset_field):
                filterset_value = self.request.query_params.get(filterset_field)
                if filterset_field == "tags":
                    if not isinstance(filterset_value, list):
                        filterset_value = filterset_value.split(",")
                    filterset_field = "tags__contains"
                filters[filterset_field] = filterset_value
        if filters:
            queryset = Hardware.objects
            if "tags__contains" in filters:
                for tag in list(filters["tags__contains"]):
                    filters["tags__contains"] = tag
                    queryset = queryset.filter(**filters)
            else:
                queryset = queryset.filter(**filters)
        return queryset

    @classmethod
    def _iterate_hardware_count(cls, hardware_type):
        hardware_devices_available, hardware_devices_checked_out, hardware_devices_total = hardware_count(hardware_type)
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
        hardware_types = self.get_queryset()
        for hardware_type in hardware_types:
            self._iterate_hardware_count(hardware_type)
        serializer = HardwareCountSerializer(hardware_types, many=True)
        return Response(status=200, data=serializer.data)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return HardwareCreateSerializer
        elif self.action in ("update", "partial_update"):
            return HardwareCreateSerializer
        return HardwareSerializer


class HardwareDeviceViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows hardware devices to be viewed or edited.
    """
    queryset = HardwareDevice.objects.all()
    permission_classes = [permissions.AllowAny]
    filterset_fields = ['hardware', 'checked_out_to', 'serial',
                        'hardware__relates_to_destiny_hardware']
    keycloak_roles = {
        'GET': [KeycloakRoles.ATTENDEE, KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER],
        'POST': [KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER, KeycloakRoles.VOLUNTEER],
        'DELETE': [KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER]
    }

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return HardwareDeviceDetailSerializer
        return HardwareDeviceSerializer


class HardwareRequestsViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows hardware devices to be viewed or edited.
    """
    queryset = HardwareRequest.objects.all()
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["hardware", "requester__first_name", "requester__last_name", "requester__id", "team"]
    keycloak_roles = {
        "GET": [KeycloakRoles.ATTENDEE, KeycloakRoles.MENTOR, KeycloakRoles.JUDGE, KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER, KeycloakRoles.VOLUNTEER],
        "POST": [KeycloakRoles.ATTENDEE, KeycloakRoles.MENTOR, KeycloakRoles.JUDGE, KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER, KeycloakRoles.VOLUNTEER],
        "PATCH": [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.ATTENDEE],
        "DELETE": [KeycloakRoles.ATTENDEE, KeycloakRoles.MENTOR, KeycloakRoles.JUDGE, KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER, KeycloakRoles.VOLUNTEER]
    }
    
    def get_serializer_class(self):
        if self.action == 'create':
            return HardwareRequestCreateSerializer
        if self.action == 'partial_update':
            return HardwareRequestSerializer
        if self.action == 'retrieve':
            return HardwareRequestDetailSerializer
        return HardwareRequestListSerializer  # pragma: nocover

    @classmethod
    def _iterate_hardware_count(cls, hardware_type):
        hardware_devices_available, hardware_devices_checked_out, hardware_devices_total = hardware_count(hardware_type)
        hardware_type.available = hardware_devices_available
        hardware_type.checked_out = hardware_devices_checked_out
        hardware_type.total = hardware_devices_total

    def retrieve(self, request, pk=None):
        hardware_request = get_object_or_404(HardwareRequest, pk=pk)
        self._iterate_hardware_count(hardware_request.hardware)
        serializer = HardwareRequestDetailSerializer(hardware_request)
        return Response(serializer.data)

    def update(self, request, pk=None, **kwargs):
        hardware_request = get_object_or_404(HardwareRequest, pk=pk)
        role = check_user(request, hardware_request.requester.id)
        if role != "admin":
            if set(request.data.keys()) != set(["reason"]):
                raise PermissionDenied("Attendee cannot modify anything other than the reason of a request")
        return super().update(request, pk=pk, **kwargs)
    
    def delete(self, request, pk=None, **kwargs):
        hardware_request = get_object_or_404(HardwareRequest, pk=pk)
        check_user(request, hardware_request.requester.id,
                   special_roles={KeycloakRoles.MENTOR, KeycloakRoles.JUDGE, KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER, KeycloakRoles.VOLUNTEER})
        return super().delete(request, pk=pk, **kwargs)

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
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
    }
    
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)


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
        # TODO: implement a better way to handle 
        # 'POST': [KeycloakRoles.ATTENDEE, KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN]
    }

    # TODO: finish implementing cache refresh for file uploads
    # def retrieve(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     if instance.is_expired():
    #         instance.refresh_uri()
    #     serializer = self.get_serializer(instance)
    #     return Response(serializer.data)

    # def create(self, request, *args, **kwargs):
    #     response = super().create(request, *args, **kwargs)
    #     if response.status_code == 201:
    #         instance = UploadedFile.objects.get(id=response.data['id'])
    #         instance.refresh_uri()
    #         response.data['uri'] = instance.uri
    #         response.data['expires_at'] = instance.expires_at
    #     return response


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
    API endpoint that allows workshop attendees to be viewed or edited.
    """
    queryset = WorkshopAttendee.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkshopAttendeeSerializer
    filterset_fields = ['workshop', 'attendee', 'participation']


def preference_auth(fn):
    def wrapper(self, request, pk=None, **kwargs):
        attendee_preference = get_object_or_404(AttendeePreference, pk=pk)
        check_user(request, attendee_preference.preferer.id)
        return fn(self, request, pk=pk, **kwargs)
    return wrapper


class AttendeePreferenceViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows attendee preferences to be viewed or edited.
    """
    queryset = AttendeePreference.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = AttendeePreferenceSerializer
    filterset_fields = ['preferer', 'preferee', 'preference']

    keycloak_roles = {
        'GET': [KeycloakRoles.ATTENDEE],
        'POST': [KeycloakRoles.ATTENDEE],
        'DELETE': [KeycloakRoles.ATTENDEE],
        'PATCH': [KeycloakRoles.ATTENDEE]
    }

    def list(self, request):
        queryset = self.queryset
        filters = {}
        for filterset_field in self.filterset_fields:
            if request.query_params.get(filterset_field):
                filterset_value = request.query_params.get(filterset_field)
                filters[filterset_field] = filterset_value
        if not any(role in request.roles for role in {KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER}):
            user_id = str(attendee_from_userinfo(request).id)
            if filters.get("preferer") != user_id:
                raise PermissionDenied("Cannot browse other people's preferences")
        if filters:
            queryset = queryset.filter(**filters)
        return Response(status=200, data=AttendeePreferenceSerializer(queryset, many=True).data)
    
    @preference_auth
    def retrieve(self, request, pk=None, **kwargs):
        return super().retrieve(request, pk=pk, **kwargs)
    
    @preference_auth
    def update(self, request, pk=None, **kwargs):
        return super().update(request, pk=pk, **kwargs)
    
    @preference_auth
    def delete(self, request, pk=None, **kwargs):
        return super().delete(request, pk=pk, **kwargs)
    
    def create(self, request, pk=None, **kwargs):
        check_user(request, request.data["preferer"])
        return super().create(request, pk=pk, **kwargs)


class DestinyTeamViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Destiny teams to be viewed or edited.
    """
    queryset = DestinyTeam.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = DestinyTeamSerializer
    filterset_fields = ["attendees", "table__number", "track", "round"]
    keycloak_roles = {
        "POST": [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        "PATCH": [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        "OPTIONS": [KeycloakRoles.ATTENDEE, KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.VOLUNTEER, KeycloakRoles.MENTOR, KeycloakRoles.JUDGE],
        "GET": [KeycloakRoles.ATTENDEE]
    }
    
    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return DestinyTeamUpdateSerializer
        return DestinyTeamSerializer


def vibe_auth(fn):
    def wrapper(self, request, pk=None, **kwargs):
        attendee_preference = get_object_or_404(DestinyTeamAttendeeVibe, pk=pk)
        check_user(request, attendee_preference.preferer.id)
        return fn(self, request, pk=pk, **kwargs)
    return wrapper


class DestinyTeamAttendeeVibeViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows Detiny team attendee vibes to be viewed or edited.
    """
    queryset = DestinyTeamAttendeeVibe.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = DestinyTeamAttendeeVibeSerializer
    filterset_fields = ["destiny_team__round", "attendee", "vibe"]
    keycloak_roles = {
        "GET": [KeycloakRoles.ATTENDEE],
        "POST": [KeycloakRoles.ATTENDEE],
        "PATCH": [KeycloakRoles.ATTENDEE],
        "DELETE": [KeycloakRoles.ATTENDEE],
    }

    def list(self, request):
        queryset = self.queryset
        filters = {}
        for filterset_field in self.filterset_fields:
            if request.query_params.get(filterset_field):
                filterset_value = request.query_params.get(filterset_field)
                filters[filterset_field] = filterset_value
        if not any(role in request.roles for role in {KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER}):
            user_id = str(attendee_from_userinfo(request).id)
            if filters.get("attendee") != user_id:
                raise PermissionDenied("Cannot browse other people's vibes")
        if filters:
            queryset = queryset.filter(**filters)
        return Response(status=200, data=DestinyTeamAttendeeVibeSerializer(queryset, many=True).data)
    
    @vibe_auth
    def retrieve(self, request, pk=None, **kwargs):
        return super().retrieve(request, pk=pk, **kwargs)
    
    @vibe_auth
    def update(self, request, pk=None, **kwargs):
        return super().update(request, pk=pk, **kwargs)
    
    @vibe_auth
    def delete(self, request, pk=None, **kwargs):
        return super().delete(request, pk=pk, **kwargs)
    
    def create(self, request, pk=None, **kwargs):
        check_user(request, request.data["attendee"])
        return super().create(request, pk=pk, **kwargs)


def lighthouse(request):  # pragma: nocover
    return render(request, "infrastructure/lighthouse.html")


def lighthouse_table(request, table_number):  # pragma: nocover
    return render(request, "infrastructure/lighthouse_table.html", {"table_number": table_number})