"""
postgres/postgis 

seed data:
    <project>/data/db/postgis/seed/
    
sample data:
    <project>/data/db/postgis/sample/
    
See _psql_pipe_data() for acceptable formats and file-naming conventions.
"""
from fabric.api import env, settings, hide
from fabric.contrib.files import exists
from fabric.decorators import roles, runs_once
import os
from ..utils import notice, warn, abort, path, ls, do, confirm
from . import django_sync


def _mysql(cmd, prefix=''):
    c = ' mysql -h %(db_host)s -u %(db_user)s '
    if env.db_password:
        c += '-p"%(db_password)s" '
    return env.doit((prefix+c+cmd) % env)
    
    
def _mysql_pipe_data(f, host='', user=''):
    """
    Pipe data from a file to the db.  Valid types of files:
    
    1.  Files created using mysqldump (full SQL statements)

    These are loaded by piping their contents directly to mysql.
    
        any_name_is_fine.sql[.gz|.gzip|.zip|.Z]   

    Files that do not follow these naming conventions are skipped.
    """    
    ## TO DO ##
    warn('db.mysql._mysql_pipe_data() not implemented')


def setup_env(conf):
    """Setup the working environment as appropriate for loc, stg, prd."""  
    #
    # TO DO: SET A ROOT USER
    # If we want to be able to create/delete the database
    # Not sure how to do that with RDS, since the root user is different
    # on every RDS instance.
    #
    env.db_name = conf['NAME']
    env.db_user = conf['USER']
    env.db_password = conf['PASSWORD']
    env.db_host = conf['HOST']
    
 
@roles('app')
@runs_once    
def setup():
    """
    Create the project database and user.
           
    For now, just check to make sure they exist, because the creation of either
    requires a root user/password, and I'm not sure how that will work.
    """
    with hide('warnings'), settings(warn_only=True):
        result = _mysql('-e "SHOW DATABASES;" | grep "^%(db_name)s$"')
    if result.failed:
        abort('Database "%(db_name)s" does not exist on host %(db_host)s' % env)
    else:
        notice('Database "%(db_name)s" exists on host %(db_host)s' % env)
        
    # Create the database user
    # ACTUALLY JUST MAKE SURE IT EXISTS
    # TO-DO... need to do this with the root user
    #with hide('warnings'), settings(warn_only=True):
    #    result = _mysql('-e "SELECT User FROM mysql.user;" | grep "^%(db_user)s$"')
    #if result.failed:
    #    abort('Database user "%(db_user)s" does not exist on host %(db_host)s' % env)
    #else:
    #    notice('Database user "%(db_user)s" exists on host %(db_host)s' % env)


@roles('app', 'work')
@runs_once
def sync():
    django_sync()


@roles('app', 'work')
@runs_once
def seed(sample='n'):
    """
    Seed the database.  Set sample=y to load sample data (default = n).
    This needs to be run once per database, but has to be run from the
    app or work server, because we need to pipe data to mysql.
    """
    warn('db.mysql.seed() not implemented')
    

@roles('app', 'work')
@runs_once
def destroy():
    """Remove the database and user."""   
    warn('db.mysql.destroy() not implemented')
    
    

