import requests
import os
import urllib
import secrets
import uuid
import json
from django.core.mail import send_mail
from infrastructure import email
from infrastructure.models import Attendee, ParticipationClass


CLIENT_ID = os.environ['KEYCLOAK_CLIENT_ID']
CLIENT_SECRET_KEY = os.environ['KEYCLOAK_CLIENT_SECRET_KEY']
KEYCLOAK_URL = os.environ['KEYCLOAK_SERVER_URL']
KEYCLOAK_REALM = os.environ['KEYCLOAK_REALM']
EVENT_YEAR = os.environ['EVENT_YEAR']


def remove_invalid_username_chars(username: str) -> str:
    """
    Clean name parameters for Keycloak
    """
    chars_to_remove = " '():" + "`,.!/"
    for char in chars_to_remove:
        username = username.replace(char, "")
    return username


EVENT_YEAR = os.environ['EVENT_YEAR']


class KeycloakRoles(object):
    ATTENDEE = f"attendee:{EVENT_YEAR}"
    ORGANIZER = f"organizer:{EVENT_YEAR}"
    ADMIN = f"admin:{EVENT_YEAR}"
    MENTOR = f"mentor:{EVENT_YEAR}"
    JUDGE = f"judge:{EVENT_YEAR}"
    VOLUNTEER = f"volunteer:{EVENT_YEAR}"
    SPONSOR = f"sponsor:{EVENT_YEAR}"
    GUARDIAN = f"guardian:{EVENT_YEAR}"
    MEDIA = f"media:{EVENT_YEAR}"


