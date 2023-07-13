# Generated by Django 4.2.2 on 2023-07-13 17:44

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0003_attendee_application_alter_application_gender'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='email',
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name='attendee',
            name='application',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='infrastructure.application'),
        ),
        migrations.AlterField(
            model_name='attendee',
            name='metadata',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
