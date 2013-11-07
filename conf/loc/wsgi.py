"""
WSGI config for twxplorer project.
"""
import os
import sys
import site

site.addsitedir('/usr/local/lib/python2.7/site-packages')
sys.path.append('/home/chris/projects/NUKnightLab/twxplorer')
sys.stdout = sys.stderr

os.environ.setdefault('FLASK_SETTINGS_MODULE', 'core.settings.loc')

from api import app as application
