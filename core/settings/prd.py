"""Production settings and globals."""
import sys
import os
from .base import *

# Import secrets
sys.path.append(
    os.path.normpath(os.path.join(PROJECT_ROOT, '../secrets/twxplorer/prd'))
)
from secrets import *

# Set static URL
STATIC_URL = 'http://media.knightlab.com/twxplorer/'

# Database
MONGODB_HOST = 'prd-mongo1.knilab.com'
MONGODB_PORT = 27017
MONGODB_NAME = 'twxplorer'

# Flask configuration
os.environ['FLASK_CONFIG_MODULE'] = os.path.join(secrets_path, 'flask_config.py')