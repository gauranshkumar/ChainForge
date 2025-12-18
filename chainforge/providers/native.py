import requests
import json
from typing import Optional, List, Any, Dict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .protocol import ProviderRegistry, provider, ChatHistory

# Setup high-throughput session
session = requests.Session()
adapter = HTTPAdapter(pool_connections=100, pool_maxsize=100, max_retries=Retry(total=3, backoff_factor=0.1))
session.mount("http://", adapter)
session.mount("https://", adapter)

@provider(name="ollama", emoji="🦙")
def ollama_provider(prompt: str, model: Optional[str] = None, chat_history: Optional[ChatHistory] = None, **kwargs) -> str:
    """
    Native Provider for ChainForge. Supports:
    1. Ollama (default)
    2. Any OpenAI-compatible API (like vLLM) if URL contains "/v1"
    """
    # Extract settings
    ollama_url = kwargs.get("ollama_url", "http://localhost:11434")
    ollama_model = kwargs.get("ollamaModel") or model or "llama2"
    temperature = kwargs.get("temperature", 1.0)
    
    # Handle model_type
    model_type = kwargs.get("model_type", "text")

    # Clean URL
    if not ollama_url.endswith("/"):
        ollama_url += "/"
    
    # Determine mode: vLLM (OpenAI-compatible) or Standard Ollama
    is_vllm = "/v1/" in ollama_url
    
    # Determine if chat or generate
    is_chat = chat_history is not None or model_type == "chat"
    
    # --- vLLM / OpenAI-Compatible Logic ---
    if is_vllm:
        api_endpoint = "chat/completions" if is_chat else "completions"
        # If url already ends in v1/, appending chat/completions works (v1/chat/completions)
        # If url is host:port/, appending v1/chat/completions is needed?? 
        # Actually user likely provided http://localhost:8000/v1/ -> http://localhost:8000/v1/chat/completions
        url = f"{ollama_url}{api_endpoint}"

        payload = {
            "model": ollama_model,
            "temperature": temperature,
            # Map other options if needed, vLLM/OpenAI uses 'max_tokens' not 'num_predict'
            **kwargs.get("options", {})
        }

        if is_chat:
            messages = []
            if chat_history:
                messages.extend(chat_history)
            messages.append({"role": "user", "content": prompt})
            payload["messages"] = messages
        else:
            payload["prompt"] = prompt
            # vLLM/OpenAI usually expects max_tokens for completions, default to something reasonable if not set
            if "max_tokens" not in payload:
                payload["max_tokens"] = 1024

        try:
            response = session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if is_chat:
                return data["choices"][0]["message"]["content"]
            else:
                return data["choices"][0]["text"]
        except Exception as e:
            raise ValueError(f"Error calling vLLM/OpenAI-compatible API at {url}: {e} | Response: {response.text if 'response' in locals() else 'None'}")

    # --- Standard Ollama Logic ---
    else:
        api_endpoint = "api/chat" if is_chat else "api/generate"
        url = f"{ollama_url}{api_endpoint}"

        payload = {
            "model": ollama_model,
            "stream": False,
            "options": {
                "temperature": temperature,
                **kwargs.get("options", {})
            }
        }

        if is_chat:
            messages = []
            if chat_history:
                messages.extend(chat_history)
            messages.append({"role": "user", "content": prompt})
            payload["messages"] = messages
        else:
            payload["prompt"] = prompt

        try:
            response = session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            if is_chat:
                return data.get("message", {}).get("content", "")
            else:
                return data.get("response", "")
                
        except Exception as e:
            raise ValueError(f"Error calling Ollama at {url}: {e}")
