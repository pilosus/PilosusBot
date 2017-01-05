from flask import jsonify, current_app
from celery import shared_task, chain
from .exceptions import APIAccessError
from .utils import map_value_from_range_to_new_range as map_val
from .models import Sentiment, Language


def celery_chain(parsed_update):
    """
    Celery chain of tasks, one task in the chain is executed after the previous one is done.

    :param parsed_update: dict
    :return:
    """
    chain_result = chain(determine_message_score.s(parsed_update),
                         select_db_sentiment.s(),
                         send_message_to_chat.s()).apply_async()


# TODO
@shared_task
def determine_message_score(parsed_update):
    """
    Return incoming message score using either polyglot or third-party API (like inidocoio).

    The task to be processed in a separate queue with rate limit in compliance with third-party API.

    :param parsed_update: dict containing message's text under 'text' key
    :return: updated dict with the text score index 'score' key.
             [0.0, 1.0], where 0.5 is neutral, <= 0.5 is negative, greater then 0.5 is positive
    """
    text = parsed_update['text']

    # calculate sentiment using polyglot library

    # map score from [-1.0, 1.0] range to [0.0, 1.0] range using map_val function
    score = 0

    # determine language (you get it for free, once sentiment is calculated)

    # request to third-party API to determine to get more precise sentiment score

    # if request to third-party API succeeded (status code is 200), update score

    # otherwise stay with score calculated by poyglot

    # return parsed_update updated with score
    parsed_update['score'] = score

    return parsed_update



@shared_task
def select_db_sentiment(parsed_update):
    """
    Return sentiment from the database.

    No rate limits for the task's queue.

    :param parsed_update: dict (with 'score' key)
    :return: dict updated with 'sentiment' key
    """

    # unpack score
    score = parsed_update['score']

    # filter Sentiments according to score

    # select Sentiment randomly

    # update dict with 'sentiment' key

    return parsed_update


@shared_task
def send_message_to_chat(parsed_update):
    """
    Send sentiment to the chat

    The task to be processed in a separate queue with rate limit in compliance with Telegram API.

    :param parsed_update: Telegram Message type (see https://core.telegram.org/bots/api#sendmessage)
    :return: Telegram Message (success) or None (fail)
    """
    URL = current_app.config['TELEGRAM_URL']

    payload = {
        'method': 'sendMessage',
    }

    return jsonify(payload)
