class InvalidEd2goRequestError(Exception):
    """Raised when the SSO or Action request is invalid."""
    pass


class CompletionProfileAlreadyExists(Exception):
    """Raised when trying to create a Completion Profile that already exists."""
    pass
