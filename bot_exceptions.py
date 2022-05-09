class ServiceDeniedError(Exception):
    """API informed about errors"""
    pass
    # def __init__(*args, **kwargs):
    #     super().__init__(*args, **kwargs)


class HTTPRequestError(Exception):
    """Unspecified non-OK response from API"""
    pass
