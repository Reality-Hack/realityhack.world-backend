# Generated by Django 4.2.2 on 2024-01-17 06:30

import multiselectfield.db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0014_alter_hardware_image_alter_hardware_tags'),
    ]

    operations = [
        migrations.AlterField(
            model_name='hardware',
            name='tags',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('AC', 'Accessory'), ('SE', 'Sensor'), ('VR', 'Virtual Reality'), ('AR', 'Augmented Reality'), ('MR', 'Mixed Reality'), ('CO', 'Computer'), ('HA', 'Haptics'), ('CA', 'Camera'), ('TA', 'Tablet'), ('HD', 'Holographic Display')], max_length=41, null=True),
        ),
    ]