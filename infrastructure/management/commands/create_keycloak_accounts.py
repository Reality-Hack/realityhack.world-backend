from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from infrastructure import email
from infrastructure.models import Attendee, Application, UploadedFile
import requests
import json
import os
import secrets
import uuid
import pprint

class Command(BaseCommand):  # pragma: no cover
    help = "resend keycloak account creation emails"
    
    def clean_name_params(self, name: str) -> str:
        return name.replace(" ", "").replace("'", "").replace("(", "").replace(")", "").replace(":", "").replace("`", "").replace(",", "").replace(".", "")

    def handle(self, *args, **kwargs):  # noqa: C901
        hackers = Attendee.objects.filter(authentication_id__isnull=True)
        for hacker in hackers:
            temporary_password = secrets.token_hex(10 // 2)
            access_token = hacker.get_authentication_token()
            first_name = self.clean_name_params(hacker.first_name)
            last_name = self.clean_name_params(hacker.last_name)
            username = f'{first_name}.{last_name}.{uuid.uuid4()}'
            print(f"Creating keycloak account for {username}")
            auth_user_dict = {
                "id": str(uuid.uuid4()),
                "username": username,
                "enabled": True,
                "email": hacker.email,
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
                url=f"{os.environ['KEYCLOAK_SERVER_URL']}/admin/realms/{os.getenv('KEYCLOAK_REALM', 'reality-hack-2024')}/users",
                headers={"Authorization": f"Bearer {access_token.json()['access_token']}", "Content-Type": "application/json"},
                data=json.dumps(auth_user_dict)
            )
            if authentication_account.ok:
                authentication_account_id = authentication_account.headers["Location"].split("/")[-1]
                hacker.authentication_id = authentication_account_id
                hacker.save()
                hacker.assign_authentication_roles()

                # send email with credentials
                subject, body = None, None
                if hacker.participation_class == Attendee.ParticipationClass.PARTICIPANT:
                    subject, body = email.get_hacker_rsvp_confirmation_template(hacker.first_name, temporary_password)
                else:
                    subject, body = email.get_non_hacker_rsvp_confirmation_template(hacker.first_name, temporary_password)

                send_mail(
                    subject,
                    body,
                    "no-reply@mitrealityhack.com",
                    [hacker.email],
                    fail_silently=False,
                )
            else:
                print(f"Error creating keycloak account for {hacker.email}")
                pprint.pprint(auth_user_dict)
                pprint.pprint(authentication_account.json())
