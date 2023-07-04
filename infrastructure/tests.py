import copy
import uuid

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

    def get_attendees_with_filter(self, filter, search_term) -> str:
        return f"/attendees/?{filter}={search_term}"

    def test_get_attendees_filters(self):
        response = self.client.get(self.get_attendees_with_filter(
            "first_name", self.mock_attendee["first_name"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_attendees_with_filter(
            "first_name", f"fake{self.mock_attendee['first_name']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_attendees_with_filter(
            "last_name", self.mock_attendee["last_name"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_attendees_with_filter(
            "last_name", f"fake{self.mock_attendee['last_name']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_attendees_with_filter(
            "email", self.mock_attendee["email"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_attendees_with_filter(
            "email", f"fake{self.mock_attendee['email']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_attendees_with_filter(
            "username", self.mock_attendee["username"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_attendees_with_filter(
            "username", f"fake{self.mock_attendee['username']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_attendees_with_filter(
            "is_staff", str(self.mock_attendee['is_staff']).lower()))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_attendees_with_filter(
            "is_staff", str(not self.mock_attendee['is_staff']).lower()))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_attendees_with_filter(
            "groups", self.mock_attendee["groups"][0]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_attendees_with_filter(
            "groups", 10000))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["groups"][0].code, "invalid_choice")

    def test_get_attendee(self):
        response = self.client.get(f"/attendees/{self.mock_attendee['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_attendee["id"], response.data["id"])

    def test_get_attendee_404(self):
        response = self.client.get(f"/attendees/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_attendee(self):
        models.Attendee.objects.all().delete()
        mock_attendee = copy.deepcopy(self.mock_attendee)
        response = self.client.post('/attendees/', mock_attendee)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_attendee["last_name"], response.data["last_name"])
        self.assertNotEqual(self.mock_attendee["id"], response.data["id"])

    def test_create_duplicate_attendee_username(self):
        mock_attendee = copy.deepcopy(self.mock_attendee)
        mock_attendee["email"] = f"updated{self.mock_attendee['email']}"
        response = self.client.post('/attendees/', mock_attendee)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["username"][0].code, "unique")

    def test_create_duplicate_attendee_email(self):
        mock_attendee = copy.deepcopy(self.mock_attendee)
        mock_attendee["username"] = f"{self.mock_attendee['username']}updated"
        response = self.client.post('/attendees/', mock_attendee)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["email"][0].code, "unique")

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

    def get_teams_with_filter(self, filter, search_term) -> str:
        return f"/teams/?{filter}={search_term}"

    def test_get_teams_filters(self):
        response = self.client.get(self.get_teams_with_filter(
            "name", self.mock_team["name"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_teams_with_filter(
            "name", f"fake{self.mock_team['name']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_teams_with_filter(
            "attendees", self.mock_team["attendees"][0]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_teams_with_filter(
            "attendees", str(uuid.uuid4())))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["attendees"][0].code, "invalid_choice")
        response = self.client.get(self.get_teams_with_filter(
            "table", self.mock_team["table"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_teams_with_filter(
            "table", str(uuid.uuid4())))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["table"][0].code, "invalid_choice")
        response = self.client.get(self.get_teams_with_filter(
            "table__number", self.table.number))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_teams_with_filter(
            "table__number", -1))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_get_team(self):
        response = self.client.get(f"/teams/{self.mock_team['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_team["id"], response.data["id"])

    def test_get_team_404(self):
        response = self.client.get(f"/teams/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

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

    def test_partial_update_team(self):
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

    def test_get_project_404(self):
        response = self.client.get(f"/projects/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_project(self):
        models.Project.objects.all().delete()
        mock_project = copy.deepcopy(self.mock_project)
        mock_project["name"] = f"{self.mock_project['name']}updated"
        response = self.client.post('/projects/', mock_project)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_project["name"], response.data["name"])
        self.assertNotEqual(self.mock_project["id"], response.data["id"])

    def test_create_duplicate_team_project(self):
        mock_project = copy.deepcopy(self.mock_project)
        mock_project["name"] = f"{self.mock_project['name']}updated"
        response = self.client.post('/projects/', mock_project)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["team"][0].code, "unique")

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

    def test_get_hardware_404(self):
        response = self.client.get(f"/hardware/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

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

    def test_get_hardware_device_404(self):
        response = self.client.get(f"/hardwaredevices/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

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
        self.assertEqual(len(response.data), 1)

    def test_get_skill(self):
        response = self.client.get(f"/skills/{self.mock_skill['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_skill["id"], response.data["id"])

    def test_get_skill_404(self):
        response = self.client.get(f"/skills/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_skill(self):
        models.Skill.objects.all().delete()
        mock_skill = copy.deepcopy(self.mock_skill)
        response = self.client.post('/skills/', mock_skill)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_skill["name"], response.data["name"])
        self.assertNotEqual(self.mock_skill["id"], response.data["id"])

    def test_update_skill(self):
        mock_skill = copy.deepcopy(self.mock_skill)
        new_name = f"{self.mock_skill['name']}updated"
        mock_skill["name"] = new_name
        response = self.client.put(
            f"/skills/{mock_skill['id']}/", mock_skill)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.data["name"])
        self.assertNotEqual(self.mock_skill["name"], response.data["name"])

    def test_partial_update_skill(self):
        mock_skill = copy.deepcopy(self.mock_skill)
        new_name = f"{self.mock_skill['name']}partially_updated"
        mock_skill["name"] = new_name
        response = self.client.patch(
            f"/skills/{mock_skill['id']}/", {"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.data["name"])
        self.assertNotEqual(self.mock_skill["name"], response.data["name"])


class SkillProficiencyTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        factories.GroupFactory()
        mock_attendee = factories.AttendeeFactory()
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
        self.assertEqual(len(response.data), 1)

    def test_get_skill_proficiency(self):
        response = self.client.get(
            f"/skillproficiencies/{self.mock_skill_proficiency['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_skill_proficiency["id"], response.data["id"])

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
            mock_skill_proficiency["skill"], response.data["skill"])
        self.assertNotEqual(
            self.mock_skill_proficiency["skill"]["id"], response.data["skill"])

    def test_create_non_unique_skill_proficiency(self):
        mock_skill_proficiency = serializers.SkillProficiencyCreateSerializer(
            models.SkillProficiency.objects.get(pk=self.mock_skill_proficiency["id"])
        ).data
        response = self.client.post('/skillproficiencies/', mock_skill_proficiency)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["non_field_errors"][0].code, "unique")

    def test_update_skill_proficiency(self):
        mock_skill_proficiency = serializers.SkillProficiencyCreateSerializer(
            models.SkillProficiency.objects.get(pk=self.mock_skill_proficiency["id"])
        ).data
        mock_skill = factories.SkillFactory()
        mock_skill_proficiency["skill"] = mock_skill.id
        response = self.client.put(
            f"/skillproficiencies/{mock_skill_proficiency['id']}/",
            mock_skill_proficiency
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_skill.id, response.data["skill"])
        self.assertNotEqual(
            self.mock_skill_proficiency["skill"]["id"], response.data["skill"])

    def test_partial_update_skill_proficiency(self):
        mock_skill = factories.SkillFactory()
        response = self.client.patch(
            f"/skillproficiencies/{self.mock_skill_proficiency['id']}/",
            {"skill": mock_skill.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_skill.id, response.data["skill"])
        self.assertNotEqual(
            self.mock_skill_proficiency["skill"]["id"], response.data["skill"])
        

class TableTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        location = models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        self.mock_location = serializers.LocationSerializer(location).data
        table = factories.TableFactory(location=location)
        self.mock_table = serializers.TableSerializer(table).data
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
            attendees=mock_attendees[0:setup_test_data.TEAM_SIZE], table=table)
        self.mock_team = serializers.TeamSerializer(team).data
        help_desk = factories.HelpDeskFactory()
        self.help_desk = serializers.HelpDeskSerializer(help_desk).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_tables(self):
        response = self.client.get('/tables/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_get_table(self):
        response = self.client.get(f"/tables/{self.mock_table['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_table["id"], response.data["id"])

    def test_get_table_404(self):
        response = self.client.get(f"/tables/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_table(self):
        mock_table = serializers.TableCreateSerializer(factories.TableFactory()).data
        mock_table["number"] += 1
        mock_table["location"] = self.mock_location["id"]
        response = self.client.post('/tables/', mock_table)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_table["number"], response.data["number"])
        self.assertNotEqual(self.mock_table["id"], response.data["id"])

    def test_update_table(self):
        mock_table = serializers.TableCreateSerializer(
            models.Table.objects.get(pk=self.mock_table["id"])).data
        new_number = self.mock_table["number"] + 1
        mock_table["number"] = new_number
        response = self.client.put(f"/tables/{mock_table['id']}/", mock_table)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_number, response.data["number"])
        self.assertNotEqual(self.mock_table["number"], response.data["number"])

    def test_partial_update_table(self):
        mock_table = serializers.TableCreateSerializer(
            models.Table.objects.get(pk=self.mock_table["id"])).data
        new_number = self.mock_table["number"] + 1
        mock_table["number"] = new_number
        response = self.client.patch(
            f"/tables/{mock_table['id']}/",{"number": new_number})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_number, response.data["number"])
        self.assertNotEqual(self.mock_table["number"], response.data["number"])


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
        self.assertEqual(
            setup_test_data.NUMBER_OF_SKILLS, models.Skill.objects.count())
        self.assertEqual(
            setup_test_data.NUMBER_OF_HARDWARE_TYPES, models.Hardware.objects.count())
