import logging

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now
from jsonfield import JSONField
from opaque_keys.edx.keys import CourseKey

from lms.djangoapps.courseware.courses import get_course
from lms.djangoapps.grades.models import PersistentCourseGrade
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from openedx.core.djangoapps.content.course_structures.models import CourseStructure
from openedx.core.djangoapps.xmodule_django.models import CourseKeyField
from student.models import CourseEnrollment

from ed2go.utils import XMLHandler

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
    problems = JSONField()
    videos = JSONField()

    # Indicates whether we need to send a report update for this completion profile.
    # Should be set to False whenever course progress or session is updated.
    reported = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """
        Override of the default save() method. Whenever a new object is instantiated
        we collect all the video block and problem block IDs that are in the course
        in dictionaries where the item values represent if the user attempted/watched
        a problem/video (defaults to False).
        """
        if self.pk is None:
            course_structure = CourseStructure.objects.get(course_id=self.course_key).structure
            problems = {}
            videos = {}

            for k, v in course_structure['blocks'].items():
                if v['block_type'] == 'video':
                    videos[k] = False
                if v['block_type'] in self.PROBLEM_TYPES:
                    problems[k] = False

            self.problems = problems
            self.videos = videos
        super(CompletionProfile, self).save(*args, **kwargs)

    def mark_progress(self, type, usage_key):
        """
        Marks a block as completed/attempted.

        Args:
            type (str): type of the block.
            usage_key (str): usage_key of the block.
        Raises:
            KeyError if the passed in usage_key does not exist in the saved problems or videos.
              Possible cause might be that a new block with a custom type was added
              subsequently to a course.
            Exception if the passed in type is not supported.
        """
        if type in self.PROBLEM_TYPES:
            self.problems[usage_key] = True
        elif type == 'video':
            self.videos[usage_key] = True
        else:
            raise Exception('Type %s not supported.' % type)
        self.reported = False
        self.save()

    def send_report(self):
        """Sends the generated completion report to the Ed2go completion report endpoint."""
        if settings.ENABLED_ED2GO_COMPLETION_REPORTING:
            report = self.report
            report['APIKey'] = settings.ED2GO_API_KEY
            url = settings.ED2GO_REGISTRATION_SERVICE_URL
            xmlh = XMLHandler()

            data = xmlh.request_data_from_dict({'UpdateCompletionReport': report})
            response = requests.post(url, data=data, headers=xmlh.headers)

            error_msg = 'Error sending completion update report: {error}'
            if response.status_code != 200:
                LOG.error(error_msg.format(error=response.reason))
                return False

            response_data = xmlh.completion_update_response_data_from_xml(response.content)
            if response_data['Success'] == 'false':
                LOG.error(error_msg.format(error=response_data['Code']))
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
        course_registration = CourseRegistration.objects.get(user=self.user, course_key=self.course_key)

        return {
            'RegistrationKey': course_registration.registration_key,
            'PercentProgress': self.progress * 100,
            'LastAccessDatetimeGMT': self.user.last_login.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'CoursePassed': str(course_grade.passed).lower(),
            'PercentOverallScore': course_grade.percent,
            'CompletionDatetimeGMT': persistent_grade.passed_timestamp if persistent_grade else '',
            'TimeSpent': str(CourseSession.total_time(user=self.user, course_key=self.course_key)),
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
        problems_completed = self.problems.values().count(True) / float(len(self.problems)) if self.problems else None
        videos_completed = self.videos.values().count(True) / float(len(self.videos)) if self.videos else None

        if problems_completed is None and videos_completed is None:
            return 0.0
        elif problems_completed is None:
            return videos_completed
        elif videos_completed is None:
            return problems_completed
        else:
            return 0.5 * problems_completed + 0.5 * videos_completed


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

    class Meta:
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
            qs = cls.objects.filter(user=self.user, course_key=self.course_key, active=True)
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
        qs = cls.objects.filter(user=user, course_key=course_key)
        first = qs.earliest()
        last = qs.latest()
        latest_time = last.last_activity_at if last.active else last.closed_at

        return latest_time - first.created_at


class CourseRegistration(models.Model):
    """
    User-course pairing to avoid making another request to Ed2go GetRegistration
    API endpoint in order to get the information about the course from the registration
    key.
    """
    user = models.ForeignKey(User)
    registration_key = models.CharField(max_length=255, db_index=True)
    course_key = CourseKeyField(max_length=255)

    def delete(self, *args, **kwargs):
        """Unenroll the user prior to deleting the CourseRegistration."""
        CourseEnrollment.unenroll(self.user, self.course_key)
        LOG.info('Deleted course registration for user %s in course %s.', self.user, self.course_key)
        super(CourseRegistration, self).delete(*args, **kwargs)