class KeycloakClient:
    def __init__(self):
        self.access_token = None
        self.expires_in = None
        self.client_uuid = None
        self.base_url = f"{KEYCLOAK_URL}/admin/realms/{KEYCLOAK_REALM}"
        self.client_role_map = {}
        self._get_authentication_token()

    @property
    def authentication_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def _get_authentication_token(self):
        access_token_params = {
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET_KEY
        }
        token_url = (f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}"
                     f"/protocol/openid-connect/token")
        token_response = requests.post(
            url=token_url,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data=urllib.parse.urlencode(access_token_params)
        )
        if not token_response.ok:
            raise Exception(
                f"Error getting authentication token: {token_response.json()}"
            )
        self.access_token = token_response.json()['access_token']
        self.expires_in = token_response.json()['expires_in']
        return self.access_token

    def get_client_uuid(self):
        if not self.access_token:
            self._get_authentication_token()
        client_uuid = requests.get(
            url=f"{self.base_url}/clients?clientId={CLIENT_ID}",
            headers=self.authentication_headers,
        )
        if not client_uuid.ok or not len(client_uuid.json()):
            status_code = client_uuid.status_code
            text = client_uuid.text
            raise Exception(
                f"Error getting client UUID: {status_code} - {text}"
            )
        self.client_uuid = client_uuid.json()[0]['id']
        return self.client_uuid

    def _get_client_roles_map(self):
        if not self.access_token:
            self._get_authentication_token()
        if not self.client_uuid:
            self.get_client_uuid()

        client_roles = requests.get(
            url=f"{self.base_url}/clients/{self.client_uuid}/roles",
            headers=self.authentication_headers,
        )

        if not client_roles.ok:
            print(f"Client roles response: {client_roles.json()}")
            status_code = client_roles.status_code
            text = client_roles.text
            raise Exception(
                f"Error getting client roles: {status_code} - {text}"
            )
        roles_data = client_roles.json()

        self.client_role_map = {
            role['name']: role for role in roles_data
        }
        return self.client_role_map

    def get_client_role_mapping(self, role_name: str):
        if not self.client_role_map:
            self._get_client_roles_map()

        role_mapping = self.client_role_map[role_name]
        if not role_mapping:
            raise Exception(f"Role mapping not found for {role_name}")

        return role_mapping

    def create_authentication_account(
        self, attendee: Attendee, temporary_password: str
    ) -> str:
        first_name = remove_invalid_username_chars(attendee.first_name)
        last_name = remove_invalid_username_chars(attendee.last_name)
        username = f'{first_name}.{last_name}.{uuid.uuid4()}'
        auth_user_dict = {
            "id": str(uuid.uuid4()),
            "username": username,
            "enabled": True,
            "email": attendee.email,
            "firstName": first_name,
            "lastName": last_name,
            "credentials": [
                {
                    "type": "password",
                    "value": temporary_password,
                    "temporary": True
                }
            ],
            "clientRoles": {
                "account": [
                    "manage-account",
                    "view-profile"
                ]
            }
        }
        authentication_account = requests.post(
            url=f"{self.base_url}/users",
            headers=self.authentication_headers,
            data=json.dumps(auth_user_dict)
        )
        if authentication_account.ok:
            account_headers = authentication_account.headers
            authentication_account_id = account_headers["Location"].split("/")[-1]
            attendee.authentication_id = authentication_account_id
            attendee.save()
            print(f"Authentication account created for {attendee.email}")
            return authentication_account_id
        else:
            print(f"Error creating authentication account for {attendee.email}")
            print(f"Authentication account response: {authentication_account.json()}")
            raise Exception(
                f"Error creating authentication account for {attendee.email}"
            )

    def assign_authentication_roles(self, attendee: Attendee):
        if not attendee.authentication_id:
            raise Exception("Authentication ID is not set")

        if not attendee.participation_class:
            raise Exception("Participation class is not set")

        if attendee.participation_class == ParticipationClass.PARTICIPANT:
            role = "attendee"
        else:
            role = attendee.get_participation_class_display().lower()

        client_role = self.get_client_role_mapping(f"{role}:{EVENT_YEAR}")

        if not client_role:
            raise Exception(f"Client role not found for {role}")

        auth_roles = [client_role]
        auth_roles_mapping = requests.post(
            url=f"{self.base_url}/users/{attendee.authentication_id}"
            f"/role-mappings/clients/{self.client_uuid}",
            headers=self.authentication_headers,
            data=json.dumps(auth_roles)
        )

        if auth_roles_mapping.ok:
            attendee.authentication_roles_assigned = True
            attendee.save()
        else:
            raise Exception(
                f"Error assigning authentication roles: {auth_roles_mapping.json()}"
            )
        return auth_roles

    def find_user_by_email(self, attendee_email: str):
        users = requests.get(
            url=f"{self.base_url}/users?email={attendee_email}&exact=true",
            headers=self.authentication_headers,
        )
        return users.json()

    def handle_user_creation(self, attendee: Attendee) -> str:
        temporary_password = secrets.token_hex(10 // 2)
        try:
            if not attendee.authentication_id:
                authentication_account_id = self.create_authentication_account(
                    attendee, temporary_password
                )
                print(f"Keycloak account created for {attendee.email}")
                attendee.authentication_id = authentication_account_id
            self.assign_authentication_roles(attendee)
            return temporary_password
        except Exception as e:
            print(f"Error creating keycloak account for {attendee.email}: {e}")
            raise e

    def _ensure_authentication_account(self, attendee: Attendee) -> str | None:
        if attendee.authentication_id:
            return None
        elif existing_users := self.find_user_by_email(attendee.email):
            if len(existing_users) > 1:
                subject, body = email.get_multiple_users_found_template(attendee.email),
                send_mail(
                    subject,
                    body,
                    "no-reply@realityhackinc.org",
                    [attendee.email, "apply@realityhackinc.org"],
                    fail_silently=False,
                )
                raise Exception(f"Multiple users found for email: {attendee.email}")
            else:
                attendee.authentication_id = existing_users[0]['id']
                attendee.save()
                return None
        else:
            return self.handle_user_creation(attendee)

    def handle_user_rsvp(self, attendee: Attendee) -> None:
        temp_password = self._ensure_authentication_account(attendee)
        self.assign_authentication_roles(attendee)
        if attendee.participation_class == ParticipationClass.PARTICIPANT:
            subject, body = email.get_hacker_rsvp_confirmation_template(
                attendee.first_name, temp_password
            )
        else:
            subject, body = email.get_non_hacker_rsvp_confirmation_template(
                attendee.first_name, temp_password
            )
        send_mail(
            subject,
            body,
            "no-reply@realityhackinc.org",
            [attendee.email],
            fail_silently=False,
        )
