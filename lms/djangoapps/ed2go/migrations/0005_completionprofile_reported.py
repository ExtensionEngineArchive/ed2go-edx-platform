# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ed2go', '0004_auto_20180131_0646'),
    ]

    operations = [
        migrations.AddField(
            model_name='completionprofile',
            name='reported',
            field=models.BooleanField(default=False),
        ),
    ]
