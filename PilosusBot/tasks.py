from celery import shared_task, chain
from .exceptions import APIAccessError
from .utils import map_value_from_range_to_new_range as map_val


# TODO
@shared_task
def determine_message_score(message):
    """
    Return incoming message score using either polyglot or third-party API (like inidoio).


    :param message: Telegram Message type (see https://core.telegram.org/bots/api#sendmessage)
    :return: float [0.0, 1.0], where 0.5 is neutral, <= 0.5 is negative,
             greater then 0.5 is positive
    """
    pass


@shared_task
def select_db_sentiment(score_slice):
    """
    Return sentiment from the database,
    :param score: slice with slice.start >= 0.0, start.stop <= 1.0
    :return: str
    """
    pass


@shared_task
def send_message_to_chat(message):
    """
    Send sentiment to the chat
    :param message: Telegram Message type (see https://core.telegram.org/bots/api#sendmessage)
    :return: Telegram Message (success) or None (fail)
    """
    pass
