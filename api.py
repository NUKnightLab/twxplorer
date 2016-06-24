'''
Main entrypoint
'''
from flask import Flask, request, session, redirect, url_for, render_template
import sys
import os
import importlib
from functools import wraps
from collections import defaultdict, Counter
import json
import re
import traceback
import datetime
import bson
import tweepy
import pymongo
import urllib2
import urllib
import lxml.html
import nltk


# Import settings module
#if __name__ == "__main__":
#    if not os.environ.get('FLASK_SETTINGS_MODULE', ''):
#        os.environ['FLASK_SETTINGS_MODULE'] = 'core.settings.dev'

#settings_module = os.environ.get('FLASK_SETTINGS_MODULE')

#try:
#    importlib.import_module(settings_module)
#except ImportError, e:
#    raise ImportError("Could not import settings module '%s': %s" % (settings_module, e))

from twxplorer.connection import _search, _session, _tweets, _url, _list
from twxplorer import extract, twutil

app = Flask(__name__)
app.config.from_envvar('FLASK_SETTINGS_MODULE')
settings = app.config
#settings = sys.modules[settings_module]

html_parser = lxml.html.HTMLParser(encoding='utf-8')


def is_logged_in():
    """
    Is the user logged in or not?
    """
    oauth = get_oauth()
    return oauth.request_token != None and oauth.access_token != None


def login_required(f):
    """
    Decorator for login required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            return redirect(url_for('index'))
            #return redirect(url_for('index', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_static_url():
    """
    Inject the variables 'static_url' and STATIC_URL into the templates.
    Grab it from the environment variable STATIC_URL, or use the default.

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

    # Create the oauth handler
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

    # Get user language
    try:
        user_obj = tweepy.API(oauth).me()
        session['language'] = user_obj.lang
    except:
        session['language'] = 'en'

    return redirect(url_for('search'))


@app.route('/logout/')
def logout():
    """
    Logout by cleaning session
    """
    for key in ['request_token_key', 'request_token_secret', \
        'access_token_key', 'access_token_secret', 'username']:
        if key in session:
            session.pop(key)
    return redirect(url_for('index'))


#
# Misc
#

def _require_session_owned(session_id):
    """
    Require that the session is owned by the logged in user
    """
    session_r = _session.find_one({'_id': bson.ObjectId(session_id)})
    if not session_r:
        raise Exception('Session not found')

    search_r = _search.find_one({'_id': bson.ObjectId(session_r['search_id'])})
    if not search_r:
        raise Exception('Search not found')

    if search_r['username'] != session.get('username', ''):
        raise Exception('You do not have permission to access this snapshot')

    return (search_r, session_r)

def _require_session_access(session_id):
    """
    Require that the session is owned by the logged in user or shared
    """
    session_r = _session.find_one({'_id': bson.ObjectId(session_id)})
    if not session_r:
        raise Exception('Session not found')

    search_r = _search.find_one({'_id': bson.ObjectId(session_r['search_id'])})
    if not search_r:
        raise Exception('Search not found')

    if not session_r.get('shared', 0):
        if search_r['username'] != session.get('username', ''):
            raise Exception('You do not have permission to view this snapshot')

    return search_r['username']

def _get_list_map():
    """
    Return list map for logged in user (id => full_name)
    """
    list_r = _list.find_one({'username': session['username']})
    list_map = {}
    if list_r:
        for r in list_r['lists']:
            list_map[r['id_str']] = r['full_name']
    return list_map


