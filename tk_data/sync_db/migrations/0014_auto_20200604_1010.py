# Generated by Django 3.0.6 on 2020-06-04 10:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sync_db', '0013_auto_20200603_0920'),
    ]

    operations = [
        migrations.AlterField(
            model_name='persoonreis',
            name='doel',
            field=models.TextField(blank=True, null=True),
        ),
    ]
