# Generated by Django 2.0.3 on 2019-08-28 19:51

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('ApiManager', '0002_auto_20190813_1708'),
    ]

    operations = [
        migrations.CreateModel(
            name='FileInfo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('update_time', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('name', models.CharField(max_length=50, verbose_name='文件名称')),
                ('belong_project', models.CharField(max_length=50, verbose_name='所属项目')),
                ('belong_module', models.CharField(max_length=50, verbose_name='所属模块')),
                ('author', models.CharField(max_length=20, verbose_name='上传人员')),
                ('create_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='上传时间')),
                ('file_size', models.IntegerField(default=0, verbose_name='文件大小')),
            ],
            options={
                'verbose_name': '上传文件管理',
                'db_table': 'FileInfo',
            },
        ),
    ]