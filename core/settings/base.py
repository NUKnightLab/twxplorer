"""Common settings and globals."""
import os
from os.path import abspath, dirname

CORE_ROOT = dirname(dirname(abspath(__file__)))
PROJECT_ROOT = dirname(CORE_ROOT)

DATABASES = {
    'default': {
        'ENGINE': 'mongo',
        'NAME': 'twxplorer',
        'HOST': '127.0.0.1',
        'PORT': 27017,
    }
}

# Maximum number of tweets to retrieve per search session
TWITTER_SEARCH_LIMIT = 500


