# Generated by Django 4.2.2 on 2024-10-15 20:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0025_application_experience_contribution_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='application',
            name='disabilities',
        ),
        migrations.RemoveField(
            model_name='application',
            name='disabilities_other',
        ),
        migrations.RemoveField(
            model_name='application',
            name='disability_accommodations',
        ),
    ]