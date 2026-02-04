# Generated manually for adding event-scoped track and hardware fields

import django.db.models.deletion
from django.db import migrations, models
import uuid


# Fixed UUID for Reality Hack at MIT 2025 event (from migration 0043)
FIRST_EVENT_UUID = uuid.UUID('888a5508-ea40-4453-84bc-a0e4a03e491b')


def migrate_legacy_to_event_scoped(apps, schema_editor):
    """
    Migrate existing char-based track/hardware selections to the new
    event-scoped M2M/FK fields for the 2025 event.
    """
    Event = apps.get_model('infrastructure', 'Event')
    EventTrack = apps.get_model('infrastructure', 'EventTrack')
    EventDestinyHardware = apps.get_model('infrastructure', 'EventDestinyHardware')
    Attendee = apps.get_model('infrastructure', 'Attendee')
    EventRsvp = apps.get_model('infrastructure', 'EventRsvp')
    Team = apps.get_model('infrastructure', 'Team')
    Hardware = apps.get_model('infrastructure', 'Hardware')
    DestinyTeam = apps.get_model('infrastructure', 'DestinyTeam')

    event = Event.objects.get(id=FIRST_EVENT_UUID)

    # Build lookup dicts for code -> EventTrack/EventDestinyHardware
    track_lookup = {t.code: t for t in EventTrack.objects.filter(event=event)}
    hardware_lookup = {h.code: h for h in EventDestinyHardware.objects.filter(event=event)}

    # Helper to parse MultiSelectField value
    # MultiSelectField can return MSFList (iterable) or string
    def parse_multiselect(value):
        if not value:
            return []
        # If it's already a list/iterable (MSFList), convert to list
        if hasattr(value, '__iter__') and not isinstance(value, str):
            return list(value)
        # If it's a string, split by comma
        if isinstance(value, str):
            return [v.strip() for v in value.split(',') if v.strip()]
        return []

    # Migrate Attendee
    for attendee in Attendee.objects.all():
        # intended_tracks -> intended_event_tracks
        if attendee.intended_tracks:
            for code in parse_multiselect(attendee.intended_tracks):
                if code in track_lookup:
                    attendee.intended_event_tracks.add(track_lookup[code])

        # prefers_destiny_hardware -> prefers_event_destiny_hardware
        if attendee.prefers_destiny_hardware:
            for code in parse_multiselect(attendee.prefers_destiny_hardware):
                if code in hardware_lookup:
                    attendee.prefers_event_destiny_hardware.add(hardware_lookup[code])

    # Migrate EventRsvp
    for rsvp in EventRsvp.objects.filter(event=event):
        if rsvp.intended_tracks:
            for code in parse_multiselect(rsvp.intended_tracks):
                if code in track_lookup:
                    rsvp.intended_event_tracks.add(track_lookup[code])

        if rsvp.prefers_destiny_hardware:
            for code in parse_multiselect(rsvp.prefers_destiny_hardware):
                if code in hardware_lookup:
                    rsvp.prefers_event_destiny_hardware.add(hardware_lookup[code])

    # Migrate Team
    for team in Team.objects.filter(event=event):
        if team.tracks:
            for code in parse_multiselect(team.tracks):
                if code in track_lookup:
                    team.event_tracks.add(track_lookup[code])

        if team.destiny_hardware:
            for code in parse_multiselect(team.destiny_hardware):
                if code in hardware_lookup:
                    team.event_destiny_hardware.add(hardware_lookup[code])

    # Migrate Hardware
    for hardware in Hardware.objects.filter(event=event):
        if hardware.relates_to_destiny_hardware:
            code = hardware.relates_to_destiny_hardware
            if code in hardware_lookup:
                hardware.relates_to_event_destiny_hardware = hardware_lookup[code]
                hardware.save()

    # Migrate DestinyTeam
    for destiny_team in DestinyTeam.objects.filter(event=event):
        if destiny_team.track:
            code = destiny_team.track
            if code in track_lookup:
                destiny_team.event_track = track_lookup[code]
                destiny_team.save()

        if destiny_team.destiny_hardware:
            for code in parse_multiselect(destiny_team.destiny_hardware):
                if code in hardware_lookup:
                    destiny_team.event_destiny_hardware.add(hardware_lookup[code])

    print("✓ Migrated legacy track/hardware selections to event-scoped fields")


