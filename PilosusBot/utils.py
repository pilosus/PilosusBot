from polyglot.detect import Detector
from polyglot.detect import langids as langs
from polyglot.text import Text
from polyglot.detect.base import UnknownLanguage
from polyglot.downloader import downloader
from flask import current_app


def download_polyglot_dicts():
    """Download dictionaries needed for Polyglot library.
    """
    langs = current_app.config['APP_LANGUAGES']
    dicts = current_app.config['APP_LANG_POLYGLOT_DICTS']

    for dic in dicts:
        for lang in langs:
            downloader.download('{dic}.{lang}'.format(dic=dic, lang=lang))


def generate_password(length=10):
    """Generate random password of the given length.
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


def detect_language_code(text):
    """
    Return language code, fall back to app's default language if detected language not in the DB.
    :param text: str
    :return: str (two-letter language code)
    """
    try:
        detector = Detector(text)
    except UnknownLanguage:
        return current_app.config['APP_LANG_FALLBACK']

    return detector.language.code


def is_valid_lang_code(code):
    """
    Return True if given two-letter language code exists in polyglot library; False otherwise.

    :param code: str (two-letter ISO 639-1 language code)
    :return: bool
    """
    return code in langs.isoLangs


def is_valid_lang_name(lang):
    """
    Return True if given language name in English exists in polyglot library; False otherwise.
    :param lang: str (language name in English)
    :return: bool
    """
    return lang.title() in Detector.supported_languages()


def lang_code_to_lang_name(code):
    """
    Return language name in English for a given language code.

    :param code: str (two-letter ISO 639-1 language code)
    :return: str
    """
    # remove additional names of the language name
    return langs.isoLangs[code]['name'].split(';')[0]


def score_to_closest_level(lang_code, score, levels):
    """
    Return level from the given list of score levels, the nearest to the given score.

    Returned score level should have at least one Sentiment in the DB for the given language.

    # assume each level has at least one row in the db
    >>> score_to_closest_level(0.63, [0.0, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0])
    0.75

    >>> score_to_closest_level(0.75, [0.0, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0])
    0.75

    >>> score_to_closest_level(1.0, [0.0, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0])
    1.0

    :param lang_code: str
    :param score: float (min(levels) <= score <= max(levels) )
    :param levels: list of floats [-1.0, 1.0] including 0.5
    :return: float (score level for which at least one Sentiment
                   in given language exists in the DB)
    """
    from .models import Sentiment, Language
    lang = Language.query.filter_by(code=lang_code).first()
    neutral_score = 0.5
    neutral_score_idx = levels.index(neutral_score)

    level = None

    if score > levels[-1]:
        score = levels[-1]
    elif score < levels[0]:
        score = levels[0]

    new_levels = sorted(levels + [score])

    cur_idx = new_levels.index(score)
    start_idx = cur_idx

    min_idx = 1
    max_idx = len(new_levels) - 1

    if score >= neutral_score:
        step = 1
    else:
        step = -1

    switch_direction = False

    while True:
        if cur_idx in range(min_idx, max_idx):
            cur_idx += step
        else:
            if not switch_direction:
                step = -step
                cur_idx = start_idx
                switch_direction = True
            # if direction already switched once, and we have reached the end of the range,
            # then search is exhausted, stop it
            else:
                break

        # if there's at least one sentiment for the level, return this level
        level = new_levels[cur_idx]
        sentiment = Sentiment.query.filter(Sentiment.score == level, Sentiment.language == lang).first()

        if sentiment:
            break

    return level


def get_rough_sentiment_score(text):
    """
    Return sentiment score calculated using polyglot words polarity.

    :param text: str (non-empty)
    :return: float
    """
    # for some odd reasons polyglot determines polarity correctly
    # iff text is lowercased
    words = Text(text.lower()).words

    polarity_scores = [word.polarity for word in words]
    text_score = sum(polarity_scores) / len(polarity_scores)

    # map score of range [-1.0, 1.0] to a new range of [0.0, 1.0]
    return map_value_from_range_to_new_range(text_score,
                                             old_slice=slice(-1.0, 1.0),
                                             new_slice=slice(0.0, 1.0))
