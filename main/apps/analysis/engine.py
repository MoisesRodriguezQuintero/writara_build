import re
import json
from collections import Counter

from main.utils import html_to_text

STOP_WORDS = set(['de','la','el','en','y','a','los','las','un','una','es','se','del',
                   'que','con','por','para','como','su','al','lo','le','más','ya',
                   'si','no','pero','o','porque','cuando','todo','esta','son','fue'])

WORD_RE = re.compile(r"[^\W\d_]+")
# Voz pasiva: ser + participio (regular -ado/-ido o irregular común), con género y número
_IRREGULAR_PARTICIPLES = 'escrit|hech|dich|vist|puest|abiert|rot|muert|vuelt|cubiert|resuelt|impres|descrit'
PASSIVE_RE = re.compile(
    r'\b(?:fue|era|es|son|fueron|eran|siendo|sido|ha sido|han sido|será|serán)\s+'
    r'(?:\w{2,}(?:ad|id)|' + _IRREGULAR_PARTICIPLES + r')[oa]s?\b',
    re.I,
)


def analyze(text: str) -> dict:
    # Los párrafos salen de los bloques HTML (<p>, <h1>, <li>…), no de "\n\n"
    clean = html_to_text(text, keep_breaks=False)
    words = WORD_RE.findall(clean.lower())
    sentences = [s.strip() for s in re.split(r'[.!?]+', clean) if s.strip()]
    paragraphs = [p.strip() for p in clean.split('\n') if p.strip()]

    unique = set(words)
    long_sents = [s for s in sentences if len(s.split()) > 30]
    content_words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
    top = Counter(content_words).most_common(30)

    return {
        'word_count': len(words),
        'sentence_count': len(sentences),
        'paragraph_count': len(paragraphs),
        'unique_words': len(unique),
        'lexical_density': round(len(unique)/len(words), 3) if words else 0,
        'avg_sentence_length': round(len(words)/len(sentences), 1) if sentences else 0,
        'avg_word_length': round(sum(len(w) for w in words)/len(words), 1) if words else 0,
        'estimated_read_min': max(1, len(words)//200),
        'passive_voice_count': len(PASSIVE_RE.findall(clean)),
        'long_sentences': len(long_sents),
        'top_words_json': json.dumps(top),
    }
