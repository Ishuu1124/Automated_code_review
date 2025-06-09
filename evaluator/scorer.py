from sentence_transformers import SentenceTransformer, util

embedder = SentenceTransformer("all-MiniLM-L6-v2")


def score_response(query: str, response: str) -> float:
    query_emb = embedder.encode(query, convert_to_tensor=True)
    response_emb = embedder.encode(response, convert_to_tensor=True)
    similarity = util.pytorch_cos_sim(query_emb, response_emb)[0].item()
    return round(similarity, 4)


def answer_length(response: str) -> int:
    return len(response.split())


def keyword_overlap(query: str, response: str) -> float:
    query_tokens = set(query.lower().split())
    answer_tokens = set(response.lower().split())
    common = query_tokens.intersection(answer_tokens)
    return round(len(common) / len(query_tokens), 4)
