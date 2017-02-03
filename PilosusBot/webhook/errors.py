from flask import jsonify
from PilosusBot.exceptions import ValidationError
from . import webhook


def bad_request(message=None):
    response = jsonify({'error': 'bad request', 'message': str(message)})
    response.status_code = 400
    return response


def unauthorized(message):
    response = jsonify({'error': 'unauthorized', 'message': str(message)})
    response.status_code = 401
    return response


def forbidden(message):
    response = jsonify({'error': 'forbidden, webhook error handler', 'message': str(message)})
    response.status_code = 403
    return response


@webhook.errorhandler(ValidationError)
def validation_error(message):
    return bad_request(message.args[0])
