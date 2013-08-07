"""
Deployment management for KnightLab web application projects.

Add the pem file to your ssh agent:
    ssh-add <pemfile>

Set your AWS credentials in environment variables:
    AWS_ACCESS_KEY_ID
    AWS_SECRET_ACCESS_KEY

or in config files:
    /etc/boto.cfg, or
    ~/.boto

Note: Do not quote key strings in the config files.

You can find this information: 
- Login to AWS Management Console
- From 'Knight Lab' menu in upper-right corner, select 'Security Credentials'
- Access Key ID and Secret Access key are visible under 'Access Credentials'

For AWS (boto) config details, see:
    http://boto.readthedocs.org/en/latest/boto_config_tut.html#credentials

Set a WORKON_HOME environment variable.  This is the root directory for all
of your local virtual environments.  If you use virtualenvwrapper, this is 
already set for you. If not, then set it manually.

USAGE:

fab <env> <operation>

i.e.: fab [loc|stg|prd] [setup|deploy]

This will execute the operation for all servers for the given environment
(loc, stg, or prd).  For loc, everything takes place on localhost.
"""
import fnmatch
import os
import sys
import re
import tempfile
import importlib
import boto
from random import choice
from boto import ec2
from fabric.api import env, put, require, run, local, sudo, settings, hide 
from fabric.context_managers import cd, prefix
from fabric.contrib.files import exists
from fabric.tasks import execute
from fabric.decorators import roles, runs_once, task
from .utils import require_settings, run_in_ve
from .utils import notice, warn, abort, path, do, confirm, check_path
import db

# PROJECT-SPECIFIC SETTINGS
PROJECT_NAME = 'twxplorer'

# COMMON SETTINGS
PYTHON = 'python2.7'
REPO_URL = 'git@github.com:NUKnightLab/%s.git' % PROJECT_NAME

# REMOTE DEPLOYMENT SETTINGS
APACHE_CONF_NAME = 'apache' # inside conf/stg, conf/prd
APACHE_MAINTENANCE_CONF_NAME = 'apache.maintenance'
APP_USER = 'apps'
CONF_DIRNAME = 'conf' # should contain stg & prd directories
ENV_DIRNAME = 'env' # virtualenvs go here
LOG_DIRNAME = 'log'
SITES_DIRNAME = 'sites'
SSH_DIRNAME = '.ssh'
STATIC_DIRNAME = 'static'
USERS_HOME = '/home'
VIRTUALENV_SYSTEM_SITE_PACKAGES = False


AWS_CREDENTIALS_ERR_MSG = """
    Unable to connect to AWS. Check your credentials. boto attempts to
    find AWS credentials in environment variables AWS_ACCESS_KEY_ID
    and AWS_SECRET_ACCESS_KEY, or in config files: /etc/boto.cfg, or
    ~/.boto. Do not quote key strings in config files. For details, see:
    http://boto.readthedocs.org/en/latest/boto_config_tut.html#credentials
"""


_ec2_con = None
_s3_con = None


env.app_user = APP_USER
env.project_name = PROJECT_NAME
env.python = PYTHON
env.repo_url = REPO_URL
env.roledefs = {'app':[], 'work':[], 'pgis':[], 'mongo':[]}
    
    
def _get_ec2_con():
    """Get an EC2 connection."""
    global _ec2_con
    if _ec2_con is None:
        try:
            _ec2_con = boto.connect_ec2()
        except boto.exception.NoAuthHandlerFound:
            print AWS_CREDENTIALS_ERR_MSG
            sys.exit(0)
    return _ec2_con


def _get_s3_con():
    """Get an S3 connection."""
    global _s3_con
    if _s3_con is None:
        try:
            _s3_con = boto.connect_s3()
        except boto.exception.NoAuthHandlerFound:
            print AWS_CREDENTIALS_ERR_MSG
            sys.exit(0)
    return _s3_con
        

def _get_ec2_reservations():
    try:
        return _get_ec2_con().get_all_instances()
    except boto.exception.EC2ResponseError, e:
        abort('Received error from AWS. Are your credentials correct?' \
            'Note: do not quote keys in boto config files.' \
            '\nError from Amazon was:\n'+str(e))
 

def _lookup_ec2_instances():
    """Load the EC2 instances by role definition into env.roledefs"""
    regex = re.compile(r'^%s-(?P<role>[a-zA-Z]+)[0-9]+$' % env.settings)
    for r in _get_ec2_reservations():
        for i in r.instances:
            m = regex.match(i.tags.get('Name', ''))
            if m:
                env.roledefs[m.group('role')].append(
                    '%s@%s' % (env.app_user, i.public_dns_name))

        
def _copy_from_s3(bucket_name, resource, dest_path):
    """Copy a resource from S3 to a remote file."""
    bucket = _get_s3_con().get_bucket(bucket_name)
    key = bucket.lookup(resource)
    f = tempfile.NamedTemporaryFile(delete=False)
    key.get_file(f)
    f.close()
    put(f.name, dest_path)
    os.unlink(f.name)


