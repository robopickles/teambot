# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-10 14:30
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('botapp', '0001_initial'),
    ]

    operations = [
        migrations.RenameField(
            model_name='serviceaccount',
            old_name='user_setting',
            new_name='user_profile',
        ),
    ]