def reverse_migration(apps, schema_editor):
    """Clear the new fields (legacy fields still contain the data)."""
    Attendee = apps.get_model('infrastructure', 'Attendee')
    EventRsvp = apps.get_model('infrastructure', 'EventRsvp')
    Team = apps.get_model('infrastructure', 'Team')
    Hardware = apps.get_model('infrastructure', 'Hardware')
    DestinyTeam = apps.get_model('infrastructure', 'DestinyTeam')

    for attendee in Attendee.objects.all():
        attendee.intended_event_tracks.clear()
        attendee.prefers_event_destiny_hardware.clear()

    for rsvp in EventRsvp.objects.all():
        rsvp.intended_event_tracks.clear()
        rsvp.prefers_event_destiny_hardware.clear()

    for team in Team.objects.all():
        team.event_tracks.clear()
        team.event_destiny_hardware.clear()

    Hardware.objects.all().update(relates_to_event_destiny_hardware=None)

    for destiny_team in DestinyTeam.objects.all():
        destiny_team.event_track = None
        destiny_team.event_destiny_hardware.clear()
        destiny_team.save()


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0053_eventtrack_eventdestinyhardware'),
    ]

    operations = [
        # Attendee fields
        migrations.AddField(
            model_name='attendee',
            name='intended_event_tracks',
            field=models.ManyToManyField(
                blank=True,
                help_text='Event-scoped track preferences',
                related_name='attendees_intended',
                to='infrastructure.eventtrack'
            ),
        ),
        migrations.AddField(
            model_name='attendee',
            name='prefers_event_destiny_hardware',
            field=models.ManyToManyField(
                blank=True,
                help_text='Event-scoped destiny hardware preferences',
                related_name='attendees_preferred',
                to='infrastructure.eventdestinyhardware'
            ),
        ),

        # EventRsvp fields
        migrations.AddField(
            model_name='eventrsvp',
            name='intended_event_tracks',
            field=models.ManyToManyField(
                blank=True,
                help_text='Event-scoped track preferences',
                related_name='rsvps_intended',
                to='infrastructure.eventtrack'
            ),
        ),
        migrations.AddField(
            model_name='eventrsvp',
            name='prefers_event_destiny_hardware',
            field=models.ManyToManyField(
                blank=True,
                help_text='Event-scoped destiny hardware preferences',
                related_name='rsvps_preferred',
                to='infrastructure.eventdestinyhardware'
            ),
        ),

        # Team fields
        migrations.AddField(
            model_name='team',
            name='event_tracks',
            field=models.ManyToManyField(
                blank=True,
                help_text='Event-scoped track selections',
                related_name='teams',
                to='infrastructure.eventtrack'
            ),
        ),
        migrations.AddField(
            model_name='team',
            name='event_destiny_hardware',
            field=models.ManyToManyField(
                blank=True,
                help_text='Event-scoped destiny hardware selections',
                related_name='teams',
                to='infrastructure.eventdestinyhardware'
            ),
        ),

        # Hardware field
        migrations.AddField(
            model_name='hardware',
            name='relates_to_event_destiny_hardware',
            field=models.ForeignKey(
                blank=True,
                help_text='Event-scoped destiny hardware association',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='hardware_items',
                to='infrastructure.eventdestinyhardware'
            ),
        ),

        # DestinyTeam fields
        migrations.AddField(
            model_name='destinyteam',
            name='event_track',
            field=models.ForeignKey(
                blank=True,
                help_text='Event-scoped track selection',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='destiny_teams',
                to='infrastructure.eventtrack'
            ),
        ),
        migrations.AddField(
            model_name='destinyteam',
            name='event_destiny_hardware',
            field=models.ManyToManyField(
                blank=True,
                help_text='Event-scoped destiny hardware selections',
                related_name='destiny_teams',
                to='infrastructure.eventdestinyhardware'
            ),
        ),

        # Data migration
        migrations.RunPython(migrate_legacy_to_event_scoped, reverse_migration),
    ]
