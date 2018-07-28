# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import jsonfield.fields


class Migration(migrations.Migration):

    dependencies = [
        ('ed2go', '0009_auto_20180723_1119'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='subsection',
            name='chapter_progress',
        ),
        migrations.RemoveField(
            model_name='unit',
            name='subsection',
        ),
        migrations.AddField(
            model_name='chapterprogress',
            name='subsections',
            field=jsonfield.fields.JSONField(default=dict),
        ),
        migrations.AlterField(
            model_name='chapterprogress',
            name='completion_profile',
            field=models.ForeignKey(related_name='chapterprogress', to='ed2go.CompletionProfile'),
        ),
        migrations.DeleteModel(
            name='SubSection',
        ),
        migrations.DeleteModel(
            name='Unit',
        ),
    ]