def _get_saved_results(params=None):
    """
    Get saved results matching params, grouped by search
    """
    search_by_query = []
    search_by_list = []

    list_map = _get_list_map()

    search_q = {'username': session['username']}
    search_q.update(params or {})

    search_cursor = _search.find(search_q, sort=[('query', pymongo.ASCENDING)])
    for search_r in search_cursor:
        search_r['_id'] = str(search_r['_id'])
        search_r['sessions'] = []

        if 'list_id' in search_r:
            search_r['list_name'] = list_map.get(search_r['list_id']) \
                or search_r.get('list_name') \
                or '[unknown]'

        session_cursor = _session.find(
            {'search_id': search_r['_id'], 'saved': 1},
            fields=['_id', 'dt', 'shared'],
            sort=[('dt', pymongo.DESCENDING)]
        )
        for session_r in session_cursor:
            session_r['_id'] = str(session_r['_id'])
            session_r['dt'] = datetime.datetime \
                .strptime(session_r['dt'], '%Y-%m-%dT%H:%M:%S.%f') \
                .strftime('%b %d %Y %H:%M:%S')

            search_r['sessions'].append(session_r)

        if search_r['sessions']:
            if 'list_id' in search_r:
                search_by_list.append(search_r)
            else:
                search_by_query.append(search_r)

    return (search_by_query, search_by_list)


def _shorten_url(url):
    """Shorten an URL."""
    if (settings.BITLY_USERNAME != False) & (settings.BITLY_APIKEY != False):
        params = {
            'login': settings.BITLY_USERNAME,
            'apiKey': settings.BITLY_APIKEY,
            'longUrl': url,
            'format': 'json'
        }
        if settings.BITLY_DOMAIN  :
            params['domain'] = settings.BITLY_DOMAIN
        bitly_call = 'https://api-ssl.bitly.com/v3/shorten?' + urllib.urlencode(params);
        response = json.loads(urllib2.urlopen(urllib2.Request(bitly_call)).read())

        if response['status_code'] == 200:
            url = response['data']['url']
        else:
            print "bitly error: %s" % response['status_txt']
    return url

#
# Main views
#

@app.route("/about/", methods=['GET', 'POST'])
def about(name=''):
    """
    About page
    """
    return render_template('about.html')

@app.route("/", methods=['GET', 'POST'])
def index(name=''):
    """
    Main page
    """
    try:
        return render_template('index.html')
    except Exception, e:
        traceback.print_exc()
        return render_template('index.html', error=str(e))


@app.route("/search/", methods=['GET', 'POST'])
@app.route("/search/<session_id>/", methods=['GET', 'POST'])
# commented out to allow shared snapshots: @login_required
def search(session_id=''):
    """
    Search by query page
    """
    try:
        logged_in = is_logged_in()
        saved_results = []
        snapshot_owner = ''

        if logged_in:
            saved_results, unused = _get_saved_results(
                {'list_id': {'$exists': False}})

        if session_id:
            snapshot_owner = _require_session_access(session_id)
        elif not logged_in:
            return redirect(url_for('index'))

        return render_template('search.html', session_id=session_id,
            snapshot_owner=snapshot_owner,
            languages=extract.stopword_languages, saved_results=saved_results)
    except Exception, e:
        traceback.print_exc()
        return render_template('search.html', session_id=session_id,
            snapshot_owner=snapshot_owner,
            languages=extract.stopword_languages, saved_results=saved_results,
            error=str(e))


