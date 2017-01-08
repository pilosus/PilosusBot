import indicoio
import random
import requests
from indicoio.utils.errors import IndicoError, DataStructureException
from flask import current_app
from celery import shared_task, chain
from .utils import score_to_closest_level as select_score_level, \
    detect_language_code, get_rough_sentiment_score, lang_code_to_lang_name
from .models import Sentiment, Language


def celery_chain(parsed_update):
    """
    Celery chain of tasks, one task in the chain is executed after the previous one is done.

    :param parsed_update: dict
    :return: dict (with 'status_code' and 'status' keys)
    """
    chain_result = chain(assess_message_score.s(parsed_update),
                         select_db_sentiment.s(),
                         send_message_to_chat.s()).apply_async()
    return chain_result


# assess queue
@shared_task
def assess_message_score(parsed_update):
    """
    Return incoming message score using either polyglot or third-party API (like inidocoio).

    The task to be processed in a separate queue with rate limit in compliance with third-party API.

    :param parsed_update: dict containing message's text under 'text' key
    :return: updated dict with the text score index 'score' key.
             [0.0, 1.0], where 0.5 is neutral, <= 0.5 is negative, greater then 0.5 is positive
    """
    text = parsed_update['text']

    # calculate sentiment using polyglot library
    score = get_rough_sentiment_score(text)

    # detect text language (fallback to default language, if detected language is not in the DB)
    lang_code_polyglot = detect_language_code(text)

    lang = Language.query.filter_by(code=lang_code_polyglot).first() or \
           Language.query.filter_by(code=current_app.config['APP_LANG_FALLBACK']).first()

    lang_name = lang_code_to_lang_name(lang.code).lower()

    # save language code for further use
    parsed_update['language'] = lang.code

    # request to third-party API to determine to get more precise sentiment score
    indicoio.config.api_key = current_app.config['INDICO_TOKEN']

    # if request to third-party API succeeded, update score
    # otherwise stay with score calculated by poyglot
    try:
        score = indicoio.sentiment(text, language=lang_name)
    except (IndicoError, DataStructureException) as err:
        pass

    # return parsed_update updated with score
    parsed_update['score'] = score

    return parsed_update


# select queue
@shared_task
def select_db_sentiment(parsed_update):
    """
    Return sentiment from the database.

    No rate limits for the task's queue.

    :param parsed_update: dict (with 'score' key)
    :return: dict updated
    """

    # unpack score, text, language
    score = parsed_update['score']
    text = parsed_update['text']
    lang_code = parsed_update['language']

    # select language
    lang = Language.query.filter_by(code=lang_code).first()

    # find score level closest to the calculated score of the text
    # with at least one Sentiment of the text's language in the DB
    level = select_score_level(lang_code=lang_code,
                               score=score,
                               levels=sorted(list(current_app.config['APP_SCORE_LEVELS'].keys())))

    # select all Sentiments of the score level and language
    sentiments = Sentiment.query.filter(Sentiment.score == level, Sentiment.language == lang).all()

    # select a Sentiment randomly,
    # select first Sentiment in a list if it's a list of length 1, so that rnd
    sentiment = random.choice(sentiments)

    # if Sentiment has 'body_html', then use 'HTML' parse_mode;
    # otherwise use 'Markdown'
    # also replace 'text' with sentiment chosen

    if sentiment.body_html:
        parsed_update['parse_mode'] = 'HTML'
        parsed_update['text'] = sentiment.body_html
    else:
        parsed_update['text'] = sentiment.body

    return parsed_update


# send queue
@shared_task
def send_message_to_chat(parsed_update):
    """
    Send sentiment to the chat

    The task to be processed in a separate queue with rate limit in compliance with Telegram API.

    :param parsed_update: dict ('text', 'chat_id', 'reply_to_message_id' keys are mandatory)
    :return: dict (with 'status_code' and 'status' keys)
    """
    url = current_app.config['TELEGRAM_URL'] + 'sendMessage'
    result = {'status_code': None, 'status': None}

    # make a request to telegram API, catch exceptions if any, return status
    try:
        r = requests.post(url,
                          json=parsed_update,
                          timeout=current_app.config['TELEGRAM_REQUEST_TIMEOUT_SEC'])
    except requests.exceptions.RequestException as err:
        result['status_code'] = 599  # informal convention for Network connect timeout error
        result['status'] = str(err)
    else:
        result['status_code'] = r.status_code
        result['status'] = "Reply to {id}. {text}".format(id=parsed_update['reply_to_message_id'],
                                                          text=r.json())

    return parsed_update
