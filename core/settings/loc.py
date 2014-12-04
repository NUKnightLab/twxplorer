"""Local settings and globals."""
import sys
import os
from .base import *

# Import secrets
# Knight Lab keeps API keys and other private data in a private git repository. If you don't have access
# to the Knight Lab secrets repository, you will have to account for establishing certain configuration values
# some other way. You may want to edit this file to establish the values directly, or you can create 
# a parallel directory structure next to where you have this code checked out such that the
# secrets path defined below is a valid directory path. 
# see https://dev.twitter.com/apps to create an app that you can use for Twxplorer development
secrets_path = os.path.normpath(os.path.join(PROJECT_ROOT, '../secrets/twxplorer/loc'))
sys.path.append(secrets_path)
from secrets import * 
# or instead of importing from secrets, uncomment these lines and provide appropriate values
# TWITTER_CONSUMER_KEY = 'consumer key'
# TWITTER_CONSUMER_SECRET = 'consumer secret'

# Flask configuration
# This doesn't need to be in the secrets path, but a flask config module commonly has a SECRET_KEY value
# which should not be made public, so the Knight Lab puts that in the private "secrets" repository as well.
# You can set the environment variable to any working filesystem path to a flask config file.
# see http://flask.pocoo.org/docs/config/ for more.
# Twxplorer has no special requirements for what goes in this file, but Flask will want you to have a SECRET_KEY
# and you may want to set the DEBUG flag to True
os.environ['FLASK_CONFIG_MODULE'] = os.path.join(secrets_path, 'flask_config.py')

# Set static URL
STATIC_URL = '/static/'
