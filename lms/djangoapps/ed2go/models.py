import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.utils.timezone import now
from waffle import switch_is_active

from lms.djangoapps.courseware.courses import get_course
from lms.djangoapps.grades.models import PersistentCourseGrade
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from openedx.core.djangoapps.content.course_structures.models import CourseStructure
from openedx.core.djangoapps.xmodule_django.models import CourseKeyField
from student.models import CourseEnrollment

from ed2go.constants import ENABLED_ED2GO_COMPLETION_REPORTING
from ed2go.utils import XMLHandler, format_timedelta

LOG = logging.getLogger(__name__)


class CompletionProfile(models.Model):
    """
    Model that keeps track of the user's completion/progress in a given course.
    Metrics are defined by the Ed2go requirements, which are to track whenever
    a user has attempted to solve a problem and watched a video in a course.

    The progress is measured by the formula:
        0.5 * (#_of_attempted_problems / total_problems) + 0.5 * (#_of_watched_videos / total_videos)

    Additional metrics can be seen in the report() method of this model. For now
    they are extracted from existing models in Open edX and don't need
    to be included in this model.
    """
    PROBLEM_TYPES = ['problem']  # If there is a custom type that is observed include it here.

    user = models.ForeignKey(User)
    course_key = CourseKeyField(max_length=255, db_index=True)

    # Indicates whether we need to send a report update for this completion profile.
    # Should be set to False whenever course progress or session is updated.
    reported = models.BooleanField(default=False)

    registration_key = models.CharField(max_length=255, db_index=True, blank=True)
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        """
        Override of the default save() method. Whenever a new object is instantiated
        we collect all the video block and problem block IDs that are in the course
        in dictionaries where the item values represent if the user attempted/watched
        a problem/video (defaults to False).

        Creating an instance of this model enrolls the user into the course.
        """
        if self.pk is None:
            CourseEnrollment.enroll(self.user, self.course_key)
        super(CompletionProfile, self).save(*args, **kwargs)

    def deactivate(self):
        """Unenroll the user prior to deactivating this instance."""
        CourseEnrollment.unenroll(self.user, self.course_key)
        self.active = False
        self.save()
        LOG.info('Deactivated course registration for user %s in course %s.', self.user, self.course_key)

    def activate(self):
        """Enroll the user and activate this instance."""
        CourseEnrollment.enroll(self.user, self.course_key)
        self.active = True
        self.save()
        LOG.info('Activated course registration for user %s in course %s.', self.user, self.course_key)

    def send_report(self):
        """Sends the generated completion report to the Ed2go completion report endpoint."""
        if switch_is_active(ENABLED_ED2GO_COMPLETION_REPORTING):
            report = self.report
            report['APIKey'] = settings.ED2GO_API_KEY
            url = settings.ED2GO_REGISTRATION_SERVICE_URL
            xmlh = XMLHandler()

            data = xmlh.request_data_from_dict({'UpdateCompletionReport': report})
            response = requests.post(url, data=data, headers=xmlh.headers)

            error_msg = 'Error sending completion update report: %s'
            if response.status_code != 200:
                LOG.error(error_msg, response.reason)
                return False

            response_data = xmlh.completion_update_response_data_from_xml(response.content)
            if response_data['Success'] == 'false':
                LOG.error(error_msg, str(response_data['Code']))
            else:
                self.reported = True
                self.save()
                LOG.info('Sent report for completion profile ID %d', self.id)
            return True

    @property
    def report(self):
        """
        Generates a report for the Ed2go completion report endpoint.

        Returns:
            A dictionary containing the report values.
        """
        course_grade = CourseGradeFactory().create(
            self.user,
            get_course(self.course_key)
        )
        persistent_grade = PersistentCourseGrade.objects.filter(
            user_id=self.user.id,
            course_id=self.course_key
        ).first()

        return {
            'RegistrationKey': self.registration_key,
            'PercentProgress': self.progress * 100,
            'LastAccessDatetimeGMT': self.user.last_login.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'CoursePassed': str(course_grade.passed).lower(),
            'PercentOverallScore': course_grade.percent,
            'CompletionDatetimeGMT': persistent_grade.passed_timestamp if persistent_grade else '',
            'TimeSpent': format_timedelta(CourseSession.total_time(user=self.user, course_key=self.course_key)),
        }

    @property
    def progress(self):
        """
        Returns the user's current progress in a course according to rules:
            * if there are no videos or problems the progress is defaulted to 0.0
            * if there are no videos the progress is measured with
              #_of_attempted_problems / total_problems
            * if there are no problems the progress is measured with
              #_of_watched_videos / total_videos
            * if there are videos and problems in the course, the progress is measured as
              0.5 * (#_of_attempted_problems / total_problems) + 0.5 * (#_of_watched_videos / total_videos)

        Returns:
            A float number that represents the percentage of user's progress in the associated course.
        """
        units = Unit.objects.filter(
            subsection__chapter_progress__completion_profile__user=self.user,
            subsection__chapter_progress__completion_profile__course_key=self.course_key
        )
        problems = units.filter(type=Unit.PROBLEM_TYPE)
        problems_completed = float(problems.filter(done=True).count()) / problems.count()

        videos = units.filter(type=Unit.VIDEO_TYPE)
        videos_completed = float(videos.filter(done=True).count()) / videos.count()

        if not problems and not videos:
            return 0.0
        elif not problems:
            return videos_completed
        elif not videos:
            return problems_completed
        return 0.5 * problems_completed + 0.5 * videos_completed

    @classmethod
    def mark_progress(cls, user, course_key, usage_key):
        """
        Marks a block as completed/attempted.

        Args:
            block_type (str): type of the block.
            usage_key (str): usage_key of the block.
        Raises:
            KeyError if the passed in usage_key does not exist in the saved problems or videos.
              Possible cause might be that a new block with a custom type was added
              subsequently to a course.
            Exception if the passed in type is not supported.
        """
        profile = cls.objects.get(user=user, course_key=course_key)
        unit = Unit.objects.get(
            unit_id=usage_key,
            subsection__chapter_progress__completion_profile__user=user
        )
        unit.done = True
        unit.save()
        profile.reported = False
        profile.save()


