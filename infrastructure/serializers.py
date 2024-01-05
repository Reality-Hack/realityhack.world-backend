import pycountry
from django.contrib.auth.models import Group
from rest_framework import fields, serializers

from infrastructure import models
from infrastructure.models import (INDUSTRIES, SPOKEN_LANGUAGES, Application,
                                   Attendee, Hardware, HardwareDevice,
                                   HelpDesk, Location, ParticipationRole,
                                   Project, Skill, SkillProficiency, Table,
                                   Team, UploadedFile, Workshop,
                                   WorkshopAttendee)


class GroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = Group
        fields = ['id', 'name']


class GroupDetailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Group
        fields = ['id', 'name', 'permissions']


class FileUploadSerializer(serializers.ModelSerializer):

    class Meta:
        model = UploadedFile
        fields = "__all__"


class ApplicationSerializer(serializers.ModelSerializer):
    gender_identity = fields.MultipleChoiceField(choices=Application.GENDER_IDENTITIES)
    nationality = fields.MultipleChoiceField(choices=[(x.alpha_2, x.name) for x in pycountry.countries])
    current_country = fields.MultipleChoiceField(choices=[(x.alpha_2, x.name) for x in pycountry.countries])
    race_ethnic_group = fields.MultipleChoiceField(choices=Application.RACE_ETHNIC_GROUPS)
    disabilities = fields.MultipleChoiceField(choices=Application.DISABILITIES)
    previous_participation = fields.MultipleChoiceField(choices=Application.PREVIOUS_PARTICIPATION)
    heard_about_us = fields.MultipleChoiceField(choices=Application.HeardAboutUs.choices)
    digital_designer_skills = fields.MultipleChoiceField(choices=Application.DigitalDesignerProficientSkills.choices)
    industry = fields.MultipleChoiceField(choices=INDUSTRIES)

    class Meta:
        model = Application
        fields = "__all__"


class AttendeeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name', 'participation_role',
                  'profile_image', 'initial_setup',
                  'communications_platform_username', 'email',
                  'sponsor_company',  'participation_class', 'initial_setup', 'profile_image',
                  'created_at', 'updated_at']


class AttendeeRSVPCreateSerializer(serializers.ModelSerializer):
    dietary_restrictions = fields.MultipleChoiceField(choices=models.DietaryRestrictions.choices)
    dietary_allergies = fields.MultipleChoiceField(choices=models.DietaryAllergies.choices)

    class Meta:
        model = Attendee
        fields = [
            "id", "first_name", "last_name",
            'profile_image',
            "application", "bio", "email", "shirt_size", "communications_platform_username",
            "dietary_restrictions", "dietary_restrictions_other",
            "dietary_allergies", "dietary_allergies_other",
            "additional_accommodations",
            "us_visa_support_is_required",  "us_visa_letter_of_invitation_required",
            "us_visa_support_full_name", "us_visa_support_document_number",
            "us_visa_support_national_identification_document_type",
            "us_visa_support_citizenship", "us_visa_support_address",
            "under_18_by_date", "parental_consent_form_signed",
            "agree_to_media_release", "agree_to_liability_release", "agree_to_rules_code_of_conduct",
            "emergency_contact_name", "personal_phone_number",
            "emergency_contact_phone_number", "emergency_contact_email",
            "emergency_contact_relationship",
            "special_track_snapdragon_spaces_interest",
            "special_track_future_constructors_interest",
            "app_in_store", "currently_build_for_xr", "currently_use_xr",
            "non_xr_talents", "ar_vr_ap_in_store",
            "reality_hack_project_to_product",
            "participation_class", "sponsor_company"
        ]


class AttendeeRSVPSerializer(serializers.ModelSerializer):
    dietary_restrictions = fields.MultipleChoiceField(choices=models.DietaryRestrictions.choices)
    dietary_allergies = fields.MultipleChoiceField(choices=models.DietaryAllergies.choices)

    class Meta:
        model = Attendee
        fields = [
            "id", "first_name", "last_name", "participation_role",
            "profile_image", "initial_setup",
            "application", "bio", "email", "shirt_size", "communications_platform_username",
            "dietary_restrictions", "dietary_restrictions_other",
            "dietary_allergies", "dietary_allergies_other",
            "additional_accommodations",
            "us_visa_support_is_required",  "us_visa_letter_of_invitation_required",
            "us_visa_support_full_name", "us_visa_support_document_number",
            "us_visa_support_national_identification_document_type",
            "us_visa_support_citizenship", "us_visa_support_address",
            "under_18_by_date", "parental_consent_form_signed",
            "agree_to_media_release", "agree_to_liability_release", "agree_to_rules_code_of_conduct",
            "emergency_contact_name", "personal_phone_number",
            "emergency_contact_phone_number", "emergency_contact_email",
            "emergency_contact_relationship",
            "special_track_snapdragon_spaces_interest",
            "special_track_future_constructors_interest",
            "app_in_store", "currently_build_for_xr", "currently_use_xr",
            "non_xr_talents", "ar_vr_ap_in_store",
            "reality_hack_project_to_product",
            "participation_class", "sponsor_company"
        ]


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name']


