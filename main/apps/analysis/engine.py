import re
import json
from collections import Counter

STOP_WORDS = set(['de','la','el','en','y','a','los','las','un','una','es','se','del',
                   'que','con','por','para','como','su','al','lo','le','más','ya',
                   'si','no','pero','o','porque','cuando','todo','esta','son','fue'])

def analyze(text: str) -> dict:
    clean = re.sub(r'<[^>]+>', ' ', text)
    words = re.findall(r'\b[a-záéíóúüñ]+\b', clean.lower())
    sentences = [s.strip() for s in re.split(r'[.!?]+', clean) if s.strip()]
    paragraphs = [p.strip() for p in clean.split('\n\n') if p.strip()]

    unique = set(words)
    passive_re = re.compile(r'\b(fue|era|es|son|fueron|siendo|sido|ha sido|han sido)\s+\w+[da]o?\b', re.I)
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
        'passive_voice_count': len(passive_re.findall(clean)),
        'long_sentences': len(long_sents),
        'top_words_json': json.dumps(top),
    }
