# Generated by Django 2.0.3 on 2020-02-24 13:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ApiManager', '0002_auto_20200212_1525'),
    ]

    operations = [
        migrations.AlterField(
            model_name='fileinfo',
            name='file_path',
            field=models.CharField(default='', max_length=250, verbose_name='文件路径'),
        ),
        migrations.AlterField(
            model_name='fileinfo',
            name='name',
            field=models.CharField(max_length=200, verbose_name='文件名称'),
        ),
    ]