@receiver(post_save, sender=CompletionProfile, dispatch_uid='populate_chapter_progress')
def populate_chapter_progress(sender, instance, created, *args, **kwargs):
    """
    After a new Completion Profile instance has been created, this will create:
    * Chapter Progress instances for all the chapters within the course structure
    * Subsection instances for all the subsections in each of chapters
    * Unit instances for each unit of the tracked type in each subsection
    """
    if created:
        course_structure = CourseStructure.objects.get(course_id=instance.course_key).ordered_blocks
        for chapter in course_structure.items()[0][1]['children']:
            chapter_progress = ChapterProgress.objects.create(
                chapter_id=chapter,
                completion_profile=instance
            )
            for section in course_structure[chapter]['children']:
                for subsection in course_structure[section]['children']:
                    sub_section = SubSection.objects.create(
                        subsection_id=subsection,
                        chapter_progress=chapter_progress
                    )
                    units = []

                    for unit in course_structure[subsection]['children']:
                        if course_structure[unit]['block_type'] in Unit.UNIT_TYPES:
                            units.append(Unit(
                                unit_id=unit,
                                subsection=sub_section,
                                type=course_structure[unit]['block_type']
                            ))
                    if units:
                        # The save method will NOT be called!
                        Unit.objects.bulk_create(units)


