import sys
import unittest
from unittest.mock import patch, MagicMock, Mock
from flask import url_for, request, current_app
from flask_login import login_user
from PilosusBot import create_app, db
from PilosusBot.models import Language, Role, Sentiment, User
from flask_sqlalchemy import BaseQuery


# TODO
# DRY: remove repeating code for logging in
# login_user from flask_loging + helper function?
class AuthTestCase(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        """Method called before each unit-test"""
        # create app, set TESTING flag to disable error catching
        self.app = create_app('testing')

        # push app context
        self.app_context = self.app.app_context()
        self.app_context.push()

        # create databases, see config.py for testing db settings
        db.create_all()

        # pre-fill db with minimal needed things
        Role.insert_roles()
        Language.insert_basic_languages()
        #User.generate_fake(10)
        #Sentiment.generate_fake(25)

        # Werkzeug Client to make requests
        self.client = self.app.test_client(use_cookies=True)

    def tearDown(self):
        """Method called after each unit-test"""
        # remove current db session
        db.session.remove()

        # remove db itself
        db.drop_all()

        # remove app context
        self.app_context.pop()

    def create_user(self, role_name='Administrator', email='admin@example.com',
                    username='admin', password='test', invited=True, confirmed=True):
        role = Role.query.filter_by(name=role_name).first()
        user = User(email=email,
                    username=username,
                    role=role,
                    password=password,
                    invited=invited,
                    confirmed=confirmed)
        db.session.add(user)
        db.session.commit()
        return user

    def login(self, email='admin@example.com', password='test', follow_redirects=True):
        response = self.client.post(url_for('auth.login'),
                                    data=dict(email=email, password=password),
                                    follow_redirects=follow_redirects)
        return response

    def test_login_post(self):
        admin = self.create_user()
        valid_credentials_no_redirect = self.login(email='admin@example.com',
                                                   password='test',
                                                   follow_redirects=False)

        # follow_redirect should be False in order to catch code 302, not 200
        self.assertEqual(valid_credentials_no_redirect.status_code, 302,
                         'Failed to redirect to info.index page')

        valid_user_valid_password_access = self.login(email='admin@example.com',
                                                      password='test',
                                                      follow_redirects=True)

        self.assertIn(b'Documentation', valid_user_valid_password_access.data,
                      'Failed to redirect to info.index page')
        self.assertEqual('info.index', request.endpoint)

        non_existent_user_access = self.login(email='non_existent@example.com',
                                              password='no', follow_redirects=True)

        self.assertIn(b'Invalid username or password', non_existent_user_access.data,
                      'Failed to restrict access to a non-existent user')

        valid_user_invalid_login_access = self.login(email='admin@example.com',
                                                     password='wrong_password',
                                                     follow_redirects=True)

        self.assertIn(b'Invalid username or password', valid_user_invalid_login_access.data,
                      'Failed to restrict access to a non-existent user')

    def test_login_get(self):
        response = self.client.get(url_for('auth.login'), follow_redirects=True)

        self.assertIn(b'Log In', response.data,
                      'Failed to show log-in form on GET request')
        self.assertIn(b'Forgot your password?', response.data)

    def test_before_request(self):
        admin = self.create_user(confirmed=False)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)

        outside_auth_response = self.client.get(url_for('admin.sentiments'),
                                                follow_redirects=True)
        data = outside_auth_response.get_data(as_text=True)

        self.assertIn('Confirm your account', data,
                      'Failed to redirect an unconfirmed user to account confirmation page')

    def test_unconfirmed(self):
        response = self.client.get(url_for('auth.unconfirmed'), follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Documentation', data,
                      'Failed to redirect anonymous user to info.index page')

    def test_logout(self):
        anon_logout_response = self.client.get(url_for('auth.logout'),
                                               follow_redirects=True)
        anon_data = anon_logout_response.get_data(as_text=True)
        self.assertNotIn('You have been logged out', anon_data,
                         'Failed to redirect anonymous user '
                         'attempting to logout to login page first')
        self.assertIn('Please log in to access this page', anon_data,
                      'Failed to notify anonymous user to log in '
                      'before accessing logout page')

        admin_role = Role.query.filter_by(name='Administrator').first()
        admin = User(email='admin@example.com',
                     username='admin',
                     role=admin_role,
                     password='test',
                     confirmed=False,
                     )
        db.session.add(admin)
        db.session.commit()

        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)

        logged_user_logout_response = self.client.get(url_for('auth.logout'),
                                                      follow_redirects=True)
        logged_user_data = logged_user_logout_response.get_data(as_text=True)

        self.assertIn('You have been logged out', logged_user_data,
                      'Failed to logout user previously logged in')
        self.assertNotIn('Please log in to access this page', logged_user_data)

    def test_register_get_registration_closed(self):
        self.app.config['APP_REGISTRATION_OPEN'] = False
        registration_closed_response = self.client.get(url_for('auth.register'),
                                                       follow_redirects=True)
        registration_closed_data = registration_closed_response.get_data(as_text=True)

        self.assertIn('Registration for new users is by invitation only.',
                      registration_closed_data, 'Failed to notify user that registration is by invites only.')
        self.assertIn('Documentation', registration_closed_data,
                      'Failed to redirect user from registration page when '
                      'registration is by invites only.')

    def test_register_get_registration_open(self):
        self.app.config['APP_REGISTRATION_OPEN'] = True
        registration_open_response = self.client.get(url_for('auth.register'),
                                                     follow_redirects=True)
        registration_open_data = registration_open_response.get_data(as_text=True)

        self.assertIn('Register', registration_open_data,
                      'Failed to show registration page when '
                      'registration is open for all users.')

    @patch.object(User, 'generate_confirmation_token')
    @patch('PilosusBot.auth.views.send_email')
    def test_register_post(self, mock_send, mock_generate_token):
        mock_generate_token.side_effect = lambda *args, **kwargs: b'token'
        self.app.config['APP_REGISTRATION_OPEN'] = True
        email = 'test@example.com'
        username = 'test_user'
        password = 'test'
        password2 = 'test'

        response = self.client.post(url_for('auth.register'),
                                    data=dict(email=email, username=username,
                                              password=password, password2=password2),
                                    follow_redirects=True)
        data = response.get_data(as_text=True)
        user = User.query.filter_by(email=email).first()

        self.assertIn('A confirmation email has been sent to you by email', data,
                      'Failed to notify user submitted registration form '
                      'about confirmation email sent.')
        self.assertIn('Log In', data,
                      'Failed to redirect user after registration submission '
                      'to a login page.')
        mock_send.assert_called_once_with(email, 'Confirm Your Account',
                                          'auth/email/confirm', user=user,
                                          token=b'token')

    def test_resiter_validation_error(self):
        admin = self.create_user(confirmed=True)
        self.app.config['APP_REGISTRATION_OPEN'] = True

        response = self.client.post(url_for('auth.register'),
                                    data=dict(email=admin.email,
                                              username=admin.username,
                                              password='test',
                                              password2='test'),
                                    follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Email already registered', data,
                      'Failed to notify user that the email already in use.')
        self.assertIn('Username already in use', data,
                      'Failed to notify user that the username already in use.')

    def test_confirm_invalid_token(self):
        admin = self.create_user(confirmed=False)

        admin_token = admin.generate_confirmation_token()
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)

        response_not_confirmed = self.client.get(url_for('auth.confirm', token='blah'),
                                                 follow_redirects=True)
        data_not_confirmed = response_not_confirmed.get_data(as_text=True)
        self.assertIn('The confirmation link is invalid or has expired', data_not_confirmed,
                      'Failed to notify user that token confirmation failed')

    def test_confirm_successful_confirmation(self):
        admin = self.create_user(confirmed=False)

        admin_token = admin.generate_confirmation_token()
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)
        response_confirm = self.client.get(url_for('auth.confirm', token=admin_token),
                                           follow_redirects=True)
        data_confirm = response_confirm.get_data(as_text=True)
        self.assertIn('You have confirmed your account', data_confirm,
                      'Failed to confirm valid token.')
        self.assertIn('Documentation', data_confirm,
                      'Failed to redirect after successful token confirmation.')

    def test_confirm_already_confirmed(self):
        yet_another_admin = self.create_user(email='yet_another_admin@example.com',
                                             username='yet_another_admin',
                                             password='test',
                                             confirmed=True)

        yet_another_admin_token = yet_another_admin.generate_confirmation_token()
        response = self.login(email='yet_another_admin@example.com', password='test',
                              follow_redirects=True)

        response_already_confirmed = self.client.get(url_for('auth.confirm',
                                                             token=yet_another_admin_token),
                                                     follow_redirects=True)
        data_already_confirmed = response_already_confirmed.get_data(as_text=True)
        self.assertIn('Your account already confirmed', data_already_confirmed,
                      'Failed to notify user already confirmed')
        self.assertIn('Documentation', data_already_confirmed,
                      'Failed to redirect already confirmed user.')

    @patch.object(User, 'generate_confirmation_token')
    @patch('PilosusBot.auth.views.send_email')
    def test_resend_confirmation(self, mock_send, mock_generate_token):
        mock_generate_token.side_effect = lambda *args, **kwargs: b'token'
        admin = self.create_user(confirmed=False)

        admin_token = admin.generate_confirmation_token()
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)
        response_confirm = self.client.get(url_for('auth.resend_confirmation',
                                                   token=admin_token),
                                           follow_redirects=True)
        data_confirm = response_confirm.get_data(as_text=True)

        self.assertIn('A new confirmation email has been sent to you by email',
                      data_confirm,
                      'Failed to send new confirmation')
        mock_send.assert_called_once_with(admin.email, 'Confirm Your Account',
                                          'auth/email/confirm', user=admin,
                                          token=b'token')

    def test_change_password_get(self):
        admin = self.create_user(confirmed=False)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)

        change_password_response = self.client.get(url_for('auth.change_password'),
                                                   follow_redirects=True)
        change_password_data = change_password_response.get_data(as_text=True)
        self.assertIn('Change Password', change_password_data,
                      'Failed to show change email form to the authenticated user.')

    def test_change_password_post_updated(self):
        admin = self.create_user(confirmed=False)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)

        change_password_response_update = \
            self.client.post(url_for('auth.change_password'),
                             data=dict(old_password='test',
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)
        change_password_data = change_password_response_update.get_data(as_text=True)

        self.assertIn('Your password has been updated', change_password_data,
                      'Failed to update password after valid password change submission '
                      'of the authenticated user.')

    def test_change_password_post_invalid(self):
        admin = self.create_user(confirmed=False)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)

        change_password_response_update = \
            self.client.post(url_for('auth.change_password'),
                             data=dict(old_password='wrong_password',
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)
        change_password_data = change_password_response_update.get_data(as_text=True)

        self.assertIn('Invalid password', change_password_data,
                      'Failed to notify user after invalid password change submission.')
        self.assertNotIn('Documentation', change_password_data,
                         'Failed to stay on email change page '
                         'after failed attempt ot change password.')

    def test_password_reset_request_get_authenticated(self):
        admin = self.create_user(confirmed=True)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)

        response = self.client.get(url_for('auth.password_reset_request'),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Documentation', data,
                      'Failed to redirect non-anonymous user to info.index page after '
                      'attempt to reset password.')

    def test_password_reset_request_get_anon(self):
        response = self.client.get(url_for('auth.password_reset_request'),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Reset Password', data,
                      'Failed to show password reset form to am anonymous use after.')

    @patch.object(User, 'generate_reset_token')
    @patch('PilosusBot.auth.views.send_email')
    def test_password_reset_request_post_existing_email(self, mock_send, mock_generate_token):
        mock_generate_token.side_effect = lambda *args, **kwargs: b'token'
        admin = self.create_user(confirmed=True)

        password_reset_response = \
            self.client.post(url_for('auth.password_reset_request'),
                             data=dict(email='admin@example.com',
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)
        password_reset_data = password_reset_response.get_data(as_text=True)
        self.assertIn('An email with instructions to reset your password has been',
                      password_reset_data,
                      'Failed to send email after successful resetting of password.')

        mock_send.assert_called_once_with(admin.email, 'Reset Your Password',
                                          'auth/email/reset_password',
                                          user=admin,
                                          token=b'token',
                                          next=None)

    @patch.object(User, 'generate_confirmation_token')
    @patch('PilosusBot.auth.views.send_email')
    def test_password_reset_request_post_no_such_email(self, mock_send, mock_generate_token):
        mock_generate_token.side_effect = lambda *args, **kwargs: b'token'
        admin = self.create_user(confirmed=True)

        password_reset_response = \
            self.client.post(url_for('auth.password_reset_request'),
                             data=dict(email='no_such_email@example.com',
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)
        password_reset_data = password_reset_response.get_data(as_text=True)
        self.assertIn('No such email registered',
                      password_reset_data,
                      'Failed to notify user about email submitted bot registered yet.')

        self.assertEqual(mock_send.call_args_list, [])
        self.assertEqual(mock_generate_token.call_args_list, [])

    def test_password_reset_get_not_anon(self):
        admin = self.create_user(confirmed=True)

        token = admin.generate_reset_token()
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)

        response = self.client.get(url_for('auth.password_reset', token=token),
                                   follow_redirects=False)
        self.assertEqual(response.status_code, 302,
                         'Failed to redirect an anonymous user '
                         'requesting password redirect with token URL.')

    def test_password_reset_get_anon(self):
        admin = self.create_user(confirmed=True)

        token = admin.generate_reset_token()
        response = self.client.get(url_for('auth.password_reset', token=token),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Reset Password', data,
                      'Failed show password resetting form for'
                      'authenticated user.')

    def test_password_reset_post_no_such_email(self):
        password_reset_response = \
            self.client.post(url_for('auth.password_reset', token='test'),
                             data=dict(email='no_such_email@example.com',
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)
        password_reset_data = password_reset_response.get_data(as_text=True)
        self.assertIn('Unknown email address',
                      password_reset_data,
                      'Failed to notify user that no such email fond in the DB '
                      'after submission of the password resetting form.')

    def test_password_reset_post_valid_user(self):
        admin = self.create_user(confirmed=True)
        token = admin.generate_reset_token()

        password_reset_response = \
            self.client.post(url_for('auth.password_reset', token=token),
                             data=dict(email=admin.email,
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)
        password_reset_data = password_reset_response.get_data(as_text=True)
        self.assertIn('Your password has been updated',
                      password_reset_data,
                      'Failed to reset password to a user with valid token.')

        self.assertIn('Log In', password_reset_data,
                      'Failed redirect user to a login page after successful '
                      'password reset.')

    def test_password_reset_post_invalid_token(self):
        admin = self.create_user(confirmed=True)

        # wrong token!
        token = admin.generate_invite_token()

        password_reset_response = \
            self.client.post(url_for('auth.password_reset', token=token),
                             data=dict(email=admin.email,
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)
        password_reset_data = password_reset_response.get_data(as_text=True)
        self.assertIn('Documentation',
                      password_reset_data,
                      'Failed to redirect user with invalid token after an attempt '
                      'to reset password.')

    @patch.object(BaseQuery, 'first')
    @patch('PilosusBot.auth.forms.User', autospec=True)
    def test_password_reset_post_no_such_email2(self, mock_user, mock_first):
        # User.query is s flask_sqlalchemy's BaseQuery, so we need to patch it.
        # Since we do no access BaseQuery explicitly in auth.views,
        # we have to patch User class with autospeccing on too.
        mock_first.side_effect = lambda *args, **kwargs: None

        password_reset_response = \
            self.client.post(url_for('auth.password_reset', token='test'),
                             data=dict(email='test@example.com',
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)
        password_reset_data = password_reset_response.get_data(as_text=True)
        self.assertIn('Documentation',
                      password_reset_data,
                      'Failed to redirect user non-existent email after an attempt '
                      'to reset password.')

        mock_first.assert_called_with()

    def test_invite_request_get(self):
        number_of_users = current_app.config['APP_ITEMS_PER_PAGE'] * 2
        User.generate_fake(count=number_of_users)
        # will be first user in the list of users, since it's not confirmed yet

        user = self.create_user(email='invited_user@example.com',
                                username='Unconfirmed user on the first page',
                                role_name='User', confirmed=False)
        admin = self.create_user(confirmed=True)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)

        response_page_1 = self.client.get(url_for('auth.invite_request'),
                                          follow_redirects=True)
        data_page_1 = response_page_1.get_data(as_text=True)
        self.assertIn('invited_user@example.com', data_page_1,
                      'Failed to show unconfirmed invited user on the first page '
                      'of user invitation form page.')
        response_page_2 = self.client.get(url_for('auth.invite_request', page=2),
                                          follow_redirects=True)
        data_page_2 = response_page_2.get_data(as_text=True)
        self.assertNotIn('invited_user@example.com', data_page_2,
                         'Failed to show invited user on the first page '
                         'of user invitation form page.')
        response_page_3 = self.client.get(url_for('auth.invite_request', page=3),
                                          follow_redirects=True)
        data_page_3 = response_page_3.get_data(as_text=True)
        self.assertNotIn('invited_user@example.com', data_page_3)

        response_page_4 = self.client.get(url_for('auth.invite_request', page=4),
                                          follow_redirects=True)
        data_page_4 = response_page_4.get_data(as_text=True)
        self.assertNotIn('@', data_page_4,
                         'Failed to show empty list of users when pagination '
                         'is exhausted as error_out=False prevents '
                         'throwing error 404.')

    @patch.object(User, 'generate_invite_token')
    @patch('PilosusBot.auth.views.send_email')
    def test_invite_request_post(self, mock_send, mock_generate_token):
        mock_generate_token.side_effect = lambda *args, **kwargs: b'token'
        admin = self.create_user(confirmed=True)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)
        user_role = Role.query.filter_by(name='User').first()

        invite_response = \
            self.client.post(url_for('auth.invite_request'),
                             data=dict(email='invited_user@example.com',
                                       role=user_role.id),
                             follow_redirects=True)
        invite_data = invite_response.get_data(as_text=True)
        self.assertIn('An invitation has been sent by email',
                      invite_data,
                      'Failed to send email after successful invitation of a user.')
        user = User.query.filter_by(email='invited_user@example.com').first()

        mock_generate_token.assert_called()
        mock_send.assert_called_once_with(user.email,
                                          'Invitation to participate',
                                          'auth/email/invite',
                                          id=user.id,
                                          token=b'token')

    def test_invite_request_post_validation_error(self):
        admin = self.create_user(confirmed=True)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)
        user_role = Role.query.filter_by(name='User').first()

        invite_response = \
            self.client.post(url_for('auth.invite_request'),
                             data=dict(email='admin@example.com',
                                       role=user_role.id),
                             follow_redirects=True)
        invite_data = invite_response.get_data(as_text=True)
        self.assertIn('Email already registered',
                      invite_data,
                      'Failed to notify user that email already in use.')

    def test_invite_accept_get_not_anon(self):
        admin = self.create_user(confirmed=True)
        token = admin.generate_invite_token()
        login_response = self.login(email='admin@example.com', password='test',
                                    follow_redirects=True)

        response = self.client.get(url_for('auth.invite_accept',
                                           id=admin.id, token=token),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Invites are for new users only.', data,
                      'Failed to refuse invitation accept '
                      'for the authenticated user.')

    def test_invite_accept_get_invalid_user_id(self):
        response = self.client.get(url_for('auth.invite_accept',
                                           id=sys.maxsize,
                                           token=b'token'),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('You are not among the invitees.', data,
                      'Failed to refuse invitation accept '
                      'for a non-existent user.')

    def test_invite_accept_get_confirmed_user(self):
        admin = self.create_user(confirmed=True)
        token = admin.generate_invite_token()
        response = self.client.get(url_for('auth.invite_accept',
                                           id=admin.id,
                                           token=token),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('You have previously confirmed your account', data)
        self.assertIn('Log In', data,
                      'Failed to redirect confirmed user to a login page '
                      'when the user attempts to accept invitation.')

    def test_invite_accept_post_valid_token(self):
        user = self.create_user(email='invited_user@example.com',
                                password='test',
                                invited=True,
                                role_name='User',
                                confirmed=False)
        token = user.generate_invite_token()
        invite_response = \
            self.client.post(url_for('auth.invite_accept',
                                     id=user.id, token=token),
                             data=dict(username='newly_created_user',
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)
        invite_data = invite_response.get_data(as_text=True)
        self.assertIn('You have confirmed your account.',
                      invite_data,
                      'Failed confirm user accepted invitation.')
        self.assertIn('Documentation', invite_data,
                      'Failed to redirect a user after '
                      'an attempt to accept invitation.')

    def test_invite_accept_post_invalid_token(self):
        user = self.create_user(email='invited_user@example.com',
                                password='test',
                                invited=True,
                                role_name='User',
                                confirmed=False)
        invite_response = \
            self.client.post(url_for('auth.invite_accept',
                                     id=user.id, token=b'token'),
                             data=dict(username='newly_created_user',
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)
        invite_data = invite_response.get_data(as_text=True)
        self.assertIn('The confirmation link is invalid or has expired.',
                      invite_data,
                      'Failed to notify user who accepted invitation '
                      'about invalid token.')
        self.assertIn('Documentation', invite_data,
                      'Failed to redirect a user after '
                      'an attempt to accept invitation.')

    def test_invite_accept_post_existing_user(self):
        admin = self.create_user(username='invited_user')
        user = self.create_user(email='invited_user@example.com',
                                password='test',
                                invited=True,
                                role_name='User',
                                confirmed=False)
        token = user.generate_invite_token()
        invite_response = \
            self.client.post(url_for('auth.invite_accept',
                                     id=user.id, token=token),
                             data=dict(username='invited_user',
                                       password='new_password',
                                       password2='new_password'),
                             follow_redirects=True)

        invite_data = invite_response.get_data(as_text=True)
        self.assertIn('Username already in use.',
                      invite_data,
                      'Failed to notify user accepted invitation '
                      'about username being in use.')

    def test_change_email_get(self):
        admin = self.create_user(confirmed=True)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)
        response = self.client.get(url_for('auth.change_email_request'),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Change Your Email Address', data,
                      'Failed to show change email form '
                      'to the authenticated used.')

    @patch('PilosusBot.auth.views.current_user')
    @patch('PilosusBot.auth.views.send_email')
    def test_change_email_post_valid_email_password(self, mock_send,
                                                    mock_current_user):
        mock_current_user.generate_email_change_token = \
            MagicMock(side_effect=lambda *args, **kwargs: b'token')
        mock_current_user.verify_password = \
            MagicMock(return_value=True)

        admin = self.create_user(confirmed=True)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)
        change_email_response = \
            self.client.post(url_for('auth.change_email_request'),
                             data=dict(email='new_admin@example.com',
                                       password='test'),
                             follow_redirects=True)

        data = change_email_response.get_data(as_text=True)
        self.assertIn('An email with instructions to confirm your new email', data,
                      'Failed to send token upon email change request '
                      'of the valid user.')

        mock_send.assert_called_once_with('new_admin@example.com',
                                          'Confirm your email address',
                                          'auth/email/change_email',
                                          user=mock_current_user,
                                          token=b'token')
        mock_current_user.verify_password.assert_called_once_with('test')
        mock_current_user.generate_email_change_token.\
            assert_called_with('new_admin@example.com')

    def test_change_email_post_password_not_verified(self):
        admin = self.create_user(confirmed=True)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)
        change_email_response = \
            self.client.post(url_for('auth.change_email_request'),
                             data=dict(email='new_admin@example.com',
                                       password='wrong_password'),
                             follow_redirects=True)

        data = change_email_response.get_data(as_text=True)
        self.assertIn('Invalid email or password.', data,
                      'Failed to notify user who attempted to '
                      'change email with wrong password.')

    def test_change_email_post_validation_error(self):
        admin = self.create_user(confirmed=True)
        response = self.login(email='admin@example.com', password='test',
                              follow_redirects=True)
        change_email_response = \
            self.client.post(url_for('auth.change_email_request'),
                             data=dict(email='admin@example.com',
                                       password='wrong_password'),
                             follow_redirects=True)

        data = change_email_response.get_data(as_text=True)
        self.assertIn('Email already registered.', data,
                      'Failed to notify user who attempted to '
                      'change email that email already registered.')

    @patch('PilosusBot.auth.views.current_user')
    def test_change_email_valid_token(self, mock_user):
        mock_user.change_email = MagicMock(return_value=True)
        admin = self.create_user(confirmed=True)
        login_response = self.login(email='admin@example.com', password='test',
                                    follow_redirects=True)
        response = self.client.get(url_for('auth.change_email', token=b'token'),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Your email address has been updated', data,
                      'Failed to update email for a user with a valid token.')
        self.assertIn('Documentation', data,
                      'Failed to redirect user to a info.index after '
                      'successful change of email.')

    @patch('PilosusBot.auth.views.current_user')
    def test_change_email_invalid_token(self, mock_user):
        mock_user.change_email = MagicMock(return_value=False)
        admin = self.create_user(confirmed=True)
        login_response = self.login(email='admin@example.com', password='test',
                                    follow_redirects=True)
        response = self.client.get(url_for('auth.change_email', token=b'token'),
                                   follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Invalid request', data,
                      'Failed to update email for a user with a valid token.')
        self.assertIn('Documentation', data,
                      'Failed to redirect user to a info.index after '
                      'failed attempt to change email address.')

    def test_user(self):
        user = self.create_user(email='invited_user@example.com',
                                username='username',
                                password='test',
                                invited=True,
                                role_name='Administrator',
                                confirmed=True)
        login_response = self.login(email='invited_user@example.com', password='test',
                                    follow_redirects=True)
        # pagination takes 2 full pages + 1 item on the page 3
        items_per_page = current_app.config['APP_ITEMS_PER_PAGE']
        Sentiment.generate_fake(count=(items_per_page * 2 + 1))

        no_such_user_response = \
            self.client.get(url_for('auth.user',
                                    username='no_such_user'),
                            follow_redirects=False)
        self.assertEqual(no_such_user_response.status_code, 404)
        no_such_user_data = no_such_user_response.get_data(as_text=True)
        self.assertNotIn('no_such_user', no_such_user_data)

        page1_response = \
            self.client.get(url_for('auth.user',
                                    username='username', page=1),
                            follow_redirects=True)
        data_page1 = page1_response.get_data(as_text=True)

        sentiments = user.sentiments.order_by(Sentiment.timestamp.desc()).all()
        page1_sentiment = sentiments[0]
        page2_sentiment = sentiments[items_per_page]
        page3_sentiment = sentiments[-1]

        self.assertIn(page1_sentiment.body_html, data_page1,
                      'Failed to show the oldest sentiment on the first page.')

        page2_response = \
            self.client.get(url_for('auth.user',
                                    username='username', page=2),
                            follow_redirects=True)
        data_page2 = page2_response.get_data(as_text=True)

        self.assertIn(page2_sentiment.body_html, data_page2,
                      'Failed to show the sentiment on the proper page.')

        page3_response = \
            self.client.get(url_for('auth.user',
                                    username='username', page=3),
                            follow_redirects=True)
        data_page3 = page3_response.get_data(as_text=True)

        self.assertIn(page3_sentiment.body_html, data_page3,
                      'Failed to show the sentiment on the proper page.')

        page777_response = \
            self.client.get(url_for('auth.user',
                                    username='username', page=777),
                            follow_redirects=True)
        data_page777 = page777_response.get_data(as_text=True)

        self.assertNotIn(page1_sentiment.body_html, data_page777,
                         'Failed to show empty list of sentiments '
                         'after pagination exhausted.')
        self.assertNotIn(page2_sentiment.body_html, data_page777)
        self.assertNotIn(page3_sentiment.body_html, data_page777)

    def test_edit_profile_get(self):
        user = self.create_user(email='user@example.com',
                                username='username',
                                password='test',
                                invited=True,
                                role_name='Administrator',
                                confirmed=True)
        login_response = self.login(email='user@example.com',
                                    password='test',
                                    follow_redirects=True)
        invalid_form_response = \
            self.client.get(url_for('auth.edit_profile'),
                            follow_redirects=True)
        invalid_form_data = invalid_form_response.get_data(as_text=True)
        self.assertIn('Edit Your Profile', invalid_form_data)

    def test_edit_profile_post(self):
        user = self.create_user(email='user@example.com',
                                username='username',
                                password='test',
                                invited=True,
                                role_name='Administrator',
                                confirmed=True)
        login_response = self.login(email='user@example.com',
                                    password='test',
                                    follow_redirects=True)
        response = self.client.post(url_for('auth.edit_profile'),
                                    data=dict(name='Test User',
                                              location='Moscow',
                                              about_me='Nothing special'),
                                    follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Your profile has been updated', data,
                      'Failed to update profile of the valid used.')
        self.assertIn('Nothing special', data,
                      'Failed to redirect user after updating the profile.')

    def test_edit_profile_admin_get(self):
        user = self.create_user(email='user@example.com',
                                username='username',
                                password='test',
                                invited=True,
                                role_name='Administrator',
                                confirmed=True)
        login_response = self.login(email='user@example.com',
                                    password='test',
                                    follow_redirects=True)
        invalid_form_response = \
            self.client.get(url_for('auth.edit_profile_admin',
                                    id=user.id),
                            follow_redirects=True)
        invalid_form_data = invalid_form_response.get_data(as_text=True)
        self.assertIn('Edit Your Profile', invalid_form_data)

    def test_edit_admin_post(self):
        user1 = self.create_user(email='user1@example.com',
                                 username='username1',
                                 password='test',
                                 invited=True,
                                 role_name='Administrator',
                                 confirmed=True)
        user2 = self.create_user(email='user2@example.com',
                                 username='username2',
                                 password='test',
                                 invited=True,
                                 role_name='Administrator',
                                 confirmed=True)

        login_response = self.login(email='user1@example.com',
                                    password='test',
                                    follow_redirects=True)
        response = self.client.post(url_for('auth.edit_profile_admin',
                                            id=user2.id),
                                    data=dict(email='user3@example.com',
                                              username='username3',
                                              confirmed=True,
                                              role=Role.query.filter_by(name='User').first().id,
                                              name='TestUser3',
                                              location='MiddleOfNowhere',
                                              about_me='Nothing interesting'),
                                    follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('The profile has been updated', data,
                      'Failed to update user profile as admin.')
        self.assertIn('MiddleOfNowhere', data,
                      "Failed to redirect after updating user's profiles as admin.")

    def test_edit_admin_post_validation_error(self):
        user1 = self.create_user(email='user1@example.com',
                                 username='username1',
                                 password='test',
                                 invited=True,
                                 role_name='Administrator',
                                 confirmed=True)
        user2 = self.create_user(email='user2@example.com',
                                 username='username2',
                                 password='test',
                                 invited=True,
                                 role_name='Administrator',
                                 confirmed=True)

        login_response = self.login(email='user1@example.com',
                                    password='test',
                                    follow_redirects=True)
        response = self.client.post(url_for('auth.edit_profile_admin',
                                            id=user2.id),
                                    data=dict(email='user1@example.com',
                                              username='username1',
                                              confirmed=True,
                                              role=Role.query.filter_by(name='User').first().id,
                                              name='TestUser1',
                                              location='MiddleOfNowhere',
                                              about_me='Nothing interesting'),
                                    follow_redirects=True)
        data = response.get_data(as_text=True)
        self.assertIn('Email already registered.', data)
        self.assertIn('Username already in use.', data)
