"""
Thread-local storage for current event context.

This module provides thread-local storage for the current event,
allowing automatic event scoping without passing event through every function.
"""

import threading
from typing import Optional
from infrastructure.models import Event


_thread_local = threading.local()


def set_current_event(event: Optional[Event]) -> None:
    """
    Set the current event in thread-local storage.

    Args:
        event: Event instance or None to clear
    """
    _thread_local.event = event


def get_current_event() -> Optional[Event]:
    """
    Get the current event from thread-local storage.

    Returns:
        Event instance or None if not set
    """
    return getattr(_thread_local, 'event', None)


def clear_current_event() -> None:
    """Clear the current event from thread-local storage."""
    if hasattr(_thread_local, 'event'):
        delattr(_thread_local, 'event')


def get_active_event() -> Event:
    """
    Get the active event (marked as is_active=True).

    Returns:
        Active Event instance

    Raises:
        Event.DoesNotExist: If no active event found
    """
    return Event.get_active()
