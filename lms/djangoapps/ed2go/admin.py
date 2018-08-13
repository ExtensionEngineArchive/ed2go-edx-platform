from django.contrib import admin

from ed2go.models import CompletionProfile, CourseSession


@admin.register(CompletionProfile)
class CompletionProfileAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'course_key', 'registration_key', 'active')
    list_filter = ('user', 'course_key', 'active')
    search_fields = ('user', 'course_key')


@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'course_key', 'created_at', 'last_activity_at', 'closed_at', 'active')
    list_filter = ('user', 'course_key', 'active')
