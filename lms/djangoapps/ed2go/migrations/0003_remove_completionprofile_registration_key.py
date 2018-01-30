# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ed2go', '0002_courseregistration'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='completionprofile',
            name='registration_key',
        ),
    ]
