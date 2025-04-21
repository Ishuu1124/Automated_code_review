import tiktoken
# Function to count tokens in a text using a specific model
def count_tokens(text, model_name="gpt-3.5-turbo"):
    encoding = tiktoken.encoding_for_model(model_name)
    return len(encoding.encode(text))
# Function to chunk text based on max_tokens
def chunk_text(text, max_tokens=100, model_name="gpt-3.5-turbo"):
    encoding = tiktoken.encoding_for_model(model_name)
    tokens = encoding.encode(text)
    chunks = []
    # Break the tokens into chunks of size max_tokens
    for i in range(0, len(tokens), max_tokens):
        chunk_tokens = tokens[i:i + max_tokens]
        chunk = encoding.decode(chunk_tokens)
        chunks.append(chunk)
    return chunks



# import re

# def chunk_text(text, max_chunk_size=500, overlap=50):
#     """
#     Splits the input text into chunks of approximately `max_chunk_size` characters, with an optional `overlap` of characters between chunks to preserve context.
#     """
#     sentences = re.split(r'(?<=[.;}\n])\s+', text)
#     chunks = []
#     current_chunk = []

#     total_len = 0
#     for sentence in sentences:
#         sentence_len = len(sentence)
#         if total_len + sentence_len > max_chunk_size:
#             chunks.append(" ".join(current_chunk))
#             if overlap > 0:
#                 overlap_tokens = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
#                 current_chunk = overlap_tokens + [sentence]
#             else:
#                 current_chunk = [sentence]
#             total_len = sum(len(s) for s in current_chunk)
#         else:
#             current_chunk.append(sentence)
#             total_len += sentence_len

#     if current_chunk:
#         chunks.append(" ".join(current_chunk))

#     return [chunk.strip() for chunk in chunks if chunk.strip()]