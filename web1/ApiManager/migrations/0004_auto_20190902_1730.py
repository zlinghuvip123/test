# Generated by Django 2.0.3 on 2019-09-02 17:30

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ApiManager', '0003_fileinfo'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='debugtalk',
            name='belong_project',
        ),
        migrations.DeleteModel(
            name='DebugTalk',
        ),
    ]
