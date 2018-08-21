"""Ed2go specific constants."""
# Incoming request names
SSO_REQUEST = 'sso_request'
ACTION_REQUEST = 'action_request'

# Request parameter names
CHECKSUM = 'Checksum'
ACTION = 'Action'
REGISTRATION_KEY = 'RegistrationKey'
REQUEST_EXPIRATION_DATETIME = 'RequestExpirationDatetimeGMT'
SOURCE = 'Source'
RETURN_URL = 'ReturnURL'

# Checksum generation parameters in the correct order.
# If new ones are needed make sure they are in the CORRECT ORDER!
SSO_CHECKSUM_PARAMS = [
    REGISTRATION_KEY,
    REQUEST_EXPIRATION_DATETIME,
    RETURN_URL,
]

ACTION_CHECKSUM_PARAMS = [
    ACTION,
    REGISTRATION_KEY,
    REQUEST_EXPIRATION_DATETIME,
]

# Task constants
ENABLED_ED2GO_COMPLETION_REPORTING = 'Completion reporting task'
REDIRECT_ANONYMOUS_TO_ED2GO_LOGIN = 'redirect_anonymous_edgo_login'

# Action names
NEW_REGISTRATION_ACTION = 'NewRegistration'
UPDATE_REGISTRATION_ACTION = 'UpdateRegistration'
CANCEL_REGISTRATION_ACTION = 'CancelRegistration'

COURSE_KEY_TEMPLATE = 'course-v1:Microsoft+{code}'

# Registration attributes
REG_COURSE = 'Course'
REG_CODE = 'Code'
REG_STUDENT = 'Student'
REG_EMAIL = 'Email'
REG_FIRST_NAME = 'FirstName'
REG_LAST_NAME = 'LastName'
REG_COUNTRY = 'Country'
REG_RETURN_URL = 'ReturnURL'
REG_BIRTHDATE = 'Birthdate'
REG_STUDENT_KEY = 'StudentKey'

# Report attributes
REP_API_KEY = 'APIKey'
REP_REGISTRATION_KEY = 'RegistrationKey'
REP_PERCENT_PROGRESS = 'PercentProgress'
REP_LAST_ACCESS_DT = 'LastAccessDatetimeGMT'
REP_COURSE_PASSED = 'CoursePassed'
REP_COMPLETION_DT = 'CompletionDatetimeGMT'
REP_TIME_SPENT = 'TimeSpent'

# Response attributes
RESP_SUCCESS = 'Success'
RESP_CODE = 'Code'

# Request names
REQ_UPDATE_COMPLETION_REPORT = 'UpdateCompletionReport'
REQ_GET_REGISTRATION = 'GetRegistration'

# Request attributes
REQ_API_KEY = 'APIKey'
REQ_REGISTRATION_KEY = 'RegistrationKey'
