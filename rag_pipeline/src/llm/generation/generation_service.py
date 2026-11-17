from src.llm.clients.llm_provider import LLMProvider 
from src.llm.context.assembler import assemble_context
from src.llm.schemas.request import LLMRequest

class GenerationService:
    """
    Coordinates context assembly and provider-based generation.
    This services does not depend on a specific LLM provider.
    """
    def __init__(self,provider:LLMProvider):
        self.provider = provider

    def generate(self,request:LLMRequest) -> str:
        """
        Assemble the validate request and generate a reponse. 
        """
        prompt = assemble_context(request)
        return self.provider.generate(prompt)