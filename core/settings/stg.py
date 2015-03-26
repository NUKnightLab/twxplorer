"""Staging settings and globals."""
import sys
import os
from .base import *

# Import secrets
secrets_path = os.path.normpath(os.path.join(PROJECT_ROOT, '../secrets/twxplorer/stg'))
sys.path.append(secrets_path)
from secrets import *

# Flask configuration
os.environ['FLASK_CONFIG_MODULE'] = os.path.join(secrets_path, 'flask_config.py')

# Set static URL
STATIC_URL = 'http://media.knilab.com/twxplorer/'

# Set databases
DATABASES = {
    'default': {
        'ENGINE': 'mongo',
        'NAME': 'twxplorer',
        'HOST': 'stage-mongo1.knilab.com',
        'PORT': 27017,
    }
}
