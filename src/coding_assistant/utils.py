from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()

def get_llm(model,max_retries):
    """
    Initializes and returns a ChatGoogleGenerativeAI instance configured
    with the 'gemini-3.5-flash-lite' model and a high retry limit to handle rate limits.
    """
    return ChatGoogleGenerativeAI(
        model=model,
        max_retries=max_retries # if we reach rpm limit it just waits before making another request
    )

def extract_text(content):
    """
    Extracts and concatenates text from a given content input.
    
    Args:
        content (str or list): Either a string or a list of dictionaries containing text keys.
        
    Returns:
        str: The extracted plain text string.
    """
    if isinstance(content,str):
        return content
    return "".join(d.get("text","") for d in content if isinstance(d,dict))