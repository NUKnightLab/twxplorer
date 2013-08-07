"""Production settings and globals."""
import sys
import os
from .base import *

# Import secrets
sys.path.append(
    os.path.normpath(os.path.join(PROJECT_ROOT, '../secrets/twxplorer/stg'))
)
from secrets import *

# Set static URL
STATIC_URL = 'http://media.knightlab.us/twxplorer/'