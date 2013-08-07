"""
Utility functions
"""
from fabric.api import env, require
from fabric.colors import red, blue
from fabric.context_managers import prefix
from fabric.decorators import task
import fabric.utils
import sys
import os
from functools import update_wrapper


def require_settings(fn=None, **kwargs):
    """
    Decorator preventing function from running unless env.settings is set.
    If not set, an error will be thrown via fabric.api.require().
    
    Available options:  
    
    allow:     Only run the function if env.settings is in this list.    
    verbose:   Output a warning to the user about skipped function.
    
    Examples:
    
    @require_settings
    def f():

    @require_settings(allow=['loc','stg'], verbose=True)
    def f():
    """ 
    allow = kwargs.pop('allow', None)
    verbose = kwargs.pop('verbose', False)   

    def decorator(func):
        def wrapper(*args, **kwargs):
            require('settings')
            if not allow or env.settings in allow:
                return func(*args, **kwargs)
            elif verbose:
                warn('Skipping "%s"' % func.__name__)
        return update_wrapper(wrapper, func)
        
    if fn:
        return decorator(fn)
    else:
        return decorator


def run_in_ve(command):
    """Execute the command inside the virtualenv."""
    with prefix('. %s' % env.activate_path):
        env.doit(command)
                
 
def notice(msg):
    """Show blue notice message."""
    print '\nNotice: '+blue(msg % env)+'\n'


def warn(msg):
    """Show red warning message."""
    fabric.utils.warn(red(msg % env))


def abort(msg):
    """Show red error message and abort."""      
    fabric.utils.abort(red(msg % env))


def path(*args):
    """Join paths."""
    return os.path.join(*args)


def ls(d):
    """Get a directory listing for directory d."""
    if env.settings == 'loc':
        return [path(d, f) for f in env.doit("ls -1 %s" % d,
            capture=True).splitlines()] 
    else:
        return [path(d, f) for f in env.doit("ls -1 %s" % d).splitlines()] 


def do(yes_no):
    """Boolean for yes/no values."""
    return yes_no.lower().startswith('y')


def confirm(msg):
    """Get confirmation from the user."""
    return do(raw_input(msg))
    
def check_path():
    """Make sure the main project directory is in sys.path."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    notice('Checking sys.path for %s' % project_root)
    if project_root not in sys.path:
        notice('Appending %s to sys.path' % project_root)
        sys.path.append(project_root)
    
