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
