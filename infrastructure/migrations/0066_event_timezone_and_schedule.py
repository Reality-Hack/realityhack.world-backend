from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import migrations, models
import multiselectfield.db.fields

import infrastructure.utils.event_dates

EVENT_2026_NAME = 'Reality Hack at MIT 2026'

# Values previously hardcoded in email templates and frontend copy.
EVENT_2026_VALUES = {
    'rsvp_deadline': datetime(2026, 1, 11, 23, 59, tzinfo=ZoneInfo('America/New_York')),
    'discord_url': 'https://discord.gg/XfDXqwTPfv',
    'special_tracks_url': 'https://www.realityhackatmit.com/2026-special-tracks',
    'parent_consent_form_url': (
        'https://na4.docusign.net/Member/PowerFormSigning.aspx'
        '?PowerFormId=64125d74-ae74-46bf-bbab-f7fb119856c2&env=na4'
        '&acct=83645d39-e03b-40e3-b225-a975e8c6f8cc&v=2'
    ),
    'discounts_page_url': (
        'https://mitrealityhack.notion.site/'
        'Reality-Hack-at-MIT-2026-Group-Accommodation-Rates-1978c5dbe2bd81949e9fe2c72efcc2b4'
    ),
}


def backfill_event_schedule(apps, schema_editor):
    """
    One-off backfill of mentor/judging windows for existing events.

    Going forward the frontend owns these defaults (mentors start with the
    event and leave a day early; judges attend only the last day) and admins
    can override them in the event edit form.
    """
    Event = apps.get_model('infrastructure', 'Event')
    for event in Event.objects.all():
        tz = ZoneInfo(event.timezone)
        local_start = event.start_date.astimezone(tz)
        local_end = event.end_date.astimezone(tz)

        judging_start = local_end.replace(
            hour=local_start.hour, minute=local_start.minute, second=0, microsecond=0
        )
        if judging_start > local_end:
            judging_start = local_end.replace(hour=0, minute=0, second=0, microsecond=0)

        event.mentor_start_date = event.mentor_start_date or event.start_date
        event.mentor_end_date = event.mentor_end_date or local_end - timedelta(days=1)
        event.judging_start_date = event.judging_start_date or judging_start
        event.judging_end_date = event.judging_end_date or event.end_date

        if event.name == EVENT_2026_NAME:
            for field, value in EVENT_2026_VALUES.items():
                if getattr(event, field) is None:
                    setattr(event, field, value)

        event.save()


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0065_alter_application_unique_together_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='timezone',
            field=models.CharField(
                default='America/New_York',
                help_text='IANA timezone the event takes place in, e.g. America/New_York',
                max_length=64,
                validators=[infrastructure.utils.event_dates.validate_iana_timezone],
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='event',
            name='mentor_start_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='mentor_end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='judging_start_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='judging_end_date',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='rsvp_deadline',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='discord_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='special_tracks_url',
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='parent_consent_form_url',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='discounts_page_url',
            field=models.URLField(blank=True, max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='previous_participation',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('A', '2016'), ('B', '2017'), ('C', '2018'), ('D', '2019'), ('E', '2020'), ('F', '2022'), ('G', '2023'), ('H', '2024'), ('I', '2025'), ('J', '2026')], max_length=20, null=True),
        ),
        migrations.RunPython(backfill_event_schedule, migrations.RunPython.noop),
    ]
