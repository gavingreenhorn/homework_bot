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


class MoCk_HtTp_ErRoR(Exception):
    def __init__(self):
        self.message = ('API request returned code other than 200 '
                        'but apparently I\'m not allowed to use '
                        'raise_for_status on a MockResponseGet '
                        'object, so here is my custom error completely '
                        'adequate to this GREAT autotest')
        super().__init__(self.message)
