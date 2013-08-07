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


def _psql(cmd, host='', user='', prefix=''):
    c = ' psql -h '+(host or env.host)+' -U '+(user or env.db_root_user)+ ' '
    return env.doit((prefix+c+cmd) % env)
    
    
def _psql_pipe_data(f, host='', user=''):
    """
    Pipe data from a file to the db.  Types of files:
    
    1.  Files created using pg_dump (full SQL statements).
    
    These are loaded by piping their contents directly to psql.
    
        any_name_is_fine.sql[.gz|.gzip|.zip|.Z]
    
    2.  Files created from psql using -c "SELECT..." (data only).
    
    These are loaded by piping their contains to to psql and having psql
    copy the data from STDIN using the COPY statement.  The table_name
    component of the filename MUST match the name of the table in the db.
    
        table_name.copy.[.gz|.gzip|.zip|.Z]
        
    Files that do not follow these naming conventions are skipped.
    """    
    (other, ext) = os.path.splitext(f)
    ext = ext.lower()
    if ext.lower() in ('.gz', '.gzip', '.zip', '.Z'):
        cmd = 'gunzip -c'
        (other, ext) = os.path.splitext(other) 
        ext = ext.lower()  
    else:
        cmd = 'cat'
                 
    if ext == '.copy':
        (other, table_name) = os.path.split(other)
        _psql('-c "COPY %s FROM STDIN" buzz' % table_name, 
            host=host, user=user, prefix='%s %s |' % (cmd, f))
    elif ext == '.sql':
        _psql('buzz', 
            host=host, user=user, prefix='%s %s |' % (cmd, f))
    else:
        warn('Skipping file, unknown format (%s)' % f)  


def setup_env(conf):
    """Setup the working environment as appropriate for loc, stg, prd."""    
    if env.settings == 'loc':
        env.db_root_user = env.local_user
        env.postgis_root = '/usr/local/share/postgis'
    else:
        env.db_root_user = 'postgres'
        env.postgis_root = '/usr/share/postgresql/9.1/contrib/postgis-1.5'
    
    env.db_name = conf['NAME']
    env.db_user = conf['USER']
    env.db_password = conf['PASSWORD'] 
    env.db_host = conf['HOST']
    
 
@roles('pgis')    
def setup():
    """Create the project database and user."""
    created_db = False
    
    # Create the template database
    with hide('warnings'), settings(warn_only=True):
        result = _psql('-l | grep "template_postgis "')
    if result.failed:
        notice('Creating template database template_postgis')
        env.doit('createdb -h %(host)s -U %(db_root_user)s template_postgis' % env)
        _psql('-f %(postgis_root)s/postgis.sql template_postgis')
        _psql('-f %(postgis_root)s/spatial_ref_sys.sql template_postgis')
    else:
        notice('Template database template_postgis already exists')
       
    # Create the project database
    with hide('warnings'), settings(warn_only=True):
        result = _psql('-l | grep "%(db_name)s "')
    if result.failed:
        notice('Creating database %(db_name)s from template' % env)
        env.doit('createdb -h %(host)s -U %(db_root_user)s -T template_postgis %(db_name)s' % env)
        created_db = True
    else:
        notice('Database %(db_name)s already exists' % env)
        
    # Create the database user
    with hide('warnings'), settings(warn_only=True):
        result = _psql('-c "SELECT rolname FROM pg_roles" %(db_name)s | grep "%(db_user)s"')
    if result.failed:
        notice('Creating database user %(db_user)s' % env)
        _psql('-c "' \
            'CREATE USER %(db_user)s;' \
            'GRANT ALL PRIVILEGES ON DATABASE %(db_name)s to %(db_user)s;' \
            'ALTER TABLE geometry_columns OWNER TO %(db_user)s;' \
            'ALTER TABLE spatial_ref_sys OWNER TO %(db_user)s;' \
            '" %(db_name)s')
    elif created_db:
        _psql('-c "' \
            'ALTER TABLE geometry_columns OWNER TO %(db_user)s;' \
            'ALTER TABLE spatial_ref_sys OWNER TO %(db_user)s;' \
            '" %(db_name)s')
    else:
        notice('Database user %(db_user)s already exists' % env)


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
    app or work server, because we need to pip data to psql.
    """
    db_hosts = [h.split('@')[-1] for h in env.roledefs.get('pgis', [])]
    
    d = path(env.data_path, 'db', 'postgis', 'seed')   
    if exists(d):
        files = ls(d)     
        for h in db_hosts:
            for f in files:
                _psql_pipe_data(f, host=h, user=env.db_user)                    
                        
    d = path(env.data_path, 'db', 'postgis', 'sample')
    if do(sample) and exists(d):
        files = ls(d)        
        for h in db_hosts:
            for f in files:
                _psql_pipe_data(f, host=h, user=env.db_user)

    
@roles('pgis')
def destroy():
    """Remove the database and user."""   
    warn('This will delete the %(db_name)s db and %(db_user)s user ' \
        'for %(settings)s on %(host)s.')        
    msg = 'Destroy %(db_name)s database and %(db_user)s user for ' \
        '%(settings)s deployment? (y/n) '
    if not confirm(msg % env):
        abort('Cancelling')
        
    with hide('warnings'):
        with settings(warn_only=True):
            result = _psql('-l | grep "%(db_name)s "')
        if result.failed:
            notice('Database %(db_name)s does not exist' % env)
            return
                
        # Drop database user
        with settings(warn_only=True):
            result = _psql(
                '-c "SELECT rolname FROM pg_roles" %(db_name)s' \
                ' | grep "%(db_user)s"')
        if result.failed:
            notice('Database user %(db_user)s does not exist' % env)
        else:
            notice('Dropping user %(db_user)s' % env)
            _psql('-c "' \
                'DROP OWNED BY %(db_user)s;' \
                'DROP USER %(db_user)s;' \
                '" %(db_name)s')
        
        # Drop project database
        with settings(warn_only=True):
            result = _psql('-l | grep "%(db_name)s "')
        if result.failed:
            notice('Database %(db_name)s does not exist' % env)
        else:
            notice('Dropping database %(db_name)s' % env)
            env.doit('dropdb -h %(host)s -U %(db_root_user)s %(db_name)s' % env)
    
    

