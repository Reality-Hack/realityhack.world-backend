# Generated by Django 4.2 on 2023-06-25 20:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='attendee',
            name='roles',
        ),
    ]
