import sys
import os
import urllib2
import re
import datetime
from collections import defaultdict, Counter
from . import extract
from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError
from refine.connection import _articles, _posts

# Get settings module
settings = sys.modules[os.environ['FLASK_SETTINGS_MODULE']]

def _update_dict_counter(d, key, new_c):
    """Update old counts under key with new counts."""
    old_c = Counter(dict(d[key]))
    old_c.update(new_c)
    d[key] = old_c.most_common()



def article_by_url(url):
    """Get article information."""
    print "fetch.article_by_url", url

    r = _articles.find_one({'url': url})
    if r:
        print 'cached', url
    else:
        cleaned_url = extract.clean_url(url)
        r = _articles.find_one({'url': cleaned_url})
        if r:
            print 'cached cleaned', cleaned_url
        else:
            print 'retrieving', url
            html = html_by_url(url)
        
            forum = extract.forum(url, html)
            if not forum:
                raise Exception("Unable to determine forum name")
        
            print 'extracting', forum, url
            text = extract.text_from_html(html)
        
            print 'analyzing', forum, url
            stems = extract.stems_from_string(text)
        
            print 'saving', url
            r = {
                'article_dt': datetime.datetime.now(),
                'url': url,
                'forum': forum,                 # disqus forum name
                'text': text,                   # article text
                'post_count': 0,                # number of posts
                'post_dt': 0,                   # datetime of last check for posts
                 # stems
                'text_stems': [' '.join(s) for s in set(stems)],
                'post_stems': [],               # [[stem, post count]]
                'diff_stems': [],               # post_stems not in text_stems
                'stem_map': {}                  # {stem: [term, count]}             
            }
            _articles.insert(r, manipulate=True)  # so id is set
    return r

def posts_by_article(article):
    """Fetch (new) posts for article."""
    print "fetch.posts_by_article", article['_id'], article['url']

    article_id = str(article['_id'])

    params = {
        'thread':'link:'+article['url'], 
        'forum':article['forum'], 
        'limit':100
    }
    print params
    
    post_dt = article.get('post_dt')
    if post_dt:
        params['since'] = post_dt.isoformat()
        params['order'] = 'asc' # for posts created _after_ since

    post_stems = Counter()
    post_count = 0
    stem_map = defaultdict(Counter)
    
    try:
        i = 0
        for i, p in enumerate(disqusapi.Paginator(_disqus.threads.listPosts, **params)):
            if i and i % 100 == 0:
                print 'Fetched %d posts' % i
            if p['isDeleted'] or p['isSpam']:
                continue

            grams = extract.grams_from_string(p['raw_message'])
            stems = extract.stems_from_grams(grams)
            
            terms = [' '.join(g) for g in grams]
            stems = [' '.join(s) for s in stems]
 
            post = extract.post_data(p)        
            post['article'] = article_id
            post['terms'] = terms
            post['stems'] = stems

            try:
                _posts.save(post, safe=True)
    
                post_stems.update(set(stems))
                post_count += 1
                
                for s, t in zip(stems, terms):
                    stem_map[s].update([t])
            except DuplicateKeyError:
                pass
        print 'Processed %d posts' % i
    except disqusapi.APIError, e:
        raise Exception(e.message)
  
    if any(post_stems):         
        _update_dict_counter(article, 'post_stems', post_stems)

        for stem in article['text_stems']:
            del post_stems[stem]           
        if any(post_stems):
            _update_dict_counter(article, 'diff_stems', post_stems)
         
        for stem, c in stem_map.iteritems():
            c.update(dict(article['stem_map'].get(stem, [])))
            article['stem_map'][stem] = c.most_common()

    article['post_count'] += post_count
    article['post_dt'] = datetime.datetime.now().replace(microsecond=0)
    _articles.save(article)
