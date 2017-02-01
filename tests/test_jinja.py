from random import choice
import unittest
from flask import current_app
from PilosusBot import create_app, db
from PilosusBot.jinja_filters import permissions2str, pluralize, score_level, \
    score_desc, code2name
from PilosusBot.models import Role, Language, Permission
from PilosusBot.utils import lang_code_to_lang_name


class JinjaTestCase(unittest.TestCase):
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

    def test_permissions2str(self):
        self.assertEqual(permissions2str(0), '--------')  # 00
        self.assertEqual(permissions2str(1), '-------[READ]')  # 01
        self.assertEqual(permissions2str(2), '------[MODERATE]-') # 10
        self.assertEqual(permissions2str(3), '------[MODERATE][READ]') # 11
        self.assertEqual(permissions2str(4), '-----[ADMINISTER]--') # 100
        self.assertEqual(permissions2str(5), '-----[ADMINISTER]-[READ]')  # 101
        self.assertEqual(permissions2str(8), '----[NA]---')  # 1000
        self.assertEqual(permissions2str(9), '----[NA]--[READ]')  # 1001

    def test_pluralize(self):
        self.assertEqual(pluralize(counter=10, singular_postfix='', plural_postfix='s'), 's')
        self.assertEqual(pluralize(counter=1, singular_postfix='', plural_postfix='s'), '')
        self.assertEqual(pluralize(counter=10, singular_postfix='y', plural_postfix='ies'), 'ies')
        self.assertEqual(pluralize(counter=1, singular_postfix='y', plural_postfix='ies'), 'y')
        self.assertEqual(pluralize(counter=0, singular_postfix='y', plural_postfix='ies'), 'ies')

    def test_score_level(self):
        score = choice(list(current_app.config['APP_SCORE_LEVELS'].keys()))
        self.assertEqual(score_level(score), current_app.config['APP_SCORE_LEVELS'][score].css)

    def test_score_desc(self):
        score = choice(list(current_app.config['APP_SCORE_LEVELS'].keys()))
        self.assertEqual(score_desc(score), current_app.config['APP_SCORE_LEVELS'][score].desc)

    def test_code2name(self):
        self.assertEqual(code2name('en'), lang_code_to_lang_name('en'))
        self.assertEqual(code2name('ru'), lang_code_to_lang_name('ru'))
