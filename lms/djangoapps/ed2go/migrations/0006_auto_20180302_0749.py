# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ed2go', '0005_completionprofile_reported'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='courseregistration',
            name='user',
        ),
        migrations.AddField(
            model_name='completionprofile',
            name='active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='completionprofile',
            name='registration_key',
            field=models.CharField(db_index=True, max_length=255, blank=True),
        ),
        migrations.DeleteModel(
            name='CourseRegistration',
        ),
    ]
