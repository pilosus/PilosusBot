from datetime import datetime
import forgery_py
import hashlib
import time
import unittest
from unittest.mock import patch
from PilosusBot import create_app, db
from PilosusBot.models import Role, Language, User, AnonymousUser, Permission, Sentiment
from PilosusBot.exceptions import ValidationError
from flask import current_app, request


class ModelsTestCase(unittest.TestCase):
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

    def test_role(self):
        user = Role.query.filter_by(name='User').first()
        self.assertEqual(repr(user), "<Role 'User'>")

    def test_is_testing(self):
        self.assertTrue(current_app.config['TESTING'])
        self.assertFalse(current_app.config['SSL_DISABLE'])
        self.assertFalse(request.is_secure)

    def test_user_suspend(self):
        admin_role = Role.query.filter_by(name='Administrator').first()
        user_role = Role.query.filter_by(name='User').first()

        User.generate_fake(count=1, roles=[admin_role])
        admin_user = User.query.filter_by(role=admin_role).first()

        self.assertEqual(admin_user.role, admin_role)

        is_suspended = admin_user.suspend()
        self.assertTrue(is_suspended)

        self.assertNotEqual(admin_user.role, admin_role)
        self.assertEqual(admin_user.role, user_role)

    def test_user_add_admin(self):
        admin_role = Role.query.filter_by(name='Administrator').first()
        admin_user = User.query.filter_by(role=admin_role).first()

        self.assertIsNone(admin_user)

        User.add_admin()
        admin_user2 = User.query.filter_by(role=admin_role).first()
        self.assertIsNotNone(admin_user2)
        self.assertEqual(admin_user2.role, admin_role)

    def test_user_init(self):
        user_role = Role.query.filter_by(name='User').first()
        admin_role = Role.query.filter_by(name='Administrator').first()

        username0 = forgery_py.internet.user_name()
        u0 = User(email=None,
                  username=username0,
                  password=forgery_py.basic.password(),
                  avatar_hash=None,
                  role=None,
                  confirmed=True)
        db.session.add(u0)
        db.session.commit()

        fetch_u0 = User.query.filter_by(username=username0).first()
        self.assertIsNone(fetch_u0.avatar_hash)

        u1 = User(email=forgery_py.internet.email_address(),
                  username=forgery_py.internet.user_name(),
                  password=forgery_py.basic.password(),
                  avatar_hash=None,
                  role=None,
                  confirmed=True)
        db.session.add(u1)
        db.session.commit()

        fetch_u1 = User.query.first()
        self.assertEqual(fetch_u1.role, user_role)

        u2 = User(email=current_app.config['APP_ADMIN_EMAIL'],
                  username=forgery_py.internet.user_name(),
                  password=forgery_py.basic.password(),
                  avatar_hash=None,
                  role=None,
                  confirmed=True)
        db.session.add(u2)
        db.session.commit()

        fetch_u2 = User.query.filter_by(email=current_app.config['APP_ADMIN_EMAIL']).first()
        self.assertEqual(fetch_u2.role, admin_role)

        avatar_hash_expected = hashlib.md5(current_app.config['APP_ADMIN_EMAIL'].\
                                           encode('utf-8')).hexdigest()
        self.assertEqual(fetch_u2.avatar_hash, avatar_hash_expected)

    def test_user_password(self):
        user_role = Role.query.filter_by(name='User').first()
        user = User(email=forgery_py.internet.email_address(),
                    username=forgery_py.internet.user_name(),
                    password='old_password',
                    avatar_hash=None,
                    role=user_role,
                    confirmed=True)
        db.session.add(user)
        db.session.commit()

        with self.assertRaises(AttributeError) as err:
            user.password()

        self.assertTrue(user.verify_password('old_password'.encode('utf-8')))
        user.password = 'new_password'
        self.assertFalse(user.verify_password('old_password'.encode('utf-8')))
        self.assertTrue(user.verify_password('new_password'.encode('utf-8')))

    def test_generate_confirmation_token(self):
        user_role = Role.query.filter_by(name='User').first()
        user = User(email=forgery_py.internet.email_address(),
                    username=forgery_py.internet.user_name(),
                    password='old_password',
                    avatar_hash=None,
                    role=user_role,
                    confirmed=True)
        db.session.add(user)
        db.session.commit()

        token1 = user.generate_confirmation_token(expiration=3600)
        token2 = user.generate_confirmation_token(expiration=3601)

        self.assertNotEqual(token1, token2)

    def test_user_confirm_token(self):
        User.generate_fake(count=2)
        user1 = User.query.first()
        user2 = User.query.filter(User.id != user1.id).first()

        token1 = user1.generate_confirmation_token(expiration=3600)
        token2 = user2.generate_confirmation_token(expiration=3600)

        self.assertTrue(user1.confirm(token1))
        self.assertFalse(user1.confirm(token2))
        self.assertTrue(user2.confirm(token2))
        self.assertFalse(user2.confirm(token1))
        self.assertFalse(user1.confirm(''))

    def test_user_reset_password(self):
        user_role = Role.query.filter_by(name='User').first()
        user = User(email=forgery_py.internet.email_address(),
                    username=forgery_py.internet.user_name(),
                    password='old_password',
                    avatar_hash=None,
                    role=user_role,
                    confirmed=True)
        db.session.add(user)
        db.session.commit()

        reset_token = user.generate_reset_token()
        confirmation_token = user.generate_confirmation_token()

        valid_result = user.reset_password(token=reset_token, new_password='new_password')
        invalid_result = user.reset_password(token='', new_password='new_password')
        invalid_result2 = user.reset_password(token=confirmation_token, new_password='new_password')

        self.assertTrue(valid_result)
        self.assertFalse(invalid_result)
        self.assertFalse(invalid_result2)

    def test_user_invite(self):
        user_role = Role.query.filter_by(name='User').first()
        User.generate_fake(count=1)
        user1 = User.query.first()
        user2 = User(email=forgery_py.internet.email_address(),
                     role=user_role)
        db.session.add(user2)
        db.session.commit()

        valid_token = user2.generate_invite_token(expiration=3600)
        invalid_token = user2.generate_confirmation_token(expiration=3600)

        valid_invite = user2.accept_invite(token=valid_token, username='username2', new_password='new_password')
        invalid_invite = user2.accept_invite(invalid_token, 'username2', 'new_password')
        invalid_invite2 = user2.accept_invite('', 'username2', 'new_password')

        self.assertTrue(valid_invite)
        self.assertTrue(user2.username, 'username2')
        self.assertTrue(user2.verify_password('new_password'))

        self.assertFalse(invalid_invite)
        self.assertFalse(invalid_invite2)

    def test_user_change_email(self):
        User.generate_fake(count=2)
        user1 = User.query.first()
        user2 = User.query.filter(User.id != user1.id).first()

        old_email_user1 = user1.email
        new_email_user2 = forgery_py.internet.email_address()
        valid_token_user1 = user1.generate_email_change_token(new_email=new_email_user2)
        invalid_token_user1 = user1.generate_confirmation_token()
        blank_new_email_user2 = user2.generate_email_change_token(new_email=None)
        email_already_in_use = user2.generate_email_change_token(new_email=user2.email)

        self.assertTrue(user1.change_email(valid_token_user1))
        self.assertEqual(user1.email, new_email_user2)
        self.assertNotEqual(user1.email, old_email_user1)
        self.assertFalse(user1.change_email(''))
        self.assertFalse(user1.change_email(invalid_token_user1))
        self.assertFalse(user2.change_email(blank_new_email_user2))
        self.assertFalse(user2.change_email(email_already_in_use))

    def test_user_has_role(self):
        admin_role = Role.query.filter_by(name='Administrator').first()
        user_role = Role.query.filter_by(name='User').first()

        user1 = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(),
                     password='old_password',
                     avatar_hash=None,
                     role=user_role,
                     confirmed=True)

        user2 = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(),
                     password='old_password',
                     avatar_hash=None,
                     role=admin_role,
                     confirmed=True)

        db.session.add(user1, user2)
        db.session.commit()

        self.assertTrue(user1.has_role(user_role.name))
        self.assertFalse(user1.has_role(admin_role.name))
        self.assertTrue(user2.has_role(admin_role.name))
        self.assertFalse(user2.has_role(user_role.name))

    def test_user_is_administrator(self):
        admin_role = Role.query.filter_by(name='Administrator').first()
        user_role = Role.query.filter_by(name='User').first()

        user1 = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(),
                     password='old_password',
                     avatar_hash=None,
                     role=user_role,
                     confirmed=True)

        user2 = User(email=forgery_py.internet.email_address(),
                     username=forgery_py.internet.user_name(),
                     password='old_password',
                     avatar_hash=None,
                     role=admin_role,
                     confirmed=True)

        db.session.add(user1, user2)
        db.session.commit()

        self.assertFalse(user1.is_administrator())
        self.assertTrue(user2.is_administrator())

    @patch('PilosusBot.models.datetime')
    def test_user_ping(self, mock_datetime):
        now = datetime.utcnow()
        mock_datetime.utcnow.return_value = now

        user_role = Role.query.filter_by(name='User').first()
        user = User(email=forgery_py.internet.email_address(),
                    username=forgery_py.internet.user_name(),
                    password='old_password',
                    avatar_hash=None,
                    role=user_role,
                    confirmed=True)
        db.session.add(user)
        db.session.commit()

        user.ping()
        self.assertEqual(user.last_seen, now)
        user.ping()
        self.assertEqual(user.last_seen, now)
        mock_datetime.utcnow.assert_called()

    def test_user_gravatar(self):
        user_role = Role.query.filter_by(name='User').first()
        user = User(email=forgery_py.internet.email_address(),
                    username=forgery_py.internet.user_name(),
                    password='old_password',
                    avatar_hash=None,
                    role=user_role,
                    confirmed=True)
        db.session.add(user)
        db.session.commit()

        https_url = 'https://secure.gravatar.com/avatar'
        http_url = 'http://www.gravatar.com/avatar'
        size = 150
        default = 'identicon'
        rating = 'g'
        hash = hashlib.md5(user.email.encode('utf-8')).hexdigest()

        http_gravatar = user.gravatar(size=size, default=default, rating=rating)


        self.assertEqual(http_gravatar,
                         '{url}/{hash}?s={size}&d={default}&r={rating}'.
                         format(url=http_url, hash=hash, size=size, default=default,
                                rating=rating))
        self.assertNotEqual(http_gravatar,
                            '{url}/{hash}?s={size}&d={default}&r={rating}'.
                            format(url=https_url, hash=hash, size=size, default=default,
                                   rating=rating))

        # 'PilosusBot.models.request' cannot be patched like this:
        #  with patch('PilosusBot.models.request.is_secure', new_callable=PropertyMock) as mock_sec:
        #      mock_sec.return_value = True
        #      request.is_secure # returns True now
        #
        # so there's no way to test HTTPS gravatar url other than
        # having fun with HTTP headers probably (?)

    def test_user_auth_token(self):
        user_role = Role.query.filter_by(name='User').first()
        user = User(email=forgery_py.internet.email_address(),
                    username=forgery_py.internet.user_name(),
                    password='old_password',
                    avatar_hash=None,
                    role=user_role,
                    confirmed=True)
        db.session.add(user)
        db.session.commit()

        token = user.generate_auth_token(3600)
        self.assertEqual(user, User.verify_auth_token(token))
        self.assertIsNone(User.verify_auth_token(''))
        self.assertEqual(repr(user), "<User '{}'>".format(user.username))

    def test_anonymous_user(self):
        anon = AnonymousUser()

        self.assertFalse(anon.can(Permission.READ))
        self.assertFalse(anon.can(Permission.MODERATE))
        self.assertFalse(anon.can(Permission.ADMINISTER))

        self.assertFalse(anon.is_administrator())

        self.assertFalse(anon.has_role(Role.query.first().name))
        self.assertFalse(anon.has_role(Role.query.filter_by(name='Administrator').first().name))
        self.assertFalse(anon.has_role('whatever'))

    def test_language(self):
        langs = Language.query.all()
        Language.insert_basic_languages()
        new_langs = Language.query.all()
        random_lang = Language.query.first()

        self.assertEqual(sorted([l.code for l in langs]), sorted([nl.code for nl in new_langs]))
        self.assertEqual(repr(random_lang), "<Language '{}'>".format(random_lang.code))

    def test_sentiment_generate_fake(self):
        User.generate_fake(count=10)
        self.assertEqual(Sentiment.query.all(), [])

        levels = [i/10.0 for i in range(100)]
        Sentiment.generate_fake(count=100, subsequent_scores=False, levels=levels)

        sentiments = Sentiment.query.order_by(Sentiment.id.asc()).all()
        self.assertNotEqual(levels, [s.score for s in sentiments])

        Sentiment.query.filter().delete()
        db.session.commit()

        Sentiment.generate_fake(count=100, subsequent_scores=True, levels=levels)
        sentiments = Sentiment.query.order_by(Sentiment.id.asc()).all()
        self.assertEqual(levels, [s.score for s in sentiments])

    def test_sentiment_json(self):
        User.generate_fake(count=2)
        Sentiment.generate_fake(count=1)
        s = Sentiment.query.first()
        json_data = s.to_json()

        self.assertEqual(json_data['body'], s.body)
        self.assertEqual(json_data['body_html'], s.body_html)
        self.assertEqual(json_data['timestamp'], s.timestamp)

        sentiment_from_json = Sentiment.from_json(json_data)
        self.assertEqual(sentiment_from_json.body, s.body)

        with self.assertRaises(ValidationError) as err:
            Sentiment.from_json({})

        self.assertIn("sentiment does not have a body", str(err.exception))

        self.assertEqual(repr(s), "<Sentiment '{}'>".format(s.body))
