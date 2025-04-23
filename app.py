import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from retriever.simple_rag import run_simple_rag
from evaluator.scorer import score_response, answer_length, keyword_overlap
import glob
from ghub import evaluate_tf_from_github

def evaluate_multiple_tf_files(tf_folder):
    tf_paths = glob.glob(f"{tf_folder}/*.tf")
    combined_content = ""

    for path in tf_paths:
        with open(path, "r", encoding="utf-8") as f:
            tf_code = f.read()
        combined_content += f"\n#File: {os.path.basename(path)}\n{tf_code}\n"

    print(f"\nEvaluating .tf files from: {tf_folder}")
    print("=" * 60)

    simple_answer = run_simple_rag(tf_text=combined_content)

    print("\n--- Simple RAG ---")
    print(simple_answer)

    print("\n--- Metrics ---")
    print(f"Score: {score_response(combined_content, simple_answer):.2f}")
    print(f"Length: {answer_length(simple_answer)} tokens")
    #print(f"Keyword Overlap: {keyword_overlap(combined_content, simple_answer):.2f}")

if __name__ == "__main__":
    #evaluate_multiple_tf_files("sample_tf")
    evaluate_tf_from_github('https://github.com/terraform-ibm-modules/terraform-ibm-cos')