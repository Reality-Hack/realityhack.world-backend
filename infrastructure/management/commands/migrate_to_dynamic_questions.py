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
    Event, Application, ApplicationQuestion, 
    ApplicationQuestionChoice, ApplicationResponse
)
from infrastructure.event_context import get_active_event


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
        dry_run = options['dry_run']

        # Get event
        if options['event_id']:
            try:
                event = Event.objects.get(id=options['event_id'])
                self.stdout.write(f"Using event: {event.name}")
            except Event.DoesNotExist:
                self.stdout.write(self.style.ERROR(
                    f"Event {options['event_id']} not found"
                ))
                return
        else:
            event = get_active_event()
            self.stdout.write(f"Using active event: {event.name}")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY RUN MODE - No changes will be made"
            ))

        with transaction.atomic():
            if not dry_run:
                self.delete_existing(event)
            self.create_essay_questions(event, dry_run)
            self.create_theme_questions(event, dry_run)
            self.create_hardware_questions(event, dry_run)

            if dry_run:
                self.stdout.write(self.style.WARNING(
                    "DRY RUN COMPLETE - Rolling back transaction"
                ))
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS("Migration complete!"))

    def delete_existing(self, event):
        applications = Application.objects.for_event(event).all()
        questions = ApplicationQuestion.objects.for_event(event).all()
        application_ids = [application.id for application in applications]
        question_ids = [question.id for question in questions]
        responses = ApplicationResponse.objects.filter(application__in=application_ids)
        choices = ApplicationQuestionChoice.objects.filter(question__in=question_ids)

        responses.delete()
        choices.delete()
        questions.delete()

    def create_essay_questions(self, event, dry_run):
        """Create essay/text questions and migrate data"""
        self.stdout.write("\n=== Creating Essay Questions ===")

        essay_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_essay',
            question_text=(
                'At MIT Reality Hack, teamwork and communication are critical to '
                'success. How do you see yourself supporting your team in this respect?'
            ),
            question_type='L',
            order=5,
            required=True,
            max_length=2000,
            placeholder_text='Enter your response here.'
        )
        self.stdout.write(f"Created question: {essay_q.question_key}")

        if not dry_run:
            self.migrate_essay_responses(event, essay_q)

    def migrate_essay_responses(self, event, essay_q):
        """Migrate existing essay responses"""
        self.stdout.write("\n  Migrating existing essay responses...")

        applications = Application.objects.for_event(event).all()
        migrated_count = 0

        for app in applications:
            if app.theme_essay:
                try:
                    ApplicationResponse.objects.create(
                        application=app,
                        question=essay_q,
                        text_response=app.theme_essay
                    )
                    migrated_count += 1
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(
                            "  Warning: Failed to migrate theme_essay for "
                            f"{app.email}: {e}"
                        )
                    )

        self.stdout.write(
            "  Migrated {migrated_count} essay responses from "
            f"{applications.count()} applications"
        )

    def create_theme_questions(self, event, dry_run):
        """Create theme-related questions and migrate data"""
        self.stdout.write("\n=== Creating Theme Questions ===")

        # Standalone question: theme_interest_track_one
        track_one_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_interest_track_one',
            question_text=(
                'Are you interested in participating in programming focused on '
                'startups and entrepreneurship? Please indicate your interest here and '
                'we will follow up.'
            ),
            question_type='S',
            order=10,
            required=True
        )
        self.stdout.write(f"Created question: {track_one_q.question_key}")

        ApplicationQuestionChoice.objects.create(
            question=track_one_q,
            choice_key='Y',
            choice_text='Yes',
            order=1,
        )
        ApplicationQuestionChoice.objects.create(
            question=track_one_q,
            choice_key='N',
            choice_text='No',
            order=2,
        )
        self.stdout.write(f"  Created {track_one_q.choices.count()} choices")

        # Parent question: theme_interest_track_two
        parent_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_interest_track_two',
            question_text='Are you interested in hacking on Apple Vision Pro?',
            question_type='S',  # Single choice
            order=20,
            required=True
        )
        self.stdout.write(f"Created question: {parent_q.question_key}")

        # Parent choices
        ApplicationQuestionChoice.objects.create(
            question=parent_q,
            choice_key='Y',
            choice_text='Yes',
            order=1,
            # event=event
        )
        ApplicationQuestionChoice.objects.create(
            question=parent_q,
            choice_key='N',
            choice_text='No',
            order=2,
            # event=event
        )
        self.stdout.write(f"  Created {parent_q.choices.count()} choices")

        # Sub-question 1: theme_detail_one
        detail_one_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_detail_one',
            question_text=(
                "Do you meet all of the minimum system requirements? This means you "
                "MUST have an Apple silicon Mac (M1, M2, etc.) to develop for visionOS."
                " Please note that this is a hard requirement for being on a Vision Pro"
                "team. These requirements are set by Apple and we unfortunately won't "
                "have Mac hardware to check out."
            ),
            question_type='S',
            order=21,
            required=True,
            parent_question=parent_q,
            trigger_choices=['Y']
        )
        self.stdout.write(f"Created question: {detail_one_q.question_key}")

        ApplicationQuestionChoice.objects.create(
            question=detail_one_q, choice_key='Y', choice_text='Yes', order=1,
            # event=event
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_one_q, choice_key='N', choice_text='No', order=2,
            # event=event
        )
        self.stdout.write(f"  Created {detail_one_q.choices.count()} choices")

        # Sub-question 2: theme_detail_two
        detail_two_q = ApplicationQuestion.objects.create(
            event=event,
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
            question_type='S',
            order=22,
            required=True,
            parent_question=parent_q,
            trigger_choices=['Y']
        )
        self.stdout.write(f"Created question: {detail_two_q.question_key}")

        ApplicationQuestionChoice.objects.create(
            question=detail_two_q, choice_key='Y', choice_text='Yes', order=1,
            # event=event
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_two_q, choice_key='N', choice_text='No', order=2,
            # event=event
        )
        self.stdout.write(f"  Created {detail_two_q.choices.count()} choices")

        # Sub-question 3: theme_detail_three
        detail_three_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_detail_three',
            question_text=(
                "Do you own a Vision Pro that you are willing to bring to support your "
                "team? You will not be expected to allow your teammates to use your "
                "device if you are uncomfortable doing so. We will set this expectation"
                " during opening ceremony."
            ),
            question_type='S',
            order=23,
            required=True,
            parent_question=parent_q,
            trigger_choices=['Y']
        )
        self.stdout.write(f"Created question: {detail_three_q.question_key}")

        ApplicationQuestionChoice.objects.create(
            question=detail_three_q, choice_key='Y', choice_text='Yes', order=1,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_three_q, choice_key='N', choice_text='No', order=2,
        )
        self.stdout.write(f"  Created {detail_three_q.choices.count()} choices")

        if not dry_run:
            self.migrate_theme_responses(
                event,
                track_one_q,
                parent_q, detail_one_q,
                detail_two_q,
                detail_three_q
            )

    def migrate_theme_responses(
        self, event, track_one_q, parent_q, detail_one_q, detail_two_q, detail_three_q
    ):
        """Migrate existing theme responses"""
        self.stdout.write("\n  Migrating existing theme responses...")

        applications = Application.objects.for_event(event).all()
        migrated_count = 0

        for app in applications:
            # Migrate theme_interest_track_one
            if (
                app.theme_interest_track_one and
                app.theme_interest_track_one in ['Y', 'N']
            ):
                try:
                    response = ApplicationResponse.objects.create(
                        application=app,
                        question=track_one_q,
                    )
                    choice = track_one_q.choices.get(
                        choice_key=app.theme_interest_track_one
                    )
                    response.selected_choices.add(choice)
                    response.update_selected_snapshot()
                    migrated_count += 1
                except ApplicationQuestionChoice.DoesNotExist as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Warning: Choice not found for {app.email}: {e}"
                        )
                    )

            # Migrate parent question (theme_interest_track_two)
            # Check for explicit values (not None or empty string)
            if (
                app.theme_interest_track_two and
                app.theme_interest_track_two in ['Y', 'N']
            ):
                try:
                    response = ApplicationResponse.objects.create(
                        application=app,
                        question=parent_q,
                    )
                    choice = parent_q.choices.get(
                        choice_key=app.theme_interest_track_two
                    )
                    response.selected_choices.add(choice)
                    response.update_selected_snapshot()
                    migrated_count += 1

                    # Only migrate sub-questions if parent was 'Y'
                    if app.theme_interest_track_two == 'Y':
                        # Migrate detail_one
                        if app.theme_detail_one and app.theme_detail_one in ['Y', 'N']:
                            detail_response = ApplicationResponse.objects.create(
                                application=app,
                                question=detail_one_q,
                            )
                            detail_choice = detail_one_q.choices.get(
                                choice_key=app.theme_detail_one
                            )
                            detail_response.selected_choices.add(detail_choice)
                            detail_response.update_selected_snapshot()
                            migrated_count += 1

                        # Migrate detail_two
                        if app.theme_detail_two and app.theme_detail_two in ['Y', 'N']:
                            detail_response = ApplicationResponse.objects.create(
                                application=app,
                                question=detail_two_q,
                            )
                            detail_choice = detail_two_q.choices.get(
                                choice_key=app.theme_detail_two
                            )
                            detail_response.selected_choices.add(detail_choice)
                            detail_response.update_selected_snapshot()
                            migrated_count += 1

                        # Migrate detail_three
                        if (
                            app.theme_detail_three and
                            app.theme_detail_three in ['Y', 'N']
                        ):
                            detail_response = ApplicationResponse.objects.create(
                                application=app,
                                question=detail_three_q,
                            )
                            detail_choice = detail_three_q.choices.get(
                                choice_key=app.theme_detail_three
                            )
                            detail_response.selected_choices.add(detail_choice)
                            detail_response.update_selected_snapshot()
                            migrated_count += 1
                except ApplicationQuestionChoice.DoesNotExist as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Warning: Choice not found for {app.email}: {e}"
                        )
                    )

        self.stdout.write(
            "  Migrated {migrated_count} responses from "
            f"{applications.count()} applications"
        )

    def create_hardware_questions(self, event, dry_run):
        """Create hardware-related questions and migrate data"""
        self.stdout.write("\n=== Creating Hardware Questions ===")

        # Parent question: hardware_hack_interest
        parent_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='hardware_hack_interest',
            question_text=(
                "How interested would you be in participating in The Hardware Hack this"
                " year? The Hardware Hack is a special hand-on track where participants"
                " use hardware kits to design XR devices that interface with our bodies"
                " and with our surroundings."
            ),
            question_type='S',
            order=30,
            required=False
        )
        self.stdout.write(f"Created question: {parent_q.question_key}")

        # Parent choices
        ApplicationQuestionChoice.objects.create(
            question=parent_q,
            choice_key='A',
            choice_text="Not at all interested; I'll pass",
            order=1,
            # event=event
        )
        ApplicationQuestionChoice.objects.create(
            question=parent_q,
            choice_key='B',
            choice_text="Some mild interest",
            order=2,
            # event=event
        )
        ApplicationQuestionChoice.objects.create(
            question=parent_q,
            choice_key='C',
            choice_text="Most likely",
            order=3,
            # event=event
        )
        ApplicationQuestionChoice.objects.create(
            question=parent_q,
            choice_key='D',
            choice_text="100%; I want to join",
            order=4,
            # event=event
        )
        self.stdout.write(f"  Created {parent_q.choices.count()} choices")

        # Sub-question: hardware_hack_detail
        detail_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='hardware_hack_detail',
            question_text=(
                'Do you have any prior experience building custom hardware in these'
                ' areas?'
            ),
            question_type='M',
            order=31,
            required=False,
            parent_question=parent_q,
            trigger_choices=['B', 'C', 'D']
        )
        self.stdout.write(f"Created question: {detail_q.question_key}")

        # Detail choices
        ApplicationQuestionChoice.objects.create(
            question=detail_q, choice_key='A', choice_text='3D Printing', order=1,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_q, choice_key='B', choice_text='Soldering', order=2,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_q, choice_key='C', choice_text='Circuits', order=3,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_q, choice_key='D', choice_text='Arduino', order=4,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_q, choice_key='E', choice_text='ESP32', order=5,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_q, choice_key='F', choice_text='Unity', order=6,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_q,
            choice_key='G',
            choice_text='Physical Prototyping',
            order=7,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_q,
            choice_key='H',
            choice_text='I have no prior experience',
            order=8,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_q, choice_key='O', choice_text='Other', order=9,
        )
        self.stdout.write(f"  Created {detail_q.choices.count()} choices")

        self.migrate_hardware_responses(event, parent_q, detail_q)

    def migrate_hardware_responses(self, event, parent_q, detail_q):
        """Migrate existing hardware responses"""
        self.stdout.write("\n  Migrating existing hardware responses...")

        applications = Application.objects.for_event(event).all()
        migrated_count = 0

        for app in applications:
            # Migrate parent question (hardware_hack_interest)
            # Check for valid choice values
            valid_choices = ['A', 'B', 'C', 'D']
            if (app.hardware_hack_interest and
                    app.hardware_hack_interest in valid_choices):
                try:
                    response = ApplicationResponse.objects.create(
                        application=app,
                        question=parent_q,
                    )
                    choice = parent_q.choices.get(
                        choice_key=app.hardware_hack_interest
                    )
                    response.selected_choices.add(choice)
                    response.update_selected_snapshot()
                    migrated_count += 1

                    # Only migrate detail if parent was B, C, or D
                    if app.hardware_hack_interest in ['B', 'C', 'D']:
                        if app.hardware_hack_detail:
                            detail_response = (
                                ApplicationResponse.objects.create(
                                    application=app,
                                    question=detail_q,
                                )
                            )

                            selected_keys = (
                                list(app.hardware_hack_detail)
                                if app.hardware_hack_detail else []
                            )

                            for key in selected_keys:
                                key = key.strip()
                                try:
                                    detail_choice = (
                                        detail_q.choices.get(choice_key=key)
                                    )
                                    detail_response.selected_choices.add(
                                        detail_choice
                                    )
                                except ApplicationQuestionChoice.DoesNotExist:
                                    self.stdout.write(
                                        self.style.WARNING(
                                            f"  Warning: Choice '{key}' "
                                            f"not found for {app.email}"
                                        )
                                    )

                            detail_response.update_selected_snapshot()
                            migrated_count += 1
                except ApplicationQuestionChoice.DoesNotExist as e:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  Warning: Choice not found for "
                            f"{app.email}: {e}"
                        )
                    )

        self.stdout.write(
            f"  Migrated {migrated_count} responses from "
            f"{applications.count()} applications"
        )
