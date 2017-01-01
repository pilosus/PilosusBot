from polyglot.detect import Detector
from flask import current_app

def generate_password(length=10):
    """Generate rnadom password of the given length.
    """
    import random
    import string
    return ''.join(random.SystemRandom(). \
                   choice(string.ascii_lowercase +
                          string.ascii_uppercase +
                          string.digits) \
                   for _ in range(length))


def to_bool(s: str) -> bool:
    """Return bool converted from string.

    bool() from the standard library convert all non-empty strings to True.
    """
    return s.lower() in ['true', 't', 'y', 'yes'] if s is not None else False


def map_value_from_range_to_new_range(old_value, old_slice=slice(-1.0, 1.0), new_slice=slice(0.0, 1.0)):
    """
    Return a number by mapping a given value from the given slice to a new slice.

    :param old_value: numbers.Number (superclass for int and float)
    :param old_slice: slice, used to extract slice.start and slice.stop only
    :param new_slice: slice, used to extract slice.start and slice.stop only
    :return: numbers.Number

    >>> map_value_from_range_to_new_range(0, slice(-1.0, 1.0), slice(0.0, 1.0))
    0.5
    >>> map_value_from_range_to_new_range(0.33, slice(-1.0, 1.0), slice(0.0, 1.0))
    0.665
    >>> map_value_from_range_to_new_range(0.123, slice(0.0, 1.0), slice(-1.0, 1.0))
    -0.754
    >>> map_value_from_range_to_new_range(0, slice(0.0, 1.0), slice(-1.0, 1.0))
    -1.0
    """
    return (old_value - old_slice.start) / \
           (old_slice.stop - old_slice.start) * \
           (new_slice.stop - new_slice.start) + \
           new_slice.start


def detect_language(text):
    """
    Return language code, fall back to app's default language if detected language not in the DB.
    :param text: str
    :return: Language instance
    """
    from .models import Language

    detector = Detector(text)
    lang = Language.query.filter_by(code=detector.language.code).first()

    if lang:
        return lang
    else:
        return Language.query.filter_by(code=current_app.config['APP_LANG_FALLBACK']).first()