@app.route("/lists/", methods=['GET', 'POST'])
@app.route("/lists/<session_id>/", methods=['GET', 'POST'])
# commented out to allow shared snapshots: @login_required
def lists(session_id=''):
    """
    Search by list page
    """
    try:
        logged_in = is_logged_in()
        list_r = {'lists': []}
        list_map = {}
        saved_results = []

        if logged_in:
            unused, saved_results = _get_saved_results(
                {'list_id': {'$exists': True}})

            username = session.get('username')
            delta = datetime.timedelta(minutes=15)
            refresh = False

            list_r = _list.find_one({'username': username})
            if not list_r:
                list_r = {'username': username}
                refresh = True
            elif (list_r['dt'] + delta) < datetime.datetime.now():
                refresh = True
            elif request.args.get('refresh'):
                refresh = True

            if refresh:
                api = tweepy.API(get_oauth())

                lists = []
                for r in api.lists_all(screen_name=username):
                    lists.append({
                        'id_str': r.id_str,
                        'slug': r.slug,
                        'name': r.name,
                        'full_name': r.full_name
                    })

                list_r['dt'] = datetime.datetime.now()
                list_r['lists'] = lists
                list_r['_id'] = _list.save(list_r, manipulate=True)

            list_map = _get_list_map()

        if session_id:
            _require_session_access(session_id)
        elif not logged_in:
            return redirect(url_for('index'))

        return render_template('lists.html', session_id=session_id,
            languages=extract.stopword_languages, saved_results=saved_results,
            lists=list_r['lists'], list_map=json.dumps(list_map))
    except tweepy.TweepError, e:
        traceback.print_exc()
        return render_template('lists.html', session_id=session_id,
            languages=extract.stopword_languages, error=str(e))
    except Exception, e:
        traceback.print_exc()
        return render_template('lists.html', session_id=session_id,
            languages=extract.stopword_languages, error=str(e))


@app.route("/history/", methods=['GET', 'POST'])
@login_required
def history():
    """
    Get search history, grouped by search -> session
    """
    try:
        searches, lists = _get_saved_results()
        return render_template('history.html',
            searches=searches, lists=lists)
    except Exception, e:
        traceback.print_exc()
        return render_template('history.html', error=str(e))


