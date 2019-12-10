import inspect
import json
import os
import logging
import traceback

import slack
import ssl as ssl_lib
import certifi

logger = logging.getLogger()


class SlackBot:
    def __init__(self, config_filepath):
        self.ssl_context = ssl_lib.create_default_context(cafile=certifi.where())
        self.slack_token = os.environ['SLACK_BOT_TOKEN']

        with open(config_filepath, 'r') as f:
            conf = json.loads(f.read())

        self.default_response_username = conf['response_username']
        self.default_response_avatar = conf['response_avatar']
        self.admin_user_slack_id = conf.get('admin_user_slack_id')

        self.function_registry = {
            'help': {
                'function': self._help,
                'help_string': 'Prints help dialogue for a command'
            }
        }
        self.admin_function_registry = {}

    def start(self):
        self.rtm_client = slack.RTMClient(token=self.slack_token)
        self.rtm_client.on(event='message', callback=self._receive_message_and_respond)
        self.rtm_client.start()

    def register_function(self, command_string, function, help_string, admin_only=False):
        assert (len(command_string))
        assert (command_string not in self.function_registry)
        assert (command_string not in self.admin_function_registry)
        assert (callable(function))
        # TODO: explicitly disallow varargs

        registry = self.admin_function_registry if admin_only else self.function_registry
        registry[command_string] = {'function': function, 'help_string': help_string}

    def _registry_for_user(self, user_id):
        return {
            **self.function_registry,
            **self.admin_function_registry
        } if user_id == self.admin_user_slack_id else self.function_registry

    @staticmethod
    def _user_input_agrees_with_function_interface(user_args, function):
        user_arg_count = len(user_args)
        parameters = [x[1] for x in inspect.signature(function).parameters.items()]

        min_args_allowed = len(list(filter(lambda x: x.default is x.empty, parameters)))
        max_args_allowed = len(parameters)

        return min_args_allowed <= user_arg_count <= max_args_allowed

    def _receive_message_and_respond(self, **payload):
        logger.debug('SlackBot received the following payload:\n\033[96m {}\033[00m'.format(payload))
        try:
            # Slack will also forward messages posted by this bot. Discard these.
            if payload['data'].get('subtype', None) == 'bot_message':
                logger.debug('Ignoring message originating from bot')
                return

            text = payload['data']['text']
            web_client = payload['web_client']
            user_id = payload['data']['user']
        except KeyError:
            logger.error('Payload from slack came packaged in an unexpected form. Failed to parse components. '
                         'Payload as follows: {}'.format(payload))
            return

        text = text.split()
        user_command = text[0]
        user_args = text[1:]

        registry = self._registry_for_user(user_id)

        if user_command not in registry:
            self.send_message(web_client, user_id, self._help())
            return

        function = registry.get(user_command)['function']

        # Do basic validation on the interface
        if not self._user_input_agrees_with_function_interface(user_args, function):
            self.send_message(web_client, user_id, 'Input parameters are incorrect')
            self.send_message(web_client, user_id, self._help(user_command))
            return

        # Run function
        try:
            response_text = registry[user_command]['function'](*user_args)
        except Exception as e:
            response_text = 'The following error occurred:\n{}'.format(traceback.format_exc())
        finally:
            self.send_message(web_client, user_id, response_text)

    def send_message(self, web_client, user_id, message):
        channel = web_client.im_open(user=user_id)["channel"]["id"]

        message = self._package_message_for_slack(channel, message)
        logger.debug('Sending the following response:\n\033[92m {}\033[00m'.format(json.dumps(message, indent=2)))
        web_client.chat_postMessage(**message)

    def _package_message_for_slack(self, channel, message='', bot_username=None, bot_avatar=None):
        bot_username = bot_username or self.default_response_username
        bot_avatar = bot_avatar or self.default_response_avatar
        message_dict = {
            'channel': channel,
            'username': bot_username,
            'icon_emoji': bot_avatar,
            'text': 'Message received from {}'.format(bot_username),
            'blocks': [{
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': (message)
                }
            }]
        }
        return message_dict

    def _help(self, command_name=None):
        registry = {**self.function_registry, **self.admin_function_registry}
        if not command_name or command_name not in registry:
            message = 'The following are the commands recognized by this bot. For more information on ' \
            'any commands, type "help <command>"'
            normal_commands = '*Normal Commands*\n' + (
                '\n- {}' * len(self.function_registry)).format(*sorted(self.function_registry))

            admin_commands = '*Admin Commands*\n' + (
                '\n- {}' * len(self.admin_function_registry)).format(*sorted(self.admin_function_registry))

            message = '{}\n{}\n\n{}'.format(message, normal_commands, admin_commands)
        else:
            message = '{}: {}'.format(command_name, registry[command_name]['help_string'])
        return message
