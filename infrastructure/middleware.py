"""
Event detection middleware for multi-tenant event scoping.

This middleware automatically detects the current event from the request
and sets it in thread-local storage for use by EventScopedModelViewSet.

Supports multiple detection strategies:
1. Subdomain-based routing (e.g., mit2025.realityhack.world)
2. Header-based routing (X-Event-ID header)
3. URL path-based routing (e.g., /api/events/{event_id}/...)
4. Query parameter (e.g., ?event=uuid)
"""

import uuid
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from infrastructure.event_context import set_current_event, clear_current_event
from infrastructure.models import Event


class EventDetectionMiddleware(MiddlewareMixin):
    """
    Middleware that detects the current event from the request and sets it
    in thread-local storage.

    Detection priority:
    1. URL path parameter (e.g., /api/events/{event_id}/teams/)
    2. X-Event-ID header
    3. Subdomain (e.g., mit2025.realityhack.world)
    4. Query parameter (?event=uuid)
    5. Active event fallback (single-tenant mode)
    """

    def process_request(self, request):
        """
        Detect event from request and set in thread-local storage.

        Returns:
            None if successful, JsonResponse with error if event not found
        """
        event = None
        detection_method = None

        # Strategy 1: URL path parameter
        # Example: /api/events/123e4567-e89b-12d3-a456-426614174000/teams/
        event, detection_method = self._detect_from_url_path(request)

        # Strategy 2: X-Event-ID header
        if not event:
            event, detection_method = self._detect_from_header(request)

        # Strategy 3: Subdomain
        if not event:
            event, detection_method = self._detect_from_subdomain(request)

        # Strategy 4: Query parameter
        if not event:
            event, detection_method = self._detect_from_query_param(request)

        # Strategy 5: Active event fallback (single-tenant mode)
        if not event:
            event, detection_method = self._detect_active_event()

        # If still no event found, return error
        if not event:
            return JsonResponse({
                'error': 'Event not found',
                'detail': 'No event could be detected from the request. '
                         'Please specify an event via header, URL, subdomain, or query parameter.'
            }, status=400)

        # Set event in thread-local storage
        set_current_event(event)

        # Add event info to request for convenience
        request.event = event
        request.event_detection_method = detection_method

        return None

    def process_response(self, request, response):
        """Clear event from thread-local storage after request completes."""
        clear_current_event()
        return response

    def process_exception(self, request, exception):
        """Clear event from thread-local storage if exception occurs."""
        clear_current_event()
        return None

    # Detection strategies

    def _detect_from_url_path(self, request):
        """
        Detect event from URL path.

        Example URLs:
        - /api/events/123e4567-e89b-12d3-a456-426614174000/teams/
        - /api/v1/events/123e4567-e89b-12d3-a456-426614174000/hardware/

        Returns:
            tuple: (Event instance or None, detection method string)
        """
        path_parts = request.path.split('/')

        # Look for /events/{uuid}/ pattern
        try:
            events_index = path_parts.index('events')
            if events_index + 1 < len(path_parts):
                event_id = path_parts[events_index + 1]
                if event_id:  # Check it's not empty
                    try:
                        event_uuid = uuid.UUID(event_id)
                        event = Event.objects.get(id=event_uuid)
                        return event, 'url_path'
                    except (ValueError, Event.DoesNotExist):
                        pass
        except ValueError:
            pass

        return None, None

    def _detect_from_header(self, request):
        """
        Detect event from X-Event-ID header.

        Example:
            X-Event-ID: 123e4567-e89b-12d3-a456-426614174000

        Returns:
            tuple: (Event instance or None, detection method string)
        """
        event_id = request.headers.get('X-Event-ID')
        if event_id:
            try:
                event_uuid = uuid.UUID(event_id)
                event = Event.objects.get(id=event_uuid)
                return event, 'header'
            except (ValueError, Event.DoesNotExist):
                pass

        return None, None

    def _detect_from_subdomain(self, request):
        """
        Detect event from subdomain.

        Examples:
            mit2025.realityhack.world -> Event with slug 'mit2025'
            stanford2025.realityhack.world -> Event with slug 'stanford2025'

        Note: Requires Event model to have a 'slug' field.

        Returns:
            tuple: (Event instance or None, detection method string)
        """
        host = request.get_host()

        # Parse subdomain
        # Example: mit2025.realityhack.world -> mit2025
        host_parts = host.split('.')
        if len(host_parts) >= 3:  # subdomain.domain.tld
            subdomain = host_parts[0]

            # Skip common subdomains
            if subdomain not in ['www', 'api', 'admin']:
                try:
                    # Try to find event by slug (you'd need to add this field)
                    # For now, we'll skip this and return None
                    # event = Event.objects.get(slug=subdomain)
                    # return event, 'subdomain'
                    pass
                except Event.DoesNotExist:
                    pass

        return None, None

    def _detect_from_query_param(self, request):
        """
        Detect event from query parameter.

        Example:
            /api/teams/?event=123e4567-e89b-12d3-a456-426614174000

        Returns:
            tuple: (Event instance or None, detection method string)
        """
        event_id = request.GET.get('event')
        if event_id:
            try:
                event_uuid = uuid.UUID(event_id)
                event = Event.objects.get(id=event_uuid)
                return event, 'query_param'
            except (ValueError, Event.DoesNotExist):
                pass

        return None, None

    def _detect_active_event(self):
        """
        Fallback to active event (single-tenant mode).

        Returns:
            tuple: (Event instance or None, detection method string)
        """
        try:
            event = Event.objects.get(is_active=True)
            return event, 'active_event_fallback'
        except Event.DoesNotExist:
            return None, None
        except Event.MultipleObjectsReturned:
            # If multiple active events, we can't use fallback
            return None, None