class SkillProficiencyDetailSerializer(serializers.ModelSerializer):
    attendee = AttendeeSerializer()
    skill = SkillSerializer()

    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency', 'attendee',
                  'created_at', 'updated_at']


class SkillProficiencySerializer(serializers.ModelSerializer):
    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency', 'attendee',
                  'created_at', 'updated_at']


class SkillProficiencyCreateSerializer(serializers.ModelSerializer):

    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency', 'attendee']


class SkillProficiencyAttendeeSerializer(serializers.ModelSerializer):
    skill = SkillSerializer()

    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency']


class AttendeeDetailSerializer(serializers.ModelSerializer):
    skill_proficiencies = SkillProficiencyAttendeeSerializer(many=True)
    profile_image = FileUploadSerializer()

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name', 'skill_proficiencies',
                  'profile_image', 'bio',
                  'communications_platform_username', 'email',
                  'sponsor_company',  'participation_class', 'initial_setup', 'profile_image',
                  'created_at', 'updated_at']


class AttendeePatchSerializer(serializers.ModelSerializer):
    skill_proficiencies = SkillProficiencyAttendeeSerializer(many=True)

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name', 'skill_proficiencies',
                  'profile_image',
                  'communications_platform_username', 'email',
                  'sponsor_company',  'participation_class', 'initial_setup', 'profile_image',
                  'created_at', 'updated_at']


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'building', 'room',
                  'created_at', 'updated_at']


class TableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'number', 'location', 'created_at', 'updated_at']


class TableTruncatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id']


class TableDetailSerializer(serializers.ModelSerializer):
    location = LocationSerializer()

    class Meta:
        model = Table
        fields = ['id', 'number', 'location', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'repository_location', 'submission_location',
                  'team', 'created_at', 'updated_at']


class HelpDeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpDesk
        fields = ['id', 'table', 'ip_address', 'mentor_requested',
                  'announcement_pending']


class TeamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table', 'created_at', 'updated_at']


class TeamProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'repository_location', 'submission_location',
                  'created_at', 'updated_at']


class TeamHelpDeskSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpDesk
        fields = ['id', 'announcement_pending', 'mentor_requested',
                  'created_at', 'updated_at']


class TeamDetailSerializer(serializers.ModelSerializer):
    table = TableDetailSerializer()
    attendees = AttendeeSerializer(many=True)
    project = TeamProjectSerializer()
    help_desk = TeamHelpDeskSerializer()

    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table', 'project', 'help_desk',
                  'created_at', 'updated_at']


class TeamCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table']


class TableDetailSerializer(serializers.ModelSerializer):
    team = TeamSerializer()
    help_desk = HelpDeskSerializer()

    class Meta:
        model = Table
        fields = ['id', 'number', 'location', 'team', 'help_desk',
                  'created_at', 'updated_at']


class TableCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Table
        fields = ['id', 'number', 'location']


class MentorRequestSerializer(serializers.Serializer):
    table = serializers.IntegerField()


class HelpDesksSerializer(serializers.ModelSerializer):
    class Meta:
        model = HelpDesk
        fields = ['id', 'table', 'ip_address', 'announcement_pending',
                  'mentor_requested', 'auxiliary_requested',
                  'created_at', 'updated_at']


class HardwareCountSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField()
    checked_out = serializers.IntegerField()
    total = serializers.IntegerField()

    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image',
                  'available', 'checked_out', 'total',
                  'created_at', 'updated_at']


class HardwareDeviceHardwareCountDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareDevice
        fields = ['id', 'serial', 'checked_out_to',
                  'created_at', 'updated_at']


class HardwareCountDetailSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField()
    checked_out = serializers.IntegerField()
    total = serializers.IntegerField()
    hardware_devices = HardwareDeviceHardwareCountDetailSerializer(many=True)

    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image',
                  'available', 'checked_out', 'total',
                  'created_at', 'updated_at', 'hardware_devices']


class HardwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image',
                  'created_at', 'updated_at']


class HardwareDeviceHardwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hardware
        fields = ['id', 'name']


class HardwareDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareDevice
        fields = ['id', 'hardware', 'serial', 'checked_out_to',
                  'created_at', 'updated_at']
 

class HardwareDeviceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareDevice.history.model
        fields = ['history_id', 'id', 'hardware', 'serial', 'checked_out_to',
                  'created_at', 'updated_at']


class HardwareDeviceDetailSerializer(serializers.ModelSerializer):
    hardware = HardwareDeviceHardwareSerializer(read_only=True)
    checked_out_to = AttendeeSerializer(read_only=True)

    class Meta:
        model = HardwareDevice
        fields = ['id', 'hardware', 'serial', 'checked_out_to',
                  'created_at', 'updated_at']


class WorkshopSerializer(serializers.ModelSerializer):
    recommended_for = fields.MultipleChoiceField(choices=ParticipationRole.choices)

    class Meta:
        model = Workshop
        fields = "__all__"


class WorkshopAttendeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkshopAttendee
        fields = "__all__"
