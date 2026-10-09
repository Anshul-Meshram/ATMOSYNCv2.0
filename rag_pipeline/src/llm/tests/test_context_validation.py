from src.llm.context.assembler import assemble_context
from src.llm.schemas.request import LLMRequest

def main():
    # Valid request should work 
    valid_request = LLMRequest(
        user_query = "Explain this climate animaly.",
        ml_context = {"severity":"high"},
        rag_context = {"results": []},
    )
    assert assemble_context(valid_request)

    #Empty query should fail 
    try:
        assemble_context(LLMRequest(user_query = "  "))
    except ValueError:
        pass
    else:
        raise AssertionError("Empty query was not rejected.")

    #Incorrect context type should fail
    try:
        assemble_context(
            LLMRequest(
                user_query = "Explain this event.",
                ml_context = "not a dictionary",
            )
        )
    except TypeError:
        pass
    else:
        raise AssertionError("Invalid ML context was not rejected.")
    print("Context validation test: SUCCESS")

if __name__ == "__main__":
    main()

