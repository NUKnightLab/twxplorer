import sys
import os
import re
import string
import HTMLParser
import nltk
from nltk.corpus import stopwords
from nltk import SnowballStemmer

# available languages (languages, ISO 639-1 code)
# ref: http://en.wikipedia.org/wiki/List_of_ISO_639-1_codes
# restricted to those languages for which we have stopwords and stemmers
stopword_languages = {
    'danish': 'da',
    'dutch': 'nl',
    'english': 'en', 
    'finnish': 'fi', 
    'french': 'fr', 
    'german': 'de', 
    'hungarian': 'hu', 
    'italian': 'it', 
    'norwegian': 'no',
    'portuguese': 'pt', 
    'russian': 'ru', 
    'spanish': 'es', 
    'swedish': 'sv'
}


stopword_sets = {} # language code -> set()
stemmers = {} # language code -> stemmer

for k, v in stopword_languages.iteritems():
    stopword_sets[v] = set(stopwords.words(k))  
    stopword_sets[v].update(['via', 'rt', 'thru'])   
    stemmers[v] = SnowballStemmer(k)

# single letters, or all punctuation/numbers
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

# maximum gram degree (e.g. 2 = bigrams)
_ngram_degree = 2

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
    s = s.encode('ascii', 'replace').replace('?', '').lower()
    
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

def stoplist_iter(it, stopwords):
    """Return True if any element should be stoplisted."""
    return any(map(lambda x: _re_stoplist.match(x) or x in stopwords, it))

def grams_from_string(s, stopwords):
    """Get list of grams from string"""
    grams = []
    
    s = _re_url.sub(' . ', s)
    s = _htmlparser.unescape(s)

    for clause in _re_clause.split(s):
        tokens = normalize(clause).split()
        if tokens:
            for n in range(1, _ngram_degree+1):
                for g in nltk.ngrams(tokens, n):
                    if not stoplist_iter(g, stopwords):
                        grams.append(g)
    return grams

def stems_from_grams(grams, stemmer):
    """Get list of stems from grams using stemmer"""
    stems = []
    for g in grams:
        stems.append(
            tuple([w if w.startswith('@') else stemmer.stem(w) for w in g])
        )
    return stems

              

            
    

    
    