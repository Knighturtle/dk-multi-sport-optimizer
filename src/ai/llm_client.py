from .providers.ollama import OllamaProvider

class OllamaChatClient:
    """
    Wrapper for OllamaProvider to maintain backward compatibility with app.py
    """
    def __init__(self, model: str = "llama3"):
        self.provider = OllamaProvider(model=model)
        
    def is_connected(self) -> bool:
        return self.provider.is_connected()
        
    def chat(self, prompt: str) -> str:
        return self.provider.chat(prompt)
