import re

def chunk_text(file_text: str, max_chars: int = 1500, file_type: str = 'tf') -> list:
    if file_type == 'tf':
        variable_blocks = re.findall(r'(variable\s+".+?"\s*\{[^}]*\})', file_text, re.DOTALL)
        chunks = []
        current_chunk = ""
        
        for block in variable_blocks:
            block = block.strip()
            if len(current_chunk) + len(block) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = block
            else:
                current_chunk += "\n\n" + block

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    else:
        paragraphs = file_text.split("\n\n")
        chunks = []
        current_chunk = ""

        def split_into_sentences(text):
            return re.split(r'(?<=[.!?])\s+', text)

        for para in paragraphs:
            para = para.strip()
            if len(para) > max_chars:
                sentences = split_into_sentences(para)
                sentence_chunk = ""
                for sentence in sentences:
                    if len(sentence_chunk) + len(sentence) > max_chars:
                        if sentence_chunk:
                            chunks.append(sentence_chunk.strip())
                        sentence_chunk = sentence
                    else:
                        sentence_chunk += " " + sentence

                if sentence_chunk:
                    chunks.append(sentence_chunk.strip())
            else:
                if len(current_chunk) + len(para) > max_chars:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    current_chunk += "\n\n" + para

        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks



# import re

# def chunk_text(file_text: str, max_chars: int = 1500, file_type: str = 'tf') -> list:
#     if file_type == 'tf':
#         variable_blocks = re.findall(r'(variable\s+".+?"\s*\{[^}]*\})', file_text, re.DOTALL)
#         chunks = []
#         current_chunk = ""
        
#         for block in variable_blocks:
#             block = block.strip()
#             if len(current_chunk) + len(block) > max_chars:
#                 if current_chunk:
#                     chunks.append(current_chunk.strip())
#                 current_chunk = block
#             else:
#                 current_chunk += "\n\n" + block

#         if current_chunk:
#             chunks.append(current_chunk.strip())

#         return chunks

#     else:
#         paragraphs = file_text.split("\n\n")
#         chunks = []
#         current_chunk = ""

#         def split_into_sentences(text):
#             return re.split(r'(?<=[.!?])\s+', text)

#         for para in paragraphs:
#             para = para.strip()
#             if len(para) > max_chars:
#                 sentences = split_into_sentences(para)
#                 sentence_chunk = ""
#                 for sentence in sentences:
#                     if len(sentence_chunk) + len(sentence) > max_chars:
#                         if sentence_chunk:
#                             chunks.append(sentence_chunk.strip())
#                         sentence_chunk = sentence
#                     else:
#                         sentence_chunk += " " + sentence

#                 if sentence_chunk:
#                     chunks.append(sentence_chunk.strip())
#             else:
#                 if len(current_chunk) + len(para) > max_chars:
#                     if current_chunk:
#                         chunks.append(current_chunk.strip())
#                     current_chunk = para
#                 else:
#                     current_chunk += "\n\n" + para

#         if current_chunk:
#             chunks.append(current_chunk.strip())
        
#         return chunks


