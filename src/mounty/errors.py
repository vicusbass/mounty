class Error(Exception):
    ...


class Unavailable(Error):
    ...


class ImposterError(Error):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message


class NotFound(ImposterError):
    """
    Actions on a non-existing Imposter
    """


class Conflict(ImposterError):
    """
    Attempt to use a port already in use by existing Imposter
    """


class MissingFields(ImposterError):
    """
    Imposter payload is missing fields
    """


class MissingEnvironmentVariable(Error):
    ...
