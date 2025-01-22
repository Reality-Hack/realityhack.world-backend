# Generated by Django 4.2.2 on 2025-01-22 01:05

from django.db import migrations, models
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0038_remove_team_track'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendee',
            name='prefers_destiny_hardware',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('M', 'Best Lifestyle Experience with Meta Quest'), ('Q', 'Best in World Building with Horizon Worlds'), ('T', 'Best use of Haptics'), ('S', 'Snap Spectacles Challenge'), ('N', 'Pioneering a Neuroadaptive Future'), ('X', 'Best Use of ShapesXR'), ('Y', 'Best use of STYLY'), ('L', 'Best use of Lambda AI Cloud Services')], max_length=17, null=True),
        ),
        migrations.AlterField(
            model_name='destinyteam',
            name='destiny_hardware',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('M', 'Best Lifestyle Experience with Meta Quest'), ('Q', 'Best in World Building with Horizon Worlds'), ('T', 'Best use of Haptics'), ('S', 'Snap Spectacles Challenge'), ('N', 'Pioneering a Neuroadaptive Future'), ('X', 'Best Use of ShapesXR'), ('Y', 'Best use of STYLY'), ('L', 'Best use of Lambda AI Cloud Services')], max_length=30),
        ),
        migrations.AlterField(
            model_name='hardware',
            name='relates_to_destiny_hardware',
            field=models.CharField(choices=[('M', 'Best Lifestyle Experience with Meta Quest'), ('Q', 'Best in World Building with Horizon Worlds'), ('T', 'Best use of Haptics'), ('S', 'Snap Spectacles Challenge'), ('N', 'Pioneering a Neuroadaptive Future'), ('X', 'Best Use of ShapesXR'), ('Y', 'Best use of STYLY'), ('L', 'Best use of Lambda AI Cloud Services')], max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='team',
            name='destiny_hardware',
            field=multiselectfield.db.fields.MultiSelectField(blank=True, choices=[('M', 'Best Lifestyle Experience with Meta Quest'), ('Q', 'Best in World Building with Horizon Worlds'), ('T', 'Best use of Haptics'), ('S', 'Snap Spectacles Challenge'), ('N', 'Pioneering a Neuroadaptive Future'), ('X', 'Best Use of ShapesXR'), ('Y', 'Best use of STYLY'), ('L', 'Best use of Lambda AI Cloud Services')], max_length=30),
        ),
    ]
