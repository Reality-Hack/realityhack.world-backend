"""
Management command to migrate existing 2025 application 
fields to dynamic question system.

Usage:
    python manage.py migrate_to_dynamic_questions
    python manage.py migrate_to_dynamic_questions --event-id <uuid>
    python manage.py migrate_to_dynamic_questions --dry-run
"""
# is there a way for this to be run as a DB migration? Is it necessary?
from django.core.management.base import BaseCommand
from django.db import transaction
from infrastructure.models import (
    Application,
    ApplicationQuestionResponse,
    ConfigurableQuestion,
    ConfigurableQuestionChoice,
    Event,
)
from infrastructure.event_context import get_active_event

# Legacy application columns read during data migration. Use .values() so this
# command can run from migration 0046 before later Application fields exist.
APPLICATION_LEGACY_FIELDS = (
    'id',
    'email',
    'theme_essay',
    'theme_interest_track_one',
    'theme_interest_track_two',
    'theme_detail_one',
    'theme_detail_two',
    'theme_detail_three',
    'hardware_hack_interest',
    'hardware_hack_detail',
)

APPLICATION_FORM_TYPE = 'A'
QUESTION_TYPE_SINGLE = 'S'
QUESTION_TYPE_MULTIPLE = 'M'
QUESTION_TYPE_LONG_TEXT = 'L'

EVENT_2025_UUID = '888a5508-ea40-4453-84bc-a0e4a03e491b'


def _question_models(apps=None):
    """Resolve question models for live code or historical migration apps."""
    if apps is not None:
        return (
            apps.get_model('infrastructure', 'ApplicationQuestion'),
            apps.get_model('infrastructure', 'ApplicationQuestionChoice'),
            apps.get_model('infrastructure', 'ApplicationResponse'),
            apps.get_model('infrastructure', 'Application'),
            apps.get_model('infrastructure', 'Event'),
        )
    return (
        ConfigurableQuestion,
        ConfigurableQuestionChoice,
        ApplicationQuestionResponse,
        Application,
        Event,
    )


def _questions_for_event(Question, event):
    queryset = Question.objects.filter(event=event)
    if _table_has_column(Question._meta.db_table, 'form_type'):
        queryset = queryset.filter(form_type=APPLICATION_FORM_TYPE)
    return queryset


def _table_has_column(table_name: str, column_name: str) -> bool:
    from django.db import connection

    if table_name not in connection.introspection.table_names():
        return False

    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)
    return any(column.name == column_name for column in description)


def _question_create_kwargs(Question, **kwargs):
    if _table_has_column(Question._meta.db_table, 'form_type'):
        kwargs.setdefault('form_type', APPLICATION_FORM_TYPE)
    return kwargs


def run_application_question_migration(apps=None, *, event_id=None, dry_run=False):
    """Run migration with live models or historical apps from migration 0046."""
    Question, Choice, Response, Application, Event = _question_models(apps)

    if event_id:
        event = Event.objects.get(id=event_id)
    elif apps is not None:
        event = Event.objects.get(id=EVENT_2025_UUID)
    else:
        event = get_active_event()

    with transaction.atomic():
        if not dry_run:
            _delete_existing(event, Question, Choice, Response, Application)
        _create_essay_questions(event, Question, Response, Application, dry_run)
        _create_theme_questions(event, Question, Choice, Response, Application, dry_run)
        _create_hardware_questions(event, Question, Choice, Response, Application, dry_run)
        if dry_run:
            transaction.set_rollback(True)


class Command(BaseCommand):
    help = 'Migrate existing application fields to dynamic question system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--event-id',
            type=str,
            help='Specific event UUID to migrate. If not provided, uses active event.'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be created without making changes'
        )

    def handle(self, *args, **options):
        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                "DRY RUN MODE - No changes will be made"
            ))

        run_application_question_migration(
            event_id=options.get('event_id'),
            dry_run=options['dry_run'],
        )

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(
                "DRY RUN COMPLETE - Rolling back transaction"
            ))
        else:
            self.stdout.write(self.style.SUCCESS("Migration complete!"))


def _applications_for_event(Application, event):
    if hasattr(Application.objects, 'for_event'):
        return Application.objects.for_event(event)
    return Application.objects.filter(event=event)


def _delete_existing(event, Question, Choice, Response, Application):
    questions = _questions_for_event(Question, event)
    question_ids = list(questions.values_list('id', flat=True))
    application_ids = list(
        _applications_for_event(Application, event).values_list('id', flat=True)
    )
    Response.objects.filter(application_id__in=application_ids).delete()
    Choice.objects.filter(question_id__in=question_ids).delete()
    questions.delete()


def _create_essay_questions(event, Question, Response, Application, dry_run):
    essay_q = Question.objects.create(
        event=event,
        **_question_create_kwargs(
            Question,
            question_key='theme_essay',
            question_text=(
                'At MIT Reality Hack, teamwork and communication are critical to '
                'success. How do you see yourself supporting your team in this respect?'
            ),
            question_type=QUESTION_TYPE_LONG_TEXT,
            order=5,
            required=True,
            max_length=2000,
            placeholder_text='Enter your response here.',
        ),
    )

    if not dry_run:
        _migrate_essay_responses(event, essay_q, Response, Application)


