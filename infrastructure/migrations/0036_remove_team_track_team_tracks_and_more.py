# Generated by Django 4.2.2 on 2025-01-21 19:44

from django.db import migrations, models
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ("infrastructure", "0035_team_devpost_url_team_github_url_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="team",
            name="track",
        ),
        migrations.AddField(
            model_name="team",
            name="tracks",
            field=multiselectfield.db.fields.MultiSelectField(
                blank=True,
                choices=[
                    ("F", "Founders Lab"),
                    ("C", "Open Lab (AKA Community Hack)"),
                    ("S", "Connecting for Change with Social XR"),
                    ("E", "Augmented Engineering"),
                    ("D", "Digitizing Sustainability"),
                    ("A", "AeroSpatial Exploration"),
                    ("L", "Augmented Intelligence"),
                    ("W", "Hardware hack"),
                    ("H", "Healthcare"),
                ],
                max_length=19,
            ),
        ),
        migrations.AlterField(
            model_name="attendee",
            name="intended_tracks",
            field=multiselectfield.db.fields.MultiSelectField(
                choices=[
                    ("F", "Founders Lab"),
                    ("C", "Open Lab (AKA Community Hack)"),
                    ("S", "Connecting for Change with Social XR"),
                    ("E", "Augmented Engineering"),
                    ("D", "Digitizing Sustainability"),
                    ("A", "AeroSpatial Exploration"),
                    ("L", "Augmented Intelligence"),
                    ("W", "Hardware hack"),
                    ("H", "Healthcare"),
                ],
                max_length=7,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="destinyteam",
            name="track",
            field=models.CharField(
                choices=[
                    ("F", "Founders Lab"),
                    ("C", "Open Lab (AKA Community Hack)"),
                    ("S", "Connecting for Change with Social XR"),
                    ("E", "Augmented Engineering"),
                    ("D", "Digitizing Sustainability"),
                    ("A", "AeroSpatial Exploration"),
                    ("L", "Augmented Intelligence"),
                    ("W", "Hardware hack"),
                    ("H", "Healthcare"),
                ],
                max_length=1,
                null=True,
            ),
        ),
    ]
