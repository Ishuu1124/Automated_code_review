import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "granite3.2"

def query_granite(prompt: str) -> str:
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"[Error querying Granite] {e}"