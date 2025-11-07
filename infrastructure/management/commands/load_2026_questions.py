"""
Management command to load 2026 application questions for Reality Hack at MIT 2026.

Usage:
    python manage.py load_2026_questions
    python manage.py load_2026_questions --dry-run
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from infrastructure.models import (
    Event, ApplicationQuestion, 
    ApplicationQuestionChoice
)


class Command(BaseCommand):
    help = 'Load 2026 application questions for Reality Hack at MIT 2026'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be created without making changes'
        )
        parser.add_argument(
            '--delete-existing',
            action='store_true',
            help='Delete existing questions for this event before creating new ones'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        delete_existing = options['delete_existing']

        # Find the 2026 event
        try:
            event = Event.objects.get(name='Reality Hack at MIT 2026')
            self.stdout.write(f"Found event: {event.name} (ID: {event.id})")
        except Event.DoesNotExist:
            self.stdout.write(self.style.ERROR(
                "Event 'Reality Hack at MIT 2026' not found. Please create it first."
            ))
            return
        except Event.MultipleObjectsReturned:
            self.stdout.write(self.style.ERROR(
                "Multiple events found with name 'Reality Hack at MIT 2026'. "
                "Please ensure only one exists."
            ))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING(
                "DRY RUN MODE - No changes will be made"
            ))

        with transaction.atomic():
            if delete_existing and not dry_run:
                self.delete_existing(event)

            self.create_essay_questions(event)
            self.create_theme_questions(event)
            self.create_hardware_questions(event)

            if dry_run:
                self.stdout.write(self.style.WARNING(
                    "DRY RUN COMPLETE - Rolling back transaction"
                ))
                transaction.set_rollback(True)
            else:
                self.stdout.write(self.style.SUCCESS(
                    "2026 questions loaded successfully!"
                ))

    def delete_existing(self, event):
        """Delete existing questions for this event"""
        self.stdout.write("\n=== Deleting Existing Questions ===")
        questions = ApplicationQuestion.objects.filter(event=event)
        count = questions.count()
        questions.delete()
        self.stdout.write(f"Deleted {count} existing questions")

    def create_essay_questions(self, event):
        """Create essay/text questions"""
        self.stdout.write("\n=== Creating Essay Questions ===")

        # Question 1: Original essay question
        essay_q1 = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_essay',
            question_text=(
                'At Reality Hack, teamwork and communication are critical to '
                'success. How do you see yourself supporting your team in this respect?'
            ),
            question_type='L',
            order=1,
            required=True,
            max_length=2000,
            placeholder_text='Enter your response here.'
        )
        self.stdout.write(f"Created question: {essay_q1.question_key}")

        # Question 2: New essay question for 2026
        essay_q2 = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_essay_follow_up',
            question_text=(
                'When you think of "Dreams," what do you think of? How do you think '
                'XR and AI technologies can help us with achieving your vision of "Dreams"?'
            ),
            question_type='L',
            order=2,
            required=True,
            max_length=2000,
            placeholder_text='Enter your response here.'
        )
        self.stdout.write(f"Created question: {essay_q2.question_key}")

    def create_theme_questions(self, event):
        """Create theme-related questions"""
        self.stdout.write("\n=== Creating Theme Questions ===")

        # Question 3: Startup/entrepreneurship interest
        track_one_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_interest_track_one',
            question_text=(
                'Are you interested in programming focused on startups and'
                ' entrepreneurship?'
            ),
            question_type='S',
            order=3,
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

        # Question 4: Vision Pro / AI glasses interest (CHANGED TO MULTIPLE CHOICE)
        track_two_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_interest_track_two',
            question_text='Are you interested in hacking on Apple Vision Pro or AI glasses?',
            question_type='M',  # Changed to Multiple Choice
            order=4,
            required=False
        )
        self.stdout.write(f"Created question: {track_two_q.question_key}")

        ApplicationQuestionChoice.objects.create(
            question=track_two_q,
            choice_key='VP',
            choice_text='Apple Vision Pro',
            order=1,
        )
        ApplicationQuestionChoice.objects.create(
            question=track_two_q,
            choice_key='AI',
            choice_text='AI glasses',
            order=2,
        )
        self.stdout.write(f"  Created {track_two_q.choices.count()} choices")

        # Question 5: Hardware platform interest (NEW - STANDALONE)
        detail_one_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_detail_one',
            question_text=(
                "If you're interested in the hardware hack, which hardware platforms "
                "would you be interested in hacking on?"
            ),
            question_type='S',
            order=5,
            required=False,
        )
        self.stdout.write(f"Created question: {detail_one_q.question_key}")

        ApplicationQuestionChoice.objects.create(
            question=detail_one_q,
            choice_key='ARD',
            choice_text='Arduino: [Discover the New Arduino UNO Q: The All-In One Toolbox](https://www.arduino.cc/product-uno-q/)',
            order=1,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_one_q,
            choice_key='RUB',
            choice_text='Rubik PI: [Edge AI Dev Kit](https://rubikpi.ai/)',
            order=2,
        )
        self.stdout.write(f"  Created {detail_one_q.choices.count()} choices")

        # Question 6: Bringing previous project (NEW - STANDALONE)
        detail_two_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_detail_two',
            question_text=(
                "Would you be interested in bringing a previous Immerse the Bay project, "
                "Reality Hack project, or other hackathon project that you have already "
                "started working on to Reality Hack? This track would not qualify for any "
                "hackathon tracks except its own track to ensure fairness. You won't need "
                "to decide on participating now but will need to decide by the time you "
                "RSVP if you get accepted."
            ),
            question_type='S',
            order=6,
            required=False,
        )
        self.stdout.write(f"Created question: {detail_two_q.question_key}")

        ApplicationQuestionChoice.objects.create(
            question=detail_two_q,
            choice_key='Y',
            choice_text='Yes',
            order=1,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_two_q,
            choice_key='N',
            choice_text='No',
            order=2,
        )
        self.stdout.write(f"  Created {detail_two_q.choices.count()} choices")

        # Question 7: Immersive media production (NEW - STANDALONE)
        detail_three_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='theme_detail_three',
            question_text='Would you be interested in working with immersive media production equipment?',
            question_type='S',
            order=7,
            required=False,
        )
        self.stdout.write(f"Created question: {detail_three_q.question_key}")

        ApplicationQuestionChoice.objects.create(
            question=detail_three_q,
            choice_key='Y',
            choice_text='Yes',
            order=1,
        )
        ApplicationQuestionChoice.objects.create(
            question=detail_three_q,
            choice_key='N',
            choice_text='No',
            order=2,
        )
        self.stdout.write(f"  Created {detail_three_q.choices.count()} choices")

    def create_hardware_questions(self, event):
        """Create hardware-related questions"""
        self.stdout.write("\n=== Creating Hardware Questions ===")

        # Question 8: Hardware hack interest
        parent_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='hardware_hack_interest',
            question_text=(
                "How interested would you be in participating in the Hardware Hack this "
                "year? The Hardware Hack is a specific track where teams are supported by "
                "workshops, mentors, and resources to build your own XR hardware (like "
                "haptics, sensing, controllers and more) and make it work with an XR headset. "
                "Activities involve building circuits, 3D printing, prototyping, and game "
                "engine work. No prior hardware experience is necessary. We are using this "
                "question to measure interest only."
            ),
            question_type='S',
            order=8,
            required=False
        )
        self.stdout.write(f"Created question: {parent_q.question_key}")

        ApplicationQuestionChoice.objects.create(
            question=parent_q,
            choice_key='A',
            choice_text="Not at all interested, I'll pass",
            order=1,
        )
        ApplicationQuestionChoice.objects.create(
            question=parent_q,
            choice_key='B',
            choice_text="Some mild interest",
            order=2,
        )
        ApplicationQuestionChoice.objects.create(
            question=parent_q,
            choice_key='C',
            choice_text="Most likely",
            order=3,
        )
        ApplicationQuestionChoice.objects.create(
            question=parent_q,
            choice_key='D',
            choice_text="100% I want to join",
            order=4,
        )
        self.stdout.write(f"  Created {parent_q.choices.count()} choices")

        # Question 9: Hardware experience (CONDITIONAL on Q8)
        detail_q = ApplicationQuestion.objects.create(
            event=event,
            question_key='hardware_hack_detail',
            question_text='Do you have any prior experience building custom hardware in these areas?',
            question_type='M',
            order=9,
            required=False,
            parent_question=parent_q,
            trigger_choices=['B', 'C', 'D']
        )
        self.stdout.write(f"Created question: {detail_q.question_key}")

        ApplicationQuestionChoice.objects.create(
            question=detail_q, choice_key='A', choice_text='3D printing', order=1,
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