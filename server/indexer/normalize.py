"""
Text normalization utilities for The Library indexer.
"""

import re
import unicodedata
from typing import List

def normalize_text(text: str) -> str:
    """
    Normalize text for search indexing.
    - Remove excessive whitespace
    - Normalize Unicode characters
    - Preserve essential punctuation for quotes
    """
    if not text:
        return ""

    # Normalize Unicode to composed form
    text = unicodedata.normalize('NFC', text)

    # Replace multiple whitespace with single space
    text = re.sub(r'\s+', ' ', text)

    # Strip leading/trailing whitespace
    text = text.strip()

    return text

def extract_keywords(text: str) -> List[str]:
    """
    Extract meaningful keywords from text.
    Basic implementation for MVP - can be enhanced later.
    """
    if not text:
        return []

    # Simple keyword extraction
    # Remove common stop words and extract meaningful terms
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
        'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
        'could', 'can', 'may', 'might', 'must', 'shall', 'this', 'that',
        'these', 'those', 'from', 'up', 'down', 'out', 'off', 'over', 'under',
        'into', 'onto', 'through', 'during', 'before', 'after', 'above',
        'below', 'between', 'among', 'around', 'about', 'as', 'like'
    }

    # Extract words (3+ characters)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

    # Filter out stop words
    keywords = [word for word in words if word not in stop_words]

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)

    return unique_keywords[:20]  # Limit to 20 keywords

def clean_quote_text(quote: str) -> str:
    """
    Clean quote text while preserving meaning and searchability.
    """
    if not quote:
        return ""

    # Normalize text
    quote = normalize_text(quote)

    # Remove excessive punctuation but preserve essential quotes and periods
    quote = re.sub(r'[^\w\s\'".,;:!?()-]', '', quote)

    # Ensure quotes don't start/end with punctuation (except quotes)
    quote = re.sub(r'^[.,;:!?()-]+', '', quote)
    quote = re.sub(r'[.,;:!?()-]+$', '', quote)

    return quote.strip()

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe processing.
    """
    if not filename:
        return ""

    # Remove or replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove excessive spaces
    filename = re.sub(r'\s+', ' ', filename)

    return filename.strip()