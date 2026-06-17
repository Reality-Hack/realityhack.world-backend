"""
Seed RSVP configurable questions and migrate legacy EventRsvp column data
into RsvpQuestionResponse rows.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from dataclasses import dataclass
from typing import Callable

from django.db import transaction

from infrastructure.models import (
    ConfigurableQuestion,
    ConfigurableQuestionChoice,
    Event,
    EventRsvp,
    LoanerHeadsetPreference,
    RsvpQuestionResponse,
)

logger = logging.getLogger(__name__)

LogWriter = Callable[[str], None]
TEXT_PREVIEW_LENGTH = 80


def _write_log(writer: LogWriter | None, message: str) -> None:
    if writer is not None:
        writer(message)
    else:
        logger.info(message)


def _preview_value(value: str | None) -> str:
    if value is None:
        return '(null)'
    if value.strip() == '':
        return '(empty)'
    if len(value) <= TEXT_PREVIEW_LENGTH:
        return repr(value)
    return repr(f'{value[:TEXT_PREVIEW_LENGTH]}…')


def _question_type_label(question_type: str) -> str:
    labels = {
        ConfigurableQuestion.QuestionType.SINGLE_CHOICE: 'single choice',
        ConfigurableQuestion.QuestionType.MULTIPLE_CHOICE: 'multiple choice',
        ConfigurableQuestion.QuestionType.TEXT: 'text',
        ConfigurableQuestion.QuestionType.LONG_TEXT: 'long text',
    }
    return labels.get(question_type, question_type)


def _log_question_mapping_plan(
    event: Event,
    questions: tuple[RsvpQuestionDefinition, ...],
    writer: LogWriter | None,
) -> None:
    _write_log(writer, '')
    _write_log(writer, f'=== {event.name} ({event.id}) ===')
    _write_log(writer, 'Question mapping (legacy EventRsvp column → config question):')
    for question_def in questions:
        _write_log(
            writer,
            (
                f"  {question_def.legacy_field} → {question_def.question_key} "
                f"({_question_type_label(question_def.question_type)})"
            ),
        )
        if question_def.choices:
            choice_keys = ', '.join(
                choice.choice_key for choice in question_def.choices
            )
            _write_log(writer, f'    choices: {choice_keys}')


def _log_question_seed_result(
    question_def: RsvpQuestionDefinition,
    *,
    created: bool,
    choices_created: int,
    writer: LogWriter | None,
) -> None:
    status = 'create' if created else 'exists'
    _write_log(
        writer,
        (
            f"  [{status}] {question_def.question_key} "
            f"({_question_type_label(question_def.question_type)})"
        ),
    )
    if choices_created:
        _write_log(writer, f'    added {choices_created} choice(s)')


EVENT_2025_UUID = uuid.UUID('888a5508-ea40-4453-84bc-a0e4a03e491b')
EVENT_2026_NAME = 'Reality Hack at MIT 2026'

LOANER_2026_EXCLUDED_KEYS = frozenset({'BYOD', 'HWHACK', 'TBD'})
YES_NO_CHOICES = (
    ('Y', 'Yes'),
    ('N', 'No'),
)

BREAKTHROUGH_HACKS_2025_QUESTION_TEXT = (
    'Breakthrough Hacks Opportunity: This year, select teams will be given '
    'the opportunity to be some of the FIRST hackers ever to work with '
    'technology from the following companies: Galea; Maradin (dev kit includes '
    'monocle display glass); Distance; Advanced haptic gloves (We will reveal '
    'who it is at the Hack!); OpenBCI Biometric Sensors; Qualcomm RB3 Gen2. '
    "If you're interested in any of these, please let us know which one and why."
)


@dataclass(frozen=True)
class RsvpChoiceDefinition:
    choice_key: str
    choice_text: str
    order: int


@dataclass(frozen=True)
class RsvpQuestionDefinition:
    question_key: str
    question_text: str
    question_type: str
    order: int
    required: bool
    choices: tuple[RsvpChoiceDefinition, ...] = ()
    max_length: int | None = None
    placeholder_text: str = ''
    legacy_field: str = ''

    def __post_init__(self) -> None:
        if not self.legacy_field:
            object.__setattr__(self, 'legacy_field', self.question_key)


def _loaner_2025_choices() -> tuple[RsvpChoiceDefinition, ...]:
    labels = dict(LoanerHeadsetPreference.choices)
    keys = ('META', 'SNAP', 'BYOD', 'HWHACK', 'TBD')
    return tuple(
        RsvpChoiceDefinition(
            choice_key=key,
            choice_text=labels[key],
            order=index + 1,
        )
        for index, key in enumerate(keys)
    )


def _loaner_2026_choices() -> tuple[RsvpChoiceDefinition, ...]:
    return tuple(
        RsvpChoiceDefinition(
            choice_key=key,
            choice_text=label,
            order=index + 1,
        )
        for index, (key, label) in enumerate(LoanerHeadsetPreference.choices)
        if key not in LOANER_2026_EXCLUDED_KEYS
    )


def _yes_no_choices() -> tuple[RsvpChoiceDefinition, ...]:
    return tuple(
        RsvpChoiceDefinition(choice_key=key, choice_text=label, order=index + 1)
        for index, (key, label) in enumerate(YES_NO_CHOICES)
    )


RSVP_QUESTIONS_2025: tuple[RsvpQuestionDefinition, ...] = (
    RsvpQuestionDefinition(
        question_key='loaner_headset_preference',
        question_text=(
            'If you had to choose one loaner headset to work with, '
            'which would be your preference?'
        ),
        question_type=ConfigurableQuestion.QuestionType.SINGLE_CHOICE,
        order=10,
        required=True,
        choices=_loaner_2025_choices(),
    ),
    RsvpQuestionDefinition(
        question_key='breakthrough_hacks_interest',
        question_text=BREAKTHROUGH_HACKS_2025_QUESTION_TEXT,
        question_type=ConfigurableQuestion.QuestionType.LONG_TEXT,
        order=20,
        required=False,
        max_length=2000,
        placeholder_text='Please describe your interest...',
    ),
    RsvpQuestionDefinition(
        question_key='special_interest_track_one',
        question_text=(
            'Would you like to register for the Hardware Hack at this time?'
        ),
        question_type=ConfigurableQuestion.QuestionType.SINGLE_CHOICE,
        order=30,
        required=True,
        choices=_yes_no_choices(),
    ),
    RsvpQuestionDefinition(
        question_key='special_interest_track_two',
        question_text=(
            'Would you like to register for the MIT Reality Hack '
            'Founders Lab at this time?'
        ),
        question_type=ConfigurableQuestion.QuestionType.SINGLE_CHOICE,
        order=40,
        required=True,
        choices=_yes_no_choices(),
    ),
)

RSVP_QUESTIONS_2026: tuple[RsvpQuestionDefinition, ...] = (
    RsvpQuestionDefinition(
        question_key='loaner_headset_preference',
        question_text=(
            'If you had to choose one device to work with, which would be '
            'your top preference? Please note that equipment listed may not '
            'be available or will be limited to specific prize tracks.'
        ),
        question_type=ConfigurableQuestion.QuestionType.SINGLE_CHOICE,
        order=10,
        required=True,
        choices=_loaner_2026_choices(),
    ),
    RsvpQuestionDefinition(
        question_key='device_preference_ranked',
        question_text=(
            'From the above list, please list other devices you may be '
            'interested in working with ranked in order of preference.'
        ),
        question_type=ConfigurableQuestion.QuestionType.LONG_TEXT,
        order=20,
        required=False,
        max_length=1000,
        placeholder_text='Please describe your interest...',
    ),
    RsvpQuestionDefinition(
        question_key='special_interest_track_one',
        question_text=(
            'Do you want to register your interest for the Immersion League '
            'Continuity Track at this time? Please make sure you\'ve filled '
            'out the Google Form found in the Track Description in the RSVP '
            'email if you want to apply to it.'
        ),
        question_type=ConfigurableQuestion.QuestionType.SINGLE_CHOICE,
        order=30,
        required=True,
        choices=_yes_no_choices(),
    ),
    RsvpQuestionDefinition(
        question_key='special_interest_track_two',
        question_text=(
            'Do you want to register your interest in the Founders Lab Prize '
            'Track at this time? This option is open to hackers interested in '
            'taking extra steps to research their concepts and polish their '
            'level of presentation. It is not for pre-formed startups.'
        ),
        question_type=ConfigurableQuestion.QuestionType.SINGLE_CHOICE,
        order=40,
        required=True,
        choices=_yes_no_choices(),
    ),
)


@dataclass(frozen=True)
class RsvpEventMigrationConfig:
    event_resolver: Callable[[], Event]
    questions: tuple[RsvpQuestionDefinition, ...]


def resolve_event_2025() -> Event:
    return Event.objects.get(id=EVENT_2025_UUID)


def resolve_event_2026() -> Event:
    return Event.objects.get(name=EVENT_2026_NAME)


RSVP_EVENT_MIGRATION_CONFIGS: tuple[RsvpEventMigrationConfig, ...] = (
    RsvpEventMigrationConfig(
        event_resolver=resolve_event_2025,
        questions=RSVP_QUESTIONS_2025,
    ),
    RsvpEventMigrationConfig(
        event_resolver=resolve_event_2026,
        questions=RSVP_QUESTIONS_2026,
    ),
)


def get_migration_config_for_event(event: Event) -> RsvpEventMigrationConfig | None:
    if event.id == EVENT_2025_UUID:
        return RSVP_EVENT_MIGRATION_CONFIGS[0]
    if event.name == EVENT_2026_NAME:
        return RSVP_EVENT_MIGRATION_CONFIGS[1]
    return None


def seed_rsvp_questions(
    event: Event,
    questions: tuple[RsvpQuestionDefinition, ...],
    *,
    writer: LogWriter | None = None,
) -> dict[str, ConfigurableQuestion]:
    """Create RSVP questions + choices for events. Returns question_key -> question."""
    seeded: dict[str, ConfigurableQuestion] = {}

    if writer is not None:
        _write_log(writer, '')
        _write_log(writer, f'Seeding RSVP questions for {event.name}')

    for question_def in questions:
        question, created = ConfigurableQuestion.objects.for_event(event).get_or_create(
            form_type=ConfigurableQuestion.FormType.RSVP,
            question_key=question_def.question_key,
            defaults={
                'event': event,
                'question_text': question_def.question_text,
                'question_type': question_def.question_type,
                'order': question_def.order,
                'required': question_def.required,
                'max_length': question_def.max_length,
                'placeholder_text': question_def.placeholder_text,
            },
        )
        choices_created = 0
        if created and question_def.choices:
            ConfigurableQuestionChoice.objects.bulk_create([
                ConfigurableQuestionChoice(
                    question=question,
                    choice_key=choice.choice_key,
                    choice_text=choice.choice_text,
                    order=choice.order,
                )
                for choice in question_def.choices
            ])
            choices_created = len(question_def.choices)
        if writer is not None:
            _log_question_seed_result(
                question_def,
                created=created,
                choices_created=choices_created,
                writer=writer,
            )
        seeded[question_def.question_key] = question

    return seeded


def _is_blank_text(value: str | None) -> bool:
    return value is None or value.strip() == ''


def _migrate_single_choice_response(
    rsvp: EventRsvp,
    question: ConfigurableQuestion,
    choice_key: str | None,
    *,
    writer: LogWriter | None = None,
    question_def: RsvpQuestionDefinition | None = None,
) -> str:
    """Migrate one single-choice field. Returns outcome label for dry-run stats."""
    if not choice_key:
        return 'skipped_blank'

    if RsvpQuestionResponse.objects.filter(rsvp=rsvp, question=question).exists():
        return 'skipped_exists'

    response = RsvpQuestionResponse.objects.create(rsvp=rsvp, question=question)
    outcome = 'migrated_choice'
    try:
        choice = question.choices.get(choice_key=choice_key)
        response.selected_choices.add(choice)
        response.update_selected_snapshot()
    except ConfigurableQuestionChoice.DoesNotExist:
        outcome = 'migrated_orphan_choice'
        logger.warning(
            'Unknown choice_key=%s for question=%s on rsvp=%s; storing raw key only',
            choice_key,
            question.question_key,
            rsvp.id,
        )
        response.selected_keys_snapshot = [choice_key]
        response.save(update_fields=['selected_keys_snapshot'])

    if writer is not None and question_def is not None:
        _write_log(
            writer,
            (
                f"  rsvp={rsvp.id} attendee={rsvp.attendee.email}: "
                f"EventRsvp.{question_def.legacy_field}={choice_key!r} → "
                f"{question_def.question_key} ({outcome})"
            ),
        )
    return outcome


def _migrate_text_response(
    rsvp: EventRsvp,
    question: ConfigurableQuestion,
    text_value: str | None,
    *,
    writer: LogWriter | None = None,
    question_def: RsvpQuestionDefinition | None = None,
) -> str:
    """Migrate one text field. Returns outcome label for dry-run stats."""
    if _is_blank_text(text_value):
        return 'skipped_blank'

    if RsvpQuestionResponse.objects.filter(rsvp=rsvp, question=question).exists():
        return 'skipped_exists'

    RsvpQuestionResponse.objects.create(
        rsvp=rsvp,
        question=question,
        text_response=text_value,
    )
    if writer is not None and question_def is not None:
        _write_log(
            writer,
            (
                f"  rsvp={rsvp.id} attendee={rsvp.attendee.email}: "
                f"EventRsvp.{question_def.legacy_field}={_preview_value(text_value)} → "
                f"{question_def.question_key} (migrated_text)"
            ),
        )
    return 'migrated_text'


def migrate_rsvp_responses(
    event: Event,
    questions: tuple[RsvpQuestionDefinition, ...],
    question_map: dict[str, ConfigurableQuestion],
    *,
    writer: LogWriter | None = None,
) -> int:
    """Migrate legacy EventRsvp columns into RsvpQuestionResponse rows."""
    migrated_count = 0
    outcome_counts: dict[str, int] = defaultdict(int)
    rsvp_total = EventRsvp.objects.filter(event=event).count()

    if writer is not None:
        _write_log(writer, '')
        _write_log(writer, f'Migrating responses for {rsvp_total} EventRsvp row(s)')

    for rsvp in EventRsvp.objects.filter(
        event=event
    ).select_related('attendee').iterator():
        for question_def in questions:
            question = question_map[question_def.question_key]
            legacy_value = getattr(rsvp, question_def.legacy_field, None)

            if question_def.question_type in (
                ConfigurableQuestion.QuestionType.SINGLE_CHOICE,
                ConfigurableQuestion.QuestionType.MULTIPLE_CHOICE,
            ):
                outcome = _migrate_single_choice_response(
                    rsvp,
                    question,
                    legacy_value,
                    writer=writer,
                    question_def=question_def,
                )
            elif question_def.question_type in (
                ConfigurableQuestion.QuestionType.TEXT,
                ConfigurableQuestion.QuestionType.LONG_TEXT,
            ):
                outcome = _migrate_text_response(
                    rsvp,
                    question,
                    legacy_value,
                    writer=writer,
                    question_def=question_def,
                )
            else:
                continue

            outcome_counts[outcome] += 1
            if outcome.startswith('migrated'):
                migrated_count += 1

    if writer is not None:
        _write_log(writer, '')
        _write_log(writer, 'Response migration summary:')
        _write_log(writer, f'  migrated: {migrated_count}')
        for outcome in (
            'migrated_choice',
            'migrated_orphan_choice',
            'migrated_text',
            'skipped_blank',
            'skipped_exists',
        ):
            if outcome_counts[outcome]:
                _write_log(writer, f'  {outcome}: {outcome_counts[outcome]}')

    return migrated_count


def reverse_rsvp_question_migration(event: Event) -> None:
    """Remove RSVP question responses and question config for an event."""
    rsvp_ids = EventRsvp.objects.filter(event=event).values_list('id', flat=True)
    RsvpQuestionResponse.objects.filter(rsvp_id__in=rsvp_ids).delete()
    ConfigurableQuestion.objects.for_event(event).filter(
        form_type=ConfigurableQuestion.FormType.RSVP,
    ).delete()


def run_rsvp_question_migration(
    *,
    event_id: str | None = None,
    dry_run: bool = False,
    writer: LogWriter | None = None,
) -> None:
    configs = RSVP_EVENT_MIGRATION_CONFIGS
    log_writer = writer if dry_run else None

    if event_id:
        event = Event.objects.get(id=event_id)
        config = get_migration_config_for_event(event)
        if config is None:
            raise ValueError(
                f'Event {event_id} ({event.name}) has no RSVP question migration config'
            )
        configs = (config,)

    if log_writer is not None:
        _write_log(log_writer, 'DRY RUN — previewing RSVP question migration')

    with transaction.atomic():
        total_responses = 0
        for config in configs:
            try:
                event = config.event_resolver()
            except Event.DoesNotExist:
                logger.warning(
                    'Skipping RSVP question migration; event not found for config'
                )
                continue

            if log_writer is not None:
                _log_question_mapping_plan(event, config.questions, log_writer)

            question_map = seed_rsvp_questions(
                event,
                config.questions,
                writer=log_writer,
            )
            total_responses += migrate_rsvp_responses(
                event,
                config.questions,
                question_map,
                writer=log_writer,
            )

        if dry_run:
            transaction.set_rollback(True)

    if dry_run:
        if log_writer is not None:
            _write_log(log_writer, '')
            _write_log(
                log_writer,
                f'DRY RUN complete — would migrate {total_responses} response(s); '
                'no changes committed',
            )
        logger.info('Dry run complete; no changes committed')
    else:
        logger.info('Migrated %s RSVP question responses', total_responses)
