import copy
import os
import random
import uuid
from datetime import datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
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

    def test_get_team_no_project(self):
        team = models.Team.objects.get(pk=self.mock_team["id"])
        team.project = None
        team.save()
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
        mock_application = factories.ApplicationFactory()
        self.mock_attendee = serializers.AttendeeSerializer(mock_attendee).data
        skill = factories.SkillFactory()
        skill_proficiency = factories.SkillProficiencyFactory(
            attendee=mock_attendee, application=mock_application, skill=skill)
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
            self.mock_skill_proficiency["id"], response.data["id"])

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
            self.mock_skill_proficiency["skill"], response.data["skill"])

    def test_partial_update_skill_proficiency(self):
        mock_skill = factories.SkillFactory()
        response = self.client.patch(
            f"/skillproficiencies/{self.mock_skill_proficiency['id']}/",
            {"skill": mock_skill.id}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_skill.id, response.data["skill"])
        self.assertNotEqual(
            self.mock_skill_proficiency["skill"], response.data["skill"])
        

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


class ApplicationTests(APITestCase):
    def setUp(self):
        # Mocking fake phone numbers does not always succeed
        self.client = APIClient()
        mock_skill = factories.SkillFactory()
        self.mock_skill = serializers.SkillSerializer(mock_skill).data
        mock_application = factories.ApplicationFactory()
        self.mock_application = serializers.ApplicationSerializer(mock_application).data
        skill_proficiency = factories.SkillProficiencyFactory(
            application=mock_application, skill=mock_skill)
        self.mock_skill_proficiency = serializers.SkillProficiencySerializer(
            skill_proficiency).data

    def tearDown(self):
        setup_test_data.delete_all()

    def test_get_applications(self):
        response = self.client.get('/applications/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

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
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_applications_with_filter(
            "participation_capacity", self.get_application_alternate_choice(
                self.mock_application['participation_capacity'], choices)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        choices = [x[0] for x in models.ParticipationRole.choices]
        response = self.client.get(self.get_applications_with_filter(
            "participation_role", self.mock_application["participation_role"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_applications_with_filter(
            "participation_role", self.get_application_alternate_choice(
                self.mock_application['participation_role'], choices)))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_applications_with_filter(
            "email", self.mock_application["email"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_applications_with_filter(
            "email", f"fake{self.mock_application['email']}"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_get_application(self):
        response = self.client.get(f"/applications/{self.mock_application['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_application["id"], response.data["id"])

    def test_get_application_404(self):
        response = self.client.get(f"/applicaitons/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_application(self):
        models.Application.objects.all().delete()
        models.SkillProficiency.objects.all().delete()
        mock_application = copy.deepcopy(self.mock_application)
        response = self.client.post('/applications/', mock_application)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.mock_application["last_name"], response.data["last_name"])
        self.assertNotEqual(self.mock_application["id"], response.data["id"])

    def test_create_duplicate_application_email_duplicate_forms(self):
        mock_application = copy.deepcopy(self.mock_application)
        mock_application["email"] = f"{self.mock_application['email']}updated"
        response = self.client.post('/applications/', mock_application)
        self.assertEqual(response.status_code, 400)

    def test_create_duplicate_application_email_unique_forms(self):
        mock_application = copy.deepcopy(self.mock_application)
        mock_application["email"] = f"{self.mock_application['email']}updated"
        mock_application["parental_consent_form"] = serializers.FileUploadSerializer(
            factories.UploadedFileFactory()).data["id"]
        mock_application["media_release"] = serializers.FileUploadSerializer(
            factories.UploadedFileFactory()).data["id"]
        mock_application["liability_release"] = serializers.FileUploadSerializer(
            factories.UploadedFileFactory()).data["id"]
        response = self.client.post('/applications/', mock_application)
        self.assertEqual(response.status_code, 201)

    def test_update_application(self):
        mock_application = copy.deepcopy(self.mock_application)
        new_last_name = f"{self.mock_application['last_name']}updated"
        mock_application["last_name"] = new_last_name
        response = self.client.put(f"/applications/{mock_application['id']}/", mock_application)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_last_name, response.data["last_name"])
        self.assertNotEqual(self.mock_application["last_name"], response.data["last_name"])

    def test_partial_update_application(self):
        mock_application = copy.deepcopy(self.mock_application)
        new_last_name = f"{self.mock_application['last_name']}partially_updated"
        mock_application["last_name"] = new_last_name
        response = self.client.patch(
            f"/applications/{mock_application['id']}/", {"last_name": new_last_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_last_name, response.data["last_name"])
        self.assertNotEqual(self.mock_application["last_name"], response.data["last_name"])


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
        self.assertEqual(uploaded_file["id"], response.data["id"])

    def test_delete_uploaded_file(self):
        uploaded_file = serializers.FileUploadSerializer(
            factories.UploadedFileFactory()).data
        response = self.client.delete(f"/uploaded_files/{uploaded_file['id']}/")
        self.assertEqual(response.status_code, 204)
        self.assertNotIn(uploaded_file["id"], os.listdir(settings.MEDIA_ROOT))


class WorkshopTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        mock_location = models.Location.objects.create(room=models.Location.Room.MAIN_HALL)
        group = factories.GroupFactory()
        mock_attendees = [
            factories.AttendeeFactory() for _ in range(
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
        self.assertEqual(len(response.data), 1)

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
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_workshops_with_filter(
            "datetime", str(datetime.now())))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_workshops_with_filter(
            "location", self.mock_workshop["location"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        location_choices = [
            str(location["id"]) for location
            in models.Location.objects.all().values()
        ]
        response = self.client.get(self.get_workshops_with_filter(
            "location", self.get_workshop_alternate_choice(
                str(self.mock_workshop["location"]), location_choices
        )))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_workshops_with_filter(
            "location", "X"))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["location"][0].code, "invalid")
        response = self.client.get(self.get_workshops_with_filter(
            "recommended_for", list(self.mock_workshop["recommended_for"])[0]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_workshops_with_filter(
            "recommended_for", str(uuid.uuid4())))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["recommended_for"][0].code, "invalid_choice")
        response = self.client.get(self.get_workshops_with_filter(
            "hardware", random.choice(self.mock_workshop["hardware"])))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        mock_hardware_type = factories.HardwareFactory()
        response = self.client.get(self.get_workshops_with_filter(
            "hardware", mock_hardware_type.id))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_get_workshop(self):
        response = self.client.get(f"/workshops/{self.mock_workshop['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_workshop["id"], response.data["id"])

    def test_get_workshop_404(self):
        response = self.client.get(f"/workshops/{str(uuid.uuid4())}/")
        self.assertEqual(response.status_code, 404)

    def test_create_workshop(self):
        mock_workshop = serializers.WorkshopSerializer(
            models.Workshop.objects.get(pk=self.mock_workshop["id"])).data
        mock_workshop["name"] = f"{self.mock_workshop['name']}updated"
        response = self.client.post('/workshops/', mock_workshop)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(mock_workshop["name"], response.data["name"])
        self.assertNotEqual(self.mock_workshop["id"], response.data["id"])

    def test_update_workshop(self):
        mock_workshop = serializers.WorkshopSerializer(
            models.Workshop.objects.get(pk=self.mock_workshop["id"])).data
        new_name = f"{self.mock_workshop['name']}updated"
        mock_workshop["name"] = new_name
        response = self.client.put(f"/workshops/{mock_workshop['id']}/", mock_workshop)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.data["name"])
        self.assertNotEqual(self.mock_workshop["name"], response.data["name"])

    def test_partial_update_workshop(self):
        mock_workshop = serializers.WorkshopSerializer(
            models.Workshop.objects.get(pk=self.mock_workshop["id"])).data
        new_name = f"{self.mock_workshop['name']}updated"
        mock_workshop = copy.deepcopy(self.mock_workshop)
        new_name = f"{self.mock_workshop['name']}partially_updated"
        mock_workshop["name"] = new_name
        response = self.client.patch(f"/workshops/{mock_workshop['id']}/", {"name": new_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_name, response.data["name"])
        self.assertNotEqual(self.mock_workshop["name"], response.data["name"])

    def test_delete_workshop(self):
        mock_workshop = serializers.WorkshopSerializer(
            factories.WorkshopFactory()).data
        response = self.client.delete(f"/workshops/{mock_workshop['id']}/")
        self.assertEqual(response.status_code, 204)


class WorkshopAttendeeTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        models.Location.objects.create(room=models.Location.Room.ATLANTIS)
        mock_location = models.Location.objects.create(room=models.Location.Room.MAIN_HALL)
        group = factories.GroupFactory()
        mock_attendees = [
            factories.AttendeeFactory() for _ in range(
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
        self.assertEqual(len(response.data), 1)

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
        self.assertEqual(len(response.data), 1)
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
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_workshop_attendees_with_filter(
            "attendee", self.mock_workshop_attendee["attendee"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_workshop_attendees_with_filter(
            "attendee", self.get_workshop_attendee_alternate_choice(
                str(self.mock_workshop_attendee["attendee"]),
                [x["id"] for x in self.mock_attendees]
            )))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)
        response = self.client.get(self.get_workshop_attendees_with_filter(
            "participation", self.mock_workshop_attendee["participation"]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        response = self.client.get(self.get_workshop_attendees_with_filter(
            "participation", self.get_workshop_attendee_alternate_choice(
                str(self.mock_workshop_attendee["participation"]),
                [x[0] for x in models.WorkshopAttendee.Participation.choices]
            )))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_get_workshop_attendee(self):
        response = self.client.get(f"/workshopattendees/{self.mock_workshop_attendee['id']}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.mock_workshop_attendee["id"], response.data["id"])

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
        self.assertEqual(mock_workshop_attendee["participation"], response.data["participation"])
        self.assertNotEqual(self.mock_workshop_attendee["id"], response.data["id"])

    def test_update_workshop_attendee(self):
        mock_workshop_attendee = serializers.WorkshopAttendeeSerializer(
            models.WorkshopAttendee.objects.get(pk=self.mock_workshop_attendee["id"])).data
        new_participation = self.get_workshop_attendee_alternate_choice(
            self.mock_workshop_attendee["participation"],
            [x[0] for x in models.WorkshopAttendee.Participation.choices]
        )
        mock_workshop_attendee["participation"] = new_participation
        response = self.client.put(
            f"/workshopattendees/{mock_workshop_attendee['id']}/", mock_workshop_attendee)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(new_participation, response.data["participation"])
        self.assertNotEqual(
            self.mock_workshop_attendee["participation"], response.data["participation"])

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
        self.assertEqual(new_participation, response.data["participation"])
        self.assertNotEqual(
            self.mock_workshop_attendee["participation"], response.data["participation"])
        
    def test_delete_workshop(self):
        mock_workshop_atttendee = serializers.WorkshopAttendeeSerializer(
            factories.WorkshopAttendeeFactory()).data
        response = self.client.delete(f"/workshopattendees/{mock_workshop_atttendee['id']}/")
        self.assertEqual(response.status_code, 204)


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
