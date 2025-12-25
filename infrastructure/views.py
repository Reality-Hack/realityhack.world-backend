from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page, never_cache
from django.views.decorators.vary import vary_on_headers
from django_keycloak_auth.decorators import keycloak_roles
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import api_view
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes
from infrastructure.keycloak import KeycloakRoles
from infrastructure.mixins import LoggingMixin, EventScopedLoggingViewSet
from infrastructure.event_context import get_active_event
from infrastructure.models import (Application,
                                   Attendee, AttendeePreference,
                                   DestinyTeam, DestinyTeamAttendeeVibe,
                                   Hardware, HardwareDevice, HardwareRequest,
                                   LightHouse, Location, MentorHelpRequest,
                                   Project, Skill, SkillProficiency, Table,
                                   Team, UploadedFile, Workshop,
                                   WorkshopAttendee, EventRsvp,
                                   ApplicationQuestion, ApplicationResponse, Event)
from infrastructure.serializers import (ApplicationSerializer,
                                        ApplicationDetailSerializer,
                                        ApplicationQuestionSerializer,
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
                                        LightHouseSerializer, EventRsvpDetailSerializer,
                                        LocationSerializer, EventRsvpSerializer,
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
                                        WorkshopSerializer, EventSerializer)
from infrastructure.filters import (
    TeamFilter,
    MentorHelpRequestFilter,
    ProjectFilter,
    HardwareDeviceFilter,
    HardwareRequestFilter,
    WorkshopFilter,
    WorkshopAttendeeFilter,
)
from infrastructure.utils.rsvp_helpers import (
    get_sponsor_handler,
    get_guardian_of,
    get_application,
    create_event_rsvp_from_request,
    get_or_create_attendee_from_request,
    handle_keycloak_account_creation,
)


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


def prepare_attendee_for_detail(attendee, event=None):
    if event is None:
        event = get_active_event()
    attendee.skill_proficiencies = SkillProficiency.objects.for_event(event).filter(attendee=attendee)
    attendee.team = Team.objects.for_event(event).filter(attendees=attendee).first()
    attendee.hardware_devices = HardwareDevice.objects.for_event(event).filter(checked_out_to=attendee.id)
    attendee.workshops = WorkshopAttendee.objects.for_event(event).filter(attendee=attendee.id)
    return attendee


@cache_page(60 * 3)
@vary_on_headers("Authorization")
@keycloak_roles([KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN, KeycloakRoles.ATTENDEE, KeycloakRoles.MENTOR])
@extend_schema(
    methods=['GET'],
    request=None,
    responses={200: AttendeeDetailSerializer},
    description="Get detailed information about an authenticated user."
)
@extend_schema(
    methods=['PATCH'],
    request=AttendeePatchSerializer,
    responses={200: AttendeePatchSerializer},
    description="Update the authenticated user's information."
)
@api_view(['GET', 'PATCH'])
def me(request):
    """
    API endpoint for getting detailed information about an authenticated user.
    """
    if request.method == "GET":
        event = get_active_event()
        attendee = attendee_from_userinfo(request)
        attendee.skill_proficiencies = SkillProficiency.objects.for_event(event).filter(
            attendee=attendee)
        attendee = prepare_attendee_for_detail(attendee, event)
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
        response = super().update(request, pk=pk, **kwargs)
        self._invalidate_list_cache(request)
        return response

    def partial_update(self, request, pk=None, **kwargs):
        check_user(request, pk)
        response = super().partial_update(request, pk, **kwargs)
        self._invalidate_list_cache(request)
        return response

    @method_decorator(never_cache)
    # @method_decorator(cache_page(60 * 60 * 2))
    def list(self, request):
        return super().list(request)

    def _invalidate_list_cache(self, request):
        """Invalidate the cache for the attendees list endpoint."""
        cache.clear()


class AttendeeRSVPViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = Attendee.objects.all().order_by('-date_joined')
    serializer_class = AttendeeRSVPSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = [
        'first_name', 'last_name', 'communications_platform_username', 'email',
        'checked_in_at', 'participation_class', 'participation_role'
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
        sponsor_handler = get_sponsor_handler(request.data.get("sponsor_handler"))
        guardian_of = get_guardian_of(request.data.get("guardian_of"))

        if application_id := request.data.get("application"):
            application = get_application(application_id)
            if not application:
                return Response(
                    f"No application ID matches the query: \"{application_id}\"",
                    status=status.HTTP_400_BAD_REQUEST
                )

        try:
            attendee = get_or_create_attendee_from_request(request, application)
        except ValidationError as e:
            return Response(
                e.message_dict,
                status=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            return Response(
                str(e),
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            event_rsvp = create_event_rsvp_from_request(request, attendee, application)
        except ValidationError as e:
            return Response(
                e.message_dict,
                status=status.HTTP_400_BAD_REQUEST
            )

        attendee.sponsor_handler = sponsor_handler
        if guardian_of:
            attendee.guardian_of.set(
                [guardian_of_attendee.id for guardian_of_attendee in guardian_of]
            )

        event_rsvp.save()
        handle_keycloak_account_creation(attendee)
        serializer = AttendeeRSVPSerializer(attendee)
        return Response(serializer.data, status=201)


class SkillViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows skills to be viewed or edited.
    """
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.AllowAny]


class LocationViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows locations to be viewed or edited.
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.AllowAny]


class TableViewSet(EventScopedLoggingViewSet):
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
        event = self.get_event()
        table = get_object_or_404(Table.objects.for_event(event), pk=pk)
        try:
            table.team = Team.objects.for_event(event).get(table=table)
        except Team.DoesNotExist:  # pragma: nocover
            table.team = None
        try:
            table.lighthouse = LightHouse.objects.for_event(event).get(table=table)
        except LightHouse.DoesNotExist:
            table.lighthouse = None
        serializer = TableDetailSerializer(table)
        return Response(serializer.data)

    def list(self, request):
        queryset = self.get_queryset()
        serializer = TableSerializer(queryset, many=True)
        return Response(serializer.data)


class TeamViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows teams to be viewed or edited.
    """
    queryset = Team.objects.all()
    permission_classes = [permissions.AllowAny]
    filterset_class = TeamFilter

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
        event = self.get_event()
        team = get_object_or_404(Team.objects.for_event(event), pk=pk)
        try:
            team.project = Project.objects.for_event(event).get(team=team)
        except Project.DoesNotExist:
            team.project = None
        try:
            team.lighthouse = LightHouse.objects.for_event(event).get(table=team.table)
        except (Table.DoesNotExist, LightHouse.DoesNotExist):
            team.lighthouse = None
        serializer = TeamDetailSerializer(team)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        team = self.get_object()
        event = self.get_event()

        project_fields = request.data.get('project')
        if project_fields:
            request.data.pop('project', None)
            try:
                team.project = Project.objects.for_event(event).get(team=team)
            except Project.DoesNotExist:
                team.project = Project(**project_fields, event=event)
            serialized_project = ProjectSerializer(team.project, project_fields, partial=True)
            if serialized_project.is_valid():
                serialized_project.update(team.project, serialized_project.validated_data)
            else:
                return Response(serialized_project.errors, status=status.HTTP_400_BAD_REQUEST)
            team.project.save()

        table_fields = request.data.get('table')
        if table_fields:
            request.data.pop('table', None)
            try:
                table = Table.objects.for_event(event).get(id=table_fields.get('id'))
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
        event = get_active_event()
        queryset = LightHouse.objects.for_event(event).all()
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
        event = get_active_event()
        lighthouse_message = request.data
        lighthouse_message._mutable = True
        lighthouse_query = LightHouse.objects.for_event(event).filter(
            table__number=lighthouse_message["table"])
        if len(lighthouse_query) > 0:
            lighthouse = lighthouse_query[0]
            lighthouse.ip_address = lighthouse_message["ip_address"]
            lighthouse.save()
        else:
            lighthouse = LightHouse.objects.create(
                event=event,
                table=Table.objects.for_event(event).get(number=lighthouse_message["table"]),
                ip_address=lighthouse_message["ip_address"]
            )
        lighthouse_message["mentor_requested"] = lighthouse.mentor_requested
        lighthouse_message["announcement_pending"] = lighthouse.announcement_pending
        return Response(data=lighthouse_message, status=201)


class MentorHelpRequestViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows mentor help requests to be viewed or edited.
    """
    queryset = MentorHelpRequest.objects.all().order_by('created_at')
    permission_classes = [permissions.AllowAny]
    filterset_class = MentorHelpRequestFilter
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
        'GET': [KeycloakRoles.ATTENDEE, KeycloakRoles.MENTOR],
        'POST': [KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ADMIN]
    }

    def get_queryset(self):
        event = get_active_event()
        if not event:
            return self.queryset.none()
        return self.queryset.filter(event_id=event.id)


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

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name='attendee__communications_platform_username',
                description='Discord username of the attendee',
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.PATH,
            )
        ]
    )
    def destroy(self, request, attendee__communications_platform_username=None):
        event = get_active_event()
        attendee = get_object_or_404(Attendee, communications_platform_username=attendee__communications_platform_username)
        team = get_object_or_404(Team.objects.for_event(event), attendees__id=attendee.id)
        table = team.table
        lighthouse = get_object_or_404(LightHouse.objects.for_event(event), table=table.id)
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


class SkillProficiencyViewSet(EventScopedLoggingViewSet):
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


class ProjectViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows projects to be viewed or edited.
    """
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.AllowAny]
    filterset_class = ProjectFilter


class GroupViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupDetailSerializer
    permission_classes = [permissions.AllowAny]


def hardware_count(hardware_type, event):
    hardware_devices = HardwareDevice.objects.for_event(event).filter(
        hardware=hardware_type)
    hardware_requests = HardwareRequest.objects.for_event(event).filter(
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


class HardwareViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows hardware types to be viewed or edited.
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
        queryset = super().get_queryset()
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
            if "tags__contains" in filters:
                for tag in list(filters["tags__contains"]):
                    filters["tags__contains"] = tag
                    queryset = queryset.filter(**filters)
            else:
                queryset = queryset.filter(**filters)
        return queryset

    def _iterate_hardware_count(self, hardware_type, event):
        hardware_devices_available, hardware_devices_checked_out, hardware_devices_total = hardware_count(hardware_type, event)
        hardware_type.available = hardware_devices_available
        hardware_type.checked_out = hardware_devices_checked_out
        hardware_type.total = hardware_devices_total

    def retrieve(self, request, pk=None):
        event = self.get_event()
        hardware_type = get_object_or_404(Hardware.objects.for_event(event), pk=pk)
        self._iterate_hardware_count(hardware_type, event)
        hardware_type.hardware_devices = HardwareDevice.objects.for_event(event).filter(
            hardware=hardware_type)
        serializer = HardwareCountDetailSerializer(hardware_type)
        return Response(serializer.data)

    def list(self, request):
        event = self.get_event()
        hardware_types = self.get_queryset()
        for hardware_type in hardware_types:
            self._iterate_hardware_count(hardware_type, event)
        serializer = HardwareCountSerializer(hardware_types, many=True)
        return Response(status=200, data=serializer.data)

    def get_serializer_class(self):
        if self.action == 'create':
            return HardwareCreateSerializer
        elif self.action in ("update", "partial_update"):
            return HardwareCreateSerializer
        elif self.action == 'list':
            return HardwareCountSerializer
        elif self.action == 'retrieve':
            return HardwareCountDetailSerializer
        return HardwareSerializer


class HardwareDeviceViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows individual hardware devices to be viewed or edited.
    """
    queryset = HardwareDevice.objects.all()
    permission_classes = [permissions.AllowAny]
    filterset_class = HardwareDeviceFilter
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


class HardwareRequestsViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows hardware device requests from participants to be viewed or edited.
    """
    queryset = HardwareRequest.objects.all()
    permission_classes = [permissions.AllowAny]
    filterset_class = HardwareRequestFilter
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

    def _iterate_hardware_count(self, hardware_type, event):
        hardware_devices_available, hardware_devices_checked_out, hardware_devices_total = hardware_count(hardware_type, event)
        hardware_type.available = hardware_devices_available
        hardware_type.checked_out = hardware_devices_checked_out
        hardware_type.total = hardware_devices_total

    def retrieve(self, request, pk=None):
        event = self.get_event()
        hardware_request = get_object_or_404(HardwareRequest.objects.for_event(event), pk=pk)
        self._iterate_hardware_count(hardware_request.hardware, event)
        serializer = HardwareRequestDetailSerializer(hardware_request)
        return Response(serializer.data)

    def update(self, request, pk=None, **kwargs):
        event = self.get_event()
        hardware_request = get_object_or_404(HardwareRequest.objects.for_event(event), pk=pk)
        role = check_user(request, hardware_request.requester.id)
        if role != "admin":
            if set(request.data.keys()) != set(["reason"]):
                raise PermissionDenied("Attendee cannot modify anything other than the reason of a request")
        return super().update(request, pk=pk, **kwargs)

    def delete(self, request, pk=None, **kwargs):
        event = self.get_event()
        hardware_request = get_object_or_404(HardwareRequest.objects.for_event(event), pk=pk)
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

    def get_queryset(self):
        event = get_active_event()
        if not event:
            return self.queryset.none()
        return self.queryset.filter(event_id=event.id)


class ApplicationQuestionViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows application questions to be viewed or edited.
    Frontend uses this to load dynamic questions for the active event.
    """
    queryset = ApplicationQuestion.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = ApplicationQuestionSerializer
    filterset_fields = ['question_key', 'parent_question']
    keycloak_roles = {
        'POST': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
    }

    def list(self, request):
        """Return all questions for the active event, ordered by order field"""
        event = self.get_event()
        questions = ApplicationQuestion.objects.for_event(event).prefetch_related(
            'choices'
        ).order_by('order')
        serializer = ApplicationQuestionSerializer(questions, many=True)
        return Response(serializer.data)


class ApplicationViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows applications to be viewed or edited.
    """
    queryset = Application.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = ApplicationSerializer
    filterset_fields = [
        'participation_capacity', 'participation_role', 'email', 'participation_class'
    ]
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
    }

    def get_queryset(self):
        """Optimize queryset with prefetch for actions that need question responses"""
        queryset = super().get_queryset()

        if self.action in ['list', 'retrieve']:
            queryset = queryset.prefetch_related('question_responses__selected_choices')

        return queryset

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return ApplicationDetailSerializer
        return ApplicationSerializer

    def retrieve(self, request, pk=None):
        event = self.get_event()
        application = get_object_or_404(
            Application.objects.for_event(event),
            pk=pk
        )
        serializer = ApplicationDetailSerializer(application)
        return Response(serializer.data)

    def create(self, request, *args, **kwargs):
        """
        Create application and handle dynamic question responses.
        """

        event = get_active_event()
        if not event:
            return Response(
                {"error": "No active event found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        dynamic_responses = {}
        question_keys = ApplicationQuestion.objects.for_event(event).values_list(
            'question_key', flat=True
        )

        for key in list(request.data.keys()):
            if key in question_keys:
                dynamic_responses[key] = request.data.pop(key)

        request.data['event'] = event.id

        response = super().create(request, *args, **kwargs)

        if response.status_code == 201:
            application = Application.objects.for_event(
                event
            ).get(id=response.data['id'])

            questions = ApplicationQuestion.objects.for_event(event)
            questions_list = list(questions)

            for question in questions_list:
                if question.question_key in dynamic_responses:
                    value = dynamic_responses[question.question_key]

                    if (value is None or value == '' or
                            (isinstance(value, list) and len(value) == 0)):
                        continue

                    app_response = ApplicationResponse.objects.create(
                        application=application,
                        question=question,
                        question_text_snapshot=question.question_text
                    )

                    if question.question_type in ['S', 'M']:
                        choices_dict = {
                            c.choice_key: c.choice_text
                            for c in question.choices.all()
                        }
                        app_response.choices_snapshot = choices_dict

                        selected_keys = value if isinstance(value, list) else [value]
                        selected_choices = question.choices.filter(
                            choice_key__in=selected_keys
                        )
                        app_response.save()
                        app_response.selected_choices.set(selected_choices)
                        app_response.selected_keys_snapshot = selected_keys
                        app_response.save()

                    elif question.question_type in ['T', 'L']:
                        app_response.text_response = value
                        app_response.text_response_snapshot = value
                        app_response.save()

        return response


class EventViewSet(LoggingMixin, viewsets.ModelViewSet):
    """
    API endpoint for editing and viewing Events.
    """
    queryset = Event.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = EventSerializer
    filterset_fields = ['is_active']
    http_method_names = ['get', 'patch', 'head', 'options']
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ADMIN],
    }


@extend_schema(
    methods=['POST'],
    request=None,
    responses={200: EventSerializer},
    description="Activate an event by its ID"
)
@api_view(['POST'])
@keycloak_roles([KeycloakRoles.ADMIN])
def activate_event(request, event_id):
    if not request.method == 'POST':
        return Response(status=404)

    event = get_object_or_404(Event, pk=event_id)
    event.activate()
    serializer = EventSerializer(event)
    return Response(serializer.data)


class EventRsvpViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows event RSVPs to be viewed or edited.
    """
    queryset = EventRsvp.objects.for_event(get_active_event())
    permission_classes = [permissions.AllowAny]
    serializer_class = EventRsvpSerializer
    filterset_fields = ['event', 'attendee', 'participation_class']
    keycloak_roles = {
        'GET': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'DELETE': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
        'PATCH': [KeycloakRoles.ORGANIZER, KeycloakRoles.ADMIN],
    }

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return EventRsvpDetailSerializer
        return EventRsvpSerializer

    def list(self, request):
        event = self.get_event()
        event_rsvps = EventRsvp.objects.for_event(event).select_related(
            'application',
            'attendee'
        )

        filters = {}
        for filterset_field in self.filterset_fields:
            if request.query_params.get(filterset_field):
                filterset_value = request.query_params.get(filterset_field)
                filters[filterset_field] = filterset_value

        if filters:
            event_rsvps = event_rsvps.filter(**filters)

        serializer = EventRsvpSerializer(event_rsvps, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        event = self.get_event()
        event_rsvp = get_object_or_404(EventRsvp.objects.for_event(event), pk=pk)
        serializer = EventRsvpSerializer(event_rsvp)
        return Response(serializer.data)


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


class WorkshopViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows workshops to be viewed or edited.
    """
    queryset = Workshop.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkshopSerializer
    filterset_class = WorkshopFilter


class WorkshopAttendeeViewSet(EventScopedLoggingViewSet):
    """
    API endpoint that allows workshop attendees to be viewed or edited.
    """
    queryset = WorkshopAttendee.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = WorkshopAttendeeSerializer
    filterset_class = WorkshopAttendeeFilter


def preference_auth(fn):
    def wrapper(self, request, pk=None, **kwargs):
        attendee_preference = get_object_or_404(AttendeePreference, pk=pk)
        check_user(request, attendee_preference.preferer.id)
        return fn(self, request, pk=pk, **kwargs)
    return wrapper


class AttendeePreferenceViewSet(EventScopedLoggingViewSet):
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
        queryset = self.get_queryset()
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


class DestinyTeamViewSet(EventScopedLoggingViewSet):
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


class DestinyTeamAttendeeVibeViewSet(EventScopedLoggingViewSet):
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
        queryset = self.get_queryset()
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