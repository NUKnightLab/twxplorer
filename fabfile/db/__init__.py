"""
Package for DB-related code.  

Each type of database should have a separate module in this package named 
according to the db backend module (e.g. 'mysql', 'postgis').  The name of
the backend module is dynamically loaded from a DATABASE attribute in your
project settings file (core.settings.[loc|stg|prd]).  The format of this
attribute follows the Django convention:
    
    DATABASES = {
        'default': {
            'ENGINE': '<package path>.<backend>'
            ...
        }
    }
    
    e.g.,
    
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis'
            ...
        }
    }
        
Each module should define these public methods:

    setup_env(conf)
        Set any necessary variables in env (e.g. filepath, system user)
        
    setup()
        Create the project database and user.
        
    sync()
        Setup the database tables.  If this is a django project, then
        you should use the syncdb command, so just call django_sync in
        this file.
    
    seed(sample='n')
        Seed the database with any necessary data.  If sample=y, then also
        attempt to seed with sample data.
    
    destroy():
        Remove the project database and user.
        
Related data files should be placed in a subdirectory named according to the 
module name:

    <project>/data/db/<module name>
"""

from fabric.api import env
from fabric.context_managers import cd
from fabric.decorators import task, roles, runs_once
import importlib
import sys
import re
from ..utils import require_settings, run_in_ve, notice, warn


@require_settings
def load_module():
    """Load the db module according to (core.settings.[loc|stg|prd])."""
    mod_name = 'core.settings.%(settings)s' % env
    
    try:
        importlib.import_module(mod_name)
        mod = sys.modules[mod_name]
        
        if hasattr(mod, 'DATABASES'):
            conf = mod.DATABASES.get('default', {})
            engine = conf.get('ENGINE', '')
            m = re.match(r'.*\.(?P<db_type>[a-zA-Z0-9]+)$', engine)
            if m:
                env.db_type = m.group('db_type')                
                env.db = importlib.import_module(
                    '.%(db_type)s' % env, 'fabfile.db')
                notice('Loaded db module for %(db_type)s' % env)
                
                env.db.setup_env(conf)
            else:
                env.db_type = 'dummy'               
                env.db = importlib.import_module(
                    '.%(db_type)s' % env, 'fabfile.db')
                warn('Could not determine db type (no ENGINE match')                
        else:
            env.db_type = 'dummy'               
            env.db = importlib.import_module(
                '.%(db_type)s' % env, 'fabfile.db')
            warn('Could not determine db type (no DATABASES match)')                
    except ImportError, e:
        env.db_type = 'dummy'               
        env.db = importlib.import_module(
            '.%(db_type)s' % env, 'fabfile.db')
        warn('Could not import settings module "%s": %s' % (mod_name, e))
 

@require_settings
def django_sync():
    """Sync the database using the Django syncdb command."""
    with cd(env.project_path):
        run_in_ve('python manage.py syncdb ' \
            '--settings=core.settings.%(settings)s' % env)
           
           