@app.route("/analyze/", methods=['GET', 'POST'])
@login_required
def analyze():
    """
    Get tweets from twitter and analyze them

    @language = language code, e.g. 'en'

    @query = query string
        OR
    @list_id = list id
     """
    try:
        language = request.args.get('language') or 'en'

        query = request.args.get('query')
        list_id = request.args.get('list_id')

        if query:
            query_lower = query.lower()
        elif list_id:
            list_map = _get_list_map()
        else:
            raise Exception('No query or list specified')

        # Get api object
        api = tweepy.API(get_oauth())

        # Get/create search record
        param = {
            'username': session['username'],
            'language': language
        }
        if query:
            param['query_lower'] = query_lower
        else:
            param['list_id'] = list_id
        search_r = _search.find_one(param)
        if not search_r:
            search_r = param
            if query:
                search_r['query'] = query
            else:
                search_r['list_name'] = list_map[list_id]
            search_r['_id'] = _search.save(search_r, manipulate=True)
        search_id = str(search_r['_id'])

        # Create search session
        session_r = {
            'search_id': search_id,
            'dt': datetime.datetime.now().isoformat(),
            'stem_counts': [],      # [[stem, post count]]
            'stem_map': {},         # {stem: [term, count]}
        }
        session_r['_id'] = _session.save(session_r, manipulate=True)
        session_id = str(session_r['_id'])

        # Process tweets
        stopwords = extract.get_stopwords(language).copy()
        stoptags = set()
        stemmer = extract.get_stemmer(language)
        stem_map = defaultdict(Counter)
        tweet_list = []

        if query:
            stoptags.update([x.lower().lstrip('#') for x in query_lower.split()])
            stopwords.update(stoptags)
            cursor = tweepy.Cursor(api.search, q=query, lang=language, \
                count=100, result_type='recent', include_entities=True)
        else:
            cursor = tweepy.Cursor(api.list_timeline, list_id=list_id, \
                count=100, include_entities=True)

        for tweet in cursor.items(limit=settings.TWITTER_SEARCH_LIMIT):
            tweet_dict = twutil.tweepy_model_to_dict(tweet)

            tweet_dict['session_id'] = session_id
            tweet_dict['embed'] = twutil.format_text(tweet_dict)
            tweet_dict['tokens'] = extract.tokenize(tweet_dict['text'])

            # Filter hashtags from query
            # tweet_dict['hashtags'] = list(set(['#'+x['text'].lower() \
            #    for x in tweet_dict['entities']['hashtags']]))
            tweet_dict['hashtags'] = list(set([
                    '#'+x['text'].lower() \
                    for x in tweet_dict['entities']['hashtags'] \
                    if x['text'].lower() not in stoptags
                ]))

            tweet_dict['urls'] = list(set([x['expanded_url'] \
                for x in tweet_dict['entities']['urls']]))

            tweet_list.append(tweet_dict)

        # ------------------------------------------------------------
        # Process trigrams

        trigram_counter = Counter()

        for tweet in tweet_list:
            grams = []

            for tokens in tweet['tokens']:
                for g in nltk.ngrams(tokens, 3):
                    if extract.stoplist_iter(g, stopwords):
                        continue
                    if g[0].startswith('@') or g[1].startswith('@') or g[2].startswith('@'):
                        continue
                    grams.append(g)

            stems = extract.stems_from_grams(grams, stemmer)
            for s, g in zip(stems, grams):
                stem_map[s].update([g])

            tweet['stems_3'] = list(set(stems))
            trigram_counter.update(tweet['stems_3'])

        # Ignore trigrams that only appear once
        for g, n in trigram_counter.items():
            if n < 2:
                del trigram_counter[g]
                del stem_map[g]

        # ------------------------------------------------------------
        # Process bigrams

        bigram_counter = Counter()

        for tweet in tweet_list:
            grams = []
            stems = []

            for tokens in tweet['tokens']:
                gram_list = nltk.ngrams(tokens, 2)
                stem_list = extract.stems_from_grams(gram_list, stemmer)

                last_i = len(gram_list) - 1

                for i, g in enumerate(gram_list):
                    if extract.stoplist_iter(g, stopwords):
                        continue
                    if g[0].startswith('@') or g[1].startswith('@'):
                        continue

                    # Filter by trigrams
                    if i > 0 and \
                    (stem_list[i-1][0], stem_list[i][0], stem_list[i][1]) in trigram_counter:
                        continue
                    if i < last_i and \
                    (stem_list[i][0], stem_list[i][1], stem_list[i+1][1]) in trigram_counter:
                        continue

                    grams.append(g)
                    stems.append(stem_list[i])

            for s, g in zip(stems, grams):
                stem_map[s].update([g])

            tweet['stems_2'] = list(set(stems))
            bigram_counter.update(tweet['stems_2'])

        # Ignore bigrams that only appear once
        for g, n in bigram_counter.items():
            if n < 2:
                del bigram_counter[g]
                del stem_map[g]

        # ------------------------------------------------------------
        # Process unigrams

        for tweet in tweet_list:
            grams = []
            stems = []

            for tokens in tweet['tokens']:
                gram_list = nltk.ngrams(tokens, 1)
                stem_list = extract.stems_from_grams(gram_list, stemmer)

                last_i = len(gram_list) - 1

                for i, g in enumerate(gram_list):
                    if extract.stoplist_iter(g, stopwords):
                        continue

                    # Filter bigram terms
                    if i > 0 and \
                    (stem_list[i-1][0], stem_list[i][0]) in bigram_counter:
                        continue
                    if i < last_i and \
                    (stem_list[i][0], stem_list[i+1][0]) in bigram_counter:
                        continue

                    # Filter trigram terms
                    if i > 1 and \
                    (stem_list[i-2][0], stem_list[i-1][0], stem_list[i][0]) in trigram_counter:
                        continue
                    if i > 0 and i < last_i and \
                    (stem_list[i-1][0], stem_list[i][0], stem_list[i+1][0]) in trigram_counter:
                        continue
                    if i < (last_i - 1) and \
                    (stem_list[i][0], stem_list[i+1][0], stem_list[i+2][0]) in trigram_counter:
                        continue

                    grams.append(g)
                    stems.append(stem_list[i])

            for s, g in zip(stems, grams):
                stem_map[s].update([g])

            # Process stems
            tweet['stems'] = [' '.join(x) for x in set(stems)]
            tweet['stems'].extend([' '.join(x) for x in tweet['stems_2'] if x in bigram_counter])
            tweet['stems'].extend([' '.join(x) for x in tweet['stems_3'] if x in trigram_counter])

            del tweet['stems_2']
            del tweet['stems_3']

        # Update session
        for stem, c in stem_map.iteritems():
            session_r['stem_map'][' '.join(stem)] = \
                [' '.join(k) for k, v in c.most_common()]

        # Save tweets
        if tweet_list:
            _tweets.insert(tweet_list)

        session_r['tweet_count'] = len(tweet_list)
        _session.save(session_r)

        return _jsonify(session=session_r)
    except tweepy.TweepError, e:
        traceback.print_exc()
        return _jsonify(error=e.message[0]['message'])
    except Exception, e:
        traceback.print_exc()
        return _jsonify(error=str(e))


