from abc import ABC , abstractmethod

class LLMProvider(ABC):
    """Abstract inteface for LLM providers."""
    @abstractmethod
    def generate(self, prompt:str) ->str:
        """
        Genrate a text response from the LLM .
        Args:
            prompt: Input prompt for the language model.
        
        Returns:
            Generated text response.
        """
        pass