@require_settings(allow=['stg','prd'])
def _setup_ssh():
    """Set up SSH."""
    with cd(env.ssh_path):
        if not exists('known_hosts'):
            _copy_from_s3('knightlab.ops', 'deploy/ssh/known_hosts',
                os.path.join(env.ssh_path, 'known_hosts'))
        if not exists('config'):
            _copy_from_s3('knightlab.ops', 'deploy/ssh/config',
                os.path.join(env.ssh_path, 'config'))
        if not exists('github.key'):
            # TODO: make github.key easily replaceable
            _copy_from_s3('knightlab.ops', 'deploy/ssh/github.key',
                os.path.join(env.ssh_path, 'github.key'))
            with cd(env.ssh_path):
                run('chmod 0600 github.key')
  
     
@require_settings(allow=['stg','prd'])
def _setup_directories():
    run('mkdir -p %(sites_path)s' % env)
    run('mkdir -p %(log_path)s' %env)
    run('mkdir -p %(ve_path)s' % env)


@require_settings(allow=['stg','prd'])
def _setup_virtualenv():
    """Create a virtualenvironment."""
    if VIRTUALENV_SYSTEM_SITE_PACKAGES:
        run('virtualenv -p %(python)s --system-site-packages %(ve_path)s' % env)
    else:
        run('virtualenv -p %(python)s %(ve_path)s' % env)


@require_settings(allow=['stg','prd'])
def _clone_repo():
    """Clone the git repository."""
    run('git clone %(repo_url)s %(project_path)s' % env)

    
@roles('app','work')
@require_settings(allow=['stg','prd'])
def _install_requirements():
    with cd(env.project_path):
        if exists('requirements.txt'):
            run_in_ve('pip install -r requirements.txt')


def _symlink(existing, link):
    """Removes link if it exists and creates the specified link."""
    if exists(link):
        run('rm %s' % link)
    run('ln -s %s %s' % (existing, link))

        
@roles('app')
@require_settings(allow=['stg','prd'])
def _link_apache_conf(maint=False):
    if maint:
        link_file = APACHE_MAINTENANCE_CONF_NAME
    else:
        link_file = APACHE_CONF_NAME
    apache_conf = path(env.conf_path, env.settings, link_file)
    if exists(apache_conf):
        run('mkdir -p %(apache_path)s' % env)
        link_path = path(env.apache_path, env.project_name)
        _symlink(apache_conf, link_path)


def _setup_env(env_type):
    """Setup the working environment as appropriate for loc, stg, prd."""
    check_path()

    env.settings = env_type
    
    if env.settings == 'loc':
        env.doit = local    # run/local
        
        # base paths
        env.home_path = path('/Users', env.local_user)
        env.env_path = os.getenv('WORKON_HOME') or \
            _abort("You must set the WORKON_HOME environment variable to the" \
                " root directory for your virtual environments.")       
        env.project_path = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        # unused: env.sites_path = os.path.dirname(env.project_path)
            
        # roledefs    
        env.roledefs = {
            'app': ['localhost'],
            'work': [],
            'pgis': ['localhost'],
            'mongo': []
        }
    else:
        env.doit = run      # run/local

        # base paths
        env.home_path = path(USERS_HOME, APP_USER)
        env.env_path = path(env.home_path, ENV_DIRNAME)
        env.sites_path = path(env.home_path, SITES_DIRNAME)
        env.project_path = path(env.sites_path, env.project_name)
             
        # roledefs  
        env.roledefs = {
            'app':[], 
            'work':[], 
            'pgis':[], 
            'mongo':[]
        }

        if not env.hosts:
            _lookup_ec2_instances()
    
    env.ssh_path = path(env.home_path, SSH_DIRNAME)
    env.log_path = path(env.home_path, LOG_DIRNAME, PROJECT_NAME)
    env.apache_path = path(env.home_path, 'apache')   
    env.ve_path = path(env.env_path, env.project_name)
    env.activate_path = path(env.ve_path, 'bin', 'activate') 
    env.conf_path = path(env.project_path, CONF_DIRNAME)
    env.data_path = path(env.project_path, 'data')

    # Load db module into env.db
    db.load_module()
    

