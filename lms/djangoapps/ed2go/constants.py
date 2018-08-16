"""Ed2go specific constants."""
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

ENABLED_ED2GO_COMPLETION_REPORTING = 'Completion reporting task'
REDIRECT_ANONYMOUS_TO_ED2GO_LOGIN = 'redirect_anonymous_edgo_login'

NEW_REGISTRATION_ACTION = 'NewRegistration'
UPDATE_REGISTRATION_ACTION = 'UpdateRegistration'
CANCEL_REGISTRATION_ACTION = 'CancelRegistration'

COURSE_KEY_TEMPLATE = 'course-v1:Microsoft+{code}'
