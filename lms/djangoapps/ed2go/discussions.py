""" Discussions stats """

from __future__ import unicode_literals

from lms.lib.comment_client import settings, utils

STATS_URL = "{prefix}/stats".format(prefix=settings.PREFIX)


def get_forum_statistics(course_id, user_id):
    """ Gets and parses discussion stats for user in a course """
    data = _get_stats(course_id, user_id)
    response = {
        'recent_posts': data['recent_posts_count'],
        'all_posts': data['all_posts_count'],
        'user_threads_count': data.get('user_threads_count', 0),
        'user_comments_count': data.get('user_comments_count', 0),
        'latest_post': data.get('latest_thread')
    }

    return response


def _get_stats(course_id, user_id):
    """ Retrives discussions stats for course from discussions api"""
    params = {"course_id": course_id, "user_id": user_id}
    response = utils.perform_request(
        'get',
        STATS_URL,
        params,
        metric_tags=["stats"],
        metric_action='discussions.stats'
    )

    if response.get('latest_comment_or_thread', {}).get('thread'):
        latest_thread = response['latest_comment_or_thread']['thread']
        latest_thread['courseware_url'] = '/courses/{}/discussion/forum/{}/threads/{}'.format(
            course_id,
            latest_thread[u'commentable_id'],
            latest_thread[u'_id']
        )
        response[u'latest_thread'] = latest_thread

    response['recent_posts_count'] = int(response['latest_threads_count']) + int(response['latest_comments_count'])
    response['all_posts_count'] = int(response['comments_count']) + int(response['threads_count'])

    return response
