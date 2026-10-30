"""Linguistic features. TEXT-ONLY: visual/presentation preferences are deliberately not features
(CLAUDE.md: visual accessibility is a separate presentation layer, not an NLP diagnosis)."""
import re

from ML.context import sentence_around, split_sentences


def linguistic_features(text):
    if any(0x900<=ord(c)<=0x97f or 0xb80<=ord(c)<=0xbff or 0xc80<=ord(c)<=0xcff for c in text):
        import regex
        tokens=regex.findall(r"[\p{L}\p{M}\p{N}]+",text)
    else:tokens = re.findall(r"\b[\w'-]+\b", text)
    n = len(tokens)
    chars = len(text)
    sentences = max(1, len(re.findall(r"[.!?।॥]+", text)))
    long_words = sum(len(t) >= 7 for t in tokens)
    return {
        "token_count": n,
        "character_count": chars,
        "avg_token_length": sum(map(len, tokens)) / max(n, 1),
        "long_word_ratio": long_words / max(n, 1),
        "punctuation_count": len(re.findall(r"[,;:!?]", text)),
        "sentence_count": sentences,
        "chars_per_sentence": chars / sentences,
    }


FEATURE_NAMES = [
    "span_token_count", "span_char_count", "span_avg_token_len", "span_long_word_ratio",
    "span_punct_count", "sent_token_count", "sent_long_word_ratio", "sent_punct_count",
    "context_sentence_count", "context_chars_per_sentence",
]


def span_context_features(span, context_before="", context_after=""):
    """Fixed-order feature vector (list of floats) aligned with FEATURE_NAMES."""
    sp = linguistic_features(span)
    sent = linguistic_features(sentence_around(context_before or "", span, context_after or ""))
    ctx = f"{context_before or ''} {span} {context_after or ''}".strip()
    n_sent = max(1, len(split_sentences(ctx)))
    return [float(sp["token_count"]), float(sp["character_count"]), sp["avg_token_length"],
            sp["long_word_ratio"], float(sp["punctuation_count"]),
            float(sent["token_count"]), sent["long_word_ratio"], float(sent["punctuation_count"]),
            float(n_sent), len(ctx) / n_sent]
