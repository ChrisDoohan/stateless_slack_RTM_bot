from setuptools import setup

setup(name='stateless_slack_RTM_bot',
      version='0.2',
      description='Bot that abstracts and simplifies the Slack API.',
      url='https://github.com/ChrisDoohan/stateless_slack_RTM_bot',
      author='Chris Doohan',
      author_email='ChrisDoohan@gmail.com',
      install_requires=['certifi', 'slackclient'],
      python_requires='~=3.0',
      license='MIT',
      packages=['stateless_slack_RTM_bot'],
      zip_safe=False)
