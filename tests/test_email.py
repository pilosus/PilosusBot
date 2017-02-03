import unittest
from threading import Thread
from unittest.mock import patch
from flask import current_app, render_template
from flask_mail import Message
from PilosusBot import create_app, db, celery
from PilosusBot.email import send_email, send_async_email
from PilosusBot.models import User, Role, Language


class EmailTestCase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        """Method called before each unit-test"""
        # create app, set TESTING flag to disable error catching
        self.app = create_app('testing')

        # push app context
        self.app_context = self.app.app_context()
        self.app_context.push()

        # make celery tasks eager
        # celery emulates the API and behavior of AsyncResult,
        # except the result is already evaluated.
        celery.conf.update(CELERY_ALWAYS_EAGER=True)

        # create databases, see config.py for testing db settings
        db.create_all()

        # pre-fill db with minimal needed things
        Role.insert_roles()
        Language.insert_basic_languages()
        User.generate_fake(5)

    def tearDown(self):
        """Method called after each unit-test"""
        # remove current db session
        db.session.remove()

        # remove db itself
        db.drop_all()

        # remove app context
        self.app_context.pop()

    @patch('PilosusBot.email.send_email_thread')
    @patch('PilosusBot.email.send_email_celery')
    def test_send_email_celery(self, mock_celery, mock_thread):
        celery_config = dict(current_app.config)
        celery_config['CELERY_INSTEAD_THREADING'] = True

        with patch.dict(current_app.config, celery_config):
            send_email(to='test@example.com', subject='test subject',
                       template='auth/email/change_email')
            mock_celery.assert_called_with('test@example.com',
                                           'test subject',
                                           'auth/email/change_email',
                                           countdown=None)
            with self.assertRaises(AssertionError):
                mock_thread.assert_called()

            self.assertEqual(mock_thread.call_args_list, [])

    @patch('PilosusBot.email.send_email_thread')
    @patch('PilosusBot.email.send_email_celery')
    def test_send_email_thread(self, mock_celery, mock_thread):
        thread_config = dict(current_app.config)
        thread_config['CELERY_INSTEAD_THREADING'] = False

        with patch.dict(current_app.config, thread_config):
            send_email(to='test@example.com', subject='test subject',
                       template='auth/email/change_email')
            mock_thread.assert_called_with('test@example.com',
                                           'test subject',
                                           'auth/email/change_email')
            with self.assertRaises(AssertionError):
                mock_celery.assert_called()

            self.assertEqual(mock_celery.call_args_list, [])

    @patch('PilosusBot.email.Message', autospec=True)
    @patch('PilosusBot.email.mail.send')
    def test_send_celery_async_email(self, mock_mail_send, mock_message):
        celery_config = dict(current_app.config)
        celery_config['CELERY_INSTEAD_THREADING'] = True

        email = {'to': 'test@example.com',
                 'subject': 'test subject',
                 'template': 'auth/email/invite'}

        user = User.query.first()
        token = user.generate_invite_token()
        kw = {'id': user.id, 'token': token}

        expected_msg = Message(subject="{prefix} {subj}".format(
            prefix=current_app.config['APP_MAIL_SUBJECT_PREFIX'],
            subj=email['subject']),
            sender=current_app.config['APP_MAIL_SENDER'], recipients=[email['to']])

        expected_msg.body = render_template(email['template'] + '.txt',
                                            id=kw['id'],
                                            token=kw['token'])
        expected_msg.html = render_template(email['template'] + '.html',
                                            id=kw['id'],
                                            token=kw['token'])
        mock_message.return_value = expected_msg

        with patch.dict(current_app.config, celery_config):
            send_email(**email, **kw)
            mock_mail_send.assert_called_with(expected_msg)

    @patch.object(Thread, 'start')
    @patch('PilosusBot.email.Message', autospec=True)
    @patch('PilosusBot.email.mail.send')
    def test_send_email_thread(self, mock_mail_send, mock_message, mock_thread):
        thread_config = dict(current_app.config)
        thread_config['CELERY_INSTEAD_THREADING'] = False

        email = {'to': 'test@example.com',
                 'subject': 'test subject',
                 'template': 'auth/email/invite'}

        user = User.query.first()
        token = user.generate_invite_token()
        kw = {'id': user.id, 'token': token}

        expected_msg = Message(subject="{prefix} {subj}".format(
            prefix=current_app.config['APP_MAIL_SUBJECT_PREFIX'],
            subj=email['subject']),
            sender=current_app.config['APP_MAIL_SENDER'], recipients=[email['to']])

        expected_msg.body = render_template(email['template'] + '.txt',
                                            id=kw['id'],
                                            token=kw['token'])
        expected_msg.html = render_template(email['template'] + '.html',
                                            id=kw['id'],
                                            token=kw['token'])
        mock_message.return_value = expected_msg

        mock_thread.side_effect = send_async_email(app=current_app._get_current_object(),
                                                   msg=expected_msg)

        with patch.dict(current_app.config, thread_config):
            send_email(**email, **kw)
            mock_mail_send.assert_called_with(expected_msg)

