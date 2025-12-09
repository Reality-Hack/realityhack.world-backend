import pycountry
from django.contrib.auth.models import Group
from rest_framework import fields, serializers
from drf_spectacular.utils import extend_schema_field
from infrastructure import models, event_context
from infrastructure.models import (INDUSTRIES, MENTOR_HELP_REQUEST_TOPICS,
                                   Application, Attendee, ApplicationQuestion,
                                   ApplicationQuestionChoice, ApplicationResponse,
                                   AttendeePreference, DestinyHardware,
                                   DestinyTeam, DestinyTeamAttendeeVibe,
                                   Hardware, HardwareDevice, HardwareRequest,
                                   HardwareTags, LightHouse, Location,
                                   MentorHelpRequest, ParticipationRole,
                                   Project, Skill, SkillProficiency, Table,
                                   Team, Track, UploadedFile, Workshop,
                                   WorkshopAttendee, Event, EventRsvp)


class EventScopedSerializer(serializers.ModelSerializer):
    """
    Base serializer that automatically scopes foreign key fields to the current event.

    This serializer ensures that when validating foreign key relationships,
    only objects from the current event are considered valid. This is crucial
    for maintaining proper event isolation in the multi-tenant system.

    Usage:
        class MySerializer(EventScopedSerializer):
            class Meta:
                model = MyModel
                fields = ['id', 'name', 'foreign_key_field']
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = event_context.get_current_event()

        # Auto-scope fields that have EventScopedManager
        for field_name, field in self.fields.items():
            if isinstance(
                field,
                (
                    serializers.PrimaryKeyRelatedField,
                    serializers.SlugRelatedField,
                ),
            ):
                queryset = field.queryset
                # Check if the queryset has event scoping methods
                if queryset is not None and hasattr(queryset, 'for_event'):
                    if event:
                        field.queryset = queryset.for_event(event)
                    else:
                        # Fallback: allow all events (for admin use or testing without event)
                        field.queryset = queryset.all_events()


class GroupSerializer(serializers.ModelSerializer):

    class Meta:
        model = Group
        fields = ['id', 'name']


class GroupDetailSerializer(serializers.ModelSerializer):
    # TODO: finish implementing cache refresh for file uploads
    class Meta:
        model = Group
        # remove after change
        fields = ['id', 'name', 'permissions']


class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = "__all__"
    #     fields = ['id', 'file', 'uri', 'claimed', 'expires_at']
    #     read_only_fields = ['uri', 'expires_at']

    # def to_representation(self, instance):
    #     data = super().to_representation(instance)
    #     if instance.is_expired():
    #         instance.refresh_uri()
    #         data['uri'] = instance.uri
    #         data['expires_at'] = instance.expires_at
    #     return data


class ApplicationSerializer(EventScopedSerializer):
    gender_identity = fields.MultipleChoiceField(
        choices=Application.GenderIdentities.choices,
    )
    nationality = fields.MultipleChoiceField(
        choices=[(x.alpha_2, x.name) for x in pycountry.countries],
    )
    current_country = fields.MultipleChoiceField(
        choices=[(x.alpha_2, x.name) for x in pycountry.countries]
    )
    race_ethnic_group = fields.MultipleChoiceField(
        choices=Application.RaceEthnicGroups.choices,
    )
    previous_participation = fields.MultipleChoiceField(
        choices=Application.PreviousParticipation.choices,
    )
    heard_about_us = fields.MultipleChoiceField(
        choices=Application.HeardAboutUs.choices,
    )
    digital_designer_skills = fields.MultipleChoiceField(
        choices=Application.DigitalDesignerProficientSkills.choices,
    )
    age_group = fields.ChoiceField(
        choices=Application.AgeGroup.choices,
    )
    industry = fields.MultipleChoiceField(choices=INDUSTRIES)

    class Meta:
        model = Application
        fields = "__all__"


class ApplicationQuestionChoiceSerializer(serializers.ModelSerializer):
    """Serializer for question choices"""
    class Meta:
        model = ApplicationQuestionChoice
        fields = ['id', 'choice_key', 'choice_text', 'order']


class ApplicationQuestionSerializer(EventScopedSerializer):
    """Serializer for application questions with nested choices"""
    choices = ApplicationQuestionChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = ApplicationQuestion
        fields = [
            'id', 'question_key', 'question_text', 'question_type',
            'order', 'required', 'parent_question', 'trigger_choices',
            'choices', 'max_length', 'min_length',
            'placeholder_text', 'created_at', 'updated_at'
        ]


class ApplicationResponseSerializer(serializers.ModelSerializer):
    """Serializer for application responses with snapshots"""
    selected_choice_keys = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationResponse
        fields = [
            'id', 'question', 'question_text_snapshot',
            'choices_snapshot', 'selected_keys_snapshot',
            'selected_choice_keys',
            'text_response',
            'text_response_snapshot',
            'created_at', 'updated_at'
        ]

    @extend_schema_field(serializers.ListField(child=serializers.CharField()))
    def get_selected_choice_keys(self, obj):
        """Get the selected choice keys (for convenience)"""
        return obj.selected_keys_snapshot

    def validate(self, data):
        """Validate based on question type"""
        question = data.get('question')

        if question.question_type in ['T', 'L']:
            # Text question validation
            if not data.get('text_response') and question.required:
                raise serializers.ValidationError(
                    "Text response is required for this question"
                )
            if data.get('selected_choices'):
                raise serializers.ValidationError(
                    "Choice selection not allowed for text questions"
                )
        else:
            # Choice question validation
            if data.get('text_response'):
                raise serializers.ValidationError(
                    "Text response not allowed for choice questions"
                )

        return data


class ApplicationDetailSerializer(EventScopedSerializer):
    """Detailed application serializer with question responses"""
    gender_identity = fields.MultipleChoiceField(
        choices=Application.GenderIdentities.choices,
    )
    nationality = fields.MultipleChoiceField(
        choices=[(x.alpha_2, x.name) for x in pycountry.countries],
    )
    current_country = fields.MultipleChoiceField(
        choices=[(x.alpha_2, x.name) for x in pycountry.countries],
    )
    race_ethnic_group = fields.MultipleChoiceField(choices=Application.RaceEthnicGroups)
    previous_participation = fields.MultipleChoiceField(
        choices=Application.PreviousParticipation,
    )
    heard_about_us = fields.MultipleChoiceField(
        choices=Application.HeardAboutUs.choices,
    )
    digital_designer_skills = fields.MultipleChoiceField(
        choices=Application.DigitalDesignerProficientSkills.choices,
    )
    industry = fields.MultipleChoiceField(choices=INDUSTRIES)
    hardware_hack_detail = fields.MultipleChoiceField(
        choices=Application.HardwareHackDetail.choices,
    )
    question_responses = ApplicationResponseSerializer(many=True, read_only=True)

    class Meta:
        model = Application
        fields = "__all__"


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = "__all__"


class AttendeeSerializer(serializers.ModelSerializer):
    intended_tracks = fields.MultipleChoiceField(choices=Track.choices)
    prefers_destiny_hardware = fields.MultipleChoiceField(choices=DestinyHardware.choices)

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name', 'participation_role', 'checked_in_at',
                  'profile_image', 'initial_setup', 'guardian_of', 'sponsor_handler', 'prefers_destiny_hardware',
                  'communications_platform_username', 'email', 'intended_tracks', 'intended_hardware_hack',
                  'sponsor_company',  'participation_class', 'initial_setup', 'profile_image',
                  'created_at', 'updated_at']


class AttendeeListSerializer(serializers.ModelSerializer):
    intended_tracks = fields.MultipleChoiceField(choices=Track.choices)
    prefers_destiny_hardware = fields.MultipleChoiceField(choices=DestinyHardware.choices)

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name', 'participation_role', 'checked_in_at',
                  'profile_image', 'initial_setup', 'guardian_of', 'sponsor_handler', 'prefers_destiny_hardware',
                  'communications_platform_username', 'intended_tracks', 'intended_hardware_hack',
                  'sponsor_company',  'participation_class', 'initial_setup', 'profile_image',
                  'created_at', 'updated_at']


class DiscordUsernameRoleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Attendee
        fields = ['communications_platform_username', 'participation_role', 'participation_class']


class AttendeeRSVPCreateSerializer(EventScopedSerializer):
    dietary_restrictions = fields.MultipleChoiceField(choices=models.DietaryRestrictions.choices)
    dietary_allergies = fields.MultipleChoiceField(choices=models.DietaryAllergies.choices)

    class Meta:
        model = Attendee
        fields = [
            "id", "first_name", "last_name", "participation_role",
            'profile_image', "authentication_id",
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
            "special_interest_track_one",
            "special_interest_track_two",
            "app_in_store", "currently_build_for_xr", "currently_use_xr",
            "non_xr_talents", "ar_vr_ap_in_store",
            "reality_hack_project_to_product",
            "participation_class", "sponsor_company",
            "breakthrough_hacks_interest",
            "loaner_headset_preference"
        ]


class AttendeeRSVPSerializer(EventScopedSerializer):
    dietary_restrictions = fields.MultipleChoiceField(
        choices=models.DietaryRestrictions.choices,
    )
    dietary_allergies = fields.MultipleChoiceField(
        choices=models.DietaryAllergies.choices,
    )

    class Meta:
        model = Attendee
        fields = [
            "id", "first_name", "last_name", "participation_role",
            "profile_image", "initial_setup", 'guardian_of', 'sponsor_handler',
            "application", "bio", "email", "shirt_size",
            "dietary_restrictions", "dietary_restrictions_other",
            "dietary_allergies", "dietary_allergies_other",
            "additional_accommodations", 'checked_in_at',
            "us_visa_support_is_required",  "us_visa_letter_of_invitation_required",
            "us_visa_support_full_name", "us_visa_support_document_number",
            "us_visa_support_national_identification_document_type",
            "us_visa_support_citizenship", "us_visa_support_address",
            "under_18_by_date", "parental_consent_form_signed",
            "agree_to_media_release", "agree_to_liability_release",
            "emergency_contact_name", "personal_phone_number",
            "emergency_contact_phone_number", "emergency_contact_email",
            "emergency_contact_relationship",
            "special_interest_track_one",
            "special_interest_track_two",
            "breakthrough_hacks_interest", "agree_to_rules_code_of_conduct",
            "loaner_headset_preference", "communications_platform_username",
            "app_in_store", "currently_build_for_xr", "currently_use_xr",
            "non_xr_talents", "ar_vr_ap_in_store",
            "reality_hack_project_to_product",
            "participation_class", "sponsor_company"
        ]


class SkillSerializer(EventScopedSerializer):
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


class SkillProficiencySerializer(EventScopedSerializer):
    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency', 'attendee',
                  'created_at', 'updated_at']


class SkillProficiencyCreateSerializer(EventScopedSerializer):

    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency', 'attendee']


class SkillProficiencyAttendeeSerializer(serializers.ModelSerializer):
    skill = SkillSerializer()

    class Meta:
        model = SkillProficiency
        fields = ['id', 'skill', 'proficiency']


class LocationSerializer(EventScopedSerializer):
    class Meta:
        model = Location
        fields = ['id', 'building', 'room',
                  'created_at', 'updated_at']


class TableSerializer(EventScopedSerializer):
    is_claimed = serializers.SerializerMethodField()

    def get_is_claimed(self, obj) -> bool:
        return hasattr(obj, 'team') and obj.team is not None

    class Meta:
        model = Table
        fields = ['id', 'number', 'location', 'created_at', 'updated_at', 'is_claimed']


class TableTruncatedSerializer(EventScopedSerializer):
    class Meta:
        model = Table
        fields = ['id']


class TeamTableSerializer(serializers.ModelSerializer):
    location = LocationSerializer()

    class Meta:
        model = Table
        fields = ['id', 'number', 'location', 'created_at', 'updated_at']


class ProjectSerializer(EventScopedSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'repository_location', 'description', 'submission_location',
                  'team', 'created_at', 'updated_at', 'census_taker_name', 'census_location_override', 'team_primary_contact']


class LightHouseSerializer(EventScopedSerializer):
    table = serializers.IntegerField()

    class Meta:
        model = LightHouse
        fields = ['id', 'table', 'ip_address', 'mentor_requested',
                  'announcement_pending']


def serialize_lighthouse(lighthouse):
    return LightHouseSerializer({
            "id": lighthouse.id,
            "table": lighthouse.table.number,
            "ip_address": lighthouse.ip_address,
            "mentor_requested": lighthouse.mentor_requested,
            "announcement_pending": lighthouse.announcement_pending
        })


class MentorHelpRequestSerializer(EventScopedSerializer):
    topic = fields.MultipleChoiceField(choices=MENTOR_HELP_REQUEST_TOPICS)

    class Meta:
        model = MentorHelpRequest
        fields = ['id', 'title', 'description', 'team', 'category', 'topic',
                  'reporter', 'mentor', 'status', 'category_specialty', 'topic_other',
                  'created_at', 'updated_at', 'reporter_location']


class HelpRequestReporterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name']


class HelpRequestTeamLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'building', 'room']

class HelpRequestTableSerializer(serializers.ModelSerializer):
    location = HelpRequestTeamLocationSerializer()

    class Meta:
        model = Table
        fields = ['id', 'number', 'location']

class HelpRequestTeamSerializer(serializers.ModelSerializer):
    table = HelpRequestTableSerializer()

    class Meta:
        model = Team
        fields = ['id', 'name', 'table']

class MentorHelpRequestReadSerializer(MentorHelpRequestSerializer):
    team = HelpRequestTeamSerializer()
    reporter = HelpRequestReporterSerializer()



class MentorHelpRequestHistorySerializer(serializers.ModelSerializer):
    topic = fields.MultipleChoiceField(choices=MENTOR_HELP_REQUEST_TOPICS)

    class Meta:
        model = MentorHelpRequest.history.model
        fields = ['history_id', 'id', 'title', 'description', 'team', 'category', 'topic',
                  'reporter', 'mentor', 'status', 'category_specialty', 'topic_other',
                  'created_at', 'updated_at']


class AttendeeNameSerializer(serializers.ModelSerializer):
    profile_image = FileUploadSerializer(read_only=True)

    class Meta:
        model = Attendee
        fields = [
            'id', 'first_name', 'last_name', 'participation_role',
            'profile_image', "email"
        ]


class EventRsvpSerializer(EventScopedSerializer):
    application = ApplicationSerializer(read_only=True)
    attendee = AttendeeNameSerializer(read_only=True)

    dietary_restrictions = fields.MultipleChoiceField(
        choices=models.DietaryRestrictions.choices,
    )
    dietary_allergies = fields.MultipleChoiceField(
        choices=models.DietaryAllergies.choices
    )

    class Meta:
        model = EventRsvp
        fields = [
            "id", "participation_role", "event",
            "application", "shirt_size",
            "attendee", "application",
            "communication_platform_username",
            "dietary_restrictions", "dietary_restrictions_other",
            "dietary_allergies", "dietary_allergies_other",
            "additional_accommodations",
            "us_visa_support_is_required",  "us_visa_letter_of_invitation_required",
            "us_visa_support_full_name", "us_visa_support_document_number",
            "us_visa_support_national_identification_document_type",
            "us_visa_support_citizenship", "us_visa_support_address",
            "under_18_by_date", "parental_consent_form_signed",
            "agree_to_media_release", "agree_to_liability_release",
            "agree_to_rules_code_of_conduct",
            "emergency_contact_name", "personal_phone_number",
            "emergency_contact_phone_number", "emergency_contact_email",
            "emergency_contact_relationship",
            "special_interest_track_one",
            "special_interest_track_two",
            "app_in_store", "currently_build_for_xr", "currently_use_xr",
            "non_xr_talents", "ar_vr_ap_in_store",
            "reality_hack_project_to_product",
            "participation_class", "sponsor_company",
            "breakthrough_hacks_interest",
            "loaner_headset_preference"
        ]


class EventRsvpDetailSerializer(EventRsvpSerializer):

    attendee = AttendeeNameSerializer()

    class Meta:
        model = EventRsvp
        fields = EventRsvpSerializer.Meta.fields + [
            "created_at", "updated_at",
            "application", "attendee", "shirt_size",
            "communication_platform_username", "us_visa_support_is_required",
            "emergency_contact_name", "emergency_contact_phone_number",
            "special_interest_track_one", "special_interest_track_two", "under_18_by_date",
        ]


class TableNumberSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Table
        fields = ['id', 'number']


class TeamSerializer(EventScopedSerializer):
    class Meta:
        model = Team
        fields = ['id', 'number', 'name', 'attendees', 'table', 
                  'tracks', 'destiny_hardware', 'team_description', 
                  'created_at', 'updated_at']


class TeamProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'repository_location', 'submission_location',
                  'census_location_override', 'census_taker_name', 'team_primary_contact',
                  'description', 'created_at', 'updated_at']


class TeamLightHouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = LightHouse
        fields = ['id', 'announcement_pending', 'mentor_requested',
                  'created_at', 'updated_at']


class TeamDetailSerializer(serializers.ModelSerializer):
    table = TeamTableSerializer()
    project = TeamProjectSerializer()
    lighthouse = TeamLightHouseSerializer()
    attendees = AttendeeNameSerializer(many=True)

    class Meta:
        model = Team
        fields = ['id', 'number', 'name', 'attendees', 'table', 'hardware_hack',
                  'startup_hack', 'project', 'lighthouse', 'tracks', 'destiny_hardware',
                  'team_description','created_at', 'updated_at']


class TeamCreateSerializer(EventScopedSerializer):
    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table', 'team_description']
        
class TeamUpdateSerializer(EventScopedSerializer):
    table = TableSerializer(allow_null=True)
    project = ProjectSerializer()
    tracks = fields.MultipleChoiceField(choices=Track.choices)
    destiny_hardware = fields.MultipleChoiceField(choices=DestinyHardware.choices)

    class Meta:
        model = Team
        fields = ['id', 'name', 'attendees', 'table', 'team_description', 'tracks', 'destiny_hardware', 'project', 'hardware_hack', 'startup_hack']

class TableDetailSerializer(EventScopedSerializer):
    team = TeamSerializer()
    lighthouse = TeamLightHouseSerializer()

    class Meta:
        model = Table
        fields = ['id', 'number', 'location', 'team', 'lighthouse',
                  'created_at', 'updated_at']


class TableCreateSerializer(EventScopedSerializer):
    class Meta:
        model = Table
        fields = ['id', 'number', 'location']


class MentorRequestSerializer(serializers.Serializer):
    table = serializers.IntegerField()


class LightHousesSerializer(EventScopedSerializer):
    class Meta:
        model = LightHouse
        fields = ['id', 'table', 'ip_address', 'announcement_pending',
                  'mentor_requested', 'auxiliary_requested',
                  'created_at', 'updated_at']


class HardwareCountSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField()
    checked_out = serializers.IntegerField()
    total = serializers.IntegerField()
    image = FileUploadSerializer()
    tags = fields.MultipleChoiceField(choices=HardwareTags)

    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image',
                  'available', 'checked_out', 'total',
                  'created_at', 'updated_at', 'tags']


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
    image = FileUploadSerializer()
    tags = fields.MultipleChoiceField(choices=HardwareTags)


    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image',
                  'available', 'checked_out', 'total',
                  'created_at', 'updated_at', 'hardware_devices', 'tags']


class HardwareSerializer(EventScopedSerializer):
    image = FileUploadSerializer()
    tags = fields.MultipleChoiceField(choices=HardwareTags)
    
    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image', 'tags',
                  'relates_to_destiny_hardware',
                  'created_at', 'updated_at']


class HardwareCreateSerializer(EventScopedSerializer):
    tags = fields.MultipleChoiceField(choices=HardwareTags)
    
    class Meta:
        model = Hardware
        fields = ['id', 'name', 'description', 'image', 'tags', 'relates_to_destiny_hardware']


class HardwareDeviceHardwareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Hardware
        fields = ['id', 'name', 'tags']


class HardwareDeviceSerializer(EventScopedSerializer):
    class Meta:
        model = HardwareDevice
        fields = ['id', 'hardware', 'serial', 'checked_out_to',
                  'created_at', 'updated_at']
 

class HardwareDeviceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = HardwareDevice.history.model
        fields = ['history_id', 'id', 'hardware', 'serial', 'checked_out_to',
                  'created_at', 'updated_at']


class HardwareRequestSerializer(EventScopedSerializer):
    class Meta:
        model = HardwareRequest
        fields = ["id", "hardware", "hardware_device", "requester", "team", "reason", "status", "created_at", "updated_at"]


class HardwareRequestRequesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendee
        fields = ["id", "first_name", "last_name"]


class HardwareRequestListSerializer(serializers.ModelSerializer):
    requester = HardwareRequestRequesterSerializer()
    team = TeamSerializer()

    class Meta:
        model = HardwareRequest
        fields = ["id", "hardware", "hardware_device", "requester", "team", "reason", "status", "created_at", "updated_at"]


class HardwareDeviceDetailSerializer(serializers.ModelSerializer):
    hardware = HardwareDeviceHardwareSerializer(read_only=True)
    checked_out_to = HardwareRequestSerializer(read_only=True)

    class Meta:
        model = HardwareDevice
        fields = ['id', 'hardware', 'serial', 'checked_out_to',
                  'created_at', 'updated_at']


class HardwareRequestDetailSerializer(serializers.ModelSerializer):
    hardware = HardwareCountSerializer(read_only=True)
    hardware_device = HardwareDeviceDetailSerializer(read_only=True)
    requester = AttendeeSerializer(read_only=True)
    team = TeamSerializer()

    class Meta:
        model = HardwareRequest
        fields = ["id", "hardware", "hardware_device", "requester", "team", "reason", "status", "created_at", "updated_at"]


class HardwareRequestCreateSerializer(EventScopedSerializer):
    hardware = serializers.PrimaryKeyRelatedField(queryset=Hardware.objects.all())
    requester = serializers.SlugRelatedField(
        slug_field="email",
        queryset=Attendee.objects.all()
    )

    class Meta:
        model = HardwareRequest
        fields = ["id", "hardware", "hardware_device", "requester", "team", "reason", "status", "created_at", "updated_at"]


class WorkshopSerializer(EventScopedSerializer):
    recommended_for = fields.MultipleChoiceField(choices=ParticipationRole.choices)

    skills = serializers.SerializerMethodField()
    hardware = serializers.SerializerMethodField()

    class Meta:
        model = Workshop
        fields = "__all__"

    @extend_schema_field(serializers.ListField(child=serializers.IntegerField()))
    def get_skills(self, obj):
        """Get skill IDs from the workshop's existing relationships."""
        return list(Skill.objects.for_event(obj.event).filter(workshop_skills=obj).values_list('id', flat=True))

    @extend_schema_field(serializers.ListField(child=serializers.IntegerField()))
    def get_hardware(self, obj):
        """Get hardware IDs from the workshop's existing relationships."""
        return list(Hardware.objects.for_event(obj.event).filter(workshop_hardware=obj).values_list('id', flat=True))