class EventRequiredMiddleware(MiddlewareMixin):
    """
    Simplified middleware that requires X-Event-ID header on all API requests.

    This is a stricter, simpler approach suitable for API-only backends
    where the frontend always knows which event context it's operating in.
    """

    # Paths that don't require event scoping
    EXEMPT_PATHS = [
        '/admin/',
        '/api/auth/',
        '/me/'
        '/api/events/',  # Event CRUD itself doesn't need event context
        '/health/',
        '/static/',
        '/media/',
    ]

    def process_request(self, request):
        """Require X-Event-ID header on all non-exempt requests."""

        # Skip exempt paths
        if any(request.path.startswith(path) for path in self.EXEMPT_PATHS):
            return None

        # Get event from header
        event_id = request.headers.get('X-Event-ID')

        if not event_id:
            return JsonResponse({
                'error': 'Event required',
                'detail': 'X-Event-ID header is required for this endpoint.'
            }, status=400)

        # Validate and load event
        try:
            event_uuid = uuid.UUID(event_id)
            event = Event.objects.get(id=event_uuid)
        except ValueError:
            return JsonResponse({
                'error': 'Invalid event ID',
                'detail': 'X-Event-ID header must be a valid UUID.'
            }, status=400)
        except Event.DoesNotExist:
            return JsonResponse({
                'error': 'Event not found',
                'detail': f'No event found with ID {event_id}.'
            }, status=404)

        # Set event in thread-local storage
        set_current_event(event)
        request.event = event

        return None

    def process_response(self, request, response):
        """Clear event from thread-local storage."""
        clear_current_event()
        return response

    def process_exception(self, request, exception):
        """Clear event from thread-local storage if exception occurs."""
        clear_current_event()
        return None


class DebugEventMiddleware(MiddlewareMixin):
    """
    Development middleware that logs event detection for debugging.

    Add this AFTER EventDetectionMiddleware to see what event was detected.
    """

    def process_request(self, request):
        """Log detected event."""
        if hasattr(request, 'event'):
            print(f"🎯 Event detected: {request.event.name} (via {request.event_detection_method})")
        else:
            print("⚠️  No event detected in request")
        return None