class CourseSession(models.Model):
    """
    Keeps track of how much time a user has spent in a course.
    """
    user = models.ForeignKey(User)
    course_key = CourseKeyField(max_length=255, db_index=True)
    created_at = models.DateTimeField()
    closed_at = models.DateTimeField(blank=True, null=True)
    last_activity_at = models.DateTimeField()
    active = models.BooleanField(default=True, db_index=True)

    class Meta:  # pylint: disable=old-style-class,no-init
        get_latest_by = 'created_at'

    def _update_completion_profile(self):
        """Update the corresponding CompletionProfile to indicate that the session was updated."""
        profile, _ = CompletionProfile.objects.get_or_create(user=self.user, course_key=self.course_key)
        profile.reported = False
        profile.save()

    def save(self, *args, **kwargs):
        if self.pk is None:
            # Only one session per user per course should be active at the same time.
            cls = self.__class__
            qs = cls.objects.filter(user=self.user, course_key=self.course_key, active=True)  # pylint: disable=invalid-name
            for obj in qs:
                obj.close()

            self.created_at = now()
            self.last_activity_at = now()
            self._update_completion_profile()

        return super(CourseSession, self).save(*args, **kwargs)

    def update(self):
        """Updates the last activity time to now. Ignores if the session is not active."""
        if self.active:
            self.last_activity_at = now()
            self.save()
            self._update_completion_profile()

    def close(self, offset_delta=None):
        """
        Closes the current session and sets the closed_at time to now. Ignores if the session is not active.

        Args:
            offset_delta (datetime.timedelta): Time value which is subtracted from closed_at time.
        """
        if self.active:
            self.closed_at = (now() - offset_delta) if offset_delta else now()
            self.active = False
            self.save()
            LOG.info('Session closed for user %s in course %s', self.user, self.course_key)

            self._update_completion_profile()

    @property
    def duration(self):
        """
        Duration of this session.
        If the session is still active, duration is measured from the creation of this
        session to the last activity, if not it's measured from the creation to the closing time.
        """
        last_activity = self.last_activity_at if self.active else self.closed_at
        return last_activity - self.created_at

    @classmethod
    def total_time(cls, user, course_key):
        """
        Total time the user spent in the course, from the first activity to the last.

        Args:
            cls (class): CourseSession class.
            user (User): user whose total session time is retrieved.
            course_key (CourseKey): key of the course where user's activity was measured.

        Returns:
            A timedelta object which represents the total time a user spent in a course.
        """
        qs = cls.objects.filter(user=user, course_key=course_key)  # pylint: disable=invalid-name
        total_duration = timedelta()
        for session in qs:
            total_duration += session.duration
        return total_duration


class ChapterProgress(models.Model):
    """
    Keeps information about a chapter within a course
    and the progress of a user in that particular chapter.
    """
    completion_profile = models.ForeignKey(CompletionProfile)
    chapter_id = models.CharField(max_length=255, db_index=True)

    @property
    def percent_complete(self):
        """
        If the chapter is empty the progress is 100%.
        If not, the progress is percent of completed subsections
        within the chapter.
        """
        total = self.subsection.count()
        if not total:
            return 100

        completed = sum([1 if subsection.done else 0 for subsection in self.subsection.all()])
        return int(round(float(completed) / total * 100))


class SubSection(models.Model):
    """
    Represents one subsection within a chapter.
    A subsection is one page of course content. It contains units of various types.
    """
    subsection_id = models.CharField(max_length=255, db_index=True)
    chapter_progress = models.ForeignKey(ChapterProgress, related_name='subsection')
    viewed = models.BooleanField(default=False)

    @property
    def done(self):
        """
        A subsection is marked as done if all the units that it contains are done.
        Or if it does not contain any tracked units then it's done one a user views it.
        """
        units = self.subsection_units.all()
        if units:
            return all((unit.done for unit in units))
        return self.viewed


class Unit(models.Model):
    """
    A unit within a course. Keeps information about the done-status of the unit.
    """
    VIDEO_TYPE = 'video'
    PROBLEM_TYPE = 'problem'
    UNIT_TYPES = [VIDEO_TYPE, PROBLEM_TYPE]
    UNIT_TYPES_CHOICES = (
        (VIDEO_TYPE, 'video'),
        (PROBLEM_TYPE, 'problem')
    )

    subsection = models.ForeignKey(SubSection, related_name='subsection_units')
    unit_id = models.CharField(max_length=255, db_index=True)
    type = models.CharField(max_length=255, choices=UNIT_TYPES_CHOICES)
    done = models.BooleanField(default=False)
