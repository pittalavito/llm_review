import re

TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_]+")


class BM25Tokenizer:
    @staticmethod
    def tokenize(text: str) -> list[str]:
        return [token.lower() for token in TOKEN_PATTERN.findall(text)]
