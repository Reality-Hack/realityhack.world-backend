"""
Shared helpers for persisting answers to event-scoped ConfigurableQuestions.

Used by both the application and RSVP create flows. The frontend posts dynamic
question answers as flat top-level keys (``question_key: value``) alongside the
regular model fields, so these helpers pull those keys out of the payload and
write the corresponding ``*QuestionResponse`` rows.
"""
from typing import Any, MutableMapping, Type

from django.db import models, transaction

from infrastructure.models import ConfigurableQuestion, Event


def _is_blank(value: Any) -> bool:
    return (
        value is None
        or value == ''
        or (isinstance(value, list) and len(value) == 0)
    )


def extract_dynamic_responses(
    data: MutableMapping[str, Any],
    event: Event,
    form_type: str,
) -> dict[str, Any]:
    """
    Remove and return the entries of ``data`` whose keys match a
    ConfigurableQuestion ``question_key`` for the given event and form type.

    The keys are popped so they never reach the model serializers; answers are
    stored only as question response rows.
    """
    question_keys = set(
        ConfigurableQuestion.objects.for_event(event)
        .filter(form_type=form_type)
        .values_list('question_key', flat=True)
    )

    responses: dict[str, Any] = {}
    for key in list(data.keys()):
        if key in question_keys:
            responses[key] = data.pop(key)
    return responses


def save_question_responses(
    *,
    response_model: Type[models.Model],
    parent_field: str,
    parent: models.Model,
    event: Event,
    form_type: str,
    responses: dict[str, Any],
) -> None:
    """
    Create one ``response_model`` row per answered question.

    ``parent_field`` is the FK name on ``response_model`` that points at
    ``parent`` (``application`` or ``rsvp``). Blank answers are skipped.
    Choice questions store the selected ``ConfigurableQuestionChoice`` rows plus
    snapshots of the choice keys; text questions store the text and a snapshot.
    """
    if not responses:
        return

    questions = ConfigurableQuestion.objects.for_event(event).filter(
        form_type=form_type
    )

    with transaction.atomic():
        for question in questions:
            if question.question_key not in responses:
                continue

            value = responses[question.question_key]
            if _is_blank(value):
                continue

            response = response_model.objects.create(
                **{parent_field: parent},
                question=question,
                question_text_snapshot=question.question_text,
            )

            if question.question_type in [
                ConfigurableQuestion.QuestionType.SINGLE_CHOICE,
                ConfigurableQuestion.QuestionType.MULTIPLE_CHOICE,
            ]:
                response.choices_snapshot = {
                    c.choice_key: c.choice_text for c in question.choices.all()
                }
                selected_keys = value if isinstance(value, list) else [value]
                response.selected_choices.set(
                    question.choices.filter(choice_key__in=selected_keys)
                )
                response.selected_keys_snapshot = selected_keys
                response.save()

            elif question.question_type in [
                ConfigurableQuestion.QuestionType.TEXT,
                ConfigurableQuestion.QuestionType.LONG_TEXT,
            ]:
                response.text_response = value
                response.text_response_snapshot = value
                response.save()
