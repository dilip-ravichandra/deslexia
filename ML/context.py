"""Context builder: locate the learner's selected span and cut the surrounding context.

Pure text handling. Visual/presentation settings are never an input here.
"""
import re

_SENT_END = re.compile(r'(?<=[.!?])\s+(?=[A-Z0-9"\'(\[])')
MAX_SPAN_CHARS = 300
MAX_TEXT_CHARS = 5000


def codepoint_offset(text, offset, unit='codepoint'):
    """Convert the declared browser wire convention; never guess an occurrence."""
    if offset is None or unit == 'codepoint':
        return offset
    if unit != 'utf16' or offset < 0:
        raise ValueError('Unsupported selection offset.')
    count = 0
    for index, char in enumerate(text):
        if count == offset:
            return index
        count += 2 if ord(char) > 0xffff else 1
        if count > offset:
            raise ValueError('Selection offset splits a Unicode character.')
    if count == offset:
        return len(text)
    raise ValueError('Selection offset is outside the text.')


def split_sentences(text):
    value=(text or '').strip()
    if re.search(r'[\u0900-\u097f\u0b80-\u0bff\u0c80-\u0cff]',value):return [s for s in re.split(r'(?<=[.!?।॥])\s+',value) if s]
    return [s for s in _SENT_END.split(value) if s]


def locate_span(text, span, span_start=None):
    """Return (start, end). Uses span_start if given and valid, else the first occurrence."""
    if not span or not span.strip():
        raise ValueError("span is empty")
    if span_start is not None:
        if text[span_start:span_start + len(span)] != span:
            raise ValueError("span does not match the text at span_start")
        return span_start, span_start + len(span)
    i = text.find(span)
    if i < 0:
        raise ValueError("span not found in text")
    return i, i + len(span)


def sentence_around(before, span, after):
    """The sentence containing the span, cut from the surrounding context."""
    ends = [m.end() for m in re.finditer(r"[.!?।॥]\s+", before)]
    tail = before[ends[-1]:] if ends else before
    m = re.search(r"[.!?।॥]", after)
    head = "" if re.search(r"[.!?।॥]\s*$", span) else after[:m.end()] if m else after
    return (tail + span + head).strip()


def span_offset_in_sentence(before, span, after):
    """Offset of the selected occurrence, even when the sentence repeats a word."""
    ends = [m.end() for m in re.finditer(r"[.!?।॥]\s+", before)]
    tail = before[ends[-1]:] if ends else before
    leading = len(tail + span) - len((tail + span).lstrip())
    return max(0, len(tail) - leading)


def build_context(text, span, span_start=None, window=1):
    """Return dict(context_before, span, context_after, sentence, span_start, span_end)."""
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"text longer than {MAX_TEXT_CHARS} characters")
    if len(span) > MAX_SPAN_CHARS:
        raise ValueError(f"span longer than {MAX_SPAN_CHARS} characters")
    s, e = locate_span(text, span, span_start)
    before, after = text[:s], text[e:]
    # keep `window` full sentences on each side of the sentence containing the span
    b_sents = split_sentences(before)
    a_sents = split_sentences(after)
    keep_b = " ".join(b_sents[-(window + 1):]) if b_sents else ""
    keep_a = " ".join(a_sents[:window + 1]) if a_sents else ""
    # Preserve boundaries adjacent to the selected span, including punctuation and
    # selections within a word. These strings are also used by linguistic features.
    if before and before[-1].isspace() and keep_b:
        keep_b = keep_b.rstrip() + " "
    if after and after[0].isspace() and keep_a:
        keep_a = " " + keep_a.lstrip()
    return {"context_before": keep_b if before.strip() else before,
            "span": span, "context_after": keep_a if after.strip() else after,
            "sentence": sentence_around(before, span, after),
            "span_start": s, "span_end": e}
