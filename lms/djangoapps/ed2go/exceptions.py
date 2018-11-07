import logging

LOG = logging.getLogger(__name__)


class InvalidEd2goRequestError(Exception):
    """Raised when the SSO or Action request is invalid."""
    def __init__(self, message):
        super(InvalidEd2goRequestError, self).__init__(message)
        LOG.error(message)


class CompletionProfileAlreadyExists(Exception):
    """Raised when trying to create a Completion Profile that already exists."""
    pass
