'''
Main entrypoint
'''
from flask import Flask, request, session, redirect, url_for, render_template
import sys
import os
import importlib
from collections import defaultdict, Counter
import json
import re
import traceback
import datetime
import bson
import tweepy
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
from twxplorer import extract, twutil


app = Flask(__name__)
app.config.from_envvar('FLASK_CONFIG_MODULE')

settings = sys.modules[settings_module]


@app.context_processor
def inject_static_url():
    """
    Inject the variables 'static_url' and STATIC_URL into the templates to
    avoid hard-coded paths to static files. Grab it from the environment 
    variable STATIC_URL, or use the default.

    Note:  The template variable will always have a trailing slash.
    """
    static_url = settings.STATIC_URL or app.static_url_path
    if not static_url.endswith('/'):
        static_url += '/'
    return dict(static_url=static_url, STATIC_URL=static_url)

class APIEncoder(json.JSONEncoder):
    def default(self, obj):
        """Format obj as json."""
        if isinstance(obj, datetime.datetime):
            return obj.isoformat()
        if isinstance(obj, bson.ObjectId):
            return str(obj)        
        return json.JSONEncoder.default(self, obj)

def _request_wants_json():
    """Determine response type."""
    best = request.accept_mimetypes \
        .best_match(['application/json', 'text/html'])
    return best == 'application/json' and \
        request.accept_mimetypes[best] > \
        request.accept_mimetypes['text/html']

def _jsonify(*args, **kwargs):
    """Convert to JSON"""
    return app.response_class(json.dumps(dict(*args, **kwargs), cls=APIEncoder),
        mimetype='application/json')
         
#
# Auth
#

def get_oauth():
    """
    Get a tweepy OAuthHander
    """
    cb_url = 'http://'+request.host+url_for('auth_verify')
    
    oauth = tweepy.OAuthHandler(
        settings.TWITTER_CONSUMER_KEY,
        settings.TWITTER_CONSUMER_SECRET,
        callback=cb_url,
        secure=True)
    
    key = session.get('request_token_key')
    secret = session.get('request_token_secret')
    if key and secret:
        oauth.set_request_token(key, secret)
    
    key = session.get('access_token_key')
    secret = session.get('access_token_secret')
    if key and secret:
        oauth.set_access_token(key, secret)
               
        if not session.get('username'):
            username = oauth.get_username()
            if username:
                session['username'] = username.lower()
    return oauth


def is_logged_in():
    """
    Is the user logged in or not?
    """
    oauth = get_oauth()
    return oauth.request_token != None and oauth.access_token != None
    
    
@app.route("/auth/", methods=['GET', 'POST'])
def auth():
    """
    Redirect to twitter for user authorization
    """
    oauth = get_oauth()
    auth_url = oauth.get_authorization_url()
    session['request_token_key'] = oauth.request_token.key
    session['request_token_secret'] = oauth.request_token.secret
    return redirect(auth_url)


@app.route("/auth/verify/", methods=['GET', 'POST'])
def auth_verify():
    """
    Twitter redirects back here post-authorization
    """
    if request.args.get('denied'):
        return redirect(url_for('logout'))
    
    oauth = get_oauth()
    oauth.get_access_token(verifier=request.args.get('oauth_verifier'))
    session['access_token_key'] = oauth.access_token.key
    session['access_token_secret'] = oauth.access_token.secret
    return redirect(url_for('index'))  


@app.route('/logout/')
def logout():
    """
    Logout
    """
    for key in ['request_token_key', 'request_token_secret', \
        'access_token_key', 'access_token_secret', 'username']:
        if key in session:
            session.pop(key)
    return redirect(url_for('index'))

         
#
# Routes
#

@app.route("/", methods=['GET', 'POST'])
def index(name=''):
    """Main page"""    
    error = ''    
    try:
        if is_logged_in():
            return redirect(url_for('main'))
            
        return render_template('index.html')
    except Exception, e:
        error = str(e)
        traceback.print_exc()
        return render_template('index.html', error=error)
        

