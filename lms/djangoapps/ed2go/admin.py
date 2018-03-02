from django.contrib import admin

from ed2go.models import CompletionProfile, CourseSession


@admin.register(CompletionProfile)
class CompletionProfileAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'course_key', 'registration_key', 'active')


@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'course_key', 'created_at', 'last_activity_at', 'active')