@app.route("/filter/<session_id>/", methods=['GET', 'POST'])
# commented out to allow shared snapshots: @login_required
def filter(session_id):
    """
    Get histogram and tweets

    @filter: comma-delimited list of elements to filter by
        if element starts with '#', then it is a hashtag
        else, it is a stem
    """
    try:
        _require_session_access(session_id)

        session_r = _session.find_one(
            {'_id': bson.ObjectId(session_id)})
        if not session_r:
            raise Exception('Session not found')

        search_r = _search.find_one(
            {'_id': bson.ObjectId(session_r['search_id'])})
        if not search_r:
            raise Exception('Search not found')

        # Find tweets
        params = {'session_id': session_id}

        filter = request.args.getlist('filter[]')
        filter_stems = []
        filter_hashtags = []
        filter_urls = []

        for element in filter:
            if element.startswith('#'):
                filter_hashtags.append(element)
            elif element.startswith('http'):
                filter_urls.append(element)
            else:
                filter_stems.append(element)

        if filter_urls:
            params['urls'] = {'$all': filter_urls}
        if filter_stems:
            params['stems'] = {'$all': filter_stems}
        if filter_hashtags:
            params['hashtags'] = {'$all': filter_hashtags}

        cursor = _tweets.find(params, {
                'embed': 1,
                'id_str': 1,
                'created_at': 1,
                'user.name': 1,
                'user.screen_name': 1,
                'retweeted_status.id_str': 1,
                'stems': 1,
                'hashtags': 1,
                'urls': 1
            }, sort=[('dt', pymongo.DESCENDING)])

        # Process tweets
        stem_counter = Counter()
        hashtag_counter = Counter()
        url_counter = Counter()

        tweets = []
        retweets = 0
        id_set = set()

        for tweet in cursor:
            stem_counter.update(tweet['stems'])
            hashtag_counter.update(tweet['hashtags'])
            url_counter.update(tweet['urls'])

            if tweet['id_str'] in id_set:
                retweets += 1
                continue
            id_set.add(tweet['id_str'])

            if 'retweeted_status' in tweet:
                retweeted_id = tweet['retweeted_status']['id_str']
                if retweeted_id in id_set:
                    retweets += 1
                    continue
                id_set.add(retweeted_id)

            tweets.append({
                'text': tweet['embed'],
                'user_name': tweet['user']['name'],
                'user_screen_name': tweet['user']['screen_name'],
                'id_str': tweet['id_str'],
                'created_at': tweet['created_at']
            })

        stem_counts = [x for x in stem_counter.most_common() \
            if x[0] not in filter_stems]
        hashtag_counts = [x for x in hashtag_counter.most_common() \
            if x[0] not in filter_hashtags]
        url_counts = [x for x in url_counter.most_common() \
            if x[0] not in filter_urls]

        return _jsonify(
            search=search_r,
            session=session_r,
            stem_counts=stem_counts,
            hashtag_counts=hashtag_counts,
            url_counts=url_counts,
            tweets=tweets,
            retweets=retweets
        )
    except Exception, e:
        traceback.print_exc()
        return _jsonify(error=str(e))


