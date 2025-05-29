import re

def chunk_text(file_text: str, max_chars: int = 1500, file_type: str = 'tf') -> list:
    """Splits the text into chunks, and tracks line numbers for .tf files."""
    if file_type == 'tf':
        lines = file_text.splitlines(keepends=True)
        chunks = []
        current_chunk_lines = []
        current_chunk_length = 0
        current_start_line = None
        inside_block = False
        brace_count = 0

        for idx, line in enumerate(lines):
            if not inside_block and re.match(r'^\s*variable\s+"[^"]+"\s*\{', line):
                inside_block = True
                brace_count = line.count('{') - line.count('}')
                current_chunk_lines = [line]
                current_chunk_length = len(line)
                current_start_line = idx + 1  # GitHub line numbers start at 1
                continue

            if inside_block:
                current_chunk_lines.append(line)
                current_chunk_length += len(line)
                brace_count += line.count('{') - line.count('}')
                
                if brace_count == 0:
                    block_text = ''.join(current_chunk_lines).strip()
                    # Extract variable names and their line numbers in this block
                    var_line_map = {}
                    for offset, block_line in enumerate(current_chunk_lines):
                        match = re.match(r'^\s*variable\s+"([^"]+)"', block_line)
                        if match:
                            var_name = match.group(1)
                            var_line_map[var_name] = current_start_line + offset

                    if not chunks or len(chunks[-1]['chunk']) + len(block_text) > max_chars:
                        chunks.append({
                            'chunk': block_text,
                            'start_line': current_start_line,
                            'var_line_map': var_line_map
                        })
                    else:
                        # Merge with previous chunk
                        prev = chunks.pop()
                        merged_text = prev['chunk'] + "\n\n" + block_text
                        # Merge var_line_maps, adjusting offset for merged block
                        merged_map = prev['var_line_map'].copy()
                        merged_map.update(var_line_map)
                        chunks.append({
                            'chunk': merged_text,
                            'start_line': prev['start_line'],
                            'var_line_map': merged_map
                        })
                    inside_block = False
                    current_chunk_lines = []
                    current_chunk_length = 0
                    current_start_line = None

        return chunks

    else:
        # Hybrid chunking for .txt files (using paragraphs + sentences fallback strategy)
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
                    if current_chunk:
                        current_chunk += "\n\n" + para
                    else:
                        current_chunk = para

        if current_chunk:
            chunks.append(current_chunk.strip())
        return chunks