import os
import json
import time
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import your LangChain logic
# Assuming these files are in the same 'backend' directory
from chains import (
    get_restaurant_analysis_chain, get_chatbot_response,
    get_dish_recommendation, get_slogan_generation
)

# Initialize the FastAPI app
app = FastAPI()

# Add CORS middleware to allow all origins (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models for Request Bodies ---
# These define the expected JSON structure for incoming requests

class AnalyzeRequest(BaseModel):
    restaurant_name: str
    analysis_type: str
    restaurant_location: str | None = None # Optional field

class ChatbotRequest(BaseModel):
    analysis_text_raw: str
    user_question: str

class DishRecommendRequest(BaseModel):
    analysis_text_raw: str

class SloganGenerateRequest(BaseModel):
    analysis_text_raw: str

# --- Helper Function ---

def clean_json_response(text: str):
    """
    Cleans the raw text output from the LLM to extract a valid JSON string.
    """
    match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if match:
        return match.group(1).strip()
    return text.strip()

# --- API Endpoints ---

@app.post('/analyze')
async def analyze_restaurant(request: AnalyzeRequest):
    """
    API endpoint for initial restaurant analysis.
    """
    try:
        restaurant_location_context = f"located in {request.restaurant_location}" if request.restaurant_location else ""
        analysis_chain = get_restaurant_analysis_chain()

        chain_input = {
            "input": request.restaurant_name,
            "analysis_type": request.analysis_type,
            "restaurant_location_context": restaurant_location_context
        }
        
        print(f"[{time.ctime()}] Starting LLM analysis for: {request.restaurant_name}")
        start_time = time.time()

        response = analysis_chain.invoke(chain_input)
        response_content = response.content

        end_time = time.time()
        print(f"[{time.ctime()}] LLM analysis completed in {end_time - start_time:.2f} seconds.")

        cleaned_json_string = clean_json_response(response_content)

        try:
            parsed_analysis = json.loads(cleaned_json_string)
            return parsed_analysis
        except json.JSONDecodeError as e:
            print(f"Warning: AI did not return valid JSON. Error: {e}. Cleaned content: {cleaned_json_string}")
            raise HTTPException(status_code=500, detail=f"Failed to parse AI response. Raw content: {response_content}")

    except Exception as e:
        print(f"[{time.ctime()}] Error in /analyze: {e}")
        error_message = str(e)
        if "quota" in error_message.lower():
            error_message = "You have exceeded the API quota. Please check your billing status or try again later."
        raise HTTPException(status_code=500, detail=error_message)


@app.post('/chatbot')
async def chatbot_query(request: ChatbotRequest):
    """
    API endpoint for chatbot follow-up questions.
    """
    try:
        print(f"[{time.ctime()}] Starting chatbot query for user: '{request.user_question}'")
        bot_response = get_chatbot_response(request.analysis_text_raw, request.user_question)
        print(f"[{time.ctime()}] Chatbot query completed.")
        return {"response": bot_response}

    except Exception as e:
        print(f"[{time.ctime()}] Error in /chatbot: {e}")
        error_message = str(e)
        if "quota" in error_message.lower():
            error_message = "You have exceeded the API quota for the chatbot. Please try again later."
        raise HTTPException(status_code=500, detail=error_message)

@app.post('/recommend_dishes')
async def recommend_dishes(request: DishRecommendRequest):
    try:
        recommendations = get_dish_recommendation(request.analysis_text_raw)
        return {"recommendations": recommendations}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post('/generate_slogan')
async def generate_slogan(request: SloganGenerateRequest):
    try:
        slogan = get_slogan_generation(request.analysis_text_raw)
        return {"slogan": slogan}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

