import sys
import os
import re
import string
import nltk
from nltk.corpus import stopwords
from nltk.stem.snowball import PorterStemmer

_stopwords = set(stopwords.words('english'))
_stopwords.update(['via', 'rt'])

# single letters, or all punctuation/numbers
_re_stoplist = re.compile(r'^([a-z]|[%s\d]+)$' % string.punctuation)

# match urls
_re_url = re.compile(r'http[^ ]+', re.I)
 
# match clause delimiters
_re_clause = re.compile(r'[.?!:;,"\r\n]')

# punctuation except '@'
_re_punctuation = re.compile(r'[%s]+' % string.punctuation.replace('@', ''))

# maximum gram degree (e.g. 2 = bigrams)
_ngram_degree = 2

# stemmer
_stemmer = PorterStemmer()

def normalize(s):
    """Return normalized version of string."""
    s = s.encode('ascii', 'replace').replace('?', '').lower()
    s = _re_punctuation.sub(' ', s)
    return s.strip()

def stoplist_iter(it, stopwords):
    """Return True if any element should be stoplisted."""
    return any(map(lambda x: _re_stoplist.match(x) or x in stopwords, it))

def grams_from_string(s, stopwords=None):
    """Get list of grams from string"""
    stopwords = stopwords or _stopwords
    grams = []
    no_url = _re_url.sub(' . ', s)

    for clause in _re_clause.split(no_url):
        tokens = normalize(clause).split()
        if tokens:
            for n in range(1, _ngram_degree+1):
                for g in nltk.ngrams(tokens, n):
                    if not stoplist_iter(g, stopwords):
                        grams.append(g)
    return grams

def stems_from_grams(grams):
    """Get list of stems from grams"""
    stems = []
    for g in grams:
        stems.append(
            tuple([w if w.startswith('@') else _stemmer.stem(w) for w in g])
        )
    return stems

              

            
    

    
    