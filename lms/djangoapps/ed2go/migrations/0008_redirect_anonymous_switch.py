# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from waffle.models import Switch

from ed2go.constants import REDIRECT_ANONYMOUS_TO_ED2GO_LOGIN


def create_switch(apps, schema_editor):
    """Create a switch for redirecting anonymous users to Ed2Go login page."""
    Switch.objects.get_or_create(
        name=REDIRECT_ANONYMOUS_TO_ED2GO_LOGIN, defaults={'active': False}
    )


def remove_switch(apps, schema_editor):
    """Remove automatic redirect switch."""
    Switch.objects.filter(name=REDIRECT_ANONYMOUS_TO_ED2GO_LOGIN).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('ed2go', '0001_initial'),
        ('ed2go', '0007_reporting_switch')
    ]
    operations = [
        migrations.RunPython(create_switch, remove_switch)
    ]
