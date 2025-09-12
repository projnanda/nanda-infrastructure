#!/usr/bin/env python3
import os
from nanda_adapter import NANDA
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_anthropic import ChatAnthropic

def create_linearalgebra():
    """Create a LangChain-powered agent that explains the important concepts of linear algebra."""

    # Initialize the LLM
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307"
    )

    # Create a prompt template for pirate transformation
    prompt = PromptTemplate(
        input_variables=["message"],
        template="""Explain what linear algebra is and why it is an important subject to study. Make sure the mention the following topics: matrix and vector algebra, Gaussian Elimination, Vector Spaces, Linear. Independence, and Eigenvectors. 
        Respond in language that is easy to understand and try solving a simple math problem with Gaussian Elimination. 
        
        Original message: {message}
        
        Linear Algebra response:"""
    )

    # Create the chain
    chain = prompt | llm | StrOutputParser()

    def pirate_improvement(message_text: str) -> str:
        """Teach the important concepts of the math subject, Linear Algebra"""
        try:
            result = chain.invoke({"message": message_text})
            return result.strip()
        except Exception as e:
            print(f"Error in teaching Linear Algebra: {e}")
            return f"Count to 1, 2, 3{message_text}, I don't know Linear Algebra!"  # Fallback pirate transformation

    return pirate_improvement

def main():
    """Main function to start the Linear Algebra Agent"""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set your ANTHROPIC_API_KEY environment variable")
        return

    # Create pirate improvement function
    pirate_logic = create_linearalgebra()

    # Initialize NANDA with pirate logic
    nanda = NANDA(pirate_logic)

    # Start the server
    print("Starting Linear Algebra Agent with LangChain...")
    print("We will teach you Linear Algebra in 3 seconds")

    domain = os.getenv("DOMAIN_NAME", "localhost")
    # debbie add
    # port = int(os.getenv("PORT", "6000"))

    if domain != "localhost":
        # Production with SSL
        nanda.start_server_api(os.getenv("ANTHROPIC_API_KEY"), domain)
    else:
        # Development server
        nanda.start_server()
        

if __name__ == "__main__":
    main()