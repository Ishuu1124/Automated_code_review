# RAG Evaluation: Simple RAG for IBM Terraform Docs
- This minimalist project evaluates a **Simple RAG** (Retrieval-Augmented Generation) pipeline using IBM Cloud Terraform `.tf` files and Granite 3.2 via [Ollama](https://ollama.com/). The goal is to assess how well RAG can answer technical prompts based on real Terraform code.
---
## Features
- **Simple RAG Implementation**:
  - FAISS-based vector search over IBM Terraform `.tf` files
  - Embedding with `sentence-transformers`
  - Generation using **Granite-3.2** model locally via Ollama
- **Evaluation Metrics**:
  - Semantic similarity score
  - Response length
  - Keyword overlap
  - Response time (seconds)
- **Formatted Results Table**:
  - Markdown table (`results/comparison_table.md`) auto-updated on each run
  - Prevents duplicate query entries
  - Supports clearing results with `--refresh`
---
## Setup Instructions
- Clone the repository
```bash
git clone https://github.ibm.com/GoldenEyeIndianSquad/Automated-TF-Code-Review.git
cd Automated-TF-Code-Review
pip install -r requirements.txt
```
- Start Granite model with Ollama
```bash
ollama run granite3.2
```
- Add terraform files in `data/sample_docs`
- Add yours prompts in `prompts/query_prompts.txt`. Write one prompt per line.
- Run the app using
```bash
python app.py
``` 
- To clear previous results and start fresh:
```bash
python app.py --refresh
```