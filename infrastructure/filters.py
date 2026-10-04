"""
Custom FilterSet classes for event-scoped models.

This module provides FilterSet classes that properly handle event scoping
for Django Filter integration with DRF ViewSets.
"""

from django_filters import rest_framework as filters
from infrastructure import event_context
from infrastructure.models import (
    Application,
    Hardware,
    HardwareDevice,
    HardwareRequest,
    Location,
    MentorHelpRequest,
    ParticipationCapacity,
    ParticipationClass,
    ParticipationRole,
    Project,
    Table,
    Team,
    Workshop,
    WorkshopAttendee,
)


class TeamFilter(filters.FilterSet):
    """Filter for Team model with event-scoped Table queryset."""

    table = filters.ModelChoiceFilter(
        field_name='table',
        queryset=None  # Set dynamically
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = event_context.get_current_event()
        if event:
            self.filters['table'].queryset = (
                Table.objects.for_event(event)
            )
        else:
            self.filters['table'].queryset = Table.objects.all_events()

    class Meta:
        model = Team
        fields = ['name', 'attendees', 'table', 'table__number']


class MentorHelpRequestFilter(filters.FilterSet):
    """Filter for MentorHelpRequest with event-scoped Team queryset."""

    team = filters.ModelChoiceFilter(
        field_name='team',
        queryset=None  # Set dynamically
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = event_context.get_current_event()
        if event:
            self.filters['team'].queryset = Team.objects.for_event(event)
        else:
            self.filters['team'].queryset = Team.objects.all_events()

    class Meta:
        model = MentorHelpRequest
        fields = [
            'reporter', 'mentor', 'team', 'status', 'team__table__number'
        ]


class ProjectFilter(filters.FilterSet):
    """Filter for Project model with event-scoped Team queryset."""

    team = filters.ModelChoiceFilter(
        field_name='team',
        queryset=None  # Set dynamically
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = event_context.get_current_event()
        if event:
            self.filters['team'].queryset = Team.objects.for_event(event)
        else:
            self.filters['team'].queryset = Team.objects.all_events()

    class Meta:
        model = Project
        fields = ['team']


class HardwareDeviceFilter(filters.FilterSet):
    """Filter for HardwareDevice with event-scoped querysets."""

    hardware = filters.ModelChoiceFilter(
        field_name='hardware',
        queryset=None  # Set dynamically
    )
    checked_out_to = filters.ModelChoiceFilter(
        field_name='checked_out_to',
        queryset=None  # Set dynamically
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = event_context.get_current_event()
        if event:
            self.filters['hardware'].queryset = (
                Hardware.objects.for_event(event)
            )
            self.filters['checked_out_to'].queryset = (
                HardwareRequest.objects.for_event(event)
            )
        else:
            self.filters['hardware'].queryset = (
                Hardware.objects.all_events()
            )
            self.filters['checked_out_to'].queryset = (
                HardwareRequest.objects.all_events()
            )

    class Meta:
        model = HardwareDevice
        fields = [
            'hardware', 'checked_out_to', 'serial',
            'hardware__relates_to_destiny_hardware'
        ]


class HardwareDeviceHistoryFilter(filters.FilterSet):
    """Filter for historical HardwareDevice rows with event-scoped FK querysets."""

    hardware = filters.ModelChoiceFilter(
        field_name='hardware',
        queryset=None,
    )
    checked_out_to = filters.ModelChoiceFilter(
        field_name='checked_out_to',
        queryset=None,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = event_context.get_current_event()
        if event:
            self.filters['hardware'].queryset = Hardware.objects.for_event(event)
            self.filters['checked_out_to'].queryset = (
                HardwareRequest.objects.for_event(event)
            )
        else:
            self.filters['hardware'].queryset = Hardware.objects.all_events()
            self.filters['checked_out_to'].queryset = (
                HardwareRequest.objects.all_events()
            )

    class Meta:
        model = HardwareDevice.history.model
        fields = ['hardware', 'checked_out_to', 'serial', 'id']


class HardwareRequestFilter(filters.FilterSet):
    """Filter for HardwareRequest with event-scoped querysets."""

    hardware = filters.ModelChoiceFilter(
        field_name='hardware',
        queryset=None  # Set dynamically
    )
    team = filters.ModelChoiceFilter(
        field_name='team',
        queryset=None  # Set dynamically
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = event_context.get_current_event()
        if event:
            self.filters['hardware'].queryset = (
                Hardware.objects.for_event(event)
            )
            self.filters['team'].queryset = Team.objects.for_event(event)
            self.filters['hardware_device'].queryset = (
                HardwareDevice.objects.for_event(event)
            )
        else:
            self.filters['hardware'].queryset = (
                Hardware.objects.all_events()
            )
            self.filters['team'].queryset = Team.objects.all_events()
            self.filters['hardware_device'].queryset = (
                HardwareDevice.objects.all_events()
            )

    class Meta:
        model = HardwareRequest
        fields = [
            "hardware", "requester__first_name", "requester__last_name",
            "requester__id", "team", "hardware_device", "status"
        ]


class WorkshopFilter(filters.FilterSet):
    """Filter for Workshop with event-scoped Location and Hardware querysets."""

    location = filters.ModelChoiceFilter(
        field_name='location',
        queryset=None  # Set dynamically
    )
    hardware = filters.ModelMultipleChoiceFilter(
        field_name='hardware',
        queryset=None  # Set dynamically
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = event_context.get_current_event()
        if event:
            self.filters['location'].queryset = (
                Location.objects.for_event(event)
            )
            self.filters['hardware'].queryset = (
                Hardware.objects.for_event(event)
            )
        else:
            self.filters['location'].queryset = (
                Location.objects.all_events()
            )
            self.filters['hardware'].queryset = (
                Hardware.objects.all_events()
            )

    class Meta:
        model = Workshop
        fields = ['datetime', 'location', 'recommended_for', 'hardware']


class ApplicationFilterSet(filters.FilterSet):
    """Filter for Application with choice, multi-choice, and boolean filters."""

    participation_capacity = filters.ChoiceFilter(
        field_name='participation_capacity',
        choices=ParticipationCapacity.choices,
    )
    participation_role = filters.ChoiceFilter(
        field_name='participation_role',
        choices=ParticipationRole.choices,
    )
    email = filters.CharFilter(field_name='email', lookup_expr='exact')
    participation_class = filters.ChoiceFilter(
        field_name='participation_class',
        choices=ParticipationClass.choices,
    )
    participation_classes = filters.MultipleChoiceFilter(
        field_name='participation_class',
        choices=ParticipationClass.choices,
        method='filter_participation_classes',
    )
    status = filters.ChoiceFilter(
        field_name='status',
        choices=Application.Status.choices,
    )
    statuses = filters.MultipleChoiceFilter(
        field_name='status',
        choices=Application.Status.choices,
        method='filter_statuses',
    )
    rsvp_unsent = filters.BooleanFilter(method='filter_rsvp_unsent')
    has_rsvp = filters.BooleanFilter(method='filter_has_rsvp')

    class Meta:
        model = Application
        fields = [
            'participation_capacity',
            'participation_role',
            'email',
            'participation_class',
            'participation_classes',
            'status',
            'statuses',
            'rsvp_unsent',
            'has_rsvp',
        ]

    def filter_participation_classes(self, queryset, name, value):
        # Empty list means no filter — return all
        if not value:
            return queryset
        return queryset.filter(participation_class__in=value)

    def filter_statuses(self, queryset, name, value):
        if not value:
            return queryset
        return queryset.filter(status__in=value)

    def filter_rsvp_unsent(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.filter(rsvp_email_sent_at__isnull=value)

    def filter_has_rsvp(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.filter(eventrsvp__isnull=not value)


class WorkshopAttendeeFilter(filters.FilterSet):
    """Filter for WorkshopAttendee with event-scoped Workshop queryset."""

    workshop = filters.ModelChoiceFilter(
        field_name='workshop',
        queryset=None  # Set dynamically
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = event_context.get_current_event()
        if event:
            self.filters['workshop'].queryset = (
                Workshop.objects.for_event(event)
            )
        else:
            self.filters['workshop'].queryset = (
                Workshop.objects.all_events()
            )

    class Meta:
        model = WorkshopAttendee
        fields = ['workshop', 'attendee', 'participation']
