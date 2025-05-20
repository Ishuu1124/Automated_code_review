import requests
OLLAMA_URL = "http://localhost:11434"
MODEL_NAME = "granite3.3"
def query_granite(prompt: str) -> str:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": False
            },
            timeout=180
        )
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.Timeout:
        return "[Error querying Granite] Request timed out."
    except Exception as e:
        return f"[Error querying Granite] {e}"
def embed_text(text: str) -> list:
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/embeddings",
            json={
                "model": MODEL_NAME,
                "prompt": text
            },
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("embedding", [])
    except requests.exceptions.Timeout:
        print("[Error embedding] Request timed out.")
        return []
    except Exception as e:
        print(f"[Error embedding] {e}")
        return []