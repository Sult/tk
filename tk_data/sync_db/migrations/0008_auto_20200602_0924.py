# Generated by Django 3.0.6 on 2020-06-02 09:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sync_db', '0007_auto_20200601_1406'),
    ]

    operations = [
        migrations.AlterField(
            model_name='zaak',
            name='groot_project',
            field=models.NullBooleanField(),
        ),
    ]