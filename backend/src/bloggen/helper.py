# Add your utilities or helper functions to this file.

import os
from dotenv import load_dotenv, find_dotenv

# these expect to find a .env file at the directory above the lesson.                                                                                                                     # the format for that file is (without the comment)                                                                                                                                       #API_KEYNAME=AStringThatIsTheLongAPIKeyFromSomeService                                                                                                                                     
def load_env():
    # Try to find .env file in the backend directory first
    backend_env = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
    if os.path.exists(backend_env):
        load_dotenv(backend_env)
        return
    
    # Fallback to standard search
    _ = load_dotenv(find_dotenv())

def get_openai_api_key():
    load_env()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    return openai_api_key

def get_serper_api_key():
    load_env()
    serper_api_key = os.getenv("SERPER_API_KEY")
    return serper_api_key

def get_researcher_model():
    load_env()
    researcher_model = os.getenv("RESEARCHER_MODEL")
    return researcher_model