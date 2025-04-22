import re

def count_tokens(text: str) -> int:
    return len(re.findall(r"\S+", text))  

def chunk_text(text: str, max_tokens: int = 200) -> list:
    words = re.findall(r"\S+", text)
    chunks = []
    for i in range(0, len(words), max_tokens):
        chunk = " ".join(words[i:i + max_tokens])
        chunks.append(chunk)
    return chunks