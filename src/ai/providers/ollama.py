import requests
from .base import LLMProvider

class OllamaProvider(LLMProvider):
    def __init__(self, model: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        
    def is_connected(self) -> bool:
        try:
            requests.get(self.base_url, timeout=1)
            return True
        except:
            return False
            
    def chat(self, prompt: str) -> str:
        try:
            url = f"{self.base_url}/api/generate"
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False
            }
            resp = requests.post(url, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("response", "")
            else:
                return f"Error: Ollama returned {resp.status_code}"
        except Exception as e:
            return f"Error communicating with Ollama: {e}"
