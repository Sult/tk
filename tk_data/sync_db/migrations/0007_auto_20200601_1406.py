# Generated by Django 3.0.6 on 2020-06-01 14:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sync_db', '0006_auto_20200601_1330'),
    ]

    operations = [
        migrations.AlterField(
            model_name='document',
            name='onderwerp',
            field=models.TextField(blank=True, null=True),
        ),
    ]
