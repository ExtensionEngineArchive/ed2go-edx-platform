import re
from django.conf import settings


def extract_problem_id(string):
    """
    Extract the problem ID from the problem event input string. Example:
        string: 'input_Sample_ChemFormula_Problem_2_1=2'
    from which the problem ID is 'Sample_ChemFormula_Problem'

    Args:
        string (str): string from which the problem ID is extracted.

    Returns:
        The problem ID string.
    """
    result = re.search(r'(?<=^input_)(\w*\d*)(?=_\d_\d=)', string)
    return result.group() if result else None


def extract_course_id_from_url(url):
    """
    Extract the course ID from a URL. Example
        url: 'http://localhost/courses/course-v1:ex+demo+1/courseware/1414ffd08f739b563ab468b7/'
    from which the coures ID is: 'course-v1:ex+demo+1'

    Args:
        url (str): string from which the course ID is extracted.

    Returns:
        The course ID string.
    """
    result = re.search(settings.COURSE_KEY_REGEX, url)
    result = result.group()
    return result.split('/')[-1]
