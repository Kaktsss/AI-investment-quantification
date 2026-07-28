"""
HTML -> cleaned text -> paragraph-sized chunks.

Replaces edgar_downloader.py's original download_text(), whose one-pass
`re.sub(r"\\s+", " ", text)` collapsed newlines along with spaces and
destroyed paragraph boundaries. Chunk boundaries matter here because
Tier 2 scores individual chunks, not whole filings.
"""

import logging
import re
import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

import config

logger = logging.getLogger("pillar_c.text_chunking")

# SEC 10-Ks are iXBRL: valid XHTML that opens with an <?xml ...?> declaration.
# bs4 flags that as "looks like XML" even though the lxml HTML parser handles
# it correctly - this warning would otherwise fire on every filing.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_MULTI_NEWLINE = re.compile(r"\n{2,}")
_WHITESPACE = re.compile(r"\s+")
_ALPHA = re.compile(r"[A-Za-z]")


def clean_html_to_paragraphs(html: str) -> list:
    """Parses filing HTML into a list of cleaned, whitespace-normalized paragraphs."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "table"]):
        tag.decompose()

    raw_text = soup.get_text(separator="\n")
    raw_text = _MULTI_NEWLINE.sub("\n\n", raw_text)

    paragraphs = []
    for para in raw_text.split("\n\n"):
        normalized = _WHITESPACE.sub(" ", para).strip()
        if normalized:
            paragraphs.append(normalized)
    return paragraphs


def _is_boilerplate(paragraph: str) -> bool:
    word_count = len(paragraph.split())
    if word_count < config.MIN_PARAGRAPH_WORDS:
        return True
    alpha_chars = len(_ALPHA.findall(paragraph))
    if alpha_chars / max(len(paragraph), 1) < config.MIN_ALPHA_FRACTION:
        return True
    return False


def _pack_paragraph(paragraph: str) -> list:
    """Splits one oversized paragraph into sentence-packed sub-chunks."""
    words = paragraph.split()
    if len(words) <= config.CHUNK_TARGET_WORDS:
        return [paragraph]

    sentences = _SENTENCE_SPLIT.split(paragraph)
    chunks = []
    buffer = []
    buffer_words = 0

    for sentence in sentences:
        sentence_words = sentence.split()
        n = len(sentence_words)

        if n > config.CHUNK_TARGET_WORDS:
            # Single sentence longer than the whole budget (rare legal run-on):
            # hard-split at the word boundary nearest the target.
            if buffer:
                chunks.append(" ".join(buffer))
                buffer, buffer_words = [], 0
            logger.debug("Hard-splitting oversized sentence (%d words)", n)
            for i in range(0, n, config.CHUNK_TARGET_WORDS):
                chunks.append(" ".join(sentence_words[i : i + config.CHUNK_TARGET_WORDS]))
            continue

        if buffer_words + n > config.CHUNK_TARGET_WORDS and buffer:
            chunks.append(" ".join(buffer))
            buffer, buffer_words = [], 0

        buffer.append(sentence)
        buffer_words += n

    if buffer:
        chunks.append(" ".join(buffer))

    # Tail-merge: a small final sub-chunk gets folded into its predecessor
    # rather than left as a near-empty standalone chunk.
    if len(chunks) >= 2:
        last_words = len(chunks[-1].split())
        prev_words = len(chunks[-2].split())
        if (
            last_words < config.MIN_CHUNK_WORDS
            and prev_words + last_words <= config.CHUNK_TARGET_WORDS * config.TAIL_MERGE_CEILING
        ):
            merged = chunks[-2] + " " + chunks[-1]
            chunks = chunks[:-2] + [merged]

    return chunks


def chunk_filing_text(html: str) -> list:
    """
    Full pipeline: HTML -> paragraphs -> boilerplate filtering -> packed chunks.
    Returns a list of {"text": str, "word_count": int}.
    """
    paragraphs = clean_html_to_paragraphs(html)
    chunks = []
    for paragraph in paragraphs:
        if _is_boilerplate(paragraph):
            continue
        for chunk_text in _pack_paragraph(paragraph):
            chunks.append({"text": chunk_text, "word_count": len(chunk_text.split())})
    return chunks
