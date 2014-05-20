"""
Tweet utilities
"""
import datetime
import re
import tweepy

def format_text(tweet_dict):
    """Return formatted version of tweet text"""
    text = tweet_dict['text']
    
    for d in tweet_dict['entities']['user_mentions']:
        text = re.sub(
            '@%(screen_name)s' % d, 
            '<a href="https://twitter.com/%(screen_name)s">@%(screen_name)s</a>' % d,
            text)
    for d in tweet_dict['entities']['hashtags']:
        text = re.sub(
            '#%(text)s' % d, 
            '<a href="https://twitter.com/search?%23%(text)s">#%(text)s</a>' % d,
            text)
    return text

def tweepy_model_to_dict(status):
    """
    Convert a tweepy status object to a dictionary
    https://dev.twitter.com/docs/platform-objects/tweets
    """ 
    d = {}
    
    for key, value in status_obj.__getstate__().iteritems():
        if isinstance(value, datetime.datetime):
            d[key] = value.isoformat()
        elif isinstance(value, tweepy.models.Model):
            d[key] = tweepy_model_to_dict(value)
        else:
            d[key] = value    
    return d
    
def process_status(status, stoptags):
    """
    Convert a tweepy status object to a dictionary
    https://dev.twitter.com/docs/platform-objects/tweets
    """ 
    d = {
        'coordinates': status.coordinates,
        'created_at': status.created_at.isoformat(),
        'favorite_count': status.favorite_count,
        'id_str': status.id_str,
        'lang': status.lang,
        'retweet_count': status.retweet_count,
        'text': status.text,
        'user':  {
            'name': status.user.name,
            'screen_name': status.user.screen_name
        },
        # special
        'hashtags': list(set(['#'+x['text'].lower() \
            for x in status.entities['hashtags'] \
            if x['text'].lower() not in stoptags])),                            
        'urls': list(set([x['expanded_url'] \
            for x in status.entities['urls']])),            
        'voices': ['@'+status.user.screen_name]
    }
    
    # embed
    text = status.text    
    for e in status.entities['user_mentions']:
        text = re.sub(
            '@%(screen_name)s' % e, 
            '<a href="https://twitter.com/%(screen_name)s">@%(screen_name)s</a>' % e,
            text)
    for e in status.entities['hashtags']:
        text = re.sub(
            '#%(text)s' % e, 
            '<a href="https://twitter.com/search?%23%(text)s">#%(text)s</a>' % e,
            text)            
    d['embed'] = text    
       
    # retweeted_status
    try:
        r = status.retweeted_status
        d['retweeted_status'] = {
            'id_str': r.id_str,
            'user': {
                'name': r.user.name,
                'screen_name': r.user.screen_name
            }   
        }
        d['voices'].append('@'+r.user.screen_name)
    except AttributeError:
        pass
    
    return d



    
