# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from waffle.models import Switch

from ed2go.constants import ENABLED_ED2GO_COMPLETION_REPORTING


def create_switch(apps, schema_editor):
    """Create a switch for sending automatic completion reports."""
    Switch.objects.get_or_create(
        name=ENABLED_ED2GO_COMPLETION_REPORTING, defaults={'active': False}
    )


def remove_switch(apps, schema_editor):
    """Remove automatic completion reports switch."""
    Switch.objects.filter(name=ENABLED_ED2GO_COMPLETION_REPORTING).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ed2go', '0001_initial'),
        ('ed2go', '0006_auto_20180302_0749')
    ]
    operations = [
        migrations.RunPython(create_switch, remove_switch)
    ]
