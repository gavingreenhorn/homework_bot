"""
Custom errors module.

Required for a more precise error logging.
All exception classes are self-describing.
"""


class TokensMissingError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class IncorrectResponseError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class UnknownReviewStatus(Exception):
    def __init__(self):
        self.message = 'Unknown review status was returned'
        super().__init__(self.message)
