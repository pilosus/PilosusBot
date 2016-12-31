from threading import Thread
from flask import current_app, render_template
from flask_mail import Message
from . import mail, celery
from celery import shared_task


def send_email(to, subject, template, **kwargs):
    """Send email using either Celery, or Thread.

    Selection depends on CELERY_INSTEAD_THREADING config variable.
    """
    app = current_app._get_current_object()
    if app.config['CELERY_INSTEAD_THREADING']:
        send_email_celery(to, subject, template, countdown=None, **kwargs)
    else:
        send_email_thread(to, subject, template, **kwargs)


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)


def send_email_thread(to, subject, template, **kwargs):
    """Send async email using threading.
    """
    app = current_app._get_current_object()
    msg = Message(app.config['APP_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['APP_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    thr = Thread(target=send_async_email, args=[app, msg])
    thr.start()
    return thr


@shared_task
def send_celery_async_email(msg):
    mail.send(msg)


# NOTE rename to send_email in production if Thread support is not needed
def send_email_celery(to, subject, template, countdown=None, **kwargs):
    """Send async email using Celery.
    """
    app = current_app._get_current_object()
    msg = Message(app.config['APP_MAIL_SUBJECT_PREFIX'] + ' ' + subject,
                  sender=app.config['APP_MAIL_SENDER'], recipients=[to])
    msg.body = render_template(template + '.txt', **kwargs)
    msg.html = render_template(template + '.html', **kwargs)
    send_celery_async_email.apply_async(args=[msg], countdown=countdown)

