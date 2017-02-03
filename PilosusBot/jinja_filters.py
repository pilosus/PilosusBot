from flask import current_app
from .utils import lang_code_to_lang_name


def permissions2str(n):
    """Convert permission representation into a string representation.

    Used as a Jinja2 custom filter.
    """
    perms = {0: '[NA]', 1: '[NA]', 2: '[NA]', 3: '[NA]',
             4: '[NA]', 5: '[ADMINISTER]', 6: '[MODERATE]', 7: '[READ]'}
    perm_str = "{0:0>8}".format(bin(n).lstrip('0b'))
    result = ''
    for k in perms.keys():
        if perm_str[k] == '1':
            result += perms[k]
        else:
            result += '-'
    return result


def pluralize(counter, singular_postfix='', plural_postfix='s'):
    """
    Simpliest implementation of Django template's filter pluralize.

    Usage in a template:
    Like{{ num_of_likes|pluralize:("", "s") }}     -> 10 Likes, 1 Like
    Cit{{ num_of_cities|pluralize:("y", "ies") }}  -> 10 Cities, 1 City

    :param counter: int
    :param singular_postfix: str a filtered word's singlular form should be postfixed with
    :param plural_postfix: str a filtered word's plural form should be postfixed with
    :return: str
    """
    if counter == 1:
        return singular_postfix
    else:
        return plural_postfix


def score_level(score):
    """
    Return CSS class associated with a given sentiment score.

    Usage in a template:
    <span class="label label-{{ 0.5|score_level }}"> -> <span class="label label-default">

    :param score: float
    :return: str
    """
    levels = current_app.config['APP_SCORE_LEVELS']
    return levels[score].css


def score_desc(score):
    """
    Return string describing level pf the given score.

    Usage in a template:
    <span title="{{ 0.0|score_desc }}"> -> <span title="Very negative">

    :param score: float
    :return: str
    """
    levels = current_app.config['APP_SCORE_LEVELS']
    return levels[score].desc


def code2name(code):
    """
    Convert language code to language name.
    """
    return lang_code_to_lang_name(code)
