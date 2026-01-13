from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    def is_connected(self) -> bool:
        pass
        
    @abstractmethod
    def chat(self, prompt: str) -> str:
        pass
