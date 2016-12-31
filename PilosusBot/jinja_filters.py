def permissions2str(n):
    """Convert permission representation into a string representation.

    Used as a Jinja2 custom filter.
    """
    perms = {0: 'a', 1: 's', 2: 'm', 3: 'u',
             4: 'c', 5: 'w', 6: 'f', 7: 'r'}
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
