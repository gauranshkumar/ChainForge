"""
Custom Ollama provider for ChainForge optimizer.

This is a workaround to make Ollama available to the Flask backend optimizer.
Built-in providers (OpenAI, Anthropic, Ollama, etc.) are only available in the frontend.
"""

from chainforge.providers import provider
import requests
import json


@provider(
    name="Ollama (Custom)",
    emoji="🦙",
    models=["llama2", "llama3", "mistral", "phi", "gemma"],  # Add your models here
    settings_schema={
        "type": "object",
        "properties": {
            "base_url": {
                "type": "string",
                "title": "Base URL",
                "description": "Ollama API base URL",
                "default": "http://localhost:11434"
            },
            "model": {
                "type": "string",
                "title": "Model",
                "description": "Model name (e.g., llama2, mistral)",
                "default": "llama2"
            },
            "temperature": {
                "type": "number",
                "title": "Temperature",
                "description": "Sampling temperature",
                "default": 0.0,
                "minimum": 0.0,
                "maximum": 2.0
            },
            "max_tokens": {
                "type": "integer",
                "title": "Max Tokens",
                "description": "Maximum tokens to generate",
                "default": 100,
                "minimum": 1,
                "maximum": 4096
            }
        }
    }
)
def ollama_custom_provider(prompt, model=None, **kwargs):
    """
    Call Ollama API.

    Args:
        prompt: The prompt string
        model: Model name (optional, falls back to settings)
        **kwargs: Additional settings (base_url, temperature, max_tokens, etc.)

    Returns:
        The generated text response
    """
    # Get settings
    base_url = kwargs.get('base_url', 'http://localhost:11434')
    model_name = model or kwargs.get('model', 'llama2')
    temperature = kwargs.get('temperature', 0.0)
    max_tokens = kwargs.get('max_tokens', 100)

    # Prepare request
    url = f"{base_url}/api/generate"
    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens
        }
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '')
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ollama API error: {str(e)}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse Ollama response: {str(e)}")
