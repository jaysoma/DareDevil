#!/usr/bin/env python3
"""Brief 22's who-it's-for cues, on a phrase in a recogniser's form (lowercase words, apostrophes kept, no punctuation).
Each is 0 or 1. Fixed rules, chosen before any scoring and not tuned on any result:

  vocative       the phrase opens with a person's name, after at most one opener (hey, hi, ok, okay, oh, well, so,
                 and, now): "dave can you ..."; names from NLTK's names corpus, minus those that are also common English
                 words (lowercase Brown count >= COMMON: will, may, bill, ...) and minus device wake words (olly, alexa)
  you            'you' or 'your' (and contractions) addressing someone, after removing fillers that don't address:
                 you know, you see, you mean, thank you, mind you
  first_person   first-person narration of a plan: i'll, i will, i'm going to, i am going to, i'm gonna, we'll,
                 we're going to, we are going to
  past_reported  past tense or reported speech: i was going to, was, were, had, did, said, told, asked, wanted,
                 thought, forgot, went, used to
  bare_imperative the phrase opens (after at most one of please, hey, ok, okay, now, just, so, and, well) with a verb
                 from IMPERATIVE, with no addressee: neither 'you' nor a vocative fires. A first person later in the
                 phrase doesn't block it ("text sam i'll be home tomorrow" is a bare imperative carrying a message)

The names list and Brown counts are loaded by init(sources_dir) once.
"""
import re
import zipfile
from collections import Counter
from pathlib import Path

NAMES = set()
WAKE = {'olly', 'alexa', 'siri', 'google', 'cortana', 'computer'}
COMMON = 20
OPEN_V = {'hey', 'hi', 'ok', 'okay', 'oh', 'well', 'so', 'and', 'now'}
OPEN_I = {'please', 'hey', 'ok', 'okay', 'now', 'just', 'so', 'and', 'well'}
IMPERATIVE = set("""set send text email play turn remind call add tell start book order find show give wake post dim make
put cancel delete remove schedule get check read open stop switch create look search go try take hold let keep bring
buy pick write change move use ask help wait listen watch follow note save mute pause resume skip repeat increase
decrease lower raise navigate drive direct share tweet message""".split())
FILLERS = re.compile(r"\byou know\b|\byou see\b|\byou mean\b|\bthank you\b|\bmind you\b")
YOU = re.compile(r"\b(you|your|yours|yourself|you're|you'll|you've|you'd)\b")
FIRST = re.compile(r"\b(i'll|i will|i'm going to|i am going to|i'm gonna|we'll|we're going to|we are going to)\b")
PAST = re.compile(r"\b(i was going to|was|were|had|did|said|told|asked|wanted|thought|forgot|went|used to)\b")
CUES = ['vocative', 'you', 'first_person', 'past_reported', 'bare_imperative']


def init(src):
    """Load NLTK's names (minus common words and wake words)."""
    if NAMES:
        return
    src = Path(src)
    z = zipfile.ZipFile(src / 'nltk' / 'names.zip')
    names = set()
    for n in z.namelist():
        if n.endswith('.txt'):
            names |= {w.strip().lower() for w in z.read(n).decode('utf-8', 'replace').splitlines() if w.strip()}
    b = zipfile.ZipFile(src / 'nltk' / 'brown.zip')
    cnt = Counter()
    for n in b.namelist():
        if n.startswith('brown/c') and len(Path(n).name) == 4:
            for t in b.read(n).decode('utf-8', 'replace').split():
                w = t.rsplit('/', 1)[0]
                if w.islower():                      # only uses as an ordinary word: 'will', not 'Will'
                    cnt[w] += 1
    NAMES.update(w for w in names if cnt[w] < COMMON and w not in WAKE and w.isalpha())


def cues(text):
    w = text.split()
    out = dict.fromkeys(CUES, 0)
    if not w:
        return out
    k = 1 if len(w) > 1 and w[0] in OPEN_V else 0
    out['vocative'] = int(len(w) > k + 1 and w[k] in NAMES)
    out['you'] = int(bool(YOU.search(FILLERS.sub(' ', text))))
    out['first_person'] = int(bool(FIRST.search(text)))
    out['past_reported'] = int(bool(PAST.search(text)))
    j = 1 if len(w) > 1 and w[0] in OPEN_I else 0
    out['bare_imperative'] = int(w[j] in IMPERATIVE and not out['you'] and not out['vocative'])
    return out
