from flask import current_app
from qr import CappedCollection


def parse_update(update):
    """
    Parse JSON posted by Telegram, get message_id, chat_id and text fields.

    Global queue of the updates received should be updated, so that no repeated updates processed.

    :param update: dict (json)
    :return: dict
    """
    # CappedCollection is a Deque analogue, push with `.push(elem)`,
    # get item with `elem in CappedCollectionInstance.elements()`
    updates = CappedCollection(key=current_app.config['DEQUE_KEY'],
                               size=current_app.config['DEQUE_MAX_LEN'],
                               host=current_app.config['DEQUE_HOST'],
                               port=current_app.config['DEQUE_PORT'])
    result = {}

    # get update_id
    try:
        update_id = update['update_id']
    except KeyError as err:
        return result

    # check update_id in the queue
    # if in queue, do nothing
    # otherwise add update_id to the queue
    if update_id in updates.elements():
        return result
    else:
        updates.push(update_id)

    # check if the update is a Message type, i.e. 'message' key exists
    try:
        message = update['message']
    except KeyError as err:
        return result

    # check if Message is a text, i.e. 'text' key exists
    # get update['chat']['chat_id'], update['message_id'] to use in bot's reply
    # these fields accessed together, as there's not much sense in 'text' without
    # 'chat_id' and 'message_id' and vice versa, i.e. normal update we should respond to
    # mush have these three fields.
    try:
        chat_id = message['chat']['id']
        message_id = message['message_id']
        text = message['text']
    except KeyError as err:
        return result
    else:
        result['chat_id'] = chat_id
        result['reply_to_message_id'] = message_id
        result['text'] = text

    return result


def parsed_update_can_be_processed(parsed_update):
    """
    Return True if a dict given contains 'text', 'chat_id', 'reply_to_message_id' fields.

    The text of the given dict should also satisfy certain criteria:

    :param parsed_update: dict (return by parse_update function)
    :return: bool
    """
    return parsed_update.get('text') and \
           parsed_update.get('chat_id') and \
           parsed_update.get('reply_to_message_id') and \
           len(parsed_update.get('text')) >= current_app.config['APP_UPDATE_TEXT_THRESHOLD_LEN'] and \
           parsed_update.get('reply_to_message_id') % current_app.config['APP_EVERY_NTH_MESSAGE_ONLY'] == 0
