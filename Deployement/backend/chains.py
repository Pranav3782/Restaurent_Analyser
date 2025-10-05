import os
from dotenv import load_dotenv
import json
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI

# Import the new, more robust prompts
from backend.prompts import (
    ANALYSIS_PROMPT,
    CHATBOT_PROMPT,
    DISH_RECOMMENDATION_PROMPT,
    SLOGAN_GENERATION_PROMPT
)

# Load environment variables from .env file
load_dotenv()

def _get_api_key_or_raise():
    """Helper to ensure the API key is loaded."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("CRITICAL ERROR: GOOGLE_API_KEY was not found. Please check your .env file.")
    print(f"API Key: {api_key[:10]}...") # Debug print
    return api_key

def get_restaurant_analysis_chain():
    """
    Creates and returns a LangChain chain for restaurant analysis.
    This now uses the modern LCEL syntax (prompt | llm).
    """
    api_key = _get_api_key_or_raise()
    print("Hello from Gemini!") # Debug print

    prompt = PromptTemplate(
        template=ANALYSIS_PROMPT,
        input_variables=["input", "analysis_type", "restaurant_location_context"]
    )
    # Using a fast model for analysis to stay within free tier limits
    json_llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-preview-05-20",
        temperature=0.5,
        google_api_key=api_key,
        # The new Google GenAI library natively supports JSON mode
        model_kwargs={"response_mime_type": "application/json"}
    )
    # Modern LCEL syntax: pipe the prompt to the language model
    chain = prompt | json_llm
    return chain

def _format_analysis_data_for_chatbot(data: dict) -> str:
    """Internal helper function to format the analysis data into a string for the chatbot context."""
    # This creates a readable summary of the analysis for the chatbot to use.
    formatted_parts = []
    for key, value in data.items():
        if isinstance(value, dict):
            # Format nested dictionaries (like dietary_options)
            for sub_key, sub_value in value.items():
                formatted_parts.append(f"{key.replace('_', ' ').title()} - {sub_key.replace('_', ' ').title()}: {sub_value}")
        elif isinstance(value, list):
            # Format lists (like popular_dishes)
            formatted_parts.append(f"{key.replace('_', ' ').title()}: {', '.join(value)}")
        else:
            # Format simple key-value pairs
            formatted_parts.append(f"{key.replace('_', ' ').title()}: {value}")
    return "\n".join(formatted_parts)


def get_chatbot_response(analysis_text_raw: str, user_question: str) -> str:
    """
    Generates a contextual response to a user's question based on the analysis.
    """
    api_key = _get_api_key_or_raise()
    print("Hello from Gemini! It's great to connect.") # Debug print
    
    # Using a fast and capable model for chat to avoid quota issues
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20", google_api_key=api_key, temperature=0.7)

    try:
        parsed_analysis_data = json.loads(analysis_text_raw)
        formatted_analysis_content = _format_analysis_data_for_chatbot(parsed_analysis_data)
    except Exception as e:
        return f"Error: Failed to process analysis data for the chatbot: {e}"

    prompt = PromptTemplate(
        template=CHATBOT_PROMPT,
        input_variables=["analysis_content", "question"]
    )
    chain = prompt | llm
    try:
        response = chain.invoke({"analysis_content": formatted_analysis_content, "question": user_question})
        return response.content
    except Exception as e:
        print(f"Error invoking chatbot chain: {e}")
        # Provide a more user-friendly error
        error_message = str(e)
        if "quota" in error_message.lower():
            return "I'm sorry, but I've reached my request limit for the moment. Please try again in a little while."
        return f"Sorry, I encountered an error trying to answer that: {e}"

# The following functions are kept for potential future use
def get_dish_recommendation(analysis_text_raw: str) -> str:
    api_key = _get_api_key_or_raise()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20", google_api_key=api_key)
    formatted_content = _format_analysis_data_for_chatbot(json.loads(analysis_text_raw))
    prompt = PromptTemplate(template=DISH_RECOMMENDATION_PROMPT, input_variables=["analysis_content"])
    chain = prompt | llm
    response = chain.invoke({"analysis_content": formatted_content})
    return response.content

def get_slogan_generation(analysis_text_raw: str) -> str:
    api_key = _get_api_key_or_raise()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20", google_api_key=api_key)
    formatted_content = _format_analysis_data_for_chatbot(json.loads(analysis_text_raw))
    prompt = PromptTemplate(template=SLOGAN_GENERATION_PROMPT, input_variables=["analysis_content"])
    chain = prompt | llm
    response = chain.invoke({"analysis_content": formatted_content})
    return response.content

