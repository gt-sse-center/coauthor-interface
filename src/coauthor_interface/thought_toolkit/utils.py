import re
from datetime import datetime

import spacy

# To install the spaCy library, run the following command in your terminal:
# pip install spacy

# To download the medium-sized English language model, run the following command in your terminal:
# python -m spacy download en_core_web_md

nlp = spacy.load("en_core_web_md")


def sent_tokenize(text):
    # Normalize multiple whitespace to single spaces
    text = re.sub(r"\s+", " ", text.strip())
    # Pattern looks for sentence boundaries
    pattern = r"([.?!]+)(?=\s|$)"
    # Split using the above pattern (text and its punctuation at the end)
    pieces = re.split(pattern, text)

    # Reconstruct sentences by pairing each text chunk with its trailing punctuation
    sentences = []
    for i in range(0, len(pieces), 2):
        sentence = pieces[i].strip()
        if i + 1 < len(pieces):
            sentence += pieces[i + 1]
        if sentence:
            sentences.append(sentence.strip())

    return sentences


def get_spacy_similarity(text1, text2, nouns_only=False):
    if nouns_only:
        doc1 = nlp(" ".join([str(t) for t in nlp(text1) if t.pos_ in ["NOUN", "PROPN"]]))
        doc2 = nlp(" ".join([str(t) for t in nlp(text2) if t.pos_ in ["NOUN", "PROPN"]]))
    else:
        doc1 = nlp(" ".join([str(t) for t in nlp(text1) if not t.is_stop]))
        doc2 = nlp(" ".join([str(t) for t in nlp(text2) if not t.is_stop]))

    if len(doc1) == 0 or len(doc2) == 0:
        return 0

    return doc1.similarity(doc2)


def get_timestamp(timestamp):
    real_timestamp = int(timestamp / 1000)
    return datetime.fromtimestamp(real_timestamp)


def convert_timestamp_to_string(timestamp):
    return timestamp.strftime("%Y/%m/%d %H:%M:%S")


def convert_string_to_timestamp(date_string):
    return datetime.strptime(date_string, "%Y/%m/%d %H:%M:%S")


def custom_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")
