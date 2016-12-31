import os
import telegram
import requests

from flask import jsonify, request, url_for, current_app
from ..models import Permission
from .. import csrf
from . import webhook
from .decorators import permission_required
from .authentication import auth


TELEGRAM_API_KEY = os.environ.get('TELEGRAM_TOKEN')
URL = "{base}{api}/".format(base='https://api.telegram.org/bot', api=TELEGRAM_API_KEY)
bot = telegram.Bot(token=TELEGRAM_API_KEY)


@webhook.route('/{api_key}/<action>'.format(api_key=TELEGRAM_API_KEY), methods=['POST'])
@csrf.exempt
@auth.login_required
@permission_required(Permission.ADMINISTER)
def set_webhook(action):
    """
    Set an URL for Telegram to send POST requests with chat updates.

    $ http --auth email:password --json POST https://bot.address/webhook/api_key/<action> text=Hello
    :param action: str (set, unset)
    :return: JSON
    """

    if action == 'unset':
        # deactivate the bot!
        url = ''
    else:
        # URL to be registered by Telegram
        url = url_for('webhook.handle_webhook', _external=True)

    payload = {'url': url,  # URL Telegram will post updates to
               'certificate': open(current_app.config['SERVER_PUBLIC_KEY'], 'rb'),  # open public key in binary mode
               'max_connections': current_app.config['SERVER_PUBLIC_KEY'],
               'allowed_updates': [],  # if empty list, then all kinds of updates, including messages, get catched.
               }

    context = {'status': None, 'url': url}

    # make a request to telegram API, catch exceptions if any, return status
    try:
        # set timeout to 120s, since we want server to unset bot even under high load/DDoS
        r = requests.post(URL + 'setWebhook', json=payload, timeout=120)
    except requests.exceptions.RequestException as err:
        context['status'] = str(err)
    else:
        context['status'] = r.text

    """
    status = None
    try:
        # TODO remove after DEBUGGING!
        status = bot.setWebhook(url)
    except Exception as err:
        context['status'] = 'exception occurred: {0}'.format(err)

    if status:
        context['status'] = 'success'
    else:
        context['status']= 'fail'
    """

    return jsonify(context)

# TODO rewrite using bare requests
@webhook.route('/{api_key}/handle'.format(api_key=TELEGRAM_API_KEY), methods=['POST'])
@csrf.exempt
def handle_webhook():
    """
    Handle POST request sent from Telegram with chat updates.

    :return: JSON
    """
    global bot

    # receive JSON request, then transform it to telegram object
    update = telegram.Update.de_json(request.get_json(force=True))

    # get chat id
    chat_id = update.message.chat.id

    # TODO process text here!
    # get text messages from updates
    text = update.message.text.encode('utf-8')

    # send the text (uppercased) back to the chat
    bot.sendMessage(chat_id=chat_id, text=text.upper())
