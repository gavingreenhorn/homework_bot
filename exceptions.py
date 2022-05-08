"""
Custom errors module.

Required for a more precise error logging.
All exception classes are self-describing.
"""


from requests import exceptions


class IncorrectResponseError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class UnknownReviewStatus(Exception):
    def __init__(self):
        self.message = 'Unknown review status was returned'
        super().__init__(self.message)


class ConnectionError(exceptions.ConnectionError):
    def __init__(self, endpoint, error_data):
        self.message = (
            f'Network error occured occured while trying to connect '
            f'to {endpoint}:\n {error_data}'
        )
        super().__init__(self.message)


class NotFoundError(exceptions.HTTPError):
    def __init__(self, endpoint):
        self.message = (
            f'Failed to connect to address {endpoint} '
            'Please check that is the correct address'
        )
        super().__init__(self.message)


class ServiceDeniedError(exceptions.HTTPError):
    def __init__(self, code=None, errors=None, **kwargs):
        self.message = (
            f'The server refused to provide requested data '
            f'with an answer [{code or None}]\n'
            f'It might be due to the following errors: {errors or None}\n'
            'The following requst was sent:\n'
            + '\n'.join(f'{k}: {v}' for k, v in kwargs.items())
        )
        super().__init__(self.message)


class HttpError(exceptions.HTTPError):
    def __init__(self, code, **kwargs):
        self.message = (
            f'The server responded with status code [{code}]\n'
            'The following requst was sent:\n'
            + '\n'.join(f'{k}: {v}' for k, v in kwargs.items())
        )
        super().__init__(self.message)
