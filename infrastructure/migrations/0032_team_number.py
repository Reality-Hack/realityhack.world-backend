# Generated by Django 4.2.2 on 2024-11-27 05:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0031_historicalmentorhelprequest_reporter_location_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='number',
            field=models.IntegerField(null=True),
        ),
    ]