import sys
import os
import re
import string
import HTMLParser
import nltk
from nltk.corpus import stopwords
from nltk import SnowballStemmer
import unicodedata

# available languages (languages, ISO 639-1 code)
# ref: http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
# restricted to those languages for which we have stopwords and stemmers
stopword_languages = [
    ('danish', 'da'),
    ('dutch', 'nl'),
    ('english', 'en'), 
    ('finnish', 'fi'), 
    ('french', 'fr'), 
    ('german', 'de'), 
    ('hungarian', 'hu'), 
    ('italian', 'it'), 
    ('norwegian', 'no'),
    ('portuguese', 'pt'), 
    ('russian', 'ru'), 
    ('spanish', 'es'), 
    ('swedish', 'sv')
]

stopword_sets = {}  # language code -> set()
stemmers = {}       # language code -> stemmer

bonus_stopwords = {
    'fr': ['les']
}

for (lang_name, lang_code) in stopword_languages:
    stopword_sets[lang_code] = set(stopwords.words(lang_name))  
    stopword_sets[lang_code].update(['via', 'rt', 'thru'])
    try:
        stopword_sets[lang_code].update(bonus_stopwords[lang_code])
    except KeyError:
        pass
    stemmers[lang_code] = SnowballStemmer(lang_name)


# single letters, all punctuation/numbers, or usermention
_re_stoplist = re.compile(r'^([a-z]|[%s\d]+)$' % string.punctuation)

# match urls
_re_url = re.compile(r'http[^ ]+', re.I)
 
# match clause delimiters
_re_clause = re.compile(r'[.?!:;,"\r\n]')

# user mentions and hashtags
_re_entity = re.compile(r'(@\w{1,15}|#\w{1,15})')

# punctuation except '@'
_re_punctuation = re.compile(r'[%s]+' % string.punctuation.replace('@', ''))

# extra space
_re_extraspace = re.compile(r'( )+')

# htmlparser
_htmlparser = HTMLParser.HTMLParser()

def get_stopwords(language='en'):
    """Return the stopwords for language"""
    if not language in stopword_sets:
        raise Exception('Unknown language "%s"' % language)
    return stopword_sets[language]
   
def get_stemmer(language='en'):
    """Return the stemmer for language"""
    if not language in stemmers:
        raise Exception('Unknown language "%s"' % language)
    return stemmers[language]
    
def normalize(s):
    """Return normalized version of string."""
    # s = s.encode('ascii', 'replace').replace('?', '').lower() # doesn't treat non-English very well.
    s = filter(lambda x: unicodedata.category(x)[0] != 'C',s.lower()) # assumes we're not dealing with any CJKV languages
    norm = ''
    for item in _re_entity.split(s):
        if _re_entity.match(item):
            if item.startswith('@'):
                norm += item
            else:
                norm += item[1:]
        else:
            norm += _re_punctuation.sub(' ', item)

    return _re_extraspace.sub(' ', norm).strip()

def tokenize(s):
    """
    Get tokens from string
    @return     list of lists
    """
    tokens = []
    
    s = _re_url.sub(' . ', s)
    s = _htmlparser.unescape(s)
    
    for clause in _re_clause.split(s):
        items = normalize(clause).strip().split()
        if items:
            tokens.append(items)    
    return tokens

def is_all_numbers_and_punctuation_in_unicode(token):
    # the _re_stoplist regex doesn't take unicode into account
    categories = set()
    for x in token:
        categories.add(unicodedata.category(x)[0])
    return (not "L" in categories)
    
def stoplist(token, stopwords):
    """Return True if token should be stoplisted."""
    return len(token) <= 1 or _re_stoplist.match(token) or token in stopwords or is_all_numbers_and_punctuation_in_unicode(token)
    
def stoplist_iter(it, stopwords):
    """Return True if any element should be stoplisted."""
    return any(map(lambda x: stoplist(x, stopwords), it))
        
def stems_from_grams(grams, stemmer):
    """Get list of stems from grams using stemmer"""
    stems = []
    for g in grams:
        stems.append(
            tuple([w if w.startswith('@') else stemmer.stem(w) for w in g])
        )
    return stems

            
    

    
    