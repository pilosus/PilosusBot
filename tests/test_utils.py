import forgery_py
import re
import unittest
from PilosusBot import create_app, db
from PilosusBot.models import Role, Language, Sentiment, User
from PilosusBot.utils import download_polyglot_dicts, generate_password, to_bool, \
    map_value_from_range_to_new_range, detect_language_code, \
    is_valid_lang_code, is_valid_lang_name, lang_code_to_lang_name, \
    score_to_closest_level, get_rough_sentiment_score
from flask import current_app


class UtilsTestCase(unittest.TestCase):
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
        User.generate_fake(count=20)
        Sentiment.generate_fake(count=50)

        # Werkzeug Client to make requests
        self.client = self.app.test_client(use_cookies=True)

    @classmethod
    def setUpClass(cls):
        #Run this class method only once per testsuite.
        super(UtilsTestCase, cls).setUpClass()

        # download polyglot dictionaries
        # UtilsTestCase.polyglot_dicts_installed is available through the class
        cls.polyglot_dicts_installed = download_polyglot_dicts()

    def tearDown(self):
        """Method called after each unit-test"""
        # remove current db session
        db.session.remove()

        # remove db itself
        db.drop_all()

        # remove app context
        self.app_context.pop()

    def create_app(self):
        """Mandatory method for Flask-Testing returning app instance"""
        return create_app('testing')

    def test_context(self):
        self.assertTrue(current_app.config['TESTING'])

    def test_langs(self):
        self.assertIn('la', current_app.config['APP_LANGUAGES'])

    def test_generate_password(self):
        password1 = generate_password()
        self.assertEqual(len(password1), 10)
        self.assertFalse(re.match(r'\s+', password1))
        self.assertFalse(re.search(r"[-!$%^&*()_+|~=`{}\[\]:\";\'<>?,.]", password1))
        self.assertTrue(re.match(r'[a-z]|[A-Z]|[0-9]', password1))

        password2 = generate_password(20)
        self.assertEqual(len(password2), 20)

    def test_to_bool(self):
        self.assertTrue(to_bool('True'))
        self.assertTrue(to_bool('true'))
        self.assertTrue(to_bool('TRUE'))
        self.assertTrue(to_bool('t'))
        self.assertTrue(to_bool('T'))
        self.assertTrue(to_bool('yes'))
        self.assertTrue(to_bool('YeS'))
        self.assertTrue(to_bool('Y'))
        self.assertFalse(to_bool('I do not know'))
        self.assertFalse(to_bool(''))

    def test_map_ranges(self):
        self.assertEqual(map_value_from_range_to_new_range(0, slice(-1.0, 1.0), slice(0.0, 1.0)), 0.5)
        self.assertEqual(map_value_from_range_to_new_range(0.5, slice(0.0, 1.0), slice(-1.0, 1.0)), 0)
        self.assertEqual(map_value_from_range_to_new_range(0.33, slice(-1.0, 1.0), slice(0.0, 1.0)), 0.665)
        self.assertEqual(map_value_from_range_to_new_range(0.123, slice(0.0, 1.0), slice(-1.0, 1.0)), -0.754)
        self.assertEqual(map_value_from_range_to_new_range(0, slice(0.0, 1.0), slice(-1.0, 1.0)), -1.0)

    def test_detect_language(self):
        eng = detect_language_code('This is pure English text!')
        rus = detect_language_code('Это текст на русском языке!')
        ger = detect_language_code('Na ja, das ist deutscher Text, glaube ich!')
        lat = detect_language_code(forgery_py.lorem_ipsum.text())
        undetected = detect_language_code('A')

        self.assertEqual(eng, 'en')
        self.assertEqual(rus, 'ru')
        self.assertEqual(ger, 'de')
        self.assertEqual(lat, 'la')
        self.assertEqual(undetected, current_app.config['APP_LANG_FALLBACK'])

    def test_is_valid_lang_code(self):
        self.assertTrue(is_valid_lang_code('en'))
        self.assertTrue(is_valid_lang_code('ru'))
        self.assertTrue(is_valid_lang_code('de'))
        self.assertFalse(is_valid_lang_code('hello'))
        self.assertFalse(is_valid_lang_code('un'))

    def test_is_valid_lang_name(self):
        self.assertTrue(is_valid_lang_name('English'))
        self.assertTrue(is_valid_lang_name('Russian'))
        self.assertTrue(is_valid_lang_name('German'))
        self.assertTrue(is_valid_lang_name('Latin'))
        self.assertFalse(is_valid_lang_name('Non existent language'))

    def test_lang_code_to_lang_name(self):
        self.assertEqual(lang_code_to_lang_name('en'), 'English')
        self.assertEqual(lang_code_to_lang_name('ru'), 'Russian')
        self.assertEqual(lang_code_to_lang_name('de'), 'German')
        self.assertEqual(lang_code_to_lang_name('la'), 'Latin')

    def test_score_to_closest_level(self):
        """Assume each level has at least one row in the db
        """
        lang = 'la'
        self.assertEqual(score_to_closest_level(lang, 0.63, [0.0, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0]), 0.75)
        self.assertEqual(score_to_closest_level(lang, 0.75, [0.0, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0]), 0.75)
        self.assertEqual(score_to_closest_level(lang, 1.0, [0.0, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0]), 1.0)
        self.assertEqual(score_to_closest_level(lang, -1.0, [0.0, 0.25, 0.375, 0.5, 0.625, 0.75, 1.0]), 0.0)
        self.assertEqual(score_to_closest_level(lang, 2.5, [0.0, 0.25, 0.375, 0.5, 0.625]), 0.625,
                         'Go backward if no sentiments found for the given score or higher')

    def test_get_rough_sentiment_score(self):
        self.assertAlmostEqual(get_rough_sentiment_score('This is a neutral sentence'), 0.5, places=3)
        self.assertLess(get_rough_sentiment_score('Testing third-party libraries is completely stupid!'), 0.5)
        self.assertGreater(get_rough_sentiment_score('Nontheless unittesting is super important!'), 0.5)
