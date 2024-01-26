import copy
import os
import random
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django.http.response import JsonResponse
from django.test import override_settings
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient, APITestCase

from infrastructure import factories, models, serializers
from infrastructure.management.commands import setup_test_data
from infrastructure.views import KeycloakRoles


class KeycloakTestMiddleware(object):
    def __init__(self, get_response):
        # Django response
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        request.roles = [
            KeycloakRoles.ATTENDEE, KeycloakRoles.MENTOR, KeycloakRoles.JUDGE, KeycloakRoles.ADMIN, KeycloakRoles.ORGANIZER, KeycloakRoles.VOLUNTEER
        ]
        # There's condictions for these view_func.cls:
        # 1) @api_view -> view_func.cls is WrappedAPIView (validates in 'keycloak_roles' in decorators.py) -> True
        # 2) When it is a APIView, ViewSet or ModelViewSet with 'keycloak_roles' attribute -> False
        try:
            is_api_view = True if str(view_func.cls.__qualname__) == "WrappedAPIView" else False
        except AttributeError:
            is_api_view = False

        # Read if View has attribute 'keycloak_roles' (for APIView, ViewSet or ModelViewSet)
        # Whether View hasn't this attribute, it means all request method routes will be permitted.        
        try:
            view_roles = view_func.cls.keycloak_roles if not is_api_view else []
        except AttributeError as e:
            return None
        if hasattr(view_func, "view_class") and view_func.view_class.__name__ == "me":
            request.userinfo = {"sub": request.headers.get("Authorization")}
            view_roles = ["GET", "PATCH"]
            return
        if request.method not in view_roles:
            uri = f"{request.path.lstrip('/').split('/')[0]}/"
            if uri not in settings.KEYCLOAK_EXEMPT_URIS:
                return JsonResponse({'detail': PermissionDenied.default_detail}, status=PermissionDenied.status_code)


middleware = settings.MIDDLEWARE[:]
middleware.insert(
    middleware.index("django_keycloak_auth.middleware.KeycloakMiddleware") + 1,
    "infrastructure.tests.KeycloakTestMiddleware",
)
middleware.remove("django_keycloak_auth.middleware.KeycloakMiddleware")
keycloak_test = override_settings(
    MIDDLEWARE=middleware,
    KEYCLOAK_EXEMPT_URIS=settings.KEYCLOAK_EXEMPT_URIS + [".*"],
)


