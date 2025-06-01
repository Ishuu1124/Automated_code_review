import requests
from ibm_watsonx_ai import APIClient, Credentials
from ibm_watsonx_ai.foundation_models import ModelInference, Embeddings
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes

import os
from dotenv import load_dotenv

load_dotenv()

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
            timeout=120
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
            timeout=60
        )
        response.raise_for_status()
        return response.json().get("embedding", [])
    except requests.exceptions.Timeout:
        print("[Error embedding] Request timed out.")
        return []
    except Exception as e:
        print(f"[Error embedding] {e}")
        return []
    
def query_watsonx(query_text: str):
    api_key=os.getenv('WATSONX_API_KEY')
    project_id=os.getenv('PROJECT_ID')
    credentials = Credentials(
        url='https://us-south.ml.cloud.ibm.com',
        api_key=api_key
    )
    client = APIClient(credentials=credentials)
    if client.set.default_project(project_id=project_id) == 'SUCCESS':
        # client.foundation_models.TextModels.show()
        # client.foundation_models.EmbeddingModels.show()
        model = ModelInference(model_id='ibm/granite-3-3-8b-instruct', project_id=project_id, credentials=credentials)
    
    try:
        response = model.chat(
            messages=[{
                "role": "user",
                "content": query_text
            }]
        )
        return response.get("choices", "")[0].get("message","").get("content","").strip()
    except requests.exceptions.Timeout:
        return "[Error querying Granite] Request timed out."
    except Exception as e:
        return f"[Error querying Granite] {e}"
        
    
def embed_watson(query_text: str):
    api_key=os.getenv('WATSONX_API_KEY')
    project_id=os.getenv('PROJECT_ID')
    credentials = Credentials(
        url='https://us-south.ml.cloud.ibm.com',
        api_key=api_key
    )
    client = APIClient(credentials=credentials)
    if client.set.default_project(project_id=project_id) == 'SUCCESS':
        # client.foundation_models.TextModels.show()
        # client.foundation_models.EmbeddingModels.show()
        model=Embeddings(model_id='ibm/slate-125m-english-rtrvr-v2', project_id=project_id, credentials=credentials, batch_size=32)
    
    try:
        response = model.embed_query(query_text)
        return response
    except requests.exceptions.Timeout:
        return "[Error querying Granite] Request timed out."
    except Exception as e:
        return f"[Error querying Granite] {e}"
        