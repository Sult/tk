# Generated by Django 3.0.6 on 2020-06-03 09:20

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('sync_db', '0012_auto_20200603_0917'),
    ]

    operations = [
        migrations.RenameField(
            model_name='activiteit',
            old_name='voortouw_commissie',
            new_name='voortouwcommissie',
        ),
    ]