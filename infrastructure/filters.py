"""
Custom FilterSet classes for event-scoped models.

This module provides FilterSet classes that properly handle event scoping
for Django Filter integration with DRF ViewSets.
"""

from django_filters import rest_framework as filters
from infrastructure import event_context
from infrastructure.models import (
    Hardware,
    HardwareDevice,
    HardwareRequest,
    Location,
    MentorHelpRequest,
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
        else:
            self.filters['hardware'].queryset = (
                Hardware.objects.all_events()
            )
            self.filters['team'].queryset = Team.objects.all_events()

    class Meta:
        model = HardwareRequest
        fields = [
            "hardware", "requester__first_name", "requester__last_name",
            "requester__id", "team"
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
