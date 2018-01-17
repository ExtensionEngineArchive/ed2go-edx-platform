from django.contrib.auth.models import User
from django.db import models
from jsonfield import JSONField

from lms.djangoapps.courseware.courses import get_course
from lms.djangoapps.grades.new.course_grade_factory import CourseGradeFactory
from openedx.core.djangoapps.content.course_structures.models import CourseStructure
from openedx.core.djangoapps.xmodule_django.models import CourseKeyField


class CompletionProfile(models.Model):
    PROBLEM_TYPES = ['problem']

    user = models.ForeignKey(User)
    course_key = CourseKeyField(max_length=255)
    registration_key = models.CharField(max_length=255, unique=True)
    problems = JSONField()
    videos = JSONField()

    def save(self, *args, **kwargs):
        """
        Override of the default save() method. Whenever a new CompletionProfile
        is created, we collect all the video block and problem block IDs.
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

    @property
    def progress(self):
        """
        Returns the user's current progress in a course according to rules:
            * if there are no videos or problems the progress is defaulted to 0.0
            * if there are no videos the progress is measured with
              #_of_attempted_problems / total_problems
            * if there are no problems the progress is measured with
              #_of_watched_videos / total_videos
            * if there are videos and problems in the course, the progress is measured with
              0.5 * (#_of_attempted_problems / total_problems) + 0.5 * (#_of_watched_videos / total_videos)
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

    def mark_progress(self, type, usage_key):
        """
        Marks a block as completed (video) or attempted (problem).

        Args:
            type (str): type of the block.
            usage_key (str): usage_key of the block.
        Raises:
            KeyError if the passed in usage_key does not exist in the saved structure.
              Possible cause might be that a new block was added subsequently to a course.
            Exception if the passed in type is not supported.
        """
        if type in self.PROBLEM_TYPES:
            self.problems[usage_key] = True
        elif type == 'video':
            self.videos[usage_key] = True
        else:
            raise Exception('Type %s not supported.' % type)
        self.save()

    @property
    def report(self):
        """Generates a report for the Ed2go completion report endpoint."""
        course_grade = CourseGradeFactory().create(
            self.user,
            get_course(self.course_key)
        )
        persistent_course_grade = PersistentCourseGrade.objects.filter(self.user.id, self.course_key).first()
        return {
            APIKey: 'changeme',
            RegistrationKey: self.registration_key,
            PercentProgress: self.progress * 100,
            LastAccessDatetimeGMT: self.user.last_login,
            CoursePassed: course_grade.passed,
            PercentOverallScore: course_grade.percent,
            CompletionDatetimeGMT: persistent_course_grade.passed_timestamp if persistent_course_grade else None,
            TimeSpent: '@TODO',
            Custom: None,
        }

    def send_report(self):
        """Sends the generated report to the Ed2go completion report endpoint."""
        pass
