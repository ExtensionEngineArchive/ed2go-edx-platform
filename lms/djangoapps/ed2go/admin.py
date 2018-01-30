from django.contrib import admin

from ed2go.models import CompletionProfile, CourseRegistration, CourseSession


@admin.register(CompletionProfile)
class CompletionProfileAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'course_key')


@admin.register(CourseRegistration)
class CourseRegistrationAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'course_key', 'registration_key')


@admin.register(CourseSession)
class CourseSessionAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'course_key', 'created_at', 'last_activity_at', 'active')
