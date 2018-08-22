# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ed2go', '0011_completionprofile_reference_id'),
    ]

    operations = [
        migrations.RenameField(
            model_name='completionprofile',
            old_name='reported',
            new_name='to_report',
        ),
    ]
