"""Common settings and globals."""
from os.path import abspath, dirname, join
from os import environ as env

# Maximum number of tweets to retrieve per search session
TWITTER_SEARCH_LIMIT = 500

SECRET_KEY = env['FLASK_SECRET_KEY']
STATIC_URL = 'http://media.knightlab.com/twxplorer/'

DATABASES = {
    'default': {
        'ENGINE': env['DB_ENGINE__DEFAULT'],
        'NAME': env['DB_NAME__DEFAULT'],
        'HOST': env['DB_HOST__DEFAULT'],
        'PORT': env['DB_PORT__DEFAULT']
    }
}

TWITTER_CONSUMER_KEY = env['TWITTER_CONSUMER_KEY']
TWITTER_CONSUMER_SECRET = env['TWITTER_CONSUMER_KEY']
BITLY_USERNAME = env['BITLY_USERNAME']
BITLY_APIKEY = env['BITLY_APIKEY']
BITLY_DOMAIN = env['BITLY_DOMAIN']
