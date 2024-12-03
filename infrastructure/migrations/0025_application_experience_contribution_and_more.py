# Generated by Django 4.2.2 on 2024-10-15 16:41

from django.db import migrations, models
import multiselectfield.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('infrastructure', '0024_alter_attendee_prefers_destiny_hardware'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='experience_contribution',
            field=models.TextField(blank=True, max_length=2000, null=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='participation_role',
            field=models.CharField(choices=[('A', 'Digital/Creative Designer'), ('D', 'Developer'), ('S', 'Domain or other Specialized Skill Expert'), ('P', 'Project Manager')], default='S', max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='application',
            name='previous_participation',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('A', '2016'), ('B', '2017'), ('C', '2018'), ('D', '2019'), ('E', '2020'), ('F', '2022'), ('G', '2023'), ('H', '2024')], max_length=16, null=True),
        ),
        migrations.AlterField(
            model_name='attendee',
            name='participation_role',
            field=models.CharField(choices=[('A', 'Digital/Creative Designer'), ('D', 'Developer'), ('S', 'Domain or other Specialized Skill Expert'), ('P', 'Project Manager')], default='S', max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='workshop',
            name='recommended_for',
            field=multiselectfield.db.fields.MultiSelectField(choices=[('A', 'Digital/Creative Designer'), ('D', 'Developer'), ('S', 'Domain or other Specialized Skill Expert'), ('P', 'Project Manager')], max_length=8, null=True),
        ),
    ]