"""
Tokenisation shared by the index builder and the front end.

The browser has to tokenise a query exactly the way the build tokenised the
corpus, or terms simply will not match. This module is the Python half of that
contract; `assets/search.js` mirrors it, and any change here needs the same
change there.

Rules, deliberately simple:
  * lowercase
  * split on anything that is not a letter or digit
  * drop tokens longer than 24 characters, and single characters unless
    they are digits ("Lecture 5", "Unit 3" are real queries here)
  * drop stopwords

No stemming in v1. Prefix expansion on the last query term covers most of what
stemming would buy for as-you-type search, without the false matches a stemmer
introduces on technical vocabulary ("routing" -> "rout").
"""

import re

TOKEN_RE = re.compile(r"[a-z0-9]+")

MIN_TOKEN_LEN = 2

# Nothing anyone searches for is this long. The cap discards the binary dumps
# and DNA strings that appear in algorithm worked-examples - 318 terms in this
# corpus, e.g. "00111110011011010000000000000000".
MAX_TOKEN_LEN = 24

# Common English words, plus a few that appear in almost every document here and
# so carry no signal. Course vocabulary ("lecture", "chapter", "unit") is
# deliberately NOT included - "lecture 5" is a query people actually type.
STOPWORDS = frozenset(
    """
a about above after again against all am an and any are as at
be because been before being below between both but by
can cannot could did do does doing down during
each few for from further
had has have having he her here hers herself him himself his how
i if in into is it its itself
let me more most my myself
no nor not of off on once only or other ought our ours ourselves out over own
same she should so some such
than that the their theirs them themselves then there these they this those
through to too
under until up very was we were what when where which while who whom why with
would you your yours yourself yourselves
""".split()
)


def tokenize(text: str) -> list:
    """Split text into index terms."""
    if not text:
        return []
    kept = []
    for token in TOKEN_RE.findall(text.lower()):
        if len(token) > MAX_TOKEN_LEN or token in STOPWORDS:
            continue
        # A lone digit carries meaning here - "Lecture 5", "Unit 3", "Lab 2" -
        # whereas a lone letter never does. Dropping both made "lecture 5"
        # silently collapse into "lecture" and rank Lecture_9 above Lecture_5.
        if len(token) < MIN_TOKEN_LEN and not token.isdigit():
            continue
        kept.append(token)
    return kept


def path_tokens(rel: str) -> list:
    """Terms derived from a file's location and name.

    These get indexed as a separate high-weight field, which is what makes
    `4thSem/DAA/Material/DP/DP_rod_cut.pdf` findable by "DAA DP" even though no
    page inside it necessarily says either word.
    """
    return tokenize(rel.replace("/", " ").replace(".", " "))
