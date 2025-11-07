import logging
from rest_framework import viewsets
from infrastructure.event_context import get_current_event, get_active_event


class LoggingMixin:
    """
    Provides full logging of requests and responses
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.getLogger('django.request')

    def initial(self, request, *args, **kwargs):
        try:
            self.logger.debug({
                "request": request.data,
                "method": request.method,
                "endpoint": request.path,
                # "user": request.user.username,
                "ip_address": request.META.get('REMOTE_ADDR'),
                "user_agent": request.META.get('HTTP_USER_AGENT')
            })
        except Exception:
            self.logger.exception("Error logging request data")
            self.logger.info({"request": request.data})
        super().initial(request, *args, **kwargs)

    def finalize_response(self, request, response, *args, **kwargs):
        try:
            self.logger.debug({
                "response": response.data,
                "status_code": response.status_code,
                # "user": request.user.username,
                "ip_address": request.META.get('REMOTE_ADDR'),
                "user_agent": request.META.get('HTTP_USER_AGENT')
            })
        except Exception:
            self.logger.exception("Error logging response data")
            self.logger.info({"request": response.data})
        return super().finalize_response(request, response, *args, **kwargs)


class EventScopedModelViewSet(viewsets.ModelViewSet):
    """
    Base ViewSet that automatically scopes queries by event.

    This ViewSet:
    - Automatically filters all queries to the current event
    - Sets event on object creation
    - Provides get_event() method for event resolution

    Subclasses can override get_event() for custom event resolution logic.
    """

    def get_event(self):
        """
        Get the event for this request.

        Default implementation uses the active event.
        Override this method for custom event resolution.

        Returns:
            Event instance
        """
        # Try thread-local context first
        event = get_current_event()
        if event:
            return event

        # Fall back to active event
        return get_active_event()

    def get_queryset(self):
        """
        Override to automatically scope queryset by event.

        Returns:
            EventScopedQuerySet filtered to current event
        """
        queryset = super().get_queryset()

        # Get the event for this request
        event = self.get_event()

        # Apply event scoping if the model has EventScopedManager
        if hasattr(queryset, 'for_event'):
            return queryset.for_event(event)

        # Fallback for models without EventScopedManager
        if hasattr(queryset.model, 'event'):
            return queryset.filter(event=event)

        return queryset

    def perform_create(self, serializer):
        """
        Override to automatically set event on object creation.

        Args:
            serializer: Serializer instance with validated data
        """
        event = self.get_event()

        # Set event if the model has an event field
        if hasattr(serializer.Meta.model, 'event'):
            serializer.save(event=event)
        else:
            serializer.save()


class EventScopedLoggingViewSet(LoggingMixin, EventScopedModelViewSet):
    """
    Combined ViewSet with both event scoping and logging.

    Use this as the base class for most ViewSets that need event scoping.
    """
    pass
