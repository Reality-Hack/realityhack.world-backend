# Generated by Django 4.2.2 on 2024-08-30 19:36

from django.db import migrations
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0023_merge_20240126_0347'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendee',
            name='prefers_destiny_hardware',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('H', 'Hardware Hack'), ('M', 'Meta'), ('Q', 'Snapdragon Spaces'), ('X', 'XREAL'), ('S', 'Snap Spectacles')], max_length=11, null=True),
        ),
    ]
