# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ed2go', '0010_auto_20180728_0858'),
    ]

    operations = [
        migrations.AddField(
            model_name='completionprofile',
            name='reference_id',
            field=models.IntegerField(null=True, blank=True),
        ),
    ]
