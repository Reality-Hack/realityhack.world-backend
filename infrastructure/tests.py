import copy

from django.contrib.auth.models import Group
from rest_framework.test import APIClient, APITestCase

from infrastructure import factories, models, serializers
from infrastructure.management.commands import setup_test_data


class AttendeeTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        group = factories.GroupFactory()
        mock_attendee = factories.AttendeeFactory()
        mock_attendee.groups.set([group])
        self.mock_attendee = serializers.AttendeeSerializer(mock_attendee).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_attendees(self):
        response = self.client.get('/attendees/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_get_attendee(self):
        response = self.client.get(f"/attendees/{self.mock_attendee['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_attendee["id"], response.data["id"])

    def test_create_attendee(self):
        mock_attendee = copy.deepcopy(self.mock_attendee)
        mock_attendee["username"] = f"{self.mock_attendee['username']}updated"
        response = self.client.post('/attendees/', mock_attendee)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_attendee["last_name"], response.data["last_name"])
        self.assertNotEqual(self.mock_attendee["id"], response.data["id"])

    def test_update_attendee(self):
        mock_attendee = copy.deepcopy(self.mock_attendee)
        new_last_name = f"{self.mock_attendee['last_name']}updated"
        mock_attendee["last_name"] = new_last_name
        response = self.client.put(f"/attendees/{mock_attendee['id']}/", mock_attendee)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_last_name, response.data["last_name"])
        self.assertNotEqual(self.mock_attendee["last_name"], response.data["last_name"])

    def test_partial_update_attendee(self):
        mock_attendee = copy.deepcopy(self.mock_attendee)
        new_last_name = f"{self.mock_attendee['last_name']}partially_updated"
        mock_attendee["last_name"] = new_last_name
        response = self.client.patch(
            f"/attendees/{mock_attendee['id']}/", {"last_name": new_last_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_last_name, response.data["last_name"])
        self.assertNotEqual(self.mock_attendee["last_name"], response.data["last_name"])


class TeamTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        self.table = factories.TableFactory()
        group = factories.GroupFactory()
        mock_attendees = [
            factories.AttendeeFactory() for _ in range(
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
        self.assertEqual(len(response.data), 1)

    def test_get_team(self):
        response = self.client.get(f"/teams/{self.mock_team['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_team["id"], response.data["id"])

    def test_create_team(self):
        table = factories.TableFactory()
        mock_team = serializers.TeamCreateSerializer(
            models.Team.objects.get(pk=self.mock_team["id"])).data
        mock_team["table"] = table.id
        mock_team["name"] = f"{self.mock_team['name']}updated"
        response = self.client.post('/teams/', mock_team)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_team["name"], response.data["name"])
        self.assertNotEqual(self.mock_team["id"], response.data["id"])

    def test_update_team(self):
        mock_team = serializers.TeamCreateSerializer(
            models.Team.objects.get(pk=self.mock_team["id"])).data
        new_name = f"{self.mock_team['name']}updated"
        mock_team["name"] = new_name
        response = self.client.put(f"/teams/{mock_team['id']}/", mock_team)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.data["name"])
        self.assertNotEqual(self.mock_team["name"], response.data["name"])

    def test_partial_update_attendee(self):
        mock_team = serializers.TeamCreateSerializer(
            models.Team.objects.get(pk=self.mock_team["id"])).data
        new_name = f"{self.mock_team['name']}updated"
        mock_team = copy.deepcopy(self.mock_team)
        new_name = f"{self.mock_team['name']}partially_updated"
        mock_team["name"] = new_name
        response = self.client.patch(f"/teams/{mock_team['id']}/", {"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.data["name"])
        self.assertNotEqual(self.mock_team["name"], response.data["name"])

    # Two Teams to a Table

    # More than five Attendees to a Team


class ProjectTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        self.table = factories.TableFactory()
        group = factories.GroupFactory()
        mock_attendees = [
            factories.AttendeeFactory() for _ in range(
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
        self.assertEqual(len(response.data), 1)

    def test_get_project(self):
        response = self.client.get(f"/projects/{self.mock_project['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_project["id"], response.data["id"])

    def test_create_project(self):
        models.Project.objects.all().delete()
        mock_project = copy.deepcopy(self.mock_project)
        mock_project["name"] = f"{self.mock_project['name']}updated"
        response = self.client.post('/projects/', mock_project)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_project["name"], response.data["name"])
        self.assertNotEqual(self.mock_project["id"], response.data["id"])

    def test_update_project(self):
        mock_team = copy.deepcopy(self.mock_project)
        new_name = f"{self.mock_project['name']}updated"
        mock_team["name"] = new_name
        response = self.client.put(f"/projects/{mock_team['id']}/", mock_team)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.data["name"])
        self.assertNotEqual(self.mock_project["name"], response.data["name"])

    def test_partial_update_project(self):
        mock_attendee = copy.deepcopy(self.mock_project)
        new_name = f"{self.mock_project['name']}partially_updated"
        mock_attendee["name"] = new_name
        response = self.client.patch(
            f"/projects/{mock_attendee['id']}/", {"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.data["name"])
        self.assertNotEqual(self.mock_project["name"], response.data["name"])


class HardwareTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        hardware_type = factories.HardwareFactory()
        self.mock_hardware_type = serializers.HardwareSerializer(hardware_type).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_hardwares(self):
        response = self.client.get('/hardware/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_get_hardware(self):
        response = self.client.get(f"/hardware/{self.mock_hardware_type['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_hardware_type["id"], response.data["id"])

    def test_create_hardware(self):
        models.Hardware.objects.all().delete()
        mock_hardware_type = copy.deepcopy(self.mock_hardware_type)
        response = self.client.post('/hardware/', mock_hardware_type)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_hardware_type["name"], response.data["name"])
        self.assertNotEqual(self.mock_hardware_type["id"], response.data["id"])

    def test_update_hardware(self):
        mock_hardware_type = copy.deepcopy(self.mock_hardware_type)
        new_name = f"{self.mock_hardware_type['name']}updated"
        mock_hardware_type["name"] = new_name
        response = self.client.put(
            f"/hardware/{mock_hardware_type['id']}/", mock_hardware_type)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.data["name"])
        self.assertNotEqual(self.mock_hardware_type["name"], response.data["name"])

    def test_partial_update_hardware(self):
        mock_hardware_type = copy.deepcopy(self.mock_hardware_type)
        new_name = f"{self.mock_hardware_type['name']}partially_updated"
        mock_hardware_type["name"] = new_name
        response = self.client.patch(
            f"/hardware/{mock_hardware_type['id']}/", {"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.data["name"])
        self.assertNotEqual(self.mock_hardware_type["name"], response.data["name"])


class HardwareDeviceTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.mock_attendee = serializers.AttendeeSerializer(
            factories.AttendeeFactory()).data
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
        self.assertEqual(len(response.data), 1)

    def test_get_hardware_device(self):
        response = self.client.get(
            f"/hardwaredevices/{self.mock_hardware_device['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_hardware_device["id"], response.data["id"])

    def test_create_hardware_device(self):
        models.HardwareDevice.objects.all().delete()
        mock_hardware_device = copy.deepcopy(self.mock_hardware_device)
        response = self.client.post('/hardwaredevices/', mock_hardware_device)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_hardware_device["serial"], response.data["serial"])
        self.assertNotEqual(self.mock_hardware_device["id"], response.data["id"])

    def test_update_hardware_device(self):
        mock_hardware_device = copy.deepcopy(self.mock_hardware_device)
        new_serial = f"{self.mock_hardware_device['serial']}updated"
        mock_hardware_device["serial"] = new_serial
        response = self.client.put(
            f"/hardwaredevices/{mock_hardware_device['id']}/", mock_hardware_device)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_serial, response.data["serial"])
        self.assertNotEqual(
            self.mock_hardware_device["serial"], response.data["serial"])

    def test_partial_update_hardware_device(self):
        mock_hardware_device = copy.deepcopy(self.mock_hardware_device)
        new_serial = f"{self.mock_hardware_type['name']}partially_updated"
        mock_hardware_device["serial"] = new_serial
        response = self.client.patch(
            f"/hardwaredevices/{mock_hardware_device['id']}/", {"serial": new_serial})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_serial, response.data["serial"])
        self.assertNotEqual(
            self.mock_hardware_device["serial"], response.data["serial"])

    def test_partial_update_hardware_device_check_out(self):
        mock_hardware_device = copy.deepcopy(self.mock_hardware_device)
        mock_hardware_device["checked_out_to"] = self.mock_attendee["id"]
        response = self.client.patch(
            f"/hardwaredevices/{mock_hardware_device['id']}/",
            {"checked_out_to": mock_hardware_device["checked_out_to"]}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            mock_hardware_device["checked_out_to"],
            str(response.data["checked_out_to"])
        )


class BulkTests(APITestCase):
    def setUp(self):
        setup_test_data.add_all()

    def tearDown(self):
        setup_test_data.delete_all()

    def test_bulk_add(self):

        # NUMBER_OF_ATTENDEES = 500
        # NUMBER_OF_GROUPS = 5
        # NUMBER_OF_SKILLS = 80
        # NUMBER_OF_TEAMS = 80
        # TEAM_SIZE = 5
        # NUMBER_OF_SKILL_PROFICIENCIES = 4
        # NUMBER_OF_HARDWARE_TYPES = 10
        # NUMBER_OF_HARDWARE_DEVICES = 25
        self.assertEqual(
            setup_test_data.NUMBER_OF_ATTENDEES, models.Attendee.objects.count())
        self.assertEqual(
            setup_test_data.NUMBER_OF_GROUPS, Group.objects.count())
        self.assertEqual(
            setup_test_data.NUMBER_OF_TEAMS, models.Team.objects.count())
        for team in models.Team.objects.all():
            self.assertEqual(setup_test_data.TEAM_SIZE, len(team.attendees.values()))
