import os
import unittest
from mock import patch

from stateless_slack_RTM_bot import SlackBot


def add_two(addend1, addend2):
    return str(int(one) + int(two) + int(three))


def function_with_default_param(param='default'):
    return param


def admin_only(x):
    return x


class TestSlackBot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        conf_filepath = os.path.dirname(__file__)
        conf_filepath = os.path.join(conf_filepath, 'bot_config.json')
        os.environ['SLACK_BOT_TOKEN'] = 'abcdefg'
        cls.bot = SlackBot(conf_filepath)
        cls.bot.register_function('add_two', add_two, 'adds two numbers')
        cls.bot.register_function('function_with_default_param', function_with_default_param,
                                  'returns what is passed in, or the word "default"')
        cls.bot.register_function('admin_only', admin_only, 'repeats parameter', admin_only=True)

    def _get_slacklike_incoming_dict(text, user='unknown'):
        return {'web_client': 'fake web client object', 'data': {'text': text, 'user': user}}

    def test_init_sets_internal_state(self):
        self.assertEqual(self.bot.slack_token, 'abcdefg')
        self.assertEqual(self.bot.default_response_username, 'stateless_slack_RTM_bot')
        self.assertEqual(self.bot.default_response_avatar, ':robot_face:')
        self.assertEqual(self.bot.admin_user_slack_id, 'ABCDEF')

    def test_help_method_returns_registered_function_info(self):
        response = self.bot._help()
        self.assertIn('add_two', response)
        self.assertIn('function_with_default_param', response)
        self.assertIn('admin_only', response)

        # Get command details
        response = self.bot._help('add_two')
        self.assertIn('adds two numbers', response)

        # Admin functions should be retrievable
        response = self.bot._help('admin_only')
        self.assertIn('repeats parameter', response)

    def test_user_args_are_validated_against_registered_function_interface(self):
        validated = self.bot._user_input_agrees_with_function_interface(['five', 'six'], add_two)
        self.assertTrue(validated)

        validated = self.bot._user_input_agrees_with_function_interface(['five', 'six', 'seven'], add_two)
        self.assertFalse(validated)

        validated = self.bot._user_input_agrees_with_function_interface(['five'], add_two)
        self.assertFalse(validated)

        # Make sure this works with default parameters
        validated = self.bot._user_input_agrees_with_function_interface([], function_with_default_param)
        self.assertTrue(validated)

        validated = self.bot._user_input_agrees_with_function_interface(['single param'], function_with_default_param)
        self.assertTrue(validated)

        validated = self.bot._user_input_agrees_with_function_interface(['one', 'two'], function_with_default_param)
        self.assertFalse(validated)