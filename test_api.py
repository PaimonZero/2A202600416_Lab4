import os
from dotenv import load_dotenv
from pydantic import SecretStr
from langchain_openai import ChatOpenAI

# 1. load environment variables from .env file
load_dotenv()

def get_test_model():
    github_pat = os.getenv("GITHUB_PAT");
    openai_key = os.getenv("OPENAI_API_KEY");
    
    # Use GitHub PAT first, then fall back to OpenAI API key if GitHub PAT is not available
    if github_pat:
        print("Using GitHub PAT for authentication.")
        return ChatOpenAI(model="gpt-4o-mini", api_key=SecretStr(github_pat), base_url="https://models.inference.ai.azure.com")
    elif openai_key:
        print("Using OpenAI API key for authentication.")
        return ChatOpenAI(model="gpt-4", api_key=SecretStr(openai_key))
    else:
        raise ValueError("No valid API key found. Please set GITHUB_PAT or OPENAI_API_KEY in your .env file.")
    
try:
    # Init model
    llm = get_test_model()
    
    # Test the model with a simple prompt
    print("[Testing API] What is the capital of France?")
    response = llm.invoke("What is the capital of France?")
    
    # Print the response
    print("[API Response]", response.content)
    print("[Test Passed] API call successful!!")
except Exception as e:
    print("[Test Failed] API call failed with error:", str(e))
    