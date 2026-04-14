import logging

from langchain_core.tools import tool


logger = logging.getLogger(__name__)

@tool
def compute_text_stats(text: str) -> str:
    """Compute word count, sentence count, and character count for the given text."""
    
    logger.info("[Tool calling] commpute_text_stats called with text of length %d", len(text))
    
    word_count = len(text.split())
    char_count = len(text)
    sentence_count = text.count('.') + text.count('!') + text.count('?')
    return (
        f"Text statistics:\n"
        f"- Words: {word_count}\n"
        f"- Characters: {char_count}\n"
        f"- Sentences: {sentence_count}"
    )