class WorkshopAttendeeSerializer(EventScopedSerializer):
    class Meta:
        model = WorkshopAttendee
        fields = "__all__"


class WorkshopAttendeeWorkshopDetailSerializer(serializers.ModelSerializer):
    workshop = WorkshopSerializer()

    class Meta:
        model = WorkshopAttendee
        fields = ['id', 'workshop', 'participation', 'created_at', 'updated_at']


class AttendeeDetailSerializer(serializers.ModelSerializer):
    skill_proficiencies = SkillProficiencyAttendeeSerializer(many=True)
    profile_image = FileUploadSerializer()
    team = TeamSerializer()
    hardware_devices = HardwareDeviceDetailSerializer(many=True)
    workshops = WorkshopAttendeeWorkshopDetailSerializer(many=True)
    intended_tracks = fields.MultipleChoiceField(choices=Track.choices)
    prefers_destiny_hardware = fields.MultipleChoiceField(choices=DestinyHardware.choices)

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name', 'skill_proficiencies',
                  'profile_image', 'bio', 'checked_in_at', 'team', 'hardware_devices',
                  'communications_platform_username', 'email', 'workshops',
                  'sponsor_company',  'participation_class', 'initial_setup', 'prefers_destiny_hardware',
                  'guardian_of', 'sponsor_handler', 'intended_tracks', 'intended_hardware_hack',
                  'created_at', 'updated_at']


