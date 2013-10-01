"""Common settings and globals."""
import os
from os.path import abspath, basename, dirname, join, normpath

CORE_ROOT = dirname(dirname(abspath(__file__)))
PROJECT_ROOT = dirname(CORE_ROOT)


# Maximum number of tweets to retrieve per search session
TWITTER_SEARCH_LIMIT = 500