@app.route("/history/update/<session_id>/", methods=['GET', 'POST'])
@login_required
def history_update(session_id):
    """
    Update search session
    """
    try:
        search_r, session_r = _require_session_owned(session_id)

        params = {}
        for k in ['saved', 'shared']:
            if k in request.args:
                params[k] = int(request.args.get(k))

        if params.get('shared') and not session_r.get('share_url'):
            if search_r.get('query'):
                params['share_url'] = _shorten_url('http://%s%s' % ( \
                    request.host,
                    url_for('search', session_id=str(session_r['_id']))
                ))
            else:
                params['share_url'] = _shorten_url('http://%s%s' % ( \
                    request.host,
                    url_for('lists', session_id=str(session_r['_id']))
                ))

        _session.update({'_id': bson.ObjectId(session_id)},
            {'$set': params}, multi=False)

        return _jsonify(**params)
    except Exception, e:
        traceback.print_exc()
        return _jsonify(error=str(e))

@app.route("/history/tweet/<session_id>/", methods=['GET', 'POST'])
def history_tweet(session_id):
    """
    Redirect to twitter sharing
    """
    search_r, session_r = _require_session_owned(session_id)

    if search_r.get('query'):
        tmpl = 'See what people tweeted about "%s" #twxplorer @KnightLab %s'
        query = search_r.get('query')

        msg = tmpl % (query, session_r['share_url'])

        n = len(msg)
        if n > 140:
            query = query[:-(n - 140 + 4)]+'...'
            msg = tmpl % (query, session_r['share_url'])
    else:
        tmpl = 'See what %s tweeted #twxplorer @KnightLab %s'
        list_map = _get_list_map()
        list_name = list_map.get(search_r['list_id']) \
            or search_r.get('list_name') \
            or '[unknown]'

        msg = tmpl % (list_name, session_r['share_url'])
        n = len(msg)
        if n > 140:
            list_name = list_name[:-(n - 140 + 4)]+'...'
            msg = tmpl % (list_name, session_r['share_url'])

    tweetUrl = 'https://twitter.com/share?'+urllib.urlencode({
        'text': msg, 'url': 'false' })

    return redirect(tweetUrl)

@app.route("/history/delete/", methods=['GET', 'POST'])
@login_required
def history_delete():
    """
    Delete searches/sessions/tweets

    @searches = list of search ids
    @sessions = list of session ids
    """
    try:
        search_ids = request.args.getlist('searches[]')
        session_ids = set(request.args.getlist('sessions[]'))

        cursor = _session.find({'search_id': {'$in': search_ids}}, {'_id': 1})
        session_ids.update([str(r['_id']) for r in cursor])
        session_ids = list(session_ids)

        _tweets.remove(
            {'session_id': {'$in': session_ids}})
        _session.remove(
            {'_id': {'$in': [bson.ObjectId(x) for x in session_ids]}})
        _search.remove(
            {'_id': {'$in': [bson.ObjectId(x) for x in search_ids]}})

        return _jsonify(deleted=session_ids)
    except Exception, e:
        traceback.print_exc()
        return _jsonify(error=str(e))


@app.route("/urls/", methods=['GET', 'POST'])
# commented out to allow shared snapshots: @login_required
def urls():
    """
    Get extended info for urls

    @urls = list of urls
    """
    try:
        urls = request.args.getlist('urls[]')
        if not urls:
            raise Exception('No urls found')

        info = []
        for url in urls:
            r = _url.find_one({'url': url})
            if not r:
                r = {'url': url, 'title': ''}
                try:
                    resp = urllib2.urlopen(url, timeout=5)
                    element = lxml.html.parse(resp, html_parser)
                    if element:
                        r['title'] = element.find(".//title").text.strip()
                except Exception, e:
                    pass

                r['_id'] = _url.insert(r, manipulate=True)

            info.append(r)

        return _jsonify(info=info)
    except Exception, e:
        traceback.print_exc()
        return _jsonify(error=str(e))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)


