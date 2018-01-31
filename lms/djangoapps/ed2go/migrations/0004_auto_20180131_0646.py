# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import openedx.core.djangoapps.xmodule_django.models


class Migration(migrations.Migration):

    dependencies = [
        ('ed2go', '0003_remove_completionprofile_registration_key'),
    ]

    operations = [
        migrations.AlterField(
            model_name='completionprofile',
            name='course_key',
            field=openedx.core.djangoapps.xmodule_django.models.CourseKeyField(max_length=255, db_index=True),
        ),
    ]
