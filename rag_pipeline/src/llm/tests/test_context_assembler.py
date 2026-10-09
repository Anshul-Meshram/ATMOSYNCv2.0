from src.llm.context.assembler import assemble_context
from src.llm.schemas.request import LLMRequest

def main():
    request = LLMRequest(
        user_query = "Why is Alberta experiencing unusual heat ?"
    )