class AttendeePatchSerializer(serializers.ModelSerializer):
    intended_tracks = fields.MultipleChoiceField(choices=Track.choices)
    prefers_destiny_hardware = fields.MultipleChoiceField(choices=DestinyHardware.choices)

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name', 'authentication_id',
                  'profile_image', 'bio', 'checked_in_at', 'prefers_destiny_hardware',
                  'communications_platform_username', 'email', 'prefers_destiny_hardware',
                  'sponsor_company',  'participation_class', 'initial_setup',
                  'guardian_of', 'sponsor_handler', 'intended_tracks', 'intended_hardware_hack',
                  'created_at', 'updated_at']


class AttendeeUpdateSerializer(serializers.ModelSerializer):
    intended_tracks = fields.MultipleChoiceField(choices=Track.choices)
    prefers_destiny_hardware = fields.MultipleChoiceField(choices=DestinyHardware.choices)

    class Meta:
        model = Attendee
        fields = ['id', 'first_name', 'last_name',
                  'profile_image', 'bio', 'checked_in_at', 'prefers_destiny_hardware',
                  'communications_platform_username', 'email', 'prefers_destiny_hardware',
                  'sponsor_company',  'participation_class', 'initial_setup',
                  'guardian_of', 'sponsor_handler', 'intended_tracks', 'intended_hardware_hack',
                  'created_at', 'updated_at', 'authentication_id']


class AttendeePreferenceSerializer(EventScopedSerializer):

    class Meta:
        model = AttendeePreference
        fields = "__all__"


class DestinyTeamSerializer(EventScopedSerializer):
    attendees = AttendeeNameSerializer(many=True)
    table = TableNumberSerializer()

    class Meta:
        model = DestinyTeam
        fields = "__all__"


class DestinyTeamUpdateSerializer(EventScopedSerializer):
    table = TableNumberSerializer()

    class Meta:
        model = DestinyTeam
        fields = "__all__"


class DestinyTeamAttendeeVibeSerializer(EventScopedSerializer):

    class Meta:
        model = DestinyTeamAttendeeVibe
        fields = "__all__"
