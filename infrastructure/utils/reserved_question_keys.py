"""
Question keys that can't be used for ConfigurableQuestions.

When a form is submitted, ``extract_dynamic_responses`` (see
``question_responses.py``) removes every payload key that matches a
configurable question's ``question_key`` before the model serializers run, and
the answer is stored as a question response instead. A question that reuses the
key of a built-in field would therefore stop that field from being saved.

The reserved keys are derived from the serializers that handle each create
endpoint, so they follow the models and need no hand-maintained list.
"""
from infrastructure.models import ConfigurableQuestion
from infrastructure.rsvp_question_migration import (
    RSVP_QUESTIONS_2025,
    RSVP_QUESTIONS_2026,
)

FormType = ConfigurableQuestion.FormType

# TEMPORARY EXCLUDES -------------------------------------------------------
# Keys that were already migrated to configurable questions. Existing events
# use them as question keys (and new events will reuse them), so they must stay
# valid even though the legacy columns still exist on the models. The legacy
# columns are only kept around to defer the destructive migration.
#
# Remove these once the legacy columns are dropped: the keys will stop being
# model fields, so they'll no longer be reserved and this exclude has no effect.
MIGRATED_QUESTION_KEYS: dict[str, frozenset[str]] = {
    # Derived from the seeded RSVP question definitions.
    FormType.RSVP: frozenset(
        question.question_key
        for question in (*RSVP_QUESTIONS_2025, *RSVP_QUESTIONS_2026)
    ),
    # Seeded by the `load_2026_questions` / `migrate_to_dynamic_questions`
    # management commands, which keep them inline.
    FormType.APPLICATION: frozenset({
        'theme_essay',
        'theme_essay_follow_up',
        'theme_interest_track_one',
        'theme_interest_track_two',
        'theme_detail_one',
        'theme_detail_two',
        'theme_detail_three',
        'hardware_hack_interest',
        'hardware_hack_detail',
    }),
}


def get_reserved_question_keys(form_type: str) -> frozenset[str]:
    """Return the keys a question on ``form_type`` may not use."""
    # Imported here because serializers.py imports this module.
    from infrastructure.serializers import (
        ApplicationSerializer,
        AttendeeRSVPCreateSerializer,
        EventRsvpSerializer,
    )

    if form_type == FormType.RSVP:
        reserved = {
            *AttendeeRSVPCreateSerializer().fields,
            *EventRsvpSerializer().fields,
            # Read straight from the request by AttendeeRSVPViewSet.create.
            'sponsor_handler',
            'guardian_of',
        }
    else:
        reserved = set(ApplicationSerializer().fields)

    return frozenset(reserved) - MIGRATED_QUESTION_KEYS.get(form_type, frozenset())
