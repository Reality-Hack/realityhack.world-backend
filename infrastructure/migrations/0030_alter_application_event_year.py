# Generated by Django 4.2.2 on 2024-10-25 03:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0029_alter_application_race_ethnic_group'),
    ]

    operations = [
        migrations.AlterField(
            model_name='application',
            name='event_year',
            field=models.IntegerField(default=2025),
        ),
    ]
