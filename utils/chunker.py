import re
def chunk_text(tf_text: str, max_chars: int = 1500) -> list:
    """
    Splits the Terraform text into chunks containing full variable blocks.
    Groups 1–3 variable blocks per chunk without exceeding max_chars.
    """
    # Find all variable blocks
    variable_blocks = re.findall(r'(variable\s+".+?"\s*\{[^}]+\})', tf_text, re.DOTALL)
    chunks = []
    current_chunk = ""
    for block in variable_blocks:
        block = block.strip()
        # Check if adding this block would exceed the limit
        if len(current_chunk) + len(block) > max_chars:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = block
        else:
            current_chunk += "\n\n" + block

    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks