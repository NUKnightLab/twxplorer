"""Staging settings and globals."""
import sys
import os
from .base import *

# Import secrets
secrets_path = os.path.normpath(os.path.join(PROJECT_ROOT, '../secrets/twxplorer/stg'))
sys.path.append(secrets_path)
from secrets import *

# Set static URL
STATIC_URL = 'http://media.knilab.com/twxplorer/'

# Database
MONGODB_HOST = 'stg-mongo1.knilab.com'
MONGODB_PORT = 27017
MONGODB_NAME = 'twxplorer'

# Flask configuration
os.environ['FLASK_CONFIG_MODULE'] = os.path.join(secrets_path, 'flask_config.py')