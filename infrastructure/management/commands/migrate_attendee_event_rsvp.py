from django.core.management.base import BaseCommand
import logging

logger = logging.getLogger(__name__)

EVENT_2025_UUID = '888a5508-ea40-4453-84bc-a0e4a03e491b'


def _attendee_models(apps=None):
    if apps is not None:
        return (
            apps.get_model('infrastructure', 'Attendee'),
            apps.get_model('infrastructure', 'EventRsvp'),
            apps.get_model('infrastructure', 'Event'),
        )
    from infrastructure.models import Attendee, EventRsvp, Event

    return Attendee, EventRsvp, Event


def _resolve_event_2025(Event, apps=None):
    if apps is not None:
        return Event.objects.get(id=EVENT_2025_UUID)
    return Event.objects.get(name='Reality Hack at MIT 2025')


def run_attendee_event_rsvp_migration(apps=None) -> None:
    """Migrate attendee RSVP columns into EventRsvp for the 2025 event."""
    Attendee, EventRsvp, Event = _attendee_models(apps)
    event_2025 = _resolve_event_2025(Event, apps=apps)

    for attendee in Attendee.objects.all():
        try:
            event_rsvp = EventRsvp.objects.create(
                attendee=attendee,
                event=event_2025,
                status=attendee.status,
                participation_class=attendee.participation_class,
                sponsor_handler=attendee.sponsor_handler,
                communications_platform_username=attendee.communications_platform_username,
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
                us_visa_letter_of_invitation_required=attendee.us_visa_letter_of_invitation_required,
                us_visa_support_full_name=attendee.us_visa_support_full_name,
                us_visa_support_document_number=attendee.us_visa_support_document_number,
                us_visa_support_national_identification_document_type=(
                    attendee.us_visa_support_national_identification_document_type
                ),
                us_visa_support_citizenship=attendee.us_visa_support_citizenship,
                us_visa_support_address=attendee.us_visa_support_address,
                under_18_by_date=attendee.under_18_by_date,
                parental_consent_form_signed=attendee.parental_consent_form_signed,
                agree_to_media_release=attendee.agree_to_media_release,
                agree_to_liability_release=attendee.agree_to_liability_release,
                agree_to_rules_code_of_conduct=attendee.agree_to_rules_code_of_conduct,
                emergency_contact_name=attendee.emergency_contact_name,
                personal_phone_number=attendee.personal_phone_number,
                emergency_contact_phone_number=attendee.emergency_contact_phone_number,
                emergency_contact_email=attendee.emergency_contact_email,
                emergency_contact_relationship=attendee.emergency_contact_relationship,
                app_in_store=attendee.app_in_store,
                currently_build_for_xr=attendee.currently_build_for_xr,
                currently_use_xr=attendee.currently_use_xr,
                non_xr_talents=attendee.non_xr_talents,
                ar_vr_ap_in_store=attendee.ar_vr_ap_in_store,
                reality_hack_project_to_product=attendee.reality_hack_project_to_product,
                sponsor_company=attendee.sponsor_company,
                breakthrough_hacks_interest=attendee.breakthrough_hacks_interest,
                loaner_headset_preference=attendee.loaner_headset_preference,
            )

            guardian_of = attendee.guardian_of.all()
            if guardian_of:
                event_rsvp.guardian_of.set(guardian_of)

            event_rsvp.save()
            logger.info('Migrated attendee %s event rsvp data', attendee.email)
        except Exception as e:
            logger.error('Error migrating attendee %s: %s', attendee.email, e)
            continue


class Command(BaseCommand):
    help = 'Migrate attendee event rsvp data to EventRsvp model'

    def handle(self, *args, **options):
        run_attendee_event_rsvp_migration()
