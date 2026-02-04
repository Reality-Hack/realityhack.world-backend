# Generated manually for event-scoped Track and DestinyHardware choices

import django.db.models.deletion
from django.db import migrations, models
import uuid


# Fixed UUID for Reality Hack at MIT 2025 event (from migration 0043)
FIRST_EVENT_UUID = uuid.UUID('888a5508-ea40-4453-84bc-a0e4a03e491b')


def seed_event_choices(apps, schema_editor):
    """Seed Track and DestinyHardware choices for the 2025 event."""
    Event = apps.get_model('infrastructure', 'Event')
    EventTrack = apps.get_model('infrastructure', 'EventTrack')
    EventDestinyHardware = apps.get_model('infrastructure', 'EventDestinyHardware')

    event = Event.objects.get(id=FIRST_EVENT_UUID)

    # Seed tracks (matching Track TextChoices)
    tracks = [
        ('C', 'Open Lab (AKA Community Hack)', 1),
        ('S', 'Connecting for Change with Social XR', 2),
        ('E', 'Augmented Design & Engineering', 3),
        ('D', 'Standing on the Shoulders of Sustainability', 4),
        ('A', 'AeroSpatial Exploration', 5),
        ('L', 'Augmented Intelligence', 6),
        ('H', 'Healthcare', 7),
    ]
    for code, name, order in tracks:
        EventTrack.objects.create(event=event, code=code, name=name, order=order)

    # Seed destiny hardware (matching DestinyHardware TextChoices)
    hardware = [
        ('M', 'Best MR Lifestyle App for Meta Quest', 1),
        ('Q', 'Best Lifestyle World with Meta Horizons Worlds', 2),
        ('T', 'Best use of Haptics', 3),
        ('S', 'Snap Spectacles Challenge', 4),
        ('N', 'Pioneering a Neuroadaptive Future', 5),
        ('X', 'Best Use of ShapesXR', 6),
        ('Y', 'Best use of STYLY', 7),
        ('L', 'Best use of Lambda AI Cloud Services', 8),
        ('U', 'Qualcomm IoT', 9),
        ('V', 'Best use of Apple Vision Pro', 10),
    ]
    for code, name, order in hardware:
        EventDestinyHardware.objects.create(event=event, code=code, name=name, order=order)

    print(f"✓ Seeded {len(tracks)} tracks and {len(hardware)} destiny hardware choices for {event.name}")


def reverse_seed(apps, schema_editor):
    """Remove seeded choices if migration is reversed."""
    EventTrack = apps.get_model('infrastructure', 'EventTrack')
    EventDestinyHardware = apps.get_model('infrastructure', 'EventDestinyHardware')

    EventTrack.objects.filter(event_id=FIRST_EVENT_UUID).delete()
    EventDestinyHardware.objects.filter(event_id=FIRST_EVENT_UUID).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0052_table_floor_table_notes_alter_location_building_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventTrack',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(help_text="Single char code like 'C', 'S'", max_length=1)),
                ('name', models.CharField(max_length=100)),
                ('order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_set', to='infrastructure.event')),
            ],
            options={
                'ordering': ['order'],
                'unique_together': {('event', 'code')},
            },
        ),
        migrations.CreateModel(
            name='EventDestinyHardware',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('code', models.CharField(help_text="Single char code like 'M', 'Q'", max_length=1)),
                ('name', models.CharField(max_length=100)),
                ('order', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_set', to='infrastructure.event')),
            ],
            options={
                'ordering': ['order'],
                'unique_together': {('event', 'code')},
            },
        ),
        # Seed the choices for the 2025 event
        migrations.RunPython(seed_event_choices, reverse_seed),
    ]
