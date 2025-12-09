from django.core.management.base import BaseCommand
from infrastructure.models import Attendee, EventRsvp, Event
import logging


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Migrate attendee event rsvp data to EventRsvp model"

    def handle(self, *args, **options):
        attendees = Attendee.objects.all()
        event_2025 = Event.objects.get(name="Reality Hack at MIT 2025")

        for attendee in attendees:
            try:
                discord_username = attendee.communications_platform_username
                visa_required = attendee.us_visa_letter_of_invitation_required
                visa_document_number = attendee.us_visa_support_document_number
                project_to_product = attendee.reality_hack_project_to_product
                id_type = attendee.us_visa_support_national_identification_document_type
                rules_cc = attendee.agree_to_rules_code_of_conduct
                emergency_phone = attendee.emergency_contact_phone_number
                emergency_rel = attendee.emergency_contact_relationship

                guardian_of = attendee.guardian_of
                sponsor_handler = attendee.sponsor_handler

                event_rsvp = EventRsvp.objects.create(
                    attendee=attendee,
                    event=event_2025,
                    status=attendee.status,
                    participation_class=attendee.participation_class,
                    sponsor_handler=sponsor_handler,
                    communications_platform_username=discord_username,
                    application=attendee.application,
                    participation_role=attendee.participation_role,
                    shirt_size=attendee.shirt_size,
                    intended_tracks=attendee.intended_tracks,
                    intended_hardware_hack=attendee.intended_hardware_hack,
                    prefers_destiny_hardware=attendee.prefers_destiny_hardware,
                    dietary_restrictions=attendee.dietary_restrictions,
                    dietary_restrictions_other=attendee.dietary_restrictions_other,
                    dietary_allergies=attendee.dietary_allergies,
                    dietary_allergies_other=attendee.dietary_allergies_other,
                    additional_accommodations=attendee.additional_accommodations,
                    us_visa_support_is_required=attendee.us_visa_support_is_required,
                    us_visa_letter_of_invitation_required=visa_required,
                    us_visa_support_full_name=attendee.us_visa_support_full_name,
                    us_visa_support_document_number=visa_document_number,
                    us_visa_support_national_identification_document_type=id_type,
                    us_visa_support_citizenship=attendee.us_visa_support_citizenship,
                    us_visa_support_address=attendee.us_visa_support_address,
                    under_18_by_date=attendee.under_18_by_date,
                    parental_consent_form_signed=attendee.parental_consent_form_signed,
                    agree_to_media_release=attendee.agree_to_media_release,
                    agree_to_liability_release=attendee.agree_to_liability_release,
                    agree_to_rules_code_of_conduct=rules_cc,
                    emergency_contact_name=attendee.emergency_contact_name,
                    personal_phone_number=attendee.personal_phone_number,
                    emergency_contact_phone_number=emergency_phone,
                    emergency_contact_email=attendee.emergency_contact_email,
                    emergency_contact_relationship=emergency_rel,
                    app_in_store=attendee.app_in_store,
                    currently_build_for_xr=attendee.currently_build_for_xr,
                    currently_use_xr=attendee.currently_use_xr,
                    non_xr_talents=attendee.non_xr_talents,
                    ar_vr_ap_in_store=attendee.ar_vr_ap_in_store,
                    reality_hack_project_to_product=project_to_product,
                    sponsor_company=attendee.sponsor_company,
                    breakthrough_hacks_interest=attendee.breakthrough_hacks_interest,
                    loaner_headset_preference=attendee.loaner_headset_preference,
                )

                if guardian_of:
                    event_rsvp.guardian_of.set(guardian_of.all())

                event_rsvp.save()
                logger.info(f"Migrated attendee {attendee.email} event rsvp data")
            except Exception as e:
                logger.error(
                    f"Error migrating attendee {attendee.email}: {e}"
                )
                continue
