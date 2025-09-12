#!/usr/bin/env python3
import os
from nanda_adapter import NANDA
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_anthropic import ChatAnthropic

def create_major_advice():
    """Create a LangChain-powered agent that gives college major advice"""

    # Initialize the LLM
    llm = ChatAnthropic(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        model="claude-3-haiku-20240307"
    )

    # Create a prompt template for pirate transformation
    prompt = PromptTemplate(
        input_variables=["message"],
        template="""Give high school and college students advice on selecting a major to study in college. Be encouraging and optimistic. Encourage the students to pursue their passions and their dreams. 
        Use positive, uplifting, and empathetic vocabularly, grammar, and expressions like 'dream', 'inspire', 'mission', etc. Ask questions to encourage students to think more deeply about what they want to study. 
        
        Original message: {message}
        
        College major advice response:"""
    )

    # Create the chain
    chain = prompt | llm | StrOutputParser()

    def pirate_improvement(message_text: str) -> str:
        """Give students encouraging advice on selecting a major to study"""
        try:
            result = chain.invoke({"message": message_text})
            return result.strip()
        except Exception as e:
            print(f"Error in giving advice: {e}")
            return f"Oh no! {message_text}, I'm sorry I don't have advice."  # Fallback response

    return pirate_improvement

def main():
    """Main function to start the college major advice agent"""

    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Please set your ANTHROPIC_API_KEY environment variable")
        return

    # Create pirate improvement function
    pirate_logic = create_major_advice()

    # Initialize NANDA with pirate logic
    nanda = NANDA(pirate_logic)

    # Start the server
    print("Starting College Major Advice Agent with LangChain...")
    print("Giving college major advice!")

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