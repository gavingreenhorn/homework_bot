class ServiceDeniedError(Exception):
    """API informed about errors."""

    pass


class HTTPRequestError(Exception):
    """Unspecified non-OK response from API."""

    pass
