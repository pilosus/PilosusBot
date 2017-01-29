from requests.exceptions import RequestException
import unittest
from unittest.mock import patch, call
from PilosusBot import create_app, db, celery
from PilosusBot.models import Role, Language, User, Sentiment
from PilosusBot.tasks import celery_chain, assess_message_score, \
    select_db_sentiment, send_message_to_chat
from PilosusBot.processing import parse_update
from tests.helpers import HTTP, TelegramUpdates, MockSentiment, MockCappedCollection
from flask import current_app
from indicoio.utils.errors import IndicoError


class TasksTestCase(unittest.TestCase):
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

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.tasks.indicoio', autospec=True)
    def test_assess_message_score(self, mock_indicoio):
        mock_indicoio.sentiment.return_value = 0.87654321

        # make sure update_id has not been used in previous tests,
        # as Redis dict is a persistent in memory dict
        update = TelegramUpdates.TEXT_OK_ID_OK_TEXT
        update['update_id'] -= 10

        parsed_update = parse_update(update)
        result = assess_message_score.delay(parsed_update).get(timeout=5)

        self.assertEqual(result['score'], 0.87654321)
        self.assertEqual(mock_indicoio.config.api_key, current_app.config['INDICO_TOKEN'])
        mock_indicoio.sentiment.assert_called_with(parsed_update['text'], language='latin')

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.tasks.get_rough_sentiment_score')
    @patch('PilosusBot.tasks.indicoio', autospec=True)
    def test_assess_message_score_raise_exception(self, mock_indicoio, mock_rough_score):
        mock_indicoio.sentiment.side_effect = IndicoError('Boom!')
        mock_rough_score.return_value = 0.67890

        # make sure update_id has not been used in previous tests,
        # as Redis dict is a persistent in memory dict
        update = TelegramUpdates.TEXT_OK_ID_OK_TEXT
        update['update_id'] -= 10

        parsed_update = parse_update(update)
        result = assess_message_score.delay(parsed_update).get(timeout=5)

        self.assertNotEqual(result['score'], 0.87654321)
        self.assertEqual(result['score'], 0.67890)
        self.assertEqual(mock_indicoio.config.api_key, current_app.config['INDICO_TOKEN'])
        mock_indicoio.sentiment.assert_called_with(parsed_update['text'], language='latin')

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    def test_select_db_sentiment(self):
        parsed_update = parse_update(TelegramUpdates.TEXT_OK_ID_OK_TEXT)
        parsed_update['score'] = 0.678
        parsed_update['language'] = 'la'
        Sentiment.generate_fake(count=2, subsequent_scores=True, levels=[0.678, 0.789, 0.90, 1.0])

        expected_sentiment = Sentiment.query.filter(Sentiment.score == parsed_update['score']).first()
        not_expected_sentiment = Sentiment.query.filter(Sentiment.score == 0.789).first()

        result = select_db_sentiment.delay(parsed_update).get(timeout=5)

        self.assertEqual(result['text'], expected_sentiment.body_html)
        self.assertNotEqual(result['text'], not_expected_sentiment.body_html)
        self.assertEqual(result['parse_mode'], 'HTML')

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.tasks.random', autospec=True)
    def test_select_db_sentiment_plain_text(self, mock_random):
        mock_sentiment = MockSentiment(body='hello', body_html=None, score=0.678)
        mock_random.choice.return_value = mock_sentiment

        parsed_update = parse_update(TelegramUpdates.TEXT_OK_ID_OK_TEXT)
        parsed_update['score'] = 0.678
        parsed_update['language'] = 'la'
        Sentiment.generate_fake(count=2, subsequent_scores=True, levels=[0.678, 0.789, 0.90, 1.0])
        not_expected_sentiment = Sentiment.query.filter(Sentiment.score == 0.678).first()

        result = select_db_sentiment.delay(parsed_update).get(timeout=5)

        self.assertEqual(result['text'], mock_sentiment.body)
        self.assertNotEqual(result['text'], not_expected_sentiment.body_html)
        mock_random.choice.assert_called()

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('requests.post', side_effect=HTTP.mocked_requests_post)
    def test_send_message_to_chat(self, mock_requests):
        parsed_update = parse_update(TelegramUpdates.TEXT_OK_ID_OK_TEXT)
        parsed_update['parse_mode'] = 'HTML'
        parsed_update['text'] = 'Sentiment'

        result = send_message_to_chat.delay(parsed_update).get(timeout=5)

        # on success the Message sent to the chat is returned
        self.assertEqual(result['text'], parsed_update['text'])
        self.assertEqual(result['parse_mode'], parsed_update['parse_mode'])
        self.assertEqual(result['reply_to_message_id'], parsed_update['reply_to_message_id'])
        self.assertEqual(result['chat_id'], parsed_update['chat_id'])

        mock_requests.assert_called()
        self.assertIn(call(current_app.config['TELEGRAM_URL'] + 'sendMessage',
                      json=parsed_update,
                      timeout=current_app.config['TELEGRAM_REQUEST_TIMEOUT_SEC']),
                      mock_requests.call_args_list)

    @patch('requests.post', side_effect=RequestException('Boom!'))
    def test_send_message_to_chat_raise_exception(self, mock_requests):
        result = send_message_to_chat.delay({}).get(timeout=5)

        self.assertEqual(result['ok'], False)
        self.assertEqual(result['error_code'], 599)
        self.assertEqual(result['description'], 'Boom!')

    @patch('PilosusBot.processing.CappedCollection', new=MockCappedCollection)
    @patch('PilosusBot.tasks.assess_message_score.s')
    @patch('PilosusBot.tasks.select_db_sentiment.s')
    @patch('PilosusBot.tasks.send_message_to_chat.s')
    @patch('PilosusBot.tasks.chain', autospec=True)
    def test_celery_chain(self, mock_chain, mock_send, mock_select, mock_assess):
        mock_chain().apply_async.return_value = 'Hola!'
        mock_assess.return_value = 1
        mock_select.return_value = 2
        mock_send.return_value = 3
        parsed_update = parse_update(TelegramUpdates.TEXT_OK_ID_OK_TEXT)

        result = celery_chain(parsed_update)

        self.assertEqual(result, 'Hola!')
        mock_chain.assert_called_with(1, 2, 3)
        mock_assess.assert_called_with(parsed_update)
        mock_select.assert_called_with()
        mock_send.assert_called_with()
