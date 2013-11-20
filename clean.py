'''
Clean up old data

Usage:
    python <script> [options]

Options:
    -h, --help
        Print this help information   
    
    -d=<n>, --days=<n>
        Delete unsaved data more than n days old (default = 7)
        
'''
import sys
import getopt
import os
import importlib
import datetime
import pymongo

# Import settings module
if __name__ == "__main__":
    if not os.environ.get('FLASK_SETTINGS_MODULE', ''):
        os.environ['FLASK_SETTINGS_MODULE'] = 'core.settings.loc'

    settings_module = os.environ.get('FLASK_SETTINGS_MODULE')

    try:
        importlib.import_module(settings_module)
    except ImportError, e:
        raise ImportError("Could not import settings module '%s': %s" % (settings_module, e))

from twxplorer.connection import _search, _session, _tweets


def clean_database(n_days):
    """Clean database"""
    print 'Clean database: %d days' % n_days
    
    dt = datetime.datetime.utcnow() - datetime.timedelta(days=n_days)
    dt_str = dt.isoformat()
    print 'Removing unsaved data before %s' % dt_str
    
    session_list = list(_session.find(
        {'saved': {'$ne': 1}, 'dt': {'$lt': dt_str}},
        {'saved': 1, 'dt': 1}
    ))
    for session_r in session_list:
        # Delete tweets associated with session
        _tweets.remove({'session_id': str(session_r['_id'])})
        
        # Delete session
        _session.remove({'_id': session_r['_id']})
        
    print 'Removed %d sessions' % len(session_list)
              
class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg

if __name__ == "__main__":
    try:
        try:
            opts, args = getopt.getopt(sys.argv[1:], "hd:", ["help", "days="])
        except getopt.error, msg:
             raise Usage(msg)

        # Handle options 
        opt_days = 7
        
        for option, value in opts:
            if option in ("-h", "--help"):
                print __doc__
                sys.exit(0)
            if option in ("-d", "--days"):
                opt_days = int(value)
            else:
                raise Usage('unhandled option "%s"' % option)
                            
        # Handle arguments 
        n_args = len(args)
        if n_args > 0:
            raise Usage("invalid number of arguments")       

        # Doit
        clean_database(opt_days)
                            
    except Usage, err:
        print >>sys.stderr, err.msg
        print >>sys.stderr, "for help use --help"
        sys.exit(2)
    except Exception, err:
        print >>sys.stderr, err
        sys.exit(1)
    else:
        sys.exit(0)
