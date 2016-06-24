"""
WSGI config for twxplorer project.
"""
import os
import sys
import site

sys.stdout = sys.stderr

from api import app as application
