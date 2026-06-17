"""
Migrate legacy EventRsvp questionnaire fields to configurable RSVP questions.

Prerequisite: apply migration 0061 (widens choice_key) before seeding RSVP choices:
    uv run python manage.py migrate infrastructure 0061

Usage:
    uv run python manage.py migrate_rsvp_to_dynamic_questions
    uv run python manage.py migrate_rsvp_to_dynamic_questions --dry-run
    uv run python manage.py migrate_rsvp_to_dynamic_questions --event-id <uuid>
"""
from django.core.management.base import BaseCommand

from infrastructure.rsvp_question_migration import run_rsvp_question_migration


class Command(BaseCommand):
    help = 'Seed RSVP configurable questions and migrate legacy EventRsvp responses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--event-id',
            type=str,
            help='Migrate a single event by UUID (2025 or 2026 config only)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview changes without committing',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        event_id = options.get('event_id')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - rolling back transaction'))

        run_rsvp_question_migration(
            event_id=event_id,
            dry_run=dry_run,
            writer=self.stdout.write if dry_run else None,
        )

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN COMPLETE'))
        else:
            self.stdout.write(self.style.SUCCESS('RSVP question migration complete'))
