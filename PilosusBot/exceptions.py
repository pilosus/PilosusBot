from indicoio.utils.errors import IndicoError


class ValidationError(ValueError):
    pass


class APIAccessError(IndicoError):
    """
    Exception wrapper for indico.io
    """
    pass