@keycloak_test
class MeTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.table = factories.TableFactory(location=models.Location.objects.create(room=models.Location.Room.ATLANTIS))
        factories.GroupFactory()
        models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        self.mock_attendee_model = factories.AttendeeFactory(
            application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
        )
        self.mock_attendee = serializers.AttendeeSerializer(self.mock_attendee_model).data
        mock_attendees = [
            factories.AttendeeFactory(
                application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
            ) for _ in range(setup_test_data.TEAM_SIZE - 1)]
        self.mock_attendees = [
            serializers.AttendeeSerializer(mock_attendee).data
            for mock_attendee in mock_attendees
        ]
        team = factories.TeamFactory(
            attendees=mock_attendees + [self.mock_attendee_model], table=self.table)
        self.mock_team = serializers.TeamSerializer(team).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_me(self):
        response = self.client.get('/me/', headers={
            "Authorization": self.mock_attendee_model.authentication_id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.mock_attendee["id"])

    def test_get_me_no_team(self):
        models.Team.objects.all().delete()
        response = self.client.get('/me/', headers={
            "Authorization": self.mock_attendee_model.authentication_id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.mock_attendee["id"])

    def test_get_me_no_profile_image(self):
        models.Team.objects.all().delete()
        response = self.client.get('/me/', headers={
            "Authorization": self.mock_attendee_model.authentication_id
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], self.mock_attendee["id"])

    def test_partial_update_me(self):
        new_profile_image = factories.UploadedFileFactory()
        new_first_name = f"{self.mock_attendee['first_name']}partially_updated"
        new_last_name = f"{self.mock_attendee['last_name']}partially_updated"
        intended_tracks = [models.Track.COMMUNITY_HACKS.value, models.Track.FUTURE_CONSTRUCTORS.value]
        prefers_destiny_hardware = [models.DestinyHardware.HARDWARE_HACK.value]
        response = self.client.patch(
            f"/me/", {
                "first_name": new_first_name,
                "last_name": new_last_name,
                "profile_image": new_profile_image.id,
                "intended_tracks": intended_tracks,
                "prefers_destiny_hardware": prefers_destiny_hardware,
                "intended_hardware_hack": True,
            }, headers={
                "Authorization": self.mock_attendee_model.authentication_id
            }
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_first_name, response.json()["first_name"])
        self.assertEqual(new_last_name, response.json()["last_name"])
        self.assertEqual(str(new_profile_image.id), response.json()["profile_image"])
        self.assertEqual(set(intended_tracks), set(response.json()["intended_tracks"]))
        self.assertEqual(set(prefers_destiny_hardware), set(response.json()["prefers_destiny_hardware"]))
        self.assertTrue(response.json()["intended_hardware_hack"])
        self.assertNotEqual(self.mock_attendee["first_name"], response.json()["first_name"])
        self.assertNotEqual(self.mock_attendee["last_name"], response.json()["last_name"])
        self.assertNotEqual(self.mock_attendee["profile_image"], response.json()["profile_image"])

    def test_partial_update_me_profile_photo_not_exists(self):
        response = self.client.patch(
            f"/me/", {
                "profile_image": str(uuid.uuid4()),
            }, headers={
                "Authorization": self.mock_attendee_model.authentication_id
            }
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["profile_image"][0].code, "does_not_exist")


@keycloak_test
class AttendeeTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        factories.GroupFactory()
        mock_attendee = factories.AttendeeFactory(
            application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
        )
        self.mock_attendee_model = mock_attendee
        self.mock_attendee = serializers.AttendeeSerializer(mock_attendee).data
        self.mock_attendee_detail = serializers.AttendeeRSVPSerializer(mock_attendee).data
        self.mock_attendee_create = serializers.AttendeeRSVPCreateSerializer(mock_attendee).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_attendees(self):
        response = self.client.get('/attendees/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def get_attendee_alternate_choice(self, choice, choices):
        alternate_choice = choice
        while alternate_choice == choice:
            alternate_choice = random.choice(choices)
        return alternate_choice

    def get_attendees_with_filter(self, filter, search_term) -> str:
        return f"/attendees/?{filter}={search_term}"

    def test_get_attendees_filters(self):
        response = self.client.get(self.get_attendees_with_filter(
            "first_name", self.mock_attendee["first_name"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_attendees_with_filter(
            "first_name", f"fake{self.mock_attendee['first_name']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_attendees_with_filter(
            "last_name", self.mock_attendee["last_name"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_attendees_with_filter(
            "last_name", f"fake{self.mock_attendee['last_name']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_attendees_with_filter(
            "email", self.mock_attendee["email"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_attendees_with_filter(
            "email", f"fake{self.mock_attendee['email']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_attendees_with_filter(
            "communications_platform_username", self.mock_attendee["communications_platform_username"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_attendees_with_filter(
            "communications_platform_username", f"fake{self.mock_attendee['communications_platform_username']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_attendees_with_filter(
            "checked_in_at", str(datetime.now())))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_get_attendee(self):
        response = self.client.get(f"/attendees/{self.mock_attendee['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_attendee["id"], response.json()["id"])

    def test_get_attendee_404(self):
        response = self.client.get(f"/attendees/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_partial_update_attendee(self):
        self.assertIsNotNone(self.mock_attendee_model.authentication_id)
        original_authentication_id = self.mock_attendee_model.authentication_id
        mock_attendee = copy.deepcopy(self.mock_attendee_detail)
        new_last_name = f"{self.mock_attendee['last_name']}partially_updated"
        new_authentication_id = str(uuid.uuid4())
        response = self.client.patch(
            f"/attendees/{mock_attendee['id']}/", {"last_name": new_last_name, "authentication_id": new_authentication_id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_last_name, response.json()["last_name"])
        self.assertNotEqual(self.mock_attendee["last_name"], response.json()["last_name"])
        self.assertNotEqual(original_authentication_id, models.Attendee.objects.get(id=mock_attendee['id']).authentication_id)

@keycloak_test
class TeamTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        self.table = factories.TableFactory()
        group = factories.GroupFactory()
        mock_attendees = [
            factories.AttendeeFactory(
                application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
            ) for _ in range(
                setup_test_data.TEAM_SIZE + 1)]
        [mock_attendee.groups.set([group]) for mock_attendee in mock_attendees]
        self.mock_attendees = [
            serializers.AttendeeSerializer(mock_attendee).data
            for mock_attendee in mock_attendees
        ]
        team = factories.TeamFactory(
            attendees=mock_attendees[0:setup_test_data.TEAM_SIZE], table=self.table)
        self.mock_team = serializers.TeamSerializer(team).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_teams(self):
        response = self.client.get('/teams/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def get_teams_with_filter(self, filter, search_term) -> str:
        return f"/teams/?{filter}={search_term}"

    def test_get_teams_filters(self):
        response = self.client.get(self.get_teams_with_filter(
            "name", self.mock_team["name"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_teams_with_filter(
            "name", f"fake{self.mock_team['name']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_teams_with_filter(
            "attendees", self.mock_team["attendees"][0]["id"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        fake_attendee = str(uuid.uuid4())
        response = self.client.get(self.get_teams_with_filter(
            "attendees", fake_attendee))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["attendees"][0].code, "invalid_choice")
        response = self.client.get(self.get_teams_with_filter(
            "table", self.mock_team["table"]["id"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_teams_with_filter(
            "table", str(uuid.uuid4())))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["table"][0].code, "invalid_choice")
        response = self.client.get(self.get_teams_with_filter(
            "table__number", self.table.number))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_teams_with_filter(
            "table__number", -1))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_get_team(self):
        response = self.client.get(f"/teams/{self.mock_team['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_team["id"], response.json()["id"])

    def test_get_team_404(self):
        response = self.client.get(f"/teams/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_get_team_no_project(self):
        team = models.Team.objects.get(pk=self.mock_team["id"])
        team.project = None
        team.save()
        response = self.client.get(f"/teams/{self.mock_team['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_team["id"], response.json()["id"])

    def test_create_team(self):
        table = factories.TableFactory()
        mock_team = serializers.TeamCreateSerializer(
            models.Team.objects.get(pk=self.mock_team["id"])).data
        mock_team["table"] = table.id
        mock_team["name"] = f"{self.mock_team['name']}updated"
        response = self.client.post('/teams/', mock_team)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_team["name"], response.json()["name"])
        self.assertNotEqual(self.mock_team["id"], response.json()["id"])

    def test_partial_update_team(self):
        mock_team = serializers.TeamCreateSerializer(
            models.Team.objects.get(pk=self.mock_team["id"])).data
        new_name = f"{self.mock_team['name']}updated"
        mock_team = copy.deepcopy(self.mock_team)
        new_name = f"{self.mock_team['name']}partially_updated"
        mock_team["name"] = new_name
        response = self.client.patch(f"/teams/{mock_team['id']}/", {"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.json()["name"])
        self.assertNotEqual(self.mock_team["name"], response.json()["name"])

@keycloak_test
class ProjectTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        self.table = factories.TableFactory()
        group = factories.GroupFactory()
        mock_attendees = [
            factories.AttendeeFactory(
                application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
            ) for _ in range(
                setup_test_data.TEAM_SIZE + 1)]
        [mock_attendee.groups.set([group]) for mock_attendee in mock_attendees]
        self.mock_attendees = [
            serializers.AttendeeSerializer(mock_attendee).data
            for mock_attendee in mock_attendees
        ]
        team = factories.TeamFactory(
            attendees=mock_attendees[0:setup_test_data.TEAM_SIZE], table=self.table)
        project = factories.ProjectFactory(team=team)
        self.mock_project = serializers.ProjectSerializer(project).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_projects(self):
        response = self.client.get('/projects/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_get_project(self):
        response = self.client.get(f"/projects/{self.mock_project['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_project["id"], response.json()["id"])

    def test_get_project_404(self):
        response = self.client.get(f"/projects/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_project(self):
        models.Project.objects.all().delete()
        mock_project = copy.deepcopy(self.mock_project)
        mock_project["name"] = f"{self.mock_project['name']}updated"
        response = self.client.post('/projects/', mock_project)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_project["name"], response.json()["name"])
        self.assertNotEqual(self.mock_project["id"], response.json()["id"])

    def test_create_duplicate_team_project(self):
        mock_project = copy.deepcopy(self.mock_project)
        mock_project["name"] = f"{self.mock_project['name']}updated"
        response = self.client.post('/projects/', mock_project)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["team"][0].code, "unique")

    def test_partial_update_project(self):
        mock_attendee = copy.deepcopy(self.mock_project)
        new_name = f"{self.mock_project['name']}partially_updated"
        mock_attendee["name"] = new_name
        response = self.client.patch(
            f"/projects/{mock_attendee['id']}/", {"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.json()["name"])
        self.assertNotEqual(self.mock_project["name"], response.json()["name"])

@keycloak_test
class HardwareTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.hardware_type = factories.HardwareFactory()
        self.mock_hardware_type = serializers.HardwareSerializer(self.hardware_type).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_hardwares(self):
        response = self.client.get('/hardware/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def get_application_alternate_choice(self, choice, choices):
        alternate_choice = choice
        while alternate_choice == choice:
            alternate_choice = random.choice(choices)
        return alternate_choice

    def get_application_alternate_choices(self, choices_a, choices_b):
        alternate_choice = choices_a[0]
        while alternate_choice in choices_a:
            alternate_choice = random.choice(choices_b)
        return alternate_choice

    def get_hardwares_with_filter(self, filter, search_term) -> str:
        return f"/hardware/?{filter}={search_term}"

    def test_get_hardwares_filters(self):
        response = self.client.get(self.get_hardwares_with_filter(
            "relates_to_destiny_hardware", self.mock_hardware_type["relates_to_destiny_hardware"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_hardwares_with_filter(
            "tags", self.hardware_type.tags[0]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_hardwares_with_filter(
            "tags", ",".join(self.hardware_type.tags)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        choices = [x[0] for x in models.HardwareTags.choices]
        response = self.client.get(self.get_hardwares_with_filter(
            "tags", self.get_application_alternate_choices(
                self.hardware_type.tags, choices)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_get_hardware(self):
        response = self.client.get(f"/hardware/{self.mock_hardware_type['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_hardware_type["id"], response.json()["id"])

    def test_get_hardware_404(self):
        response = self.client.get(f"/hardware/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_hardware(self):
        models.Hardware.objects.all().delete()
        mock_hardware_type = copy.deepcopy(self.mock_hardware_type)
        del mock_hardware_type["id"]
        del mock_hardware_type["created_at"]
        del mock_hardware_type["updated_at"]
        mock_hardware_type["image"] = mock_hardware_type["image"]["id"]
        serializer = serializers.HardwareCreateSerializer(data=mock_hardware_type)
        serializer.is_valid(raise_exception=True)
        response = self.client.post('/hardware/', serializer.data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_hardware_type["name"], response.json()["name"])
        self.assertNotEqual(self.mock_hardware_type["id"], response.json()["id"])

    def test_partial_update_hardware(self):
        mock_hardware_type = copy.deepcopy(self.mock_hardware_type)
        new_name = f"{self.mock_hardware_type['name']}partially_updated"
        mock_hardware_type["name"] = new_name
        response = self.client.patch(
            f"/hardware/{mock_hardware_type['id']}/", {"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.json()["name"])
        self.assertNotEqual(self.mock_hardware_type["name"], response.json()["name"])

@keycloak_test
class HardwareDeviceTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        mock_attendee = factories.AttendeeFactory(
            application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
        )
        self.mock_attendee = serializers.AttendeeSerializer(mock_attendee).data
        self.mock_request = serializers.HardwareRequestSerializer(
            factories.HardwareRequestFactory(requester=mock_attendee)).data
        hardware_type = factories.HardwareFactory()
        self.mock_hardware_type = serializers.HardwareSerializer(
            hardware_type).data
        hardware_device = factories.HardwareDeviceFactory(
            hardware=hardware_type, checked_out_to=None)
        self.mock_hardware_device = serializers.HardwareDeviceSerializer(
            hardware_device).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_hardware_devices(self):
        response = self.client.get('/hardwaredevices/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_get_hardware_device(self):
        response = self.client.get(
            f"/hardwaredevices/{self.mock_hardware_device['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_hardware_device["id"], response.json()["id"])

    def test_get_hardware_device_404(self):
        response = self.client.get(f"/hardwaredevices/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_hardware_device(self):
        models.HardwareDevice.objects.all().delete()
        mock_hardware_device = copy.deepcopy(self.mock_hardware_device)
        response = self.client.post('/hardwaredevices/', mock_hardware_device)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_hardware_device["serial"], response.json()["serial"])
        self.assertNotEqual(self.mock_hardware_device["id"], response.json()["id"])

    def test_partial_update_hardware_device(self):
        mock_hardware_device = copy.deepcopy(self.mock_hardware_device)
        new_serial = f"{self.mock_hardware_type['name']}partially_updated"
        mock_hardware_device["serial"] = new_serial
        response = self.client.patch(
            f"/hardwaredevices/{mock_hardware_device['id']}/", {"serial": new_serial})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_serial, response.json()["serial"])
        self.assertNotEqual(
            self.mock_hardware_device["serial"], response.json()["serial"])

    def test_partial_update_hardware_device_check_out(self):
        mock_hardware_device = copy.deepcopy(self.mock_hardware_device)
        mock_hardware_device["checked_out_to"] = self.mock_request["id"]
        response = self.client.patch(
            f"/hardwaredevices/{mock_hardware_device['id']}/",
            {"checked_out_to": mock_hardware_device["checked_out_to"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_hardware_device["checked_out_to"],
            str(response.json()["checked_out_to"])
        )

@keycloak_test
class HardwareRequestTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        factories.GroupFactory()
        self.mock_attendee = factories.AttendeeFactory(application=None)
        self.mock_attendees = [
            factories.AttendeeFactory(
                application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
            ) for _ in range(setup_test_data.TEAM_SIZE)
        ]
        self.mock_attendees.append(self.mock_attendee)
        models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        self.mock_table = factories.TableFactory()
        self.mock_team = factories.TeamFactory(attendees=self.mock_attendees)
        self.mock_hardware = factories.HardwareFactory()
        self.mock_hardware_devices = [
            factories.HardwareDeviceFactory(
                hardware=self.mock_hardware, checked_out_to=None
            ) for _ in range(setup_test_data.NUMBER_OF_HARDWARE_DEVICES)
        ]
        self.mock_hardware_request = serializers.HardwareRequestCreateSerializer(factories.HardwareRequestFactory(
            hardware=self.mock_hardware, hardware_device=self.mock_hardware_devices[0],
            requester=self.mock_attendee, team=self.mock_team
        )).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_hardware_requests(self):
        response = self.client.get('/hardwarerequests/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_get_hardware_request(self):
        response = self.client.get(
            f"/hardwarerequests/{self.mock_hardware_request['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_hardware_request["id"], response.json()["id"])

    def test_get_hardware_request_404(self):
        response = self.client.get(f"/hardwarerequests/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_hardware_request(self):
        models.HardwareRequest.objects.all().delete()
        mock_hardware_request = copy.deepcopy(self.mock_hardware_request)
        del mock_hardware_request["id"]
        response = self.client.post('/hardwarerequests/', mock_hardware_request)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_hardware_request["reason"], response.json()["reason"])
        self.assertEqual(self.mock_hardware_request["requester"], response.json()["requester"])
        self.assertEqual(str(self.mock_hardware_request["team"]), response.json()["team"])
        self.assertEqual(self.mock_hardware_request["status"], response.json()["status"])
        self.assertNotEqual(self.mock_hardware_request["id"], response.json()["id"])

    def test_partial_update_hardware_request(self):
        mock_hardware_request = copy.deepcopy(self.mock_hardware_request)
        new_reason = f"{self.mock_hardware_request['reason']}partially_updated"
        mock_hardware_request["reason"] = new_reason
        response = self.client.patch(
            f"/hardwarerequests/{mock_hardware_request['id']}/", {"reason": new_reason})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_reason, response.json()["reason"])
        self.assertNotEqual(self.mock_hardware_request["reason"], response.json()["reason"])

@keycloak_test
class SkillTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        skill = factories.SkillFactory()
        self.mock_skill = serializers.SkillSerializer(skill).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_skills(self):
        response = self.client.get('/skills/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_get_skill(self):
        response = self.client.get(f"/skills/{self.mock_skill['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_skill["id"], response.json()["id"])

    def test_get_skill_404(self):
        response = self.client.get(f"/skills/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_skill(self):
        models.Skill.objects.all().delete()
        mock_skill = copy.deepcopy(self.mock_skill)
        response = self.client.post('/skills/', mock_skill)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_skill["name"], response.json()["name"])
        self.assertNotEqual(self.mock_skill["id"], response.json()["id"])

    def test_partial_update_skill(self):
        mock_skill = copy.deepcopy(self.mock_skill)
        new_name = f"{self.mock_skill['name']}partially_updated"
        mock_skill["name"] = new_name
        response = self.client.patch(
            f"/skills/{mock_skill['id']}/", {"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.json()["name"])
        self.assertNotEqual(self.mock_skill["name"], response.json()["name"])

@keycloak_test
class SkillProficiencyTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        factories.GroupFactory()
        mock_attendee = factories.AttendeeFactory(
            application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
        )
        self.mock_attendee = serializers.AttendeeSerializer(mock_attendee).data
        skill = factories.SkillFactory()
        skill_proficiency = factories.SkillProficiencyFactory(
            attendee=mock_attendee, skill=skill)
        self.mock_skill_proficiency = serializers.SkillProficiencySerializer(
            skill_proficiency).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_skill_proficiencies(self):
        response = self.client.get('/skillproficiencies/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_get_skill_proficiency(self):
        response = self.client.get(
            f"/skillproficiencies/{self.mock_skill_proficiency['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_skill_proficiency["id"], response.json()["id"])

    def test_get_skill_proficiency_404(self):
        response = self.client.get(f"/skillproficiencies/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_skill_proficiency(self):
        mock_skill_proficiency = serializers.SkillProficiencyCreateSerializer(
            models.SkillProficiency.objects.get(pk=self.mock_skill_proficiency["id"])
        ).data
        models.SkillProficiency.objects.all().delete()
        response = self.client.post('/skillproficiencies/', mock_skill_proficiency)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            str(mock_skill_proficiency["skill"]), response.json()["skill"])
        self.assertNotEqual(
            self.mock_skill_proficiency["id"], response.json()["id"])

    def test_create_non_unique_skill_proficiency(self):
        mock_skill_proficiency = serializers.SkillProficiencyCreateSerializer(
            models.SkillProficiency.objects.get(pk=self.mock_skill_proficiency["id"])
        ).data
        response = self.client.post('/skillproficiencies/', mock_skill_proficiency)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["non_field_errors"][0].code, "unique")

    def test_partial_update_skill_proficiency(self):
        mock_skill = factories.SkillFactory()
        response = self.client.patch(
            f"/skillproficiencies/{self.mock_skill_proficiency['id']}/",
            {"skill": mock_skill.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(str(mock_skill.id), response.json()["skill"])
        self.assertNotEqual(
            self.mock_skill_proficiency["skill"], response.json()["skill"])
        
@keycloak_test
class TableTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        location = models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        self.mock_location = serializers.LocationSerializer(location).data
        table = factories.TableFactory(location=location)
        self.mock_table = serializers.TableSerializer(table).data
        group = factories.GroupFactory()
        mock_attendees = [
            factories.AttendeeFactory(
                application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
            ) for _ in range(
                setup_test_data.TEAM_SIZE + 1)]
        [mock_attendee.groups.set([group]) for mock_attendee in mock_attendees]
        self.mock_attendees = [
            serializers.AttendeeSerializer(mock_attendee).data
            for mock_attendee in mock_attendees
        ]
        team = factories.TeamFactory(
            attendees=mock_attendees[0:setup_test_data.TEAM_SIZE], table=table)
        self.mock_team = serializers.TeamSerializer(team).data
        lighthouse = factories.LightHouseFactory()
        self.lighthouse = serializers.serialize_lighthouse(lighthouse).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_tables(self):
        response = self.client.get('/tables/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_get_table(self):
        response = self.client.get(f"/tables/{self.mock_table['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_table["id"], response.json()["id"])

    def test_get_table_404(self):
        response = self.client.get(f"/tables/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_get_table_404(self):
        response = self.client.get(f"/tables/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_table(self):
        mock_table = serializers.TableCreateSerializer(factories.TableFactory()).data
        mock_table["number"] += 1
        mock_table["location"] = self.mock_location["id"]
        response = self.client.post('/tables/', mock_table)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_table["number"], response.json()["number"])
        self.assertNotEqual(self.mock_table["id"], response.json()["id"])

    def test_partial_update_table(self):
        mock_table = serializers.TableCreateSerializer(
            models.Table.objects.get(pk=self.mock_table["id"])).data
        new_number = self.mock_table["number"] + 1
        mock_table["number"] = new_number
        response = self.client.patch(
            f"/tables/{mock_table['id']}/",{"number": new_number})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_number, response.json()["number"])
        self.assertNotEqual(self.mock_table["number"], response.json()["number"])

@keycloak_test
class ApplicationTests(APITestCase):
    def setUp(self):
        # Mocking fake phone numbers does not always succeed
        self.client = APIClient()
        mock_resume = factories.UploadedFileFactory()
        mock_application = factories.ApplicationFactory(resume=mock_resume)
        self.mock_application = serializers.ApplicationSerializer(mock_application).data


    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_applications(self):
        response = self.client.get('/applications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def get_application_alternate_choice(self, choice, choices):
        alternate_choice = choice
        while alternate_choice == choice:
            alternate_choice = random.choice(choices)
        return alternate_choice

    def get_applications_with_filter(self, filter, search_term) -> str:
        return f"/applications/?{filter}={search_term}"

    def test_get_applications_filters(self):
        choices = [x[0] for x in models.ParticipationCapacity.choices]
        response = self.client.get(self.get_applications_with_filter(
            "participation_capacity", self.mock_application["participation_capacity"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_applications_with_filter(
            "participation_capacity", self.get_application_alternate_choice(
                self.mock_application['participation_capacity'], choices)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        choices = [x[0] for x in models.ParticipationRole.choices]
        response = self.client.get(self.get_applications_with_filter(
            "participation_role", self.mock_application["participation_role"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_applications_with_filter(
            "participation_role", self.get_application_alternate_choice(
                self.mock_application['participation_role'], choices)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_applications_with_filter(
            "email", self.mock_application["email"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_applications_with_filter(
            "email", f"fake{self.mock_application['email']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_get_application(self):
        response = self.client.get(f"/applications/{self.mock_application['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_application["id"], response.json()["id"])

    def test_get_application_404(self):
        response = self.client.get(f"/applications/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_application(self):
        models.Application.objects.all().delete()
        mock_resume = factories.UploadedFileFactory()
        mock_application = copy.deepcopy(self.mock_application)
        del mock_application["id"]
        mock_application["resume"] = mock_resume.id
        response = self.client.post('/applications/', mock_application)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_application["last_name"], response.json()["last_name"])
        self.assertNotEqual(self.mock_application["id"], response.json()["id"])

    def test_create_duplicate_application_email_duplicate_forms(self):
        mock_resume = factories.UploadedFileFactory()
        mock_application = copy.deepcopy(self.mock_application)
        mock_application["email"] = f"{self.mock_application['email']}"
        mock_application["resume"] = mock_resume.id
        response = self.client.post('/applications/', mock_application)
        self.assertEqual(response.status_code, 400)

    def test_create_duplicate_application_email_unique_forms(self):
        mock_resume = factories.UploadedFileFactory()
        mock_application = copy.deepcopy(self.mock_application)
        mock_application["email"] = f"{self.mock_application['email']}updated"
        mock_application["resume"] = mock_resume.id
        response = self.client.post('/applications/', mock_application)
        self.assertEqual(response.status_code, 201)

    def test_partial_update_application(self):
        mock_application = copy.deepcopy(self.mock_application)
        new_last_name = f"{self.mock_application['last_name']}partially_updated"
        mock_application["last_name"] = new_last_name
        response = self.client.patch(
            f"/applications/{mock_application['id']}/", {"last_name": new_last_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_last_name, response.json()["last_name"])
        self.assertNotEqual(self.mock_application["last_name"], response.json()["last_name"])


@keycloak_test
class UploadedFileTests(APITestCase):
    def setUp(self):
        self.filename = "test_file.pdf"
        self.client = APIClient()
        self.file_path = f"{settings.MEDIA_ROOT}/{self.filename}"
        with open(self.file_path, "wb") as f:
            self.file_data = b"Test data"
            f.write(self.file_data)

    def tearDown(self):
        os.remove(self.file_path)
        setup_test_data.delete_all()

    def test_create_uploaded_file(self):
        with open(self.file_path, "rb") as f:
            response = self.client.post(
                "/uploaded_files/",
                files={self.filename, self.file_path},
                data=encode_multipart(
                    data=dict(file=f, name=self.filename), boundary=BOUNDARY
                ), content_type=MULTIPART_CONTENT
            )
        self.assertEqual(response.status_code, 201)
        with open(f"{settings.MEDIA_ROOT}/{response.json()['id']}/{self.filename}", "rb") as f:
            self.assertEqual(self.file_data, f.read())

    def test_get_uploaded_file(self):
        uploaded_file = serializers.FileUploadSerializer(
            factories.UploadedFileFactory()).data
        response = self.client.get(f"/uploaded_files/{uploaded_file['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(uploaded_file["id"], response.json()["id"])

    def test_delete_uploaded_file(self):
        uploaded_file = serializers.FileUploadSerializer(
            factories.UploadedFileFactory()).data
        response = self.client.delete(f"/uploaded_files/{uploaded_file['id']}/")
        self.assertEqual(response.status_code, 204)
        self.assertNotIn(uploaded_file["id"], os.listdir(settings.MEDIA_ROOT))


@keycloak_test
class WorkshopTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        mock_location = models.Location.objects.create(room=models.Location.Room.MAIN_HALL)
        group = factories.GroupFactory()
        mock_attendees = [
            factories.AttendeeFactory(
                application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
            ) for _ in range(
                setup_test_data.TEAM_SIZE + 1)]
        [mock_attendee.groups.set([group]) for mock_attendee in mock_attendees]
        self.mock_attendees = [
            serializers.AttendeeSerializer(mock_attendee).data
            for mock_attendee in mock_attendees
        ]
        mock_skills = []
        for _ in range(setup_test_data.NUMBER_OF_SKILLS):
            skill = factories.SkillFactory()
            skill.name = skill.name.lower().replace(
                " ", "_").replace("-", "_").replace(",", "")
            skill.save()
            mock_skills.append(skill)
        self.mock_skills = [
            serializers.SkillSerializer(mock_skill).data for mock_skill in mock_skills
        ]
        mock_hardware_types = []
        for _ in range(setup_test_data.NUMBER_OF_HARDWARE_TYPES):
            hardware_type = factories.HardwareFactory()
            mock_hardware_types.append(hardware_type)
        self.mock_hardware_types = [
            serializers.SkillSerializer(mock_hardware_type).data
            for mock_hardware_type in mock_hardware_types
        ]
        mock_workshop = factories.WorkshopFactory(
            location=mock_location,
            skills=random.sample(mock_skills, random.randint(1, 10)),
            hardware=random.sample(mock_hardware_types, random.randint(1, 10)),
        )
        self.mock_workshop = serializers.WorkshopSerializer(mock_workshop).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_workshops(self):
        response = self.client.get('/workshops/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def get_workshops_with_filter(self, filter, search_term) -> str:
        return f"/workshops/?{filter}={search_term}"

    def get_workshop_alternate_choice(self, original_choice, choices):
        choices_set = set(choices)
        choices_set.remove(original_choice)
        return random.choice(list(choices_set))

    def test_get_workshops_filters(self):
        response = self.client.get(self.get_workshops_with_filter(
            "datetime", self.mock_workshop["datetime"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_workshops_with_filter(
            "datetime", str(datetime.now())))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_workshops_with_filter(
            "location", self.mock_workshop["location"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        location_choices = [
            str(location["id"]) for location
            in models.Location.objects.all().values()
        ]
        response = self.client.get(self.get_workshops_with_filter(
            "location", self.get_workshop_alternate_choice(
                str(self.mock_workshop["location"]), location_choices
        )))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_workshops_with_filter(
            "location", "X"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["location"][0].code, "invalid")
        response = self.client.get(self.get_workshops_with_filter(
            "recommended_for", list(self.mock_workshop["recommended_for"])[0]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_workshops_with_filter(
            "recommended_for", str(uuid.uuid4())))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["recommended_for"][0].code, "invalid_choice")
        response = self.client.get(self.get_workshops_with_filter(
            "hardware", random.choice(self.mock_workshop["hardware"])))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        mock_hardware_type = factories.HardwareFactory()
        response = self.client.get(self.get_workshops_with_filter(
            "hardware", mock_hardware_type.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_get_workshop(self):
        response = self.client.get(f"/workshops/{self.mock_workshop['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_workshop["id"], response.json()["id"])

    def test_get_workshop_404(self):
        response = self.client.get(f"/workshops/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_workshop(self):
        mock_workshop = serializers.WorkshopSerializer(
            models.Workshop.objects.get(pk=self.mock_workshop["id"])).data
        mock_workshop["name"] = f"{self.mock_workshop['name']}updated"
        response = self.client.post('/workshops/', mock_workshop)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_workshop["name"], response.json()["name"])
        self.assertNotEqual(self.mock_workshop["id"], response.json()["id"])

    def test_partial_update_workshop(self):
        mock_workshop = serializers.WorkshopSerializer(
            models.Workshop.objects.get(pk=self.mock_workshop["id"])).data
        new_name = f"{self.mock_workshop['name']}updated"
        mock_workshop = copy.deepcopy(self.mock_workshop)
        new_name = f"{self.mock_workshop['name']}partially_updated"
        mock_workshop["name"] = new_name
        response = self.client.patch(f"/workshops/{mock_workshop['id']}/", {"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.json()["name"])
        self.assertNotEqual(self.mock_workshop["name"], response.json()["name"])

    def test_delete_workshop(self):
        mock_workshop = serializers.WorkshopSerializer(
            factories.WorkshopFactory()).data
        response = self.client.delete(f"/workshops/{mock_workshop['id']}/")
        self.assertEqual(response.status_code, 204)

@keycloak_test
class WorkshopAttendeeTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        mock_location = models.Location.objects.create(room=models.Location.Room.MAIN_HALL)
        group = factories.GroupFactory()
        mock_attendees = [
            factories.AttendeeFactory(
                application=factories.ApplicationFactory(resume=factories.UploadedFileFactory())
            ) for _ in range(
                setup_test_data.TEAM_SIZE + 1)]
        [mock_attendee.groups.set([group]) for mock_attendee in mock_attendees]
        mock_attendee = random.choice(mock_attendees)
        self.mock_attendees = [
            serializers.AttendeeSerializer(mock_attendee).data
            for mock_attendee in mock_attendees
        ]
        self.mock_attendee = serializers.AttendeeSerializer(mock_attendee)
        mock_skills = []
        for _ in range(setup_test_data.NUMBER_OF_SKILLS):
            skill = factories.SkillFactory()
            skill.name = skill.name.lower().replace(
                " ", "_").replace("-", "_").replace(",", "")
            skill.save()
            mock_skills.append(skill)
        self.mock_skills = [
            serializers.SkillSerializer(mock_skill).data for mock_skill in mock_skills
        ]
        mock_hardware_types = []
        for _ in range(setup_test_data.NUMBER_OF_HARDWARE_TYPES):
            hardware_type = factories.HardwareFactory()
            mock_hardware_types.append(hardware_type)
        self.mock_hardware_types = [
            serializers.SkillSerializer(mock_hardware_type).data
            for mock_hardware_type in mock_hardware_types
        ]
        mock_workshop = factories.WorkshopFactory(
            location=mock_location,
            skills=random.sample(mock_skills, random.randint(1, 10)),
            hardware=random.sample(mock_hardware_types, random.randint(1, 10)),
        )
        self.mock_workshop = serializers.WorkshopSerializer(mock_workshop).data
        mock_workshop_attendee = factories.WorkshopAttendeeFactory(
            workshop=mock_workshop, attendee=mock_attendee
        )
        self.mock_workshop_attendee = serializers.WorkshopAttendeeSerializer(
            mock_workshop_attendee).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_workshop_attendees(self):
        response = self.client.get('/workshopattendees/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def get_workshop_attendees_with_filter(self, filter, search_term) -> str:
        return f"/workshopattendees/?{filter}={search_term}"

    def get_workshop_attendee_alternate_choice(self, original_choice, choices):
        choices_set = set(choices)
        choices_set.remove(original_choice)
        return random.choice(list(choices_set))

    def test_get_workshop_attendees_filters(self):
        response = self.client.get(self.get_workshop_attendees_with_filter(
            "workshop", self.mock_workshop_attendee["workshop"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        factories.WorkshopFactory()
        workshop_choices = [
            str(workshop["id"]) for workshop
            in models.Workshop.objects.all().values()
        ]
        response = self.client.get(self.get_workshop_attendees_with_filter(
            "workshop", self.get_workshop_attendee_alternate_choice(
                str(self.mock_workshop_attendee["workshop"]), workshop_choices
            )))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_workshop_attendees_with_filter(
            "attendee", self.mock_workshop_attendee["attendee"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_workshop_attendees_with_filter(
            "attendee", self.get_workshop_attendee_alternate_choice(
                str(self.mock_workshop_attendee["attendee"]),
                [x["id"] for x in self.mock_attendees]
            )))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_workshop_attendees_with_filter(
            "participation", self.mock_workshop_attendee["participation"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_workshop_attendees_with_filter(
            "participation", self.get_workshop_attendee_alternate_choice(
                str(self.mock_workshop_attendee["participation"]),
                [x[0] for x in models.WorkshopAttendee.Participation.choices]
            )))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_get_workshop_attendee(self):
        response = self.client.get(f"/workshopattendees/{self.mock_workshop_attendee['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_workshop_attendee["id"], response.json()["id"])

    def test_get_workshop_attendee_404(self):
        response = self.client.get(f"/workshopattendees/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_workshop_attendee(self):
        mock_workshop_attendee = serializers.WorkshopAttendeeSerializer(
            models.WorkshopAttendee.objects.get(pk=self.mock_workshop_attendee["id"])).data
        mock_workshop_attendee["participation"] = self.get_workshop_attendee_alternate_choice(
            self.mock_workshop_attendee["participation"],
            [x[0] for x in models.WorkshopAttendee.Participation.choices]
        )
        response = self.client.post('/workshopattendees/', mock_workshop_attendee)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_workshop_attendee["participation"], response.json()["participation"])
        self.assertNotEqual(self.mock_workshop_attendee["id"], response.json()["id"])

    def test_partial_update_workshop_attendee(self):
        mock_workshop_attendee = serializers.WorkshopAttendeeSerializer(
            models.WorkshopAttendee.objects.get(pk=self.mock_workshop_attendee["id"])).data
        new_participation = self.get_workshop_attendee_alternate_choice(
            self.mock_workshop_attendee["participation"],
            [x[0] for x in models.WorkshopAttendee.Participation.choices]
        )
        mock_workshop_attendee = copy.deepcopy(self.mock_workshop_attendee)
        mock_workshop_attendee["participation"] = new_participation
        response = self.client.patch(
            f"/workshopattendees/{mock_workshop_attendee['id']}/",
            {"participation": new_participation}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_participation, response.json()["participation"])
        self.assertNotEqual(
            self.mock_workshop_attendee["participation"], response.json()["participation"])
        
    def test_delete_workshop(self):
        mock_workshop_atttendee = serializers.WorkshopAttendeeSerializer(
            factories.WorkshopAttendeeFactory()).data
        response = self.client.delete(f"/workshopattendees/{mock_workshop_atttendee['id']}/")
        self.assertEqual(response.status_code, 204)


@keycloak_test
class AttendeeRSVPTests(APITestCase):
    def setUp(self):
        # Mocking fake phone numbers does not always succeed
        self.client = APIClient()
        factories.GroupFactory()
        mock_resume = factories.UploadedFileFactory()
        mock_application = factories.ApplicationFactory(resume=mock_resume)
        self.mock_application = serializers.ApplicationSerializer(mock_application).data
        mock_attendee = factories.AttendeeFactory(application=mock_application)
        self.mock_attendee_model = mock_attendee
        self.mock_attendee = serializers.AttendeeSerializer(mock_attendee).data
        self.mock_attendee_detail = serializers.AttendeeRSVPSerializer(mock_attendee).data
        self.mock_attendee_create = serializers.AttendeeRSVPCreateSerializer(mock_attendee).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_rsvps(self):
        response = self.client.get('/rsvps/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def get_rsvp_alternate_choice(self, choice, choices):
        alternate_choice = choice
        while alternate_choice == choice:
            alternate_choice = random.choice(choices)
        return alternate_choice

    def get_rsvps_with_filter(self, filter, search_term) -> str:
        return f"/rsvps/?{filter}={search_term}"

    def test_get_rsvps_filters(self):
        response = self.client.get(self.get_rsvps_with_filter(
            "first_name", self.mock_attendee["first_name"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_rsvps_with_filter(
            "first_name", str(uuid.uuid4())))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_rsvps_with_filter(
            "last_name", self.mock_attendee["last_name"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_rsvps_with_filter(
            "last_name", str(uuid.uuid4())))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_rsvps_with_filter(
            "communications_platform_username", self.mock_attendee["communications_platform_username"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_rsvps_with_filter(
            "communications_platform_username", str(uuid.uuid4())))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get(self.get_rsvps_with_filter(
            "email", self.mock_attendee["email"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_rsvps_with_filter(
            "email", str(uuid.uuid4())))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        choices = [x[0] for x in models.Attendee.ParticipationClass.choices]
        response = self.client.get(self.get_rsvps_with_filter(
            "participation_class", self.mock_attendee["participation_class"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_rsvps_with_filter(
            "participation_class", self.get_rsvp_alternate_choice(
                self.mock_attendee['participation_class'], choices)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        choices = [x[0] for x in models.ParticipationRole.choices]
        response = self.client.get(self.get_rsvps_with_filter(
            "participation_role", self.mock_attendee["participation_role"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_rsvps_with_filter(
            "participation_role", self.get_rsvp_alternate_choice(
                self.mock_attendee['participation_role'], choices)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)
        response = self.client.get("/rsvps/?checked_in_at__isnull")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        response = self.client.get(self.get_rsvps_with_filter(
            "checked_in_at", str(datetime.now())))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 0)

    def test_get_rsvp(self):
        response = self.client.get(f"/rsvps/{self.mock_attendee['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_attendee["id"], response.json()["id"])

    def test_get_application_404(self):
        response = self.client.get(f"/rsvps/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_rsvp(self):
        models.Attendee.objects.all().delete()
        mock_sponsor_handler = serializers.AttendeeSerializer(factories.AttendeeFactory(application=None)).data
        mock_attendee = copy.deepcopy(self.mock_attendee)
        del mock_attendee["id"]
        mock_attendee["application"] = self.mock_application["id"]
        mock_attendee["dietary_restrictions"] = [
            models.DietaryRestrictions.GLUTEN_FREE.value,
            models.DietaryRestrictions.KOSHER.value
        ]
        mock_attendee["dietary_allergies"] = [
            models.DietaryAllergies.DAIRY.value,
            models.DietaryAllergies.NUT.value
        ]
        mock_attendee["us_visa_support_is_required"] = False
        mock_attendee["emergency_contact_name"] = str(uuid.uuid4())
        mock_attendee["under_18_by_date"] = False
        mock_attendee["personal_phone_number"] = "+19048800020"
        mock_attendee["emergency_contact_phone_number"] = "+14072394137"
        mock_attendee["emergency_contact_email"] = self.mock_attendee_model.email
        mock_attendee["emergency_contact_relationship"] = str(uuid.uuid4())
        mock_attendee["sponsor_handler"] = mock_sponsor_handler["id"]
        response = self.client.post('/rsvps/', mock_attendee)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(str(self.mock_attendee_model.application.id), response.json()["application"])
        self.assertEqual(self.mock_application["last_name"], response.json()["last_name"])
        self.assertNotEqual(self.mock_attendee["id"], response.json()["id"])

    def test_create_rsvp_application_not_exists(self):
        models.Attendee.objects.all().delete()
        mock_attendee = copy.deepcopy(self.mock_attendee)
        del mock_attendee["id"]
        mock_attendee["application"] = str(uuid.uuid4())
        response = self.client.post('/rsvps/', mock_attendee)
        self.assertEqual(response.status_code, 400)

    def test_create_duplicate_rsvp_email_duplicate_forms(self):
        mock_attendee = copy.deepcopy(self.mock_attendee)
        mock_attendee["email"] = f"{self.mock_attendee['email']}"
        response = self.client.post('/rsvps/', mock_attendee)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["email"][0].code, "unique")

    def test_partial_update_rsvp(self):
        mock_attendee = copy.deepcopy(self.mock_attendee)
        new_last_name = f"{self.mock_attendee['last_name']}partially_updated"
        mock_attendee["last_name"] = new_last_name
        response = self.client.patch(
            f"/rsvps/{mock_attendee['id']}/", {"last_name": new_last_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_last_name, response.json()["last_name"])
        self.assertNotEqual(self.mock_attendee["last_name"], response.json()["last_name"])


class LightHouseTests(APITestCase):
    pass


class DiscordTests(APITestCase):
    pass


@keycloak_test
class BulkTests(APITestCase):
    def setUp(self):
        setup_test_data.add_all()

    def tearDown(self):
        setup_test_data.delete_all()

    def test_bulk_add(self):
        self.assertLessEqual(
            setup_test_data.NUMBER_OF_ATTENDEES, models.Attendee.objects.count())
        self.assertEqual(
            setup_test_data.NUMBER_OF_ATTENDEES * 2, models.Application.objects.count())
        self.assertEqual(
            setup_test_data.NUMBER_OF_GROUPS, Group.objects.count())
        self.assertEqual(
            setup_test_data.NUMBER_OF_TEAMS, models.Team.objects.count())
        for team in models.Team.objects.all():
            self.assertEqual(setup_test_data.TEAM_SIZE, len(team.attendees.values()))
        self.assertEqual(
            setup_test_data.NUMBER_OF_SKILLS, models.Skill.objects.count())
        self.assertEqual(
            setup_test_data.NUMBER_OF_HARDWARE_TYPES, models.Hardware.objects.count())
        self.assertEqual(
            setup_test_data.NUMBER_OF_WORKSHOPS, models.Workshop.objects.count())
        self.assertEqual(
            setup_test_data.NUMBER_OF_WORKSHOP_ATTENDEES * setup_test_data.NUMBER_OF_WORKSHOPS,
            models.WorkshopAttendee.objects.count()
        )
