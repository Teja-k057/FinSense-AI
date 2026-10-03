import re
import html

class TextCleaner:
    """Sanitizes unstructured text while preserving critical financial indicators."""

    @staticmethod
    def clean(text: str) -> str:
        if not text:
            return ""

        # Unescape HTML entities
        text = html.unescape(text)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Remove URLs
        text = re.sub(r"https?://\S+|www\.\S+", "", text)

        # Expand financial contractions
        # Handle 2-digit years: Q1'24 -> Q1 2024
        text = re.sub(r"\bQ([1-4])['’]?(\d{2})\b", r"Q\1 20\2", text, flags=re.IGNORECASE)
        # Handle 4-digit years: Q1'2024 -> Q1 2024
        text = re.sub(r"\bQ([1-4])['’]?(\d{4})\b", r"Q\1 \2", text, flags=re.IGNORECASE)
        
        # FY24 -> Fiscal Year 2024
        text = re.sub(r"\bFY['’]?(\d{2})\b", r"Fiscal Year 20\1", text, flags=re.IGNORECASE)
        text = re.sub(r"\bFY['’]?(\d{4})\b", r"Fiscal Year \1", text, flags=re.IGNORECASE)

        # Metric acronyms
        text = re.sub(r"\bbps\b", "basis points", text, flags=re.IGNORECASE)
        text = re.sub(r"\byoy\b", "year over year", text, flags=re.IGNORECASE)
        text = re.sub(r"\bqoq\b", "quarter over quarter", text, flags=re.IGNORECASE)

        # Remove extraneous whitespace
        text = re.sub(r"\s+", " ", text).strip()
        return text