@app.route("/main/", methods=['GET', 'POST'])
def main():
    """Main page for logged in user"""
    if not is_logged_in():
        return redirect(url_for('index'))

    return render_template('main.html')
   
@app.route("/main/search/", methods=['GET', 'POST'])
def search():
    """Search twitter"""
    error = ''

    if not is_logged_in():
        return redirect(url_for('index'))
    
    try:
        query = request.args.get('query')
        if not query:
            raise Exception('No query found')
        
        api = tweepy.API(get_oauth())
        
        response = api.search(
            q=query, result_type='recent', count=100, include_entities=True)
                    
        # Get/create search record
        param = {'username': session['username'], 'query': query}
        search_r = _search.find_one(param)
        if not search_r:
            search_r = param
            search_r['_id'] = _search.save(search_r, manipulate=True)
        search_id = str(search_r['_id'])
        
        # Create new search session
        session_r = {
            'search_id': search_id,
            'dt': datetime.datetime.now().isoformat(),
            'stem_counts': [],      # [[stem, post count]]
            'stem_map': {},         # {stem: [term, count]}  
        }
        session_r['_id'] = _session.save(session_r, manipulate=True)
        session_id = str(session_r['_id'])
        
        # Process tweets
        stem_map = defaultdict(Counter)
        stem_counter = Counter()
       
        # Add query terms to stopwords
        stopwords = extract._stopwords.copy()
        stopwords.update([x.lower() for x in query.split()])
        
        tweets = []        
        for tweet in response:
            tweet_dict = twutil.status_to_dict(tweet)
            
            grams = extract.grams_from_string(tweet_dict['text'], stopwords)
            stems = extract.stems_from_grams(grams)
            
            terms = [' '.join(g) for g in grams]
            stems = [' '.join(s) for s in stems]
                      
            for s, t in zip(stems, terms):
                stem_map[s].update([t])
            
            stem_set = set(stems)
            stem_counter.update(stem_set)
            
            tweet_dict['session_id'] = session_id
            tweet_dict['stems'] = list(stem_set)            
            tweets.append(tweet_dict)
                      
        # Update session
        session_r['stem_counts'] = stem_counter.most_common()
        for stem, c in stem_map.iteritems():
            session_r['stem_map'][stem] = c.most_common()
        _session.save(session_r)
        
        # Save tweets
        _tweets.insert(tweets)   
        
        return _jsonify(error=error, search=search_r, session=session_r)
    except tweepy.TweepError, e:
        error = e.message[0]['message']
        traceback.print_exc()
        return _jsonify(error=error)        
    except Exception, e:
        error = str(e)
        traceback.print_exc()
        return _jsonify(error=error)
            
        
@app.route("/main/search/<session_id>/", methods=['GET', 'POST'])
def results(session_id):
    """
    Get histogram and tweets
    @filter: comma-delimited list of stems to filter by
    """
    error = ''

    if not is_logged_in():
        return redirect(url_for('index'))
    
    try:
        # Find session
        session_r = _session.find_one({'_id': bson.ObjectId(session_id)})
        if not session_r:
            raise Exception('Session not found')
            
        # Find tweets
        filter = request.args.get('filter')
        if filter:
            cursor = _tweets.find({
                'session_id': session_id, 
                'stems': {'$all': filter.split(',')}
            })
        else:
            ignore_stems = []
            cursor = _tweets.find({
                'session_id': session_id,
            })
        
        # Process tweets
        stem_counter = Counter()
        tweets = []        
    
        for tweet in cursor:  
            stem_counter.update(set(tweet['stems']))
                                
            tweets.append({
                'text': twutil.format_text(tweet),
                'user_name': tweet['user']['name'],
                'user_screen_name': tweet['user']['screen_name'],
                'id_str': tweet['id_str'],
                'created_at': tweet['created_at']           
            })
            
        return _jsonify(stem_counts=stem_counter.most_common(), tweets=tweets)
    except Exception, e:
        error = str(e)
        traceback.print_exc()
        return _jsonify(error=error)

      
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


