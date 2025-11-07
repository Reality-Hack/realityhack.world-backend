"""
Custom managers and querysets for event-scoped models.

This module provides the infrastructure for multi-tenant event scoping,
ensuring that queries are properly filtered by event to maintain data isolation.
"""

from django.db import models


class EventScopingError(Exception):
    """Raised when a query is executed without proper event scoping"""
    pass


class EventScopedQuerySet(models.QuerySet):
    """
    Custom QuerySet that enforces event scoping on all queries.

    Queries must explicitly call .for_event(event) or .all_events() before
    execution, otherwise an EventScopingError will be raised.

    Usage:
        # Scoped to a specific event
        Team.objects.for_event(event).all()

        # Explicitly query across all events (admin only)
        Team.objects.all_events().count()
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._is_event_scoped = False

    def for_event(self, event):
        """
        Filter queryset to a specific event and mark as properly scoped.

        Args:
            event: Event instance or event ID to filter by

        Returns:
            EventScopedQuerySet filtered to the specified event
        """
        qs = self.filter(event=event)
        qs._is_event_scoped = True
        return qs

    def all_events(self):
        """
        Explicitly bypass event scoping for cross-event queries.

        This should only be used for administrative operations, analytics,
        or other legitimate cross-event use cases.

        Returns:
            EventScopedQuerySet marked as properly scoped but not filtered
        """
        qs = self._clone()
        qs._is_event_scoped = True
        return qs

    def _fetch_all(self):
        """
        Override _fetch_all to enforce event scoping before query execution.

        Raises:
            EventScopingError: If query is executed without .for_event()
                               or .all_events()
        """
        if not self._is_event_scoped and self._result_cache is None:
            raise EventScopingError(
                f"Query on {self.model.__name__} must use .for_event(event) "
                f"or .all_events() before execution. This ensures proper event "
                f"isolation in the multi-tenant system."
            )
        super()._fetch_all()

    def _clone(self):
        """
        Override _clone to preserve event scoping state in cloned querysets.
        """
        clone = super()._clone()
        clone._is_event_scoped = self._is_event_scoped
        return clone


class EventScopedManager(models.Manager):
    """
    Custom Manager that uses EventScopedQuerySet as its base queryset.

    This manager should be set as the default manager (objects) for all
    event-scoped models to enforce proper event filtering.

    Usage:
        class Team(models.Model):
            event = models.ForeignKey(Event, on_delete=models.CASCADE)
            objects = EventScopedManager()
    """

    def get_queryset(self):
        """Return EventScopedQuerySet instead of standard QuerySet"""
        return EventScopedQuerySet(self.model, using=self._db)

    def for_event(self, event):
        """
        Shortcut to filter by event at the manager level.

        Args:
            event: Event instance or event ID to filter by

        Returns:
            EventScopedQuerySet filtered to the specified event
        """
        return self.get_queryset().for_event(event)

    def all_events(self):
        """
        Shortcut to bypass event scoping at the manager level.

        Returns:
            EventScopedQuerySet marked as properly scoped
        """
        return self.get_queryset().all_events()

