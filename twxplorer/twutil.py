"""
Tweet utilities
"""
import datetime
import re
import tweepy

def tweepy_model_to_dict(status_obj):
    """Convert a tweepy status object to a dictionary""" 
    d = {}
    for key, value in status_obj.__getstate__().iteritems():
        if isinstance(value, datetime.datetime):
            d[key] = value.isoformat()
        elif isinstance(value, tweepy.models.Model):
            d[key] = tweepy_model_to_dict(value)
        else:
            d[key] = value    
    return d

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