def _migrate_essay_responses(event, essay_q, Response, Application):
    applications = list(
        _applications_for_event(Application, event).values(*APPLICATION_LEGACY_FIELDS)
    )

    for app in applications:
        if app['theme_essay']:
            Response.objects.create(
                application_id=app['id'],
                question=essay_q,
                text_response=app['theme_essay'],
            )


def _create_theme_questions(event, Question, Choice, Response, Application, dry_run):
    track_one_q = Question.objects.create(
        event=event,
        **_question_create_kwargs(
            Question,
            question_key='theme_interest_track_one',
            question_text=(
                'Are you interested in participating in programming focused on '
                'startups and entrepreneurship? Please indicate your interest here and '
                'we will follow up.'
            ),
            question_type=QUESTION_TYPE_SINGLE,
            order=10,
            required=True,
        ),
    )
    Choice.objects.create(question=track_one_q, choice_key='Y', choice_text='Yes', order=1)
    Choice.objects.create(question=track_one_q, choice_key='N', choice_text='No', order=2)

    parent_q = Question.objects.create(
        event=event,
        **_question_create_kwargs(
            Question,
            question_key='theme_interest_track_two',
            question_text='Are you interested in hacking on Apple Vision Pro?',
            question_type=QUESTION_TYPE_SINGLE,
            order=20,
            required=True,
        ),
    )
    Choice.objects.create(question=parent_q, choice_key='Y', choice_text='Yes', order=1)
    Choice.objects.create(question=parent_q, choice_key='N', choice_text='No', order=2)

    detail_one_q = Question.objects.create(
        event=event,
        **_question_create_kwargs(
            Question,
            question_key='theme_detail_one',
            question_text=(
                "Do you meet all of the minimum system requirements? This means you "
                "MUST have an Apple silicon Mac (M1, M2, etc.) to develop for visionOS."
                " Please note that this is a hard requirement for being on a Vision Pro"
                "team. These requirements are set by Apple and we unfortunately won't "
                "have Mac hardware to check out."
            ),
            question_type=QUESTION_TYPE_SINGLE,
            order=21,
            required=True,
            parent_question=parent_q,
            trigger_choices=['Y'],
        ),
    )
    Choice.objects.create(question=detail_one_q, choice_key='Y', choice_text='Yes', order=1)
    Choice.objects.create(question=detail_one_q, choice_key='N', choice_text='No', order=2)

    detail_two_q = Question.objects.create(
        event=event,
        **_question_create_kwargs(
            Question,
            question_key='theme_detail_two',
            question_text=(
                "If your team decides to develop using Unity, are you willing to sign "
                "up for a 30-Day Unity Pro Trial? CRITICAL: You MUST cancel the trial "
                "before the 30 days is up or you will be charged $2,040 USD. This is "
                "true even if you choose the monthly payment plan, since the "
                "subscription is for one year and the payment plan just spreads the "
                "cost over one year. The 30 day trial can be cancelled the moment you "
                "activate it and you will still have access for 30 days. Unity allows "
                "only one 30 day trial per account. Please ensure your trial period "
                "will cover the event days from January 23 - 27, 2025. "
                "Unity Pro is required to develop for Apple Vision Pro."
            ),
            question_type=QUESTION_TYPE_SINGLE,
            order=22,
            required=True,
            parent_question=parent_q,
            trigger_choices=['Y'],
        ),
    )
    Choice.objects.create(question=detail_two_q, choice_key='Y', choice_text='Yes', order=1)
    Choice.objects.create(question=detail_two_q, choice_key='N', choice_text='No', order=2)

    detail_three_q = Question.objects.create(
        event=event,
        **_question_create_kwargs(
            Question,
            question_key='theme_detail_three',
            question_text=(
                "Do you own a Vision Pro that you are willing to bring to support your "
                "team? You will not be expected to allow your teammates to use your "
                "device if you are uncomfortable doing so. We will set this expectation"
                " during opening ceremony."
            ),
            question_type=QUESTION_TYPE_SINGLE,
            order=23,
            required=True,
            parent_question=parent_q,
            trigger_choices=['Y'],
        ),
    )
    Choice.objects.create(question=detail_three_q, choice_key='Y', choice_text='Yes', order=1)
    Choice.objects.create(question=detail_three_q, choice_key='N', choice_text='No', order=2)

    if not dry_run:
        _migrate_theme_responses(
            event,
            track_one_q,
            parent_q,
            detail_one_q,
            detail_two_q,
            detail_three_q,
            Choice,
            Response,
            Application,
        )


def _save_selected_snapshot(response):
    if hasattr(response, 'update_selected_snapshot'):
        response.update_selected_snapshot()
        return

    response.selected_keys_snapshot = list(
        response.selected_choices.values_list('choice_key', flat=True)
    )
    response.save(update_fields=['selected_keys_snapshot'])


