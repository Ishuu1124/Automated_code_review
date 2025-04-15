from retriever.simple_rag import run_simple_rag
from evaluator.scorer import score_response, answer_length, keyword_overlap

def load_prompts(filepath="prompts/query_prompts.txt"):
    with open(filepath, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]
    

def evaluate_tf_file(tf_path):
    print(f"\nEvaluating file: {tf_path}")
    print("=" * 40)

    simple_answer = run_simple_rag(tf_path)

    print("\n--- Simple RAG ---")
    print(simple_answer)

    print("\n--- Metrics ---")
    print(f"Score: {score_response(tf_path, simple_answer):.2f}")
    print(f"Length: {answer_length(simple_answer)} tokens")
    print(f"Keyword Overlap: {keyword_overlap(tf_path, simple_answer):.2f}")

if __name__ == "__main__":
    evaluate_tf_file("sample_tf/variables.tf")