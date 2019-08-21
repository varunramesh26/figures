# -*- coding: utf-8 -*-
# Generated by Django 1.11.15 on 2019-08-14 21:19
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('student', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='allow_certificate',
            field=models.BooleanField(default=1),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='bio',
            field=models.CharField(blank=True, max_length=3000, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='city',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='courseware',
            field=models.CharField(blank=True, default=b'course.xml', max_length=255),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='goals',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='language',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='location',
            field=models.CharField(blank=True, db_index=True, max_length=255),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='mailing_address',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='meta',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='courseenrollment',
            name='created',
            field=models.DateTimeField(null=True),
        ),
    ]
