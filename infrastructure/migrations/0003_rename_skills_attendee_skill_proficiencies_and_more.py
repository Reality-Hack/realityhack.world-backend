# Generated by Django 4.2 on 2023-06-23 05:28

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import multiselectfield.db.fields
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0002_rename_role_attendee_roles'),
    ]

    operations = [
        migrations.RenameField(
            model_name='attendee',
            old_name='skills',
            new_name='skill_proficiencies',
        ),
        migrations.RenameField(
            model_name='project',
            old_name='location',
            new_name='repository_location',
        ),
        migrations.AddField(
            model_name='hardware',
            name='description',
            field=models.TextField(blank=True, max_length=1000),
        ),
        migrations.AddField(
            model_name='hardware',
            name='image',
            field=models.URLField(default=None),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='hardware',
            name='name',
            field=models.CharField(default=None, max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='location',
            name='building',
            field=models.CharField(choices=[], default=None, max_length=2),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='project',
            name='name',
            field=models.CharField(default=None, max_length=50),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='project',
            name='submission_location',
            field=models.URLField(default=''),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='attendee',
            name='roles',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('P', 'Participant'), ('O', 'Organizer'), ('M', 'Mentor'), ('S', 'Sponsor')], max_length=3),
        ),
        migrations.AlterField(
            model_name='hardware',
            name='id',
            field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
        migrations.CreateModel(
            name='HardwareDevice',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('serial', models.CharField(max_length=100)),
                ('checked_out_to', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('hardware', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='infrastructure.hardware')),
            ],
        ),
    ]
