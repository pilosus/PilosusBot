from flask import render_template, request, jsonify
from . import info

"""
errorhandler decorator will only be invoked for errors in the blueprint.
There's no way to tell if errors 404, 405 or 500 originate from the blueprint.
That's why application-wide error handlers to be used for these errors.

I order to register app-wide error handlers, either the @blueprint.app_errorhandler
or @app.errorhandler must be used instead.

See discussion:
https://github.com/pallets/flask/issues/1935#issuecomment-229308296
"""


@info.app_errorhandler(400)
def bad_request(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'bad request'})
        response.status_code = 400
        return response
    return render_template('error/400.html'), 400


@info.app_errorhandler(401)
def unauthorized(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'unauthorized'})
        response.status_code = 401
        return response
    return render_template('error/401.html'), 401


@info.app_errorhandler(403)
def forbidden(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'forbidden'})
        response.status_code = 403
        return response
    return render_template('error/403.html'), 403


@info.app_errorhandler(404)
def page_not_found(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'not found'})
        response.status_code = 404
        return response
    return render_template('error/404.html'), 404


@info.app_errorhandler(405)
def method_not_allowed(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'method not allowed'})
        response.status_code = 405
        return response
    return render_template('error/405.html'), 405


@info.app_errorhandler(500)
def internal_server_error(e):
    if request.accept_mimetypes.accept_json and \
            not request.accept_mimetypes.accept_html:
        response = jsonify({'error': 'internal server error'})
        response.status_code = 500
        return response
    return render_template('error/500.html'), 500
