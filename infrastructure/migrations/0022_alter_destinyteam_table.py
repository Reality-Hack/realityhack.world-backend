# Generated by Django 4.2.2 on 2024-01-25 22:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("infrastructure", "0021_merge_20240125_1613"),
    ]

    operations = [
        migrations.AlterField(
            model_name="destinyteam",
            name="table",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="infrastructure.table",
            ),
        ),
    ]
