# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ed2go', '0008_redirect_anonymous_switch'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChapterProgress',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('chapter_id', models.CharField(max_length=255, db_index=True)),
            ],
        ),
        migrations.CreateModel(
            name='SubSection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('subsection_id', models.CharField(max_length=255, db_index=True)),
                ('viewed', models.BooleanField(default=False)),
                ('chapter_progress', models.ForeignKey(related_name='subsection', to='ed2go.ChapterProgress')),
            ],
        ),
        migrations.CreateModel(
            name='Unit',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('unit_id', models.CharField(max_length=255, db_index=True)),
                ('type', models.CharField(max_length=255, choices=[(b'video', b'video'), (b'problem', b'problem')])),
                ('done', models.BooleanField(default=False)),
                ('subsection', models.ForeignKey(related_name='subsection_units', to='ed2go.SubSection')),
            ],
        ),
        migrations.RemoveField(
            model_name='completionprofile',
            name='problems',
        ),
        migrations.RemoveField(
            model_name='completionprofile',
            name='videos',
        ),
        migrations.AddField(
            model_name='chapterprogress',
            name='completion_profile',
            field=models.ForeignKey(to='ed2go.CompletionProfile'),
        ),
    ]
