import requests
import json
from typing import Optional, List, Any, Dict
from .protocol import ProviderRegistry, provider, ChatHistory

@provider(name="ollama", emoji="🦙")
def ollama_provider(prompt: str, model: Optional[str] = None, chat_history: Optional[ChatHistory] = None, **kwargs) -> str:
    """
    Native Ollama provider for ChainForge backend.
    """
    # Extract settings
    ollama_url = kwargs.get("ollama_url", "http://localhost:11434")
    ollama_model = kwargs.get("ollamaModel") or model or "llama2"
    temperature = kwargs.get("temperature", 1.0)
    
    # Handle model_type if present (not strictly needed if we infer from usage, but good to have)
    model_type = kwargs.get("model_type", "text")

    # Construct URL
    if not ollama_url.endswith("/"):
        ollama_url += "/"
    
    # Determine if chat or generate
    # Simple heuristic: if chat_history is present or model_type is chat, use chat endpoint
    is_chat = chat_history is not None or model_type == "chat"
    
    api_endpoint = "api/chat" if is_chat else "api/generate"
    url = f"{ollama_url}{api_endpoint}"

    payload = {
        "model": ollama_model,
        "stream": False,
        "options": {
            "temperature": temperature,
            # Add other options from kwargs if needed
        }
    }

    if is_chat:
        messages = []
        if chat_history:
            messages.extend(chat_history)
        # Add the current prompt as a user message
        messages.append({"role": "user", "content": prompt})
        payload["messages"] = messages
    else:
        payload["prompt"] = prompt

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        
        if is_chat:
            return data.get("message", {}).get("content", "")
        else:
            return data.get("response", "")
            
    except Exception as e:
        raise ValueError(f"Error calling Ollama: {e}")