def _migrate_theme_responses(
    event,
    track_one_q,
    parent_q,
    detail_one_q,
    detail_two_q,
    detail_three_q,
    Choice,
    Response,
    Application,
):
    applications = list(
        _applications_for_event(Application, event).values(*APPLICATION_LEGACY_FIELDS)
    )

    for app in applications:
        if app['theme_interest_track_one'] in ('Y', 'N'):
            try:
                response = Response.objects.create(
                    application_id=app['id'],
                    question=track_one_q,
                )
                choice = track_one_q.choices.get(
                    choice_key=app['theme_interest_track_one']
                )
                response.selected_choices.add(choice)
                _save_selected_snapshot(response)
            except Choice.DoesNotExist:
                continue

        if app['theme_interest_track_two'] in ('Y', 'N'):
            try:
                response = Response.objects.create(
                    application_id=app['id'],
                    question=parent_q,
                )
                choice = parent_q.choices.get(
                    choice_key=app['theme_interest_track_two']
                )
                response.selected_choices.add(choice)
                _save_selected_snapshot(response)

                if app['theme_interest_track_two'] == 'Y':
                    for detail_value, detail_question in (
                        (app['theme_detail_one'], detail_one_q),
                        (app['theme_detail_two'], detail_two_q),
                        (app['theme_detail_three'], detail_three_q),
                    ):
                        if detail_value in ('Y', 'N'):
                            detail_response = Response.objects.create(
                                application_id=app['id'],
                                question=detail_question,
                            )
                            detail_choice = detail_question.choices.get(
                                choice_key=detail_value
                            )
                            detail_response.selected_choices.add(detail_choice)
                            _save_selected_snapshot(detail_response)
            except Choice.DoesNotExist:
                continue


def _create_hardware_questions(event, Question, Choice, Response, Application, dry_run):
    parent_q = Question.objects.create(
        event=event,
        **_question_create_kwargs(
            Question,
            question_key='hardware_hack_interest',
            question_text=(
                "How interested would you be in participating in The Hardware Hack this"
                " year? The Hardware Hack is a special hand-on track where participants"
                " use hardware kits to design XR devices that interface with our bodies"
                " and with our surroundings."
            ),
            question_type=QUESTION_TYPE_SINGLE,
            order=30,
            required=False,
        ),
    )
    for choice_key, choice_text, order in (
        ('A', "Not at all interested; I'll pass", 1),
        ('B', 'Some mild interest', 2),
        ('C', 'Most likely', 3),
        ('D', '100%; I want to join', 4),
    ):
        Choice.objects.create(
            question=parent_q,
            choice_key=choice_key,
            choice_text=choice_text,
            order=order,
        )

    detail_q = Question.objects.create(
        event=event,
        **_question_create_kwargs(
            Question,
            question_key='hardware_hack_detail',
            question_text=(
                'Do you have any prior experience building custom hardware in these'
                ' areas?'
            ),
            question_type=QUESTION_TYPE_MULTIPLE,
            order=31,
            required=False,
            parent_question=parent_q,
            trigger_choices=['B', 'C', 'D'],
        ),
    )
    for choice_key, choice_text, order in (
        ('A', '3D Printing', 1),
        ('B', 'Soldering', 2),
        ('C', 'Circuits', 3),
        ('D', 'Arduino', 4),
        ('E', 'ESP32', 5),
        ('F', 'Unity', 6),
        ('G', 'Physical Prototyping', 7),
        ('H', 'I have no prior experience', 8),
        ('O', 'Other', 9),
    ):
        Choice.objects.create(
            question=detail_q,
            choice_key=choice_key,
            choice_text=choice_text,
            order=order,
        )

    if not dry_run:
        _migrate_hardware_responses(event, parent_q, detail_q, Choice, Response, Application)


def _migrate_hardware_responses(event, parent_q, detail_q, Choice, Response, Application):
    applications = list(
        _applications_for_event(Application, event).values(*APPLICATION_LEGACY_FIELDS)
    )

    for app in applications:
        if app['hardware_hack_interest'] not in ('A', 'B', 'C', 'D'):
            continue

        try:
            response = Response.objects.create(
                application_id=app['id'],
                question=parent_q,
            )
            choice = parent_q.choices.get(choice_key=app['hardware_hack_interest'])
            response.selected_choices.add(choice)
            _save_selected_snapshot(response)

            if app['hardware_hack_interest'] in ('B', 'C', 'D') and app['hardware_hack_detail']:
                detail_response = Response.objects.create(
                    application_id=app['id'],
                    question=detail_q,
                )
                for key in app['hardware_hack_detail']:
                    key = key.strip()
                    try:
                        detail_choice = detail_q.choices.get(choice_key=key)
                        detail_response.selected_choices.add(detail_choice)
                    except Choice.DoesNotExist:
                        continue
                _save_selected_snapshot(detail_response)
        except Choice.DoesNotExist:
            continue
