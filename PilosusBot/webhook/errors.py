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


def page_not_found(message):
    response = jsonify({'error': 'not found', 'message': str(message)})
    response.status_code = 404
    return response


def method_not_allowed(message):
    response = jsonify({'error': 'method not allowed', 'message': str(message)})
    response.status_code = 405
    return response


def internal_server_error(message):
    response = jsonify({'error': 'internal server error', 'message': str(message)})
    response.status_code = 500
    return response


@webhook.errorhandler(ValidationError)
def validation_error(message):
    return bad_request(message.args[0])