def _random_key(length=50,
        chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'):
    return ''.join([choice(chars) for i in range(length)])


def _run_in_ve_local(command):
    """
    Execute the command inside the local virtialenv.
    This is some hacky stuff that is only used in deploystatic.
    """
    cur_settings = env.settings
    loc()
    run_in_ve(command)
    globals()[cur_settings]()  

   
#
# tasks
#


@task
def prd():
    """Work on production environment."""
    _setup_env('prd')
    os.environ['AWS_STORAGE_BUCKET_NAME'] = 'media.knightlab.com'
    
@task
def stg():
    """Work on staging environment."""
    _setup_env('stg')
    os.environ['AWS_STORAGE_BUCKET_NAME'] = 'media.knilab.com'  
           
@task
def loc():
    """Work on local environment."""
    _setup_env('loc')    

      
@task      
@roles('app','work')
@require_settings                    
def setup_project(django='n'):
    """Setup new application deployment.  Run only once per project."""
    _setup_ssh()
    _setup_directories()
    _clone_repo()
    _setup_virtualenv()
    _install_requirements()
   

@task
@require_settings
def setup_db(sample='n'):
    """Setup new database and user."""
    execute(env.db.setup)
    execute(env.db.seed, sample=sample)      
    
    
@task
@require_settings                    
def setup(sample='n'):
    """Setup new application deployment.  Run only once per project."""    
    execute(setup_project, django='n')
    execute(env.db.setup)
    execute(env.db.seed, sample=sample)      
    execute(_link_apache_conf)
    

@task
@roles('app', 'work')    
@require_settings                    
def checkout():
    """Pull the latest code on remote servers."""
    env.doit('cd %(project_path)s; git pull' % env)


@task
@roles('app')    
@require_settings(allow=['stg','prd'])                    
def a2start():
    """Start apache.  Uses init.d instead of apachectl for fabric."""
    env.doit('sudo /etc/init.d/apache2 start')

@task
@roles('app')    
@require_settings(allow=['stg','prd'])                    
def a2stop(graceful='y'):
    """Stop apache.  Set graceful=n for immediate stop (default = y)."""
    if do(graceful):
        env.doit('sudo /usr/sbin/apache2ctl graceful-stop')
    else:
        env.doit('sudo /usr/sbin/apache2ctl stop')


@task
@roles('app')    
@require_settings(allow=['stg','prd'])                    
def a2restart(graceful='y'):
    """Restart apache.  Set graceful=n for immediate restart (default = y)."""
    if do(graceful):
        env.doit('sudo /usr/sbin/apache2ctl graceful')
    else:
        env.doit('sudo /usr/sbin/apache2ctl restart')

@task
@roles('app')
@require_settings(allow=['stg','prd'])                    
def mrostart():
    """Start maintenance mode (maintenance/repair/operations)."""
    _link_apache_conf(maint=True)
    a2restart()

    
@task
@roles('app')
@require_settings(allow=['stg','prd'])                    
def mrostop():
    """End maintenance mode."""
    _link_apache_conf()
    a2restart()


@task
@runs_once
@require_settings
@require_settings(allow=['prd','stg'], verbose=True)
def deploystatic(django='n', fnpattern='[!.]*'):
    """Copy local static files to S3.  Does not perform server operations.  
    Requires that the local git repository has no uncommitted changes.  If
    django flag is set, will use collectstatic.  Else, uses boto directly and
    an optional filename matching pattern fnpattern."""
    git_status = os.popen('git status').read()
    ready_status = '# On branch master\nnothing to commit'
    
    if True or git_status.startswith(ready_status):    
        print 'deploying to S3 ...'
        if do(django):
            _run_in_ve_local('python manage.py collectstatic ' + \
                '--settings=core.settings.deploystatic''')
        else:
            bucket_name = os.environ['AWS_STORAGE_BUCKET_NAME']
            bucket = _get_s3_con().get_bucket(bucket_name)
            matched_file = False
            for path, dirs, files in os.walk(STATIC_DIRNAME):
                for f in fnmatch.filter(files, fnpattern):
                    matched_file = True
                    dest = os.path.join(env.project_name,
                        path[len(STATIC_DIRNAME)+1:], f)
                    print 'Copying file to %s:%s' % (bucket_name, dest)
                    key = boto.s3.key.Key(bucket)
                    key.key = dest
                    fn = os.path.join(path, f)
                    key.set_contents_from_filename(fn)
                    key.set_acl('public-read')
            if not matched_file:
                notice('Nothing to deploy')
    else:
        abort('You have uncommitted local code changes. ' \
            'Please commit and push changes before deploying to S3.')      
              
 
@task  
@require_settings(allow=['prd','stg'], verbose=True)
def deploy(mro='y', restart='y', static='y', requirements='n'):
    """Deploy the latest version of the site to the server(s). Defaults to
    setting maintenance mode during the deployment and restarting apache."""
    if do(mro):
        execute(mrostart)
    execute(checkout)
    if do(requirements):
        execute(_install_requirements)
    if do(static):
        execute(deploystatic)
    if do(restart):
        if do(mro):
            execute(mrostop)
        else:
            execute(a2restart)
 
           
@roles('app', 'work')
@require_settings(allow=['prd','stg'], verbose=True)
def destroy_project():
    """Remove the project directories and config files."""
    warn('This will remove all %(project_name)s project files for' \
        ' %(settings)s on %(host)s.')
    msg = 'Destroy %(project_name)s project %(settings)s deployment? (y/n) '
    if not confirm(msg % env):
        abort('Cancelling')

    apache_link = path(env.apache_path, env.project_name)
    if exists(apache_link):
        run('rm %s' % apache_link)
    run('rm -rf %(project_path)s' % env) 
    run('rm -rf %(log_path)s' % env) 
    run('rm -rf %(ve_path)s' % env)

         
@task    
@require_settings
def destroy():
    """Remove the project directory, config files, and databases."""
    execute(destroy_project)
    execute(env.db.destroy)
    
    
